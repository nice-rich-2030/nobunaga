"""
SequentialTurnManager - Sequential方式ターン進行管理
README_FLOW2.md準拠: 大名順逐次処理方式

S1. 全ての領地について（税収・維持費・イベント）
S2. 全ての生きている大名・将軍について（健康・加齢・死亡判定）
S3. すべての生きている大名について（ランダム順序でコマンド実行）
"""
from typing import List, Dict, Any, Generator, Tuple, Optional
import random
import config
from models.province import Province
from models.daimyo import Daimyo


class SequentialTurnManager:
    """Sequential方式ターン進行管理クラス（generator/yieldパターン）"""

    # コマンド分類
    INTERNAL_COMMANDS = [
        "cultivate", "develop_town", "flood_control", "give_rice",
        "transfer_soldiers", "transfer_gold", "transfer_rice", "assign_general"
    ]
    MILITARY_COMMANDS = ["recruit", "attack"]

    def __init__(self, game_state):
        self.game_state = game_state
        self.turn_events: List[str] = []
        self.ai_system = None
        self.diplomacy_system = None
        self.event_system = None
        self.internal_affairs = None
        self.military_system = None
        self.transfer_system = None

        # V2用の状態
        self.pending_event_choices: List[Dict[str, Any]] = []
        self.current_daimyo_order: List[int] = []

    def execute_turn(self) -> Generator[Tuple[str, Any], None, Optional[Dict]]:
        """
        メインのターン実行（generator）

        yieldされるイベント:
        - ("turn_start", message): ターン開始メッセージ
        - ("message", text): AI大名のコマンド実行メッセージ
        - ("death_animation", character_data): 死亡演出
        - ("battle_animation", battle_data): 戦闘演出
        - ("victory", None): 勝利
        - ("player_turn", daimyo_id): プレイヤーの番
        - ("game_over", None): ゲームオーバー

        Returns:
            勝者の大名ID（勝利条件達成時）またはNone
        """
        self.turn_events.clear()

        # ターン開始メッセージを即座に表示
        turn_start_msg = f"=== ターン {self.game_state.current_turn + 1} 開始 ==="
        self.turn_events.append(turn_start_msg)
        yield ("turn_start", turn_start_msg)

        # ターンを進める
        self.game_state.advance_turn()

        # 領地のコマンドフラグをリセット
        for province in self.game_state.provinces.values():
            province.reset_command_flag()

        # S1: 全ての領地について
        yield from self._section_1_provinces()

        # S2: 全ての生きている大名・将軍について
        yield from self._section_2_characters()

        # S3: すべての生きている大名について（ランダム順序）
        result = yield from self._section_3_daimyo_actions()

        # ターン終了処理
        self._turn_end()

        return result

    # ========================================
    # S1: 領地処理
    # ========================================

    def _section_1_provinces(self) -> Generator:
        """S1: 全領地の処理"""
        player_daimyo = self.game_state.get_player_daimyo()
        total_rice = 0
        total_gold = 0
        total_rice_consumed = 0

        # 忠誠度を事前記録（警告判定用）
        loyalty_before = {}

        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id is None:
                continue

            # 忠誠度を記録
            loyalty_before[province.id] = province.peasant_loyalty

            # Phase1: 税収・米生産
            rice_income, gold_income = self._s1_phase1_income(province)

            # Phase2: 維持費処理
            rice_consumed = self._s1_phase2_upkeep(province)

            # Phase3: ランダムイベント抽選
            self._s1_phase3_random_events(province)

            # Phase4: 状態反映（忠誠度減衰など）
            self._s1_phase4_apply_state(province)

            # プレイヤーの収支を集計
            if player_daimyo and province.owner_daimyo_id == player_daimyo.id:
                total_rice += rice_income
                total_gold += gold_income
                total_rice_consumed += rice_consumed

        # プレイヤーの収支を表示
        if player_daimyo:
            if total_rice > 0 or total_gold > 0:
                self.turn_events.append(f" 【収入】米+{total_rice}、金+{total_gold}")
            if total_rice_consumed > 0:
                self.turn_events.append(f" 【維持費】米-{total_rice_consumed}（兵士の消費）")

        # ランダムイベント処理（yield版で即座に表示）
        yield from self._s1_process_random_events_with_yield()

        # 忠誠度警告をyield
        for province_id, old_loyalty in loyalty_before.items():
            province = self.game_state.get_province(province_id)
            if not province:
                continue

            new_loyalty = province.peasant_loyalty
            change = new_loyalty - old_loyalty

            # 20以上低下 または 30以下になった場合に警告
            if change <= -20 or new_loyalty <= 30:
                msg = self._format_loyalty_warning(province, change)
                yield ("message", msg)

    def _s1_phase1_income(self, province: Province) -> Tuple[int, int]:
        """Phase1: 税収・米生産"""
        # 農民の自然増加（1%）
        peasant_growth = int(province.peasants * 0.01)
        if peasant_growth > 0:
            province.add_peasants(peasant_growth)

        # 米生産
        rice_produced = province.calculate_rice_production()
        province.add_rice(rice_produced)

        # 税収
        gold_income = province.calculate_tax_income()
        province.add_gold(gold_income)

        return rice_produced, gold_income

    def _s1_phase2_upkeep(self, province: Province) -> int:
        """Phase2: 維持費処理"""
        # 兵士の米消費
        rice_needed = province.calculate_soldier_rice_consumption()
        province.add_rice(-rice_needed)

        # 米不足の場合、士気低下
        if province.rice < 0:
            province.rice = 0
            province.update_morale(config.MORALE_LOW_RICE_PENALTY)
            self.turn_events.append(f"【警告】{province.name}: 米不足により士気低下")
        else:
            # 士気の自然回復
            province.update_morale(config.MORALE_DECAY_RATE)

        return rice_needed

    def _s1_phase3_random_events(self, province: Province):
        """Phase3: ランダムイベント抽選"""
        # V2では領地ごとにイベントチェックを行う必要があるが、
        # EventSystemは全領地を一括チェックするため、ここでは何もしない
        # イベント処理はS1の最後にまとめて行う
        pass

    def _s1_process_random_events(self):
        """S1の最後に全領地のランダムイベントをまとめて処理"""
        if not self.event_system:
            return

        current_season = self.game_state.get_season_name()
        triggered_events = self.event_system.check_events_for_turn(current_season)

        for event, province in triggered_events:
            # 選択肢があるイベントかつプレイヤーの領地の場合
            if event.has_choices() and province.owner_daimyo_id == 1:
                self.pending_event_choices.append({
                    "event": event,
                    "province": province
                })
                self.turn_events.append(
                    f"【{event.name}】{province.name}でイベントが発生しました（選択待ち）"
                )
            else:
                # 自動処理
                choice_id = None
                if event.has_choices() and province.owner_daimyo_id != 1:
                    choice = random.choice(event.choices)
                    choice_id = choice.choice_id

                self.event_system.apply_event_effect(event, province, choice_id)

                daimyo = self.game_state.get_daimyo(province.owner_daimyo_id)
                owner_name = daimyo.clan_name if daimyo else "無所属"
                description = event.description.format(province_name=province.name)
                self.turn_events.append(
                    f"【{event.name}】{owner_name}の{province.name}: {description}"
                )

    def _s1_process_random_events_with_yield(self) -> Generator:
        """S1のランダムイベント処理（yield版 - 即座に表示）"""
        if not self.event_system:
            return

        current_season = self.game_state.get_season_name()
        triggered_events = self.event_system.check_events_for_turn(current_season)

        for event, province in triggered_events:
            # 選択肢があるイベントかつプレイヤーの領地の場合
            if event.has_choices() and province.owner_daimyo_id == 1:
                self.pending_event_choices.append({
                    "event": event,
                    "province": province
                })
                msg = f"【{event.name}】{province.name}でイベントが発生しました（選択待ち）"
                self.turn_events.append(msg)
                # プレイヤー選択イベントは後で処理するため、ここでは表示のみ
            else:
                # 自動処理
                choice_id = None
                if event.has_choices() and province.owner_daimyo_id != 1:
                    choice = random.choice(event.choices)
                    choice_id = choice.choice_id

                self.event_system.apply_event_effect(event, province, choice_id)

                owner_name = self._get_owner_name(province)
                description = event.description.format(province_name=province.name)
                # icon = self._get_event_icon(event.event_type)

                msg = f" 【{owner_name}】【{province.name}】  {event.name}: {description}"

                # 即座にyield
                yield ("message", msg)
                self.turn_events.append(msg)

    def _s1_phase4_apply_state(self, province: Province):
        """Phase4: 領地の状態に反映（忠誠度減衰など）"""
        # 忠誠度の自然減衰
        loyalty_change = config.LOYALTY_DECAY_RATE
        # 税率が高い場合、追加ペナルティ
        if province.tax_rate > 50:
            loyalty_change += int((province.tax_rate - 50) * config.LOYALTY_TAX_PENALTY)
        province.update_loyalty(loyalty_change)

    # ========================================
    # S2: キャラクター処理
    # ========================================

    def _section_2_characters(self) -> Generator:
        """S2: 全大名・武将の処理"""
        # 春のみ加齢処理
        if self.game_state.current_season != config.SEASON_SPRING:
            return
            yield

        # 大名の処理
        for daimyo in list(self.game_state.daimyo.values()):
            if not daimyo.is_alive:
                continue

            # Phase1: 健康処理
            self._s2_phase1_health(daimyo)

            # Phase2: 年齢処理
            old_age = daimyo.age
            old_health = daimyo.health
            daimyo.age_one_year()

            # Phase3: 死亡判定
            if old_health > 0 and not daimyo.is_alive:
                death_data = {
                    "type": "daimyo",
                    "id": daimyo.id,
                    "daimyo_id": daimyo.id,  # UI互換性のため
                    "name": daimyo.name,
                    "daimyo_name": daimyo.name,  # UI互換性のため
                    "clan_name": daimyo.clan_name,
                    "age": old_age,
                    "is_player": daimyo.is_player,
                    "cause": "illness"  # 病死
                }

                # Phase4: 死亡演出（UIへ制御を渡す）
                yield ("death_animation", death_data)

                # プレイヤーが病死した場合はゲームオーバー
                if daimyo.is_player:
                    yield ("game_over", death_data)
                    return

                # Phase5: 死亡結果を反映
                self._s2_phase5_apply_daimyo_death(daimyo)

        # 武将の処理
        for general in list(self.game_state.generals.values()):
            if not general.is_alive():
                continue

            old_health = general.health
            general.age_one_year()

            if old_health > 0 and not general.is_alive():
                self.turn_events.append(f"武将 {general.name}が死去しました")

    def _s2_phase1_health(self, character):
        """Phase1: 健康処理（将来の拡張用）"""
        pass

    def _s2_phase5_apply_daimyo_death(self, daimyo: Daimyo):
        """Phase5: 大名死亡結果を反映"""
        self.turn_events.append(f"【訃報】{daimyo.clan_name}の{daimyo.name}が病死しました（享年{daimyo.age}歳）")

        # 領地を中立に
        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id == daimyo.id:
                province.owner_daimyo_id = None

    # ========================================
    # S3: 大名行動処理
    # ========================================

    def _section_3_daimyo_actions(self) -> Generator:
        """S3: 大名ごとの行動処理（ランダム順序）"""
        # ランダム順序で大名を取得
        self.current_daimyo_order = self._get_randomized_daimyo_order()

        # デバッグログ: 大名の処理順序を出力
        order_names = [self.game_state.get_daimyo(did).clan_name for did in self.current_daimyo_order
                       if self.game_state.get_daimyo(did) and self.game_state.get_daimyo(did).is_alive]
        print(f"[DEBUG-S3開始] 大名処理順序: {' → '.join(order_names)}")

        for daimyo_id in self.current_daimyo_order:
            daimyo = self.game_state.get_daimyo(daimyo_id)
            if not daimyo or not daimyo.is_alive:
                continue

            print(f"\n[DEBUG-S3] === {daimyo.clan_name}のターン開始 ===")

            # 軍事コマンドリスト（この大名の番で登録されたもの）
            military_commands = []

            if daimyo.is_player:
                # Phase2: プレイヤー大名のコマンド選択
                # UIへ制御を渡してプレイヤーの入力を待つ
                print(f"[DEBUG-プレイヤーターン] プレイヤー入力待機中...")
                player_result = yield ("player_turn", daimyo_id)
                print(f"[DEBUG-プレイヤーターン] プレイヤー入力受信: {player_result}")

                # プレイヤーが登録した内政コマンドを実行
                if player_result and "internal_commands" in player_result:
                    print(f"[DEBUG-プレイヤーターン] 内政コマンド数: {len(player_result['internal_commands'])}")
                    for cmd in player_result["internal_commands"]:
                        province = self.game_state.get_province(cmd["province_id"])
                        if province:
                            yield from self._execute_internal_command(province, daimyo, cmd)

                # プレイヤーが登録した軍事コマンドを受け取る
                if player_result and "military_commands" in player_result:
                    military_commands = player_result["military_commands"]
                    print(f"[DEBUG-プレイヤーターン] 軍事コマンド数: {len(military_commands)}")
            else:
                # Phase1: AI大名のコマンド自動選択
                # generatorを実行してメッセージをyield、最後に軍事コマンドリストを取得
                ai_gen = self._execute_ai_commands(daimyo)
                military_commands = None
                try:
                    while True:
                        event = next(ai_gen)
                        yield event  # メッセージイベントをUIに渡す
                except StopIteration as e:
                    military_commands = e.value if e.value is not None else []

            # Phase3: 軍事コマンドリストの順次実行
            print(f"[DEBUG-S3] {daimyo.clan_name}の軍事コマンド実行開始（コマンド数: {len(military_commands)}）")
            result = yield from self._execute_military_commands(daimyo, military_commands)
            print(f"[DEBUG-S3] === {daimyo.clan_name}のターン終了 ===\n")
            if result:
                return result

        # 外交更新
        if self.diplomacy_system:
            events = self.diplomacy_system.update_treaties()
            self.turn_events.extend(events)

        return None

    def _get_randomized_daimyo_order(self) -> List[int]:
        """ランダム順序で大名IDリストを取得"""
        living_daimyo_ids = [
            d.id for d in self.game_state.daimyo.values()
            if d.is_alive
        ]
        random.shuffle(living_daimyo_ids)
        return living_daimyo_ids

    def _execute_ai_commands(self, daimyo: Daimyo) -> Generator:
        """AI大名のコマンドを実行し、軍事コマンドリストを返す（generator）"""
        military_commands = []

        if not self.ai_system:
            return military_commands

        # AI大名の領地を取得
        ai_provinces = [
            p for p in self.game_state.provinces.values()
            if p.owner_daimyo_id == daimyo.id
        ]

        print(f"[DEBUG-AI実行] {daimyo.clan_name}の領地数: {len(ai_provinces)}")
        if ai_provinces:
            province_names = [p.name for p in ai_provinces]
            print(f"[DEBUG-AI実行] {daimyo.clan_name}の領地: {', '.join(province_names)}")

        if not ai_provinces:
            print(f"[DEBUG-AI実行] {daimyo.clan_name}は領地なし、コマンド決定をスキップ")
            return military_commands

        # AI大名の行動開始ディレイ
        import config
        yield ("ai_action_delay", config.AI_ACTION_DELAY)

        # 将軍配置（コマンド扱い）
        yield from self._ai_assign_generals(daimyo, ai_provinces)

        # 各領地でコマンドを決定・実行（1領地につき1コマンド）
        for province in ai_provinces:
            if province.command_used_this_turn:
                continue  # 既にコマンド使用済み

            # 軍事コマンドを優先的に検討
            military_action = self._ai_decide_military_action(province, daimyo)
            if military_action["type"] != "none":
                military_action["province_id"] = province.id
                military_commands.append(military_action)
                province.command_used_this_turn = True
                continue

            # 軍事コマンドがなければ内政コマンド（即時反映）
            internal_action = self._ai_decide_internal_action(province, daimyo)
            if internal_action["type"] != "none":
                yield from self._execute_internal_command(province, daimyo, internal_action)

        return military_commands

    def _ai_assign_generals(self, daimyo: Daimyo, provinces: List[Province]) -> Generator:
        """AI: 将軍を領地に配置（generator）"""
        if not self.internal_affairs:
            yield from []  # 空のgeneratorを返す
            return

        available_generals = [
            g for g in self.game_state.generals.values()
            if g.serving_daimyo_id == daimyo.id and g.is_available
        ]

        if not available_generals:
            return

        unassigned = [p for p in provinces if not p.governor_general_id]
        if not unassigned:
            return

        # 優先度でソート
        def priority(p):
            score = p.soldiers
            if p.has_castle:
                score += 1000
            for adj_id in p.adjacent_provinces:
                adj = self.game_state.get_province(adj_id)
                if adj and adj.owner_daimyo_id != daimyo.id:
                    score += 500
            return score

        unassigned.sort(key=priority, reverse=True)
        available_generals.sort(
            key=lambda g: g.war_skill + g.leadership + g.politics + g.intelligence,
            reverse=True
        )

        for i, province in enumerate(unassigned):
            if i >= len(available_generals):
                break
            if province.command_used_this_turn:
                continue

            general = available_generals[i]
            result = self.internal_affairs.assign_governor(province, general)
            if result["success"]:
                msg = f" 【{daimyo.clan_name}】{general.name}を{province.name}の守将に任命"
                self.turn_events.append(msg)
                yield ("message", msg)  # UIに即座に表示
                # AI将軍配置: 便宜上command_used_this_turnを設定
                # （この領地で他のコマンドを実行しないようにするため）
                # プレイヤーの将軍配置はコマンド扱いではないが、
                # AIは戦略的に将軍配置した領地を優先するため、この設計とする
                province.command_used_this_turn = True

    def _ai_decide_internal_action(self, province: Province, daimyo: Daimyo) -> Dict:
        """AI: 内政行動を決定"""
        # 忠誠度が低い場合は米配布
        if province.peasant_loyalty < 40 and province.rice >= config.GIVE_RICE_AMOUNT:
            return {"type": "give_rice"}

        # 開発レベルが低い場合は開墾
        if province.gold >= config.CULTIVATION_COST and province.development_level < 5:
            return {"type": "cultivate"}

        # 町レベルが低い場合は町開発
        if province.gold >= config.TOWN_DEVELOPMENT_COST and province.town_level < 5:
            return {"type": "develop_town"}

        # 治水レベルが低い場合は治水
        if province.gold >= config.FLOOD_CONTROL_COST and province.flood_control < 80:
            return {"type": "flood_control"}

        # 転送の判断
        transfer_action = self._ai_decide_transfer_action(province, daimyo)
        if transfer_action["type"] != "none":
            return transfer_action

        return {"type": "none"}

    def _ai_decide_transfer_action(self, province: Province, daimyo: Daimyo) -> Dict:
        """AI: 転送行動を決定"""
        # 隣接する自領地で敵に面している領地を探す
        transfer_targets = []
        for adj_id in province.adjacent_provinces:
            adj = self.game_state.get_province(adj_id)
            if not adj or adj.owner_daimyo_id != daimyo.id:
                continue

            # 転送先が敵に隣接しているか
            has_enemy = False
            for adj2_id in adj.adjacent_provinces:
                adj2 = self.game_state.get_province(adj2_id)
                if adj2 and adj2.owner_daimyo_id != daimyo.id:
                    has_enemy = True
                    break

            if has_enemy:
                priority = 0
                if adj.has_castle:
                    priority += 1000
                if adj.soldiers < 200:
                    priority += 500
                transfer_targets.append((adj, priority))

        if not transfer_targets:
            return {"type": "none"}

        transfer_targets.sort(key=lambda x: x[1], reverse=True)
        target = transfer_targets[0][0]

        # 兵士転送
        if target.soldiers < 300 and province.soldiers > 100:
            return {
                "type": "transfer_soldiers",
                "target_id": target.id,
                "amount": 60
            }

        # 金転送
        if target.gold < 500 and province.gold > 380:
            return {
                "type": "transfer_gold",
                "target_id": target.id,
                "amount": 300
            }

        # 米転送
        if province.rice > 500:
            return {
                "type": "transfer_rice",
                "target_id": target.id,
                "amount": 300
            }

        return {"type": "none"}

    def _ai_decide_military_action(self, province: Province, daimyo: Daimyo) -> Dict:
        """AI: 軍事行動を決定"""
        print(f"[DEBUG-決定チェック] {daimyo.clan_name}の{province.name}: 兵{province.soldiers}")

        # 攻撃可能な隣接敵領地があり、兵力が十分な場合は攻撃
        if province.soldiers >= 150:
            target_id = self._find_attack_target(province, daimyo.id)
            print(f"[DEBUG-決定チェック] {daimyo.clan_name}の{province.name}: 攻撃対象検索結果={target_id}")
            if target_id:
                target = self.game_state.get_province(target_id)
                attack_force = int(province.soldiers * 0.8)

                # デバッグログ: 決定時の情報を記録
                target_owner = self.game_state.get_daimyo(target.owner_daimyo_id)
                target_owner_name = target_owner.clan_name if target_owner else "無所属"
                print(f"[DEBUG-決定] {daimyo.clan_name}が{province.name}(兵{province.soldiers})から{target_owner_name}の{target.name}(兵{target.soldiers})への攻撃を決定（攻撃兵力{attack_force}）")

                return {
                    "type": "attack",
                    "target_id": target_id,
                    "attack_force": attack_force,
                    "general_id": province.governor_general_id
                }
        else:
            print(f"[DEBUG-決定チェック] {daimyo.clan_name}の{province.name}: 兵力不足（{province.soldiers} < 150）")

        # 徴兵が必要かチェック
        max_enemy = self._get_max_adjacent_enemy_soldiers(province, daimyo.id)
        if max_enemy > 0:
            required = int(max_enemy * 1.35)
            if (province.soldiers < required and
                province.peasants >= 100 and
                province.gold >= config.RECRUIT_COST_PER_SOLDIER * 100):
                print(f"[DEBUG-決定] {daimyo.clan_name}が{province.name}で徴兵を決定")
                return {"type": "recruit", "amount": 100}

        return {"type": "none"}

    def _find_attack_target(self, province: Province, daimyo_id: int) -> Optional[int]:
        """攻撃対象を探す"""
        daimyo = self.game_state.get_daimyo(daimyo_id)
        print(f"[DEBUG-攻撃対象検索] {daimyo.clan_name}の{province.name}から攻撃可能な隣接領地を検索中...")
        candidates = []

        for adj_id in province.adjacent_provinces:
            adj = self.game_state.get_province(adj_id)
            if not adj:
                continue

            adj_owner = self.game_state.get_daimyo(adj.owner_daimyo_id) if adj.owner_daimyo_id else None
            adj_owner_name = adj_owner.clan_name if adj_owner else "無所属"

            if adj.owner_daimyo_id == daimyo_id:
                print(f"  {adj.name}({adj_owner_name}): 自領地のためスキップ")
                continue

            # 外交関係をチェック
            if self.diplomacy_system and not self.diplomacy_system.can_attack(daimyo_id, adj.owner_daimyo_id):
                print(f"  {adj.name}({adj_owner_name}): 外交関係により攻撃不可")
                continue

            # 戦力比較
            required = adj.soldiers * 1.35
            if province.soldiers >= required:
                print(f"  {adj.name}({adj_owner_name}): 攻撃可能（兵{province.soldiers} >= {required:.0f}）")
                candidates.append((adj_id, adj.soldiers))
            else:
                print(f"  {adj.name}({adj_owner_name}): 兵力不足（兵{province.soldiers} < {required:.0f}）")

        if candidates:
            candidates.sort(key=lambda x: x[1])
            target = self.game_state.get_province(candidates[0][0])
            print(f"[DEBUG-攻撃対象検索] 攻撃対象決定: {target.name}")
            return candidates[0][0]

        print(f"[DEBUG-攻撃対象検索] 攻撃可能な対象なし")
        return None

    def _get_max_adjacent_enemy_soldiers(self, province: Province, daimyo_id: int) -> int:
        """隣接する敵領地の最大兵力を取得"""
        max_soldiers = 0

        for adj_id in province.adjacent_provinces:
            adj = self.game_state.get_province(adj_id)
            if not adj or adj.owner_daimyo_id == daimyo_id:
                continue

            if self.diplomacy_system and not self.diplomacy_system.can_attack(daimyo_id, adj.owner_daimyo_id):
                continue

            if adj.soldiers > max_soldiers:
                max_soldiers = adj.soldiers

        return max_soldiers

    def _execute_internal_command(self, province: Province, daimyo: Daimyo, action: Dict) -> Generator:
        """内政コマンドを即時実行（generator）"""
        action_type = action["type"]

        if action_type == "cultivate" and self.internal_affairs:
            result = self.internal_affairs.execute_cultivation(province)
            if result["success"]:
                msg = f" 【{daimyo.clan_name}】{province.name}で開墾（開発Lv→{province.development_level}）"
                self.turn_events.append(msg)
                yield ("message", msg)  # UIに即座に表示
                province.command_used_this_turn = True

        elif action_type == "develop_town" and self.internal_affairs:
            result = self.internal_affairs.execute_town_development(province)
            if result["success"]:
                msg = f" 【{daimyo.clan_name}】{province.name}で町開発（町Lv→{province.town_level}）"
                self.turn_events.append(msg)
                yield ("message", msg)  # UIに即座に表示
                province.command_used_this_turn = True

        elif action_type == "flood_control" and self.internal_affairs:
            result = self.internal_affairs.execute_flood_control(province)
            if result["success"]:
                msg = f" 【{daimyo.clan_name}】{province.name}で治水（治水→{province.flood_control}%）"
                self.turn_events.append(msg)
                yield ("message", msg)  # UIに即座に表示
                province.command_used_this_turn = True

        elif action_type == "give_rice" and self.internal_affairs:
            result = self.internal_affairs.execute_give_rice(province)
            if result["success"]:
                msg = f" 【{daimyo.clan_name}】{province.name}で米配布（忠誠度→{province.peasant_loyalty}）"
                self.turn_events.append(msg)
                yield ("message", msg)  # UIに即座に表示
                province.command_used_this_turn = True

        elif action_type == "transfer_soldiers" and self.transfer_system:
            target_id = action.get("target_id")
            amount = action.get("amount", 60)
            result = self.transfer_system.transfer_soldiers(province.id, target_id, amount)
            if result.success:
                self.turn_events.append(f"【{daimyo.clan_name}】{result.message}")
                province.command_used_this_turn = True

        elif action_type == "transfer_gold" and self.transfer_system:
            target_id = action.get("target_id")
            amount = action.get("amount", 300)
            result = self.transfer_system.transfer_gold(province.id, target_id, amount)
            if result.success:
                self.turn_events.append(f"【{daimyo.clan_name}】{result.message}")
                province.command_used_this_turn = True

        elif action_type == "transfer_rice" and self.transfer_system:
            target_id = action.get("target_id")
            amount = action.get("amount", 300)
            result = self.transfer_system.transfer_rice(province.id, target_id, amount)
            if result.success:
                self.turn_events.append(f"【{daimyo.clan_name}】{result.message}")
                province.command_used_this_turn = True

    def _execute_military_commands(self, daimyo: Daimyo, commands: List[Dict]) -> Generator:
        """軍事コマンドリストを順次実行"""
        from systems.combat import CombatSystem

        for cmd in commands:
            cmd_type = cmd["type"]
            province_id = cmd.get("province_id")
            province = self.game_state.get_province(province_id)

            if not province:
                continue

            if cmd_type == "recruit":
                # 徴兵は即時反映
                amount = cmd.get("amount", 100)
                if self.military_system:
                    result = self.military_system.recruit_soldiers(province, amount)
                    if result["success"]:
                        msg = f" 【{daimyo.clan_name}】【{province.name}】徴兵{amount}人"
                        yield ("message", msg)
                        self.turn_events.append(msg)

            elif cmd_type == "attack":
                # 攻撃: 計算→演出→適用→死亡判定→勝利判定
                target_id = cmd.get("target_id")
                attack_force = cmd.get("attack_force")
                general_id = cmd.get("general_id")

                target_province = self.game_state.get_province(target_id)
                if not target_province:
                    continue

                # デバッグログ: 実行時の情報を記録
                print(f"[DEBUG-実行] {daimyo.clan_name}の軍事コマンド実行: {province.name}(現在兵{province.soldiers})から{target_province.name}へ攻撃（攻撃兵力{attack_force}）")

                # 出陣ログ
                defender = self.game_state.get_daimyo(target_province.owner_daimyo_id)
                defender_name = defender.clan_name if defender else "無所属"
                msg = f" 【{daimyo.clan_name}】【{province.name}】{defender_name}の{target_province.name}へ出陣（兵力{attack_force}人）"
                yield ("message", msg)
                self.turn_events.append(msg)

                # 軍を作成
                if self.military_system:
                    result = self.military_system.create_attack_army(
                        province, target_province, attack_force, general_id
                    )
                    if not result["success"]:
                        # 攻撃失敗のログを追加
                        fail_msg = f"【{daimyo.clan_name}】{province.name}からの出陣失敗: {result.get('message', '不明')}（必要兵力{attack_force}、現在{province.soldiers}）"
                        self.turn_events.append(fail_msg)
                        print(f"[DEBUG] {fail_msg}")
                        continue

                    army = result["army"]

                    # 戦闘計算
                    combat_system = CombatSystem(self.game_state)
                    battle_result = combat_system.resolve_battle(army, target_province)

                    # 戦闘データを作成
                    attacker_general = self.game_state.get_general(army.general_id) if army.general_id else None
                    defender_general = self.game_state.get_general(target_province.governor_general_id) if target_province.governor_general_id else None

                    battle_data = {
                        "attacker_name": daimyo.clan_name,
                        "defender_name": defender_name,
                        "attacker_province": province.name,
                        "defender_province": target_province.name,
                        "attacker_troops": army.total_troops,
                        "defender_troops": target_province.soldiers,
                        "attacker_general": attacker_general.name if attacker_general else None,
                        "defender_general": defender_general.name if defender_general else None,
                        "attacker_general_obj": attacker_general,
                        "defender_general_obj": defender_general,
                        "attacker_daimyo_obj": daimyo,
                        "defender_daimyo_obj": defender,
                        "attacker_general_id": army.general_id,
                        "defender_general_id": target_province.governor_general_id,
                        "attacker_daimyo_id": daimyo.id,
                        "defender_daimyo_id": target_province.owner_daimyo_id,
                        "result": battle_result,
                        "army": army,
                        "target_province_id": target_id,
                        "origin_province_id": province.id,
                        "combat_system": combat_system
                    }

                    # 戦闘演出（UIへ制御を渡す）
                    yield ("battle_animation", battle_data)

                    # 戦闘結果を適用
                    defeated_daimyo_id = combat_system.apply_battle_result(
                        battle_result, army, target_province
                    )

                    # 死亡判定
                    if defeated_daimyo_id:
                        defeated_daimyo = self.game_state.get_daimyo(defeated_daimyo_id)
                        if defeated_daimyo:
                            death_data = {
                                "type": "daimyo",
                                "id": defeated_daimyo.id,
                                "daimyo_id": defeated_daimyo.id,  # UI互換性のため
                                "name": defeated_daimyo.name,
                                "daimyo_name": defeated_daimyo.name,  # UI互換性のため
                                "clan_name": defeated_daimyo.clan_name,
                                "age": defeated_daimyo.age,
                                "is_player": defeated_daimyo.is_player,
                                "cause": "territory_loss"  # 全領地喪失による滅亡
                            }

                            yield ("death_animation", death_data)

                            if defeated_daimyo.is_player:
                                yield ("game_over", death_data)
                                return {"game_over": True}

                    # 勝利判定
                    winner = self.game_state.check_victory_conditions()
                    if winner:
                        player_daimyo = self.game_state.get_player_daimyo()
                        if player_daimyo and winner == player_daimyo.id:
                            yield ("victory", None)
                            return {"winner": winner}

        return None

    def _turn_end(self):
        """ターン終了処理"""
        # 統計を更新
        self.game_state.update_all_statistics()

        # 20ターンごとにコマンド統計を表示
        if self.game_state.current_turn > 0 and self.game_state.current_turn % 20 == 0:
            stats_report = self.game_state.get_command_statistics_report()
            self.turn_events.extend(stats_report)

    def get_turn_events(self) -> List[str]:
        """ターンイベントログを取得"""
        return self.turn_events.copy()

    # ========================================
    # プレイヤー用API
    # ========================================

    def can_use_command(self, province: Province) -> bool:
        """コマンドが使用可能か（1領地1コマンド）"""
        return not province.command_used_this_turn

    def mark_command_used(self, province: Province):
        """コマンド使用済みにマーク"""
        province.command_used_this_turn = True

    # ========================================
    # 軍報システム用ヘルパーメソッド
    # ========================================

    def _get_owner_name(self, province: Province) -> str:
        """領地所有者の表示名を取得"""
        if not province.owner_daimyo_id:
            return "無所属"
        owner = self.game_state.get_daimyo(province.owner_daimyo_id)
        return owner.clan_name if owner else "不明"

    def _format_loyalty_warning(self, province: Province, change: int) -> str:
        """治安悪化メッセージをフォーマット"""
        owner_name = self._get_owner_name(province)

        if province.peasant_loyalty <= 30:
            return f" 【{owner_name}】【{province.name}】[警告] 反乱の危険（忠誠度{province.peasant_loyalty}）"
        else:
            return f" 【{owner_name}】【{province.name}】[治安] 治安悪化（忠誠度{change:+d}）"

    def _get_event_icon(self, event_type: str) -> str:
        """イベントタイプに応じたアイコンを取得"""
        icons = {
            "natural_disaster": "[災害]",  # 自然災害
            "economic": "[経済]",          # 経済
            "social": "[社会]",            # 社会
            "military": "[軍事]",          # 軍事
            "diplomatic": "[外交]"         # 外交
        }
        return icons.get(event_type, "[情報]")  # デフォルトは一般情報
