"""
GeneralPool - 浪人将軍管理システム
未所属の将軍を管理し、登用イベントを提供
"""
import random
from typing import List, Optional
from models.general import General


class GeneralPool:
    """浪人将軍プール管理クラス"""

    def __init__(self, game_state):
        self.game_state = game_state
        self.available_generals: List[int] = []  # 浪人の将軍ID

    def initialize(self):
        """初期化: 全将軍を浪人プールに追加"""
        for general_id, general in self.game_state.generals.items():
            if general.serving_daimyo_id is None:
                self.available_generals.append(general_id)

    def get_available_generals(self) -> List[General]:
        """登用可能な浪人将軍のリストを取得"""
        return [
            self.game_state.generals[gid]
            for gid in self.available_generals
            if gid in self.game_state.generals
        ]

    def get_random_general(self) -> Optional[General]:
        """ランダムに浪人将軍を1人選択"""
        available = self.get_available_generals()
        if not available:
            return None
        return random.choice(available)

    def recruit_general(self, general_id: int, daimyo_id: int) -> bool:
        """将軍を登用"""
        if general_id not in self.available_generals:
            return False

        general = self.game_state.generals.get(general_id)
        if not general:
            return False

        # 浪人プールから削除
        self.available_generals.remove(general_id)

        # 大名に仕える
        general.serving_daimyo_id = daimyo_id
        general.loyalty_to_daimyo = 60  # 初期忠誠度

        return True

    def return_to_pool(self, general_id: int):
        """将軍を浪人プールに戻す（主君が滅亡した場合など）"""
        if general_id in self.game_state.generals:
            general = self.game_state.generals[general_id]
            general.serving_daimyo_id = None
            general.unassign()

            if general_id not in self.available_generals:
                self.available_generals.append(general_id)

    def calculate_recruitment_cost(self, general: General) -> int:
        """登用費用を計算（100-300金）"""
        # 将軍の総合能力値（4つの平均）
        avg_skill = (
            general.war_skill +
            general.leadership +
            general.politics +
            general.intelligence
        ) / 4

        # 能力値に応じて100-300金
        # 能力40以下: 100金
        # 能力70: 200金
        # 能力100: 300金
        if avg_skill <= 40:
            return 100
        elif avg_skill >= 85:
            return 300
        else:
            # 線形補間
            return int(100 + (avg_skill - 40) / 45 * 200)
