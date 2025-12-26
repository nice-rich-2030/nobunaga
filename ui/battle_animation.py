"""
BattleAnimationScreen - 戦闘演出画面
戦闘の流れを視覚的に表現（テキストと図形ベース）
"""
import pygame
import config
from typing import Optional


class BattleAnimationScreen:
    """戦闘演出画面（テキスト＋図形ベース）"""

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.SysFont('meiryo', 28, bold=True)
        self.large_font = pygame.font.SysFont('meiryo', 24, bold=True)

        # 画面の状態
        self.is_visible = False
        self.battle_data = None
        self.animation_phase = 0  # 0:準備, 1:戦闘開始, 2:交戦中, 3:結果表示
        self.animation_timer = 0
        self.phase_duration = [60, 40, 80, 120]  # 各フェーズの表示時間（フレーム数）

        # 演出用の変数
        self.attacker_bar_value = 100
        self.defender_bar_value = 100
        self.shake_offset = 0
        self.flash_alpha = 0

        # 色定義
        self.bg_color = (20, 15, 10)
        self.border_color = (180, 140, 100)
        self.attacker_color = (200, 60, 60)
        self.defender_color = (60, 120, 200)
        self.text_color = (220, 220, 220)
        self.gold_color = (255, 215, 0)

        # コールバック
        self.on_finish_callback = None

    def show(self, battle_data, on_finish=None):
        """戦闘演出を開始

        battle_data = {
            "attacker_name": str,
            "defender_name": str,
            "attacker_province": str,
            "defender_province": str,
            "attacker_troops": int,
            "defender_troops": int,
            "attacker_general": str or None,
            "defender_general": str or None,
            "result": BattleResult
        }
        """
        self.is_visible = True
        self.battle_data = battle_data
        self.animation_phase = 0
        self.animation_timer = 0
        self.on_finish_callback = on_finish

        # 戦力バーの初期値
        self.attacker_bar_value = 100
        self.defender_bar_value = 100

    def update(self):
        """アニメーション更新"""
        if not self.is_visible:
            return

        self.animation_timer += 1

        # フェーズ遷移
        if self.animation_timer >= self.phase_duration[self.animation_phase]:
            self.animation_timer = 0
            self.animation_phase += 1

            # 演出終了判定
            if self.animation_phase >= len(self.phase_duration):
                self.hide()
                return

        # フェーズごとのアニメーション
        if self.animation_phase == 2:  # 交戦中
            self._animate_battle()

    def _animate_battle(self):
        """戦闘中のアニメーション"""
        if not self.battle_data or not self.battle_data.get("result"):
            return

        result = self.battle_data["result"]
        progress = self.animation_timer / self.phase_duration[2]

        # 兵力バーを徐々に減少
        attacker_initial = self.battle_data["attacker_troops"]
        defender_initial = self.battle_data["defender_troops"]

        if attacker_initial > 0:
            attacker_final = max(0, result.attacker_remaining / attacker_initial * 100)
            self.attacker_bar_value = 100 - (100 - attacker_final) * progress

        if defender_initial > 0:
            defender_final = max(0, result.defender_remaining / defender_initial * 100)
            self.defender_bar_value = 100 - (100 - defender_final) * progress

        # 画面シェイク効果
        import math
        self.shake_offset = int(math.sin(self.animation_timer * 0.5) * 5)

        # フラッシュ効果（ダメージ時）
        if self.animation_timer % 20 == 0:
            self.flash_alpha = 100

        if self.flash_alpha > 0:
            self.flash_alpha -= 10

    def handle_event(self, event):
        """イベント処理"""
        if not self.is_visible:
            return False

        # スペースキーまたはマウスクリックでスキップ/閉じる
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self.animation_phase >= 3:  # 結果表示中なら閉じる
                self.hide()
            else:
                self.skip_to_result()
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.animation_phase >= 3:  # 結果表示中なら閉じる
                self.hide()
            else:
                self.skip_to_result()
            return True

        return False

    def skip_to_result(self):
        """結果表示にスキップ"""
        self.animation_phase = 3
        self.animation_timer = 0

        # 最終状態に設定
        if self.battle_data and self.battle_data.get("result"):
            result = self.battle_data["result"]
            attacker_initial = self.battle_data["attacker_troops"]
            defender_initial = self.battle_data["defender_troops"]

            if attacker_initial > 0:
                self.attacker_bar_value = max(0, result.attacker_remaining / attacker_initial * 100)

            if defender_initial > 0:
                self.defender_bar_value = max(0, result.defender_remaining / defender_initial * 100)

    def hide(self):
        """演出終了"""
        self.is_visible = False
        self.battle_data = None
        self.shake_offset = 0
        self.flash_alpha = 0

        # 終了コールバックを呼ぶ
        if self.on_finish_callback:
            callback = self.on_finish_callback
            self.on_finish_callback = None
            callback()

    def draw(self):
        """戦闘演出を描画"""
        if not self.is_visible or not self.battle_data:
            return

        # 半透明オーバーレイ
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(self.bg_color)
        self.screen.blit(overlay, (0, 0))

        # シェイクオフセット適用
        offset_x = self.shake_offset if self.animation_phase == 2 else 0

        # タイトル
        title = "⚔ 戦 闘 ⚔"
        title_surface = self.title_font.render(title, True, self.gold_color)
        title_x = (config.SCREEN_WIDTH - title_surface.get_width()) // 2 + offset_x
        self.screen.blit(title_surface, (title_x, 50))

        # フェーズごとの描画
        if self.animation_phase == 0:
            self._draw_preparation()
        elif self.animation_phase == 1:
            self._draw_battle_start()
        elif self.animation_phase == 2:
            self._draw_battle_progress(offset_x)
        elif self.animation_phase == 3:
            self._draw_battle_result()

        # フラッシュ効果
        if self.flash_alpha > 0:
            flash = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            flash.set_alpha(self.flash_alpha)
            flash.fill((255, 255, 255))
            self.screen.blit(flash, (0, 0))

        # 操作説明
        if self.animation_phase < 3:
            help_text = "[SPACE/クリック]でスキップ"
            help_surface = self.font.render(help_text, True, (150, 150, 150))
            help_x = (config.SCREEN_WIDTH - help_surface.get_width()) // 2
            self.screen.blit(help_surface, (help_x, config.SCREEN_HEIGHT - 40))

    def _draw_preparation(self):
        """準備フェーズの描画"""
        y_offset = 120

        # 領地名と大名名
        attacker_text = f"{self.battle_data['attacker_province']} ({self.battle_data['attacker_name']})"
        defender_text = f"{self.battle_data['defender_province']} ({self.battle_data['defender_name']})"

        attacker_surface = self.large_font.render(attacker_text, True, self.attacker_color)
        defender_surface = self.large_font.render(defender_text, True, self.defender_color)

        self.screen.blit(attacker_surface, (100, y_offset))
        self.screen.blit(defender_surface, (config.SCREEN_WIDTH - 400, y_offset))

        # VS
        vs_surface = self.title_font.render("VS", True, self.gold_color)
        vs_x = (config.SCREEN_WIDTH - vs_surface.get_width()) // 2
        self.screen.blit(vs_surface, (vs_x, y_offset + 80))

        # 兵力表示
        y_offset += 180
        attacker_troops_text = f"兵力: {self.battle_data['attacker_troops']}"
        defender_troops_text = f"兵力: {self.battle_data['defender_troops']}"

        self.screen.blit(self.font.render(attacker_troops_text, True, self.text_color), (100, y_offset))
        self.screen.blit(self.font.render(defender_troops_text, True, self.text_color), (config.SCREEN_WIDTH - 400, y_offset))

        # 武将表示
        if self.battle_data.get("attacker_general"):
            general_text = f"武将: {self.battle_data['attacker_general']}"
            self.screen.blit(self.font.render(general_text, True, self.gold_color), (100, y_offset + 30))

            # 将軍の能力値を表示
            attacker_general_obj = self.battle_data.get("attacker_general_obj")
            if attacker_general_obj:
                stats_text = f"  武{attacker_general_obj.war_skill} 統{attacker_general_obj.leadership}"
                self.screen.blit(self.font.render(stats_text, True, self.text_color), (100, y_offset + 55))

        if self.battle_data.get("defender_general"):
            general_text = f"武将: {self.battle_data['defender_general']}"
            self.screen.blit(self.font.render(general_text, True, self.gold_color), (config.SCREEN_WIDTH - 400, y_offset + 30))

            # 将軍の能力値を表示
            defender_general_obj = self.battle_data.get("defender_general_obj")
            if defender_general_obj:
                stats_text = f"  武{defender_general_obj.war_skill} 統{defender_general_obj.leadership}"
                self.screen.blit(self.font.render(stats_text, True, self.text_color), (config.SCREEN_WIDTH - 400, y_offset + 55))

    def _draw_battle_start(self):
        """戦闘開始フェーズの描画"""
        # 大きく「戦闘開始」を表示
        start_text = "戦 闘 開 始 ！"
        start_surface = self.title_font.render(start_text, True, self.gold_color)
        start_x = (config.SCREEN_WIDTH - start_surface.get_width()) // 2
        start_y = (config.SCREEN_HEIGHT - start_surface.get_height()) // 2

        # 点滅効果
        if (self.animation_timer // 10) % 2 == 0:
            self.screen.blit(start_surface, (start_x, start_y))

    def _draw_battle_progress(self, offset_x):
        """戦闘進行中の描画"""
        # 攻撃側（左側）
        self._draw_army_status(
            100 + offset_x,
            150,
            self.battle_data['attacker_name'],
            self.battle_data['attacker_province'],
            self.battle_data['attacker_troops'],
            self.attacker_bar_value,
            self.attacker_color,
            is_attacker=True
        )

        # 守備側（右側）
        self._draw_army_status(
            config.SCREEN_WIDTH - 400 - offset_x,
            150,
            self.battle_data['defender_name'],
            self.battle_data['defender_province'],
            self.battle_data['defender_troops'],
            self.defender_bar_value,
            self.defender_color,
            is_attacker=False
        )

        # 中央に刀のアイコン（交戦表現）
        center_x = config.SCREEN_WIDTH // 2
        center_y = 280

        # アニメーション効果（刀が交差）
        sword_offset = int((self.animation_timer % 20) * 2)

        # 攻撃側の刀（右向き）
        pygame.draw.line(self.screen, self.attacker_color,
                        (center_x - 60 - sword_offset, center_y),
                        (center_x - 10 - sword_offset, center_y), 5)
        pygame.draw.line(self.screen, self.attacker_color,
                        (center_x - 15 - sword_offset, center_y - 10),
                        (center_x - 15 - sword_offset, center_y + 10), 3)

        # 守備側の刀（左向き）
        pygame.draw.line(self.screen, self.defender_color,
                        (center_x + 60 + sword_offset, center_y),
                        (center_x + 10 + sword_offset, center_y), 5)
        pygame.draw.line(self.screen, self.defender_color,
                        (center_x + 15 + sword_offset, center_y - 10),
                        (center_x + 15 + sword_offset, center_y + 10), 3)

    def _draw_army_status(self, x, y, daimyo_name, province_name, initial_troops, bar_value, color, is_attacker):
        """軍の状態を描画"""
        # 大名名
        name_surface = self.large_font.render(daimyo_name, True, color)
        self.screen.blit(name_surface, (x, y))

        # 領地名
        province_surface = self.font.render(f"[{province_name}]", True, self.text_color)
        self.screen.blit(province_surface, (x, y + 35))

        # 兵力バー
        bar_width = 250
        bar_height = 30
        bar_y = y + 70

        # 背景バー（灰色）
        pygame.draw.rect(self.screen, (50, 50, 50), (x, bar_y, bar_width, bar_height))

        # 現在兵力バー
        current_width = int(bar_width * (bar_value / 100))
        pygame.draw.rect(self.screen, color, (x, bar_y, current_width, bar_height))

        # 枠線
        pygame.draw.rect(self.screen, self.border_color, (x, bar_y, bar_width, bar_height), 2)

        # 兵力数値
        current_troops = int(initial_troops * (bar_value / 100))
        troops_text = f"{current_troops:,} / {initial_troops:,}"
        troops_surface = self.font.render(troops_text, True, self.text_color)
        troops_x = x + (bar_width - troops_surface.get_width()) // 2
        self.screen.blit(troops_surface, (troops_x, bar_y + 5))

        # 損失率
        loss_rate = 100 - bar_value
        if loss_rate > 0:
            loss_text = f"損失 {loss_rate:.0f}%"
            loss_surface = self.font.render(loss_text, True, (255, 100, 100))
            self.screen.blit(loss_surface, (x, bar_y + 40))

    def _draw_battle_result(self):
        """戦闘結果の描画"""
        if not self.battle_data.get("result"):
            return

        result = self.battle_data["result"]
        y_offset = 120

        # 勝敗表示（勝った側に表示）
        if result.attacker_won:
            winner_text = f"⚔ {self.battle_data['attacker_name']} の勝利！ ⚔"
            winner_color = self.attacker_color
            winner_x = 100  # 左側（攻撃側）に表示
        else:
            winner_text = f"🛡 {self.battle_data['defender_name']} の勝利！ 🛡"
            winner_color = self.defender_color
            winner_x = config.SCREEN_WIDTH - 500  # 右側（守備側）に表示

        winner_surface = self.title_font.render(winner_text, True, winner_color)
        self.screen.blit(winner_surface, (winner_x, y_offset))

        # 区切り線
        pygame.draw.line(self.screen, self.border_color,
                        (100, y_offset + 50), (config.SCREEN_WIDTH - 100, y_offset + 50), 2)

        # 戦果詳細
        y_offset += 80

        # 攻撃側
        attacker_result = [
            f"【{self.battle_data['attacker_name']}】",
            f"初期兵力: {self.battle_data['attacker_troops']:,}",
            f"損　　失: {result.attacker_casualties:,}",
            f"残存兵力: {result.attacker_remaining:,}"
        ]

        for i, line in enumerate(attacker_result):
            color = self.attacker_color if i == 0 else self.text_color
            surface = self.font.render(line, True, color)
            self.screen.blit(surface, (150, y_offset + i * 30))

        # 守備側
        defender_result = [
            f"【{self.battle_data['defender_name']}】",
            f"初期兵力: {self.battle_data['defender_troops']:,}",
            f"損　　失: {result.defender_casualties:,}",
            f"残存兵力: {result.defender_remaining:,}"
        ]

        for i, line in enumerate(defender_result):
            color = self.defender_color if i == 0 else self.text_color
            surface = self.font.render(line, True, color)
            self.screen.blit(surface, (config.SCREEN_WIDTH - 400, y_offset + i * 30))

        # 領地占領
        if result.province_captured:
            y_offset += 150
            capture_text = f"★ {self.battle_data['defender_province']} を占領！ ★"
            capture_surface = self.large_font.render(capture_text, True, self.gold_color)
            capture_x = (config.SCREEN_WIDTH - capture_surface.get_width()) // 2
            self.screen.blit(capture_surface, (capture_x, y_offset))

        # 継続メッセージ
        y_offset = config.SCREEN_HEIGHT - 60
        continue_text = "[SPACE/クリック]で続行"
        continue_surface = self.font.render(continue_text, True, self.gold_color)

        # 点滅効果
        if (self.animation_timer // 15) % 2 == 0:
            continue_x = (config.SCREEN_WIDTH - continue_surface.get_width()) // 2
            self.screen.blit(continue_surface, (continue_x, y_offset))

    def is_finished(self):
        """演出が終了したか"""
        return not self.is_visible
