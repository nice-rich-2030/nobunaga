"""
AIシステム - コンピュータ制御の大名の意思決定
"""
import random
import config
from models.diplomacy import RelationType


class AISystem:
    """AIシステム"""

    def __init__(self, game_state, internal_affairs, military_system, diplomacy_system):
        self.game_state = game_state
        self.internal_affairs = internal_affairs
        self.military_system = military_system
        self.diplomacy_system = diplomacy_system
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

            elif action["type"] == "develop_town":
                result = self.internal_affairs.execute_town_development(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で町開発（町Lv→{province.town_level}）")

            elif action["type"] == "flood_control":
                result = self.internal_affairs.execute_flood_control(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で治水（治水→{province.flood_control}%）")

            elif action["type"] == "give_rice":
                result = self.internal_affairs.execute_give_rice(province)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で米配布（忠誠度→{province.peasant_loyalty}）")

            elif action["type"] == "recruit":
                result = self.military_system.recruit_soldiers(province, 100)
                if result["success"]:
                    events.append(f"【{daimyo.clan_name}】{province.name}で徴兵100人（兵力→{province.soldiers}人）")

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

            elif action["type"] == "transfer":
                # 転送コマンドを実行
                target_province_id = action["target"]
                resource_type = action["resource"]
                amount = action["amount"]
                target_province = self.game_state.get_province(target_province_id)

                if target_province:
                    result = self.internal_affairs.transfer_resources(
                        province, target_province, resource_type, amount
                    )
                    if result["success"]:
                        resource_names = {"gold": "金", "rice": "米", "soldiers": "兵"}
                        events.append(f"【{daimyo.clan_name}】{province.name}から{target_province.name}へ{resource_names[resource_type]}{amount}を転送")

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

        # 転送先候補を探す（敵に隣接している自領地）
        transfer_targets = []
        for other_province in self.game_state.provinces.values():
            if other_province.owner_daimyo_id != daimyo.id:
                continue

            if other_province.id == province.id:
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

        if not transfer_targets:
            return {"type": "none"}

        # 最優先の転送先を選択
        transfer_targets.sort(key=lambda x: x[1], reverse=True)
        target = transfer_targets[0][0]

        # 転送する資源を決定
        if target.soldiers < 200 and province.soldiers > 150:
            return {"type": "transfer", "target": target.id, "resource": "soldiers", "amount": 100}
        elif target.gold < 500 and province.gold > 1000:
            return {"type": "transfer", "target": target.id, "resource": "gold", "amount": 500}
        elif province.rice > 1000:
            return {"type": "transfer", "target": target.id, "resource": "rice", "amount": 500}

        return {"type": "none"}

    def _has_enemy_neighbor(self, province, daimyo_id):
        """領地が敵に隣接しているかチェック"""
        for adj_id in province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
            if adj_province and adj_province.owner_daimyo_id != daimyo_id:
                return True
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

        return events
