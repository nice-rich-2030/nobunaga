"""
転送・配置処理モジュール

資源転送と武将配置の処理を担当するクラス
"""


class TransferHandler:
    """転送・配置処理を管理するクラス"""

    def __init__(self, game_instance):
        """初期化

        Args:
            game_instance: Gameクラスのインスタンス
        """
        self.game = game_instance

    def show_transfer_dialog(self, resource_type):
        """転送ダイアログを表示"""
        if not self.game.selected_province_id:
            return

        province = self.game.game_state.get_province(self.game.selected_province_id)
        if not province:
            return

        # 転送可能な隣接領地を取得
        target_provinces = self.game.transfer_system.get_valid_transfer_targets(self.game.selected_province_id)

        if not target_provinces:
            self.game.add_message("転送可能な隣接領地がありません")
            return

        # 転送可能な最大量を計算
        max_amount = 0
        if resource_type == "soldiers":
            max_amount = min(province.soldiers - 10, self.game.transfer_system.MAX_SOLDIERS_TRANSFER)
        elif resource_type == "gold":
            max_amount = min(province.gold, self.game.transfer_system.MAX_GOLD_TRANSFER)
        elif resource_type == "rice":
            max_amount = min(province.rice, self.game.transfer_system.MAX_RICE_TRANSFER)

        if max_amount <= 0:
            resource_names = {"soldiers": "兵士", "gold": "金", "rice": "米"}
            self.game.add_message(f"{resource_names.get(resource_type)}が不足しています")
            return

        # ダイアログを表示
        self.game.transfer_dialog.show(
            province,
            target_provinces,
            resource_type,
            max_amount,
            lambda target_id, amount: self.execute_transfer(resource_type, target_id, amount),
            lambda: None  # キャンセル時は何もしない
        )

    def execute_transfer(self, resource_type, target_province_id, amount):
        """転送を実行（即時実行）"""
        if not self.game.selected_province_id:
            return

        province = self.game.game_state.get_province(self.game.selected_province_id)
        if not province:
            return

        # 既にコマンド使用済みかチェック
        if province.command_used_this_turn:
            self.game.add_message("この領地は既にコマンドを登録しました")
            return

        # 転送を即時実行
        result = None
        if resource_type == "soldiers":
            result = self.game.transfer_system.transfer_soldiers(
                province.id,
                target_province_id,
                amount
            )
        elif resource_type == "gold":
            result = self.game.transfer_system.transfer_gold(
                province.id,
                target_province_id,
                amount
            )
        elif resource_type == "rice":
            result = self.game.transfer_system.transfer_rice(
                province.id,
                target_province_id,
                amount
            )

        if result and result.success:
            province.command_used_this_turn = True
            self.game.add_message(result.message)
            # 統計記録のみ実行
            command_type_map = {
                "soldiers": "transfer_soldiers",
                "gold": "transfer_gold",
                "rice": "transfer_rice"
            }
            self.game.game_state.record_command(
                province.owner_daimyo_id,
                province.id,
                command_type_map[resource_type]
            )
        else:
            error_msg = result.message if result else "転送に失敗しました"
            self.game.add_message(error_msg)

    def show_general_assign_dialog(self):
        """将軍配置ダイアログを表示"""
        if not self.game.selected_province_id:
            return

        province = self.game.game_state.get_province(self.game.selected_province_id)
        if not province:
            return

        # 配置可能な将軍を取得（プレイヤーに仕える将軍で配置されていないもの）
        player_daimyo = self.game.game_state.get_player_daimyo()
        if not player_daimyo:
            return

        available_generals = [
            general for general in self.game.game_state.generals.values()
            if general.serving_daimyo_id == player_daimyo.id and general.is_available
        ]

        # 現在配置されている将軍を取得
        current_general = None
        if province.governor_general_id:
            current_general = self.game.game_state.get_general(province.governor_general_id)

        # ダイアログを表示
        self.game.general_assign_dialog.show(
            province,
            available_generals,
            lambda general: self.execute_general_assignment(general),
            lambda: None,  # キャンセル時は何もしない
            current_general
        )

    def execute_general_assignment(self, general):
        """将軍配置を実行"""
        if not self.game.selected_province_id:
            return

        province = self.game.game_state.get_province(self.game.selected_province_id)
        if not province:
            return

        # コマンド使用済みチェックを削除
        # （将軍配置・配置解除はコマンドとして扱わない）

        # 将軍配置または配置解除
        if general is None:
            # 配置解除（即時実行）
            result = self.game.internal_affairs.remove_governor(province)
            if result["success"]:
                self.game.add_message(result["message"])
        else:
            # 将軍配置（即時実行に変更）
            result = self.game.internal_affairs.assign_governor(province, general)
            if result["success"]:
                self.game.add_message(f"{province.name}に{general.name}を配置しました")
                # 統計記録のみ実行（コマンド消費はしない）
                self.game.game_state.record_command(province.owner_daimyo_id, province.id, "assign_general")
            else:
                self.game.add_message(result.get("message", "配置に失敗しました"))
