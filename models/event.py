"""
Event（イベント）モデル
ゲームイベントとその効果を管理
"""
from enum import Enum
from typing import Optional, Dict, List


class EventType(Enum):
    """イベントタイプ"""
    NATURAL_DISASTER = "natural_disaster"  # 自然災害
    ECONOMIC = "economic"  # 経済
    SOCIAL = "social"  # 社会
    MILITARY = "military"  # 軍事
    DIPLOMATIC = "diplomatic"  # 外交


class EventChoice:
    """イベント選択肢"""

    def __init__(self, choice_id: str, text: str, cost: Dict, effect: Dict):
        self.choice_id = choice_id
        self.text = text
        self.cost = cost  # {"gold": 200, "rice": 100}
        self.effect = effect  # {"loyalty_change": 10}

    def __repr__(self) -> str:
        return f"EventChoice({self.choice_id}: {self.text})"


class GameEvent:
    """ゲームイベントクラス"""

    def __init__(self, event_id: str, event_type: EventType,
                 name: str, description: str):
        self.event_id = event_id
        self.event_type = event_type
        self.name = name
        self.description = description

        # 発生条件
        self.probability = 0.0  # 0.0～1.0
        self.season_restriction = None  # List[str] or None
        self.terrain_restriction = None  # List[str] or None
        self.trigger_conditions = {}  # dict of conditions

        # 効果
        self.effects = {}  # {"rice_multiplier": 0.7, "gold": -200, ...}
        self.mitigation = {}  # 軽減条件

        # 選択肢（10%のイベントのみ）
        self.choices = []  # List[EventChoice]

    def has_choices(self) -> bool:
        """選択肢があるか"""
        return len(self.choices) > 0

    def __repr__(self) -> str:
        return f"GameEvent({self.event_id}: {self.name}, prob={self.probability})"
