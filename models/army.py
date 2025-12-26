"""
Army（軍隊）モデル
移動中または戦闘中の軍事ユニット
"""
from typing import Optional


class Army:
    """軍隊クラス - 移動・戦闘用の軍事ユニット"""

    def __init__(
        self,
        army_id: int,
        daimyo_id: int,
        general_id: Optional[int],
        current_province_id: int
    ):
        # ========================================
        # アイデンティティ
        # ========================================
        self.id = army_id
        self.daimyo_id = daimyo_id
        self.general_id = general_id  # 指揮官（None可）

        # ========================================
        # 部隊構成
        # ========================================
        self.infantry = 0  # 歩兵
        self.cavalry = 0  # 騎兵
        self.archers = 0  # 弓兵

        # ========================================
        # ステータス
        # ========================================
        self.morale = 70  # 0-100
        self.rice_supply = 0  # 遠征用の米補給

        # ========================================
        # 位置
        # ========================================
        self.current_province_id = current_province_id
        self.destination_province_id: Optional[int] = None  # 移動中の場合

        # ========================================
        # 移動
        # ========================================
        self.movement_points = 1  # 1ターンに移動できる領地数

    @property
    def total_troops(self) -> int:
        """総兵力"""
        return self.infantry + self.cavalry + self.archers

    def set_troops(self, infantry: int = 0, cavalry: int = 0, archers: int = 0):
        """部隊を設定"""
        self.infantry = max(0, infantry)
        self.cavalry = max(0, cavalry)
        self.archers = max(0, archers)

    def add_troops(self, infantry: int = 0, cavalry: int = 0, archers: int = 0):
        """部隊を追加"""
        self.infantry += infantry
        self.cavalry += cavalry
        self.archers += archers

    def calculate_combat_power(self, general_bonus: float = 1.0) -> int:
        """戦闘力を計算"""
        # 基本戦闘力（兵種による差）
        power = self.infantry * 1.0  # 歩兵は基本
        power += self.cavalry * 1.5  # 騎兵は1.5倍
        power += self.archers * 1.2  # 弓兵は1.2倍

        # 士気効果
        if self.morale > 50:
            morale_bonus = 1.0 + (self.morale - 50) * 0.02
            power *= morale_bonus
        elif self.morale < 50:
            morale_penalty = 1.0 - (50 - self.morale) * 0.02
            power *= max(0.5, morale_penalty)

        # 武将ボーナス
        power *= general_bonus

        return int(power)

    def consume_rice(self, amount: int) -> bool:
        """米を消費（成功/失敗を返す）"""
        if self.rice_supply >= amount:
            self.rice_supply -= amount
            return True
        else:
            # 米不足の場合、士気低下
            self.morale = max(0, self.morale - 10)
            return False

    def update_morale(self, change: int):
        """士気を更新"""
        self.morale = max(0, min(100, self.morale + change))

    def is_moving(self) -> bool:
        """移動中か"""
        return self.destination_province_id is not None

    def to_dict(self) -> dict:
        """辞書形式に変換（セーブ用）"""
        return {
            "id": self.id,
            "daimyo_id": self.daimyo_id,
            "general_id": self.general_id,
            "infantry": self.infantry,
            "cavalry": self.cavalry,
            "archers": self.archers,
            "morale": self.morale,
            "rice_supply": self.rice_supply,
            "current_province_id": self.current_province_id,
            "destination_province_id": self.destination_province_id,
            "movement_points": self.movement_points
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Army':
        """辞書から復元（ロード用）"""
        army = cls(
            army_id=data["id"],
            daimyo_id=data["daimyo_id"],
            general_id=data.get("general_id"),
            current_province_id=data["current_province_id"]
        )

        army.infantry = data.get("infantry", 0)
        army.cavalry = data.get("cavalry", 0)
        army.archers = data.get("archers", 0)
        army.morale = data.get("morale", 70)
        army.rice_supply = data.get("rice_supply", 0)
        army.destination_province_id = data.get("destination_province_id")
        army.movement_points = data.get("movement_points", 1)

        return army

    def __repr__(self) -> str:
        return f"Army({self.id}: Total {self.total_troops}, Morale: {self.morale}, At: {self.current_province_id})"
