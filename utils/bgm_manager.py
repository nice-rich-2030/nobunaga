"""
BGMManager - BGM管理クラス
場面に応じたBGMの再生・切り替えを管理
"""
import pygame
import os
import config
from typing import Optional


class BGMScene:
    """BGMシーン定義"""
    PROLOGUE = "prologue"
    AI_TURN = "ai_turn"
    PLAYER_TURN = "player_turn"
    BATTLE = "battle"


class BGMManager:
    """BGM管理クラス"""

    def __init__(self):
        self.enabled = config.BGM_ENABLED
        self.volumes = config.BGM_VOLUMES.copy()  # 各曲の音量設定
        self.fade_ms = config.BGM_FADE_MS
        self.current_scene: Optional[str] = None
        self.is_playing = False

        # 再生位置を記憶するシーンのリスト
        self.resume_scenes = set(config.BGM_RESUME_SCENES)

        # プレイヤーターンBGMの再生位置を記憶（秒単位）
        self.player_turn_position = 0.0

        # pygame.mixer.music の初期化は既にSoundManagerで実行済み

    def play_scene(self, scene: str, force_restart: bool = False):
        """指定シーンのBGMを再生"""
        # 同じシーンならスキップ（force_restart=Falseの場合）
        if not force_restart and self.current_scene == scene and self.is_playing:
            return

        if not self.enabled:
            return

        # BGMファイルパスを取得
        filename = config.BGM_FILES.get(scene)
        if not filename:
            return

        filepath = os.path.join(config.BGM_DIR, filename)

        # ファイルの存在確認
        if not os.path.exists(filepath):
            return

        try:
            # 既存BGMの再生位置を保存（player_turnの場合のみ）
            if self.is_playing and self.current_scene == "player_turn":
                self.player_turn_position = pygame.mixer.music.get_pos() / 1000.0  # ミリ秒→秒

            # 既存BGMをフェードアウト
            if self.is_playing:
                pygame.mixer.music.fadeout(self.fade_ms)
                pygame.time.wait(self.fade_ms)

            # 新しいBGMをロード
            pygame.mixer.music.load(filepath)

            # 曲ごとの音量を設定
            volume = self.volumes.get(scene, 0.5)
            pygame.mixer.music.set_volume(volume)

            # 再生位置から再開するか判定
            if scene == "player_turn" and self.player_turn_position > 0:
                # プレイヤーターンBGMは中断位置から再開
                pygame.mixer.music.play(loops=-1, start=self.player_turn_position)
            else:
                # その他のBGMは最初から再生
                pygame.mixer.music.play(loops=-1)

            self.current_scene = scene
            self.is_playing = True
        except Exception as e:
            print(f"BGM再生エラー: {e}")
            self.enabled = False

    def stop(self, fade_out: bool = True):
        """BGMを停止"""
        if not self.is_playing:
            return

        if fade_out:
            pygame.mixer.music.fadeout(self.fade_ms)
        else:
            pygame.mixer.music.stop()

        self.is_playing = False
        self.current_scene = None

    def set_volume(self, scene: str, volume: float):
        """特定のシーンの音量を設定（0.0 - 1.0）"""
        self.volumes[scene] = max(0.0, min(1.0, volume))
        # 現在再生中のシーンの音量なら即座に反映
        if self.is_playing and self.current_scene == scene:
            pygame.mixer.music.set_volume(self.volumes[scene])

    def set_all_volumes(self, volume: float):
        """全シーンの音量を一括設定（0.0 - 1.0）"""
        volume = max(0.0, min(1.0, volume))
        for scene in self.volumes.keys():
            self.volumes[scene] = volume
        # 現在再生中なら即座に反映
        if self.is_playing:
            pygame.mixer.music.set_volume(volume)

    def toggle_mute(self):
        """ミュート切り替え"""
        if self.is_playing:
            current_vol = pygame.mixer.music.get_volume()
            current_scene_vol = self.volumes.get(self.current_scene, 0.5)
            if current_vol > 0:
                pygame.mixer.music.set_volume(0.0)
            else:
                pygame.mixer.music.set_volume(current_scene_vol)

    def pause(self):
        """一時停止"""
        if self.is_playing:
            pygame.mixer.music.pause()

    def unpause(self):
        """再開"""
        if self.is_playing:
            pygame.mixer.music.unpause()
