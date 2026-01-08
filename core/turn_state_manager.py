"""
ターン状態管理モジュール

Sequential方式のターン処理フローを管理するクラス
"""
import config


class TurnStateManager:
    """Sequential方式のターン処理フローを管理するクラス"""

    def __init__(self, game_instance):
        """初期化

        Args:
            game_instance: Gameクラスのインスタンス
        """
        self.game = game_instance

    def end_turn_sequential(self):
        """Sequential方式: ターン終了（generator方式）"""
        if not self.game.turn_manager:
            return

        # generatorを開始
        self.game.seq_turn_generator = self.game.turn_manager.execute_turn()
        self.game.seq_mode_state = "processing"

        # 最初のイベントを処理
        self.process_turn_event()

    def process_turn_event(self):
        """Sequential方式: generatorから次のイベントを処理"""
        if not self.game.seq_turn_generator:
            self.on_turn_complete()
            return

        try:
            event = next(self.game.seq_turn_generator)
            event_type = event[0]

            if event_type == "turn_start":
                # ターン開始メッセージ
                message = event[1]
                self.game.add_message(message)
                # ターン1開始時はプロローグBGM終了、AI大名ターンBGMへ
                if self.game.game_state.current_turn == 1:
                    self.game.bgm_manager.play_scene("ai_turn")
                # 次のイベントへ
                self.process_turn_event()

            elif event_type == "message":
                # AI大名の内政コマンドメッセージ
                message = event[1]
                self.game.add_message(message)
                # 次のイベントへ
                self.process_turn_event()

            elif event_type == "death_animation":
                # 死亡演出
                death_data = event[1]
                self.game.seq_mode_state = "animating"
                self.game.daimyo_death_screen.show(
                    death_data,
                    on_finish=self.on_seq_death_animation_finished,
                    on_play=self.game.restart_game,
                    on_end=self.game.quit
                )

            elif event_type == "battle_animation":
                # 戦闘演出
                battle_data = event[1]
                self.game.seq_mode_state = "animating"

                # 戦闘BGMに切り替え
                self.game.bgm_manager.play_scene("battle")

                # 戦闘記録を保存（ログ用）
                self.game.turn_battle_records.append(battle_data)

                # プレビュー → アニメーション
                preview_data = {
                    "attacker_province_id": battle_data["origin_province_id"],
                    "defender_province_id": battle_data["target_province_id"],
                    "attacker_name": battle_data["attacker_name"],
                    "defender_name": battle_data["defender_name"]
                }
                self.game.battle_preview.show(
                    preview_data,
                    on_finish=lambda: self.show_seq_battle_animation(battle_data)
                )

            elif event_type == "ai_action_delay":
                # AI大名の行動決定前のディレイ
                delay_seconds = event[1]
                self.game.seq_mode_state = "ai_action_delay"
                self.game.ai_action_delay_timer = 0
                self.game.ai_action_delay_duration = int(delay_seconds * config.FPS)  # フレーム数に変換
                print(f"[DEBUG-ディレイ] AI行動ディレイ開始: {delay_seconds}秒 ({self.game.ai_action_delay_duration}フレーム)")

            elif event_type == "player_turn":
                # プレイヤーの番
                daimyo_id = event[1]
                self.game.seq_mode_state = "waiting_player_input"
                self.game.player_internal_commands = []
                self.game.player_military_commands = []
                self.game.portrait_highlight_timer = self.game.portrait_highlight_duration  # アニメーション開始

                # プレイヤーターンBGMに切り替え
                self.game.bgm_manager.play_scene("player_turn")

                # 大名名を含むメッセージを表示
                player_daimyo = self.game.game_state.get_player_daimyo()
                if player_daimyo:
                    self.game.add_message(f"【{player_daimyo.clan_name}】行動を決定してください。")
                else:
                    self.game.add_message("【プレイヤー】行動を決定してください。")  # フォールバック

            elif event_type == "victory":
                # 勝利
                player_daimyo = self.game.game_state.get_player_daimyo()
                if player_daimyo:
                    self.game.add_message(f"*** {player_daimyo.clan_name} {player_daimyo.name}が天下統一！***")
                self.game.game_ended = True  # ゲーム終了フラグ
                self.on_turn_complete()

            elif event_type == "game_over":
                # ゲームオーバー
                death_data = event[1]
                self.game.add_message(f"*** {death_data['clan_name']} {death_data['name']}が滅亡しました ***")
                self.game.game_ended = True  # ゲーム終了フラグ
                # 死亡演出は既に表示されているはず

        except StopIteration:
            # ターン終了
            self.on_turn_complete()

    def show_seq_battle_animation(self, battle_data):
        """Sequential方式: 戦闘アニメーションを表示"""
        self.game.battle_animation.show(
            battle_data,
            on_finish=lambda: self.on_seq_battle_animation_finished(battle_data)
        )

    def on_seq_battle_animation_finished(self, battle_data):
        """Sequential方式: 戦闘演出終了時のコールバック"""
        # 戦闘結果は既にturn_managerで適用済み
        # メッセージを表示
        result = battle_data.get("result")
        if result:
            if result.attacker_won:
                self.game.add_message(f" 【{battle_data['attacker_name']}】【戦闘】 {battle_data['defender_province']}を占領")
                # 勢力図をハイライト
                for province in self.game.game_state.provinces.values():
                    if province.name == battle_data['defender_province']:
                        self.game.power_map.set_highlight(province.id)
                        break
            else:
                self.game.add_message(f" 【{battle_data['defender_name']}】【戦闘】 {battle_data['defender_province']}を防衛")

        # 戦闘終了後、BGMを復帰
        # 現在の状態に応じてBGMを切り替え
        if self.game.seq_mode_state == "animating":
            # アニメーション終了後は通常AI大名ターンに戻る
            self.game.bgm_manager.play_scene("ai_turn")

        # 次のイベントへ
        self.process_turn_event()

    def on_seq_death_animation_finished(self):
        """Sequential方式: 死亡演出終了時のコールバック"""
        # 次のイベントへ
        self.process_turn_event()

    def on_turn_complete(self):
        """Sequential方式: ターン完了"""
        self.game.seq_turn_generator = None
        self.game.seq_mode_state = None

        # ターンイベントをメッセージログに追加
        if self.game.turn_manager:
            for event in self.game.turn_manager.get_turn_events():
                # AI大名のコマンドメッセージ、戦闘メッセージ、ターン開始メッセージは既に表示済み
                # 【収入】【維持費】などのプレイヤー向けメッセージのみここで表示
                if ("【戦闘】" not in event and "ターン" not in event and "開始" not in event and
                    "【" not in event or event.startswith(" 【収入】") or event.startswith(" 【維持費】")):
                    self.game.add_message(event)

        # デバッグログ出力（Sequential方式用にturn_managerをturn_managerに参照変更）
        if config.DEBUG_MODE and self.game.debug_logger:
            self._log_turn_state_seq()

        # ターン0以外、かつゲーム終了していない場合は自動的に次のターンへ進む
        if self.game.game_state.current_turn > 0 and not self.game.game_ended:
            self.end_turn_sequential()

    def confirm_player_actions(self):
        """Sequential方式: プレイヤーの行動を確定"""
        if self.game.seq_mode_state != "waiting_player_input":
            return

        # generatorに内政コマンドと軍事コマンドを送信して再開
        self.game.seq_mode_state = "processing"

        # プレイヤーターン終了 → AI大名のターンBGMへ
        self.game.bgm_manager.play_scene("ai_turn")

        try:
            event = self.game.seq_turn_generator.send({
                "internal_commands": self.game.player_internal_commands,
                "military_commands": self.game.player_military_commands
            })
            # 次のイベントを処理（send後に返されたイベント）
            self._handle_seq_event(event)
        except StopIteration:
            self.on_turn_complete()

    def _handle_seq_event(self, event):
        """Sequential方式: イベントをハンドル"""
        event_type = event[0]

        if event_type == "message":
            # AI大名の内政コマンドメッセージ
            message = event[1]
            self.game.add_message(message)
            # 次のイベントを処理
            try:
                next_event = next(self.game.seq_turn_generator)
                self._handle_seq_event(next_event)
            except StopIteration:
                self.on_turn_complete()

        elif event_type == "ai_action_delay":
            # AI大名の行動決定前のディレイ
            delay_seconds = event[1]
            self.game.seq_mode_state = "ai_action_delay"
            self.game.ai_action_delay_timer = 0
            self.game.ai_action_delay_duration = int(delay_seconds * config.FPS)  # フレーム数に変換
            print(f"[DEBUG-ディレイ] AI行動ディレイ開始: {delay_seconds}秒 ({self.game.ai_action_delay_duration}フレーム)")

        elif event_type == "death_animation":
            death_data = event[1]
            self.game.seq_mode_state = "animating"
            self.game.daimyo_death_screen.show(
                death_data,
                on_finish=self.on_seq_death_animation_finished,
                on_play=self.game.restart_game,
                on_end=self.game.quit
            )
        elif event_type == "battle_animation":
            battle_data = event[1]
            self.game.seq_mode_state = "animating"
            self.game.turn_battle_records.append(battle_data)
            preview_data = {
                "attacker_province_id": battle_data["origin_province_id"],
                "defender_province_id": battle_data["target_province_id"],
                "attacker_name": battle_data["attacker_name"],
                "defender_name": battle_data["defender_name"]
            }
            self.game.battle_preview.show(
                preview_data,
                on_finish=lambda: self.show_seq_battle_animation(battle_data)
            )
        elif event_type == "player_turn":
            daimyo_id = event[1]
            self.game.seq_mode_state = "waiting_player_input"
            self.game.player_internal_commands = []
            self.game.player_military_commands = []
            self.game.portrait_highlight_timer = self.game.portrait_highlight_duration  # アニメーション開始
            self.game.add_message("=== あなたの番です ===")
        elif event_type == "victory":
            player_daimyo = self.game.game_state.get_player_daimyo()
            if player_daimyo:
                self.game.add_message(f"*** {player_daimyo.clan_name} {player_daimyo.name}が天下統一！***")
            self.on_turn_complete()
        elif event_type == "game_over":
            death_data = event[1]
            self.game.add_message(f"*** {death_data['clan_name']} {death_data['name']}が滅亡しました ***")

    def _log_turn_state_seq(self):
        """Sequential方式: ターン終了時のゲーム状態をログに出力"""
        self.game.debug_logger.log_turn_state(self.game.game_state, self.game.turn_battle_records, self.game.turn_manager)
        # 戦闘記録をクリア
        self.game.turn_battle_records = []
