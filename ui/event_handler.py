"""
イベント処理モジュール

ユーザー入力（キーボード、マウス）のイベント処理を担当するクラス
"""
import pygame
import config


class EventHandler:
    """ゲームイベントの処理を管理するクラス"""

    def __init__(self, game_instance):
        """初期化

        Args:
            game_instance: Gameクラスのインスタンス
        """
        self.game = game_instance

    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.running = False

            # 大名死亡演出が表示中は最優先で処理
            if self.game.daimyo_death_screen.is_visible:
                self.game.daimyo_death_screen.handle_event(event)
                continue

            # 戦闘プレビューが表示されている場合は優先処理
            if self.game.battle_preview.is_visible:
                self.game.battle_preview.handle_event(event)
                continue

            # 戦闘演出が表示されている場合は優先処理
            if self.game.battle_animation.is_visible:
                self.game.battle_animation.handle_event(event)
                continue

            # 転送ダイアログが表示されている場合は優先処理
            if self.game.transfer_dialog.is_visible:
                self.game.transfer_dialog.handle_event(event)
                continue

            # 将軍配置ダイアログが表示されている場合は優先処理
            if self.game.general_assign_dialog.is_visible:
                self.game.general_assign_dialog.handle_event(event)
                continue

            # イベントダイアログが表示されている場合は優先処理
            if self.game.event_dialog.is_visible:
                self.game.event_dialog.handle_event(event)
                continue

            # イベント履歴画面が表示されている場合
            if self.game.event_history_screen.is_visible:
                self.game.event_history_screen.handle_event(event)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # キャンセル音再生
                    self.game.sound_manager.play("cancel")

                    if self.game.show_province_detail:
                        self.game.close_province_detail()
                    else:
                        self.game.running = False
                # Hキーでイベント履歴を表示
                elif event.key == pygame.K_h:
                    if not self.game.show_province_detail and not self.game.show_attack_selection:
                        self.game.event_history_screen.show(self.game.event_system, self.game.game_state)
                # 矢印キーでメッセージログをスクロール
                elif event.key == pygame.K_UP:
                    self.game.message_scroll_offset = min(self.game.message_scroll_offset + 1, len(self.game.message_log) - self.game.disp_message)
                elif event.key == pygame.K_DOWN:
                    self.game.message_scroll_offset = max(self.game.message_scroll_offset - 1, 0)
                elif event.key == pygame.K_PAGEUP:
                    self.game.message_scroll_offset = min(self.game.message_scroll_offset + 10, len(self.game.message_log) - self.game.disp_message)
                elif event.key == pygame.K_PAGEDOWN:
                    self.game.message_scroll_offset = max(self.game.message_scroll_offset - 10, 0)
            # マウスホイールでスクロール
            elif event.type == pygame.MOUSEWHEEL:
                if not self.game.show_province_detail and not self.game.show_attack_selection:
                    self.game.message_scroll_offset = max(0, min(
                        self.game.message_scroll_offset - event.y * 3,
                        len(self.game.message_log) - self.game.disp_message
                    ))

            # ボタンイベント処理
            if self.game.show_territory_info:
                # 領地情報パネル表示中 - クリックで閉じる
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.game.show_territory_info = False
                    self.game.sound_manager.play("cancel")
            elif self.game.show_attack_selection:
                # 攻撃対象選択画面
                self.game.btn_confirm_attack.handle_event(event)
                self.game.btn_cancel_attack.handle_event(event)
                self.game.btn_attack_25.handle_event(event)
                self.game.btn_attack_50.handle_event(event)
                self.game.btn_attack_75.handle_event(event)
                self.game.btn_attack_100.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_attack_target_click(event.pos)
            elif self.game.show_province_detail:
                self.game.btn_close_detail.handle_event(event)

                # プレイヤーの番のみコマンド実行可能
                can_execute_command = (self.game.seq_mode_state == "waiting_player_input")

                # 将軍配置は常に利用可能（コマンド扱いではない）
                self.game.btn_assign_general.handle_event(event)

                if can_execute_command:
                    self.game.btn_cultivate.handle_event(event)
                    self.game.btn_develop_town.handle_event(event)
                    self.game.btn_flood_control.handle_event(event)
                    self.game.btn_give_rice.handle_event(event)
                    self.game.btn_recruit.handle_event(event)
                    self.game.btn_attack.handle_event(event)
                    self.game.btn_transfer_soldiers.handle_event(event)
                    self.game.btn_transfer_gold.handle_event(event)
                    self.game.btn_transfer_rice.handle_event(event)
            else:
                # プレイヤーの番の場合は「行動決定終了」ボタンを使用
                if self.game.seq_mode_state == "waiting_player_input":
                    self.game.btn_confirm_actions.handle_event(event)
                elif self.game.seq_mode_state is None:  # 処理中でない場合のみ
                    self.game.btn_end_turn.handle_event(event)

                # 領地クリック処理（処理中・アニメーション中は無効）
                if self.game.seq_mode_state not in ("processing", "animating"):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_province_click(event.pos)
                        self.handle_portrait_click(event.pos)

    def handle_province_click(self, pos):
        """領地クリック処理"""
        # 勢力マップ上のクリック判定を優先
        province_id = self.game.power_map.get_province_at_position(pos[0], pos[1], self.game.game_state)
        if province_id:
            province = self.game.game_state.get_province(province_id)
            # プレイヤーの領地のみ選択可能
            if province and province.owner_daimyo_id == 1:
                # 決定音再生
                self.game.sound_manager.play("decide")

                self.game.selected_province_id = province.id
                self.game.show_province_detail = True
                return

        # 簡易的な領地選択（リスト形式）
        y_start = 240
        line_height = 25

        player_provinces = self.game.game_state.get_player_provinces()
        for i, province in enumerate(player_provinces):
            y_pos = y_start + i * line_height
            rect = pygame.Rect(40, y_pos, 600, line_height)

            if rect.collidepoint(pos):
                self.game.selected_province_id = province.id
                self.game.show_province_detail = True
                break

    def handle_portrait_click(self, pos):
        """肖像画クリック処理 - 領地情報パネルを表示"""
        # 肖像画の位置（portrait_y = 70）とサイズ（138x138）
        portrait_rect = pygame.Rect(20, 70, 138, 138)

        if portrait_rect.collidepoint(pos):
            # 領地情報パネルの表示/非表示を切り替え
            self.game.show_territory_info = not self.game.show_territory_info
            self.game.sound_manager.play("decide")

    def handle_attack_target_click(self, pos):
        """攻撃対象クリック処理"""
        if not self.game.selected_province_id:
            return

        origin_province = self.game.game_state.get_province(self.game.selected_province_id)
        if not origin_province:
            return

        # 隣接する敵領地リストを取得
        adjacent_enemies = []
        for adj_id in origin_province.adjacent_provinces:
            adj_province = self.game.game_state.get_province(adj_id)
            if adj_province and adj_province.owner_daimyo_id != origin_province.owner_daimyo_id:
                adjacent_enemies.append(adj_province)

        # クリック位置から選択された領地を判定
        y_start = 200
        line_height = 30
        for i, target in enumerate(adjacent_enemies):
            y_pos = y_start + i * line_height
            rect = pygame.Rect(100, y_pos, 600, line_height)

            if rect.collidepoint(pos):
                # トグル動作: 同じ領地を再クリックで選択解除
                if self.game.selected_attack_target_id == target.id:
                    self.game.selected_attack_target_id = None
                else:
                    self.game.selected_attack_target_id = target.id
                    # 決定音再生
                    self.game.sound_manager.play("decide")
                break
