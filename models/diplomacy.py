"""
Diplomacy（外交）モデル
大名間の関係、条約、同盟を管理
"""
from typing import Optional
from enum import Enum


class RelationType(Enum):
    """外交関係のタイプ"""
    NEUTRAL = "neutral"  # 中立
    NON_AGGRESSION = "non_aggression"  # 不可侵条約
    ALLIANCE = "alliance"  # 同盟
    WAR = "war"  # 戦争状態


class DiplomaticRelation:
    """外交関係クラス - 2つの大名間の関係"""

    def __init__(self, daimyo_a_id: int, daimyo_b_id: int):
        # ========================================
        # 関係する大名
        # ========================================
        self.daimyo1_id = daimyo_a_id  # diplomacy systemで使用
        self.daimyo2_id = daimyo_b_id  # diplomacy systemで使用
        self.daimyo_a_id = daimyo_a_id
        self.daimyo_b_id = daimyo_b_id

        # ========================================
        # 関係値（-100〜+100）
        # ========================================
        self.relation_value = 0  # 中立からスタート

        # ========================================
        # 関係タイプと条約期間
        # ========================================
        self.relation_type = RelationType.NEUTRAL
        self.treaty_duration = 0  # 条約残り期間（ターン数）

        # ========================================
        # 条約（旧形式、後方互換性のため残す）
        # ========================================
        self.has_non_aggression_pact = False
        self.pact_expires_turn: Optional[int] = None

        self.has_alliance = False
        self.alliance_expires_turn: Optional[int] = None

        # ========================================
        # 婚姻
        # ========================================
        self.marriage_connection = False

        # ========================================
        # 履歴
        # ========================================
        self.wars_fought = 0
        self.gifts_exchanged = 0
        self.betrayals = 0  # 条約破棄回数

    def update_relation(self, change: int):
        """関係値を更新（-100〜+100に制限）"""
        self.relation_value = max(-100, min(100, self.relation_value + change))

    def set_relation(self, value: int):
        """関係値を設定"""
        self.relation_value = max(-100, min(100, value))

    def is_at_war(self) -> bool:
        """戦争状態か（関係値が大きくマイナス）"""
        return self.relation_value < -50

    def is_friendly(self) -> bool:
        """友好的か"""
        return self.relation_value > 0

    def is_hostile(self) -> bool:
        """敵対的か"""
        return self.relation_value < 0

    def can_form_alliance(self) -> bool:
        """同盟を結べるか"""
        from config import ALLIANCE_RELATION_THRESHOLD
        return self.relation_value >= ALLIANCE_RELATION_THRESHOLD and not self.has_alliance

    def can_form_pact(self) -> bool:
        """不可侵条約を結べるか"""
        from config import NON_AGGRESSION_RELATION_THRESHOLD
        return self.relation_value >= NON_AGGRESSION_RELATION_THRESHOLD and not self.has_non_aggression_pact

    def form_non_aggression_pact(self, current_turn: int, duration: int):
        """不可侵条約を締結"""
        self.has_non_aggression_pact = True
        self.pact_expires_turn = current_turn + duration

    def form_alliance(self, current_turn: int, duration: int):
        """同盟を締結"""
        self.has_alliance = True
        self.alliance_expires_turn = current_turn + duration
        # 同盟締結時は不可侵条約も自動的に締結
        if not self.has_non_aggression_pact:
            self.form_non_aggression_pact(current_turn, duration)

    def break_pact(self):
        """不可侵条約を破棄"""
        if self.has_non_aggression_pact:
            self.has_non_aggression_pact = False
            self.pact_expires_turn = None
            self.betrayals += 1

    def break_alliance(self):
        """同盟を破棄"""
        if self.has_alliance:
            self.has_alliance = False
            self.alliance_expires_turn = None
            self.betrayals += 1

    def arrange_marriage(self):
        """婚姻を結ぶ"""
        self.marriage_connection = True
        # 婚姻は関係を大きく改善
        self.update_relation(20)

    def declare_war(self):
        """宣戦布告"""
        self.wars_fought += 1
        # 条約を破棄
        if self.has_non_aggression_pact or self.has_alliance:
            if self.has_alliance:
                self.break_alliance()
            if self.has_non_aggression_pact:
                self.break_pact()

    def send_gift(self):
        """贈物を送る"""
        self.gifts_exchanged += 1

    def check_treaty_expiration(self, current_turn: int):
        """条約の期限切れをチェック"""
        if self.has_non_aggression_pact and self.pact_expires_turn:
            if current_turn >= self.pact_expires_turn:
                self.has_non_aggression_pact = False
                self.pact_expires_turn = None

        if self.has_alliance and self.alliance_expires_turn:
            if current_turn >= self.alliance_expires_turn:
                self.has_alliance = False
                self.alliance_expires_turn = None

    def to_dict(self) -> dict:
        """辞書形式に変換（セーブ用）"""
        return {
            "daimyo_a_id": self.daimyo_a_id,
            "daimyo_b_id": self.daimyo_b_id,
            "relation_value": self.relation_value,
            "has_non_aggression_pact": self.has_non_aggression_pact,
            "pact_expires_turn": self.pact_expires_turn,
            "has_alliance": self.has_alliance,
            "alliance_expires_turn": self.alliance_expires_turn,
            "marriage_connection": self.marriage_connection,
            "wars_fought": self.wars_fought,
            "gifts_exchanged": self.gifts_exchanged,
            "betrayals": self.betrayals
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DiplomaticRelation':
        """辞書から復元（ロード用）"""
        relation = cls(
            daimyo_a_id=data["daimyo_a_id"],
            daimyo_b_id=data["daimyo_b_id"]
        )

        relation.relation_value = data.get("relation_value", 0)
        relation.has_non_aggression_pact = data.get("has_non_aggression_pact", False)
        relation.pact_expires_turn = data.get("pact_expires_turn")
        relation.has_alliance = data.get("has_alliance", False)
        relation.alliance_expires_turn = data.get("alliance_expires_turn")
        relation.marriage_connection = data.get("marriage_connection", False)
        relation.wars_fought = data.get("wars_fought", 0)
        relation.gifts_exchanged = data.get("gifts_exchanged", 0)
        relation.betrayals = data.get("betrayals", 0)

        return relation

    def __repr__(self) -> str:
        status = []
        if self.has_alliance:
            status.append("Alliance")
        if self.has_non_aggression_pact:
            status.append("Pact")
        if self.marriage_connection:
            status.append("Marriage")
        status_str = ", ".join(status) if status else "None"

        return f"DiplomaticRelation({self.daimyo_a_id}<->{self.daimyo_b_id}: {self.relation_value}, {status_str})"
