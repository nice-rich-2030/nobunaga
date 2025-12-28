"""
EventDialog - イベント選択肢ダイアログ
選択肢のあるイベント用のモーダルダイアログ
"""
import pygame
import config
from ui.widgets import Button


class EventDialog:
    """イベント選択肢ダイアログ"""

    def __init__(self, screen, font, sound_manager=None):
        self.screen = screen
        self.font = font
        self.large_font = pygame.font.SysFont('meiryo', 24, bold=True)
        self.sound_manager = sound_manager

        # ダイアログの状態
        self.is_visible = False
        self.event = None
        self.province = None
        self.choice_buttons = []
        self.selected_choice = None

        # ダイアログのサイズと位置
        self.width = 600
        self.height = 400
        self.x = (config.SCREEN_WIDTH - self.width) // 2
        self.y = (config.SCREEN_HEIGHT - self.height) // 2

        # 色定義
        self.bg_color = (40, 30, 20)
        self.border_color = (180, 140, 100)
        self.overlay_color = (0, 0, 0, 180)

    def show(self, event, province, callback):
        """ダイアログを表示"""
        self.is_visible = True
        self.event = event
        self.province = province
        self.callback = callback
        self.selected_choice = None

        # 選択肢ボタンを作成
        self.choice_buttons.clear()
        if event.choices:
            button_y = self.y + 250
            for i, choice in enumerate(event.choices):
                btn = Button(
                    self.x + 50,
                    button_y + i * 60,
                    self.width - 100,
                    50,
                    choice.text,
                    lambda c=choice: self._on_choice_selected(c),
                    self.font
                )
                self.choice_buttons.append(btn)

    def hide(self):
        """ダイアログを非表示"""
        self.is_visible = False
        self.event = None
        self.province = None
        self.choice_buttons.clear()

    def _on_choice_selected(self, choice):
        """選択肢が選択された"""
        # 決定音再生
        if self.sound_manager:
            self.sound_manager.play("decide")

        self.selected_choice = choice
        if self.callback:
            self.callback(choice)
        self.hide()

    def handle_event(self, event_obj):
        """イベント処理"""
        if not self.is_visible:
            return False

        # ボタンのイベント処理
        for btn in self.choice_buttons:
            if btn.handle_event(event_obj):
                return True

        # ESCキーで閉じる（デフォルト選択）
        if event_obj.type == pygame.KEYDOWN and event_obj.key == pygame.K_ESCAPE:
            if self.event.choices:
                self._on_choice_selected(self.event.choices[0])
            return True

        return False

    def draw(self):
        """ダイアログを描画"""
        if not self.is_visible or not self.event:
            return

        # 半透明オーバーレイ
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # ダイアログ背景
        pygame.draw.rect(self.screen, self.bg_color,
                        (self.x, self.y, self.width, self.height))

        # 和風の枠線（二重枠）
        pygame.draw.rect(self.screen, self.border_color,
                        (self.x, self.y, self.width, self.height), 3)
        pygame.draw.rect(self.screen, self.border_color,
                        (self.x + 5, self.y + 5, self.width - 10, self.height - 10), 1)

        # イベント名（タイトル）
        title_text = self.large_font.render(self.event.name, True, (255, 220, 180))
        title_x = self.x + (self.width - title_text.get_width()) // 2
        self.screen.blit(title_text, (title_x, self.y + 20))

        # 区切り線
        pygame.draw.line(self.screen, self.border_color,
                        (self.x + 30, self.y + 60),
                        (self.x + self.width - 30, self.y + 60), 2)

        # イベント説明文
        description = self.event.description.format(province_name=self.province.name)
        desc_lines = self._wrap_text(description, self.width - 60)

        desc_y = self.y + 80
        for line in desc_lines:
            desc_surface = self.font.render(line, True, (220, 220, 220))
            self.screen.blit(desc_surface, (self.x + 30, desc_y))
            desc_y += 25

        # 効果の概要
        effects_y = desc_y + 20
        effects_text = self._format_effects()
        if effects_text:
            effects_surface = self.font.render(effects_text, True, (255, 200, 100))
            self.screen.blit(effects_surface, (self.x + 30, effects_y))

        # 選択肢ボタン
        for btn in self.choice_buttons:
            btn.draw(self.screen)

        # 操作説明
        help_text = "[ESC]でキャンセル（最初の選択肢を選択）"
        help_surface = self.font.render(help_text, True, (150, 150, 150))
        help_x = self.x + (self.width - help_surface.get_width()) // 2
        self.screen.blit(help_surface, (help_x, self.y + self.height - 30))

    def _wrap_text(self, text, max_width):
        """テキストを折り返す"""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            test_surface = self.font.render(test_line, True, (255, 255, 255))

            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.strip())

        return lines

    def _format_effects(self):
        """効果を簡潔にフォーマット"""
        if not self.event.effects:
            return ""

        effects = self.event.effects
        parts = []

        if "rice_multiplier" in effects:
            multiplier = effects["rice_multiplier"]
            if multiplier > 1.0:
                parts.append(f"米+{int((multiplier - 1.0) * 100)}%")
            else:
                parts.append(f"米{int((multiplier - 1.0) * 100)}%")

        if "gold" in effects:
            gold = effects["gold"]
            parts.append(f"金{gold:+d}")

        if "rice" in effects:
            rice = effects["rice"]
            parts.append(f"米{rice:+d}")

        if "peasant_loss" in effects:
            loss = effects["peasant_loss"]
            parts.append(f"農民{loss:+d}")

        if "soldier_loss" in effects:
            loss = effects["soldier_loss"]
            parts.append(f"兵士{loss:+d}")

        if "loyalty_change" in effects:
            change = effects["loyalty_change"]
            parts.append(f"忠誠度{change:+d}")

        return "効果: " + ", ".join(parts) if parts else ""
