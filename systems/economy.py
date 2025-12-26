"""
EconomySystem - 経済システム
金・米の管理、交易、商人システム
"""
from typing import Optional
from models.province import Province
import config


class EconomySystem:
    """経済システムクラス"""

    def __init__(self, game_state):
        self.game_state = game_state

    def calculate_total_income(self, daimyo_id: int) -> dict:
        """大名の総収入を計算"""
        total_gold = 0
        total_rice = 0

        provinces = self.game_state.get_daimyo_provinces(daimyo_id)
        for province in provinces:
            total_gold += province.calculate_tax_income()
            total_rice += province.calculate_rice_production()

        return {
            "gold": total_gold,
            "rice": total_rice
        }

    def calculate_total_upkeep(self, daimyo_id: int) -> dict:
        """大名の総維持費を計算"""
        total_rice_upkeep = 0

        provinces = self.game_state.get_daimyo_provinces(daimyo_id)
        for province in provinces:
            total_rice_upkeep += province.calculate_soldier_rice_consumption()

        return {
            "rice": total_rice_upkeep
        }

    def trade_rice_for_gold(self, province: Province, rice_amount: int) -> bool:
        """米を金に交換（商人取引）"""
        if not province.can_afford(rice=rice_amount):
            return False

        # 交換レート: 米2 = 金1
        gold_received = rice_amount // 2

        province.spend(rice=rice_amount)
        province.add_gold(gold_received)

        return True

    def trade_gold_for_rice(self, province: Province, gold_amount: int) -> bool:
        """金を米に交換（商人取引）"""
        if not province.can_afford(gold=gold_amount):
            return False

        # 交換レート: 金1 = 米1.5
        rice_received = int(gold_amount * 1.5)

        province.spend(gold=gold_amount)
        province.add_rice(rice_received)

        return True

    def borrow_gold(self, province: Province, amount: int) -> bool:
        """金を借りる（利息なし、簡略版）"""
        # 将来的には利息システムを追加可能
        province.add_gold(amount)
        return True

    def transfer_resources(
        self,
        from_province: Province,
        to_province: Province,
        gold: int = 0,
        rice: int = 0
    ) -> bool:
        """領地間でリソースを移動"""
        # 同じ大名の領地かチェック
        if from_province.owner_daimyo_id != to_province.owner_daimyo_id:
            return False

        # リソース確認
        if not from_province.can_afford(gold=gold, rice=rice):
            return False

        # 転送実行
        from_province.spend(gold=gold, rice=rice)
        to_province.add_gold(gold)
        to_province.add_rice(rice)

        return True

    def get_province_budget_status(self, province: Province) -> dict:
        """領地の収支状況を取得"""
        income = province.calculate_tax_income()
        rice_production = province.calculate_rice_production()
        rice_consumption = province.calculate_soldier_rice_consumption()

        return {
            "gold_income": income,
            "rice_production": rice_production,
            "rice_consumption": rice_consumption,
            "rice_balance": rice_production - rice_consumption,
            "gold_reserve": province.gold,
            "rice_reserve": province.rice
        }

    def can_afford_development(self, province: Province, development_type: str) -> bool:
        """開発を実行できるか確認"""
        costs = {
            "cultivate": config.CULTIVATION_COST,
            "develop_town": config.TOWN_DEVELOPMENT_COST,
            "flood_control": config.FLOOD_CONTROL_COST,
            "training": config.TRAINING_COST
        }

        cost = costs.get(development_type, 0)
        return province.can_afford(gold=cost)
