"""
TransferSystem - リソース転送システム
隣接する自領地間で兵士・金・米を転送
"""
from typing import Optional, List, Tuple
from models.province import Province


class TransferResult:
    """転送結果クラス"""

    def __init__(self):
        self.success = False
        self.message = ""
        self.from_province_name = ""
        self.to_province_name = ""
        self.resource_type = ""
        self.amount = 0


class TransferSystem:
    """リソース転送システムクラス"""

    # 転送上限
    MAX_SOLDIERS_TRANSFER = 100
    MAX_GOLD_TRANSFER = 500
    MAX_RICE_TRANSFER = 300

    def __init__(self, game_state):
        self.game_state = game_state

    def get_valid_transfer_targets(self, from_province_id: int) -> List[Province]:
        """
        転送可能な隣接領地のリストを取得

        条件:
        - 隣接している
        - 同じ大名が支配している
        """
        from_province = self.game_state.get_province(from_province_id)
        if not from_province or not from_province.owner_daimyo_id:
            return []

        valid_targets = []

        for adj_id in from_province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
            if not adj_province:
                continue

            # 同じ大名が支配しているか確認
            if adj_province.owner_daimyo_id == from_province.owner_daimyo_id:
                valid_targets.append(adj_province)

        return valid_targets

    def transfer_soldiers(
        self,
        from_province_id: int,
        to_province_id: int,
        amount: int
    ) -> TransferResult:
        """兵士を転送"""
        result = TransferResult()
        result.resource_type = "兵士"

        # バリデーション
        validation_msg = self._validate_transfer(from_province_id, to_province_id)
        if validation_msg:
            result.success = False
            result.message = validation_msg
            return result

        from_province = self.game_state.get_province(from_province_id)
        to_province = self.game_state.get_province(to_province_id)

        # 転送量の検証
        if amount <= 0:
            result.success = False
            result.message = "転送量は1以上を指定してください"
            return result

        if amount > self.MAX_SOLDIERS_TRANSFER:
            result.success = False
            result.message = f"兵士は1ターンに最大{self.MAX_SOLDIERS_TRANSFER}人まで転送可能です"
            return result

        if from_province.soldiers < amount:
            result.success = False
            result.message = f"兵士が不足しています（必要: {amount}人、保有: {from_province.soldiers}人）"
            return result

        # 最低守備兵を残す（10人）
        if from_province.soldiers - amount < 10:
            result.success = False
            result.message = "最低10人の兵士を残す必要があります"
            return result

        # 転送実行
        from_province.soldiers -= amount
        to_province.soldiers += amount

        result.success = True
        result.from_province_name = from_province.name
        result.to_province_name = to_province.name
        result.amount = amount
        result.message = f"⚔ {from_province.name} → {to_province.name}: 兵士{amount}人を移動"

        return result

    def transfer_gold(
        self,
        from_province_id: int,
        to_province_id: int,
        amount: int
    ) -> TransferResult:
        """金を転送"""
        result = TransferResult()
        result.resource_type = "金"

        # バリデーション
        validation_msg = self._validate_transfer(from_province_id, to_province_id)
        if validation_msg:
            result.success = False
            result.message = validation_msg
            return result

        from_province = self.game_state.get_province(from_province_id)
        to_province = self.game_state.get_province(to_province_id)

        # 転送量の検証
        if amount <= 0:
            result.success = False
            result.message = "転送量は1以上を指定してください"
            return result

        if amount > self.MAX_GOLD_TRANSFER:
            result.success = False
            result.message = f"金は1ターンに最大{self.MAX_GOLD_TRANSFER}まで転送可能です"
            return result

        if from_province.gold < amount:
            result.success = False
            result.message = f"金が不足しています（必要: {amount}、保有: {from_province.gold}）"
            return result

        # 転送実行
        from_province.gold -= amount
        to_province.gold += amount

        result.success = True
        result.from_province_name = from_province.name
        result.to_province_name = to_province.name
        result.amount = amount
        result.message = f"💰 {from_province.name} → {to_province.name}: 金{amount}を送付"

        return result

    def transfer_rice(
        self,
        from_province_id: int,
        to_province_id: int,
        amount: int
    ) -> TransferResult:
        """米を転送"""
        result = TransferResult()
        result.resource_type = "米"

        # バリデーション
        validation_msg = self._validate_transfer(from_province_id, to_province_id)
        if validation_msg:
            result.success = False
            result.message = validation_msg
            return result

        from_province = self.game_state.get_province(from_province_id)
        to_province = self.game_state.get_province(to_province_id)

        # 転送量の検証
        if amount <= 0:
            result.success = False
            result.message = "転送量は1以上を指定してください"
            return result

        if amount > self.MAX_RICE_TRANSFER:
            result.success = False
            result.message = f"米は1ターンに最大{self.MAX_RICE_TRANSFER}まで転送可能です"
            return result

        if from_province.rice < amount:
            result.success = False
            result.message = f"米が不足しています（必要: {amount}、保有: {from_province.rice}）"
            return result

        # 転送実行
        from_province.rice -= amount
        to_province.rice += amount

        result.success = True
        result.from_province_name = from_province.name
        result.to_province_name = to_province.name
        result.amount = amount
        result.message = f"🌾 {from_province.name} → {to_province.name}: 米{amount}を運搬"

        return result

    def _validate_transfer(self, from_province_id: int, to_province_id: int) -> Optional[str]:
        """転送の基本バリデーション（共通）"""
        from_province = self.game_state.get_province(from_province_id)
        to_province = self.game_state.get_province(to_province_id)

        if not from_province:
            return "転送元の領地が存在しません"

        if not to_province:
            return "転送先の領地が存在しません"

        # 同じ領地への転送は不可
        if from_province_id == to_province_id:
            return "同じ領地への転送はできません"

        # 隣接チェック
        if to_province_id not in from_province.adjacent_provinces:
            return "隣接していない領地への転送はできません"

        # 所有者チェック
        if from_province.owner_daimyo_id != to_province.owner_daimyo_id:
            return "異なる大名の領地への転送はできません"

        if not from_province.owner_daimyo_id:
            return "無所属の領地からは転送できません"

        return None
