"""
AIシステム - コンピュータ制御の大名の意思決定
"""
import random
import config
from models.diplomacy import RelationType


class AISystem:
    """AIシステム"""

    def __init__(self, game_state, internal_affairs, military_system, diplomacy_system, transfer_system=None):
        self.game_state = game_state
        self.internal_affairs = internal_affairs
        self.military_system = military_system
        self.diplomacy_system = diplomacy_system
        self.transfer_system = transfer_system
        self.turn_manager = None  # TurnManagerへの参照（main.pyから設定）

    def execute_ai_turn(self, daimyo_id):
        """AI大名のターンを実行"""
        daimyo = self.game_state.get_daimyo(daimyo_id)
        if not daimyo or not daimyo.is_alive or daimyo.is_player:
            return []

        events = []

        # AI大名の領地を取得
        ai_provinces = [p for p in self.game_state.provinces.values() if p.owner_daimyo_id == daimyo_id]

        if not ai_provinces:
            return events

        # ターン開始時に将軍を配置
        general_events = self._assign_generals_to_provinces(daimyo_id, ai_provinces)
        events.extend(general_events)

        # 領地を行動順序でソート（後方→国境の順）
        # 転送を即時実行するため、後方から先に処理
        sorted_provinces = self._sort_provinces_by_action_order(ai_provinces, daimyo_id)

        # 各領地でコマンドを実行
        for province in sorted_provinces:
            if province.command_used_this_turn:
                continue

            # 行動カテゴリを決定（内政/軍事/転送）
            category = self._decide_action_category(province, daimyo)

            # カテゴリ内での具体的行動を決定
            action = self._decide_specific_action(province, daimyo, category)

            if action["type"] == "cultivate":
                result = self.internal_affairs.execute_cultivation(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で開墾（開発Lv→{province.development_level}）")
                    self.game_state.record_command(daimyo_id, province.id, "cultivate")

            elif action["type"] == "develop_town":
                result = self.internal_affairs.execute_town_development(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で町開発（町Lv→{province.town_level}）")
                    self.game_state.record_command(daimyo_id, province.id, "develop_town")

            elif action["type"] == "flood_control":
                result = self.internal_affairs.execute_flood_control(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で治水（治水→{province.flood_control}%）")
                    self.game_state.record_command(daimyo_id, province.id, "flood_control")

            elif action["type"] == "give_rice":
                result = self.internal_affairs.execute_give_rice(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で米配布（忠誠度→{province.peasant_loyalty}）")
                    self.game_state.record_command(daimyo_id, province.id, "give_rice")

            elif action["type"] == "recruit":
                result = self.military_system.recruit_soldiers(province, 100)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で徴兵100人（兵力→{province.soldiers}人）")
                    self.game_state.record_command(daimyo_id, province.id, "recruit")

            elif action["type"] == "attack":
                target_province_id = action["target"]
                target_province = self.game_state.get_province(target_province_id)
                if target_province:
                    attack_force = int(province.soldiers * 0.8)
                    result = self.military_system.create_attack_army(
                        province,
                        target_province,
                        attack_force,
                        None
                    )
                    if result["success"] and self.turn_manager:
                        army = result["army"]
                        # 戦闘をキューに追加
                        self.turn_manager.queue_battle({
                            "army": army,
                            "target_province_id": target_province_id,
                            "origin_province_id": province.id
                        })
                        defender = self.game_state.get_daimyo(target_province.owner_daimyo_id)
                        defender_name = defender.clan_name if defender else "無所属"
                        events.append(f"【{daimyo.clan_name}】{province.name}から{defender_name}の{target_province.name}へ出陣（兵力{attack_force}人）")
                        self.game_state.record_command(daimyo_id, province.id, "attack")

            elif action["type"] == "transfer":
                # 転送コマンドを実行
                target_province_id = action["target"]
                resource_type = action["resource"]
                amount = action["amount"]
                target_province = self.game_state.get_province(target_province_id)

                # デバッグログ
                debug = self.game_state.get_player_daimyo() is None
                if debug:
                    print(f"[TRANSFER EXECUTE] {daimyo.clan_name} {province.name} → {target_province.name if target_province else 'None'}")
                    print(f"[TRANSFER EXECUTE]   resource={resource_type}, amount={amount}")
                    print(f"[TRANSFER EXECUTE]   転送元兵力={province.soldiers}")
                    if target_province:
                        print(f"[TRANSFER EXECUTE]   転送先兵力={target_province.soldiers}")

                if target_province and self.transfer_system:
                    # resource_typeに応じて適切なメソッドを呼び出す
                    if resource_type == "soldiers":
                        result = self.transfer_system.transfer_soldiers(province.id, target_province.id, amount)
                    elif resource_type == "gold":
                        result = self.transfer_system.transfer_gold(province.id, target_province.id, amount)
                    elif resource_type == "rice":
                        result = self.transfer_system.transfer_rice(province.id, target_province.id, amount)
                    else:
                        if debug:
                            print(f"[TRANSFER EXECUTE]   ✗ 不明なリソースタイプ")
                        continue

                    if debug:
                        print(f"[TRANSFER EXECUTE]   result.success={result.success}")
                        if not result.success:
                            print(f"[TRANSFER EXECUTE]   ✗ 失敗理由: {result.message}")
                        else:
                            print(f"[TRANSFER EXECUTE]   ✓ 成功: {result.message}")

                    if result.success:
                        events.append(f"【{daimyo.clan_name}】{result.message}")
                        # コマンド実行統計を記録
                        if resource_type == "soldiers":
                            self.game_state.record_command(daimyo_id, province.id, "transfer_soldiers")
                        elif resource_type == "gold":
                            self.game_state.record_command(daimyo_id, province.id, "transfer_gold")
                        elif resource_type == "rice":
                            self.game_state.record_command(daimyo_id, province.id, "transfer_rice")
                else:
                    if debug:
                        print(f"[TRANSFER EXECUTE]   ✗ target_province={target_province is not None}, transfer_system={self.transfer_system is not None}")

        return events

    def _sort_provinces_by_action_order(self, provinces, daimyo_id):
        """領地を行動順序でソート（後方→国境の順）"""
        def action_priority(province):
            # 敵に隣接していない領地ほど優先度が高い（先に行動）
            has_enemy = self._has_enemy_neighbor(province, daimyo_id)
            if has_enemy:
                return 1  # 国境は後回し
            else:
                return 0  # 後方を先に

        return sorted(provinces, key=action_priority)

    def _decide_action_category(self, province, daimyo):
        """行動カテゴリを決定（内政/軍事/転送）"""

        # 緊急時は優先処理（ランダムを無視）
        if province.peasant_loyalty < 40 and province.rice >= config.GIVE_RICE_AMOUNT:
            return "internal"  # 一揆防止最優先

        # 隣接敵領地の確認
        has_enemy_neighbor = self._has_enemy_neighbor(province, daimyo.id)

        # 状況に応じた重み付け
        weights = {"internal": 1.0, "military": 1.0, "transfer": 1.0}

        # 国境の領地は軍事重視
        if has_enemy_neighbor:
            weights["military"] = 2.0
            weights["transfer"] = 0.3  # 国境では転送出しにくい
        else:
            # 後方の領地は転送重視
            weights["transfer"] = 2.0
            weights["military"] = 0.5  # 後方では攻撃しにくい

        # 兵力状況
        if province.soldiers >= 200:
            weights["military"] += 1.0
        elif province.soldiers < 100:
            weights["internal"] += 1.0  # 徴兵のため

        # 重み付きランダム選択
        total = sum(weights.values())
        rand = random.random() * total

        cumulative = 0
        for category, weight in weights.items():
            cumulative += weight
            if rand < cumulative:
                # デバッグログ
                if self.game_state.get_player_daimyo() is None:  # 全AI操作モード
                    print(f"[AI DEBUG] {daimyo.clan_name} {province.name}: カテゴリ={category} (重み={weights})")
                return category

        return "internal"

    def _decide_specific_action(self, province, daimyo, category):
        """カテゴリ内での具体的行動を決定"""

        if category == "internal":
            return self._decide_internal_action(province, daimyo)
        elif category == "military":
            return self._decide_military_action(province, daimyo)
        elif category == "transfer":
            return self._decide_transfer_action(province, daimyo)

        return {"type": "none"}

    def _decide_internal_action(self, province, daimyo):
        """内政行動を決定"""

        # 1. 忠誠度が低い場合は米配布
        if province.peasant_loyalty < 40 and province.rice >= config.GIVE_RICE_AMOUNT:
            return {"type": "give_rice"}

        # 2. 金があり、開発レベルが低い場合は開墾
        if province.gold >= config.CULTIVATION_COST and province.development_level < 5:
            return {"type": "cultivate"}

        # 3. 金があり、町レベルが低い場合は町開発
        if province.gold >= config.TOWN_DEVELOPMENT_COST and province.town_level < 5:
            return {"type": "develop_town"}

        # 4. 治水レベルが低い場合は治水
        if province.gold >= config.FLOOD_CONTROL_COST and province.flood_control < 80:
            return {"type": "flood_control"}

        # 5. 兵士が少なく、農民がいる場合は徴兵
        if province.soldiers < 300 and province.peasants >= 100 and province.gold >= config.RECRUIT_COST_PER_SOLDIER * 100:
            return {"type": "recruit"}

        return {"type": "none"}

    def _decide_military_action(self, province, daimyo):
        """軍事行動を決定"""

        # 1. 攻撃可能な隣接敵領地があり、兵力が十分な場合は攻撃
        if province.soldiers >= 150:
            target = self._find_attack_target(province, daimyo.id)
            if target:
                return {"type": "attack", "target": target}

        # 2. 兵士が少なく、農民がいる場合は徴兵
        if province.soldiers < 300 and province.peasants >= 100 and province.gold >= config.RECRUIT_COST_PER_SOLDIER * 100:
            return {"type": "recruit"}

        return {"type": "none"}

    def _decide_transfer_action(self, province, daimyo):
        """転送コマンドの具体的内容を決定"""

        # デバッグログ
        debug = self.game_state.get_player_daimyo() is None

        # 転送先候補を探す（隣接している敵に隣接している自領地）
        transfer_targets = []
        for other_province in self.game_state.provinces.values():
            if other_province.owner_daimyo_id != daimyo.id:
                continue

            if other_province.id == province.id:
                continue

            # 【重要】隣接チェック - TransferSystemの制約に従う
            if other_province.id not in province.adjacent_provinces:
                continue

            # 敵に隣接しているか
            if self._has_enemy_neighbor(other_province, daimyo.id):
                # 優先度を計算
                priority = 0
                if other_province.has_castle:
                    priority += 1000
                if other_province.soldiers < 200:
                    priority += 500
                if other_province.gold < 500:
                    priority += 300

                transfer_targets.append((other_province, priority))

        if debug:
            print(f"[TRANSFER DEBUG] {daimyo.clan_name} {province.name}: 転送先候補={len(transfer_targets)}件 (隣接のみ)")

        if not transfer_targets:
            if debug:
                print(f"[TRANSFER DEBUG] → 転送先なし（国境領地なし）")
            return {"type": "none"}

        # 最優先の転送先を選択
        transfer_targets.sort(key=lambda x: x[1], reverse=True)
        target = transfer_targets[0][0]

        if debug:
            print(f"[TRANSFER DEBUG] → 転送先={target.name} (兵{target.soldiers}, 金{target.gold})")
            print(f"[TRANSFER DEBUG] → 転送元リソース: 兵{province.soldiers}, 金{province.gold}, 米{province.rice}")

        # 転送可能な資源の候補リストを作成
        transfer_options = []

        # 兵士転送の条件チェック
        if target.soldiers < 300 and province.soldiers > 100:
            transfer_options.append({
                "resource": "soldiers",
                "amount": 60,
                "weight": 3.0  # 最重要（軍事力）
            })

        # 金転送の条件チェック
        if target.gold < 500 and province.gold > 380:
            transfer_options.append({
                "resource": "gold",
                "amount": 300,
                "weight": 1 # 重要（経済・徴兵）
            })

        # 米転送の条件チェック
        if province.rice > 500:
            transfer_options.append({
                "resource": "rice",
                "amount": 300,
                "weight": 2 # 基本（忠誠度）
            })

        # 候補がない場合
        if not transfer_options:
            if debug:
                print(f"[TRANSFER DEBUG] → 転送条件を満たさず")
            return {"type": "none"}

        # 重み付きランダムで資源を選択
        if debug:
            print(f"[TRANSFER DEBUG] → 転送候補: {[opt['resource'] for opt in transfer_options]}")

        choices = [opt for opt in transfer_options]
        weights = [opt["weight"] for opt in transfer_options]
        selected_option = random.choices(choices, weights=weights, k=1)[0]

        if debug:
            print(f"[TRANSFER DEBUG] → {selected_option['resource']}転送決定 (weight={selected_option['weight']})")

        return {
            "type": "transfer",
            "target": target.id,
            "resource": selected_option["resource"],
            "amount": selected_option["amount"]
        }

    def _has_enemy_neighbor(self, province, daimyo_id):
        """領地が敵に隣接しているかチェック"""
        debug = self.game_state.get_player_daimyo() is None
        if debug:
            daimyo = self.game_state.get_daimyo(daimyo_id)
            daimyo_name = daimyo.clan_name if daimyo else "Unknown"
            print(f"[NEIGHBOR DEBUG] Checking {province.name} (owner_id={province.owner_daimyo_id}, check_id={daimyo_id}, clan={daimyo_name})")

        for adj_id in province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
            if adj_province:
                adj_daimyo = self.game_state.get_daimyo(adj_province.owner_daimyo_id) if adj_province.owner_daimyo_id else None
                adj_name = adj_daimyo.clan_name if adj_daimyo else "無所属"
                is_enemy = adj_province.owner_daimyo_id != daimyo_id
                if debug:
                    print(f"[NEIGHBOR DEBUG]   → {adj_province.name}: owner_id={adj_province.owner_daimyo_id} ({adj_name}), is_enemy={is_enemy}")
                if is_enemy:
                    if debug:
                        print(f"[NEIGHBOR DEBUG]   ✓ Enemy found! Returning True")
                    return True

        if debug:
            print(f"[NEIGHBOR DEBUG]   ✗ No enemies found. Returning False")
        return False


    def _find_attack_target(self, province, daimyo_id):
        """攻撃対象を見つける"""
        candidates = []

        for adj_id in province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
            if not adj_province:
                continue

            # 自分の領地はスキップ
            if adj_province.owner_daimyo_id == daimyo_id:
                continue

            # 外交関係をチェック
            if not self.diplomacy_system.can_attack(daimyo_id, adj_province.owner_daimyo_id):
                continue

            # 戦力比較（守備側が有利なため、攻撃側は十分な兵力が必要）
            attack_force = int(province.soldiers * 0.8)  # 出陣できる兵力（80%）
            defender_force = adj_province.soldiers

            # 守備側の防御ボーナスを考慮した必要兵力比率
            defense_bonus = adj_province.get_defense_bonus()

            # 基本的に攻撃側は守備側の1.5倍必要
            # さらに防御ボーナスに応じて必要兵力が増加
            # 例: 防御1.5倍の山岳 → 1.5 * 1.5 = 2.25倍の兵力が必要
            required_ratio = 1.5 * defense_bonus

            # 攻撃側の兵力が必要比率以上なら攻撃を検討
            if attack_force >= defender_force * required_ratio:
                candidates.append((adj_id, adj_province.soldiers))

        # 最も守備兵力が少ない領地を選択
        if candidates:
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

        return None

    def execute_ai_diplomacy(self, daimyo_id):
        """AI大名の外交行動を実行"""
        daimyo = self.game_state.get_daimyo(daimyo_id)
        if not daimyo or not daimyo.is_alive or daimyo.is_player:
            return []

        events = []

        # 外交行動は確率的に実行（毎ターンではない）
        if random.random() > 0.3:  # 30%の確率で外交行動
            return events

        # 他の大名との関係を評価
        relations = self.diplomacy_system.get_all_relations(daimyo_id)

        for rel_info in relations:
            other_daimyo = rel_info["daimyo"]
            relation = rel_info["relation"]

            # 関係値が非常に低く、まだ戦争していない場合は宣戦布告を検討
            if relation.relation_value < -30 and relation.relation_type != RelationType.WAR:
                if random.random() < 0.5:  # 50%の確率
                    result = self.diplomacy_system.declare_war(daimyo_id, other_daimyo.id)
                    if result["success"]:
                        events.append(f"【外交】{daimyo.clan_name}が{other_daimyo.clan_name}に宣戦布告！")
                        break

            # 関係値が良好で、まだ条約がない場合は不可侵条約を提案
            elif relation.relation_value >= config.NON_AGGRESSION_RELATION_THRESHOLD and \
                 relation.relation_type == RelationType.NEUTRAL:
                if random.random() < 0.3:  # 30%の確率
                    result = self.diplomacy_system.propose_non_aggression(daimyo_id, other_daimyo.id)
                    if result["success"]:
                        events.append(f"【外交】{daimyo.clan_name}と{other_daimyo.clan_name}が不可侵条約を締結")
                        break

            # 関係値が非常に良好な場合は同盟を提案
            elif relation.relation_value >= config.ALLIANCE_RELATION_THRESHOLD and \
                 relation.relation_type != RelationType.ALLIANCE:
                if random.random() < 0.2:  # 20%の確率
                    result = self.diplomacy_system.propose_alliance(daimyo_id, other_daimyo.id)
                    if result["success"]:
                        events.append(f"【外交】{daimyo.clan_name}と{other_daimyo.clan_name}が同盟を締結")
                        break

        return events

    def _assign_generals_to_provinces(self, daimyo_id, provinces):
        """将軍を領地に配置"""
        events = []

        # 利用可能な将軍を取得
        available_generals = [
            general for general in self.game_state.generals.values()
            if general.serving_daimyo_id == daimyo_id and general.is_available
        ]

        if not available_generals:
            return events

        # 将軍が配置されていない領地を優先度順にソート
        # 優先度: 兵士数が多い、城がある、国境の領地
        unassigned_provinces = [p for p in provinces if not p.governor_general_id]

        if not unassigned_provinces:
            return events

        # 兵士数と城の有無で優先度を計算
        def province_priority(province):
            priority = province.soldiers
            if province.has_castle:
                priority += 1000  # 城がある領地は優先
            # 隣接領地に敵がいる場合は優先度アップ
            for adj_id in province.adjacent_provinces:
                adj = self.game_state.get_province(adj_id)
                if adj and adj.owner_daimyo_id != daimyo_id:
                    priority += 500
            return priority

        unassigned_provinces.sort(key=province_priority, reverse=True)

        # 能力値の高い将軍から配置
        available_generals.sort(
            key=lambda g: g.war_skill + g.leadership + g.politics + g.intelligence,
            reverse=True
        )

        # 将軍を配置
        for i, province in enumerate(unassigned_provinces):
            if i >= len(available_generals):
                break

            general = available_generals[i]
            result = self.internal_affairs.assign_governor(province, general)
            if result["success"]:
                daimyo = self.game_state.get_daimyo(daimyo_id)
                events.append(f"【{daimyo.clan_name}】{general.name}を{province.name}の守将に任命")
                self.game_state.record_command(daimyo_id, province.id, "assign_general")

        return events
