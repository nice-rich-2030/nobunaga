"""
戦国時代 ～織田信長～ - メインエントリーポイント
pygameを使用した戦略シミュレーションゲーム
"""
import pygame
import sys
import config
from core.game_initializer import (
    initialize_pygame,
    initialize_managers,
    initialize_game_systems,
    create_ui_components,
    create_buttons
)
from debug.debug_logger import DebugLogger
from ui.power_map import PowerMap
from ui.renderer import GameRenderer
from ui.event_handler import EventHandler
from commands.command_executor import CommandExecutor
from commands.transfer_handler import TransferHandler
from animation.animation_manager import AnimationManager
from core.turn_state_manager import TurnStateManager


class Game:
    """メインゲームクラス"""

    def __init__(self):
        # Pygameとリソースの初期化
        self.screen, self.clock, self.font_large, self.font_medium, self.font_small = initialize_pygame()
        self.image_manager, self.sound_manager, self.bgm_manager = initialize_managers()

        # ゲームシステムの初期化
        systems = initialize_game_systems()
        self.game_state = systems['game_state']
        self.economy_system = systems['economy_system']
        self.internal_affairs = systems['internal_affairs']
        self.turn_manager = systems['turn_manager']
        self.military_system = systems['military_system']
        self.combat_system = systems['combat_system']
        self.diplomacy_system = systems['diplomacy_system']
        self.transfer_system = systems['transfer_system']
        self.ai_system = systems['ai_system']
        self.event_system = systems['event_system']

        # デバッグログの初期化
        self.debug_logger = DebugLogger()

        # ゲーム実行フラグ
        self.running = True
        self.game_ended = False  # ゲーム終了フラグ（勝利/敗北）

        # AI行動ディレイ制御
        self.ai_action_delay_timer = 0
        self.ai_action_delay_duration = 0

        # UI状態
        self.selected_province_id = None
        self.selected_attack_target_id = None  # 攻撃対象として選択中の領地ID
        self.selected_attack_ratio = config.ATTACK_RATIO_OPTIONS[2]  # 攻撃時の兵力比率（デフォルト75%）
        self.show_province_detail = False
        self.show_attack_selection = False
        self.show_territory_info = False  # 肖像クリックで領地情報を表示
        self.message_log = []
        self.message_scroll_offset = 0  # メッセージログのスクロール位置
        self.disp_message = 26  # 支配領地リストを削除したため大幅に増加

        # 戦闘演出管理
        self.pending_battle_animations = []  # 表示待ちの戦闘演出
        self.pending_turn_messages = []  # 演出後に表示するメッセージ
        self.pending_winner_message = None  # 演出後に表示する勝利メッセージ
        self.current_battle_index = 0  # 現在表示中の戦闘インデックス

        # 大名死亡演出管理
        self.pending_daimyo_death_animations = []  # 表示待ちの大名死亡演出
        self.current_death_index = 0  # 現在表示中の死亡演出インデックス

        # 戦闘記録（ターンごとにリセット）
        self.turn_battle_records = []  # このターンの戦闘記録

        # デバッグログ出力フラグ
        self.need_log_turn_state = False  # ターン終了時にログ出力が必要かどうか

        # Sequential方式の状態管理
        self.seq_mode_state = None  # "waiting_player_input" / "animating" / None
        self.seq_turn_generator = None  # generatorの参照保持
        self.player_internal_commands = []  # プレイヤーが登録した内政コマンド
        self.player_military_commands = []  # プレイヤーが登録した軍事コマンド

        # プレイヤーの番強調アニメーション（2.5秒 = 75フレーム）
        self.portrait_highlight_timer = 0
        self.portrait_highlight_duration = 75  # 2.5秒 @ 30FPS

        # UIコンポーネントとボタンの作成
        self.power_map = PowerMap(self.screen, self.font_medium, self.image_manager)
        ui_components = create_ui_components(
            self.screen, self.font_large, self.font_medium, self.font_small,
            self.image_manager, self.sound_manager, self.power_map
        )
        self.event_dialog = ui_components['event_dialog']
        self.event_history_screen = ui_components['event_history_screen']
        self.battle_preview = ui_components['battle_preview']
        self.battle_animation = ui_components['battle_animation']
        self.daimyo_death_screen = ui_components['daimyo_death_screen']
        self.transfer_dialog = ui_components['transfer_dialog']
        self.general_assign_dialog = ui_components['general_assign_dialog']

        # Rendererの初期化
        self.renderer = GameRenderer(
            self.screen, self.font_large, self.font_medium, self.font_small,
            self.image_manager, self.power_map
        )

        # イベントハンドラーの作成
        self.event_handler = EventHandler(self)

        # コマンド実行ハンドラーの作成
        self.command_executor = CommandExecutor(self)

        # 転送・配置ハンドラーの作成
        self.transfer_handler = TransferHandler(self)

        # アニメーション管理の作成
        self.animation_manager = AnimationManager(self)

        # ターン状態管理の作成
        self.turn_state_manager = TurnStateManager(self)

        # ボタンの作成
        self._create_buttons()

    def _create_buttons(self):
        """ボタンを作成（game_initializerから呼び出される）"""
        buttons = create_buttons(self.font_medium, self.font_small, self.sound_manager, self)

        # ボタンをインスタンス変数に割り当て
        self.btn_end_turn = buttons['end_turn']
        self.btn_confirm_actions = buttons['confirm_actions']
        self.btn_close_detail = buttons['close_detail']
        self.btn_cultivate = buttons['cultivate']
        self.btn_develop_town = buttons['develop_town']
        self.btn_flood_control = buttons['flood_control']
        self.btn_give_rice = buttons['give_rice']
        self.btn_recruit = buttons['recruit']
        self.btn_attack = buttons['attack']
        self.btn_transfer_soldiers = buttons['transfer_soldiers']
        self.btn_transfer_gold = buttons['transfer_gold']
        self.btn_transfer_rice = buttons['transfer_rice']
        self.btn_assign_general = buttons['assign_general']
        self.btn_confirm_attack = buttons['confirm_attack']
        self.btn_cancel_attack = buttons['cancel_attack']
        self.btn_attack_25 = buttons['attack_25']
        self.btn_attack_50 = buttons['attack_50']
        self.btn_attack_75 = buttons['attack_75']
        self.btn_attack_100 = buttons['attack_100']

    def execute_command(self, command_type):
        """コマンドを実行 - CommandExecutorに委譲"""
        self.command_executor.execute_command(command_type)

    def execute_attack(self, target_province_id):
        """攻撃を実行 - CommandExecutorに委譲"""
        return self.command_executor.execute_attack(target_province_id)

    def end_turn(self):
        """ターン終了（Sequential方式）- TurnStateManagerに委譲"""
        self.turn_state_manager.end_turn_sequential()

    # ========================================
    # Sequential方式（sequential）用メソッド
    # ========================================

    def end_turn_sequential(self):
        """Sequential方式: ターン終了 - TurnStateManagerに委譲"""
        self.turn_state_manager.end_turn_sequential()

    def process_turn_event(self):
        """Sequential方式: generatorから次のイベントを処理 - TurnStateManagerに委譲"""
        self.turn_state_manager.process_turn_event()

    def show_seq_battle_animation(self, battle_data):
        """Sequential方式: 戦闘アニメーションを表示 - TurnStateManagerに委譲"""
        self.turn_state_manager.show_seq_battle_animation(battle_data)

    def on_seq_battle_animation_finished(self, battle_data):
        """Sequential方式: 戦闘演出終了時のコールバック - TurnStateManagerに委譲"""
        self.turn_state_manager.on_seq_battle_animation_finished(battle_data)

    def on_seq_death_animation_finished(self):
        """Sequential方式: 死亡演出終了時のコールバック - TurnStateManagerに委譲"""
        self.turn_state_manager.on_seq_death_animation_finished()

    def on_turn_complete(self):
        """Sequential方式: ターン完了 - TurnStateManagerに委譲"""
        self.turn_state_manager.on_turn_complete()

    def confirm_player_actions(self):
        """Sequential方式: プレイヤーの行動を確定 - TurnStateManagerに委譲"""
        self.turn_state_manager.confirm_player_actions()

    def _handle_seq_event(self, event):
        """Sequential方式: イベントをハンドル - TurnStateManagerに委譲"""
        self.turn_state_manager._handle_seq_event(event)

    def _log_turn_state_seq(self):
        """Sequential方式: ターン終了時のゲーム状態をログに出力 - TurnStateManagerに委譲"""
        self.turn_state_manager._log_turn_state_seq()

    def log_turn_state(self):
        """ターン終了時のゲーム状態をログに出力"""
        self.debug_logger.log_turn_state(self.game_state, self.turn_battle_records, self.turn_manager)

    def show_next_battle(self):
        """次の戦闘演出を表示 - AnimationManagerに委譲"""
        self.animation_manager.show_next_battle()

    def show_battle_animation(self, battle_data):
        """戦闘アニメーション画面を表示 - AnimationManagerに委譲"""
        self.animation_manager.show_battle_animation(battle_data)

    def on_battle_animation_finished(self):
        """戦闘演出が終了したときのコールバック - AnimationManagerに委譲"""
        self.animation_manager.on_battle_animation_finished()

    def flush_turn_messages(self):
        """保留中のターンメッセージをすべて表示 - AnimationManagerに委譲"""
        self.animation_manager.flush_turn_messages()

    def show_next_daimyo_death(self):
        """次の大名死亡演出を表示 - AnimationManagerに委譲"""
        self.animation_manager.show_next_daimyo_death()

    def on_daimyo_death_finished(self):
        """死亡演出終了時のコールバック - AnimationManagerに委譲"""
        self.animation_manager.on_daimyo_death_finished()

    def check_territory_loss_deaths(self):
        """領地喪失による死亡チェック - AnimationManagerに委譲"""
        self.animation_manager.check_territory_loss_deaths()

    def handle_daimyo_death(self, daimyo_id: int):
        """大名死亡時の領地処理 - AnimationManagerに委譲"""
        self.animation_manager.handle_daimyo_death(daimyo_id)

    def restart_game(self):
        """ゲームを完全リセットして再開"""
        # 1. GameStateを新規作成
        self.game_state = GameState()
        self.game_state.load_game_data()

        # 2. 将軍プール再初期化
        from systems.general_pool import GeneralPool
        self.game_state.general_pool = GeneralPool(self.game_state)
        self.game_state.general_pool.initialize()

        # 3. 各システムのGameState参照を更新
        self.turn_manager.game_state = self.game_state
        self.economy_system.game_state = self.game_state
        self.internal_affairs.game_state = self.game_state
        self.military_system.game_state = self.game_state
        self.combat_system.game_state = self.game_state
        self.diplomacy_system.game_state = self.game_state
        self.transfer_system.game_state = self.game_state
        self.ai_system.game_state = self.game_state
        self.event_system.game_state = self.game_state

        # 4. イベントシステム再初期化
        self.event_system.load_events_from_file(config.EVENTS_DATA)
        self.event_system.general_pool = self.game_state.general_pool

        # 5. UIとフラグのリセット
        self.selected_province_id = None
        self.selected_attack_target_id = None
        self.show_province_detail = False
        self.show_attack_selection = False
        self.message_log.clear()
        self.message_scroll_offset = 0

        # 6. 演出キューのクリア
        self.pending_battle_animations.clear()
        self.pending_daimyo_death_animations.clear()
        self.pending_turn_messages.clear()
        self.pending_winner_message = None
        self.current_battle_index = 0
        self.current_death_index = 0

        # 7. Sequential方式状態のリセット
        self.seq_mode_state = None
        self.seq_turn_generator = None
        self.player_military_commands = []
        self.game_ended = False  # ゲーム終了フラグをリセット
        if self.turn_manager:
            self.turn_manager.game_state = self.game_state
            self.turn_manager.ai_system = self.ai_system
            self.turn_manager.diplomacy_system = self.diplomacy_system
            self.turn_manager.event_system = self.event_system
            self.turn_manager.internal_affairs = self.internal_affairs
            self.turn_manager.military_system = self.military_system
            self.turn_manager.transfer_system = self.transfer_system

        # 8. 再開メッセージ
        self.add_message("=== ゲーム再開 ===")

    def on_event_choice_selected(self, choice):
        """イベント選択肢が選択された"""
        if not self.turn_manager.pending_event_choices:
            return

        event_data = self.turn_manager.pending_event_choices.pop(0)
        event = event_data["event"]
        province = event_data["province"]

        # 選択肢の効果を適用
        self.event_system.apply_event_effect(event, province, choice.choice_id)

        # メッセージ追加
        description = event.description.format(province_name=province.name)
        self.add_message(f"【{event.name}】{province.name}: {description}")
        self.add_message(f"  → {choice.text}を選択しました")

        # 次のイベントがあれば表示
        if self.turn_manager.pending_event_choices:
            next_event_data = self.turn_manager.pending_event_choices[0]
            self.event_dialog.show(
                next_event_data["event"],
                next_event_data["province"],
                self.on_event_choice_selected
            )

    def show_transfer_dialog(self, resource_type):
        """転送ダイアログを表示 - TransferHandlerに委譲"""
        self.transfer_handler.show_transfer_dialog(resource_type)

    def execute_transfer(self, resource_type, target_province_id, amount):
        """転送を実行 - TransferHandlerに委譲"""
        self.transfer_handler.execute_transfer(resource_type, target_province_id, amount)

    def show_general_assign_dialog(self):
        """将軍配置ダイアログを表示 - TransferHandlerに委譲"""
        self.transfer_handler.show_general_assign_dialog()

    def execute_general_assignment(self, general):
        """将軍配置を実行 - TransferHandlerに委譲"""
        self.transfer_handler.execute_general_assignment(general)

    def _set_attack_ratio(self, ratio):
        """攻撃兵力比率を設定"""
        self.selected_attack_ratio = ratio

    def _confirm_attack(self):
        """攻撃決定ボタンのコールバック"""
        if self.selected_attack_target_id is None:
            return

        result = self.execute_attack(self.selected_attack_target_id)
        if result:
            self.add_message(result["message"])

        # 選択状態をリセット
        self.selected_attack_target_id = None

    def _cancel_attack(self):
        """攻撃キャンセルボタンのコールバック"""
        # 選択状態をリセット
        self.selected_attack_target_id = None
        # 攻撃対象選択画面を閉じる
        self.show_attack_selection = False

    def close_province_detail(self):
        """領地詳細を閉じる"""
        self.show_province_detail = False
        self.show_attack_selection = False
        self.selected_province_id = None
        self.selected_attack_target_id = None  # 追加

    def add_message(self, message):
        """メッセージをログに追加"""
        self.message_log.append(message)

        # 新しいメッセージが追加されたら、スクロールを最新に戻す
        self.message_scroll_offset = 0
        # ログが長くなりすぎたら古いものを削除（500件まで保持）
        if len(self.message_log) > 500:
            self.message_log.pop(0)


    def handle_events(self):
        """イベント処理 - EventHandlerに委譲"""
        self.event_handler.handle_events()

    def update(self):
        """ゲームロジックの更新"""
        # プレイヤーの番強調アニメーション
        if self.portrait_highlight_timer > 0:
            self.portrait_highlight_timer -= 1

        # 大名死亡演出の更新
        if self.daimyo_death_screen.is_visible:
            self.daimyo_death_screen.update()

        # 戦闘プレビューの更新
        if self.battle_preview.is_visible:
            self.battle_preview.update(self.game_state)

        # 戦闘演出の更新
        if self.battle_animation.is_visible:
            self.battle_animation.update()

        # AI行動ディレイタイマー処理
        if self.seq_mode_state == "ai_action_delay":
            self.ai_action_delay_timer += 1
            if self.ai_action_delay_timer >= self.ai_action_delay_duration:
                # ディレイ終了 → 次のイベント処理
                print(f"[DEBUG-ディレイ] AI行動ディレイ終了: {self.ai_action_delay_timer}フレーム経過")
                self.seq_mode_state = "processing"
                self.process_turn_event()

        # 勢力マップの更新（ハイライトアニメーション＋マウスオーバー）
        mouse_pos = pygame.mouse.get_pos()
        self.power_map.update(mouse_pos, self.game_state)

    def render(self):
        """画面の描画"""
        # UI状態を辞書にまとめる
        ui_state = {
            'show_attack_selection': self.show_attack_selection,
            'show_province_detail': self.show_province_detail,
            'show_territory_info': self.show_territory_info,
            'selected_province_id': self.selected_province_id,
            'seq_mode_state': self.seq_mode_state,
            'portrait_highlight_timer': self.portrait_highlight_timer,
            'portrait_highlight_duration': self.portrait_highlight_duration,
            'message_log': self.message_log,
            'message_scroll_offset': self.message_scroll_offset,
            'disp_message': self.disp_message,
            'total_provinces': len(self.game_state.provinces),
            # 攻撃選択画面用
            'selected_attack_target_id': self.selected_attack_target_id,
            'selected_attack_ratio': self.selected_attack_ratio
        }

        # ボタンを辞書にまとめる
        buttons = {
            'end_turn': self.btn_end_turn,
            'confirm_actions': self.btn_confirm_actions,
            'close_detail': self.btn_close_detail,
            # 領地詳細画面用ボタン
            'cultivate': self.btn_cultivate,
            'develop_town': self.btn_develop_town,
            'flood_control': self.btn_flood_control,
            'give_rice': self.btn_give_rice,
            'recruit': self.btn_recruit,
            'attack': self.btn_attack,
            'transfer_soldiers': self.btn_transfer_soldiers,
            'transfer_gold': self.btn_transfer_gold,
            'transfer_rice': self.btn_transfer_rice,
            'assign_general': self.btn_assign_general,
            # 攻撃選択画面用ボタン
            'attack_25': self.btn_attack_25,
            'attack_50': self.btn_attack_50,
            'attack_75': self.btn_attack_75,
            'attack_100': self.btn_attack_100,
            'confirm_attack': self.btn_confirm_attack,
            'cancel_attack': self.btn_cancel_attack
        }

        # ダイアログを辞書にまとめる
        dialogs = {
            'battle_preview': self.battle_preview,
            'battle_animation': self.battle_animation,
            'event_dialog': self.event_dialog,
            'event_history_screen': self.event_history_screen,
            'transfer_dialog': self.transfer_dialog,
            'general_assign_dialog': self.general_assign_dialog,
            'daimyo_death_screen': self.daimyo_death_screen,
            'game_state': self.game_state
        }

        # Rendererに描画を委譲
        if self.show_attack_selection:
            # 攻撃選択画面をRendererに委譲
            self.renderer.render_attack_selection(self.game_state, ui_state, buttons)
        elif self.show_province_detail:
            # 領地詳細画面: メイン画面を描画してから暗転オーバーレイを適用
            self.renderer.render_main_map(self.game_state, ui_state, self.economy_system, buttons)
            self.renderer._draw_dark_overlay()
            self.renderer.render_province_detail(self.game_state, ui_state, buttons,
                                                  self.economy_system, self.transfer_system)
        else:
            # メインマップをRendererに委譲
            self.renderer.render_main_map(self.game_state, ui_state, self.economy_system, buttons)

        # オーバーレイはRendererに委譲
        self.renderer._render_overlays(dialogs, ui_state)

        pygame.display.flip()

    def run(self):
        """メインゲームループ"""
        try:
            print("=== Nobunaga's Ambition - Game Start ===")
            print(f"Player: {self.game_state.get_player_daimyo()}")
            print(f"Provinces: {len(self.game_state.provinces)}")
            print()
        except:
            pass

        # プロローグBGMを開始（Turn 0の場合）
        if self.game_state.current_turn == 0:
            self.bgm_manager.play_scene("prologue")

        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(config.FPS)

        self.quit()

    def quit(self):
        """ゲーム終了"""
        # ログファイルを閉じる
        self.debug_logger.close()

        try:
            print("\nGame Over")
        except:
            pass
        pygame.quit()
        sys.exit()


def main():
    """エントリーポイント"""
    try:
        game = Game()
        game.run()
    except Exception as e:
        try:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
        except:
            pass
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
