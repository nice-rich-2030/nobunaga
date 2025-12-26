"""
ScreenManager - 画面遷移管理
各画面の状態を管理
"""
from enum import Enum


class ScreenType(Enum):
    """画面タイプの列挙"""
    MAIN_MAP = "main_map"
    PROVINCE_DETAIL = "province_detail"
    BATTLE = "battle"
    DIPLOMACY = "diplomacy"
    STATUS = "status"


class ScreenManager:
    """画面遷移を管理するクラス"""

    def __init__(self):
        self.current_screen = ScreenType.MAIN_MAP
        self.screen_stack = []  # 画面履歴スタック
        self.screen_data = {}  # 画面間でデータを渡すための辞書

    def push_screen(self, screen_type: ScreenType, data: dict = None):
        """新しい画面に遷移（現在の画面をスタックに保存）"""
        self.screen_stack.append(self.current_screen)
        self.current_screen = screen_type

        if data:
            self.screen_data = data.copy()

    def pop_screen(self):
        """前の画面に戻る"""
        if self.screen_stack:
            self.current_screen = self.screen_stack.pop()
            self.screen_data.clear()
            return True
        return False

    def set_screen(self, screen_type: ScreenType, data: dict = None):
        """画面を直接設定（スタックをクリア）"""
        self.screen_stack.clear()
        self.current_screen = screen_type

        if data:
            self.screen_data = data.copy()
        else:
            self.screen_data.clear()

    def get_current_screen(self) -> ScreenType:
        """現在の画面タイプを取得"""
        return self.current_screen

    def get_screen_data(self, key: str, default=None):
        """画面データを取得"""
        return self.screen_data.get(key, default)

    def set_screen_data(self, key: str, value):
        """画面データを設定"""
        self.screen_data[key] = value

    def is_main_map(self) -> bool:
        """メインマップ画面か"""
        return self.current_screen == ScreenType.MAIN_MAP

    def is_province_detail(self) -> bool:
        """領地詳細画面か"""
        return self.current_screen == ScreenType.PROVINCE_DETAIL
