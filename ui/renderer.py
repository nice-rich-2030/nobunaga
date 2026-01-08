"""
UI描画モジュール

ゲーム画面の描画を担当するクラス
"""
import pygame
import config
from ui.widgets import Panel, ProgressBar


class GameRenderer:
    """ゲーム画面の描画を管理するクラス"""

    def __init__(self, screen, font_large, font_medium, font_small, image_manager, power_map):
        """初期化

        Args:
            screen: Pygameスクリーン
            font_large: 大フォント
            font_medium: 中フォント
            font_small: 小フォント
            image_manager: 画像マネージャー
            power_map: 勢力マップ
        """
        self.screen = screen
        self.font_large = font_large
        self.font_medium = font_medium
        self.font_small = font_small
        self.image_manager = image_manager
        self.power_map = power_map

    def render_main(self, game_state, ui_state, economy_system, buttons, dialogs):
        """メイン描画ディスパッチャー

        Args:
            game_state: ゲーム状態
            ui_state: UI状態辞書
            economy_system: 経済システム
            buttons: ボタン辞書
            dialogs: ダイアログ辞書
        """
        # 背景画像を描画
        main_bg = self.image_manager.load_background(
            "main_background.png",
            target_size=(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        if main_bg:
            self.screen.blit(main_bg, (0, 0))
        else:
            self.screen.fill(config.UI_BG_COLOR)

        # 画面状態に応じて描画
        if ui_state['show_attack_selection']:
            self.render_attack_selection(game_state, ui_state, buttons)
        elif ui_state['show_province_detail']:
            self.render_province_detail(game_state, ui_state, buttons)
        else:
            self.render_main_map(game_state, ui_state, economy_system, buttons)

        # ダイアログ・オーバーレイを最前面に描画
        self._render_overlays(dialogs, ui_state)

        pygame.display.flip()

    def _render_overlays(self, dialogs, ui_state):
        """ダイアログとオーバーレイを描画

        Args:
            dialogs: ダイアログ辞書
            ui_state: UI状態辞書
        """
        # 戦闘プレビュー画面
        if dialogs['battle_preview'].is_visible:
            dialogs['battle_preview'].draw(dialogs['game_state'])

        # 戦闘演出画面
        if dialogs['battle_animation'].is_visible:
            dialogs['battle_animation'].draw()

        # イベントダイアログ
        if dialogs['event_dialog'].is_visible:
            dialogs['event_dialog'].draw()

        # イベント履歴画面
        if dialogs['event_history_screen'].is_visible:
            dialogs['event_history_screen'].draw()

        # 転送ダイアログ
        if dialogs['transfer_dialog'].is_visible:
            dialogs['transfer_dialog'].draw()

        # 将軍配置ダイアログ
        if dialogs['general_assign_dialog'].is_visible:
            dialogs['general_assign_dialog'].draw()

        # 大名死亡演出画面
        if dialogs['daimyo_death_screen'].is_visible:
            dialogs['daimyo_death_screen'].draw()

        # 領地情報パネル
        if ui_state['show_territory_info']:
            self.draw_territory_info_panel(dialogs['game_state'], ui_state)

    def render_main_map(self, game_state, ui_state, economy_system, buttons):
        """メインマップ画面を描画

        Args:
            game_state: ゲーム状態
            ui_state: UI状態辞書
            economy_system: 経済システム
            buttons: ボタン辞書
        """
        # 背景画像を描画（明るさ調整付き）
        main_bg = self.image_manager.load_background(
            "main_background.png",
            target_size=(config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            brightness=config.BACKGROUND_BRIGHTNESS
        )
        if main_bg:
            self.screen.blit(main_bg, (0, 0))
        else:
            self.screen.fill(config.UI_BG_COLOR)

        # タイトルとターン情報
        title = self.font_large.render("戦国時代 ～織田信長～", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (20, 20))

        season_name = game_state.get_season_name()
        year = game_state.get_year()
        turn_info = f"ターン {game_state.current_turn} - {season_name} {year}年"
        turn_text = self.font_medium.render(turn_info, True, config.UI_TEXT_COLOR)
        title_width = title.get_width()
        self.screen.blit(turn_text, (20 + title_width + 30, 28))

        # プレイヤー情報
        player = game_state.get_player_daimyo()
        if player:
            self._draw_player_info(player, economy_system, ui_state)

        # 勢力マップを描画
        self.power_map.draw(game_state)

        # 大名健康状態表示
        self.draw_daimyo_health_status(game_state)

        # ボタン
        if ui_state['seq_mode_state'] == "waiting_player_input":
            buttons['confirm_actions'].draw(self.screen)
        elif ui_state['seq_mode_state'] is None:
            if game_state.current_turn == 0:
                buttons['end_turn'].text = "統一開始"
            else:
                buttons['end_turn'].text = "次のターンへ"
            buttons['end_turn'].draw(self.screen)

        # 操作説明
        help_y = config.SCREEN_HEIGHT - 30
        help_text = "操作: [ESC]終了 [H]イベント履歴 [↑↓]ログスクロール"
        text = self.font_small.render(help_text, True, config.LIGHT_GRAY)
        self.screen.blit(text, (100, help_y))

        # メッセージログ
        self._draw_message_log(ui_state)

    def _draw_player_info(self, player, economy_system, ui_state):
        """プレイヤー情報を描画

        Args:
            player: プレイヤー大名
            economy_system: 経済システム
            ui_state: UI状態辞書
        """
        portrait_y = 70
        portrait_size = (138, 138)
        player_portrait = self.image_manager.get_portrait_for_battle(
            None, player.id, portrait_size
        )
        self.screen.blit(player_portrait, (20, portrait_y))

        # 枠の描画（アニメーション中は強調）
        if ui_state['portrait_highlight_timer'] > 0:
            alpha = int(128 + 127 * (ui_state['portrait_highlight_timer'] / ui_state['portrait_highlight_duration']))
            thickness = 3 + int(2 * (ui_state['portrait_highlight_timer'] / ui_state['portrait_highlight_duration']))
            highlight_color = (255, 215, 0, alpha)
            pygame.draw.rect(self.screen, highlight_color[:3], (20, portrait_y, 138, 138), thickness)
        else:
            pygame.draw.rect(self.screen, config.UI_HIGHLIGHT_COLOR, (20, portrait_y, 138, 138), 2)

        # 大名情報
        text_x = 168
        player_info = f"大名: {player.clan_name} {player.name}"
        player_text = self.font_medium.render(player_info, True, config.UI_TEXT_COLOR)
        self.screen.blit(player_text, (text_x, portrait_y + 5))

        province_count = len(player.controlled_provinces)
        total_provinces = ui_state['total_provinces']
        count_text = f"支配領地: {province_count}/{total_provinces}"
        count_render = self.font_small.render(count_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(count_render, (text_x, portrait_y + 40))

        # 総収支表示
        income = economy_system.calculate_total_income(player.id)
        upkeep = economy_system.calculate_total_upkeep(player.id)
        balance_text = f"総収入: 金{income['gold']} 米{income['rice']}  総維持: 米{upkeep['rice']}"
        balance_render = self.font_small.render(balance_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(balance_render, (text_x, portrait_y + 70))

    def _draw_message_log(self, ui_state):
        """メッセージログを描画

        Args:
            ui_state: UI状態辞書
        """
        log_y_start = 220
        log_y = log_y_start

        log_title = self.font_small.render("=== 軍報 ===", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(log_title, (20, log_y))

        message_log = ui_state['message_log']
        message_scroll_offset = ui_state['message_scroll_offset']
        disp_message = ui_state['disp_message']

        # スクロール位置の表示
        if len(message_log) > disp_message:
            scroll_info = f"({len(message_log) - message_scroll_offset - disp_message}/{len(message_log)})"
            scroll_text = self.font_small.render(scroll_info, True, config.LIGHT_GRAY)
            self.screen.blit(scroll_text, (250, log_y))

        log_y += 25

        # スクロール位置に基づいて表示
        if len(message_log) <= disp_message:
            display_messages = message_log
        else:
            start_idx = max(0, len(message_log) - disp_message - message_scroll_offset)
            end_idx = len(message_log) - message_scroll_offset
            display_messages = message_log[start_idx:end_idx]

        for message in display_messages:
            display_message = message[:100]
            msg_text = self.font_small.render(display_message, True, config.LIGHT_GRAY)
            self.screen.blit(msg_text, (30, log_y))
            log_y += 16

    def draw_daimyo_health_status(self, game_state):
        """天下情勢（全大名の状態）を表示

        Args:
            game_state: ゲーム状態
        """
        # 画面右側に表示
        panel_x = 510
        panel_y = 40
        panel_width = 340

        # タイトル
        title = self.font_medium.render("=== 天下情勢 ===", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (panel_x, panel_y))

        y_pos = panel_y + 27

        # 全大名の情報を表示
        for daimyo in sorted(game_state.daimyo.values(), key=lambda d: d.id):
            # 生存状態のアイコン
            if daimyo.is_alive:
                alive_icon = "●"
                if daimyo.health > 50:
                    alive_color = config.STATUS_GOOD  # 緑
                elif daimyo.health > 30:
                    alive_color = config.STATUS_NEUTRAL  # 黄
                else:
                    alive_color = config.STATUS_BAD  # 赤
            else:
                alive_icon = "×"
                alive_color = config.GRAY

            # 大名名
            name_text = f"{alive_icon} {daimyo.clan_name} {daimyo.name}"
            name_surface = self.font_small.render(name_text, True, alive_color)
            self.screen.blit(name_surface, (panel_x, y_pos))

            # 健康度と年齢
            if daimyo.is_alive:
                status_text = f"健康{daimyo.health} 年齢{daimyo.age} 領{len(daimyo.controlled_provinces)}"
                status_color = config.UI_TEXT_COLOR
            else:
                status_text = "死亡"
                status_color = config.GRAY

            status_surface = self.font_small.render(status_text, True, status_color)
            self.screen.blit(status_surface, (panel_x + 90, y_pos))

            y_pos += 24

    def draw_territory_info_panel(self, game_state, ui_state):
        """支配領地情報パネルを描画

        Args:
            game_state: ゲーム状態
            ui_state: UI状態辞書
        """
        # 半透明の背景
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # パネルサイズと位置
        panel_width = 600
        panel_height = 500
        panel_x = (config.SCREEN_WIDTH - panel_width) // 2
        panel_y = (config.SCREEN_HEIGHT - panel_height) // 2

        # パネル背景
        pygame.draw.rect(self.screen, config.UI_PANEL_COLOR,
                        (panel_x, panel_y, panel_width, panel_height))
        pygame.draw.rect(self.screen, config.UI_BORDER_COLOR,
                        (panel_x, panel_y, panel_width, panel_height), 3)

        # タイトル
        player = game_state.get_player_daimyo()
        title_text = f"=== {player.clan_name} 支配領地一覧 ==="
        title = self.font_large.render(title_text, True, config.UI_HIGHLIGHT_COLOR)
        title_rect = title.get_rect(centerx=panel_x + panel_width // 2, top=panel_y + 15)
        self.screen.blit(title, title_rect)

        # 閉じる説明
        close_text = "（画面をクリックで閉じる）"
        close_render = self.font_small.render(close_text, True, config.LIGHT_GRAY)
        close_rect = close_render.get_rect(centerx=panel_x + panel_width // 2, top=panel_y + 45)
        self.screen.blit(close_render, close_rect)

        # 領地一覧ヘッダー
        header_y = panel_y + 80
        # ヘッダーを2つに分けてデータと同じ位置に描画
        header_name = self.font_medium.render("領地(守将)", True, config.UI_TEXT_COLOR)
        header_info = self.font_medium.render("     金      米    農民    兵士    開発     町     治水", True, config.UI_TEXT_COLOR)
        self.screen.blit(header_name, (panel_x + 20, header_y))
        self.screen.blit(header_info, (panel_x + 170, header_y))

        # 領地リスト
        y_pos = header_y + 30
        player_provinces = game_state.get_player_provinces()

        for province in player_provinces:
            # 領地名
            if province.governor_general_id:
                general = game_state.get_general(province.governor_general_id)
                name_text = f"{province.name}({general.name})"
            else:
                name_text = province.name
            name_render = self.font_medium.render(name_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(name_render, (panel_x + 20, y_pos))

            # 資源情報
            info_text = f"{province.gold:5} {province.rice:6} {province.peasants:6} {province.soldiers:6} {province.development_level:7} {province.town_level:7} {province.flood_control:7}%"
            info_render = self.font_medium.render(info_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(info_render, (panel_x + 170, y_pos))

            y_pos += 22

        # 合計を表示
        total_y = panel_y + panel_height - 60
        pygame.draw.line(self.screen, config.UI_BORDER_COLOR,
                        (panel_x + 20, total_y - 5),
                        (panel_x + panel_width - 20, total_y - 5), 2)

        total_gold = sum(p.gold for p in player_provinces)
        total_rice = sum(p.rice for p in player_provinces)
        total_peasants = sum(p.peasants for p in player_provinces)
        total_soldiers = sum(p.soldiers for p in player_provinces)

        total_text = f"合計: 金{total_gold}  米{total_rice}  農民{total_peasants}  兵士{total_soldiers}  領地数{len(player_provinces)}"
        total_render = self.font_medium.render(total_text, True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(total_render, (panel_x + 20, total_y + 5))

    def render_province_detail(self, game_state, ui_state, buttons, economy_system, transfer_system):
        """領地詳細パネルを描画

        Args:
            game_state: ゲーム状態
            ui_state: UI状態辞書
            buttons: ボタン辞書
            economy_system: 経済システム
            transfer_system: 転送システム
        """
        selected_province_id = ui_state.get('selected_province_id')
        seq_mode_state = ui_state.get('seq_mode_state')

        province = game_state.get_province(selected_province_id)
        if not province:
            return

        # 背景パネル
        panel = Panel(60, 60, config.SCREEN_WIDTH - 120, config.SCREEN_HEIGHT - 120,
                      f"{province.name} の詳細", self.font_large)
        panel.draw(self.screen)

        # 領地情報
        y = 100
        info_lines = [
            f"地形: {province.terrain_type}  城: {'有' if province.has_castle else '無'}",
            f"",
            f"=== リソース ===",
            f"金: {province.gold}  (収入: +{province.calculate_tax_income()}/ターン)",
            f"米: {province.rice}  (生産: +{province.calculate_rice_production()}, 消費: -{province.calculate_soldier_rice_consumption()}/ターン)",
            f"",
            f"=== 人口 ===",
            f"農民: {province.peasants} / {province.max_peasants}",
            f"兵士: {province.soldiers}",
        ]

        # 戦闘力セクション
        info_lines.append(f"")
        info_lines.append(f"=== 戦闘力 ===")

        # 守将情報
        general = None
        if province.governor_general_id:
            general = game_state.get_general(province.governor_general_id)
            info_lines.append(f"守将: {general.name} (武力{general.war_skill} 統率{general.leadership} 政治{general.politics} 知力{general.intelligence})")
        else:
            info_lines.append(f"守将: なし")

        # 防御力計算
        base_defense_power = province.get_combat_power()
        defense_bonus = province.get_defense_bonus()
        general_bonus = general.get_combat_bonus() if general else 1.0

        final_defense_power = int(base_defense_power * defense_bonus * general_bonus)

        # 士気補正を計算（基本戦闘力に含まれる）
        morale_mult = 1.0
        if province.soldier_morale > 50:
            morale_mult = 1.0 + (province.soldier_morale - 50) * config.MORALE_COMBAT_MODIFIER
        elif province.soldier_morale < 50:
            morale_mult = max(0.5, 1.0 - (50 - province.soldier_morale) * config.MORALE_COMBAT_MODIFIER)

        # 攻撃力計算
        expedition_penalty = 0.8
        base_attack_power = base_defense_power  # 基本戦闘力は同じ
        final_attack_power = int(base_attack_power * expedition_penalty * general_bonus)

        info_lines.append(f"防御力: {final_defense_power:,} (兵{province.soldiers} × 士気{morale_mult:.2f} × 地形{defense_bonus:.2f} × 将軍{general_bonus:.2f})")
        info_lines.append(f"攻撃力: {final_attack_power:,} (兵{province.soldiers} × 士気{morale_mult:.2f} × 遠征{expedition_penalty:.2f} × 将軍{general_bonus:.2f})")

        # 開発セクション
        info_lines.extend([
            f"",
            f"=== 開発 ===",
            f"開発レベル: {province.development_level}/10  町レベル: {province.town_level}/10",
            f"治水レベル: {province.flood_control}%",
            f"税率: {province.tax_rate}%",
        ])

        for line in info_lines:
            text = self.font_small.render(line, True, config.UI_TEXT_COLOR)
            self.screen.blit(text, (100, y))
            y += 22

        # 忠誠度バー
        loyalty_label = self.font_small.render("農民忠誠度:", True, config.UI_TEXT_COLOR)
        self.screen.blit(loyalty_label, (100, 535))
        loyalty_bar = ProgressBar(100, 560, 300, 20, 100, province.peasant_loyalty)
        loyalty_bar.draw(self.screen, self.font_small)

        # 士気バー
        morale_label = self.font_small.render("兵士士気:", True, config.UI_TEXT_COLOR)
        self.screen.blit(morale_label, (100, 595))
        morale_bar = ProgressBar(100, 620, 300, 20, 100, province.soldier_morale)
        morale_bar.draw(self.screen, self.font_small)

        # 内政コマンドパネル
        cmd_panel = Panel(520, 220-60, 220, 250, "内政コマンド", self.font_medium)
        cmd_panel.draw(self.screen)

        # プレイヤーの番のみコマンド実行可能
        can_execute_command = (seq_mode_state == "waiting_player_input")

        # 内政ボタンの有効/無効を設定と描画
        btn_cultivate = buttons.get('cultivate')
        btn_develop_town = buttons.get('develop_town')
        btn_flood_control = buttons.get('flood_control')
        btn_give_rice = buttons.get('give_rice')

        if btn_cultivate:
            btn_cultivate.set_enabled(
                can_execute_command and
                province.can_afford(gold=config.CULTIVATION_COST) and not province.command_used_this_turn
            )
            btn_cultivate.draw(self.screen)

        if btn_develop_town:
            btn_develop_town.set_enabled(
                can_execute_command and
                province.can_afford(gold=config.TOWN_DEVELOPMENT_COST) and not province.command_used_this_turn
            )
            btn_develop_town.draw(self.screen)

        if btn_flood_control:
            btn_flood_control.set_enabled(
                can_execute_command and
                province.can_afford(gold=config.FLOOD_CONTROL_COST) and not province.command_used_this_turn
            )
            btn_flood_control.draw(self.screen)

        if btn_give_rice:
            btn_give_rice.set_enabled(
                can_execute_command and
                province.can_afford(rice=config.GIVE_RICE_AMOUNT) and not province.command_used_this_turn
            )
            btn_give_rice.draw(self.screen)

        # ステータスメッセージ表示
        if province.command_used_this_turn:
            status_text = self.font_small.render("このターンのコマンドは実行済みです", True, config.STATUS_NEUTRAL)
            self.screen.blit(status_text, (840, 680))
        elif not can_execute_command:
            status_text = self.font_small.render("将軍を配置できます。", True, config.STATUS_NEUTRAL)
            self.screen.blit(status_text, (840, 680))

        # 軍事コマンドパネル
        mil_panel = Panel(520, 500-60, 220, 140, "軍事コマンド", self.font_medium)
        mil_panel.draw(self.screen)

        # 軍事ボタンの有効/無効を設定
        recruit_cost = 100 * config.RECRUIT_COST_PER_SOLDIER  # 100人 × 2 = 200金
        btn_recruit = buttons.get('recruit')
        btn_attack = buttons.get('attack')

        if btn_recruit:
            btn_recruit.set_enabled(
                can_execute_command and
                province.peasants >= 100 and
                province.gold >= recruit_cost and
                not province.command_used_this_turn
            )
            btn_recruit.draw(self.screen)

        if btn_attack:
            btn_attack.set_enabled(
                can_execute_command and
                province.soldiers >= 100 and not province.command_used_this_turn
            )
            btn_attack.draw(self.screen)

        # 転送コマンドパネル
        transfer_panel = Panel(770, 220-60, 220, 250, "転送コマンド", self.font_medium)
        transfer_panel.draw(self.screen)

        # 転送可能な隣接領地があるかチェック
        valid_targets = transfer_system.get_valid_transfer_targets(selected_province_id)
        has_targets = len(valid_targets) > 0

        # 転送ボタンの有効/無効を設定
        btn_transfer_soldiers = buttons.get('transfer_soldiers')
        btn_transfer_gold = buttons.get('transfer_gold')
        btn_transfer_rice = buttons.get('transfer_rice')

        if btn_transfer_soldiers:
            btn_transfer_soldiers.set_enabled(
                can_execute_command and
                has_targets and province.soldiers > 10 and not province.command_used_this_turn
            )
            btn_transfer_soldiers.draw(self.screen)

        if btn_transfer_gold:
            btn_transfer_gold.set_enabled(
                can_execute_command and
                has_targets and province.gold > 0 and not province.command_used_this_turn
            )
            btn_transfer_gold.draw(self.screen)

        if btn_transfer_rice:
            btn_transfer_rice.set_enabled(
                can_execute_command and
                has_targets and province.rice > 0 and not province.command_used_this_turn
            )
            btn_transfer_rice.draw(self.screen)

        # 将軍配置ボタンの有効化設定と描画
        # 将軍配置はコマンド扱いではないので自領地であれば常に利用可能
        player_daimyo = game_state.get_daimyo(game_state.player_daimyo_id)
        is_own_province = (
            player_daimyo and
            province.owner_daimyo_id == player_daimyo.id
        )
        can_assign_general = is_own_province

        btn_assign_general = buttons.get('assign_general')
        if btn_assign_general:
            btn_assign_general.set_enabled(can_assign_general)
            btn_assign_general.draw(self.screen)

        # 転送情報の表示
        transfer_info_y = 490-70
        if has_targets:
            info_text = f"転送できる隣接領地: {len(valid_targets)}箇所"
        else:
            info_text = "転送できる隣接領地なし"
        text = self.font_small.render(info_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(text, (810, transfer_info_y))

        # 戻るボタン
        btn_close_detail = buttons.get('close_detail')
        if btn_close_detail:
            btn_close_detail.draw(self.screen)

    def render_attack_selection(self, game_state, ui_state, buttons):
        """攻撃対象選択画面を描画

        Args:
            game_state: ゲーム状態
            ui_state: UI状態辞書
            buttons: ボタン辞書
        """
        selected_province_id = ui_state.get('selected_province_id')
        selected_attack_target_id = ui_state.get('selected_attack_target_id')
        selected_attack_ratio = ui_state.get('selected_attack_ratio', 0.5)

        if not selected_province_id:
            return

        origin_province = game_state.get_province(selected_province_id)
        if not origin_province:
            return

        # 背景パネル
        panel = Panel(50, 50, config.SCREEN_WIDTH - 100, config.SCREEN_HEIGHT - 100,
                      "攻撃対象を選択", self.font_large)
        panel.draw(self.screen)

        # 出発地情報
        y = 120
        info_text = f"出発地: {origin_province.name}  兵力: {origin_province.soldiers}人"
        text = self.font_medium.render(info_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(text, (100, y))

        # 選択中の兵力比率を表示
        y += 30
        selected_troops = int(origin_province.soldiers * selected_attack_ratio)
        ratio_text = f"派遣兵力: {selected_troops}人 ({int(selected_attack_ratio * 100)}%)  残留: {origin_province.soldiers - selected_troops}人"
        ratio_render = self.font_medium.render(ratio_text, True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(ratio_render, (100, y))

        # 隣接する敵領地リストを取得
        adjacent_enemies = []
        for adj_id in origin_province.adjacent_provinces:
            adj_province = game_state.get_province(adj_id)
            if adj_province and adj_province.owner_daimyo_id != origin_province.owner_daimyo_id:
                adjacent_enemies.append(adj_province)

        y = 170
        if not adjacent_enemies:
            no_enemy_text = self.font_medium.render("攻撃可能な敵領地がありません", True, config.STATUS_NEGATIVE)
            self.screen.blit(no_enemy_text, (100, y))
        else:
            title_text = self.font_medium.render("=== 攻撃可能な領地 ===", True, config.UI_HIGHLIGHT_COLOR)
            self.screen.blit(title_text, (100, y))

            y = 200
            for target in adjacent_enemies:
                # 選択中の領地をハイライト表示
                if selected_attack_target_id == target.id:
                    highlight_rect = pygame.Rect(100, y, 600, 30)
                    pygame.draw.rect(self.screen, config.UI_HIGHLIGHT_COLOR, highlight_rect)
                    text_color = config.BLACK
                else:
                    text_color = config.UI_TEXT_COLOR

                owner = game_state.get_daimyo(target.owner_daimyo_id)
                owner_name = owner.clan_name if owner else "無所属"

                info = f"{target.name} ({owner_name})  守備兵: {target.soldiers}人  城: {'有' if target.has_castle else '無'}"
                text = self.font_small.render(info, True, text_color)
                self.screen.blit(text, (120, y))

                # 勝率予測（選択中の比率を使用）
                attack_force = int(origin_province.soldiers * selected_attack_ratio)
                if attack_force > target.soldiers * 1.5:
                    recommendation = "有利"
                    color = config.STATUS_POSITIVE
                elif attack_force > target.soldiers:
                    recommendation = "互角"
                    color = config.STATUS_NEUTRAL
                else:
                    recommendation = "不利"
                    color = config.STATUS_NEGATIVE

                pred_text = self.font_small.render(f"  予測: {recommendation}", True, text_color if selected_attack_target_id == target.id else color)
                self.screen.blit(pred_text, (650, y))

                y += 30

        # 説明
        help_text = self.font_small.render("領地をクリックして選択", True, config.LIGHT_GRAY)
        self.screen.blit(help_text, (100, config.SCREEN_HEIGHT - 150))

        # 兵力選択ボタンを描画（選択中のボタンをハイライト）
        ratio_label = self.font_medium.render("派遣規模:", True, config.UI_TEXT_COLOR)
        self.screen.blit(ratio_label, (100, config.SCREEN_HEIGHT - 195))

        # 選択中のボタンは強調表示
        btn_attack_25 = buttons.get('attack_25')
        btn_attack_50 = buttons.get('attack_50')
        btn_attack_75 = buttons.get('attack_75')
        btn_attack_100 = buttons.get('attack_100')

        for btn, ratio in [(btn_attack_25, config.ATTACK_RATIO_OPTIONS[0]),
                           (btn_attack_50, config.ATTACK_RATIO_OPTIONS[1]),
                           (btn_attack_75, config.ATTACK_RATIO_OPTIONS[2]),
                           (btn_attack_100, config.ATTACK_RATIO_OPTIONS[3])]:
            if btn and abs(selected_attack_ratio - ratio) < 0.01:
                # 選択中: ホバー状態を一時的にTrueにして描画
                original_hover = btn.is_hovered
                btn.is_hovered = True
                btn.draw(self.screen)
                btn.is_hovered = original_hover

                # 選択マーカーを追加（ボタンの下に小さな三角形）
                marker_x = btn.rect.centerx
                marker_y = btn.rect.bottom + 3
                marker_points = [
                    (marker_x, marker_y),
                    (marker_x - 5, marker_y + 5),
                    (marker_x + 5, marker_y + 5)
                ]
                pygame.draw.polygon(self.screen, config.UI_HIGHLIGHT_COLOR, marker_points)
            elif btn:
                btn.draw(self.screen)

        # ボタン表示
        # 決定ボタンは選択中のみ有効化
        btn_confirm_attack = buttons.get('confirm_attack')
        btn_cancel_attack = buttons.get('cancel_attack')

        if btn_confirm_attack:
            if selected_attack_target_id is not None:
                btn_confirm_attack.enabled = True
            else:
                btn_confirm_attack.enabled = False
            btn_confirm_attack.draw(self.screen)

        if btn_cancel_attack:
            btn_cancel_attack.draw(self.screen)
