"""
信長の野望 - メインエントリーポイント
pygameを使用した戦略シミュレーションゲーム
"""
import pygame
import sys
import config
from datetime import datetime
import os
from core.game_state import GameState
from core.turn_manager import TurnManager
from core.turn_manager_v2 import TurnManagerV2
from systems.economy import EconomySystem
from systems.internal_affairs import InternalAffairsSystem
from ui.widgets import Button, Panel, TextLabel, ProgressBar
from ui.event_dialog import EventDialog
from ui.event_history_screen import EventHistoryScreen
from ui.battle_animation import BattleAnimationScreen
from ui.battle_preview import BattlePreviewScreen
from ui.power_map import PowerMap
from ui.transfer_dialog import TransferDialog
from ui.general_assign_dialog import GeneralAssignDialog
from ui.daimyo_death_screen import DaimyoDeathScreen


class Game:
    """メインゲームクラス"""

    def __init__(self):
        # Pygameの初期化
        pygame.init()

        # 画面の設定
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.WINDOW_TITLE)

        # クロックの設定
        self.clock = pygame.time.Clock()

        # フォントの設定（日本語対応）
        try:
            self.font_large = pygame.font.SysFont('meiryo', config.FONT_SIZE_LARGE)
            self.font_medium = pygame.font.SysFont('meiryo', config.FONT_SIZE_MEDIUM)
            self.font_small = pygame.font.SysFont('meiryo', config.FONT_SIZE_SMALL)
        except:
            self.font_large = pygame.font.Font(None, config.FONT_SIZE_LARGE)
            self.font_medium = pygame.font.Font(None, config.FONT_SIZE_MEDIUM)
            self.font_small = pygame.font.Font(None, config.FONT_SIZE_SMALL)

        # ゲーム状態の初期化
        self.game_state = GameState()
        self.game_state.load_game_data()

        # 画像管理の初期化
        from utils.image_manager import ImageManager
        assets_path = os.path.join(config.BASE_DIR, "assets")
        self.image_manager = ImageManager(assets_path)
        self.image_manager.preload_all_portraits()

        # 音声管理の初期化
        from utils.sound_manager import SoundManager
        self.sound_manager = SoundManager(assets_path)
        self.sound_manager.preload_all_sounds()

        # ゲームシステムの初期化
        self.turn_manager = TurnManager(self.game_state)
        self.economy_system = EconomySystem(self.game_state)
        self.internal_affairs = InternalAffairsSystem(self.game_state)

        # V2ターンマネージャー（sequentialモード用）
        self.turn_manager_v2 = None
        if config.TURN_PROCESSING_MODE == "sequential":
            self.turn_manager_v2 = TurnManagerV2(self.game_state)

        # 軍事システムのインポートと初期化
        from systems.military import MilitarySystem
        from systems.combat import CombatSystem
        from systems.diplomacy import DiplomacySystem
        from systems.ai import AISystem
        from systems.events import EventSystem
        from systems.transfer_system import TransferSystem

        self.military_system = MilitarySystem(self.game_state)
        self.combat_system = CombatSystem(self.game_state)
        self.diplomacy_system = DiplomacySystem(self.game_state)
        self.transfer_system = TransferSystem(self.game_state)
        self.ai_system = AISystem(
            self.game_state,
            self.internal_affairs,
            self.military_system,
            self.diplomacy_system,
            self.transfer_system
        )

        # イベントシステムの初期化
        self.event_system = EventSystem(self.game_state)
        self.event_system.load_events_from_file(config.EVENTS_DATA)
        self.event_system.general_pool = self.game_state.general_pool

        # TurnManagerにシステムを設定
        self.turn_manager.ai_system = self.ai_system
        self.turn_manager.diplomacy_system = self.diplomacy_system
        self.turn_manager.event_system = self.event_system

        # AISystemにTurnManagerへの参照を設定
        self.ai_system.turn_manager = self.turn_manager

        # TurnManagerV2にシステムを設定（sequentialモード用）
        if self.turn_manager_v2:
            self.turn_manager_v2.ai_system = self.ai_system
            self.turn_manager_v2.diplomacy_system = self.diplomacy_system
            self.turn_manager_v2.event_system = self.event_system
            self.turn_manager_v2.internal_affairs = self.internal_affairs
            self.turn_manager_v2.military_system = self.military_system
            self.turn_manager_v2.transfer_system = self.transfer_system

        # ゲーム実行フラグ
        self.running = True

        # UI状態
        self.selected_province_id = None
        self.selected_attack_target_id = None  # 攻撃対象として選択中の領地ID
        self.show_province_detail = False
        self.show_attack_selection = False
        self.show_territory_info = False  # 肖像クリックで領地情報を表示
        self.message_log = []
        self.message_scroll_offset = 0  # メッセージログのスクロール位置
        self.disp_message = 26  # 支配領地リストを削除したため大幅に増加

        # ログファイル設定（デバッグモード）
        self.log_file = None
        self._setup_log_file()

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

        # V2モード状態管理（sequentialモード用）
        self.v2_mode_state = None  # "waiting_player_input" / "animating" / None
        self.v2_turn_generator = None  # generatorの参照保持
        self.v2_player_internal_commands = []  # プレイヤーが登録した内政コマンド
        self.v2_player_military_commands = []  # プレイヤーが登録した軍事コマンド

        # プレイヤーの番強調アニメーション（2.5秒 = 75フレーム）
        self.portrait_highlight_timer = 0
        self.portrait_highlight_duration = 75  # 2.5秒 @ 30FPS

        # ボタンの作成
        self.create_buttons()

    def create_buttons(self):
        """ボタンを作成"""
        button_y = config.SCREEN_HEIGHT - 50

        self.btn_end_turn = Button(
            1100,button_y, 150, 40,
            "ターン終了",
            self.font_medium,
            self.end_turn,
            self.sound_manager,
            "decide"
        )

        # V2モード用: 行動決定ボタン（プレイヤーの番終了用）
        self.btn_confirm_actions_v2 = Button(
            1100, button_y, 150, 40,
            "行動決定",
            self.font_medium,
            self.confirm_player_actions_v2,
            self.sound_manager,
            "decide"
        )

        # イベントダイアログ
        self.event_dialog = EventDialog(self.screen, self.font_medium, self.sound_manager)

        # イベント履歴画面
        self.event_history_screen = EventHistoryScreen(self.screen, self.font_medium, self.sound_manager)

        # 勢力マップ
        self.power_map = PowerMap(self.screen, self.font_medium, self.image_manager)

        # 戦闘プレビュー画面（勢力図を使うので後に初期化）
        self.battle_preview = BattlePreviewScreen(self.screen, self.font_medium, self.power_map)

        # 戦闘演出画面
        self.battle_animation = BattleAnimationScreen(self.screen, self.font_medium, self.image_manager, self.sound_manager)

        # 大名死亡演出画面
        self.daimyo_death_screen = DaimyoDeathScreen(self.screen, self.font_medium, self.image_manager, self.sound_manager)

        # 転送ダイアログ
        self.transfer_dialog = TransferDialog(self.screen, self.font_medium, self.sound_manager)

        # 将軍配置ダイアログ
        self.general_assign_dialog = GeneralAssignDialog(self.screen, self.font_medium, self.sound_manager)

        self.btn_close_detail = Button(
            config.SCREEN_WIDTH - 170, button_y, 150, 40,
            "戻る",
            self.font_medium,
            self.close_province_detail,
            self.sound_manager,
            "cancel"
        )

        # 内政コマンドボタン
        self.btn_cultivate = Button(
            540, 270, 180, 35,
            "開墾 (金200)",
            self.font_small,
            lambda: self.execute_command("cultivate"),
            self.sound_manager,
            "decide"
        )

        self.btn_develop_town = Button(
            540, 315, 180, 35,
            "町開発 (金300)",
            self.font_small,
            lambda: self.execute_command("develop_town"),
            self.sound_manager,
            "decide"
        )

        self.btn_flood_control = Button(
            540, 360, 180, 35,
            "治水 (金150)",
            self.font_small,
            lambda: self.execute_command("flood_control"),
            self.sound_manager,
            "decide"
        )

        self.btn_give_rice = Button(
            540, 405, 180, 35,
            "米配布 (米100)",
            self.font_small,
            lambda: self.execute_command("give_rice"),
            self.sound_manager,
            "decide"
        )

        # 軍事コマンドボタン
        self.btn_recruit = Button(
            540, 540, 180, 35,
            "100人徴兵 (金200)",
            self.font_small,
            lambda: self.execute_command("recruit"),
            self.sound_manager,
            "decide"
        )

        self.btn_attack = Button(
            540, 585, 180, 35,
            "攻撃",
            self.font_small,
            lambda: self.execute_command("attack"),
            self.sound_manager,
            "decide"
        )

        # 転送コマンドボタン
        self.btn_transfer_soldiers = Button(
            790, 270, 180, 35,
            "兵士転送",
            self.font_small,
            lambda: self.execute_command("transfer_soldiers"),
            self.sound_manager,
            "decide"
        )

        self.btn_transfer_gold = Button(
            790, 315, 180, 35,
            "金送付",
            self.font_small,
            lambda: self.execute_command("transfer_gold"),
            self.sound_manager,
            "decide"
        )

        self.btn_transfer_rice = Button(
            790, 360, 180, 35,
            "米運搬",
            self.font_small,
            lambda: self.execute_command("transfer_rice"),
            self.sound_manager,
            "decide"
        )

        # 将軍配置ボタン
        self.btn_assign_general = Button(
            790, 405, 180, 35,
            "将軍配置",
            self.font_small,
            lambda: self.execute_command("assign_general"),
            self.sound_manager,
            "decide"
        )

        # 攻撃対象選択画面用のボタン
        self.btn_confirm_attack = Button(
            config.SCREEN_WIDTH // 2 - 160, config.SCREEN_HEIGHT - 120,
            150, 40,
            "決定",
            self.font_medium,
            self._confirm_attack,
            self.sound_manager,
            "decide"
        )

        self.btn_cancel_attack = Button(
            config.SCREEN_WIDTH // 2 + 10, config.SCREEN_HEIGHT - 120,
            150, 40,
            "戻る",
            self.font_medium,
            self._cancel_attack,
            self.sound_manager,
            "cancel"
        )

    def _format_player_command_event(self, daimyo, province, command_type):
        """プレイヤーコマンドをイベントメッセージに変換"""
        if command_type == "cultivate":
            return f"【{daimyo.clan_name}】{province.name}で開墾（開発Lv→{province.development_level}）"
        elif command_type == "develop_town":
            return f"【{daimyo.clan_name}】{province.name}で町開発（町Lv→{province.town_level}）"
        elif command_type == "flood_control":
            return f"【{daimyo.clan_name}】{province.name}で治水（治水→{province.flood_control}%）"
        elif command_type == "give_rice":
            return f"【{daimyo.clan_name}】{province.name}で米配布（忠誠度→{province.peasant_loyalty}）"
        elif command_type == "recruit":
            return f"【{daimyo.clan_name}】{province.name}で徴兵100人（兵力→{province.soldiers}人）"
        return None

    def execute_command(self, command_type):
        """コマンドを実行（V2モードでは記録のみ、classicモードは即座に実行）"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province or province.command_used_this_turn:
            self.add_message("このターンは既にコマンドを実行しました")
            return

        # V2モード: コマンドを記録だけして、「行動決定」時に実行
        # ただし、Turn 0での将軍配置は即座に実行可能
        is_turn0_general_assignment = (
            self.game_state.current_turn == 0 and command_type == "assign_general"
        )
        if config.TURN_PROCESSING_MODE == "sequential" and self.v2_mode_state == "waiting_player_input" and not is_turn0_general_assignment:
            self._register_v2_command(command_type, province)
            return

        # classicモード: 即座に実行
        result = None
        if command_type == "cultivate":
            result = self.internal_affairs.execute_cultivation(province)
        elif command_type == "develop_town":
            result = self.internal_affairs.execute_town_development(province)
        elif command_type == "flood_control":
            result = self.internal_affairs.execute_flood_control(province)
        elif command_type == "give_rice":
            result = self.internal_affairs.execute_give_rice(province)
        elif command_type == "recruit":
            result = self.military_system.recruit_soldiers(province, 100)
        elif command_type == "attack":
            # 攻撃対象選択状態を初期化
            self.selected_attack_target_id = None
            self.show_attack_selection = True
            return  # 攻撃対象選択画面に遷移
        elif command_type == "transfer_soldiers":
            self.show_transfer_dialog("soldiers")
            return
        elif command_type == "transfer_gold":
            self.show_transfer_dialog("gold")
            return
        elif command_type == "transfer_rice":
            self.show_transfer_dialog("rice")
            return
        elif command_type == "assign_general":
            self.show_general_assign_dialog()
            return

        if result:
            self.add_message(result["message"])
            if result["success"]:
                province.command_used_this_turn = True
                # コマンド実行統計を記録
                self.game_state.record_command(province.owner_daimyo_id, province.id, command_type)

                # プレイヤーコマンドをターンイベントに記録
                daimyo = self.game_state.get_daimyo(province.owner_daimyo_id)
                if daimyo and daimyo.is_player:
                    event_msg = self._format_player_command_event(daimyo, province, command_type)
                    if event_msg:
                        self.turn_manager.turn_events.append(event_msg)

    def _register_v2_command(self, command_type, province):
        """V2モード: コマンドを記録（即座には実行しない）"""
        # 内政コマンドと軍事コマンドを分類
        internal_commands = ["cultivate", "develop_town", "flood_control", "give_rice",
                           "transfer_soldiers", "transfer_gold", "transfer_rice", "assign_general"]
        military_commands = ["recruit", "attack"]

        if command_type in internal_commands:
            # 内政コマンドの登録
            if province.internal_command_used:
                self.add_message("この領地は既に内政コマンドを登録しました")
                return

            # ダイアログ系コマンドは後で処理
            if command_type in ["transfer_soldiers", "transfer_gold", "transfer_rice", "assign_general"]:
                if command_type == "transfer_soldiers":
                    self.show_transfer_dialog("soldiers")
                elif command_type == "transfer_gold":
                    self.show_transfer_dialog("gold")
                elif command_type == "transfer_rice":
                    self.show_transfer_dialog("rice")
                elif command_type == "assign_general":
                    self.show_general_assign_dialog()
                return

            self.v2_player_internal_commands.append({
                "type": command_type,
                "province_id": province.id
            })
            province.internal_command_used = True
            province.command_used_this_turn = True  # UI用フラグも設定
            self.add_message(f"{province.name}で{self._get_command_name(command_type)}を登録しました")

        elif command_type in military_commands:
            # 軍事コマンドの登録
            if province.military_command_used:
                self.add_message("この領地は既に軍事コマンドを登録しました")
                return

            if command_type == "attack":
                # 攻撃対象選択画面へ
                self.selected_attack_target_id = None
                self.show_attack_selection = True
                return

            # 徴兵の場合
            self.v2_player_military_commands.append({
                "type": "recruit",
                "province_id": province.id
            })
            province.military_command_used = True
            province.command_used_this_turn = True  # UI用フラグも設定
            self.add_message(f"{province.name}で徴兵を登録しました")

    def _get_command_name(self, command_type):
        """コマンドタイプから日本語名を取得"""
        names = {
            "cultivate": "開墾",
            "develop_town": "町開発",
            "flood_control": "治水",
            "give_rice": "米配布"
        }
        return names.get(command_type, command_type)

    def execute_attack(self, target_province_id):
        """攻撃を実行"""
        if not self.selected_province_id:
            return

        origin_province = self.game_state.get_province(self.selected_province_id)
        target_province = self.game_state.get_province(target_province_id)

        if not origin_province or not target_province:
            return {"success": False, "message": "無効な領地です"}

        # 兵士が足りるかチェック
        if origin_province.soldiers < 100:
            return {"success": False, "message": "兵士が不足しています（最低100人必要）"}

        # 隣接チェック
        if target_province_id not in origin_province.adjacent_provinces:
            return {"success": False, "message": "隣接していない領地には攻撃できません"}

        # 自分の領地には攻撃できない
        if target_province.owner_daimyo_id == origin_province.owner_daimyo_id:
            return {"success": False, "message": "自分の領地には攻撃できません"}

        # 攻撃軍を編成（全兵力の80%を派遣）
        attack_force = int(origin_province.soldiers * 0.8)
        # 守将がいれば将軍として配属
        general_id = origin_province.governor_general_id

        # V2モードでは事前検証のみ、classicモードでは軍を作成
        if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
            # V2モード: 基本的な検証のみ（実際の軍作成は実行時）
            if origin_province.soldiers < attack_force:
                return {"success": False, "message": "兵士が不足しています"}
            result = {"success": True}
        else:
            # Classicモード: 軍を実際に作成
            result = self.military_system.create_attack_army(
                origin_province,
                target_province,
                attack_force,
                general_id
            )

        if result["success"]:
            # V2モードとclassicモードで処理を分岐
            if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
                # V2モード: 軍事コマンドリストに追加（軍は作成しない、実行時に作成）
                # create_attack_armyの結果は無視し、コマンド情報のみ保存
                self.v2_player_military_commands.append({
                    "type": "attack",
                    "province_id": origin_province.id,
                    "target_id": target_province_id,
                    "attack_force": attack_force,
                    "general_id": general_id
                })
                origin_province.military_command_used = True
                origin_province.command_used_this_turn = True  # UI用フラグも設定

                # コマンド実行統計を記録
                self.game_state.record_command(origin_province.owner_daimyo_id, origin_province.id, "attack")

                # ターンイベントに記録
                daimyo = self.game_state.get_daimyo(origin_province.owner_daimyo_id)
                if daimyo and daimyo.is_player:
                    defender_name = "無所属"
                    if target_province.owner_daimyo_id:
                        defender_daimyo = self.game_state.get_daimyo(target_province.owner_daimyo_id)
                        if defender_daimyo:
                            defender_name = defender_daimyo.clan_name
                    event_msg = f"【{daimyo.clan_name}】{origin_province.name}から{defender_name}の{target_province.name}へ攻撃準備（兵力{attack_force}人）"
                    self.turn_manager_v2.turn_events.append(event_msg)

                self.show_attack_selection = False
                return {"success": True, "message": f"{target_province.name}への攻撃を準備しました（{attack_force}人）"}
            else:
                # Classicモード: 従来通り戦闘キューに追加
                army = result["army"]
                self.turn_manager.queue_battle({
                    "army": army,
                    "target_province_id": target_province_id,
                    "origin_province_id": origin_province.id
                })
                origin_province.command_used_this_turn = True
                # コマンド実行統計を記録
                self.game_state.record_command(origin_province.owner_daimyo_id, origin_province.id, "attack")

                # プレイヤーコマンドをターンイベントに記録
                daimyo = self.game_state.get_daimyo(origin_province.owner_daimyo_id)
                if daimyo and daimyo.is_player:
                    defender_name = "無所属"
                    if target_province.owner_daimyo_id:
                        defender_daimyo = self.game_state.get_daimyo(target_province.owner_daimyo_id)
                        if defender_daimyo:
                            defender_name = defender_daimyo.clan_name
                    event_msg = f"【{daimyo.clan_name}】{origin_province.name}から{defender_name}の{target_province.name}へ出陣（兵力{attack_force}人）"
                    self.turn_manager.turn_events.append(event_msg)

                self.show_attack_selection = False
                return {"success": True, "message": f"{target_province.name}への攻撃軍を編成しました（{attack_force}人）"}
        else:
            return result

    def end_turn(self):
        """ターン終了"""
        # モード分岐
        if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
            self.end_turn_v2()
            return

        winner = self.turn_manager.execute_turn()

        # ターンイベントを取得（戦闘メッセージは含まない）
        all_events = self.turn_manager.get_turn_events()

        # 戦闘メッセージ以外を保留（戦闘演出後に表示）
        self.pending_turn_messages = []
        for event in all_events:
            # 戦闘メッセージは個別に表示するのでスキップ
            if "【戦闘】" not in event and "⚔" not in event and "🛡" not in event and "★" not in event:
                self.pending_turn_messages.append(event)

        # 勝利メッセージも戦闘演出後に表示するため保留
        self.pending_winner_message = None
        if winner:
            daimyo = self.game_state.get_daimyo(winner)
            if daimyo:
                self.pending_winner_message = f"*** {daimyo.clan_name} {daimyo.name}が天下統一！***"

        # 戦闘結果があれば演出キューに追加
        if self.turn_manager.battle_results:
            self.pending_battle_animations = self.turn_manager.battle_results.copy()
            # 戦闘記録を保存（デバッグログ用）
            self.turn_battle_records = self.turn_manager.battle_results.copy()
            self.current_battle_index = 0
            # 最初の戦闘演出を開始（結果適用は演出後）
            self.show_next_battle()
        else:
            # 戦闘がなければすぐにメッセージを表示
            self.turn_battle_records = []

            # デバッグログ出力（戦闘がない場合は即座に出力）
            if self.need_log_turn_state:
                self.log_turn_state()
                self.need_log_turn_state = False

            self.flush_turn_messages()
            # 勝利メッセージも表示
            if self.pending_winner_message:
                self.add_message(self.pending_winner_message)
                self.pending_winner_message = None

        # 保留中のイベント選択があれば表示（戦闘演出後）
        if self.turn_manager.pending_event_choices and not self.battle_animation.is_visible:
            event_data = self.turn_manager.pending_event_choices[0]
            self.event_dialog.show(
                event_data["event"],
                event_data["province"],
                self.on_event_choice_selected
            )

        # デバッグログ出力フラグを設定（実際の出力は戦闘演出後）
        self.need_log_turn_state = True

    # ========================================
    # V2モード（sequential）用メソッド
    # ========================================

    def end_turn_v2(self):
        """V2モード: ターン終了（generator方式）"""
        if not self.turn_manager_v2:
            return

        # generatorを開始
        self.v2_turn_generator = self.turn_manager_v2.execute_turn()
        self.v2_mode_state = "processing"

        # 最初のイベントを処理
        self.process_v2_turn_event()

    def process_v2_turn_event(self):
        """V2モード: generatorから次のイベントを処理"""
        if not self.v2_turn_generator:
            self.on_v2_turn_complete()
            return

        try:
            event = next(self.v2_turn_generator)
            event_type = event[0]

            if event_type == "turn_start":
                # ターン開始メッセージ
                message = event[1]
                self.add_message(message)
                # 次のイベントへ
                self.process_v2_turn_event()

            elif event_type == "message":
                # AI大名の内政コマンドメッセージ
                message = event[1]
                self.add_message(message)
                # 次のイベントへ
                self.process_v2_turn_event()

            elif event_type == "death_animation":
                # 死亡演出
                death_data = event[1]
                self.v2_mode_state = "animating"
                self.daimyo_death_screen.show(
                    death_data,
                    on_finish=self.on_v2_death_animation_finished,
                    on_play=self.restart_game,
                    on_end=self.quit
                )

            elif event_type == "battle_animation":
                # 戦闘演出
                battle_data = event[1]
                self.v2_mode_state = "animating"

                # 戦闘記録を保存（ログ用）
                self.turn_battle_records.append(battle_data)

                # プレビュー → アニメーション
                preview_data = {
                    "attacker_province_id": battle_data["origin_province_id"],
                    "defender_province_id": battle_data["target_province_id"],
                    "attacker_name": battle_data["attacker_name"],
                    "defender_name": battle_data["defender_name"]
                }
                self.battle_preview.show(
                    preview_data,
                    on_finish=lambda: self.show_v2_battle_animation(battle_data)
                )

            elif event_type == "player_turn":
                # プレイヤーの番
                daimyo_id = event[1]
                self.v2_mode_state = "waiting_player_input"
                self.v2_player_internal_commands = []
                self.v2_player_military_commands = []
                self.portrait_highlight_timer = self.portrait_highlight_duration  # アニメーション開始
                self.add_message("=== あなたの番です ===")

            elif event_type == "victory":
                # 勝利
                player_daimyo = self.game_state.get_player_daimyo()
                if player_daimyo:
                    self.add_message(f"*** {player_daimyo.clan_name} {player_daimyo.name}が天下統一！***")
                self.on_v2_turn_complete()

            elif event_type == "game_over":
                # ゲームオーバー
                death_data = event[1]
                self.add_message(f"*** {death_data['clan_name']} {death_data['name']}が滅亡しました ***")
                # 死亡演出は既に表示されているはず

        except StopIteration:
            # ターン終了
            self.on_v2_turn_complete()

    def show_v2_battle_animation(self, battle_data):
        """V2モード: 戦闘アニメーションを表示"""
        self.battle_animation.show(
            battle_data,
            on_finish=lambda: self.on_v2_battle_animation_finished(battle_data)
        )

    def on_v2_battle_animation_finished(self, battle_data):
        """V2モード: 戦闘演出終了時のコールバック"""
        # 戦闘結果は既にturn_manager_v2で適用済み
        # メッセージを表示
        result = battle_data.get("result")
        if result:
            if result.attacker_won:
                self.add_message(f"【戦闘】{battle_data['attacker_name']}が{battle_data['defender_province']}を占領")
                # 勢力図をハイライト
                for province in self.game_state.provinces.values():
                    if province.name == battle_data['defender_province']:
                        self.power_map.set_highlight(province.id)
                        break
            else:
                self.add_message(f"【戦闘】{battle_data['defender_name']}が{battle_data['defender_province']}を防衛")

        # 次のイベントへ
        self.process_v2_turn_event()

    def on_v2_death_animation_finished(self):
        """V2モード: 死亡演出終了時のコールバック"""
        # 次のイベントへ
        self.process_v2_turn_event()

    def on_v2_turn_complete(self):
        """V2モード: ターン完了"""
        self.v2_turn_generator = None
        self.v2_mode_state = None

        # ターンイベントをメッセージログに追加
        if self.turn_manager_v2:
            for event in self.turn_manager_v2.get_turn_events():
                # AI大名のコマンドメッセージ、戦闘メッセージ、ターン開始メッセージは既に表示済み
                # 【収入】【維持費】などのプレイヤー向けメッセージのみここで表示
                if ("【戦闘】" not in event and "ターン" not in event and "開始" not in event and
                    "【" not in event or event.startswith("【収入】") or event.startswith("【維持費】")):
                    self.add_message(event)

        # デバッグログ出力（V2モード用にturn_managerをturn_manager_v2に参照変更）
        if config.DEBUG_MODE and self.log_file:
            self._log_turn_state_v2()

        self.add_message("=== ターン終了 ===")

    def confirm_player_actions_v2(self):
        """V2モード: プレイヤーの行動を確定"""
        if self.v2_mode_state != "waiting_player_input":
            return

        # generatorに内政コマンドと軍事コマンドを送信して再開
        self.v2_mode_state = "processing"
        try:
            event = self.v2_turn_generator.send({
                "internal_commands": self.v2_player_internal_commands,
                "military_commands": self.v2_player_military_commands
            })
            # 次のイベントを処理（send後に返されたイベント）
            self._handle_v2_event(event)
        except StopIteration:
            self.on_v2_turn_complete()

    def _handle_v2_event(self, event):
        """V2モード: イベントをハンドル"""
        event_type = event[0]

        if event_type == "message":
            # AI大名の内政コマンドメッセージ
            message = event[1]
            self.add_message(message)
            # 次のイベントを処理
            try:
                next_event = next(self.v2_turn_generator)
                self._handle_v2_event(next_event)
            except StopIteration:
                self.on_v2_turn_complete()

        elif event_type == "death_animation":
            death_data = event[1]
            self.v2_mode_state = "animating"
            self.daimyo_death_screen.show(
                death_data,
                on_finish=self.on_v2_death_animation_finished,
                on_play=self.restart_game,
                on_end=self.quit
            )
        elif event_type == "battle_animation":
            battle_data = event[1]
            self.v2_mode_state = "animating"
            self.turn_battle_records.append(battle_data)
            preview_data = {
                "attacker_province_id": battle_data["origin_province_id"],
                "defender_province_id": battle_data["target_province_id"],
                "attacker_name": battle_data["attacker_name"],
                "defender_name": battle_data["defender_name"]
            }
            self.battle_preview.show(
                preview_data,
                on_finish=lambda: self.show_v2_battle_animation(battle_data)
            )
        elif event_type == "player_turn":
            daimyo_id = event[1]
            self.v2_mode_state = "waiting_player_input"
            self.v2_player_internal_commands = []
            self.v2_player_military_commands = []
            self.portrait_highlight_timer = self.portrait_highlight_duration  # アニメーション開始
            self.add_message("=== あなたの番です ===")
        elif event_type == "victory":
            player_daimyo = self.game_state.get_player_daimyo()
            if player_daimyo:
                self.add_message(f"*** {player_daimyo.clan_name} {player_daimyo.name}が天下統一！***")
            self.on_v2_turn_complete()
        elif event_type == "game_over":
            death_data = event[1]
            self.add_message(f"*** {death_data['clan_name']} {death_data['name']}が滅亡しました ***")

    def _log_turn_state_v2(self):
        """V2モード: ターン終了時のゲーム状態をログに出力"""
        if not config.DEBUG_MODE or not self.log_file:
            return

        log = []
        log.append(f"\n{'='*80}\n")
        log.append(f"TURN {self.game_state.current_turn} - {self.game_state.get_season_name()} {self.game_state.get_year()}年 [V2モード]\n")
        log.append(f"{'='*80}\n\n")

        # ターンイベント情報
        if self.turn_manager_v2 and self.turn_manager_v2.turn_events:
            log.append(f"【ターンイベント】\n")
            for event in self.turn_manager_v2.turn_events:
                log.append(f"  - {event}\n")
            log.append("\n")

        # 戦闘情報
        if self.turn_battle_records:
            log.append(f"【戦闘結果】\n")
            for i, battle in enumerate(self.turn_battle_records, 1):
                attacker_name = battle.get("attacker_name", "不明")
                defender_name = battle.get("defender_name", "不明")
                origin_province = battle.get("attacker_province", "不明")
                target_province = battle.get("defender_province", "不明")

                attacker_initial = battle.get("attacker_troops", 0)
                defender_initial = battle.get("defender_troops", 0)

                result_obj = battle.get("result")
                if result_obj:
                    attacker_remaining = result_obj.attacker_remaining
                    defender_remaining = result_obj.defender_remaining
                    attacker_casualties = result_obj.attacker_casualties
                    defender_casualties = result_obj.defender_casualties
                    attacker_won = result_obj.attacker_won
                else:
                    attacker_remaining = 0
                    defender_remaining = 0
                    attacker_casualties = 0
                    defender_casualties = 0
                    attacker_won = False

                winner = "攻撃側" if attacker_won else "防御側"
                result_text = "勝利" if attacker_won else "敗北"

                attacker_general = battle.get("attacker_general", "なし")
                defender_general = battle.get("defender_general", "なし")

                log.append(f"  戦闘{i}: {origin_province}({attacker_name}) vs {target_province}({defender_name})\n")
                log.append(f"      攻撃側将軍:{attacker_general} / 防御側将軍:{defender_general}\n")
                log.append(f"      攻撃側: 初期兵力{attacker_initial} → 残存{attacker_remaining} (損失{attacker_casualties})\n")
                log.append(f"      防御側: 初期兵力{defender_initial} → 残存{defender_remaining} (損失{defender_casualties})\n")
                log.append(f"      結果: {winner}の{result_text}\n")

                if attacker_won:
                    log.append(f"      {target_province}を{attacker_name}が占領\n")
                else:
                    log.append(f"      {defender_name}が{target_province}を守り切った\n")
            log.append("\n")
            # 戦闘記録をクリア
            self.turn_battle_records = []

        # 大名情報
        log.append(f"【大名情報】\n")
        for daimyo in sorted(self.game_state.daimyo.values(), key=lambda d: d.id):
            status = "生存" if daimyo.is_alive else "死亡"
            log.append(f"  [{daimyo.id}] {daimyo.clan_name} {daimyo.name} ({status})\n")
            log.append(f"      年齢:{daimyo.age} 健康:{daimyo.health} 野心:{daimyo.ambition}\n")
            log.append(f"      魅力:{daimyo.charm} 知力:{daimyo.intelligence} 武力:{daimyo.war_skill}\n")
            log.append(f"      支配領地数:{len(daimyo.controlled_provinces)} 領地ID:{sorted(daimyo.controlled_provinces)}\n")

        # 将軍情報
        log.append(f"\n【将軍情報】\n")
        for general in sorted(self.game_state.generals.values(), key=lambda g: g.id):
            serving = f"仕官先:{general.serving_daimyo_id}" if general.serving_daimyo_id else "浪人"
            assigned = f"配置:{general.current_province_id}" if general.current_province_id else "未配置"
            log.append(f"  [{general.id}] {general.name} ({serving}, {assigned})\n")
            log.append(f"      年齢:{general.age} 健康:{general.health}\n")
            log.append(f"      統率:{general.leadership} 武力:{general.war_skill} 知力:{general.intelligence} 政治:{general.politics}\n")

        # 領地情報
        log.append(f"\n【領地情報】\n")
        for province in sorted(self.game_state.provinces.values(), key=lambda p: p.id):
            owner_name = "無所属"
            if province.owner_daimyo_id:
                owner = self.game_state.get_daimyo(province.owner_daimyo_id)
                if owner:
                    owner_name = f"{owner.clan_name}"

            governor_name = "なし"
            if province.governor_general_id:
                if config.DAIMYO_ID_MIN <= province.governor_general_id <= config.DAIMYO_ID_MAX:
                    gov = self.game_state.get_daimyo(province.governor_general_id)
                    if gov:
                        governor_name = f"大名:{gov.name}"
                elif config.GENERAL_ID_MIN <= province.governor_general_id <= config.GENERAL_ID_MAX:
                    gov = self.game_state.get_general(province.governor_general_id)
                    if gov:
                        governor_name = f"将軍:{gov.name}"

            log.append(f"  [{province.id:2d}] {province.name} (所有:{owner_name}, 守将:{governor_name})\n")
            log.append(f"      兵:{province.soldiers} 農民:{province.peasants} 金:{province.gold} 米:{province.rice}\n")
            log.append(f"      開発Lv:{province.development_level} 町Lv:{province.town_level} 農民忠誠:{province.peasant_loyalty} 兵士士気:{province.soldier_morale}\n")

        self.write_debug_log(''.join(log))

    def log_turn_state(self):
        """ターン終了時のゲーム状態をログに出力"""
        if not config.DEBUG_MODE or not self.log_file:
            return

        log = []
        log.append(f"\n{'='*80}\n")
        log.append(f"TURN {self.game_state.current_turn} - {self.game_state.get_season_name()} {self.game_state.get_year()}年\n")
        log.append(f"{'='*80}\n\n")

        # ターンイベント情報（最初に表示）
        if self.turn_manager.turn_events:
            log.append(f"【ターンイベント】\n")
            for event in self.turn_manager.turn_events:
                log.append(f"  - {event}\n")
            log.append("\n")

        # 戦闘情報（ターンイベントの後に表示 - フェーズ8で処理されるため）
        if self.turn_battle_records:
            log.append(f"【戦闘結果】\n")
            for i, battle in enumerate(self.turn_battle_records, 1):
                attacker_name = battle.get("attacker_name", "不明")
                defender_name = battle.get("defender_name", "不明")
                origin_province = battle.get("attacker_province", "不明")
                target_province = battle.get("defender_province", "不明")

                attacker_initial = battle.get("attacker_troops", 0)
                defender_initial = battle.get("defender_troops", 0)

                # resultオブジェクトから残存兵力を取得
                result_obj = battle.get("result")
                if result_obj:
                    attacker_remaining = result_obj.attacker_remaining
                    defender_remaining = result_obj.defender_remaining
                    attacker_casualties = result_obj.attacker_casualties
                    defender_casualties = result_obj.defender_casualties
                    attacker_won = result_obj.attacker_won
                else:
                    attacker_remaining = 0
                    defender_remaining = 0
                    attacker_casualties = 0
                    defender_casualties = 0
                    attacker_won = False

                winner = "攻撃側" if attacker_won else "防御側"
                result_text = "勝利" if attacker_won else "敗北"

                attacker_general = battle.get("attacker_general", "なし")
                defender_general = battle.get("defender_general", "なし")

                log.append(f"  戦闘{i}: {origin_province}({attacker_name}) vs {target_province}({defender_name})\n")
                log.append(f"      攻撃側将軍:{attacker_general} / 防御側将軍:{defender_general}\n")
                log.append(f"      攻撃側: 初期兵力{attacker_initial} → 残存{attacker_remaining} (損失{attacker_casualties})\n")
                log.append(f"      防御側: 初期兵力{defender_initial} → 残存{defender_remaining} (損失{defender_casualties})\n")
                log.append(f"      結果: {winner}の{result_text}\n")

                if attacker_won:
                    log.append(f"      {target_province}を{attacker_name}が占領\n")
                else:
                    log.append(f"      {defender_name}が{target_province}を守り切った\n")
            log.append("\n")

        # 大名情報
        log.append(f"【大名情報】\n")
        for daimyo in sorted(self.game_state.daimyo.values(), key=lambda d: d.id):
            status = "生存" if daimyo.is_alive else "死亡"
            log.append(f"  [{daimyo.id}] {daimyo.clan_name} {daimyo.name} ({status})\n")
            log.append(f"      年齢:{daimyo.age} 健康:{daimyo.health} 野心:{daimyo.ambition}\n")
            log.append(f"      魅力:{daimyo.charm} 知力:{daimyo.intelligence} 武力:{daimyo.war_skill}\n")
            log.append(f"      支配領地数:{len(daimyo.controlled_provinces)} 領地ID:{sorted(daimyo.controlled_provinces)}\n")

        # 将軍情報
        log.append(f"\n【将軍情報】\n")
        for general in sorted(self.game_state.generals.values(), key=lambda g: g.id):
            serving = f"仕官先:{general.serving_daimyo_id}" if general.serving_daimyo_id else "浪人"
            assigned = f"配置:{general.current_province_id}" if general.current_province_id else "未配置"
            log.append(f"  [{general.id}] {general.name} ({serving}, {assigned})\n")
            log.append(f"      年齢:{general.age} 健康:{general.health}\n")
            log.append(f"      統率:{general.leadership} 武力:{general.war_skill} 知力:{general.intelligence} 政治:{general.politics}\n")

        # 領地情報
        log.append(f"\n【領地情報】\n")
        for province in sorted(self.game_state.provinces.values(), key=lambda p: p.id):
            owner_name = "無所属"
            if province.owner_daimyo_id:
                owner = self.game_state.get_daimyo(province.owner_daimyo_id)
                if owner:
                    owner_name = f"{owner.clan_name}"

            governor_name = "なし"
            if province.governor_general_id:
                if config.DAIMYO_ID_MIN <= province.governor_general_id <= config.DAIMYO_ID_MAX:
                    gov = self.game_state.get_daimyo(province.governor_general_id)
                    if gov:
                        governor_name = f"大名:{gov.name}"
                elif config.GENERAL_ID_MIN <= province.governor_general_id <= config.GENERAL_ID_MAX:
                    gov = self.game_state.get_general(province.governor_general_id)
                    if gov:
                        governor_name = f"将軍:{gov.name}"

            log.append(f"  [{province.id:2d}] {province.name} (所有:{owner_name}, 守将:{governor_name})\n")
            log.append(f"      兵:{province.soldiers} 農民:{province.peasants} 金:{province.gold} 米:{province.rice}\n")
            log.append(f"      開発Lv:{province.development_level} 町Lv:{province.town_level} 農民忠誠:{province.peasant_loyalty} 兵士士気:{province.soldier_morale}\n")

        self.write_debug_log(''.join(log))

    def show_next_battle(self):
        """次の戦闘演出を表示"""
        if self.current_battle_index < len(self.pending_battle_animations):
            battle_data = self.pending_battle_animations[self.current_battle_index]
            self.current_battle_index += 1

            # まず戦闘プレビューを表示
            preview_data = {
                "attacker_province_id": battle_data["origin_province_id"],
                "defender_province_id": battle_data["target_province_id"],
                "attacker_name": battle_data["attacker_name"],
                "defender_name": battle_data["defender_name"]
            }
            self.battle_preview.show(preview_data, on_finish=lambda: self.show_battle_animation(battle_data))
        else:
            # すべての戦闘演出が終了
            self.pending_battle_animations.clear()

            # 全戦闘終了後に領地喪失による死亡チェック
            self.check_territory_loss_deaths()

            # デバッグログ出力（すべての戦闘結果が反映された後）
            if self.need_log_turn_state:
                self.log_turn_state()
                self.need_log_turn_state = False

            # 大名死亡演出があれば開始
            if self.turn_manager.pending_daimyo_deaths:
                self.pending_daimyo_death_animations = self.turn_manager.pending_daimyo_deaths.copy()
                self.turn_manager.pending_daimyo_deaths.clear()
                self.current_death_index = 0
                self.show_next_daimyo_death()
            else:
                # 死亡演出もなければメッセージ表示
                self.flush_turn_messages()

                # 勝利メッセージを表示
                if self.pending_winner_message:
                    self.add_message(self.pending_winner_message)
                    self.pending_winner_message = None

    def show_battle_animation(self, battle_data):
        """戦闘アニメーション画面を表示（プレビュー後）"""
        self.battle_animation.show(battle_data, on_finish=self.on_battle_animation_finished)

    def on_battle_animation_finished(self):
        """戦闘演出が終了したときのコールバック"""
        # 今終わった戦闘の結果を処理
        if self.current_battle_index > 0:
            battle_data = self.pending_battle_animations[self.current_battle_index - 1]

            # 1. 戦闘結果を適用（演出後に初めて領地所有権を変更）
            if "combat_system" in battle_data and "army" in battle_data:
                combat_system = battle_data["combat_system"]
                army = battle_data["army"]
                target_province = self.game_state.get_province(battle_data["target_province_id"])
                result = battle_data["result"]

                if target_province:
                    # 結果を適用（大名が討死した場合、defeated_daimyo_idが返る）
                    defeated_daimyo_id = combat_system.apply_battle_result(result, army, target_province)

                    # 大名が討死した場合、演出キューに追加
                    if defeated_daimyo_id:
                        defeated_daimyo = self.game_state.get_daimyo(defeated_daimyo_id)
                        if defeated_daimyo:
                            self.turn_manager.pending_daimyo_deaths.append({
                                "daimyo_id": defeated_daimyo.id,
                                "daimyo_name": defeated_daimyo.name,
                                "clan_name": defeated_daimyo.clan_name,
                                "age": defeated_daimyo.age,
                                "is_player": defeated_daimyo.is_player,
                                "cause": "battle_defeat"
                            })

                    # 敗北した軍は撤退（削除）
                    if not result.attacker_won and army.id in self.game_state.armies:
                        origin_province = self.game_state.get_province(battle_data["origin_province_id"])
                        if origin_province and army.total_troops > 0:
                            origin_province.add_soldiers(army.total_troops)
                        del self.game_state.armies[army.id]

            # 2. 勢力図の反映（領地変更があればハイライト）
            if battle_data.get("result") and battle_data["result"].province_captured:
                # 戦闘音再生
                self.sound_manager.play("battle")

                # 占領された領地をハイライト
                defender_province_name = battle_data["defender_province"]
                for province in self.game_state.provinces.values():
                    if province.name == defender_province_name:
                        self.power_map.set_highlight(province.id)
                        break

            # 3. この戦闘のメッセージを表示
            if "messages" in battle_data:
                for message in battle_data["messages"]:
                    self.add_message(message)

        # 4. 次の戦闘があれば表示、なければ残りのメッセージを表示
        self.show_next_battle()

    def flush_turn_messages(self):
        """保留中のターンメッセージをすべて表示"""
        for event in self.pending_turn_messages:
            self.add_message(event)
        self.pending_turn_messages.clear()

    def show_next_daimyo_death(self):
        """次の大名死亡演出を表示"""
        if self.current_death_index < len(self.pending_daimyo_death_animations):
            death_data = self.pending_daimyo_death_animations[self.current_death_index]
            self.current_death_index += 1

            # 演出開始
            self.daimyo_death_screen.show(
                death_data,
                on_finish=self.on_daimyo_death_finished,
                on_play=self.restart_game,
                on_end=self.quit
            )
        else:
            # 全死亡演出終了
            self.pending_daimyo_death_animations.clear()
            self.flush_turn_messages()
            if self.pending_winner_message:
                self.add_message(self.pending_winner_message)
                self.pending_winner_message = None

    def on_daimyo_death_finished(self):
        """死亡演出終了時のコールバック"""
        # 最後に表示した死亡データを取得
        death_data = self.pending_daimyo_death_animations[self.current_death_index - 1]

        # 領地を回収（中立化）
        self.handle_daimyo_death(death_data["daimyo_id"])

        # 次の死亡演出へ
        self.show_next_daimyo_death()

    def check_territory_loss_deaths(self):
        """領地喪失による死亡チェック"""
        for daimyo in self.game_state.daimyo.values():
            # 既に死亡している、または領地を持っている場合はスキップ
            if not daimyo.is_alive or len(daimyo.controlled_provinces) > 0:
                continue

            # 全領地を失った大名は死亡
            daimyo.is_alive = False

            # 死亡演出キューに追加
            self.turn_manager.pending_daimyo_deaths.append({
                "daimyo_id": daimyo.id,
                "daimyo_name": daimyo.name,
                "clan_name": daimyo.clan_name,
                "age": daimyo.age,
                "is_player": daimyo.is_player,
                "cause": "territory_loss"  # 新しい死因
            })

            print(f"[Game] 大名 {daimyo.clan_name} {daimyo.name} が全領地喪失により死亡")

    def handle_daimyo_death(self, daimyo_id: int):
        """大名死亡時の領地処理"""
        daimyo = self.game_state.get_daimyo(daimyo_id)
        if not daimyo:
            return

        # 全領地を中立化
        for province_id in list(daimyo.controlled_provinces):
            province = self.game_state.get_province(province_id)
            if province:
                province.owner_daimyo_id = None
                province.governor_general_id = None
                daimyo.remove_province(province_id)

        # 配下の将軍を浪人化
        for general in list(self.game_state.generals.values()):
            if general.serving_daimyo_id == daimyo_id:
                general.serving_daimyo_id = None
                general.unassign()

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

        # 7. V2モード状態のリセット
        self.v2_mode_state = None
        self.v2_turn_generator = None
        self.v2_player_military_commands = []
        if self.turn_manager_v2:
            self.turn_manager_v2.game_state = self.game_state
            self.turn_manager_v2.ai_system = self.ai_system
            self.turn_manager_v2.diplomacy_system = self.diplomacy_system
            self.turn_manager_v2.event_system = self.event_system
            self.turn_manager_v2.internal_affairs = self.internal_affairs
            self.turn_manager_v2.military_system = self.military_system
            self.turn_manager_v2.transfer_system = self.transfer_system

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
        """転送ダイアログを表示"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province:
            return

        # 転送可能な隣接領地を取得
        target_provinces = self.transfer_system.get_valid_transfer_targets(self.selected_province_id)

        if not target_provinces:
            self.add_message("転送可能な隣接領地がありません")
            return

        # 転送可能な最大量を計算
        max_amount = 0
        if resource_type == "soldiers":
            max_amount = min(province.soldiers - 10, self.transfer_system.MAX_SOLDIERS_TRANSFER)
        elif resource_type == "gold":
            max_amount = min(province.gold, self.transfer_system.MAX_GOLD_TRANSFER)
        elif resource_type == "rice":
            max_amount = min(province.rice, self.transfer_system.MAX_RICE_TRANSFER)

        if max_amount <= 0:
            resource_names = {"soldiers": "兵士", "gold": "金", "rice": "米"}
            self.add_message(f"{resource_names.get(resource_type)}が不足しています")
            return

        # ダイアログを表示
        self.transfer_dialog.show(
            province,
            target_provinces,
            resource_type,
            max_amount,
            lambda target_id, amount: self.execute_transfer(resource_type, target_id, amount),
            lambda: None  # キャンセル時は何もしない
        )

    def execute_transfer(self, resource_type, target_province_id, amount):
        """転送を実行"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province:
            return

        # V2モードとclassicモードで処理を分岐
        if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
            # V2モード: 既にコマンド使用済みかチェック
            if province.internal_command_used or province.command_used_this_turn:
                self.add_message("この領地は既に内政コマンドを登録しました")
                return

            # V2モード: コマンドをリストに登録
            command_type_map = {
                "soldiers": "transfer_soldiers",
                "gold": "transfer_gold",
                "rice": "transfer_rice"
            }
            self.v2_player_internal_commands.append({
                "type": command_type_map[resource_type],
                "province_id": province.id,
                "target_id": target_province_id,
                "amount": amount
            })
            province.internal_command_used = True
            province.command_used_this_turn = True

            resource_names = {"soldiers": "兵士", "gold": "金", "rice": "米"}
            self.add_message(f"{province.name}から{resource_names[resource_type]}{amount}の転送を登録しました")
            self.game_state.record_command(province.owner_daimyo_id, province.id, command_type_map[resource_type])
        else:
            # Classicモード: 既にコマンド使用済みかチェック
            if province.command_used_this_turn:
                self.add_message("このターンは既にコマンドを実行しました")
                return

            # 転送実行
            result = None
            if resource_type == "soldiers":
                result = self.transfer_system.transfer_soldiers(
                    self.selected_province_id,
                    target_province_id,
                    amount
                )
            elif resource_type == "gold":
                result = self.transfer_system.transfer_gold(
                    self.selected_province_id,
                    target_province_id,
                    amount
                )
            elif resource_type == "rice":
                result = self.transfer_system.transfer_rice(
                    self.selected_province_id,
                    target_province_id,
                    amount
                )

            if result:
                self.add_message(result.message)
                if result.success:
                    province.command_used_this_turn = True
                    target_province = self.game_state.get_province(target_province_id)

                    # コマンド実行統計を記録
                    if resource_type == "soldiers":
                        self.game_state.record_command(province.owner_daimyo_id, province.id, "transfer_soldiers")
                    elif resource_type == "gold":
                        self.game_state.record_command(province.owner_daimyo_id, province.id, "transfer_gold")
                    elif resource_type == "rice":
                        self.game_state.record_command(province.owner_daimyo_id, province.id, "transfer_rice")

                # プレイヤーコマンドをターンイベントに記録
                daimyo = self.game_state.get_daimyo(province.owner_daimyo_id)
                if daimyo and daimyo.is_player and target_province:
                    resource_name = {"soldiers": "兵", "gold": "金", "rice": "米"}[resource_type]
                    event_msg = f"【{daimyo.clan_name}】{province.name}から{target_province.name}へ{resource_name}{amount}を転送"
                    # V2モードとclassicモードで適切なターンマネージャーを使用
                    if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
                        self.turn_manager_v2.turn_events.append(event_msg)
                    else:
                        self.turn_manager.turn_events.append(event_msg)

    def show_general_assign_dialog(self):
        """将軍配置ダイアログを表示"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province:
            return

        # 配置可能な将軍を取得（プレイヤーに仕える将軍で配置されていないもの）
        player_daimyo = self.game_state.get_player_daimyo()
        if not player_daimyo:
            return

        available_generals = [
            general for general in self.game_state.generals.values()
            if general.serving_daimyo_id == player_daimyo.id and general.is_available
        ]

        # 現在配置されている将軍を取得
        current_general = None
        if province.governor_general_id:
            current_general = self.game_state.get_general(province.governor_general_id)

        # ダイアログを表示
        self.general_assign_dialog.show(
            province,
            available_generals,
            lambda general: self.execute_general_assignment(general),
            lambda: None,  # キャンセル時は何もしない
            current_general
        )

    def execute_general_assignment(self, general):
        """将軍配置を実行"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province:
            return

        # V2モードとclassicモードで処理を分岐
        if config.TURN_PROCESSING_MODE == "sequential" and self.turn_manager_v2:
            # V2モード: 既にコマンド使用済みかチェック
            if province.internal_command_used or province.command_used_this_turn:
                self.add_message("この領地は既に内政コマンドを登録しました")
                return

            # 将軍配置または配置解除
            if general is None:
                # 配置解除（即時実行）
                result = self.internal_affairs.remove_governor(province)
                if result["success"]:
                    self.add_message(result["message"])
            else:
                # V2モード: コマンドをリストに登録
                self.v2_player_internal_commands.append({
                    "type": "assign_general",
                    "province_id": province.id,
                    "general_id": general.id
                })
                province.internal_command_used = True
                province.command_used_this_turn = True

                self.add_message(f"{province.name}に{general.name}の配置を登録しました")
                self.game_state.record_command(province.owner_daimyo_id, province.id, "assign_general")
        else:
            # Classicモード: 将軍配置または配置解除
            if general is None:
                # 配置解除
                result = self.internal_affairs.remove_governor(province)
                if result["success"]:
                    self.add_message(result["message"])
            else:
                # 将軍配置
                result = self.internal_affairs.assign_governor(province, general)
                if result["success"]:
                    self.add_message(result["message"])
                    # コマンド実行統計を記録
                    self.game_state.record_command(province.owner_daimyo_id, province.id, "assign_general")

                    # プレイヤーコマンドをターンイベントに記録
                    daimyo = self.game_state.get_daimyo(province.owner_daimyo_id)
                    if daimyo and daimyo.is_player:
                        event_msg = f"【{daimyo.clan_name}】{general.name}を{province.name}の守将に任命"
                        self.turn_manager.turn_events.append(event_msg)

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

    def handle_attack_target_click(self, pos):
        """攻撃対象クリック処理"""
        if not self.selected_province_id:
            return

        origin_province = self.game_state.get_province(self.selected_province_id)
        if not origin_province:
            return

        # 隣接する敵領地リストを取得
        adjacent_enemies = []
        for adj_id in origin_province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
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
                if self.selected_attack_target_id == target.id:
                    self.selected_attack_target_id = None
                else:
                    self.selected_attack_target_id = target.id
                    # 決定音再生
                    self.sound_manager.play("decide")
                break

    def _setup_log_file(self):
        """ログファイルを作成（デバッグモードのみ）"""
        if not config.DEBUG_MODE:
            self.log_file = None
            return

        # logsディレクトリを作成
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # 現在時刻からファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/debug_{timestamp}.txt"

        try:
            self.log_file = open(log_filename, "w", encoding="utf-8")
            self.log_file.write(f"=== Nobunaga's Ambition - Debug Log ===\n")
            self.log_file.write(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"Debug Mode: {config.DEBUG_MODE}\n")
            self.log_file.write(f"{'='*80}\n\n")
            self.log_file.flush()
        except Exception as e:
            self.log_file = None

    def add_message(self, message):
        """メッセージをログに追加"""
        self.message_log.append(message)

        # 新しいメッセージが追加されたら、スクロールを最新に戻す
        self.message_scroll_offset = 0
        # ログが長くなりすぎたら古いものを削除（500件まで保持）
        if len(self.message_log) > 500:
            self.message_log.pop(0)

    def write_debug_log(self, content):
        """デバッグログに書き込み（デバッグモードのみ）"""
        if not config.DEBUG_MODE or not self.log_file:
            return

        try:
            self.log_file.write(content)
            self.log_file.flush()
        except Exception:
            pass

    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # 大名死亡演出が表示中は最優先で処理
            if self.daimyo_death_screen.is_visible:
                self.daimyo_death_screen.handle_event(event)
                continue

            # 戦闘プレビューが表示されている場合は優先処理
            if self.battle_preview.is_visible:
                self.battle_preview.handle_event(event)
                continue

            # 戦闘演出が表示されている場合は優先処理
            if self.battle_animation.is_visible:
                self.battle_animation.handle_event(event)
                continue

            # 転送ダイアログが表示されている場合は優先処理
            if self.transfer_dialog.is_visible:
                self.transfer_dialog.handle_event(event)
                continue

            # 将軍配置ダイアログが表示されている場合は優先処理
            if self.general_assign_dialog.is_visible:
                self.general_assign_dialog.handle_event(event)
                continue

            # イベントダイアログが表示されている場合は優先処理
            if self.event_dialog.is_visible:
                self.event_dialog.handle_event(event)
                continue

            # イベント履歴画面が表示されている場合
            if self.event_history_screen.is_visible:
                self.event_history_screen.handle_event(event)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # キャンセル音再生
                    self.sound_manager.play("cancel")

                    if self.show_province_detail:
                        self.close_province_detail()
                    else:
                        self.running = False
                # Hキーでイベント履歴を表示
                elif event.key == pygame.K_h:
                    if not self.show_province_detail and not self.show_attack_selection:
                        self.event_history_screen.show(self.event_system, self.game_state)
                # 矢印キーでメッセージログをスクロール
                elif event.key == pygame.K_UP:
                    self.message_scroll_offset = min(self.message_scroll_offset + 1, len(self.message_log) - self.disp_message)
                elif event.key == pygame.K_DOWN:
                    self.message_scroll_offset = max(self.message_scroll_offset - 1, 0)
                elif event.key == pygame.K_PAGEUP:
                    self.message_scroll_offset = min(self.message_scroll_offset + 10, len(self.message_log) - self.disp_message)
                elif event.key == pygame.K_PAGEDOWN:
                    self.message_scroll_offset = max(self.message_scroll_offset - 10, 0)
            # マウスホイールでスクロール
            elif event.type == pygame.MOUSEWHEEL:
                if not self.show_province_detail and not self.show_attack_selection:
                    self.message_scroll_offset = max(0, min(
                        self.message_scroll_offset - event.y * 3,
                        len(self.message_log) - self.disp_message
                    ))

            # ボタンイベント処理
            if self.show_territory_info:
                # 領地情報パネル表示中 - クリックで閉じる
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.show_territory_info = False
                    self.sound_manager.play("cancel")
            elif self.show_attack_selection:
                # 攻撃対象選択画面
                self.btn_confirm_attack.handle_event(event)
                self.btn_cancel_attack.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_attack_target_click(event.pos)
            elif self.show_province_detail:
                self.btn_close_detail.handle_event(event)

                # V2モード: プレイヤーの番のみコマンド実行可能
                # classicモード: いつでもコマンド実行可能
                can_execute_command = (
                    config.TURN_PROCESSING_MODE == "classic" or
                    (config.TURN_PROCESSING_MODE == "sequential" and
                     self.v2_mode_state == "waiting_player_input")
                )

                if can_execute_command:
                    self.btn_cultivate.handle_event(event)
                    self.btn_develop_town.handle_event(event)
                    self.btn_flood_control.handle_event(event)
                    self.btn_give_rice.handle_event(event)
                    self.btn_recruit.handle_event(event)
                    self.btn_attack.handle_event(event)
                    self.btn_transfer_soldiers.handle_event(event)
                    self.btn_transfer_gold.handle_event(event)
                    self.btn_transfer_rice.handle_event(event)
                    self.btn_assign_general.handle_event(event)
                elif self.game_state.current_turn == 0:
                    # ターン0では将軍配置のみ可能
                    self.btn_assign_general.handle_event(event)
            else:
                # V2モードで「プレイヤーの番」の場合は「行動決定」ボタンを使用
                if config.TURN_PROCESSING_MODE == "sequential" and self.v2_mode_state == "waiting_player_input":
                    self.btn_confirm_actions_v2.handle_event(event)
                elif self.v2_mode_state is None:  # 処理中でない場合のみ
                    self.btn_end_turn.handle_event(event)

                # 領地クリック処理（V2の処理中・アニメーション中は無効）
                if self.v2_mode_state not in ("processing", "animating"):
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_province_click(event.pos)
                        self.handle_portrait_click(event.pos)

    def handle_province_click(self, pos):
        """領地クリック処理"""
        # 勢力マップ上のクリック判定を優先
        province_id = self.power_map.get_province_at_position(pos[0], pos[1], self.game_state)
        if province_id:
            province = self.game_state.get_province(province_id)
            # プレイヤーの領地のみ選択可能
            if province and province.owner_daimyo_id == 1:
                # 決定音再生
                self.sound_manager.play("decide")

                self.selected_province_id = province.id
                self.show_province_detail = True
                return

        # 簡易的な領地選択（リスト形式）
        y_start = 240
        line_height = 25

        player_provinces = self.game_state.get_player_provinces()
        for i, province in enumerate(player_provinces):
            y_pos = y_start + i * line_height
            rect = pygame.Rect(40, y_pos, 600, line_height)

            if rect.collidepoint(pos):
                self.selected_province_id = province.id
                self.show_province_detail = True
                break

    def handle_portrait_click(self, pos):
        """肖像画クリック処理 - 領地情報パネルを表示"""
        # 肖像画の位置（portrait_y = 70）とサイズ（138x138）
        portrait_rect = pygame.Rect(20, 70, 138, 138)

        if portrait_rect.collidepoint(pos):
            # 領地情報パネルの表示/非表示を切り替え
            self.show_territory_info = not self.show_territory_info
            self.sound_manager.play("decide")

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

        # 勢力マップの更新（ハイライトアニメーション＋マウスオーバー）
        mouse_pos = pygame.mouse.get_pos()
        self.power_map.update(mouse_pos, self.game_state)

    def render(self):
        """画面の描画"""
        # 背景画像を描画、なければ単色で塗りつぶし
        # スケール＆トリミング機能を使用
        main_bg = self.image_manager.load_background(
            "main_background.png",
            target_size=(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        if main_bg:
            self.screen.blit(main_bg, (0, 0))
        else:
            self.screen.fill(config.UI_BG_COLOR)

        if self.show_attack_selection:
            self.render_attack_selection()
        elif self.show_province_detail:
            self.render_province_detail()
        else:
            self.render_main_map()

        # 戦闘プレビュー画面を最前面に描画
        if self.battle_preview.is_visible:
            self.battle_preview.draw(self.game_state)

        # 戦闘演出画面を最前面に描画
        if self.battle_animation.is_visible:
            self.battle_animation.draw()

        # イベントダイアログを最前面に描画
        if self.event_dialog.is_visible:
            self.event_dialog.draw()

        # イベント履歴画面を最前面に描画
        if self.event_history_screen.is_visible:
            self.event_history_screen.draw()

        # 転送ダイアログを最前面に描画
        if self.transfer_dialog.is_visible:
            self.transfer_dialog.draw()

        # 将軍配置ダイアログを最前面に描画
        if self.general_assign_dialog.is_visible:
            self.general_assign_dialog.draw()

        # 大名死亡演出画面を最前面に描画
        if self.daimyo_death_screen.is_visible:
            self.daimyo_death_screen.draw()

        # 領地情報パネルを最前面に描画
        if self.show_territory_info:
            self.draw_territory_info_panel()

        pygame.display.flip()

    def render_main_map(self):
        """メインマップ画面を描画"""
        # 背景画像を描画（明るさ調整付き）
        main_bg = self.image_manager.load_background(
            "main_background.png",
            target_size=(config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            brightness=config.BACKGROUND_BRIGHTNESS
        )
        if main_bg:
            self.screen.blit(main_bg, (0, 0))
        else:
            # フォールバック：単色背景
            self.screen.fill(config.UI_BG_COLOR)

        # タイトルとターン情報を横並びに表示
        title = self.font_large.render("信長の野望", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (20, 20))

        # ターン情報（タイトルの右側）
        season_name = self.game_state.get_season_name()
        year = self.game_state.get_year()
        turn_info = f"ターン {self.game_state.current_turn} - {season_name} {year}年"
        turn_text = self.font_medium.render(turn_info, True, config.UI_TEXT_COLOR)
        title_width = title.get_width()
        self.screen.blit(turn_text, (20 + title_width + 30, 28))

        # プレイヤー情報（上にずらす）
        player = self.game_state.get_player_daimyo()
        if player:
            # プレイヤー大名の肖像画を表示（15%拡大して138x138に）
            portrait_y = 70
            portrait_size = (138, 138)
            player_portrait = self.image_manager.get_portrait_for_battle(
                None, player.id, portrait_size
            )
            self.screen.blit(player_portrait, (20, portrait_y))

            # 枠の描画（アニメーション中は強調）
            if self.portrait_highlight_timer > 0:
                # アニメーション中: 黄色の太い枠で脈動
                alpha = int(128 + 127 * (self.portrait_highlight_timer / self.portrait_highlight_duration))
                thickness = 3 + int(2 * (self.portrait_highlight_timer / self.portrait_highlight_duration))
                highlight_color = (255, 215, 0, alpha)  # ゴールド
                pygame.draw.rect(self.screen, highlight_color[:3], (20, portrait_y, 138, 138), thickness)
            else:
                # 通常時: 通常の枠
                pygame.draw.rect(self.screen, config.UI_HIGHLIGHT_COLOR, (20, portrait_y, 138, 138), 2)

            # 大名情報（肖像画の右、肖像が大きくなったので位置調整）
            text_x = 168  # 20 + 138 + 10
            player_info = f"大名: {player.clan_name} {player.name}"
            player_text = self.font_medium.render(player_info, True, config.UI_TEXT_COLOR)
            self.screen.blit(player_text, (text_x, portrait_y + 5))

            province_count = len(player.controlled_provinces)
            total_provinces = len(self.game_state.provinces)
            count_text = f"支配領地: {province_count}/{total_provinces}"
            count_render = self.font_small.render(count_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(count_render, (text_x, portrait_y + 40))

            # 総収支表示
            income = self.economy_system.calculate_total_income(player.id)
            upkeep = self.economy_system.calculate_total_upkeep(player.id)
            balance_text = f"総収入: 金{income['gold']} 米{income['rice']}  総維持: 米{upkeep['rice']}"
            balance_render = self.font_small.render(balance_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(balance_render, (text_x, portrait_y + 70))

        # 勢力マップを描画
        self.power_map.draw(self.game_state)

        # 大名健康状態表示（右側）
        self.draw_daimyo_health_status()

        # ボタン（メッセージログの上に配置）
        # V2モードで「プレイヤーの番」の場合は「行動決定」ボタンを表示
        if config.TURN_PROCESSING_MODE == "sequential" and self.v2_mode_state == "waiting_player_input":
            self.btn_confirm_actions_v2.draw(self.screen)
        elif self.v2_mode_state is None:  # V2モードで処理中でない、またはclassicモード
            # ボタンのテキストを状態に応じて変更
            if self.game_state.current_turn == 0:
                self.btn_end_turn.text = "統一開始"
            else:
                self.btn_end_turn.text = "次のターンへ"
            self.btn_end_turn.draw(self.screen)

        # 操作説明（ボタンの右側）
        help_y = config.SCREEN_HEIGHT - 30
        help_text = "操作: [ESC]終了 [H]イベント履歴 [↑↓]ログスクロール"
        text = self.font_small.render(help_text, True, config.LIGHT_GRAY)
        self.screen.blit(text, (100, help_y))

        # メッセージログ（スクロール可能）- 高い位置から表示
        log_y_start = 220  # 固定位置から開始
        log_y = log_y_start

        log_title = self.font_small.render("=== 軍報 ===", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(log_title, (20, log_y))

        # スクロール位置の表示
        if len(self.message_log) > self.disp_message:
            scroll_info = f"({len(self.message_log) - self.message_scroll_offset - self.disp_message}/{len(self.message_log)})"
            scroll_text = self.font_small.render(scroll_info, True, config.LIGHT_GRAY)
            self.screen.blit(scroll_text, (250, log_y))

        log_y += 25
        # スクロール位置に基づいて表示
        if len(self.message_log) <= self.disp_message:
            # self.disp_message件以下ならすべて表示
            display_messages = self.message_log
        else:
            # スクロールオフセットを適用
            start_idx = max(0, len(self.message_log) - self.disp_message - self.message_scroll_offset)
            end_idx = len(self.message_log) - self.message_scroll_offset
            display_messages = self.message_log[start_idx:end_idx]

        for message in display_messages:
            # 長いメッセージは100文字まで表示
            display_message = message[:100]
            msg_text = self.font_small.render(display_message, True, config.LIGHT_GRAY)
            self.screen.blit(msg_text, (30, log_y))
            log_y += 16

    def draw_daimyo_health_status(self):
        """全大名の健康状態を表示"""
        # 画面右側に表示
        panel_x = 510
        panel_y = 40
        panel_width = 340

        # タイトル
        title = self.font_medium.render("=== 天下情勢 ===", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (panel_x, panel_y))

        y_pos = panel_y + 27

        # 全大名の情報を表示
        for daimyo in sorted(self.game_state.daimyo.values(), key=lambda d: d.id):
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
            self.screen.blit(status_surface, (panel_x + 90, y_pos ))

            y_pos += 24

    def draw_territory_info_panel(self):
        """支配領地情報パネルを描画"""
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
        player = self.game_state.get_player_daimyo()
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
        header = self.font_medium.render("領地名      金    米    農民  兵士  開発 町  治水", True, config.UI_TEXT_COLOR)
        self.screen.blit(header, (panel_x + 20, header_y))

        # 領地リスト
        y_pos = header_y + 30
        player_provinces = self.game_state.get_player_provinces()

        for province in player_provinces:
            # 領地名
            name_text = f"{province.name:8}"
            name_render = self.font_small.render(name_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(name_render, (panel_x + 20, y_pos))

            # 資源情報
            info_text = f"{province.gold:5} {province.rice:5} {province.peasants:5} {province.soldiers:4} {province.development_level:4} {province.town_level:3} {province.flood_control:3}%"
            info_render = self.font_small.render(info_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(info_render, (panel_x + 120, y_pos))

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

    def render_province_detail(self):
        """領地詳細画面を描画"""
        province = self.game_state.get_province(self.selected_province_id)
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
            general = self.game_state.get_general(province.governor_general_id)
            info_lines.append(f"守将: {general.name}")
            info_lines.append(f"  武力{general.war_skill} 統率{general.leadership} 政治{general.politics} 知力{general.intelligence}")
        else:
            info_lines.append(f"守将: なし")

        # 防御力計算
        base_defense_power = province.get_combat_power()
        defense_bonus = province.get_defense_bonus()
        general_bonus = general.get_combat_bonus() if general else 1.0

        final_defense_power = int(base_defense_power * defense_bonus * general_bonus)

        info_lines.append(f"防御力: {final_defense_power:,} (基本{base_defense_power:,} × 地形{defense_bonus:.2f} × 将軍{general_bonus:.2f})")

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
        self.screen.blit(loyalty_label, (100, 525))
        loyalty_bar = ProgressBar(100, 550, 300, 25, 100, province.peasant_loyalty)
        loyalty_bar.draw(self.screen, self.font_small)

        # 士気バー
        morale_label = self.font_small.render("兵士士気:", True, config.UI_TEXT_COLOR)
        self.screen.blit(morale_label, (100, 585))
        morale_bar = ProgressBar(100, 610, 300, 25, 100, province.soldier_morale)
        morale_bar.draw(self.screen, self.font_small)

        # 内政コマンドパネル
        cmd_panel = Panel(520, 220, 220, 250, "内政コマンド", self.font_medium)
        cmd_panel.draw(self.screen)

        # コマンドボタン
        province = self.game_state.get_province(self.selected_province_id)

        # V2モード: プレイヤーの番のみコマンド実行可能
        can_execute_command = (
            config.TURN_PROCESSING_MODE == "classic" or
            (config.TURN_PROCESSING_MODE == "sequential" and
             self.v2_mode_state == "waiting_player_input")
        )

        self.btn_cultivate.set_enabled(
            can_execute_command and
            province.can_afford(gold=config.CULTIVATION_COST) and not province.command_used_this_turn
        )
        self.btn_develop_town.set_enabled(
            can_execute_command and
            province.can_afford(gold=config.TOWN_DEVELOPMENT_COST) and not province.command_used_this_turn
        )
        self.btn_flood_control.set_enabled(
            can_execute_command and
            province.can_afford(gold=config.FLOOD_CONTROL_COST) and not province.command_used_this_turn
        )
        self.btn_give_rice.set_enabled(
            can_execute_command and
            province.can_afford(rice=config.GIVE_RICE_AMOUNT) and not province.command_used_this_turn
        )

        self.btn_cultivate.draw(self.screen)
        self.btn_develop_town.draw(self.screen)
        self.btn_flood_control.draw(self.screen)
        self.btn_give_rice.draw(self.screen)

        # ステータスメッセージ表示
        if province.command_used_this_turn:
            status_text = self.font_small.render("このターンのコマンドは実行済みです", True, config.STATUS_NEUTRAL)
            self.screen.blit(status_text, (840, 680))
        elif not can_execute_command:
            status_text = self.font_small.render("「ターン終了」を押してください", True, config.STATUS_NEUTRAL)
            self.screen.blit(status_text, (840, 680))

        # 軍事コマンドパネル
        mil_panel = Panel(520, 500, 220, 140, "軍事コマンド", self.font_medium)
        mil_panel.draw(self.screen)

        # 軍事ボタンの有効/無効を設定
        recruit_cost = 100 * config.RECRUIT_COST_PER_SOLDIER  # 100人 × 2 = 200金
        self.btn_recruit.set_enabled(
            can_execute_command and
            province.peasants >= 100 and
            province.gold >= recruit_cost and
            not province.command_used_this_turn
        )
        self.btn_attack.set_enabled(
            can_execute_command and
            province.soldiers >= 100 and not province.command_used_this_turn
        )

        self.btn_recruit.draw(self.screen)
        self.btn_attack.draw(self.screen)

        # 転送コマンドパネル
        transfer_panel = Panel(770, 220, 220, 250, "転送コマンド", self.font_medium)
        transfer_panel.draw(self.screen)

        # 転送可能な隣接領地があるかチェック
        valid_targets = self.transfer_system.get_valid_transfer_targets(self.selected_province_id)
        has_targets = len(valid_targets) > 0

        # 転送ボタンの有効/無効を設定
        self.btn_transfer_soldiers.set_enabled(
            can_execute_command and
            has_targets and province.soldiers > 10 and not province.command_used_this_turn
        )
        self.btn_transfer_gold.set_enabled(
            can_execute_command and
            has_targets and province.gold > 0 and not province.command_used_this_turn
        )
        self.btn_transfer_rice.set_enabled(
            can_execute_command and
            has_targets and province.rice > 0 and not province.command_used_this_turn
        )

        self.btn_transfer_soldiers.draw(self.screen)
        self.btn_transfer_gold.draw(self.screen)
        self.btn_transfer_rice.draw(self.screen)

        # 将軍配置ボタンの有効化設定と描画
        # Turn 0でも将軍配置は可能にする
        can_assign_general = (
            can_execute_command or
            (self.game_state.current_turn == 0 and not province.command_used_this_turn)
        )
        self.btn_assign_general.set_enabled(can_assign_general)
        self.btn_assign_general.draw(self.screen)

        # 転送情報の表示
        transfer_info_y = 490
        if has_targets:
            info_text = f"隣接領地: {len(valid_targets)}箇所"
        else:
            info_text = "隣接領地なし"
        text = self.font_small.render(info_text, True, config.UI_TEXT_COLOR)
        self.screen.blit(text, (810, transfer_info_y))

        # 戻るボタン
        self.btn_close_detail.draw(self.screen)

    def render_attack_selection(self):
        """攻撃対象選択画面を描画"""
        if not self.selected_province_id:
            return

        origin_province = self.game_state.get_province(self.selected_province_id)
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

        # 隣接する敵領地リストを取得
        adjacent_enemies = []
        for adj_id in origin_province.adjacent_provinces:
            adj_province = self.game_state.get_province(adj_id)
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
                if self.selected_attack_target_id == target.id:
                    highlight_rect = pygame.Rect(100, y, 600, 30)
                    pygame.draw.rect(self.screen, config.UI_HIGHLIGHT_COLOR, highlight_rect)
                    text_color = config.BLACK
                else:
                    text_color = config.UI_TEXT_COLOR

                owner = self.game_state.get_daimyo(target.owner_daimyo_id)
                owner_name = owner.clan_name if owner else "無所属"

                info = f"{target.name} ({owner_name})  守備兵: {target.soldiers}人  城: {'有' if target.has_castle else '無'}"
                text = self.font_small.render(info, True, text_color)
                self.screen.blit(text, (120, y))

                # 勝率予測（簡易版）
                attack_force = int(origin_province.soldiers * 0.8)
                if attack_force > target.soldiers * 1.5:
                    recommendation = "有利"
                    color = config.STATUS_POSITIVE
                elif attack_force > target.soldiers:
                    recommendation = "互角"
                    color = config.STATUS_NEUTRAL
                else:
                    recommendation = "不利"
                    color = config.STATUS_NEGATIVE

                pred_text = self.font_small.render(f"  予測: {recommendation}", True, text_color if self.selected_attack_target_id == target.id else color)
                self.screen.blit(pred_text, (650, y))

                y += 30

        # 説明
        help_text = self.font_small.render("領地をクリックして選択", True, config.LIGHT_GRAY)
        self.screen.blit(help_text, (100, config.SCREEN_HEIGHT - 150))

        # ボタン表示
        # 決定ボタンは選択中のみ有効化
        if self.selected_attack_target_id is not None:
            self.btn_confirm_attack.enabled = True
        else:
            self.btn_confirm_attack.enabled = False

        self.btn_confirm_attack.draw(self.screen)
        self.btn_cancel_attack.draw(self.screen)

    def run(self):
        """メインゲームループ"""
        try:
            print("=== Nobunaga's Ambition - Game Start ===")
            print(f"Player: {self.game_state.get_player_daimyo()}")
            print(f"Provinces: {len(self.game_state.provinces)}")
            print()
        except:
            pass

        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(config.FPS)

        self.quit()

    def quit(self):
        """ゲーム終了"""
        # ログファイルを閉じる
        if self.log_file:
            try:
                self.log_file.write(f"\n{'='*80}\n")
                self.log_file.write(f"Game End - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"Total Turns: {self.game_state.current_turn}\n")
                self.log_file.close()
            except Exception:
                pass  # エラーは無視

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
