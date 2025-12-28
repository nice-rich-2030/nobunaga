"""
UIウィジェット - 再利用可能なUIコンポーネント
"""
import pygame
import config


class Button:
    """ボタンウィジェット"""

    def __init__(self, x, y, width, height, text, font, callback=None, sound_manager=None, sound_type="decide"):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.callback = callback
        self.is_hovered = False
        self.is_enabled = True
        self.sound_manager = sound_manager
        self.sound_type = sound_type  # "decide", "battle", "cancel"

    def draw(self, surface):
        """ボタンを描画"""
        if not self.is_enabled:
            color = config.DARK_GRAY
            text_color = config.GRAY
        elif self.is_hovered:
            color = config.UI_HIGHLIGHT_COLOR
            text_color = config.BLACK
        else:
            color = config.UI_PANEL_COLOR
            text_color = config.UI_TEXT_COLOR

        # ボタン背景
        pygame.draw.rect(surface, color, self.rect)
        # ボタン枠
        pygame.draw.rect(surface, config.UI_BORDER_COLOR, self.rect, 2)

        # テキスト
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        """イベント処理"""
        if not self.is_enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.is_hovered = True  # クリック時にホバー状態を設定
                # 効果音再生
                if self.sound_manager:
                    self.sound_manager.play(self.sound_type)
                if self.callback:
                    self.callback()
                return True

        return False

    def set_enabled(self, enabled: bool):
        """有効/無効を設定"""
        self.is_enabled = enabled

    def set_position(self, x, y):
        """ボタンの位置を設定"""
        self.rect.x = x
        self.rect.y = y


class Panel:
    """パネルウィジェット"""

    def __init__(self, x, y, width, height, title="", font=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.font = font

    def draw(self, surface):
        """パネルを描画"""
        # 背景
        pygame.draw.rect(surface, config.UI_PANEL_COLOR, self.rect)
        # 枠
        pygame.draw.rect(surface, config.UI_BORDER_COLOR, self.rect, 3)

        # タイトル
        if self.title and self.font:
            title_surface = self.font.render(self.title, True, config.UI_HIGHLIGHT_COLOR)
            title_rect = title_surface.get_rect(
                centerx=self.rect.centerx,
                top=self.rect.top + 10
            )
            surface.blit(title_surface, title_rect)


class TextLabel:
    """テキストラベルウィジェット"""

    def __init__(self, x, y, text, font, color=None):
        self.x = x
        self.y = y
        self.text = text
        self.font = font
        self.color = color or config.UI_TEXT_COLOR

    def draw(self, surface):
        """ラベルを描画"""
        text_surface = self.font.render(self.text, True, self.color)
        surface.blit(text_surface, (self.x, self.y))

    def set_text(self, text):
        """テキストを変更"""
        self.text = text

    def set_color(self, color):
        """色を変更"""
        self.color = color


class ProgressBar:
    """プログレスバーウィジェット"""

    def __init__(self, x, y, width, height, max_value, current_value=0):
        self.rect = pygame.Rect(x, y, width, height)
        self.max_value = max_value
        self.current_value = current_value

    def draw(self, surface, font=None):
        """プログレスバーを描画"""
        # 背景
        pygame.draw.rect(surface, config.DARK_GRAY, self.rect)

        # プログレス
        if self.max_value > 0:
            progress_width = int((self.current_value / self.max_value) * self.rect.width)
            progress_rect = pygame.Rect(
                self.rect.x,
                self.rect.y,
                progress_width,
                self.rect.height
            )

            # 色を値に応じて変更
            if self.current_value / self.max_value > 0.7:
                color = config.STATUS_GOOD
            elif self.current_value / self.max_value > 0.3:
                color = config.STATUS_NEUTRAL
            else:
                color = config.STATUS_BAD

            pygame.draw.rect(surface, color, progress_rect)

        # 枠
        pygame.draw.rect(surface, config.UI_BORDER_COLOR, self.rect, 2)

        # テキスト（オプション）
        if font:
            text = f"{self.current_value}/{self.max_value}"
            text_surface = font.render(text, True, config.WHITE)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)

    def set_value(self, value):
        """現在値を設定"""
        self.current_value = max(0, min(self.max_value, value))


class ListBox:
    """リストボックスウィジェット"""

    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.items = []
        self.selected_index = -1
        self.scroll_offset = 0
        self.item_height = 30

    def add_item(self, text, data=None):
        """アイテムを追加"""
        self.items.append({"text": text, "data": data})

    def clear(self):
        """全アイテムをクリア"""
        self.items.clear()
        self.selected_index = -1
        self.scroll_offset = 0

    def draw(self, surface):
        """リストボックスを描画"""
        # 背景
        pygame.draw.rect(surface, config.UI_PANEL_COLOR, self.rect)

        # アイテム描画
        visible_items = self.rect.height // self.item_height
        for i in range(self.scroll_offset, min(len(self.items), self.scroll_offset + visible_items)):
            item = self.items[i]
            y_pos = self.rect.y + (i - self.scroll_offset) * self.item_height

            # 選択背景
            if i == self.selected_index:
                item_rect = pygame.Rect(self.rect.x, y_pos, self.rect.width, self.item_height)
                pygame.draw.rect(surface, config.UI_HIGHLIGHT_COLOR, item_rect)

            # テキスト
            text_color = config.BLACK if i == self.selected_index else config.UI_TEXT_COLOR
            text_surface = self.font.render(item["text"], True, text_color)
            surface.blit(text_surface, (self.rect.x + 10, y_pos + 5))

        # 枠
        pygame.draw.rect(surface, config.UI_BORDER_COLOR, self.rect, 2)

    def handle_event(self, event):
        """イベント処理"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                # クリック位置からアイテムインデックスを計算
                relative_y = event.pos[1] - self.rect.y
                index = (relative_y // self.item_height) + self.scroll_offset

                if 0 <= index < len(self.items):
                    self.selected_index = index
                    return True

            # スクロール
            elif event.button == 4:  # マウスホイール上
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif event.button == 5:  # マウスホイール下
                max_scroll = max(0, len(self.items) - (self.rect.height // self.item_height))
                self.scroll_offset = min(max_scroll, self.scroll_offset + 1)

        return False

    def get_selected_item(self):
        """選択されたアイテムを取得"""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None
