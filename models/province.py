"""
Province（領地）モデル
各領地はローカルリソース（金、米、農民、兵士）を管理
"""
from typing import Optional, List
import config


class Province:
    """領地クラス - ゲームの基本単位"""

    def __init__(
        self,
        province_id: int,
        name: str,
        position: tuple[int, int],
        terrain_type: str = config.TERRAIN_PLAINS,
        max_peasants: int = 8000
    ):
        # ========================================
        # アイデンティティ
        # ========================================
        self.id = province_id
        self.name = name
        self.position = position  # マップ上の座標
        self.adjacent_provinces: List[int] = []  # 隣接領地のID

        # ========================================
        # 所有権
        # ========================================
        self.owner_daimyo_id: Optional[int] = None  # 所有大名
        self.governor_general_id: Optional[int] = None  # 統治武将

        # ========================================
        # 人口
        # ========================================
        self.peasants = max_peasants // 2  # 初期は最大の半分
        self.max_peasants = max_peasants
        self.peasant_loyalty = 50  # 0-100

        # ========================================
        # 軍事
        # ========================================
        self.soldiers = 200  # 初期兵力
        self.soldier_morale = 70  # 0-100
        self.soldier_training = 1.0  # 訓練度（戦闘力乗数）

        # ========================================
        # 経済
        # ========================================
        self.gold = 500
        self.rice = 300
        self.tax_rate = config.TAX_RATE_DEFAULT  # デフォルト50%

        # ========================================
        # 開発
        # ========================================
        self.development_level = 3  # 1-10（米生産に影響）
        self.town_level = 2  # 1-10（税収に影響）
        self.flood_control = 40  # 0-100（災害防止）

        # ========================================
        # 地形と特徴
        # ========================================
        self.terrain_type = terrain_type
        self.has_castle = True  # 初期は全領地に城あり
        self.castle_defense = 50  # 0-100

        # ========================================
        # コマンド実行フラグ
        # ========================================
        self.command_used_this_turn = False

    def calculate_rice_production(self) -> int:
        """米生産量を計算"""
        base_production = config.BASE_RICE_PRODUCTION * self.development_level

        # 地形効果
        terrain_mult = config.TERRAIN_EFFECTS.get(
            self.terrain_type, {}
        ).get("rice_multiplier", 1.0)

        # 忠誠度ボーナス
        loyalty_mult = 1.0
        if self.peasant_loyalty >= config.HIGH_LOYALTY_THRESHOLD:
            loyalty_mult = config.HIGH_LOYALTY_BONUS

        production = int(base_production * terrain_mult * loyalty_mult)
        return production

    def calculate_tax_income(self) -> int:
        """税収を計算"""
        base_income = config.BASE_TAX_INCOME * self.town_level
        tax_multiplier = self.tax_rate / 100.0

        # 農民数に基づく補正
        peasant_ratio = self.peasants / self.max_peasants

        income = int(base_income * tax_multiplier * peasant_ratio)
        return income

    def calculate_soldier_rice_consumption(self) -> int:
        """兵士の米消費量を計算"""
        return self.soldiers * config.SOLDIER_RICE_CONSUMPTION

    def update_loyalty(self, change: int):
        """忠誠度を更新（0-100に制限）"""
        self.peasant_loyalty = max(0, min(100, self.peasant_loyalty + change))

    def update_morale(self, change: int):
        """士気を更新（0-100に制限）"""
        self.soldier_morale = max(0, min(100, self.soldier_morale + change))

    def add_gold(self, amount: int):
        """金を追加"""
        self.gold = max(0, self.gold + amount)

    def add_rice(self, amount: int):
        """米を追加"""
        self.rice = max(0, self.rice + amount)

    def add_peasants(self, amount: int):
        """農民を追加（最大値制限あり）"""
        self.peasants = max(0, min(self.max_peasants, self.peasants + amount))

    def add_soldiers(self, amount: int):
        """兵士を追加"""
        self.soldiers = max(0, self.soldiers + amount)

    def can_afford(self, gold: int = 0, rice: int = 0) -> bool:
        """コストを支払えるか確認"""
        return self.gold >= gold and self.rice >= rice

    def spend(self, gold: int = 0, rice: int = 0) -> bool:
        """リソースを消費（成功/失敗を返す）"""
        if not self.can_afford(gold, rice):
            return False
        self.gold -= gold
        self.rice -= rice
        return True

    def get_defense_bonus(self) -> float:
        """防御ボーナスを計算"""
        bonus = 1.0

        # 地形ボーナス
        terrain_bonus = config.TERRAIN_EFFECTS.get(
            self.terrain_type, {}
        ).get("defense_bonus", 1.0)
        bonus *= terrain_bonus

        # 城ボーナス
        if self.has_castle:
            castle_mult = 1.0 + (self.castle_defense / 100.0) * (config.CASTLE_DEFENSE_BONUS - 1.0)
            bonus *= castle_mult

        return bonus

    def get_combat_power(self) -> int:
        """戦闘力を計算"""
        base_power = self.soldiers

        # 訓練度
        base_power = int(base_power * self.soldier_training)

        # 士気効果
        if self.soldier_morale > 50:
            morale_bonus = 1.0 + (self.soldier_morale - 50) * config.MORALE_COMBAT_MODIFIER
            base_power = int(base_power * morale_bonus)
        elif self.soldier_morale < 50:
            morale_penalty = 1.0 - (50 - self.soldier_morale) * config.MORALE_COMBAT_MODIFIER
            base_power = int(base_power * max(0.5, morale_penalty))

        return base_power

    def is_revolt_risk(self) -> bool:
        """反乱リスクがあるか"""
        return self.peasant_loyalty < config.REVOLT_THRESHOLD

    def reset_command_flag(self):
        """ターン開始時にコマンドフラグをリセット"""
        self.command_used_this_turn = False

    def to_dict(self) -> dict:
        """辞書形式に変換（セーブ用）"""
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "adjacent_provinces": self.adjacent_provinces,
            "owner_daimyo_id": self.owner_daimyo_id,
            "governor_general_id": self.governor_general_id,
            "peasants": self.peasants,
            "max_peasants": self.max_peasants,
            "peasant_loyalty": self.peasant_loyalty,
            "soldiers": self.soldiers,
            "soldier_morale": self.soldier_morale,
            "soldier_training": self.soldier_training,
            "gold": self.gold,
            "rice": self.rice,
            "tax_rate": self.tax_rate,
            "development_level": self.development_level,
            "town_level": self.town_level,
            "flood_control": self.flood_control,
            "terrain_type": self.terrain_type,
            "has_castle": self.has_castle,
            "castle_defense": self.castle_defense
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Province':
        """辞書から復元（ロード用）"""
        province = cls(
            province_id=data["id"],
            name=data["name"],
            position=tuple(data["position"]),
            terrain_type=data.get("terrain_type", config.TERRAIN_PLAINS),
            max_peasants=data.get("max_peasants", 8000)
        )

        # 全ての属性を復元
        province.adjacent_provinces = data.get("adjacent_provinces", [])
        province.owner_daimyo_id = data.get("owner_daimyo_id")
        province.governor_general_id = data.get("governor_general_id")
        province.peasants = data.get("peasants", province.peasants)
        province.peasant_loyalty = data.get("peasant_loyalty", 50)
        province.soldiers = data.get("soldiers", 200)
        province.soldier_morale = data.get("soldier_morale", 70)
        province.soldier_training = data.get("soldier_training", 1.0)
        province.gold = data.get("gold", 500)
        province.rice = data.get("rice", 300)
        province.tax_rate = data.get("tax_rate", config.TAX_RATE_DEFAULT)
        province.development_level = data.get("development_level", 3)
        province.town_level = data.get("town_level", 2)
        province.flood_control = data.get("flood_control", 40)
        province.has_castle = data.get("has_castle", True)
        province.castle_defense = data.get("castle_defense", 50)

        return province

    def __repr__(self) -> str:
        return f"Province({self.id}: {self.name}, Owner: {self.owner_daimyo_id}, Gold: {self.gold}, Rice: {self.rice})"
