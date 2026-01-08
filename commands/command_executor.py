"""
コマンド実行モジュール

内政・軍事コマンドの実行を担当するクラス
"""


class CommandExecutor:
    """コマンド実行を管理するクラス"""

    def __init__(self, game_instance):
        """初期化

        Args:
            game_instance: Gameクラスのインスタンス
        """
        self.game = game_instance

    def execute_command(self, command_type):
        """コマンドを実行（Sequential方式では記録のみ、classicモードは即座に実行）"""
        if not self.game.selected_province_id:
            return

        province = self.game.game_state.get_province(self.game.selected_province_id)
        if not province or province.command_used_this_turn:
            self.game.add_message("このターンは既にコマンドを実行しました")
            return

        # Sequential方式: コマンドを記録だけして、「行動決定」時に実行
        # 武将配置は常に即時実行なので例外処理不要
        if self.game.seq_mode_state == "waiting_player_input":
            self._register_command(command_type, province)
            return

        # 即座に実行するケース
        result = None
        if command_type == "cultivate":
            result = self.game.internal_affairs.execute_cultivation(province)
        elif command_type == "develop_town":
            result = self.game.internal_affairs.execute_town_development(province)
        elif command_type == "flood_control":
            result = self.game.internal_affairs.execute_flood_control(province)
        elif command_type == "give_rice":
            result = self.game.internal_affairs.execute_give_rice(province)
        elif command_type == "recruit":
            result = self.game.military_system.recruit_soldiers(province, 100)
        elif command_type == "attack":
            # 攻撃対象選択状態を初期化
            self.game.selected_attack_target_id = None
            self.game.show_attack_selection = True
            return  # 攻撃対象選択画面に遷移
        elif command_type == "transfer_soldiers":
            self.game.show_transfer_dialog("soldiers")
            return
        elif command_type == "transfer_gold":
            self.game.show_transfer_dialog("gold")
            return
        elif command_type == "transfer_rice":
            self.game.show_transfer_dialog("rice")
            return
        elif command_type == "assign_general":
            self.game.show_general_assign_dialog()
            return

        if result:
            self.game.add_message(result["message"])
            if result["success"]:
                province.command_used_this_turn = True
                # コマンド実行統計を記録
                self.game.game_state.record_command(province.owner_daimyo_id, province.id, command_type)

                # プレイヤーコマンドをターンイベントに記録
                daimyo = self.game.game_state.get_daimyo(province.owner_daimyo_id)
                if daimyo and daimyo.is_player:
                    event_msg = self._format_player_command_event(daimyo, province, command_type)
                    if event_msg:
                        self.game.turn_manager.turn_events.append(event_msg)

    def _register_command(self, command_type, province):
        """Sequential方式: コマンドを記録（即座には実行しない）"""
        # ダイアログ系コマンドは後で処理（フラグは設定しない）
        if command_type in ["transfer_soldiers", "transfer_gold", "transfer_rice", "assign_general"]:
            if command_type == "transfer_soldiers":
                self.game.show_transfer_dialog("soldiers")
            elif command_type == "transfer_gold":
                self.game.show_transfer_dialog("gold")
            elif command_type == "transfer_rice":
                self.game.show_transfer_dialog("rice")
            elif command_type == "assign_general":
                self.game.show_general_assign_dialog()
            return

        if command_type == "attack":
            # 攻撃対象選択画面へ
            self.game.selected_attack_target_id = None
            self.game.show_attack_selection = True
            return

        # 内政コマンド
        internal_commands = ["cultivate", "develop_town", "flood_control", "give_rice"]
        if command_type in internal_commands:
            self.game.player_internal_commands.append({
                "type": command_type,
                "province_id": province.id
            })
            province.command_used_this_turn = True
            self.game.add_message(f"{province.name}で{self._get_command_name(command_type)}を登録しました")
            return

        # 軍事コマンド（徴兵）
        if command_type == "recruit":
            self.game.player_military_commands.append({
                "type": "recruit",
                "province_id": province.id
            })
            province.command_used_this_turn = True
            self.game.add_message(f"{province.name}で徴兵を登録しました")

    def _get_command_name(self, command_type):
        """コマンドタイプから日本語名を取得"""
        names = {
            "cultivate": "開墾",
            "develop_town": "町開発",
            "flood_control": "治水",
            "give_rice": "米配布"
        }
        return names.get(command_type, command_type)

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

    def execute_attack(self, target_province_id):
        """攻撃を実行"""
        if not self.game.selected_province_id:
            return

        origin_province = self.game.game_state.get_province(self.game.selected_province_id)
        target_province = self.game.game_state.get_province(target_province_id)

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

        # 攻撃軍を編成（選択された比率を使用）
        attack_force = int(origin_province.soldiers * self.game.selected_attack_ratio)
        # 守将がいれば将軍として配属
        general_id = origin_province.governor_general_id

        # 基本的な検証（実際の軍作成は実行時）
        if origin_province.soldiers < attack_force:
            return {"success": False, "message": "兵士が不足しています"}

        # 軍事コマンドリストに追加（軍は作成しない、実行時に作成）
        self.game.player_military_commands.append({
            "type": "attack",
            "province_id": origin_province.id,
            "target_id": target_province_id,
            "attack_force": attack_force,
            "general_id": general_id
        })
        origin_province.command_used_this_turn = True

        # コマンド実行統計を記録
        self.game.game_state.record_command(origin_province.owner_daimyo_id, origin_province.id, "attack")

        # ターンイベントに記録
        daimyo = self.game.game_state.get_daimyo(origin_province.owner_daimyo_id)
        if daimyo and daimyo.is_player:
            defender_name = "無所属"
            if target_province.owner_daimyo_id:
                defender_daimyo = self.game.game_state.get_daimyo(target_province.owner_daimyo_id)
                if defender_daimyo:
                    defender_name = defender_daimyo.clan_name
            event_msg = f"【{daimyo.clan_name}】{origin_province.name}から{defender_name}の{target_province.name}へ攻撃準備（兵力{attack_force}人）"
            self.game.turn_manager.turn_events.append(event_msg)

        self.game.show_attack_selection = False
        return {"success": True, "message": f"{target_province.name}への攻撃を準備しました（{attack_force}人）"}
