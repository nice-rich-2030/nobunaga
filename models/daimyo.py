"""
Daimyo（大名）モデル
プレイヤーまたはAI勢力のリーダー
"""
from typing import Optional, List, Dict


class Daimyo:
    """大名クラス - 勢力のリーダー"""

    def __init__(
        self,
        daimyo_id: int,
        name: str,
        clan_name: str,
        is_player: bool = False
    ):
        # ========================================
        # アイデンティティ
        # ========================================
        self.id = daimyo_id
        self.name = name
        self.clan_name = clan_name
        self.portrait = f"{clan_name}.png"  # アセットパス

        # ========================================
        # プレイヤー/AI
        # ========================================
        self.is_player = is_player
        self.is_alive = True

        # ========================================
        # 能力値（0-100）
        # ========================================
        self.age = 30
        self.health = 90
        self.ambition = 70  # AI攻撃性
        self.luck = 50  # ランダムイベント修正
        self.charm = 60  # 外交、忠誠度
        self.intelligence = 70  # 経済、戦略
        self.war_skill = 60  # 戦闘能力

        # ========================================
        # 継承
        # ========================================
        self.successor_id: Optional[int] = None  # 後継者（武将ID）

        # ========================================
        # 領土
        # ========================================
        self.capital_province_id: Optional[int] = None
        self.controlled_provinces: List[int] = []

        # ========================================
        # 外交関係（他大名IDをキー、関係値-100〜+100を値）
        # ========================================
        self.relations: Dict[int, int] = {}

        # ========================================
        # 統計（計算値）
        # ========================================
        self.total_military_strength = 0
        self.total_gold = 0
        self.total_rice = 0

        # ========================================
        # 戦績
        # ========================================
        self.battle_wins = 0  # 勝利数
        self.battle_losses = 0  # 敗北数

    def add_province(self, province_id: int):
        """領地を追加"""
        if province_id not in self.controlled_provinces:
            self.controlled_provinces.append(province_id)

    def remove_province(self, province_id: int):
        """領地を削除"""
        if province_id in self.controlled_provinces:
            self.controlled_provinces.remove(province_id)

    def get_province_count(self) -> int:
        """支配領地数を取得"""
        return len(self.controlled_provinces)

    def set_relation(self, other_daimyo_id: int, value: int):
        """他大名との関係値を設定（-100〜+100）"""
        self.relations[other_daimyo_id] = max(-100, min(100, value))

    def adjust_relation(self, other_daimyo_id: int, change: int):
        """関係値を調整"""
        current = self.relations.get(other_daimyo_id, 0)
        self.set_relation(other_daimyo_id, current + change)

    def get_relation(self, other_daimyo_id: int) -> int:
        """関係値を取得"""
        return self.relations.get(other_daimyo_id, 0)

    def is_friendly(self, other_daimyo_id: int) -> bool:
        """友好的か（関係値 > 0）"""
        return self.get_relation(other_daimyo_id) > 0

    def is_hostile(self, other_daimyo_id: int) -> bool:
        """敵対的か（関係値 < 0）"""
        return self.get_relation(other_daimyo_id) < 0

    def age_one_year(self):
        """1年加齢"""
        import random
        self.age += 1

        # 年齢による健康減少（より速く）
        health_loss = 0

        if self.age > 60:
            # 60歳以上：大きく減少
            health_loss = random.randint(3, 8)
        elif self.age > 50:
            # 50歳以上：中程度減少
            health_loss = random.randint(2, 5)
        elif self.age > 40:
            # 40歳以上：小さく減少
            health_loss = random.randint(1, 3)
        else:
            # 40歳以下：ごく稀に減少
            if random.random() < 0.1:  # 10%の確率
                health_loss = 1

        self.health = max(0, self.health - health_loss)

        # 健康が0になったら死亡
        if self.health <= 0:
            self.is_alive = False

    def get_diplomacy_bonus(self) -> float:
        """外交ボーナス（魅力値に基づく）"""
        return 1.0 + (self.charm / 100.0) * 0.5  # 最大1.5倍

    def get_economic_bonus(self) -> float:
        """経済ボーナス（知力値に基づく）"""
        return 1.0 + (self.intelligence / 100.0) * 0.3  # 最大1.3倍

    def get_military_bonus(self) -> float:
        """軍事ボーナス（戦闘値に基づく）"""
        return 1.0 + (self.war_skill / 100.0) * 0.2  # 最大1.2倍

    def update_statistics(self, provinces: List):
        """統計を更新（ターン終了時などに呼ぶ）"""
        self.total_gold = 0
        self.total_rice = 0
        self.total_military_strength = 0

        for province in provinces:
            if province.owner_daimyo_id == self.id:
                self.total_gold += province.gold
                self.total_rice += province.rice
                self.total_military_strength += province.soldiers

    def to_dict(self) -> dict:
        """辞書形式に変換（セーブ用）"""
        return {
            "id": self.id,
            "name": self.name,
            "clan_name": self.clan_name,
            "portrait": self.portrait,
            "is_player": self.is_player,
            "is_alive": self.is_alive,
            "age": self.age,
            "health": self.health,
            "ambition": self.ambition,
            "luck": self.luck,
            "charm": self.charm,
            "intelligence": self.intelligence,
            "war_skill": self.war_skill,
            "successor_id": self.successor_id,
            "capital_province_id": self.capital_province_id,
            "controlled_provinces": self.controlled_provinces,
            "relations": self.relations
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Daimyo':
        """辞書から復元（ロード用）"""
        daimyo = cls(
            daimyo_id=data["id"],
            name=data["name"],
            clan_name=data["clan_name"],
            is_player=data.get("is_player", False)
        )

        # 全ての属性を復元
        daimyo.portrait = data.get("portrait", f"{data['clan_name']}.png")
        daimyo.is_alive = data.get("is_alive", True)
        daimyo.age = data.get("age", 30)
        daimyo.health = data.get("health", 90)
        daimyo.ambition = data.get("ambition", 70)
        daimyo.luck = data.get("luck", 50)
        daimyo.charm = data.get("charm", 60)
        daimyo.intelligence = data.get("intelligence", 70)
        daimyo.war_skill = data.get("war_skill", 60)
        daimyo.successor_id = data.get("successor_id")
        daimyo.capital_province_id = data.get("capital_province_id")
        daimyo.controlled_provinces = data.get("controlled_provinces", [])
        daimyo.relations = data.get("relations", {})

        return daimyo

    def __repr__(self) -> str:
        return f"Daimyo({self.id}: {self.clan_name} {self.name}, Provinces: {len(self.controlled_provinces)}, Player: {self.is_player})"
