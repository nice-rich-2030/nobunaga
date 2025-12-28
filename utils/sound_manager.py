"""
SoundManager - 効果音の読み込みと再生管理
全ての効果音の一元管理を行う
"""
import pygame
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SoundManager:
    """効果音の読み込み、キャッシング、再生を管理"""

    def __init__(self, base_path: str):
        """
        Args:
            base_path: アセットの基底パス（通常は "assets" ディレクトリ）
        """
        self.base_path = base_path
        self.sounds_path = os.path.join(base_path, "sounds")

        # キャッシュ: "sound_name" -> pygame.mixer.Sound
        self._cache = {}

        # デフォルト設定
        self.volume = 0.7  # 70%
        self.muted = False
        self.disabled = False  # エラー時に無効化

        # pygame.mixerの初期化
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            logger.info(f"SoundManager initialized with base_path: {base_path}")
        except pygame.error as e:
            logger.warning(f"Failed to initialize pygame.mixer: {e}")
            logger.warning("Sound will be disabled")
            self.disabled = True

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        """効果音ファイルを読み込む

        Args:
            filename: ファイル名（例: "decide.wav"）

        Returns:
            読み込んだSound、失敗時はNone
        """
        # 無効化されている場合は何もしない
        if self.disabled:
            return None

        # キャッシュにあれば返す
        if filename in self._cache:
            return self._cache[filename]

        # ファイルパス
        filepath = os.path.join(self.sounds_path, filename)

        # ファイル存在チェック
        if not os.path.exists(filepath):
            logger.warning(f"Sound file not found: {filepath}")
            return None

        # サウンドロード
        try:
            sound = pygame.mixer.Sound(filepath)
            self._cache[filename] = sound
            logger.debug(f"Loaded sound: {filename}")
            return sound
        except pygame.error as e:
            logger.error(f"Failed to load sound {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {filepath}: {e}")
            return None

    def play(self, sound_name: str, volume: Optional[float] = None):
        """効果音を再生

        Args:
            sound_name: 効果音名（"decide", "battle", "cancel"）または
                       ファイル名（"decide.wav"）
            volume: 個別音量（0.0-1.0）。Noneの場合はself.volumeを使用
        """
        # 無効化またはミュート時は何もしない
        if self.disabled or self.muted:
            return

        # ファイル名に変換（拡張子がなければ .wav を追加）
        if not sound_name.endswith(".wav"):
            filename = f"{sound_name}.wav"
        else:
            filename = sound_name

        # サウンドロード
        sound = self.load_sound(filename)
        if sound is None:
            return

        # 音量設定
        if volume is None:
            volume = self.volume

        sound.set_volume(volume)

        # 再生
        try:
            sound.play()
        except pygame.error as e:
            logger.error(f"Failed to play sound {filename}: {e}")

    def preload_all_sounds(self):
        """全効果音をプリロード（起動時に使用）"""
        logger.info("Preloading all sound effects...")

        sound_files = ["decide.wav", "battle.wav", "cancel.wav"]

        for filename in sound_files:
            self.load_sound(filename)

        logger.info(f"Preloaded {len(self._cache)} sound effects")

    def set_volume(self, volume: float):
        """全体音量を設定

        Args:
            volume: 音量（0.0-1.0）
        """
        self.volume = max(0.0, min(1.0, volume))
        logger.info(f"Sound volume set to {self.volume:.1%}")

    def toggle_mute(self):
        """ミュート切り替え"""
        self.muted = not self.muted
        status = "muted" if self.muted else "unmuted"
        logger.info(f"Sound {status}")

    def clear_cache(self):
        """キャッシュをクリア（メモリ節約用）"""
        self._cache.clear()
        logger.info("Sound cache cleared")
