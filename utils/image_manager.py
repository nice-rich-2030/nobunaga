"""
ImageManager - 画像読み込みとキャッシング管理
全ての肖像画と背景画像の一元管理を行う
"""
import pygame
import os
import logging
from typing import Optional, Tuple
import config

logger = logging.getLogger(__name__)


class ImageManager:
    """画像の読み込み、キャッシング、フォールバック処理を管理"""

    def __init__(self, base_path: str):
        """
        Args:
            base_path: アセットの基底パス（通常は "assets" ディレクトリ）
        """
        self.base_path = base_path
        self.portraits_path = os.path.join(base_path, "portraits")
        self.backgrounds_path = os.path.join(base_path, "backgrounds")

        # キャッシュ: "type_id_widthxheight" -> pygame.Surface
        self._cache = {}

        logger.info(f"ImageManager initialized with base_path: {base_path}")

    def load_general_portrait(self, general_id: int, size: Tuple[int, int] = (256, 256)) -> Optional[pygame.Surface]:
        """武将肖像画を読み込む

        Args:
            general_id: 武将ID (1-15)
            size: 出力サイズ（width, height）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # 範囲チェック
        if general_id < 1 or general_id > 15:
            logger.warning(f"Invalid general_id: {general_id}. Must be 1-15.")
            return None

        # キャッシュキー生成
        cache_key = f"general_{general_id:02d}_{size[0]}x{size[1]}"

        # キャッシュにあれば返す
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ファイルパス
        filename = f"general_{general_id:02d}.png"
        filepath = os.path.join(self.portraits_path, "generals", filename)

        # 画像ロード
        surface = self._load_image(filepath, size)

        if surface:
            self._cache[cache_key] = surface
            logger.debug(f"Loaded general portrait: {filename}")
        else:
            logger.warning(f"Failed to load general portrait: {filepath}")

        return surface

    def load_daimyo_portrait(self, daimyo_id: int, size: Tuple[int, int] = (256, 256)) -> Optional[pygame.Surface]:
        """大名肖像画を読み込む

        Args:
            daimyo_id: 大名ID (1-6)
            size: 出力サイズ（width, height）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # 範囲チェック
        if daimyo_id < 1 or daimyo_id > 6:
            logger.warning(f"Invalid daimyo_id: {daimyo_id}. Must be 1-6.")
            return None

        # キャッシュキー生成
        cache_key = f"daimyo_{daimyo_id:02d}_{size[0]}x{size[1]}"

        # キャッシュにあれば返す
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ファイルパス
        filename = f"daimyo_{daimyo_id:02d}.png"
        filepath = os.path.join(self.portraits_path, "daimyo", filename)

        # 画像ロード
        surface = self._load_image(filepath, size)

        if surface:
            self._cache[cache_key] = surface
            logger.debug(f"Loaded daimyo portrait: {filename}")
        else:
            logger.warning(f"Failed to load daimyo portrait: {filepath}")

        return surface

    def load_background(self, name: str) -> Optional[pygame.Surface]:
        """背景画像を読み込む

        Args:
            name: ファイル名（例: "main_background.png"）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # キャッシュキー
        cache_key = f"bg_{name}"

        # キャッシュにあれば返す
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ファイルパス
        filepath = os.path.join(self.backgrounds_path, name)

        # 画像ロード（背景はリサイズしない）
        surface = self._load_image(filepath, size=None)

        if surface:
            self._cache[cache_key] = surface
            logger.debug(f"Loaded background: {name}")
        else:
            logger.warning(f"Failed to load background: {filepath}")

        return surface

    def get_portrait_for_battle(self, general_id: Optional[int], daimyo_id: int,
                                size: Tuple[int, int] = (220, 220)) -> pygame.Surface:
        """戦闘用の肖像画を取得（フォールバック階層あり）

        Args:
            general_id: 武将ID（Noneの場合は武将なし）
            daimyo_id: 大名ID
            size: 出力サイズ

        Returns:
            肖像画Surface（必ずSurfaceを返す、フォールバックあり）
        """
        # 1. 武将肖像を試す
        if general_id is not None:
            portrait = self.load_general_portrait(general_id, size)
            if portrait:
                return portrait

        # 2. 大名肖像を試す
        portrait = self.load_daimyo_portrait(daimyo_id, size)
        if portrait:
            return portrait

        # 3. フォールバック: 色付き矩形
        color = self._get_daimyo_color(daimyo_id)
        return self.create_fallback_portrait(color, size)

    def create_fallback_portrait(self, color: Tuple[int, int, int], size: Tuple[int, int]) -> pygame.Surface:
        """フォールバック用の色付き矩形を生成

        Args:
            color: RGB色
            size: サイズ（width, height）

        Returns:
            矩形のSurface
        """
        surface = pygame.Surface(size)
        surface.fill(color)

        # 枠線を描画
        border_color = (max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40))
        pygame.draw.rect(surface, border_color, (0, 0, size[0], size[1]), 3)

        # "?" マークを中央に描画
        try:
            font = pygame.font.SysFont('meiryo', min(size[0], size[1]) // 3, bold=True)
            text = font.render("?", True, (255, 255, 255))
            text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
            surface.blit(text, text_rect)
        except:
            pass  # フォント読み込み失敗時は無視

        return surface

    def preload_all_portraits(self):
        """全肖像画をプリロード（起動時に使用）"""
        logger.info("Preloading all portraits...")

        # 武将肖像（1-15）
        for general_id in range(1, 16):
            self.load_general_portrait(general_id, (256, 256))

        # 大名肖像（1-6）
        for daimyo_id in range(1, 7):
            self.load_daimyo_portrait(daimyo_id, (256, 256))

        logger.info(f"Preloaded {len(self._cache)} portraits")

    def clear_cache(self):
        """キャッシュをクリア（メモリ節約用）"""
        self._cache.clear()
        logger.info("Image cache cleared")

    def _load_image(self, filepath: str, size: Optional[Tuple[int, int]]) -> Optional[pygame.Surface]:
        """画像ファイルを読み込む（内部用）

        Args:
            filepath: ファイルパス
            size: リサイズ先サイズ、Noneの場合はリサイズしない

        Returns:
            読み込んだSurface、失敗時はNone
        """
        try:
            # ファイル存在チェック
            if not os.path.exists(filepath):
                return None

            # 画像ロード
            surface = pygame.image.load(filepath)

            # アルファチャンネル変換（高速化）
            surface = surface.convert_alpha()

            # リサイズ
            if size is not None:
                surface = pygame.transform.scale(surface, size)

            return surface

        except pygame.error as e:
            logger.error(f"Pygame error loading {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {filepath}: {e}")
            return None

    def _get_daimyo_color(self, daimyo_id: int) -> Tuple[int, int, int]:
        """大名IDから色を取得（フォールバック用）

        Args:
            daimyo_id: 大名ID (1-6)

        Returns:
            RGB色タプル
        """
        # config.DAIMYO_COLORSからインデックス取得（1始まりなので-1）
        index = max(0, min(daimyo_id - 1, len(config.DAIMYO_COLORS) - 1))
        return config.DAIMYO_COLORS[index]
