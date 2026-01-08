"""
アニメーション管理モジュール

戦闘アニメーション、大名死亡演出などのアニメーション管理を担当するクラス
"""
import config


class AnimationManager:
    """アニメーション管理を担当するクラス"""

    def __init__(self, game_instance):
        """初期化

        Args:
            game_instance: Gameクラスのインスタンス
        """
        self.game = game_instance

    def show_next_battle(self):
        """次の戦闘演出を表示"""
        if self.game.current_battle_index < len(self.game.pending_battle_animations):
            battle_data = self.game.pending_battle_animations[self.game.current_battle_index]
            self.game.current_battle_index += 1

            # まず戦闘プレビューを表示
            preview_data = {
                "attacker_province_id": battle_data["origin_province_id"],
                "defender_province_id": battle_data["target_province_id"],
                "attacker_name": battle_data["attacker_name"],
                "defender_name": battle_data["defender_name"]
            }
            self.game.battle_preview.show(preview_data, on_finish=lambda: self.show_battle_animation(battle_data))
        else:
            # すべての戦闘演出が終了
            self.game.pending_battle_animations.clear()

            # 全戦闘終了後に領地喪失による死亡チェック
            self.check_territory_loss_deaths()

            # デバッグログ出力（すべての戦闘結果が反映された後）
            if self.game.need_log_turn_state:
                self.game.log_turn_state()
                self.game.need_log_turn_state = False

            # 大名死亡演出があれば開始
            if self.game.turn_manager.pending_daimyo_deaths:
                self.game.pending_daimyo_death_animations = self.game.turn_manager.pending_daimyo_deaths.copy()
                self.game.turn_manager.pending_daimyo_deaths.clear()
                self.game.current_death_index = 0
                self.show_next_daimyo_death()
            else:
                # 死亡演出もなければメッセージ表示
                self.flush_turn_messages()

                # 勝利メッセージを表示
                if self.game.pending_winner_message:
                    self.game.add_message(self.game.pending_winner_message)
                    self.game.pending_winner_message = None

    def show_battle_animation(self, battle_data):
        """戦闘アニメーション画面を表示（プレビュー後）"""
        self.game.battle_animation.show(battle_data, on_finish=self.on_battle_animation_finished)

    def on_battle_animation_finished(self):
        """戦闘演出が終了したときのコールバック"""
        # 今終わった戦闘の結果を処理
        if self.game.current_battle_index > 0:
            battle_data = self.game.pending_battle_animations[self.game.current_battle_index - 1]

            # 1. 戦闘結果を適用（演出後に初めて領地所有権を変更）
            if "combat_system" in battle_data and "army" in battle_data:
                combat_system = battle_data["combat_system"]
                army = battle_data["army"]
                target_province = self.game.game_state.get_province(battle_data["target_province_id"])
                result = battle_data["result"]

                if target_province:
                    # 結果を適用（大名が討死した場合、defeated_daimyo_idが返る）
                    defeated_daimyo_id = combat_system.apply_battle_result(result, army, target_province)

                    # 大名が討死した場合、演出キューに追加
                    if defeated_daimyo_id:
                        defeated_daimyo = self.game.game_state.get_daimyo(defeated_daimyo_id)
                        if defeated_daimyo:
                            self.game.turn_manager.pending_daimyo_deaths.append({
                                "daimyo_id": defeated_daimyo.id,
                                "daimyo_name": defeated_daimyo.name,
                                "clan_name": defeated_daimyo.clan_name,
                                "age": defeated_daimyo.age,
                                "is_player": defeated_daimyo.is_player,
                                "cause": "battle_defeat"
                            })

                    # 敗北した軍は撤退（削除）
                    if not result.attacker_won and army.id in self.game.game_state.armies:
                        origin_province = self.game.game_state.get_province(battle_data["origin_province_id"])
                        if origin_province and army.total_troops > 0:
                            origin_province.add_soldiers(army.total_troops)
                        del self.game.game_state.armies[army.id]

            # 2. 勢力図の反映（領地変更があればハイライト）
            if battle_data.get("result") and battle_data["result"].province_captured:
                # 戦闘音再生
                self.game.sound_manager.play("battle")

                # 占領された領地をハイライト
                defender_province_name = battle_data["defender_province"]
                for province in self.game.game_state.provinces.values():
                    if province.name == defender_province_name:
                        self.game.power_map.set_highlight(province.id)
                        break

            # 3. この戦闘のメッセージを表示
            if "messages" in battle_data:
                for message in battle_data["messages"]:
                    self.game.add_message(message)

        # 4. 次の戦闘があれば表示、なければ残りのメッセージを表示
        self.show_next_battle()

    def flush_turn_messages(self):
        """保留中のターンメッセージをすべて表示"""
        for event in self.game.pending_turn_messages:
            self.game.add_message(event)
        self.game.pending_turn_messages.clear()

    def show_next_daimyo_death(self):
        """次の大名死亡演出を表示"""
        if self.game.current_death_index < len(self.game.pending_daimyo_death_animations):
            death_data = self.game.pending_daimyo_death_animations[self.game.current_death_index]
            self.game.current_death_index += 1

            # 演出開始
            self.game.daimyo_death_screen.show(
                death_data,
                on_finish=self.on_daimyo_death_finished,
                on_play=self.game.restart_game,
                on_end=self.game.quit
            )
        else:
            # 全死亡演出終了
            self.game.pending_daimyo_death_animations.clear()
            self.flush_turn_messages()
            if self.game.pending_winner_message:
                self.game.add_message(self.game.pending_winner_message)
                self.game.pending_winner_message = None

    def on_daimyo_death_finished(self):
        """死亡演出終了時のコールバック"""
        # 最後に表示した死亡データを取得
        death_data = self.game.pending_daimyo_death_animations[self.game.current_death_index - 1]

        # 領地を回収（中立化）
        self.handle_daimyo_death(death_data["daimyo_id"])

        # 次の死亡演出へ
        self.show_next_daimyo_death()

    def check_territory_loss_deaths(self):
        """領地喪失による死亡チェック"""
        for daimyo in self.game.game_state.daimyo.values():
            # 既に死亡している、または領地を持っている場合はスキップ
            if not daimyo.is_alive or len(daimyo.controlled_provinces) > 0:
                continue

            # 全領地を失った大名は死亡
            daimyo.is_alive = False

            # 死亡演出キューに追加
            self.game.turn_manager.pending_daimyo_deaths.append({
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
        daimyo = self.game.game_state.get_daimyo(daimyo_id)
        if not daimyo:
            return

        # 全領地を中立化
        for province_id in list(daimyo.controlled_provinces):
            province = self.game.game_state.get_province(province_id)
            if province:
                province.owner_daimyo_id = None
                province.governor_general_id = None
                daimyo.remove_province(province_id)

        # 配下の将軍を浪人化
        for general in list(self.game.game_state.generals.values()):
            if general.serving_daimyo_id == daimyo_id:
                general.serving_daimyo_id = None
                general.unassign()
