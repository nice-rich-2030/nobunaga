"""
信長の野望 - メインエントリーポイント
pygameを使用した戦略シミュレーションゲーム
"""
import pygame
import sys
import config
from core.game_state import GameState
from core.turn_manager import TurnManager
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

        # ゲームシステムの初期化
        self.turn_manager = TurnManager(self.game_state)
        self.economy_system = EconomySystem(self.game_state)
        self.internal_affairs = InternalAffairsSystem(self.game_state)

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
            self.diplomacy_system
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

        # ゲーム実行フラグ
        self.running = True

        # UI状態
        self.selected_province_id = None
        self.show_province_detail = False
        self.show_attack_selection = False
        self.message_log = []
        self.message_scroll_offset = 0  # メッセージログのスクロール位置
        self.disp_message = 7

        # 戦闘演出管理
        self.pending_battle_animations = []  # 表示待ちの戦闘演出
        self.pending_turn_messages = []  # 演出後に表示するメッセージ
        self.current_battle_index = 0  # 現在表示中の戦闘インデックス

        # ボタンの作成
        self.create_buttons()

    def create_buttons(self):
        """ボタンを作成"""
        button_y = config.SCREEN_HEIGHT - 50

        self.btn_end_turn = Button(
            1100,button_y, 150, 40,
            "ターン終了",
            self.font_medium,
            self.end_turn
        )

        # イベントダイアログ
        self.event_dialog = EventDialog(self.screen, self.font_medium)

        # イベント履歴画面
        self.event_history_screen = EventHistoryScreen(self.screen, self.font_medium)

        # 勢力マップ
        self.power_map = PowerMap(self.screen, self.font_medium)

        # 戦闘プレビュー画面（勢力図を使うので後に初期化）
        self.battle_preview = BattlePreviewScreen(self.screen, self.font_medium, self.power_map)

        # 戦闘演出画面
        self.battle_animation = BattleAnimationScreen(self.screen, self.font_medium)

        # 転送ダイアログ
        self.transfer_dialog = TransferDialog(self.screen, self.font_medium)

        # 将軍配置ダイアログ
        self.general_assign_dialog = GeneralAssignDialog(self.screen, self.font_medium)

        self.btn_close_detail = Button(
            config.SCREEN_WIDTH - 170, button_y, 150, 40,
            "戻る",
            self.font_medium,
            self.close_province_detail
        )

        # 内政コマンドボタン
        self.btn_cultivate = Button(
            540, 270, 180, 35,
            "開墾 (金200)",
            self.font_small,
            lambda: self.execute_command("cultivate")
        )

        self.btn_develop_town = Button(
            540, 315, 180, 35,
            "町開発 (金300)",
            self.font_small,
            lambda: self.execute_command("develop_town")
        )

        self.btn_flood_control = Button(
            540, 360, 180, 35,
            "治水 (金150)",
            self.font_small,
            lambda: self.execute_command("flood_control")
        )

        self.btn_give_rice = Button(
            540, 405, 180, 35,
            "米配布 (米100)",
            self.font_small,
            lambda: self.execute_command("give_rice")
        )

        # 軍事コマンドボタン
        self.btn_recruit = Button(
            540, 540, 180, 35,
            "100人徴兵 (金200)",
            self.font_small,
            lambda: self.execute_command("recruit")
        )

        self.btn_attack = Button(
            540, 585, 180, 35,
            "攻撃",
            self.font_small,
            lambda: self.execute_command("attack")
        )

        # 転送コマンドボタン
        self.btn_transfer_soldiers = Button(
            790, 270, 180, 35,
            "兵士転送",
            self.font_small,
            lambda: self.execute_command("transfer_soldiers")
        )

        self.btn_transfer_gold = Button(
            790, 315, 180, 35,
            "金送付",
            self.font_small,
            lambda: self.execute_command("transfer_gold")
        )

        self.btn_transfer_rice = Button(
            790, 360, 180, 35,
            "米運搬",
            self.font_small,
            lambda: self.execute_command("transfer_rice")
        )

        # 将軍配置ボタン
        self.btn_assign_general = Button(
            790, 405, 180, 35,
            "将軍配置",
            self.font_small,
            lambda: self.execute_command("assign_general")
        )

    def execute_command(self, command_type):
        """コマンドを実行"""
        if not self.selected_province_id:
            return

        province = self.game_state.get_province(self.selected_province_id)
        if not province or province.command_used_this_turn:
            self.add_message("このターンは既にコマンドを実行しました")
            return

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
        result = self.military_system.create_attack_army(
            origin_province,
            target_province,
            attack_force,
            None  # 武将なし（将来実装）
        )

        if result["success"]:
            army = result["army"]
            # 戦闘をキューに追加
            self.turn_manager.queue_battle({
                "army": army,
                "target_province_id": target_province_id,
                "origin_province_id": origin_province.id
            })
            origin_province.command_used_this_turn = True
            self.show_attack_selection = False
            return {"success": True, "message": f"{target_province.name}への攻撃軍を編成しました（{attack_force}人）"}
        else:
            return result

    def end_turn(self):
        """ターン終了"""
        winner = self.turn_manager.execute_turn()

        # ターンイベントを取得（戦闘メッセージは含まない）
        all_events = self.turn_manager.get_turn_events()

        # 戦闘メッセージ以外を保留
        self.pending_turn_messages = []
        for event in all_events:
            # 戦闘メッセージは個別に表示するのでスキップ
            if "【戦闘】" not in event and "⚔" not in event and "🛡" not in event and "★" not in event:
                self.pending_turn_messages.append(event)

        # 戦闘結果があれば演出キューに追加
        if self.turn_manager.battle_results:
            self.pending_battle_animations = self.turn_manager.battle_results.copy()
            self.current_battle_index = 0
            # 最初の戦闘演出を開始
            self.show_next_battle()
        else:
            # 戦闘がなければすぐにメッセージを表示
            self.flush_turn_messages()

        # 保留中のイベント選択があれば表示（戦闘演出後）
        if self.turn_manager.pending_event_choices and not self.battle_animation.is_visible:
            event_data = self.turn_manager.pending_event_choices[0]
            self.event_dialog.show(
                event_data["event"],
                event_data["province"],
                self.on_event_choice_selected
            )

        if winner:
            daimyo = self.game_state.get_daimyo(winner)
            if daimyo:
                self.add_message(f"*** {daimyo.clan_name} {daimyo.name}が天下統一！***")

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
            self.flush_turn_messages()

    def show_battle_animation(self, battle_data):
        """戦闘アニメーション画面を表示（プレビュー後）"""
        self.battle_animation.show(battle_data, on_finish=self.on_battle_animation_finished)

    def on_battle_animation_finished(self):
        """戦闘演出が終了したときのコールバック"""
        # 今終わった戦闘の結果を処理
        if self.current_battle_index > 0:
            battle_data = self.pending_battle_animations[self.current_battle_index - 1]

            # 1. 戦闘結果を実際に適用（領地の所有者変更など）
            if "combat_system" in battle_data and "army" in battle_data:
                combat_system = battle_data["combat_system"]
                army = battle_data["army"]
                target_province = self.game_state.get_province(battle_data["target_province_id"])
                result = battle_data["result"]

                if target_province:
                    # 結果を適用
                    combat_system.apply_battle_result(result, army, target_province)

                    # 敗北した軍は撤退（削除）
                    if not result.attacker_won and army.id in self.game_state.armies:
                        origin_province = self.game_state.get_province(battle_data["origin_province_id"])
                        if origin_province and army.total_troops > 0:
                            origin_province.add_soldiers(army.total_troops)
                        del self.game_state.armies[army.id]

            # 2. 勢力図の反映（領地変更があればハイライト）
            if battle_data.get("result") and battle_data["result"].province_captured:
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

        # 既にコマンド使用済みかチェック
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

        # 将軍配置または配置解除
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

    def close_province_detail(self):
        """領地詳細を閉じる"""
        self.show_province_detail = False
        self.show_attack_selection = False
        self.selected_province_id = None

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
                result = self.execute_attack(target.id)
                if result:
                    self.add_message(result["message"])
                break

    def add_message(self, message):
        """メッセージをログに追加"""
        self.message_log.append(message)
        # 新しいメッセージが追加されたら、スクロールを最新に戻す
        self.message_scroll_offset = 0
        # ログが長くなりすぎたら古いものを削除（500件まで保持）
        if len(self.message_log) > 500:
            self.message_log.pop(0)

    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

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
            if self.show_attack_selection:
                # 攻撃対象選択画面
                self.btn_close_detail.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_attack_target_click(event.pos)
            elif self.show_province_detail:
                self.btn_close_detail.handle_event(event)
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
            else:
                self.btn_end_turn.handle_event(event)

                # 領地クリック処理
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_province_click(event.pos)

    def handle_province_click(self, pos):
        """領地クリック処理"""
        # 勢力マップ上のクリック判定を優先
        province_id = self.power_map.get_province_at_position(pos[0], pos[1], self.game_state)
        if province_id:
            province = self.game_state.get_province(province_id)
            # プレイヤーの領地のみ選択可能
            if province and province.owner_daimyo_id == 1:
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

    def update(self):
        """ゲームロジックの更新"""
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

        pygame.display.flip()

    def render_main_map(self):
        """メインマップ画面を描画"""
        # タイトル
        title = self.font_large.render("信長の野望", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title, (20, 20))

        # ターン情報
        season_name = self.game_state.get_season_name()
        year = self.game_state.get_year()
        turn_info = f"ターン {self.game_state.current_turn} - {season_name} {year}年"
        turn_text = self.font_medium.render(turn_info, True, config.UI_TEXT_COLOR)
        self.screen.blit(turn_text, (20, 70))

        # プレイヤー情報
        player = self.game_state.get_player_daimyo()
        if player:
            player_info = f"大名: {player.clan_name} {player.name}"
            player_text = self.font_medium.render(player_info, True, config.UI_TEXT_COLOR)
            self.screen.blit(player_text, (20, 110))

            province_count = len(player.controlled_provinces)
            total_provinces = len(self.game_state.provinces)
            count_text = f"支配領地: {province_count}/{total_provinces}"
            count_render = self.font_small.render(count_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(count_render, (20, 145))

            # 総収支表示
            income = self.economy_system.calculate_total_income(player.id)
            upkeep = self.economy_system.calculate_total_upkeep(player.id)
            balance_text = f"総収入: 金{income['gold']} 米{income['rice']}  総維持: 米{upkeep['rice']}"
            balance_render = self.font_small.render(balance_text, True, config.UI_TEXT_COLOR)
            self.screen.blit(balance_render, (20, 170))

        # 領地一覧
        title_text = self.font_medium.render("=== 支配領地一覧 ===", True, config.UI_HIGHLIGHT_COLOR)
        self.screen.blit(title_text, (20, 205))

        help_text = self.font_small.render("（クリックで詳細表示）", True, config.GRAY)
        self.screen.blit(help_text, (250, 210))

        y_pos = 235
        player_provinces = self.game_state.get_player_provinces()
        for province in player_provinces:
            # 領地情報
            info = f"{province.name}: 金{province.gold} 米{province.rice} 農民{province.peasants} 兵{province.soldiers}"
            if province.command_used_this_turn:
                info += " [✓]"

            text = self.font_small.render(info, True, config.UI_TEXT_COLOR)
            self.screen.blit(text, (40, y_pos))
            y_pos += 19

        # 勢力マップを描画
        self.power_map.draw(self.game_state)

        # ボタン（メッセージログの上に配置）
        self.btn_end_turn.draw(self.screen)

        # 操作説明（ボタンの右側）
        help_y = config.SCREEN_HEIGHT - 30
        help_text = "操作: [ESC]終了 [H]イベント履歴 [↑↓]ログスクロール"
        text = self.font_small.render(help_text, True, config.LIGHT_GRAY)
        self.screen.blit(text, (100, help_y))

        # メッセージログ（スクロール可能）- 最下部から上に配置
        log_height = self.disp_message * 16 + 30  # 15行 × 16ピクセル + ヘッダー
        log_y_start = config.SCREEN_HEIGHT - 65 - log_height
        log_y = log_y_start

        log_title = self.font_small.render("=== メッセージログ ===", True, config.UI_HIGHLIGHT_COLOR)
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
        self.btn_cultivate.set_enabled(
            province.can_afford(gold=config.CULTIVATION_COST) and not province.command_used_this_turn
        )
        self.btn_develop_town.set_enabled(
            province.can_afford(gold=config.TOWN_DEVELOPMENT_COST) and not province.command_used_this_turn
        )
        self.btn_flood_control.set_enabled(
            province.can_afford(gold=config.FLOOD_CONTROL_COST) and not province.command_used_this_turn
        )
        self.btn_give_rice.set_enabled(
            province.can_afford(rice=config.GIVE_RICE_AMOUNT) and not province.command_used_this_turn
        )

        self.btn_cultivate.draw(self.screen)
        self.btn_develop_town.draw(self.screen)
        self.btn_flood_control.draw(self.screen)
        self.btn_give_rice.draw(self.screen)

        if province.command_used_this_turn:
            status_text = self.font_small.render("このターンのコマンドは実行済みです", True, config.STATUS_NEUTRAL)
            self.screen.blit(status_text, (840, 680))

        # 軍事コマンドパネル
        mil_panel = Panel(520, 500, 220, 140, "軍事コマンド", self.font_medium)
        mil_panel.draw(self.screen)

        # 軍事ボタンの有効/無効を設定
        recruit_cost = 100 * config.RECRUIT_COST_PER_SOLDIER  # 100人 × 2 = 200金
        self.btn_recruit.set_enabled(
            province.peasants >= 100 and
            province.gold >= recruit_cost and
            not province.command_used_this_turn
        )
        self.btn_attack.set_enabled(
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
            has_targets and province.soldiers > 10 and not province.command_used_this_turn
        )
        self.btn_transfer_gold.set_enabled(
            has_targets and province.gold > 0 and not province.command_used_this_turn
        )
        self.btn_transfer_rice.set_enabled(
            has_targets and province.rice > 0 and not province.command_used_this_turn
        )

        self.btn_transfer_soldiers.draw(self.screen)
        self.btn_transfer_gold.draw(self.screen)
        self.btn_transfer_rice.draw(self.screen)

        # 将軍配置ボタンの有効化設定と描画
        self.btn_assign_general.set_enabled(True)  # 将軍配置はターン制限なし
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
                owner = self.game_state.get_daimyo(target.owner_daimyo_id)
                owner_name = owner.clan_name if owner else "無所属"

                info = f"{target.name} ({owner_name})  守備兵: {target.soldiers}人  城: {'有' if target.has_castle else '無'}"
                text = self.font_small.render(info, True, config.UI_TEXT_COLOR)
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

                pred_text = self.font_small.render(f"  予測: {recommendation}", True, color)
                self.screen.blit(pred_text, (650, y))

                y += 30

        # 説明
        help_text = self.font_small.render("領地をクリックして攻撃", True, config.LIGHT_GRAY)
        self.screen.blit(help_text, (100, config.SCREEN_HEIGHT - 150))

        # 戻るボタン
        self.btn_close_detail.draw(self.screen)

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
