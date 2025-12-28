"""
ImageManager - 画像読み込みとキャッシング管理
全ての肖像画と背景画像の一元管理を行う
"""
import pygame
import os
import logging
from typing import Optional, Tuple
from PIL import Image
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

    def load_daimyo_portrait(self, daimyo_id: Optional[int], size: Tuple[int, int] = (256, 256)) -> Optional[pygame.Surface]:
        """大名肖像画を読み込む

        Args:
            daimyo_id: 大名ID (1-6)、Noneの場合は失敗を返す
            size: 出力サイズ（width, height）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # Noneチェック
        if daimyo_id is None:
            logger.warning("daimyo_id is None. Cannot load portrait.")
            return None

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

    def load_background(self, name: str, target_size: Optional[Tuple[int, int]] = None,
                        brightness: float = 1.0) -> Optional[pygame.Surface]:
        """背景画像を読み込む

        Args:
            name: ファイル名（例: "main_background.png"）
            target_size: 目標サイズ（指定時はスケール＆トリミング）
            brightness: 明るさ（0.0=真っ黒、1.0=元の明るさ）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # キャッシュキー（サイズと明るさを含める）
        brightness_str = f"{brightness:.2f}"
        if target_size:
            cache_key = f"bg_{name}_{target_size[0]}x{target_size[1]}_b{brightness_str}"
        else:
            cache_key = f"bg_{name}_b{brightness_str}"

        # キャッシュにあれば返す
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ファイルパス
        filepath = os.path.join(self.backgrounds_path, name)

        # 画像ロード（背景はまず元サイズで読み込む）
        surface = self._load_image(filepath, size=None)

        if surface:
            # サイズ指定がある場合はスケール＆トリミング
            if target_size:
                surface = self._scale_and_crop(surface, target_size)

            # 明るさ調整（1.0未満の場合のみ）
            if brightness < 1.0:
                surface = self._adjust_brightness(surface, brightness)

            self._cache[cache_key] = surface
            logger.debug(f"Loaded background: {name} (brightness={brightness})")
        else:
            logger.warning(f"Failed to load background: {filepath}")

        return surface

    def get_portrait_for_battle(self, general_id: Optional[int], daimyo_id: Optional[int],
                                size: Tuple[int, int] = (220, 220), brightness: float = 1.0) -> pygame.Surface:
        """戦闘用の肖像画を取得（フォールバック階層あり）

        Args:
            general_id: 武将ID（Noneの場合は武将なし）
            daimyo_id: 大名ID（Noneの場合は大名なし）
            size: 出力サイズ
            brightness: 明るさ（0.0=真っ黒、1.0=元の明るさ）

        Returns:
            肖像画Surface（必ずSurfaceを返す、フォールバックあり）
        """
        # 1. 武将肖像を試す
        if general_id is not None:
            portrait = self.load_general_portrait(general_id, size)
            if portrait:
                if brightness < 1.0:
                    portrait = self._adjust_brightness(portrait, brightness)
                return portrait

        # 2. 大名肖像を試す（daimyo_idがNoneでない場合）
        if daimyo_id is not None:
            portrait = self.load_daimyo_portrait(daimyo_id, size)
            if portrait:
                if brightness < 1.0:
                    portrait = self._adjust_brightness(portrait, brightness)
                return portrait

        # 3. 大名も武将もいない場合: general_00.png（デフォルト肖像）を試す
        portrait = self._load_default_portrait(size)
        if portrait:
            if brightness < 1.0:
                portrait = self._adjust_brightness(portrait, brightness)
            return portrait

        # 4. 最終フォールバック: 色付き矩形
        # daimyo_idがNoneの場合はデフォルトカラー（グレー）を使用
        if daimyo_id is not None:
            color = self._get_daimyo_color(daimyo_id)
        else:
            color = (128, 128, 128)  # グレー（中立）
        portrait = self.create_fallback_portrait(color, size)
        if brightness < 1.0:
            portrait = self._adjust_brightness(portrait, brightness)
        return portrait

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

            # リサイズ（高品質）
            if size is not None:
                surface = self._high_quality_scale(surface, size)

            return surface

        except pygame.error as e:
            logger.error(f"Pygame error loading {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {filepath}: {e}")
            return None

    def _load_default_portrait(self, size: Tuple[int, int] = (256, 256)) -> Optional[pygame.Surface]:
        """デフォルト肖像画（general_00.png）を読み込む

        大名も武将もいない領地用の特別な肖像画

        Args:
            size: 出力サイズ（width, height）

        Returns:
            読み込んだSurface、失敗時はNone
        """
        # キャッシュキー生成
        cache_key = f"general_00_{size[0]}x{size[1]}"

        # キャッシュにあれば返す
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ファイルパス
        filename = "general_00.png"
        filepath = os.path.join(self.portraits_path, "generals", filename)

        # 画像ロード
        surface = self._load_image(filepath, size)

        if surface:
            self._cache[cache_key] = surface
            logger.debug(f"Loaded default portrait: {filename}")
        else:
            logger.warning(f"Failed to load default portrait: {filepath}")

        return surface

    def _get_daimyo_color(self, daimyo_id: Optional[int]) -> Tuple[int, int, int]:
        """大名IDから色を取得（フォールバック用）

        Args:
            daimyo_id: 大名ID (1-6)、Noneの場合はグレーを返す

        Returns:
            RGB色タプル
        """
        # daimyo_idがNoneの場合はグレーを返す
        if daimyo_id is None:
            return (128, 128, 128)  # グレー（中立）

        # config.DAIMYO_COLORSからインデックス取得（1始まりなので-1）
        index = max(0, min(daimyo_id - 1, len(config.DAIMYO_COLORS) - 1))
        return config.DAIMYO_COLORS[index]

    def _scale_and_crop(self, surface: pygame.Surface, target_size: Tuple[int, int]) -> pygame.Surface:
        """画像をアスペクト比を維持しながらスケール＆トリミング

        領域全体をカバーするようにスケールし、はみ出た部分をトリミングします。
        （CSS の background-size: cover 相当）

        Args:
            surface: 元のSurface
            target_size: 目標サイズ (width, height)

        Returns:
            スケール＆トリミングされたSurface
        """
        original_width, original_height = surface.get_size()
        target_width, target_height = target_size

        # 元画像と目標サイズのアスペクト比を計算
        original_aspect = original_width / original_height
        target_aspect = target_width / target_height

        # スケール率を計算（領域全体をカバーするため、大きい方を採用）
        if original_aspect > target_aspect:
            # 元画像が横長 → 高さを基準にスケール
            scale_factor = target_height / original_height
        else:
            # 元画像が縦長 → 幅を基準にスケール
            scale_factor = target_width / original_width

        # スケール後のサイズを計算
        scaled_width = int(original_width * scale_factor)
        scaled_height = int(original_height * scale_factor)

        # スケール実行
        scaled_surface = pygame.transform.scale(surface, (scaled_width, scaled_height))

        # トリミング（中央部分を切り出す）
        crop_x = (scaled_width - target_width) // 2
        crop_y = (scaled_height - target_height) // 2

        # 新しいSurfaceを作成してトリミング部分をblit
        result_surface = pygame.Surface(target_size)
        result_surface.blit(scaled_surface, (0, 0), (crop_x, crop_y, target_width, target_height))

        # アルファチャンネル変換
        result_surface = result_surface.convert()

        logger.debug(f"Scaled and cropped: {original_width}x{original_height} -> {target_width}x{target_height}")

        return result_surface

    def _high_quality_scale(self, surface: pygame.Surface, size: Tuple[int, int]) -> pygame.Surface:
        """高品質な画像スケーリング（BICUBIC補間使用）

        Args:
            surface: 元のSurface
            size: 目標サイズ (width, height)

        Returns:
            スケールされたSurface
        """
        # pygame Surface → PIL Image に変換
        # まずSurfaceを文字列バッファに変換
        width, height = surface.get_size()
        image_string = pygame.image.tostring(surface, 'RGBA')
        pil_image = Image.frombytes('RGBA', (width, height), image_string)

        # BICUBIC補間でリサイズ
        pil_image_scaled = pil_image.resize(size, Image.Resampling.BICUBIC)

        # PIL Image → pygame Surface に変換
        image_string_scaled = pil_image_scaled.tobytes()
        scaled_surface = pygame.image.fromstring(image_string_scaled, size, 'RGBA')

        # アルファチャンネル変換（高速化）
        scaled_surface = scaled_surface.convert_alpha()

        logger.debug(f"High-quality scaled: {width}x{height} -> {size[0]}x{size[1]}")

        return scaled_surface

    def _adjust_brightness(self, surface: pygame.Surface, brightness: float) -> pygame.Surface:
        """画像の明るさを調整

        Args:
            surface: 元のSurface
            brightness: 明るさ（0.0=真っ黒、1.0=元の明るさ）

        Returns:
            明るさ調整されたSurface
        """
        # 新しいSurfaceを作成（元と同じサイズ）
        width, height = surface.get_size()
        adjusted_surface = pygame.Surface((width, height))

        # 元画像をコピー
        adjusted_surface.blit(surface, (0, 0))

        # 半透明の黒オーバーレイを作成（明るさに応じて透明度を変更）
        # brightness=1.0 → alpha=0 (完全透明、オーバーレイなし)
        # brightness=0.0 → alpha=255 (完全不透明、真っ黒)
        overlay_alpha = int(255 * (1.0 - brightness))

        if overlay_alpha > 0:
            overlay = pygame.Surface((width, height))
            overlay.set_alpha(overlay_alpha)
            overlay.fill((0, 0, 0))
            adjusted_surface.blit(overlay, (0, 0))

        logger.debug(f"Adjusted brightness: {brightness:.2f} (overlay_alpha={overlay_alpha})")

        return adjusted_surface
