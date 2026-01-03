"""
TransferDialog - リソース転送ダイアログ
隣接する自領地へのリソース転送UI
"""
import pygame
import config
from typing import Optional, Callable, List
from models.province import Province


class TransferDialog:
    """リソース転送ダイアログクラス"""

    def __init__(self, screen, font, sound_manager=None):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont('meiryo', 14)
        self.sound_manager = sound_manager

        self.is_visible = False
        self.from_province = None
        self.target_provinces: List[Province] = []
        self.selected_target_index = 0
        self.resource_type = ""  # "soldiers", "gold", "rice"
        self.transfer_amount = 0
        self.max_amount = 0

        # コールバック
        self.on_confirm_callback: Optional[Callable] = None
        self.on_cancel_callback: Optional[Callable] = None

        # ダイアログのサイズ
        self.dialog_width = 500
        self.dialog_height = 450  # 高さを増やしてヘルプテキスト用スペースを確保
        self.dialog_x = (config.SCREEN_WIDTH - self.dialog_width) // 2
        self.dialog_y = (config.SCREEN_HEIGHT - self.dialog_height) // 2

        # 色設定
        self.bg_color = (35, 30, 25)
        self.border_color = (180, 140, 100)
        self.button_color = (70, 60, 50)
        self.button_hover_color = (90, 75, 60)

        # ボタン状態
        self.confirm_button_rect = None
        self.cancel_button_rect = None
        self.increase_10_button_rect = None
        self.decrease_10_button_rect = None
        self.increase_50_button_rect = None
        self.decrease_50_button_rect = None
        self.increase_100_button_rect = None
        self.decrease_100_button_rect = None
        self.target_rects = []

    def show(
        self,
        from_province: Province,
        target_provinces: List[Province],
        resource_type: str,
        max_amount: int,
        on_confirm: Callable,
        on_cancel: Callable
    ):
        """ダイアログを表示"""
        self.is_visible = True
        self.from_province = from_province
        self.target_provinces = target_provinces
        self.resource_type = resource_type
        self.max_amount = max_amount
        self.transfer_amount = min(10, max_amount)  # 初期値は10
        self.selected_target_index = 0
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel

    def hide(self):
        """ダイアログを非表示"""
        self.is_visible = False
        self.from_province = None
        self.target_provinces = []

    def handle_event(self, event):
        """イベント処理"""
        if not self.is_visible:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._cancel()
            elif event.key == pygame.K_RETURN:
                self._confirm()
            elif event.key == pygame.K_UP:
                self.selected_target_index = max(0, self.selected_target_index - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_target_index = min(len(self.target_provinces) - 1, self.selected_target_index + 1)
            elif event.key == pygame.K_LEFT:
                self._decrease_amount(1)
            elif event.key == pygame.K_RIGHT:
                self._increase_amount(1)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # 転送先クリック
            for i, rect in enumerate(self.target_rects):
                if rect.collidepoint(mouse_pos):
                    self.selected_target_index = i
                    return

            # ボタンクリック
            if self.confirm_button_rect and self.confirm_button_rect.collidepoint(mouse_pos):
                self._confirm()
            elif self.cancel_button_rect and self.cancel_button_rect.collidepoint(mouse_pos):
                self._cancel()
            elif self.increase_100_button_rect and self.increase_100_button_rect.collidepoint(mouse_pos):
                self._increase_amount(100)
            elif self.decrease_100_button_rect and self.decrease_100_button_rect.collidepoint(mouse_pos):
                self._decrease_amount(100)
            elif self.increase_50_button_rect and self.increase_50_button_rect.collidepoint(mouse_pos):
                self._increase_amount(50)
            elif self.decrease_50_button_rect and self.decrease_50_button_rect.collidepoint(mouse_pos):
                self._decrease_amount(50)
            elif self.increase_10_button_rect and self.increase_10_button_rect.collidepoint(mouse_pos):
                self._increase_amount(10)
            elif self.decrease_10_button_rect and self.decrease_10_button_rect.collidepoint(mouse_pos):
                self._decrease_amount(10)

    def draw(self):
        """ダイアログを描画"""
        if not self.is_visible:
            return

        # 半透明の背景
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # ダイアログの背景
        pygame.draw.rect(self.screen, self.bg_color,
                        (self.dialog_x, self.dialog_y, self.dialog_width, self.dialog_height))
        pygame.draw.rect(self.screen, self.border_color,
                        (self.dialog_x, self.dialog_y, self.dialog_width, self.dialog_height), 3)

        # リソース名の表示
        resource_names = {
            "soldiers": "兵士",
            "gold": "金",
            "rice": "米"
        }
        resource_name = resource_names.get(self.resource_type, "")

        # タイトル
        title_text = f"{resource_name}の転送"
        title_surface = self.font.render(title_text, True, config.UI_HIGHLIGHT_COLOR)
        title_rect = title_surface.get_rect(center=(self.dialog_x + self.dialog_width // 2, self.dialog_y + 30))
        self.screen.blit(title_surface, title_rect)

        # 転送元の表示
        from_text = f"転送元: {self.from_province.name}"
        from_surface = self.small_font.render(from_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(from_surface, (self.dialog_x + 20, self.dialog_y + 70))

        # 転送先の選択
        target_y = self.dialog_y + 100
        target_text = self.small_font.render("転送先:", True, config.UI_TEXT_COLOR)
        self.screen.blit(target_text, (self.dialog_x + 20, target_y))

        target_y += 25
        self.target_rects = []

        for i, province in enumerate(self.target_provinces):
            rect = pygame.Rect(self.dialog_x + 30, target_y, 440, 25)
            self.target_rects.append(rect)

            # 選択された領地をハイライト
            if i == self.selected_target_index:
                pygame.draw.rect(self.screen, (80, 70, 60), rect)
            else:
                pygame.draw.rect(self.screen, (50, 45, 40), rect)

            pygame.draw.rect(self.screen, (100, 90, 80), rect, 1)

            # 領地名を表示
            province_text = f"{province.name} (兵{province.soldiers}, 金{province.gold}, 米{province.rice})"
            province_surface = self.small_font.render(province_text, True, (240, 240, 240))
            self.screen.blit(province_surface, (rect.x + 10, rect.y + 5))

            target_y += 30

        # 転送量の設定
        amount_y = target_y + 20
        amount_text = self.small_font.render(f"転送量: {self.transfer_amount} / {self.max_amount}", True, config.UI_TEXT_COLOR)
        self.screen.blit(amount_text, (self.dialog_x + 20, amount_y))

        # 兵士転送の場合は補足説明を追加
        if self.resource_type == "soldiers":
            note_y = amount_y + 20
            note_text = self.small_font.render("※守備のため最低10人を残します", True, (180, 180, 180))
            self.screen.blit(note_text, (self.dialog_x + 20, note_y))
            amount_y = note_y  # ボタンの位置を調整

        # 増減ボタン（-100, -50, -10, +10, +50, +100）
        button_y = amount_y + 30
        button_width = 60
        button_spacing = 5
        start_x = self.dialog_x + 40  # 左端から開始

        # マウスオーバー判定
        mouse_pos = pygame.mouse.get_pos()

        # -100 ボタン
        self.decrease_100_button_rect = pygame.Rect(start_x, button_y, button_width, 30)
        dec100_color = self.button_hover_color if self.decrease_100_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, dec100_color, self.decrease_100_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.decrease_100_button_rect, 2)
        dec100_text = self.small_font.render("-100", True, (240, 240, 240))
        dec100_rect = dec100_text.get_rect(center=self.decrease_100_button_rect.center)
        self.screen.blit(dec100_text, dec100_rect)

        # -50 ボタン
        self.decrease_50_button_rect = pygame.Rect(start_x + button_width + button_spacing, button_y, button_width, 30)
        dec50_color = self.button_hover_color if self.decrease_50_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, dec50_color, self.decrease_50_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.decrease_50_button_rect, 2)
        dec50_text = self.small_font.render("-50", True, (240, 240, 240))
        dec50_rect = dec50_text.get_rect(center=self.decrease_50_button_rect.center)
        self.screen.blit(dec50_text, dec50_rect)

        # -10 ボタン
        self.decrease_10_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 2, button_y, button_width, 30)
        dec10_color = self.button_hover_color if self.decrease_10_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, dec10_color, self.decrease_10_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.decrease_10_button_rect, 2)
        dec10_text = self.small_font.render("-10", True, (240, 240, 240))
        dec10_rect = dec10_text.get_rect(center=self.decrease_10_button_rect.center)
        self.screen.blit(dec10_text, dec10_rect)

        # +10 ボタン
        self.increase_10_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 3, button_y, button_width, 30)
        inc10_color = self.button_hover_color if self.increase_10_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, inc10_color, self.increase_10_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.increase_10_button_rect, 2)
        inc10_text = self.small_font.render("+10", True, (240, 240, 240))
        inc10_rect = inc10_text.get_rect(center=self.increase_10_button_rect.center)
        self.screen.blit(inc10_text, inc10_rect)

        # +50 ボタン
        self.increase_50_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 4, button_y, button_width, 30)
        inc50_color = self.button_hover_color if self.increase_50_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, inc50_color, self.increase_50_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.increase_50_button_rect, 2)
        inc50_text = self.small_font.render("+50", True, (240, 240, 240))
        inc50_rect = inc50_text.get_rect(center=self.increase_50_button_rect.center)
        self.screen.blit(inc50_text, inc50_rect)

        # +100 ボタン
        self.increase_100_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 5, button_y, button_width, 30)
        inc100_color = self.button_hover_color if self.increase_100_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, inc100_color, self.increase_100_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.increase_100_button_rect, 2)
        inc100_text = self.small_font.render("+100", True, (240, 240, 240))
        inc100_rect = inc100_text.get_rect(center=self.increase_100_button_rect.center)
        self.screen.blit(inc100_text, inc100_rect)

        # 確定・キャンセルボタン
        button_y = self.dialog_y + self.dialog_height - 80  # ヘルプテキスト用のスペースを確保
        self.confirm_button_rect = pygame.Rect(self.dialog_x + 100, button_y, 120, 40)
        self.cancel_button_rect = pygame.Rect(self.dialog_x + 280, button_y, 120, 40)

        # 確定ボタン
        confirm_color = self.button_hover_color if self.confirm_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, confirm_color, self.confirm_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.confirm_button_rect, 2)
        confirm_text = self.font.render("転送", True, (240, 240, 240))
        confirm_rect = confirm_text.get_rect(center=self.confirm_button_rect.center)
        self.screen.blit(confirm_text, confirm_rect)

        # キャンセルボタン
        cancel_color = self.button_hover_color if self.cancel_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, cancel_color, self.cancel_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.cancel_button_rect, 2)
        cancel_text = self.font.render("キャンセル", True, (240, 240, 240))
        cancel_rect = cancel_text.get_rect(center=self.cancel_button_rect.center)
        self.screen.blit(cancel_text, cancel_rect)

        # ヘルプテキスト
        help_text = "↑↓: 転送先選択 | ←→: 転送量調整 | Enter: 転送 | Esc: キャンセル"
        help_surface = self.small_font.render(help_text, True, (150, 150, 150))
        help_rect = help_surface.get_rect(center=(self.dialog_x + self.dialog_width // 2, self.dialog_y + self.dialog_height - 15))
        self.screen.blit(help_surface, help_rect)

    def _increase_amount(self, delta):
        """転送量を増やす"""
        self.transfer_amount = min(self.max_amount, self.transfer_amount + delta)

    def _decrease_amount(self, delta):
        """転送量を減らす"""
        self.transfer_amount = max(1, self.transfer_amount - delta)

    def _confirm(self):
        """転送を確定"""
        if len(self.target_provinces) == 0:
            return

        # 決定音再生
        if self.sound_manager:
            self.sound_manager.play("decide")

        target_province = self.target_provinces[self.selected_target_index]

        if self.on_confirm_callback:
            self.on_confirm_callback(target_province.id, self.transfer_amount)

        self.hide()

    def _cancel(self):
        """キャンセル"""
        # キャンセル音再生
        if self.sound_manager:
            self.sound_manager.play("cancel")

        if self.on_cancel_callback:
            self.on_cancel_callback()

        self.hide()
