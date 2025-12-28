"""
DaimyoDeathScreen - 大名死亡演出画面
大名が討死または病死した際の演出画面
"""
import pygame
from typing import Optional, Callable, Dict, Any
from utils.image_manager import ImageManager
from utils.sound_manager import SoundManager
from ui.widgets import Button


class DaimyoDeathScreen:
    """大名死亡演出画面クラス"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font,
                 image_manager: ImageManager, sound_manager: SoundManager):
        self.screen = screen
        self.font_medium = font
        # 日本語対応の大きいフォント
        try:
            self.font_large = pygame.font.SysFont('meiryo', 62)
        except:
            self.font_large = pygame.font.Font(None, 62)
        self.image_manager = image_manager
        self.sound_manager = sound_manager

        self.is_visible = False
        self.animation_phase = 0
        self.phase_timer = 0

        # 演出データ
        self.death_data: Optional[Dict[str, Any]] = None
        self.daimyo_portrait: Optional[pygame.Surface] = None

        # コールバック
        self.on_finish_callback: Optional[Callable] = None
        self.on_play_callback: Optional[Callable] = None
        self.on_end_callback: Optional[Callable] = None

        # ボタン（プレイヤー大名用）
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        button_y = screen_height - 90

        self.play_button = Button(
            x=screen_width * 4 // 5 - 220,
            y=button_y,
            width=200,
            height=60,
            text="PLAY",
            font=self.font_medium,
            callback=self._on_play_clicked,
            sound_manager=self.sound_manager,
            sound_type="decide"
        )

        self.end_button = Button(
            x=screen_width * 4 // 5 + 20,
            y=button_y,
            width=200,
            height=60,
            text="END",
            font=self.font_medium,
            callback=self._on_end_clicked,
            sound_manager=self.sound_manager,
            sound_type="cancel"
        )

        # フェーズ設定
        # Phase 0: 暗転フェードイン (30フレーム)
        # Phase 1: 肖像画・テキスト表示 (60フレーム)
        # Phase 2: 入力待ち (無制限)
        self.phase_duration = [30, 60, -1]

    def show(self, death_data: Dict[str, Any],
             on_finish: Optional[Callable] = None,
             on_play: Optional[Callable] = None,
             on_end: Optional[Callable] = None):
        """演出を開始

        Args:
            death_data: 死亡データ
                {
                    "daimyo_id": int,
                    "daimyo_name": str,
                    "clan_name": str,
                    "age": int,
                    "is_player": bool,
                    "cause": str  # "battle_defeat" or "natural_death"
                }
            on_finish: 演出終了時のコールバック（AI大名用）
            on_play: PLAYボタン押下時のコールバック（プレイヤー大名用）
            on_end: ENDボタン押下時のコールバック（プレイヤー大名用）
        """
        self.is_visible = True
        self.animation_phase = 0
        self.phase_timer = 0
        self.death_data = death_data
        self.on_finish_callback = on_finish
        self.on_play_callback = on_play
        self.on_end_callback = on_end

        # 肖像画を読み込み（brightness=0.3で暗く）
        self.daimyo_portrait = self.image_manager.get_portrait_for_battle(
            general_id=None,
            daimyo_id=death_data["daimyo_id"],
            size=(640, 640),
            brightness=0.3
        )

        print(f"[DaimyoDeathScreen] 演出開始: {death_data['clan_name']} {death_data['daimyo_name']} (享年{death_data['age']})")

    def hide(self):
        """演出を終了"""
        self.is_visible = False
        self.death_data = None
        self.daimyo_portrait = None
        print("[DaimyoDeathScreen] 演出終了")

    def update(self):
        """アニメーション更新"""
        if not self.is_visible:
            return

        self.phase_timer += 1

        # フェーズ遷移
        current_duration = self.phase_duration[self.animation_phase]
        if current_duration > 0 and self.phase_timer >= current_duration:
            self.animation_phase += 1
            self.phase_timer = 0

            # Phase 2に到達したらボタン有効化（プレイヤーの場合）
            if self.animation_phase == 2 and self.death_data and self.death_data["is_player"]:
                print("[DaimyoDeathScreen] プレイヤー大名死亡 - ボタン表示")

    def draw(self):
        """描画"""
        if not self.is_visible or not self.death_data:
            return

        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()

        # 背景画像を描画
        background = self.image_manager.load_background(
            "battle_result_background.png",
            target_size=(screen_width, screen_height)
        )
        if background:
            self.screen.blit(background, (0, 0))

        # Phase 0: 暗転フェードイン
        if self.animation_phase == 0:
            alpha = int(255 * (self.phase_timer / self.phase_duration[0]))
            overlay = pygame.Surface((screen_width, screen_height))
            overlay.set_alpha(alpha)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

        # Phase 1以降: 肖像画とテキスト表示
        elif self.animation_phase >= 1:
            # フェードイン計算（Phase 1のみ）
            fade_alpha = 255
            if self.animation_phase == 1:
                fade_alpha = int(255 * (self.phase_timer / self.phase_duration[1]))

            # 肖像画を中央上部に表示
            if self.daimyo_portrait:
                portrait_x = (screen_width - 640) // 2
                portrait_y = 50

                # フェードイン適用
                if fade_alpha < 255:
                    portrait_copy = self.daimyo_portrait.copy()
                    portrait_copy.set_alpha(fade_alpha)
                    self.screen.blit(portrait_copy, (portrait_x, portrait_y))
                else:
                    self.screen.blit(self.daimyo_portrait, (portrait_x, portrait_y))

            # テキスト表示
            if self.death_data["cause"] == "battle_defeat":
                cause_text = "討死"
            elif self.death_data["cause"] == "territory_loss":
                cause_text = "滅亡"
            else:
                cause_text = "病死"

            # メインメッセージ（氏名と死因）
            main_text = f"{self.death_data['clan_name']} {self.death_data['daimyo_name']}"
            death_text = f"{cause_text}で死去"
            age_text = f"享年 {self.death_data['age']}歳"

            # 暗い背景パネルを描画（肖像画の下部に重ねて配置）
            panel_width = 700
            panel_height = 180
            panel_x = (screen_width - panel_width) // 2
            panel_y = 520  # 肖像画（50-690）の下部に重ねる
            panel_surface = pygame.Surface((panel_width, panel_height))
            panel_surface.set_alpha(200)
            panel_surface.fill((10, 10, 10))
            self.screen.blit(panel_surface, (panel_x, panel_y))

            # メインテキスト（大名名）- 肖像画の上部
            main_surface = self.font_large.render(main_text, True, (255, 255, 255))
            main_rect = main_surface.get_rect(center=(screen_width // 2, 560))

            # 死因テキスト（中）
            death_surface = self.font_medium.render(death_text, True, (255, 200, 200))
            death_rect = death_surface.get_rect(center=(screen_width // 2, 620))

            # 年齢テキスト（中）
            age_surface = self.font_medium.render(age_text, True, (200, 200, 200))
            age_rect = age_surface.get_rect(center=(screen_width // 2, 660))

            # フェードイン適用
            if fade_alpha < 255:
                main_surface.set_alpha(fade_alpha)
                death_surface.set_alpha(fade_alpha)
                age_surface.set_alpha(fade_alpha)

            self.screen.blit(main_surface, main_rect)
            self.screen.blit(death_surface, death_rect)
            self.screen.blit(age_surface, age_rect)

            # Phase 2: ボタンまたは指示テキスト表示
            if self.animation_phase == 2:
                if self.death_data["is_player"]:
                    # プレイヤー大名: PLAYとENDボタン
                    self.play_button.draw(self.screen)
                    self.end_button.draw(self.screen)
                else:
                    # AI大名: スペース/クリック/Enterで次へ
                    instruction_text = "スペース/クリック/Enterで次へ"
                    instruction_surface = self.font_medium.render(instruction_text, True, (150, 150, 150))
                    instruction_rect = instruction_surface.get_rect(center=(screen_width // 2, screen_height - 20))
                    self.screen.blit(instruction_surface, instruction_rect)

    def handle_event(self, event: pygame.event.Event):
        """イベント処理"""
        if not self.is_visible or not self.death_data:
            return

        # Phase 2のみ入力受付
        if self.animation_phase < 2:
            return

        if self.death_data["is_player"]:
            # プレイヤー大名: ボタンクリック
            self.play_button.handle_event(event)
            self.end_button.handle_event(event)
        else:
            # AI大名: スペース/クリック/Enterで終了
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._finish()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._finish()

    def _on_play_clicked(self):
        """PLAYボタンクリック時"""
        print("[DaimyoDeathScreen] PLAY選択 - ゲーム再開")
        self.hide()
        if self.on_play_callback:
            self.on_play_callback()

    def _on_end_clicked(self):
        """ENDボタンクリック時"""
        print("[DaimyoDeathScreen] END選択 - ゲーム終了")
        self.hide()
        if self.on_end_callback:
            self.on_end_callback()

    def _finish(self):
        """演出終了（AI大名用）"""
        print("[DaimyoDeathScreen] 演出完了（AI大名）")
        self.hide()
        if self.on_finish_callback:
            self.on_finish_callback()
