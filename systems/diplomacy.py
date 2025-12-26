"""
外交システム - 大名間の外交関係を管理
"""
import config
from models.diplomacy import DiplomaticRelation, RelationType


class DiplomacySystem:
    """外交システム"""

    def __init__(self, game_state):
        self.game_state = game_state

    def propose_alliance(self, proposer_id, target_id):
        """同盟を提案"""
        proposer = self.game_state.get_daimyo(proposer_id)
        target = self.game_state.get_daimyo(target_id)

        if not proposer or not target:
            return {"success": False, "message": "無効な大名です"}

        if proposer_id == target_id:
            return {"success": False, "message": "自分自身とは同盟できません"}

        # 既存の関係を取得
        relation = self.game_state.get_diplomatic_relation(proposer_id, target_id)

        if relation.relation_type == RelationType.ALLIANCE:
            return {"success": False, "message": f"{target.clan_name}とは既に同盟関係です"}

        if relation.relation_type == RelationType.WAR:
            return {"success": False, "message": f"{target.clan_name}とは交戦中です"}

        # 関係値チェック
        if relation.relation_value < config.ALLIANCE_RELATION_THRESHOLD:
            return {
                "success": False,
                "message": f"{target.clan_name}との関係が不十分です（必要: {config.ALLIANCE_RELATION_THRESHOLD}）"
            }

        # 同盟成立
        relation.relation_type = RelationType.ALLIANCE
        relation.treaty_duration = config.TREATY_DURATION_TURNS

        return {
            "success": True,
            "message": f"{target.clan_name}と同盟を結びました（{config.TREATY_DURATION_TURNS}ターン）"
        }

    def propose_non_aggression(self, proposer_id, target_id):
        """不可侵条約を提案"""
        proposer = self.game_state.get_daimyo(proposer_id)
        target = self.game_state.get_daimyo(target_id)

        if not proposer or not target:
            return {"success": False, "message": "無効な大名です"}

        if proposer_id == target_id:
            return {"success": False, "message": "自分自身とは条約を結べません"}

        relation = self.game_state.get_diplomatic_relation(proposer_id, target_id)

        if relation.relation_type == RelationType.ALLIANCE:
            return {"success": False, "message": f"{target.clan_name}とは既に同盟関係です"}

        if relation.relation_type == RelationType.WAR:
            return {"success": False, "message": f"{target.clan_name}とは交戦中です"}

        if relation.relation_type == RelationType.NON_AGGRESSION:
            return {"success": False, "message": f"{target.clan_name}とは既に不可侵条約を結んでいます"}

        # 関係値チェック
        if relation.relation_value < config.NON_AGGRESSION_RELATION_THRESHOLD:
            return {
                "success": False,
                "message": f"{target.clan_name}との関係が不十分です（必要: {config.NON_AGGRESSION_RELATION_THRESHOLD}）"
            }

        # 条約成立
        relation.relation_type = RelationType.NON_AGGRESSION
        relation.treaty_duration = config.TREATY_DURATION_TURNS

        return {
            "success": True,
            "message": f"{target.clan_name}と不可侵条約を結びました（{config.TREATY_DURATION_TURNS}ターン）"
        }

    def declare_war(self, declarer_id, target_id):
        """宣戦布告"""
        declarer = self.game_state.get_daimyo(declarer_id)
        target = self.game_state.get_daimyo(target_id)

        if not declarer or not target:
            return {"success": False, "message": "無効な大名です"}

        if declarer_id == target_id:
            return {"success": False, "message": "自分自身には宣戦布告できません"}

        relation = self.game_state.get_diplomatic_relation(declarer_id, target_id)

        if relation.relation_type == RelationType.WAR:
            return {"success": False, "message": f"{target.clan_name}とは既に交戦中です"}

        # 同盟や不可侵条約を破棄する場合、大きなペナルティ
        if relation.relation_type in [RelationType.ALLIANCE, RelationType.NON_AGGRESSION]:
            relation.relation_value += config.BETRAYAL_PENALTY
            betrayal_msg = f"（条約破棄により関係値{config.BETRAYAL_PENALTY}）"
        else:
            betrayal_msg = ""

        # 宣戦布告
        relation.relation_type = RelationType.WAR
        relation.relation_value += config.WAR_RELATION_PENALTY
        relation.treaty_duration = 0

        return {
            "success": True,
            "message": f"{target.clan_name}に宣戦布告しました{betrayal_msg}"
        }

    def send_gift(self, sender_id, receiver_id):
        """贈り物（金）を送る"""
        sender = self.game_state.get_daimyo(sender_id)
        receiver = self.game_state.get_daimyo(receiver_id)

        if not sender or not receiver:
            return {"success": False, "message": "無効な大名です"}

        if sender_id == receiver_id:
            return {"success": False, "message": "自分自身には贈り物できません"}

        # 金をチェック（全領地の合計）
        total_gold = sum(p.gold for p in self.game_state.provinces.values() if p.owner_daimyo_id == sender_id)

        if total_gold < config.GIFT_GOLD_AMOUNT:
            return {
                "success": False,
                "message": f"金が不足しています（必要: {config.GIFT_GOLD_AMOUNT}）"
            }

        # 金を差し引く（最初の領地から）
        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id == sender_id:
                province.add_gold(-config.GIFT_GOLD_AMOUNT)
                break

        # 相手の最初の領地に金を追加
        for province in self.game_state.provinces.values():
            if province.owner_daimyo_id == receiver_id:
                province.add_gold(config.GIFT_GOLD_AMOUNT)
                break

        # 関係値を向上
        relation = self.game_state.get_diplomatic_relation(sender_id, receiver_id)
        relation.relation_value += config.GIFT_RELATION_BOOST

        return {
            "success": True,
            "message": f"{receiver.clan_name}に金{config.GIFT_GOLD_AMOUNT}を贈りました（関係値+{config.GIFT_RELATION_BOOST}）"
        }

    def get_all_relations(self, daimyo_id):
        """指定された大名の全ての外交関係を取得"""
        relations = []
        for other_id, other_daimyo in self.game_state.daimyo.items():
            if other_id != daimyo_id and other_daimyo.is_alive:
                relation = self.game_state.get_diplomatic_relation(daimyo_id, other_id)
                relations.append({
                    "daimyo": other_daimyo,
                    "relation": relation
                })
        return relations

    def update_treaties(self):
        """条約期間を更新（ターン終了時に呼ばれる）"""
        events = []

        for relation in self.game_state.diplomatic_relations:
            if relation.treaty_duration > 0:
                relation.treaty_duration -= 1

                # 条約期間終了
                if relation.treaty_duration == 0:
                    daimyo1 = self.game_state.get_daimyo(relation.daimyo1_id)
                    daimyo2 = self.game_state.get_daimyo(relation.daimyo2_id)

                    if daimyo1 and daimyo2:
                        relation_name = "同盟" if relation.relation_type == RelationType.ALLIANCE else "不可侵条約"
                        events.append(f"{daimyo1.clan_name}と{daimyo2.clan_name}の{relation_name}が期限切れになりました")

                        # 条約終了後は中立に
                        relation.relation_type = RelationType.NEUTRAL

        return events

    def can_attack(self, attacker_id, target_id):
        """攻撃可能かチェック（外交関係を考慮）"""
        if attacker_id == target_id:
            return False

        relation = self.game_state.get_diplomatic_relation(attacker_id, target_id)

        # 関係が存在しない場合は攻撃可能
        if not relation:
            return True

        # 同盟国や不可侵条約国には攻撃できない（条約を破棄すれば可能）
        if relation.relation_type in [RelationType.ALLIANCE, RelationType.NON_AGGRESSION]:
            return False

        return True
