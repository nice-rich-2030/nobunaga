"""
CombatSystem - 戦闘システム
戦闘解決とダメージ計算
"""
import random
from typing import Optional, Dict, List
from models.province import Province
from models.army import Army
from models.general import General
import config


class BattleResult:
    """戦闘結果クラス"""

    def __init__(self):
        self.attacker_won = False
        self.attacker_casualties = 0
        self.defender_casualties = 0
        self.attacker_remaining = 0
        self.defender_remaining = 0
        self.province_captured = False
        self.battle_log: List[str] = []


class CombatSystem:
    """戦闘システムクラス"""

    def __init__(self, game_state):
        self.game_state = game_state

    def resolve_battle(
        self,
        attacker_army: Army,
        defender_province: Province
    ) -> BattleResult:
        """戦闘を解決（自動戦闘）"""
        result = BattleResult()

        # 攻撃側の戦力計算
        attacker_general = None
        if attacker_army.general_id:
            attacker_general = self.game_state.get_general(attacker_army.general_id)

        attacker_power = self._calculate_army_power(attacker_army, attacker_general)

        # 防御側の戦力計算
        defender_general = None
        if defender_province.governor_general_id:
            defender_general = self.game_state.get_general(defender_province.governor_general_id)

        defender_power = self._calculate_defender_power(defender_province, defender_general)

        # 戦闘ラウンド数（最大10ラウンド）
        max_rounds = 10
        attacker_troops = attacker_army.total_troops
        defender_troops = defender_province.soldiers

        for round_num in range(1, max_rounds + 1):
            # 双方のダメージ計算
            # damage_to_XXX = XXXが受けるダメージ
            damage_to_attacker = self._calculate_damage(defender_power, defender_troops, is_attacker=False)  # 守備側→攻撃側
            damage_to_defender = self._calculate_damage(attacker_power, attacker_troops, is_attacker=True)   # 攻撃側→守備側

            # 城防御ボーナス（守備側の攻撃力が増加）
            damage_to_attacker = int(damage_to_attacker * defender_province.get_defense_bonus())

            # ダメージ適用
            defender_casualties = min(damage_to_defender, defender_troops)
            attacker_casualties = min(damage_to_attacker, attacker_troops)

            defender_troops -= defender_casualties
            attacker_troops -= attacker_casualties

            # 勝敗判定
            if defender_troops <= 0:
                result.attacker_won = True
                break
            elif attacker_troops <= 0:
                result.attacker_won = False
                break

            # 士気による撤退判定
            if attacker_troops < attacker_army.total_troops * 0.3:
                if random.random() < 0.3:  # 30%の確率で撤退
                    result.attacker_won = False
                    break

        # 結果を記録
        result.attacker_casualties = attacker_army.total_troops - attacker_troops
        result.defender_casualties = defender_province.soldiers - defender_troops
        result.attacker_remaining = max(0, attacker_troops)
        result.defender_remaining = max(0, defender_troops)

        # 戦闘結果サマリー
        if result.attacker_won:
            result.battle_log.append(f"⚔ 攻撃軍が勝利！（損失{result.attacker_casualties}人、残存{result.attacker_remaining}人）")
            result.battle_log.append(f"   守備軍は壊滅（損失{result.defender_casualties}人）")
        else:
            result.battle_log.append(f"🛡 守備軍が勝利！（損失{result.defender_casualties}人、残存{result.defender_remaining}人）")
            result.battle_log.append(f"   攻撃軍は撤退（損失{result.attacker_casualties}人）")

        # 領地占領
        if result.attacker_won and defender_troops <= 0:
            result.province_captured = True
            result.battle_log.append(f"★ {defender_province.name}を占領！")

        return result

    def apply_battle_result(
        self,
        result: BattleResult,
        attacker_army: Army,
        defender_province: Province
    ) -> Optional[int]:
        """戦闘結果を適用

        Returns:
            defeated_daimyo_id: 討死した大名のID（Noneの場合は死亡なし）
        """
        # 守備側の兵士を更新
        defender_province.soldiers = result.defender_remaining

        # 攻撃側の軍を更新
        remaining_ratio = result.attacker_remaining / attacker_army.total_troops if attacker_army.total_troops > 0 else 0
        attacker_army.infantry = int(attacker_army.infantry * remaining_ratio)

        # 士気の更新
        if result.attacker_won:
            attacker_army.update_morale(config.MORALE_VICTORY_BOOST)
            defender_province.update_morale(config.MORALE_DEFEAT_PENALTY)
        else:
            attacker_army.update_morale(config.MORALE_DEFEAT_PENALTY)
            defender_province.update_morale(config.MORALE_VICTORY_BOOST)

        # 勝敗記録の更新
        self._update_battle_records(result, attacker_army, defender_province)

        # 領地占領処理
        defeated_daimyo_id = None
        if result.province_captured:
            defeated_daimyo_id = self._capture_province(attacker_army, defender_province)
        else:
            # 占領失敗時は元の領地に撤退
            self._retreat_to_home(attacker_army)

        return defeated_daimyo_id

    def _capture_province(self, attacker_army: Army, province: Province) -> Optional[int]:
        """領地を占領

        Returns:
            defeated_daimyo_id: 討死した大名のID（Noneの場合は死亡なし）
        """
        old_owner = province.owner_daimyo_id
        new_owner = attacker_army.daimyo_id
        defeated_daimyo_id = None

        # 守将を討ち取る
        if province.governor_general_id:
            general_id = province.governor_general_id

            # 大名ID範囲かチェック
            if config.DAIMYO_ID_MIN <= general_id <= config.DAIMYO_ID_MAX:
                # 大名を死亡させる
                daimyo = self.game_state.get_daimyo(general_id)
                if daimyo:
                    daimyo.is_alive = False
                    defeated_daimyo_id = general_id
                    print(f"[Combat] 大名 {daimyo.clan_name} {daimyo.name} が討死")
            elif config.GENERAL_ID_MIN <= general_id <= config.GENERAL_ID_MAX:
                # 将軍を討ち取る（敗北した将軍は殺される）
                if general_id in self.game_state.generals:
                    del self.game_state.generals[general_id]
            else:
                print(f"[Combat] Warning: Invalid general_id {general_id} found in governor_general_id")

            province.governor_general_id = None

        # 旧所有者から削除
        if old_owner:
            old_daimyo = self.game_state.get_daimyo(old_owner)
            if old_daimyo:
                old_daimyo.remove_province(province.id)

        # 新所有者に追加
        new_daimyo = self.game_state.get_daimyo(new_owner)
        if new_daimyo:
            new_daimyo.add_province(province.id)

        # 領地の所有者を変更
        province.owner_daimyo_id = new_owner

        # 占領軍を駐留
        province.soldiers = attacker_army.total_troops
        province.soldier_morale = attacker_army.morale

        # 忠誠度低下（占領されたため）
        province.peasant_loyalty = max(20, province.peasant_loyalty - 30)

        # 攻撃側の将軍を占領した領地の守将として配属
        if attacker_army.general_id:
            attacker_general = self.game_state.get_general(attacker_army.general_id)
            if attacker_general:
                # 元の領地から解除
                old_province_id = attacker_general.current_province_id
                if old_province_id:
                    old_province = self.game_state.get_province(old_province_id)
                    if old_province and old_province.governor_general_id == attacker_army.general_id:
                        old_province.governor_general_id = None

                # 占領した領地に配属
                province.governor_general_id = attacker_army.general_id
                attacker_general.assign_to_province(province.id)

        # 軍を解散（領地に駐留）
        if attacker_army.id in self.game_state.armies:
            del self.game_state.armies[attacker_army.id]

        return defeated_daimyo_id

    def _update_battle_records(self, result: BattleResult, attacker_army: Army, defender_province: Province):
        """勝敗記録を更新"""
        # 攻撃側の将軍・大名の記録を更新
        if attacker_army.general_id:
            attacker_general = self.game_state.get_general(attacker_army.general_id)
            if attacker_general:
                if result.attacker_won:
                    attacker_general.battle_wins += 1
                else:
                    attacker_general.battle_losses += 1

        # 攻撃側大名の記録を更新
        attacker_daimyo = self.game_state.get_daimyo(attacker_army.daimyo_id)
        if attacker_daimyo:
            if result.attacker_won:
                attacker_daimyo.battle_wins += 1
            else:
                attacker_daimyo.battle_losses += 1

        # 防御側の守将・大名の記録を更新
        if defender_province.governor_general_id:
            defender_general = self.game_state.get_general(defender_province.governor_general_id)
            if defender_general:
                if result.attacker_won:
                    defender_general.battle_losses += 1
                else:
                    defender_general.battle_wins += 1

        # 防御側大名の記録を更新
        defender_daimyo = self.game_state.get_daimyo(defender_province.owner_daimyo_id)
        if defender_daimyo:
            if result.attacker_won:
                defender_daimyo.battle_losses += 1
            else:
                defender_daimyo.battle_wins += 1

    def _retreat_to_home(self, attacker_army: Army):
        """攻撃失敗時に元の領地に撤退"""
        # 出陣元の領地を取得
        home_province = self.game_state.get_province(attacker_army.current_province_id)
        if not home_province:
            # 領地が存在しない場合（占領されている可能性）、軍を解散
            if attacker_army.id in self.game_state.armies:
                del self.game_state.armies[attacker_army.id]
            return

        # 生き残った兵士を元の領地に戻す
        home_province.add_soldiers(attacker_army.total_troops)

        # 戦闘後の士気を元の領地に反映
        # 元の領地の兵士と撤退した兵士の加重平均を取る
        total_soldiers = home_province.soldiers
        if total_soldiers > 0:
            # 撤退した兵士の士気を反映
            home_province.soldier_morale = int(
                (home_province.soldier_morale * (total_soldiers - attacker_army.total_troops) +
                 attacker_army.morale * attacker_army.total_troops) / total_soldiers
            )

        # 軍を解散
        if attacker_army.id in self.game_state.armies:
            del self.game_state.armies[attacker_army.id]

    def _calculate_army_power(self, army: Army, general: Optional[General]) -> int:
        """軍の戦力を計算"""
        general_bonus = 1.0
        if general:
            general_bonus = general.get_combat_bonus()

        base_power = army.calculate_combat_power(general_bonus)

        # 攻撃側ペナルティ（遠征による士気低下）
        # 攻撃側は城壁がなく、補給線が伸びているため戦力が0.8倍になる
        expedition_penalty = 0.8
        base_power = int(base_power * expedition_penalty)

        return base_power

    def _calculate_defender_power(self, province: Province, general: Optional[General]) -> int:
        """防御側の戦力を計算"""
        base_power = province.get_combat_power()

        # 武将ボーナス
        if general:
            base_power = int(base_power * general.get_combat_bonus())

        return base_power

    def _calculate_damage(self, power: int, troop_count: int, is_attacker: bool = True) -> int:
        """ダメージを計算

        Args:
            power: 戦力
            troop_count: 相手の兵力
            is_attacker: 攻撃側かどうか（True=攻撃側、False=防御側）
        """
        # 攻撃側と防御側でダメージ範囲を変える
        if is_attacker:
            # 攻撃側: 13-21%
            damage_ratio = 0.13 + random.random() * 0.09
        else:
            # 防御側: 10-17%
            damage_ratio = 0.10 + random.random() * 0.07

        damage = int(power * damage_ratio)

        # 最低1、最大でも相手の兵力まで
        return max(1, min(damage, troop_count))

    def predict_battle_outcome(
        self,
        attacker_army: Army,
        defender_province: Province
    ) -> dict:
        """戦闘の予測結果を返す（実際には実行しない）"""
        attacker_general = None
        if attacker_army.general_id:
            attacker_general = self.game_state.get_general(attacker_army.general_id)

        defender_general = None
        if defender_province.governor_general_id:
            defender_general = self.game_state.get_general(defender_province.governor_general_id)

        attacker_power = self._calculate_army_power(attacker_army, attacker_general)
        defender_power = self._calculate_defender_power(defender_province, defender_general)

        # 防御ボーナスを考慮
        defender_power = int(defender_power * defender_province.get_defense_bonus())

        # 勝率計算（簡易版）
        total_power = attacker_power + defender_power
        if total_power > 0:
            win_probability = attacker_power / total_power
        else:
            win_probability = 0.5

        return {
            "attacker_power": attacker_power,
            "defender_power": defender_power,
            "win_probability": win_probability,
            "recommendation": "攻撃推奨" if win_probability > 0.6 else "慎重に" if win_probability > 0.4 else "撤退推奨"
        }
