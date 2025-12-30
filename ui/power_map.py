"""
PowerMap - 勢力マップ表示ウィジェット
各大名の領土を色分けして視覚的に表示
"""
import pygame
from pygame import gfxdraw
import config
from typing import Dict, List, Optional


class PowerMap:
    """勢力マップ表示クラス"""

    def __init__(self, screen, font, image_manager):
        self.screen = screen
        self.font = font
        self.image_manager = image_manager
        self.small_font = pygame.font.SysFont('meiryo', config.FONT_SIZE_MEDIUM)

        # マップ表示領域の設定（画面右側に配置）
        self.map_x = 500  # 右側に配置
        self.map_y = 40   # もっと上に
        self.map_width = 760
        self.map_height = 560

        # 背景色
        self.bg_color = (25, 20, 15)
        self.border_color = (180, 140, 100)

        # 大名ごとの色（最大8大名分）
        self.daimyo_colors = {
            1: (220, 60, 60),    # 織田 - 赤
            2: (60, 140, 220),   # 武田 - 青
            3: (60, 200, 80),    # 上杉 - 緑
            4: (220, 180, 60),   # 北条 - 黄
            5: (180, 80, 200),   # 毛利 - 紫
            6: (220, 120, 40),   # 斎藤 - オレンジ
            7: (80, 200, 200),   # 今川 - シアン
            8: (200, 80, 120),   # 浅井 - ピンク
        }
        self.neutral_color = (80, 80, 80)  # 無所属 - グレー

        # マップのスケール調整（provinces.jsonのposition座標を画面座標に変換）
        self.scale_x = 1.4
        self.scale_y = 1.1
        self.offset_x = -130
        self.offset_y = -100

        # アニメーション用
        self.highlight_province_id = None
        self.highlight_timer = 0
        self.highlight_duration = 60  # フレーム数

        # マウスオーバー用
        self.hovered_province_id = None
        self.hovered_daimyo_id = None

        # 戦闘演出中の表示制御
        self.frozen_ownership = None  # 凍結された領地所有情報 {province_id: owner_daimyo_id}
        self.is_frozen = False  # フリーズモード（演出中はTrue）

    def freeze(self, game_state):
        """勢力図を現在の状態で凍結（戦闘演出開始時）"""
        self.frozen_ownership = {}
        for province in game_state.provinces.values():
            self.frozen_ownership[province.id] = province.owner_daimyo_id
        self.is_frozen = True

    def unfreeze(self):
        """勢力図の凍結を解除（戦闘演出終了時）"""
        self.is_frozen = False
        self.frozen_ownership = None

    def update_frozen_state(self, game_state):
        """凍結状態を現在の状態に更新（各戦闘終了後）"""
        if self.is_frozen:
            self.frozen_ownership = {}
            for province in game_state.provinces.values():
                self.frozen_ownership[province.id] = province.owner_daimyo_id

    def set_highlight(self, province_id: int):
        """特定の領地をハイライト表示（戦闘後の領地変更時など）"""
        self.highlight_province_id = province_id
        self.highlight_timer = 0

    def update(self, mouse_pos=None, game_state=None):
        """アニメーション更新とマウスオーバー検出"""
        # ハイライトアニメーション
        if self.highlight_province_id is not None:
            self.highlight_timer += 1
            if self.highlight_timer >= self.highlight_duration:
                self.highlight_province_id = None
                self.highlight_timer = 0

        # マウスオーバー検出
        if mouse_pos and game_state:
            self.hovered_province_id = self.get_province_at_position(mouse_pos[0], mouse_pos[1], game_state)
            self.hovered_daimyo_id = self._get_daimyo_at_legend(mouse_pos[0], mouse_pos[1], game_state)
        else:
            self.hovered_province_id = None
            self.hovered_daimyo_id = None

    def draw(self, game_state):
        """勢力マップを描画"""
        # 背景画像を読み込んで描画、なければ単色で塗りつぶし
        # スケール＆トリミング機能を使用
        power_map_bg = self.image_manager.load_background(
            "power_map_background.png",
            target_size=(self.map_width, self.map_height)
        )
        if power_map_bg:
            # スケール＆トリミング済みなのでそのままblit
            self.screen.blit(power_map_bg, (self.map_x, self.map_y))
        else:
            # フォールバック: 単色背景
            pygame.draw.rect(self.screen, self.bg_color,
                            (self.map_x, self.map_y, self.map_width, self.map_height))

        # 枠線（常に描画）
        pygame.draw.rect(self.screen, self.border_color,
                        (self.map_x, self.map_y, self.map_width, self.map_height), 2)

        # タイトル
        title = self.font.render("勢力図", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (self.map_x + 10, self.map_y - 30))

        # 領地間の接続線を先に描画（下層）
        self._draw_connections(game_state)

        # 各領地を描画
        for province in game_state.provinces.values():
            self._draw_province(province, game_state)

        # 凡例を描画
        self._draw_legend(game_state)

        # ツールチップを描画（最前面）
        self._draw_tooltip(game_state)

    def _draw_connections(self, game_state):
        """領地間の接続線を描画"""
        drawn_connections = set()

        for province in game_state.provinces.values():
            for adj_id in province.adjacent_provinces:
                # 既に描画済みの接続はスキップ（双方向なので）
                connection_key = tuple(sorted([province.id, adj_id]))
                if connection_key in drawn_connections:
                    continue
                drawn_connections.add(connection_key)

                adj_province = game_state.get_province(adj_id)
                if not adj_province:
                    continue

                # 座標を計算
                x1, y1 = self._convert_position(province.position)
                x2, y2 = self._convert_position(adj_province.position)

                # 接続線を描画（灰色の縁を追加）
                # まず灰色の線を描画（縁、幅2）
                pygame.draw.line(self.screen, (128, 128, 128), (x1, y1), (x2, y2), 2)
                # 次に通常の線を描画（本体）
                gfxdraw.line(self.screen, x1, y1, x2, y2, (60, 60, 60))

    def _draw_province(self, province, game_state):
        """個別の領地を描画"""
        # 座標を計算
        x, y = self._convert_position(province.position)

        # 大名の色を取得（フリーズモード時は凍結された所有者を使用）
        if self.is_frozen and self.frozen_ownership:
            owner_daimyo_id = self.frozen_ownership.get(province.id, province.owner_daimyo_id)
        else:
            owner_daimyo_id = province.owner_daimyo_id
        color = self._get_daimyo_color(owner_daimyo_id)

        # ハイライト効果
        is_highlighted = (province.id == self.highlight_province_id)
        if is_highlighted:
            # 点滅効果
            pulse = int((self.highlight_timer / 10) % 2)
            if pulse == 0:
                # 外側に光る円を描画（アンチエイリアシング付き、線幅2）
                glow_radius = 30 + int((self.highlight_timer % 10) * 2)
                glow_color = (255, 255, 100)
                for i in range(2):
                    r = glow_radius - i
                    if r > 0:
                        gfxdraw.aacircle(self.screen, x, y, r, glow_color)

        # 領地の円を描画（大きさは農民数に応じて変化）
        base_radius = 27  # 少し大きく
        max_peasants = 11000  # provinces.jsonの最大値
        size_ratio = province.peasants / max_peasants
        radius = int(base_radius * (0.7 + 0.3 * size_ratio))

        # 内側の円（領地の色）- アンチエイリアシング付き
        gfxdraw.filled_circle(self.screen, x, y, radius, color)
        gfxdraw.aacircle(self.screen, x, y, radius, color)

        # 外側の枠 - アンチエイリアシング付き
        border_color = (255, 255, 255) if is_highlighted else (40, 40, 40)
        border_width = 3 if is_highlighted else 2
        for i in range(border_width):
            r = radius - i
            if r > 0:
                gfxdraw.aacircle(self.screen, x, y, r, border_color)

        # 城マーク（has_castleがTrueの場合）
        marker_offset = 0
        if province.has_castle:
            castle_points = [
                (x, y - radius - 5),
                (x - 4, y - radius - 2),
                (x + 4, y - radius - 2)
            ]
            pygame.draw.polygon(self.screen, (255, 215, 0), castle_points)
            marker_offset = 10  # 城マークの分だけずらす

        # コマンド使用済みマーク（✓マーク）
        if province.command_used_this_turn:
            check_x = x + marker_offset
            check_y = y - radius - 5
            # ✓マークを描画（小さなチェック記号）
            check_font = pygame.font.SysFont('meiryo', 12, bold=True)
            check_surface = check_font.render("✓", True, (100, 255, 100))
            check_rect = check_surface.get_rect(center=(check_x, check_y))
            self.screen.blit(check_surface, check_rect)

        # 領地名を表示
        name_surface = self.small_font.render(province.name, True, (240, 240, 240))
        name_rect = name_surface.get_rect()
        name_rect.center = (x, y + radius + 12)

        # 名前の背景（読みやすくするため）
        bg_rect = name_rect.inflate(4, 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(180)
        bg_surface.fill((0, 0, 0))
        self.screen.blit(bg_surface, bg_rect)

        self.screen.blit(name_surface, name_rect)

    def _draw_legend(self, game_state):
        """凡例を描画"""
        legend_x = self.map_x + 10
        legend_y = self.map_y + self.map_height + 10

        # legend_title = self.small_font.render("【凡例】", True, config.UI_TEXT_COLOR)
        # self.screen.blit(legend_title, (legend_x, legend_y))

        #legend_y += 10
        x_offset = 0

        # 各大名の色を表示
        active_daimyos = []
        for daimyo in game_state.daimyo.values():
            if len(daimyo.controlled_provinces) > 0:
                active_daimyos.append(daimyo)

        for i, daimyo in enumerate(active_daimyos):
            color = self._get_daimyo_color(daimyo.id)

            # 2列表示
            if i > 0 and i % 2 == 0:
                legend_y += 22
                x_offset = 0

            current_x = legend_x + x_offset

            # 色の四角
            pygame.draw.rect(self.screen, color, (current_x, legend_y, 15, 15))
            pygame.draw.rect(self.screen, (40, 40, 40), (current_x, legend_y, 15, 15), 1)

            # 大名名と領地数
            province_count = len(daimyo.controlled_provinces)
            text = f"{daimyo.clan_name} ({province_count})"
            text_surface = self.small_font.render(text, True, config.UI_TEXT_COLOR)
            self.screen.blit(text_surface, (current_x + 20, legend_y-6))

            x_offset += 140

        # マークの説明を追加
        legend_y += 30
        mark_font = pygame.font.SysFont('meiryo', 11)

        # 城マーク
        castle_text = "▲ = 城"
        castle_surface = mark_font.render(castle_text, True, (255, 215, 0))
        self.screen.blit(castle_surface, (legend_x, legend_y))

        # チェックマーク
        check_text = "✓ = コマンド使用済み"
        check_surface = mark_font.render(check_text, True, (100, 255, 100))
        self.screen.blit(check_surface, (legend_x + 80, legend_y))

    def _convert_position(self, position: List[int]) -> tuple:
        """provinces.jsonの座標を画面座標に変換"""
        x = self.map_x + self.offset_x + int(position[0] * self.scale_x)
        y = self.map_y + self.offset_y + int(position[1] * self.scale_y)
        return (x, y)

    def _get_daimyo_color(self, daimyo_id: Optional[int]) -> tuple:
        """大名IDから色を取得"""
        if daimyo_id is None:
            return self.neutral_color
        return self.daimyo_colors.get(daimyo_id, self.neutral_color)

    def get_province_at_position(self, mouse_x: int, mouse_y: int, game_state) -> Optional[int]:
        """マウス座標から領地IDを取得（クリック判定用）"""
        for province in game_state.provinces.values():
            x, y = self._convert_position(province.position)

            # クリック判定（円の範囲内）
            dx = mouse_x - x
            dy = mouse_y - y
            distance = (dx * dx + dy * dy) ** 0.5

            base_radius = 18  # _draw_provinceと同じ値
            max_peasants = 11000
            size_ratio = province.peasants / max_peasants
            radius = int(base_radius * (0.7 + 0.3 * size_ratio))

            if distance <= radius:
                return province.id

        return None

    def _get_daimyo_at_legend(self, mouse_x: int, mouse_y: int, game_state) -> Optional[int]:
        """凡例のマウス座標から大名IDを取得"""
        legend_x = self.map_x + 10
        legend_y = self.map_y + self.map_height + 10  

        # アクティブな大名のみ
        active_daimyos = []
        for daimyo in game_state.daimyo.values():
            if len(daimyo.controlled_provinces) > 0:
                active_daimyos.append(daimyo)

        for i, daimyo in enumerate(active_daimyos):
            # 2列表示
            row = i // 2
            col = i % 2
            current_x = legend_x + col * 140
            current_y = legend_y + row * 22

            # 判定領域（色の四角 + テキスト）
            rect = pygame.Rect(current_x, current_y, 130, 15)
            if rect.collidepoint(mouse_x, mouse_y):
                return daimyo.id

        return None

    def _draw_tooltip(self, game_state):
        """ツールチップを描画"""
        if self.hovered_province_id:
            self._draw_province_tooltip(game_state)
        elif self.hovered_daimyo_id:
            self._draw_daimyo_tooltip(game_state)

    def _draw_province_tooltip(self, game_state):
        """領地のツールチップを描画"""
        province = game_state.get_province(self.hovered_province_id)
        if not province:
            return

        # ツールチップの内容
        daimyo = game_state.get_daimyo(province.owner_daimyo_id)
        owner_name = daimyo.clan_name if daimyo else "無所属"

        lines = [
            f"【{province.name}】",
            f"支配: {owner_name}",
        ]

        # 将軍情報を追加
        if province.governor_general_id:
            general = game_state.get_general(province.governor_general_id)
            if general:
                lines.append(f"守将: {general.name}")
                lines.append(f"  武{general.war_skill} 統{general.leadership} 政{general.politics} 知{general.intelligence}")
        else:
            lines.append(f"守将: なし")

        lines.extend([
            f"兵力: {province.soldiers:,}人",
            f"農民: {province.peasants:,}人",
            f"金: {province.gold:,}",
            f"米: {province.rice:,}",
        ])

        # ツールチップのサイズ計算
        max_width = max([self.font.size(line)[0] for line in lines])
        tooltip_width = max_width + 20
        tooltip_height = len(lines) * 20 + 10

        # マウス位置を取得（少しオフセット）
        mouse_pos = pygame.mouse.get_pos()
        tooltip_x = mouse_pos[0] + 15
        tooltip_y = mouse_pos[1] + 15

        # 画面外に出ないように調整
        if tooltip_x + tooltip_width > config.SCREEN_WIDTH:
            tooltip_x = mouse_pos[0] - tooltip_width - 15
        if tooltip_y + tooltip_height > config.SCREEN_HEIGHT:
            tooltip_y = mouse_pos[1] - tooltip_height - 15

        # 背景
        pygame.draw.rect(self.screen, (40, 35, 30), (tooltip_x, tooltip_y, tooltip_width, tooltip_height))
        pygame.draw.rect(self.screen, (200, 180, 140), (tooltip_x, tooltip_y, tooltip_width, tooltip_height), 2)

        # テキスト描画
        y_offset = tooltip_y + 5
        for line in lines:
            text_surface = self.font.render(line, True, (240, 240, 240))
            self.screen.blit(text_surface, (tooltip_x + 10, y_offset))
            y_offset += 20

    def _draw_daimyo_tooltip(self, game_state):
        """大名のツールチップを描画"""
        daimyo = game_state.get_daimyo(self.hovered_daimyo_id)
        if not daimyo:
            return

        # 総兵力、総金、総米を計算
        total_soldiers = 0
        total_gold = 0
        total_rice = 0
        for province_id in daimyo.controlled_provinces:
            province = game_state.get_province(province_id)
            if province:
                total_soldiers += province.soldiers
                total_gold += province.gold
                total_rice += province.rice

        lines = [
            f"【{daimyo.clan_name} {daimyo.name}】",
            f"領地数: {len(daimyo.controlled_provinces)}",
            f"総兵力: {total_soldiers:,}人",
            f"総金: {total_gold:,}",
            f"総米: {total_rice:,}",
        ]

        # ツールチップのサイズ計算
        max_width = max([self.font.size(line)[0] for line in lines])
        tooltip_width = max_width + 20
        tooltip_height = len(lines) * 20 + 10

        # マウス位置を取得
        mouse_pos = pygame.mouse.get_pos()
        tooltip_x = mouse_pos[0] + 15
        tooltip_y = mouse_pos[1] + 15

        # 画面外に出ないように調整
        if tooltip_x + tooltip_width > config.SCREEN_WIDTH:
            tooltip_x = mouse_pos[0] - tooltip_width - 15
        if tooltip_y + tooltip_height > config.SCREEN_HEIGHT:
            tooltip_y = mouse_pos[1] - tooltip_height - 15

        # 背景
        pygame.draw.rect(self.screen, (40, 35, 30), (tooltip_x, tooltip_y, tooltip_width, tooltip_height))
        pygame.draw.rect(self.screen, (200, 180, 140), (tooltip_x, tooltip_y, tooltip_width, tooltip_height), 2)

        # テキスト描画
        y_offset = tooltip_y + 5
        for line in lines:
            text_surface = self.font.render(line, True, (240, 240, 240))
            self.screen.blit(text_surface, (tooltip_x + 10, y_offset))
            y_offset += 20
