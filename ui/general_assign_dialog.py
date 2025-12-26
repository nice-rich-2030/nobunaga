"""
GeneralAssignDialog - 将軍配置ダイアログ
将軍を領地に配置または配置解除するUI
"""
import pygame
import config
from typing import Optional, Callable, List
from models.province import Province
from models.general import General


class GeneralAssignDialog:
    """将軍配置ダイアログクラス"""

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont('meiryo', 14)

        self.is_visible = False
        self.province = None
        self.available_generals: List[General] = []
        self.current_general = None  # 現在配置されている将軍
        self.selected_general_index = -1  # -1は配置解除

        # コールバック
        self.on_confirm_callback: Optional[Callable] = None
        self.on_cancel_callback: Optional[Callable] = None

        # ダイアログのサイズ
        self.dialog_width = 600
        self.dialog_height = 500
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
        self.general_rects = []

    def show(
        self,
        province: Province,
        available_generals: List[General],
        on_confirm: Callable,
        on_cancel: Callable,
        current_general: Optional[General] = None
    ):
        """ダイアログを表示"""
        self.is_visible = True
        self.province = province
        self.available_generals = available_generals
        self.current_general = current_general
        self.selected_general_index = -1  # デフォルトは配置解除
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel

    def hide(self):
        """ダイアログを非表示"""
        self.is_visible = False
        self.province = None
        self.available_generals = []

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
                self.selected_general_index = max(-1, self.selected_general_index - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_general_index = min(len(self.available_generals) - 1, self.selected_general_index + 1)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # 将軍クリック
            for i, rect in enumerate(self.general_rects):
                if rect.collidepoint(mouse_pos):
                    self.selected_general_index = i - 1  # -1は配置解除、0以降は将軍
                    return

            # ボタンクリック
            if self.confirm_button_rect and self.confirm_button_rect.collidepoint(mouse_pos):
                self._confirm()
            elif self.cancel_button_rect and self.cancel_button_rect.collidepoint(mouse_pos):
                self._cancel()

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

        # タイトル
        title_text = f"将軍配置 - {self.province.name}"
        title_surface = self.font.render(title_text, True, config.UI_HIGHLIGHT_COLOR)
        title_rect = title_surface.get_rect(center=(self.dialog_x + self.dialog_width // 2, self.dialog_y + 30))
        self.screen.blit(title_surface, title_rect)

        # 現在の将軍情報
        current_y = self.dialog_y + 70
        current_text = "現在の守将: "
        if self.current_general:
            current_text += f"{self.current_general.name} (武{self.current_general.war_skill} 政{self.current_general.politics})"
        else:
            current_text += "なし"

        current_surface = self.small_font.render(current_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(current_surface, (self.dialog_x + 20, current_y))

        # 選択肢の表示
        choice_y = current_y + 40
        choice_text = self.small_font.render("選択:", True, config.UI_TEXT_COLOR)
        self.screen.blit(choice_text, (self.dialog_x + 20, choice_y))

        choice_y += 25
        self.general_rects = []

        # 配置解除オプション
        rect = pygame.Rect(self.dialog_x + 30, choice_y, 540, 30)
        self.general_rects.append(rect)

        # 選択されている場合はハイライト
        if self.selected_general_index == -1:
            pygame.draw.rect(self.screen, (80, 70, 60), rect)
        else:
            pygame.draw.rect(self.screen, (50, 45, 40), rect)

        pygame.draw.rect(self.screen, (100, 90, 80), rect, 1)

        unassign_text = "配置解除"
        unassign_surface = self.small_font.render(unassign_text, True, (240, 240, 240))
        self.screen.blit(unassign_surface, (rect.x + 10, rect.y + 8))

        choice_y += 35

        # 利用可能な将軍リスト
        for i, general in enumerate(self.available_generals):
            rect = pygame.Rect(self.dialog_x + 30, choice_y, 540, 30)
            self.general_rects.append(rect)

            # 選択されている場合はハイライト
            if i == self.selected_general_index:
                pygame.draw.rect(self.screen, (80, 70, 60), rect)
            else:
                pygame.draw.rect(self.screen, (50, 45, 40), rect)

            pygame.draw.rect(self.screen, (100, 90, 80), rect, 1)

            # 将軍情報を表示
            general_text = f"{general.name} - 武{general.war_skill} 統{general.leadership} 政{general.politics} 知{general.intelligence}"
            general_surface = self.small_font.render(general_text, True, (240, 240, 240))
            self.screen.blit(general_surface, (rect.x + 10, rect.y + 8))

            choice_y += 35

        # 確定・キャンセルボタン
        button_y = self.dialog_y + self.dialog_height - 80
        self.confirm_button_rect = pygame.Rect(self.dialog_x + 150, button_y, 120, 40)
        self.cancel_button_rect = pygame.Rect(self.dialog_x + 330, button_y, 120, 40)

        # マウスオーバー判定
        mouse_pos = pygame.mouse.get_pos()

        # 確定ボタン
        confirm_color = self.button_hover_color if self.confirm_button_rect.collidepoint(mouse_pos) else self.button_color
        pygame.draw.rect(self.screen, confirm_color, self.confirm_button_rect)
        pygame.draw.rect(self.screen, (100, 90, 80), self.confirm_button_rect, 2)
        confirm_text = self.font.render("確定", True, (240, 240, 240))
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
        help_text = "↑↓: 選択 | Enter: 確定 | Esc: キャンセル"
        help_surface = self.small_font.render(help_text, True, (150, 150, 150))
        help_rect = help_surface.get_rect(center=(self.dialog_x + self.dialog_width // 2, self.dialog_y + self.dialog_height - 15))
        self.screen.blit(help_surface, help_rect)

    def _confirm(self):
        """配置を確定"""
        if self.on_confirm_callback:
            # selected_general_index == -1は配置解除、0以降は将軍選択
            if self.selected_general_index == -1:
                self.on_confirm_callback(None)
            else:
                general = self.available_generals[self.selected_general_index]
                self.on_confirm_callback(general)

        self.hide()

    def _cancel(self):
        """キャンセル"""
        if self.on_cancel_callback:
            self.on_cancel_callback()

        self.hide()
