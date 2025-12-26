"""
イベントシステム - ランダムイベントとトリガーイベントの管理
"""
import random
import json
from typing import List, Tuple, Optional
from models.event import GameEvent, EventType, EventChoice


class EventSystem:
    """イベントシステム"""

    def __init__(self, game_state):
        self.game_state = game_state
        self.events = []  # List[GameEvent]
        self.event_history = []  # イベント履歴
        self.general_pool = None  # GeneralPoolは後で設定

    def load_events_from_file(self, events_file_path: str):
        """events.jsonからイベントを読み込む"""
        try:
            with open(events_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.load_events(data)
        except FileNotFoundError:
            print(f"Warning: Events file not found: {events_file_path}")
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse events file: {e}")

    def load_events(self, events_data: dict):
        """イベントデータを読み込んでGameEventオブジェクトを作成"""
        if "events" not in events_data:
            return

        for event_data in events_data["events"]:
            event = self._create_event_from_dict(event_data)
            if event:
                self.events.append(event)

    def _create_event_from_dict(self, data: dict) -> Optional[GameEvent]:
        """辞書からGameEventオブジェクトを作成"""
        try:
            # EventTypeに変換
            event_type_str = data.get("type", "economic")
            event_type = EventType(event_type_str)

            # 基本情報
            event = GameEvent(
                event_id=data["id"],
                event_type=event_type,
                name=data["name"],
                description=data["description"]
            )

            # 発生条件
            event.probability = data.get("probability", 0.0)
            event.season_restriction = data.get("season_restriction")
            event.terrain_restriction = data.get("terrain_restriction")
            event.trigger_conditions = data.get("trigger_conditions", {})

            # 効果
            event.effects = data.get("effects", {})
            event.mitigation = data.get("mitigation", {})

            # 選択肢
            choices_data = data.get("choices", [])
            for choice_data in choices_data:
                choice = EventChoice(
                    choice_id=choice_data["id"],
                    text=choice_data["text"],
                    cost=choice_data.get("cost", {}),
                    effect=choice_data.get("effect", {})
                )
                event.choices.append(choice)

            return event

        except (KeyError, ValueError) as e:
            print(f"Error creating event from data: {e}")
            return None

    def check_events_for_turn(self, current_season: str) -> List[Tuple[GameEvent, any]]:
        """今ターンで発生するイベントをチェック
        Returns: List[(event, province)]
        """
        triggered_events = []
        triggered_provinces = set()  # 同じ領地で重複発生を防ぐ

        # 各領地に対してイベントチェック
        for province in self.game_state.provinces.values():
            # 既にこの領地でイベントが発生している場合はスキップ
            if province.id in triggered_provinces:
                continue

            # 各イベントをチェック
            for event in self.events:
                if self._should_trigger(event, province, current_season):
                    triggered_events.append((event, province))
                    triggered_provinces.add(province.id)
                    break  # 1領地につき1イベントまで

        return triggered_events

    def _should_trigger(self, event: GameEvent, province, season: str) -> bool:
        """イベントが発生すべきか判定"""
        # 季節チェック
        if event.season_restriction and season not in event.season_restriction:
            return False

        # 地形チェック
        if event.terrain_restriction and province.terrain not in event.terrain_restriction:
            return False

        # トリガー条件チェック
        if event.trigger_conditions:
            if not self._check_trigger_conditions(event, province):
                return False

        # 確率判定
        return random.random() < event.probability

    def _check_trigger_conditions(self, event: GameEvent, province) -> bool:
        """トリガー条件をチェック"""
        conditions = event.trigger_conditions

        # 忠誠度の最大値チェック
        if "peasant_loyalty_max" in conditions:
            if province.peasant_loyalty > conditions["peasant_loyalty_max"]:
                return False

        # 忠誠度の最小値チェック
        if "peasant_loyalty_min" in conditions:
            if province.peasant_loyalty < conditions["peasant_loyalty_min"]:
                return False

        # 町レベルチェック
        if "town_level_min" in conditions:
            if province.town_level < conditions["town_level_min"]:
                return False

        # 兵士数チェック
        if "soldiers_max" in conditions:
            if province.soldiers > conditions["soldiers_max"]:
                return False

        # その他の条件は将来実装
        return True

    def apply_event_effect(self, event: GameEvent, province,
                          choice_id: Optional[str] = None):
        """イベント効果を適用"""
        effects = event.effects.copy()
        selected_choice = None

        # 選択肢による効果の上書き
        if choice_id and event.choices:
            for choice in event.choices:
                if choice.choice_id == choice_id:
                    selected_choice = choice
                    effects.update(choice.effect)
                    # コストを差し引く
                    if "gold" in choice.cost:
                        province.add_gold(-choice.cost["gold"])
                    if "rice" in choice.cost:
                        province.add_rice(-choice.cost["rice"])
                    break

        # 軽減条件のチェック
        if event.mitigation:
            self._apply_mitigation(event, province, effects)

        # 将軍登用の特殊処理
        if selected_choice and "recruit_general" in selected_choice.effect:
            general_id = selected_choice.effect["recruit_general"]
            if self.general_pool and general_id:
                self.general_pool.recruit_general(general_id, province.owner_daimyo_id)
                # 指定された領地に配置
                general = self.game_state.get_general(general_id)
                if general and "assign_to_province" in selected_choice.effect:
                    province.governor_general_id = general.id
                    general.assign_to_province(province.id)

        # 効果を適用
        self._apply_effects_to_province(province, effects)

        # 履歴に記録
        self.event_history.append({
            "turn": self.game_state.current_turn,
            "season": self.game_state.get_season_name(),
            "event_id": event.event_id,
            "province_id": province.id,
            "choice": choice_id,
            "effects": effects
        })

    def _apply_mitigation(self, event: GameEvent, province, effects: dict):
        """軽減条件を適用"""
        attr = event.mitigation.get("attribute")
        threshold = event.mitigation.get("threshold", 0)
        reduction = event.mitigation.get("reduction_factor", 1.0)

        # 治水レベルによる被害軽減
        if attr == "flood_control" and province.flood_control >= threshold:
            # rice_multiplierの軽減
            if "rice_multiplier" in effects:
                # 例: 0.7 → 0.85（被害を半減）
                original = effects["rice_multiplier"]
                diff = 1.0 - original
                effects["rice_multiplier"] = 1.0 - (diff * reduction)

            # 損失系の軽減
            for key in list(effects.keys()):
                if "loss" in key or key in ["peasants", "soldiers", "gold", "rice"]:
                    if effects[key] < 0:  # マイナス値（損失）の場合
                        effects[key] = int(effects[key] * reduction)

            # loyalty_changeの軽減（マイナスの場合）
            if "loyalty_change" in effects and effects["loyalty_change"] < 0:
                effects["loyalty_change"] = int(effects["loyalty_change"] * reduction)

    def _apply_effects_to_province(self, province, effects: dict):
        """効果を領地に適用"""
        # 米の増減（multiplier）
        if "rice_multiplier" in effects:
            rice_production = province.calculate_rice_production()
            rice_change = int(rice_production * (effects["rice_multiplier"] - 1.0))
            province.add_rice(rice_change)

        # 米の増減（直接）
        if "rice" in effects:
            province.add_rice(effects["rice"])

        # 金の増減
        if "gold" in effects:
            province.add_gold(effects["gold"])

        # 農民の増減
        if "peasant_loss" in effects:
            province.peasants = max(0, province.peasants + effects["peasant_loss"])

        if "peasants" in effects:
            province.peasants = max(0, province.peasants + effects["peasants"])

        # 兵士の増減
        if "soldier_loss" in effects:
            province.soldiers = max(0, province.soldiers + effects["soldier_loss"])

        if "soldiers" in effects:
            province.soldiers = max(0, province.soldiers + effects["soldiers"])

        # 兵士の割合減少
        if "soldier_loss_percent" in effects:
            loss_count = int(province.soldiers * abs(effects["soldier_loss_percent"]))
            province.soldiers = max(0, province.soldiers - loss_count)

        # 忠誠度
        if "loyalty_change" in effects:
            province.peasant_loyalty = max(0, min(100,
                province.peasant_loyalty + effects["loyalty_change"]))

        # 開発レベル
        if "development_level" in effects:
            province.development_level = max(0, province.development_level + effects["development_level"])

        # 町レベル
        if "town_level" in effects:
            province.town_level = max(0, province.town_level + effects["town_level"])

    def get_recent_events(self, count: int = 10) -> List[dict]:
        """最近のイベント履歴を取得"""
        return self.event_history[-count:] if self.event_history else []
