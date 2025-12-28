"""
EventHistoryScreen - イベント履歴画面（簡易版）
過去のイベント履歴を表示
"""
import pygame
import config


class EventHistoryScreen:
    """イベント履歴画面（簡易版）"""

    def __init__(self, screen, font, sound_manager=None):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.SysFont('meiryo', 20, bold=True)
        self.sound_manager = sound_manager

        # 画面の状態
        self.is_visible = False
        self.event_system = None
        self.game_state = None

        # 画面のサイズと位置
        self.width = 700
        self.height = 500
        self.x = (config.SCREEN_WIDTH - self.width) // 2
        self.y = (config.SCREEN_HEIGHT - self.height) // 2

        # スクロール
        self.scroll_offset = 0

        # 色定義
        self.bg_color = (30, 25, 20)
        self.border_color = (180, 140, 100)
        self.text_color = (220, 220, 220)
        self.header_color = (255, 220, 180)

    def show(self, event_system, game_state):
        """履歴画面を表示"""
        self.is_visible = True
        self.event_system = event_system
        self.game_state = game_state
        self.scroll_offset = 0

    def hide(self):
        """履歴画面を非表示"""
        self.is_visible = False

    def handle_event(self, event):
        """イベント処理"""
        if not self.is_visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # キャンセル音再生
                if self.sound_manager:
                    self.sound_manager.play("cancel")
                self.hide()
                return True
            elif event.key == pygame.K_UP:
                self.scroll_offset = max(0, self.scroll_offset - 1)
                return True
            elif event.key == pygame.K_DOWN:
                max_offset = max(0, len(self.event_system.event_history) - 10)
                self.scroll_offset = min(max_offset, self.scroll_offset + 1)
                return True
            elif event.key == pygame.K_PAGEUP:
                self.scroll_offset = max(0, self.scroll_offset - 10)
                return True
            elif event.key == pygame.K_PAGEDOWN:
                max_offset = max(0, len(self.event_system.event_history) - 10)
                self.scroll_offset = min(max_offset, self.scroll_offset + 10)
                return True

        elif event.type == pygame.MOUSEWHEEL:
            if self.is_visible:
                max_offset = max(0, len(self.event_system.event_history) - 10)
                self.scroll_offset = max(0, min(max_offset, self.scroll_offset - event.y))
                return True

        return False

    def draw(self):
        """履歴画面を描画"""
        if not self.is_visible or not self.event_system:
            return

        # 半透明オーバーレイ
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # 背景
        pygame.draw.rect(self.screen, self.bg_color,
                        (self.x, self.y, self.width, self.height))

        # 枠線
        pygame.draw.rect(self.screen, self.border_color,
                        (self.x, self.y, self.width, self.height), 3)

        # タイトル
        title_text = self.title_font.render("イベント履歴", True, self.header_color)
        title_x = self.x + (self.width - title_text.get_width()) // 2
        self.screen.blit(title_text, (title_x, self.y + 15))

        # 区切り線
        pygame.draw.line(self.screen, self.border_color,
                        (self.x + 20, self.y + 50),
                        (self.x + self.width - 20, self.y + 50), 2)

        # イベント履歴の表示
        history = self.event_system.event_history
        if not history:
            no_events_text = self.font.render("まだイベントが発生していません", True, self.text_color)
            no_events_x = self.x + (self.width - no_events_text.get_width()) // 2
            self.screen.blit(no_events_text, (no_events_x, self.y + 100))
        else:
            # 最新のイベントから表示（逆順）
            y_offset = self.y + 70
            line_height = 40

            # スクロール範囲を計算
            start_idx = max(0, len(history) - 10 - self.scroll_offset)
            end_idx = min(len(history), start_idx + 10)

            for i in range(end_idx - 1, start_idx - 1, -1):
                event_data = history[i]

                # ターン・季節情報
                turn_season = f"第{event_data['turn']}ターン {event_data['season']}"
                turn_surface = self.font.render(turn_season, True, (200, 180, 150))
                self.screen.blit(turn_surface, (self.x + 30, y_offset))

                # イベント名とイベントID
                event_name = self._get_event_name(event_data['event_id'])
                event_surface = self.font.render(event_name, True, self.header_color)
                self.screen.blit(event_surface, (self.x + 200, y_offset))

                # 影響を受けた領地
                province = self.game_state.get_province(event_data['province_id'])
                province_name = province.name if province else "不明"
                province_surface = self.font.render(f"[{province_name}]", True, (180, 180, 180))
                self.screen.blit(province_surface, (self.x + 400, y_offset))

                y_offset += line_height

                # 画面からはみ出したら終了
                if y_offset > self.y + self.height - 80:
                    break

        # スクロール情報
        if history:
            total_count = len(history)
            showing_start = len(history) - end_idx + 1
            showing_end = len(history) - start_idx
            scroll_info = f"表示: {showing_start}-{showing_end} / 全{total_count}件"
            scroll_surface = self.font.render(scroll_info, True, (150, 150, 150))
            self.screen.blit(scroll_surface, (self.x + 30, self.y + self.height - 50))

        # 操作説明
        help_text = "[ESC]閉じる  [↑↓]スクロール  [PageUp/Down]高速スクロール"
        help_surface = self.font.render(help_text, True, (150, 150, 150))
        help_x = self.x + (self.width - help_surface.get_width()) // 2
        self.screen.blit(help_surface, (help_x, self.y + self.height - 25))

    def _get_event_name(self, event_id):
        """イベントIDからイベント名を取得"""
        if not self.event_system:
            return event_id

        for event in self.event_system.events:
            if event.event_id == event_id:
                return event.name

        return event_id
