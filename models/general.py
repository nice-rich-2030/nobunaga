"""
General（武将）モデル
軍を率い、領地を統治する
"""
from typing import Optional, List


class General:
    """武将クラス - 軍指揮官・行政官"""

    def __init__(
        self,
        general_id: int,
        name: str,
        serving_daimyo_id: Optional[int] = None
    ):
        # ========================================
        # アイデンティティ
        # ========================================
        self.id = general_id
        self.name = name
        self.portrait = f"general_{general_id}.png"

        # ========================================
        # 忠誠
        # ========================================
        self.loyalty_to_daimyo = 70  # 0-100
        self.serving_daimyo_id = serving_daimyo_id

        # ========================================
        # 基本属性
        # ========================================
        self.age = 25
        self.health = 90  # 0-100

        # ========================================
        # 能力値（0-100）
        # ========================================
        self.war_skill = 60  # 戦闘効果
        self.leadership = 60  # 部隊士気ボーナス
        self.politics = 50  # 内政効果
        self.intelligence = 50  # 諜報/戦略成功率

        # ========================================
        # ステータス
        # ========================================
        self.is_available = True  # 領地に配属されていない
        self.current_province_id: Optional[int] = None

        # ========================================
        # 特殊能力（将来の拡張用）
        # ========================================
        self.special_traits: List[str] = []

    def assign_to_province(self, province_id: int):
        """領地に配属"""
        self.current_province_id = province_id
        self.is_available = False

    def unassign(self):
        """配属解除"""
        self.current_province_id = None
        self.is_available = True

    def change_loyalty(self, amount: int):
        """忠誠度を変更（0-100に制限）"""
        self.loyalty_to_daimyo = max(0, min(100, self.loyalty_to_daimyo + amount))

    def is_loyal(self) -> bool:
        """忠誠か（裏切りリスクなし）"""
        return self.loyalty_to_daimyo >= 50

    def betrayal_risk(self) -> float:
        """裏切りリスク（0.0-1.0）"""
        if self.loyalty_to_daimyo >= 80:
            return 0.0
        elif self.loyalty_to_daimyo >= 50:
            return 0.1
        elif self.loyalty_to_daimyo >= 30:
            return 0.3
        else:
            return 0.6

    def get_combat_bonus(self) -> float:
        """戦闘ボーナス（戦闘スキルに基づく）"""
        return 1.0 + (self.war_skill / 100.0) * 0.5  # 最大1.5倍

    def get_morale_bonus(self) -> int:
        """士気ボーナス（統率力に基づく）"""
        return int(self.leadership / 5)  # 最大+20

    def get_politics_bonus(self) -> float:
        """内政ボーナス（政治力に基づく）"""
        return 1.0 + (self.politics / 100.0) * 0.3  # 最大1.3倍

    def get_intelligence_bonus(self) -> float:
        """諜報ボーナス（知力に基づく）"""
        return 1.0 + (self.intelligence / 100.0) * 0.5  # 最大1.5倍

    def age_one_year(self):
        """1年加齢"""
        import random
        self.age += 1

        # 年齢による健康減少（大名と同じロジック）
        health_loss = 0

        if self.age > 60:
            health_loss = random.randint(3, 8)
        elif self.age > 50:
            health_loss = random.randint(2, 5)
        elif self.age > 40:
            health_loss = random.randint(1, 3)
        else:
            if random.random() < 0.1:
                health_loss = 1

        self.health = max(0, self.health - health_loss)

    def is_alive(self) -> bool:
        """生存しているか"""
        return self.health > 0

    def to_dict(self) -> dict:
        """辞書形式に変換（セーブ用）"""
        return {
            "id": self.id,
            "name": self.name,
            "portrait": self.portrait,
            "loyalty_to_daimyo": self.loyalty_to_daimyo,
            "serving_daimyo_id": self.serving_daimyo_id,
            "age": self.age,
            "health": self.health,
            "war_skill": self.war_skill,
            "leadership": self.leadership,
            "politics": self.politics,
            "intelligence": self.intelligence,
            "is_available": self.is_available,
            "current_province_id": self.current_province_id,
            "special_traits": self.special_traits
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'General':
        """辞書から復元（ロード用）"""
        general = cls(
            general_id=data["id"],
            name=data["name"],
            serving_daimyo_id=data.get("serving_daimyo_id")
        )

        # 全ての属性を復元
        general.portrait = data.get("portrait", f"general_{data['id']}.png")
        general.loyalty_to_daimyo = data.get("loyalty_to_daimyo", 70)
        general.age = data.get("age", 25)
        general.health = data.get("health", 90)
        general.war_skill = data.get("war_skill", 60)
        general.leadership = data.get("leadership", 60)
        general.politics = data.get("politics", 50)
        general.intelligence = data.get("intelligence", 50)
        general.is_available = data.get("is_available", True)
        general.current_province_id = data.get("current_province_id")
        general.special_traits = data.get("special_traits", [])

        return general

    def __repr__(self) -> str:
        status = "Available" if self.is_available else f"At Province {self.current_province_id}"
        return f"General({self.id}: {self.name}, War: {self.war_skill}, {status})"
