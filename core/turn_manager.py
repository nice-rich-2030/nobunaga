"""
TurnManager - ターン進行管理
11フェーズのターンシステムを実装
"""
from typing import List, Dict, Any
import config
from models.province import Province
from models.daimyo import Daimyo


class TurnManager:
    """ターン進行を管理するクラス"""

    def __init__(self, game_state):
        self.game_state = game_state
        self.command_queue: List[Dict[str, Any]] = []
        self.turn_events: List[str] = []  # ターン中に発生したイベントのログ
        self.pending_battles: List[Dict[str, Any]] = []  # 保留中の戦闘
        self.pending_event_choices: List[Dict[str, Any]] = []  # 保留中のイベント選択
        self.battle_results: List[Dict[str, Any]] = []  # ターン中の戦闘結果（演出用）
        self.ai_system = None  # AIシステム（main.pyから設定）
        self.diplomacy_system = None  # 外交システム（main.pyから設定）
        self.event_system = None  # イベントシステム（main.pyから設定）

    def execute_turn(self):
        """1ターン全体を実行（11フェーズ）"""
        self.turn_events.clear()
        self.battle_results.clear()

        # フェーズ1: ターン開始
        self._phase_1_turn_start()

        # フェーズ2: 収入と生産
        self._phase_2_income_production()

        # フェーズ3: 維持費
        self._phase_3_upkeep()

        # フェーズ4: ランダムイベント
        self._phase_4_random_events()

        # フェーズ5: プレイヤーコマンドフェーズ（main.pyで処理）
        # フェーズ6: AIコマンドフェーズ
        self._phase_6_ai_commands()

        # フェーズ7: コマンド解決
        self._phase_7_command_resolution()

        # フェーズ8: 戦闘解決
        self._phase_8_battle_resolution()

        # フェーズ9: 外交更新
        self._phase_9_diplomacy_update()

        # フェーズ10: 勝利判定
        winner = self._phase_10_victory_check()

        # フェーズ11: ターン終了
        self._phase_11_turn_end()

        return winner

    def _phase_1_turn_start(self):
        """フェーズ1: ターン開始処理"""
        self.turn_events.append(f"=== ターン {self.game_state.current_turn + 1} 開始 ===")

        # ターンを進める
        self.game_state.advance_turn()

        # 新年の場合、加齢処理
        if self.game_state.current_season == config.SEASON_SPRING:
            self._age_characters()

        # 領地のコマンドフラグをリセット
        for province in self.game_state.provinces.values():
            province.reset_command_flag()

    def _age_characters(self):
        """キャラクターを1年加齢させる"""
        # 大名を加齢
        for daimyo in self.game_state.daimyo.values():
            # 既に死亡している場合はスキップ
            if not daimyo.is_alive:
                continue

            old_age = daimyo.age
            old_health = daimyo.health
            daimyo.age_one_year()

            # 今年死亡した場合のみメッセージを表示
            if old_health > 0 and not daimyo.is_alive:
                self.turn_events.append(f"{daimyo.clan_name} {daimyo.name}が死去しました（享年{old_age}）")

        # 武将を加齢
        for general in self.game_state.generals.values():
            # 既に死亡している場合はスキップ
            if not general.is_alive():
                continue

            old_health = general.health
            general.age_one_year()

            # 今年死亡した場合のみメッセージを表示
            if old_health > 0 and not general.is_alive():
                self.turn_events.append(f"武将 {general.name}が死去しました")

    def _phase_2_income_production(self):
        """フェーズ2: 収入と生産"""
        # プレイヤー大名の収入サマリー
        player_daimyo = None
        total_rice = 0
        total_gold = 0

        for daimyo in self.game_state.daimyo.values():
            if daimyo.is_player:
                player_daimyo = daimyo
                break

        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id is None:
                continue

            # 米生産
            rice_produced = province.calculate_rice_production()
            province.add_rice(rice_produced)

            # 税収
            gold_income = province.calculate_tax_income()
            province.add_gold(gold_income)

            # プレイヤーの収入を集計
            if player_daimyo and province.owner_daimyo_id == player_daimyo.id:
                total_rice += rice_produced
                total_gold += gold_income

            # 忠誠度の自然減衰
            loyalty_change = config.LOYALTY_DECAY_RATE
            # 税率が高い場合、追加ペナルティ
            if province.tax_rate > 50:
                loyalty_change += int((province.tax_rate - 50) * config.LOYALTY_TAX_PENALTY)
            province.update_loyalty(loyalty_change)

        # プレイヤーの収入を表示
        if player_daimyo and (total_rice > 0 or total_gold > 0):
            self.turn_events.append(f"【収入】米+{total_rice}、金+{total_gold}")

    def _phase_3_upkeep(self):
        """フェーズ3: 維持費"""
        # プレイヤー大名の維持費サマリー
        player_daimyo = None
        total_rice_consumed = 0

        for daimyo in self.game_state.daimyo.values():
            if daimyo.is_player:
                player_daimyo = daimyo
                break

        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id is None:
                continue

            # 兵士の米消費
            rice_needed = province.calculate_soldier_rice_consumption()
            province.add_rice(-rice_needed)

            # プレイヤーの維持費を集計
            if player_daimyo and province.owner_daimyo_id == player_daimyo.id:
                total_rice_consumed += rice_needed

            # 米不足の場合、士気低下
            if province.rice < 0:
                province.rice = 0
                province.update_morale(config.MORALE_LOW_RICE_PENALTY)
                self.turn_events.append(f"【警告】{province.name}: 米不足により士気低下")
            else:
                # 士気の自然減衰
                province.update_morale(config.MORALE_DECAY_RATE)

        # プレイヤーの維持費を表示
        if player_daimyo and total_rice_consumed > 0:
            self.turn_events.append(f"【維持費】米-{total_rice_consumed}（兵士の消費）")

    def _phase_4_random_events(self):
        """フェーズ4: ランダムイベント"""
        if not self.event_system:
            return

        current_season = self.game_state.get_season_name()
        triggered_events = self.event_system.check_events_for_turn(current_season)

        for event, province in triggered_events:
            # 選択肢があるイベントかつプレイヤーの領地の場合
            if event.has_choices() and province.owner_daimyo_id == 1:
                # UIで選択を待つ（pending_event_choicesに追加）
                self.pending_event_choices.append({
                    "event": event,
                    "province": province
                })
                # 通知メッセージのみ追加
                self.turn_events.append(
                    f"【{event.name}】{province.name}でイベントが発生しました（選択待ち）"
                )
            else:
                # 自動処理（AIまたは選択肢なし）
                # AIの場合はランダムに選択
                choice_id = None
                if event.has_choices() and province.owner_daimyo_id != 1:
                    import random
                    choice = random.choice(event.choices)
                    choice_id = choice.choice_id

                self.event_system.apply_event_effect(event, province, choice_id)

                daimyo = self.game_state.get_daimyo(province.owner_daimyo_id)
                owner_name = daimyo.clan_name if daimyo else "無所属"

                # イベント説明文のフォーマット
                description = event.description.format(province_name=province.name)

                self.turn_events.append(
                    f"【{event.name}】{owner_name}の{province.name}: {description}"
                )

    def _phase_7_command_resolution(self):
        """フェーズ7: コマンド解決"""
        # コマンドキューを実行
        for command in self.command_queue:
            self._execute_command(command)

        # キューをクリア
        self.command_queue.clear()

    def _execute_command(self, command: Dict[str, Any]):
        """個別コマンドを実行"""
        command_type = command.get("type")
        province_id = command.get("province_id")

        province = self.game_state.get_province(province_id)
        if not province:
            return

        if command_type == "cultivate":
            self._execute_cultivate(province)
        elif command_type == "develop_town":
            self._execute_develop_town(province)
        elif command_type == "flood_control":
            self._execute_flood_control(province)
        elif command_type == "give_rice":
            self._execute_give_rice(province)
        elif command_type == "adjust_tax":
            new_rate = command.get("new_rate", 50)
            self._execute_adjust_tax(province, new_rate)
        # 他のコマンドは将来実装

    def _execute_cultivate(self, province: Province):
        """開墾コマンド実行"""
        if not province.can_afford(gold=config.CULTIVATION_COST):
            self.turn_events.append(f"{province.name}: 開墾に失敗（金不足）")
            return

        province.spend(gold=config.CULTIVATION_COST)
        province.development_level = min(10, province.development_level + 1)
        province.update_loyalty(config.CULTIVATION_LOYALTY_PENALTY)
        self.turn_events.append(f"{province.name}: 開墾を実施（開発Lv {province.development_level}）")

    def _execute_develop_town(self, province: Province):
        """町開発コマンド実行"""
        if not province.can_afford(gold=config.TOWN_DEVELOPMENT_COST):
            self.turn_events.append(f"{province.name}: 町開発に失敗（金不足）")
            return

        province.spend(gold=config.TOWN_DEVELOPMENT_COST)
        province.town_level = min(10, province.town_level + 1)
        self.turn_events.append(f"{province.name}: 町開発を実施（町Lv {province.town_level}）")

    def _execute_flood_control(self, province: Province):
        """治水コマンド実行"""
        if not province.can_afford(gold=config.FLOOD_CONTROL_COST):
            self.turn_events.append(f"{province.name}: 治水に失敗（金不足）")
            return

        province.spend(gold=config.FLOOD_CONTROL_COST)
        province.flood_control = min(100, province.flood_control + config.FLOOD_CONTROL_BOOST)
        self.turn_events.append(f"{province.name}: 治水を実施（{province.flood_control}%）")

    def _execute_give_rice(self, province: Province):
        """米配布コマンド実行"""
        if not province.can_afford(rice=config.GIVE_RICE_AMOUNT):
            self.turn_events.append(f"{province.name}: 米配布に失敗（米不足）")
            return

        province.spend(rice=config.GIVE_RICE_AMOUNT)
        province.update_loyalty(config.GIVE_RICE_LOYALTY_BOOST)
        self.turn_events.append(f"{province.name}: 米配布を実施（忠誠度 {province.peasant_loyalty}）")

    def _execute_adjust_tax(self, province: Province, new_rate: int):
        """税率調整コマンド実行"""
        old_rate = province.tax_rate
        province.tax_rate = max(config.TAX_RATE_MIN, min(config.TAX_RATE_MAX, new_rate))
        self.turn_events.append(f"{province.name}: 税率変更 {old_rate}% → {province.tax_rate}%")

    def _phase_8_battle_resolution(self):
        """フェーズ8: 戦闘解決"""
        if not self.pending_battles:
            return

        # combat_systemはmain.pyから設定される想定
        from systems.combat import CombatSystem
        combat_system = CombatSystem(self.game_state)

        # 戦闘計算は順次行うが、結果適用は演出後に行う
        # ただし、同一ターン内の戦闘順序を考慮する必要がある
        for battle in self.pending_battles:
            army = battle["army"]
            target_province = self.game_state.get_province(battle["target_province_id"])
            origin_province = self.game_state.get_province(battle["origin_province_id"])

            if not target_province or not origin_province:
                continue

            # 【注意】この時点では戦闘結果は未適用なので、
            # 現在の領地状態で計算される（これが正しい動作）

            # 攻撃側と防御側の大名情報を取得（現在の状態で）
            attacker_daimyo = self.game_state.get_daimyo(army.daimyo_id)
            defender_daimyo = self.game_state.get_daimyo(target_province.owner_daimyo_id)

            attacker_name = attacker_daimyo.clan_name if attacker_daimyo else "無所属"
            defender_name = defender_daimyo.clan_name if defender_daimyo else "無所属"

            # 武将情報を取得
            attacker_general = None
            attacker_general_name = None
            if army.general_id:
                attacker_general = self.game_state.get_general(army.general_id)
                if attacker_general:
                    attacker_general_name = attacker_general.name

            defender_general = None
            defender_general_name = None
            if target_province.governor_general_id:
                defender_general = self.game_state.get_general(target_province.governor_general_id)
                if defender_general:
                    defender_general_name = defender_general.name

            # 戦闘前の兵力を記録
            initial_attacker_troops = army.total_troops
            initial_defender_troops = target_province.soldiers

            # 戦闘を解決（結果を計算のみ、適用はしない）
            result = combat_system.resolve_battle(army, target_province)

            # この戦闘のメッセージログを作成
            battle_messages = []
            battle_messages.append(f"\n=== 【戦闘】{attacker_name}軍が{defender_name}の{target_province.name}を攻撃 ===")
            battle_messages.append(f"攻撃側: {origin_province.name}から出陣 兵力{initial_attacker_troops}人")
            battle_messages.append(f"防御側: {target_province.name} 守備兵{initial_defender_troops}人")
            for log_entry in result.battle_log:
                battle_messages.append(log_entry)

            # 戦闘結果を演出用に保存（結果の適用は演出後）
            self.battle_results.append({
                "attacker_name": attacker_name,
                "defender_name": defender_name,
                "attacker_province": origin_province.name,
                "defender_province": target_province.name,
                "attacker_troops": initial_attacker_troops,
                "defender_troops": initial_defender_troops,
                "attacker_general": attacker_general_name,
                "defender_general": defender_general_name,
                "attacker_general_obj": attacker_general,  # 将軍オブジェクト
                "defender_general_obj": defender_general,  # 将軍オブジェクト
                "result": result,
                "messages": battle_messages,
                # 結果適用のために必要なデータ
                "army": army,
                "target_province_id": target_province.id,
                "origin_province_id": origin_province.id,
                "combat_system": combat_system
            })

        # 戦闘キューをクリア
        self.pending_battles.clear()

    def queue_battle(self, battle_data: dict):
        """戦闘をキューに追加"""
        self.pending_battles.append(battle_data)

    def _phase_6_ai_commands(self):
        """フェーズ6: AIコマンドフェーズ"""
        if not self.ai_system:
            return

        # 各AI大名のターンを実行
        for daimyo in self.game_state.daimyo.values():
            if not daimyo.is_player and daimyo.is_alive:
                events = self.ai_system.execute_ai_turn(daimyo.id)
                self.turn_events.extend(events)

                # AI外交
                diplomacy_events = self.ai_system.execute_ai_diplomacy(daimyo.id)
                self.turn_events.extend(diplomacy_events)

    def _phase_9_diplomacy_update(self):
        """フェーズ9: 外交更新"""
        if not self.diplomacy_system:
            return

        # 条約の期限切れチェック
        events = self.diplomacy_system.update_treaties()
        self.turn_events.extend(events)

    def _phase_10_victory_check(self):
        """フェーズ10: 勝利判定"""
        return self.game_state.check_victory_conditions()

    def _phase_11_turn_end(self):
        """フェーズ11: ターン終了処理"""
        # 統計を更新
        self.game_state.update_all_statistics()

        # 20ターンごとにコマンド統計を表示
        if self.game_state.current_turn > 0 and self.game_state.current_turn % 20 == 0:
            stats_report = self.game_state.get_command_statistics_report()
            self.turn_events.extend(stats_report)

    def queue_command(self, command: Dict[str, Any]):
        """コマンドをキューに追加"""
        self.command_queue.append(command)

    def get_turn_events(self) -> List[str]:
        """ターンイベントログを取得"""
        return self.turn_events.copy()
