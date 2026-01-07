"""
InternalAffairsSystem - 内政システム
開発、耕作、忠誠度管理
"""
from models.province import Province
from models.general import General
import config


class InternalAffairsSystem:
    """内政システムクラス"""

    def __init__(self, game_state):
        self.game_state = game_state

    def execute_cultivation(self, province: Province) -> dict:
        """開墾を実行"""
        if not province.can_afford(gold=config.CULTIVATION_COST):
            return {"success": False, "message": "金が不足しています"}

        if province.development_level >= 10:
            return {"success": False, "message": "これ以上開発できません"}

        province.spend(gold=config.CULTIVATION_COST)
        province.development_level += 1
        province.update_loyalty(config.CULTIVATION_LOYALTY_PENALTY)

        return {
            "success": True,
            "message": f"開墾完了。開発レベル: {province.development_level}",
            "new_level": province.development_level
        }

    def execute_town_development(self, province: Province) -> dict:
        """町開発を実行"""
        if not province.can_afford(gold=config.TOWN_DEVELOPMENT_COST):
            return {"success": False, "message": "金が不足しています"}

        if province.town_level >= 10:
            return {"success": False, "message": "これ以上開発できません"}

        province.spend(gold=config.TOWN_DEVELOPMENT_COST)
        province.town_level += 1

        return {
            "success": True,
            "message": f"町開発完了。町レベル: {province.town_level}",
            "new_level": province.town_level
        }

    def execute_flood_control(self, province: Province) -> dict:
        """治水を実行"""
        if not province.can_afford(gold=config.FLOOD_CONTROL_COST):
            return {"success": False, "message": "金が不足しています"}

        if province.flood_control >= 100:
            return {"success": False, "message": "既に最大レベルです"}

        province.spend(gold=config.FLOOD_CONTROL_COST)
        province.flood_control = min(100, province.flood_control + config.FLOOD_CONTROL_BOOST)

        return {
            "success": True,
            "message": f"治水完了。治水レベル: {province.flood_control}%",
            "new_level": province.flood_control
        }

    def execute_give_rice(self, province: Province) -> dict:
        """米配布を実行"""
        if not province.can_afford(rice=config.GIVE_RICE_AMOUNT):
            return {"success": False, "message": "米が不足しています"}

        province.spend(rice=config.GIVE_RICE_AMOUNT)

        # 忠誠度上昇量を動的計算: (100 - 現在の忠誠度) // 2
        loyalty_boost = (100 - province.peasant_loyalty) // 2
        province.update_loyalty(loyalty_boost)

        return {
            "success": True,
            "message": f"米配布完了。忠誠度: {province.peasant_loyalty}",
            "new_loyalty": province.peasant_loyalty
        }

    def adjust_tax_rate(self, province: Province, new_rate: int) -> dict:
        """税率を調整"""
        new_rate = max(config.TAX_RATE_MIN, min(config.TAX_RATE_MAX, new_rate))
        old_rate = province.tax_rate
        province.tax_rate = new_rate

        return {
            "success": True,
            "message": f"税率変更: {old_rate}% → {new_rate}%",
            "old_rate": old_rate,
            "new_rate": new_rate
        }

    def assign_governor(self, province: Province, general: General) -> dict:
        """武将を太守として配属"""
        # 既に他の領地にいる場合は解除
        if general.current_province_id:
            old_province = self.game_state.get_province(general.current_province_id)
            if old_province:
                old_province.governor_general_id = None

        # 既存の太守を解除
        if province.governor_general_id:
            old_governor = self.game_state.get_general(province.governor_general_id)
            if old_governor:
                old_governor.unassign()

        # 新しい太守を配属
        province.governor_general_id = general.id
        general.assign_to_province(province.id)

        return {
            "success": True,
            "message": f"{general.name}を{province.name}の太守に任命",
            "general_name": general.name
        }

    def remove_governor(self, province: Province) -> dict:
        """太守を解任"""
        if not province.governor_general_id:
            return {"success": False, "message": "太守がいません"}

        general = self.game_state.get_general(province.governor_general_id)
        if general:
            general.unassign()

        province.governor_general_id = None

        return {
            "success": True,
            "message": "太守を解任しました"
        }

    def get_governor_bonus(self, province: Province) -> dict:
        """太守による各種ボーナスを取得"""
        if not province.governor_general_id:
            return {
                "politics_bonus": 1.0,
                "morale_bonus": 0
            }

        general = self.game_state.get_general(province.governor_general_id)
        if not general:
            return {
                "politics_bonus": 1.0,
                "morale_bonus": 0
            }

        return {
            "politics_bonus": general.get_politics_bonus(),
            "morale_bonus": general.get_morale_bonus()
        }

    def calculate_loyalty_change(self, province: Province) -> int:
        """忠誠度の変化量を計算"""
        change = config.LOYALTY_DECAY_RATE

        # 税率によるペナルティ
        if province.tax_rate > 50:
            change += int((province.tax_rate - 50) * config.LOYALTY_TAX_PENALTY)

        # 太守のボーナス
        if province.governor_general_id:
            general = self.game_state.get_general(province.governor_general_id)
            if general and general.politics > 70:
                change += 2  # 優秀な太守は忠誠度を維持

        return change

    def check_revolt_risk(self, province: Province) -> dict:
        """反乱リスクをチェック"""
        is_risk = province.is_revolt_risk()
        risk_level = "なし"

        if province.peasant_loyalty < 10:
            risk_level = "極めて高い"
        elif province.peasant_loyalty < 20:
            risk_level = "高い"
        elif province.peasant_loyalty < 30:
            risk_level = "中"
        elif province.peasant_loyalty < 40:
            risk_level = "低"

        return {
            "is_risk": is_risk,
            "risk_level": risk_level,
            "loyalty": province.peasant_loyalty
        }
