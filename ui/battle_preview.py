"""
BattlePreviewScreen - 戦闘開始前のプレビュー画面
勢力図上で戦闘する領地をアニメーション表示
"""
import pygame
from pygame import gfxdraw
import math
import config
from typing import Optional, Callable


class BattlePreviewScreen:
    """戦闘プレビュー画面（勢力図ベース）"""

    def __init__(self, screen, font, power_map):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.SysFont('meiryo', 24, bold=True)
        self.power_map = power_map

        # 画面の状態
        self.is_visible = False
        self.battle_data = None
        self.animation_timer = 0
        self.total_duration = 80  # 60フレーム(矢印) + 20フレーム(静止画)

        # アニメーションフェーズの時間設定
        self.phase_2_end = 60   # 0-60: 攻撃経路アニメーション
        self.phase_3_end = 80   # 60-80: 戦闘準備（静止画）


        # コールバック
        self.on_finish_callback = None

    def show(self, battle_data, on_finish=None):
        """プレビューを開始

        battle_data = {
            "attacker_province_id": int,
            "defender_province_id": int,
            "attacker_name": str,
            "defender_name": str
        }
        """
        self.is_visible = True
        self.battle_data = battle_data
        self.animation_timer = 0
        self.on_finish_callback = on_finish

    def update(self, game_state):
        """アニメーション更新"""
        if not self.is_visible:
            return

        self.animation_timer += 1

        # アニメーション終了判定
        if self.animation_timer >= self.total_duration:
            self.hide()
            return

    def hide(self):
        """プレビュー終了"""
        self.is_visible = False
        self.battle_data = None
        self.animation_timer = 0

        # 終了コールバックを呼ぶ
        if self.on_finish_callback:
            callback = self.on_finish_callback
            self.on_finish_callback = None
            callback()

    def handle_event(self, event):
        """イベント処理（スペースキーでスキップ可能）"""
        if not self.is_visible:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.hide()
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.hide()
            return True

        return False

    def draw(self, game_state):
        """プレビュー描画"""
        if not self.is_visible or not self.battle_data:
            return

        # 勢力図を背景として描画
        self.power_map.draw(game_state)

        # 半透明オーバーレイ
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(100)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # 領地情報を取得
        attacker_province = game_state.get_province(self.battle_data["attacker_province_id"])
        defender_province = game_state.get_province(self.battle_data["defender_province_id"])

        if not attacker_province or not defender_province:
            return

        # 領地の座標を取得
        attacker_pos = self.power_map._convert_position(attacker_province.position)
        defender_pos = self.power_map._convert_position(defender_province.position)

        # フェーズごとの描画
        if self.animation_timer < self.phase_2_end:
            self._draw_phase2_attack_route(attacker_province, defender_province, attacker_pos, defender_pos)
        else:
            self._draw_phase3_battle_ready(attacker_province, defender_province, attacker_pos, defender_pos)

        # 操作説明
        help_text = "[SPACE/クリック]でスキップ"
        help_surface = self.font.render(help_text, True, (200, 200, 200))
        help_x = (config.SCREEN_WIDTH - help_surface.get_width()) // 2
        self.screen.blit(help_surface, (help_x, config.SCREEN_HEIGHT - 40))

    def _draw_phase2_attack_route(self, attacker_prov, defender_prov, attacker_pos, defender_pos):
        """フェーズ2: 攻撃経路アニメーション"""
        # 点滅効果
        blink = (self.animation_timer // 10) % 2 == 0

        if blink:
            # アンチエイリアシング付き円（線幅4）
            for i in range(4):
                r = 35 - i
                if r > 0:
                    gfxdraw.aacircle(self.screen, attacker_pos[0], attacker_pos[1], r, (255, 100, 100))
                    gfxdraw.aacircle(self.screen, defender_pos[0], defender_pos[1], r, (100, 100, 255))

        # 矢印アニメーション
        phase_progress = self.animation_timer / self.phase_2_end

        # 攻撃元から防御先への方向ベクトル
        dx = defender_pos[0] - attacker_pos[0]
        dy = defender_pos[1] - attacker_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 矢印の終点（進行度に応じて伸びる）
            arrow_end_x = attacker_pos[0] + dx * phase_progress
            arrow_end_y = attacker_pos[1] + dy * phase_progress

            # 矢印本体
            pygame.draw.line(
                self.screen,
                (255, 200, 0),
                attacker_pos,
                (arrow_end_x, arrow_end_y),
                5
            )

            # 矢印の先端（三角形）
            if phase_progress > 0.1:
                arrow_size = 15
                angle = math.atan2(dy, dx)

                # 矢印先端の座標
                tip = (arrow_end_x, arrow_end_y)
                left = (
                    arrow_end_x - arrow_size * math.cos(angle - 0.5),
                    arrow_end_y - arrow_size * math.sin(angle - 0.5)
                )
                right = (
                    arrow_end_x - arrow_size * math.cos(angle + 0.5),
                    arrow_end_y - arrow_size * math.sin(angle + 0.5)
                )

                pygame.draw.polygon(self.screen, (255, 200, 0), [tip, left, right])

        # 情報表示
        info_text = f"{attacker_prov.name} から {defender_prov.name} へ進軍"
        info_surface = self.font.render(info_text, True, (240, 240, 240))
        info_x = (config.SCREEN_WIDTH - info_surface.get_width()) // 2
        self.screen.blit(info_surface, (info_x, 100))

    def _draw_phase3_battle_ready(self, attacker_prov, defender_prov, attacker_pos, defender_pos):
        """フェーズ3: 戦闘準備（静止画）"""
        # 矢印を完全に表示（静止画）
        dx = defender_pos[0] - attacker_pos[0]
        dy = defender_pos[1] - attacker_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # 攻撃側と防御側のハイライト（アンチエイリアシング付き、線幅4）
        for i in range(4):
            r = 35 - i
            if r > 0:
                gfxdraw.aacircle(self.screen, attacker_pos[0], attacker_pos[1], r, (255, 100, 100))
                gfxdraw.aacircle(self.screen, defender_pos[0], defender_pos[1], r, (100, 100, 255))

        if distance > 0:
            # 矢印本体
            pygame.draw.line(
                self.screen,
                (255, 200, 0),
                attacker_pos,
                defender_pos,
                5
            )

            # 矢印の先端（三角形）
            arrow_size = 15
            angle = math.atan2(dy, dx)

            tip = defender_pos
            left = (
                defender_pos[0] - arrow_size * math.cos(angle - 0.5),
                defender_pos[1] - arrow_size * math.sin(angle - 0.5)
            )
            right = (
                defender_pos[0] - arrow_size * math.cos(angle + 0.5),
                defender_pos[1] - arrow_size * math.sin(angle + 0.5)
            )

            pygame.draw.polygon(self.screen, (255, 200, 0), [tip, left, right])

        # 情報表示
        info_text = f"{attacker_prov.name} から {defender_prov.name} へ進軍"
        info_surface = self.font.render(info_text, True, (240, 240, 240))
        info_x = (config.SCREEN_WIDTH - info_surface.get_width()) // 2
        self.screen.blit(info_surface, (info_x, 100))
