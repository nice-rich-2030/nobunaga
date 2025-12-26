"""
MilitarySystem - 軍事システム
徴兵、訓練、移動、攻撃の管理
"""
from typing import Optional, List
from models.province import Province
from models.general import General
from models.army import Army
import config


class MilitarySystem:
    """軍事システムクラス"""

    def __init__(self, game_state):
        self.game_state = game_state

    def recruit_soldiers(self, province: Province, amount: int) -> dict:
        """兵士を徴兵（農民を兵士に変換）"""
        # コスト計算
        cost = amount * config.RECRUIT_COST_PER_SOLDIER

        # リソースチェック
        if not province.can_afford(gold=cost):
            return {"success": False, "message": "金が不足しています"}

        # 農民数チェック
        if province.peasants < amount:
            return {"success": False, "message": "農民が不足しています"}

        # 徴兵実行
        province.spend(gold=cost)
        province.add_peasants(-amount)
        province.add_soldiers(amount)

        # 忠誠度低下（徴兵は農民に不評）
        province.update_loyalty(-5)

        return {
            "success": True,
            "message": f"{amount}人の兵士を徴兵しました",
            "recruited": amount
        }

    def train_army(self, province: Province) -> dict:
        """軍を訓練（戦闘力向上）"""
        if not province.can_afford(gold=config.TRAINING_COST):
            return {"success": False, "message": "金が不足しています"}

        if province.soldiers <= 0:
            return {"success": False, "message": "訓練する兵士がいません"}

        # 訓練実行
        province.spend(gold=config.TRAINING_COST)
        old_training = province.soldier_training
        province.soldier_training = min(2.0, province.soldier_training * config.TRAINING_EFFECTIVENESS_BOOST)

        return {
            "success": True,
            "message": f"軍を訓練しました（訓練度: {old_training:.2f} → {province.soldier_training:.2f}）",
            "new_training": province.soldier_training
        }

    def transfer_troops(
        self,
        from_province: Province,
        to_province: Province,
        amount: int
    ) -> dict:
        """兵士を他の領地に移動"""
        # 同じ大名の領地かチェック
        if from_province.owner_daimyo_id != to_province.owner_daimyo_id:
            return {"success": False, "message": "自分の領地間でのみ移動できます"}

        # 兵士数チェック
        if from_province.soldiers < amount:
            return {"success": False, "message": "移動させる兵士が不足しています"}

        # 隣接チェック（簡略化：将来的には経路探索を実装）
        if to_province.id not in from_province.adjacent_provinces:
            return {"success": False, "message": "隣接する領地にのみ移動できます"}

        # 移動実行
        from_province.add_soldiers(-amount)
        to_province.add_soldiers(amount)

        return {
            "success": True,
            "message": f"{from_province.name}から{to_province.name}へ{amount}人を移動",
            "amount": amount
        }

    def create_attack_army(
        self,
        from_province: Province,
        target_province: Province,
        soldier_count: int,
        general_id: Optional[int] = None
    ) -> dict:
        """攻撃軍を編成"""
        # 兵士数チェック
        if from_province.soldiers < soldier_count:
            return {"success": False, "message": "兵士が不足しています"}

        # 隣接チェック
        if target_province.id not in from_province.adjacent_provinces:
            return {"success": False, "message": "隣接する領地のみ攻撃できます"}

        # 自分の領地はチェック
        if target_province.owner_daimyo_id == from_province.owner_daimyo_id:
            return {"success": False, "message": "自分の領地を攻撃できません"}

        # 武将の確認
        general = None
        if general_id:
            general = self.game_state.get_general(general_id)
            if not general or general.serving_daimyo_id != from_province.owner_daimyo_id:
                return {"success": False, "message": "指定された武将は使用できません"}

        # 軍を編成
        army = Army(
            army_id=self.game_state.next_army_id,
            daimyo_id=from_province.owner_daimyo_id,
            general_id=general_id,
            current_province_id=from_province.id
        )
        self.game_state.next_army_id += 1

        # 兵士を配置（簡略版：全て歩兵）
        army.set_troops(infantry=soldier_count)
        army.morale = from_province.soldier_morale

        # 米の補給（1兵士あたり10ターン分）
        rice_needed = soldier_count * config.SOLDIER_RICE_CONSUMPTION * 10
        if from_province.rice >= rice_needed:
            from_province.add_rice(-rice_needed)
            army.rice_supply = rice_needed
        else:
            # 米不足でも出陣可能だが士気低下
            army.rice_supply = from_province.rice
            from_province.rice = 0
            army.morale = max(30, army.morale - 20)

        # 出陣した兵士を領地から減らす
        from_province.add_soldiers(-soldier_count)

        # 軍を保存
        self.game_state.armies[army.id] = army

        return {
            "success": True,
            "message": f"{from_province.name}から{soldier_count}人が出陣",
            "army_id": army.id,
            "army": army
        }

    def get_province_military_power(self, province: Province) -> int:
        """領地の軍事力を計算"""
        return province.get_combat_power()

    def can_recruit(self, province: Province, amount: int) -> bool:
        """徴兵可能かチェック"""
        cost = amount * config.RECRUIT_COST_PER_SOLDIER
        return province.can_afford(gold=cost) and province.peasants >= amount

    def get_recruitment_cost(self, amount: int) -> int:
        """徴兵コストを計算"""
        return amount * config.RECRUIT_COST_PER_SOLDIER

    def get_max_recruitable(self, province: Province) -> int:
        """最大徴兵可能数を計算"""
        max_by_gold = province.gold // config.RECRUIT_COST_PER_SOLDIER
        max_by_peasants = province.peasants
        return min(max_by_gold, max_by_peasants)
