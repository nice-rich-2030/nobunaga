"""
GameState - ゲーム状態管理
全ての領地、大名、武将、軍隊を管理
"""
import json
from typing import Dict, List, Optional
from models.province import Province
from models.daimyo import Daimyo
from models.general import General
from models.army import Army
from models.diplomacy import DiplomaticRelation
import config


class GameState:
    """ゲーム状態を管理するメインクラス"""

    def __init__(self):
        # ========================================
        # ゲームエンティティ
        # ========================================
        self.provinces: Dict[int, Province] = {}
        self.daimyo: Dict[int, Daimyo] = {}
        self.generals: Dict[int, General] = {}
        self.armies: Dict[int, Army] = {}
        self.diplomatic_relations: List[DiplomaticRelation] = []

        # ========================================
        # ゲーム進行
        # ========================================
        self.current_turn = 0
        self.current_season = config.SEASON_SPRING  # 0=春, 1=夏, 2=秋, 3=冬

        # ========================================
        # プレイヤー
        # ========================================
        self.player_daimyo_id: Optional[int] = None

        # ========================================
        # ID カウンター
        # ========================================
        self.next_army_id = 1

        # ========================================
        # 将軍プール
        # ========================================
        self.general_pool = None  # 後で初期化

    def load_game_data(self):
        """JSONファイルからゲームデータを読み込む"""
        # Windowsのコンソール出力問題を回避
        try:
            print("ゲームデータを読み込んでいます...")
        except:
            pass

        # 領地データの読み込み
        self._load_provinces()

        # 大名データの読み込み
        self._load_daimyo()

        # 武将データの読み込み
        self._load_generals()

        # 外交関係の初期化
        self._initialize_diplomacy()

        # 将軍プールの初期化
        from systems.general_pool import GeneralPool
        self.general_pool = GeneralPool(self)
        self.general_pool.initialize()

        try:
            print(f"読み込み完了: {len(self.provinces)}領地, {len(self.daimyo)}大名, {len(self.generals)}武将")
        except:
            pass

    def _load_provinces(self):
        """領地データを読み込む"""
        with open(config.PROVINCES_DATA, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for province_data in data["provinces"]:
            province = Province(
                province_id=province_data["id"],
                name=province_data["name"],
                position=tuple(province_data["position"]),
                terrain_type=province_data.get("terrain", config.TERRAIN_PLAINS),
                max_peasants=province_data.get("max_peasants", 8000)
            )
            province.adjacent_provinces = province_data.get("adjacent", [])
            province.has_castle = province_data.get("has_castle", True)

            self.provinces[province.id] = province

    def _load_daimyo(self):
        """大名データを読み込み、領地を割り当てる"""
        with open(config.DAIMYO_DATA, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for i, daimyo_data in enumerate(data["daimyo"]):
            daimyo = Daimyo(
                daimyo_id=daimyo_data["id"],
                name=daimyo_data["name"],
                clan_name=daimyo_data["clan"],
                is_player=(i == 0)  # 最初の大名をプレイヤーとする
            )

            # 能力値を設定
            daimyo.age = daimyo_data.get("age", 30)
            daimyo.health = daimyo_data.get("health", 90)
            daimyo.ambition = daimyo_data.get("ambition", 70)
            daimyo.luck = daimyo_data.get("luck", 50)
            daimyo.charm = daimyo_data.get("charm", 60)
            daimyo.intelligence = daimyo_data.get("intelligence", 70)
            daimyo.war_skill = daimyo_data.get("war_skill", 60)

            # 開始領地を設定
            starting_province_id = daimyo_data.get("starting_province")
            if starting_province_id and starting_province_id in self.provinces:
                province = self.provinces[starting_province_id]
                province.owner_daimyo_id = daimyo.id
                daimyo.add_province(starting_province_id)
                daimyo.capital_province_id = starting_province_id

            self.daimyo[daimyo.id] = daimyo

            if daimyo.is_player:
                self.player_daimyo_id = daimyo.id

    def _load_generals(self):
        """武将データを読み込み、大名に配属"""
        with open(config.GENERALS_DATA, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for general_data in data["generals"]:
            general = General(
                general_id=general_data["id"],
                name=general_data["name"],
                serving_daimyo_id=general_data.get("starting_daimyo")
            )

            # 能力値を設定
            general.age = general_data.get("age", 25)
            general.war_skill = general_data.get("war_skill", 60)
            general.leadership = general_data.get("leadership", 60)
            general.politics = general_data.get("politics", 50)
            general.intelligence = general_data.get("intelligence", 50)

            self.generals[general.id] = general

    def _initialize_diplomacy(self):
        """大名間の外交関係を初期化"""
        daimyo_ids = list(self.daimyo.keys())

        for i, daimyo_a_id in enumerate(daimyo_ids):
            for daimyo_b_id in daimyo_ids[i + 1:]:
                relation = DiplomaticRelation(daimyo_a_id, daimyo_b_id)
                # 初期関係値はランダムまたは中立
                relation.set_relation(0)
                self.diplomatic_relations.append(relation)

    def get_province(self, province_id: int) -> Optional[Province]:
        """IDで領地を取得"""
        return self.provinces.get(province_id)

    def get_daimyo(self, daimyo_id: int) -> Optional[Daimyo]:
        """IDで大名を取得"""
        return self.daimyo.get(daimyo_id)

    def get_general(self, general_id: int) -> Optional[General]:
        """IDで武将を取得"""
        return self.generals.get(general_id)

    def get_player_daimyo(self) -> Optional[Daimyo]:
        """プレイヤー大名を取得"""
        if self.player_daimyo_id:
            return self.daimyo.get(self.player_daimyo_id)
        return None

    def get_player_provinces(self) -> List[Province]:
        """プレイヤーの領地リストを取得"""
        if not self.player_daimyo_id:
            return []

        return [
            province for province in self.provinces.values()
            if province.owner_daimyo_id == self.player_daimyo_id
        ]

    def get_daimyo_provinces(self, daimyo_id: int) -> List[Province]:
        """特定の大名の領地リストを取得"""
        return [
            province for province in self.provinces.values()
            if province.owner_daimyo_id == daimyo_id
        ]

    def get_diplomatic_relation(self, daimyo_a_id: int, daimyo_b_id: int) -> Optional[DiplomaticRelation]:
        """2つの大名間の外交関係を取得"""
        for relation in self.diplomatic_relations:
            if ((relation.daimyo_a_id == daimyo_a_id and relation.daimyo_b_id == daimyo_b_id) or
                    (relation.daimyo_a_id == daimyo_b_id and relation.daimyo_b_id == daimyo_a_id)):
                return relation
        return None

    def get_season_name(self) -> str:
        """現在の季節名を取得"""
        return config.SEASONS[self.current_season]

    def get_year(self) -> int:
        """現在の年を計算（1560年スタート）"""
        return 1560 + (self.current_turn // 4)

    def advance_turn(self):
        """ターンを進める"""
        self.current_turn += 1
        self.current_season = (self.current_season + 1) % 4

    def check_victory_conditions(self) -> Optional[int]:
        """勝利条件をチェック（勝者のdaimyo_idを返す、なければNone）"""
        alive_daimyo = [d for d in self.daimyo.values() if d.is_alive and len(d.controlled_provinces) > 0]

        # すべての領地を支配
        for daimyo in alive_daimyo:
            if len(daimyo.controlled_provinces) == len(self.provinces):
                return daimyo.id

        # 他のすべてのライバルを排除
        if len(alive_daimyo) == 1:
            return alive_daimyo[0].id

        return None

    def update_all_statistics(self):
        """全大名の統計を更新"""
        for daimyo in self.daimyo.values():
            provinces = self.get_daimyo_provinces(daimyo.id)
            daimyo.update_statistics(provinces)

    def __repr__(self) -> str:
        return f"GameState(Turn: {self.current_turn}, Season: {self.get_season_name()}, Year: {self.get_year()})"
