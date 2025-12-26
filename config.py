"""
ゲーム設定と定数の定義
"""
import os

# ========================================
# 画面設定
# ========================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 30
WINDOW_TITLE = "信長の野望 - Nobunaga's Ambition"

# ========================================
# 色定義
# ========================================
# 基本色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)

# 大名色（プレイヤーとAI）
PLAYER_COLOR = (50, 100, 200)  # 青
AI_COLOR_1 = (200, 50, 50)     # 赤
AI_COLOR_2 = (50, 200, 50)     # 緑
AI_COLOR_3 = (200, 200, 50)    # 黄
AI_COLOR_4 = (150, 50, 200)    # 紫
AI_COLOR_5 = (200, 100, 50)    # オレンジ
NEUTRAL_COLOR = (180, 180, 180)  # 中立（所有者なし）

DAIMYO_COLORS = [
    PLAYER_COLOR,
    AI_COLOR_1,
    AI_COLOR_2,
    AI_COLOR_3,
    AI_COLOR_4,
    AI_COLOR_5
]

# UI色
UI_BG_COLOR = (60, 40, 20)           # ダークブラウン（木の背景）
UI_PANEL_COLOR = (80, 60, 40)        # パネル背景
UI_BORDER_COLOR = (200, 180, 100)    # ゴールド枠
UI_TEXT_COLOR = WHITE
UI_HIGHLIGHT_COLOR = (255, 215, 0)   # ゴールド（ハイライト）

# ステータス色
STATUS_GOOD = (50, 200, 50)      # 緑
STATUS_POSITIVE = (50, 200, 50)  # 緑（同義語）
STATUS_NEUTRAL = (200, 200, 50)  # 黄
STATUS_BAD = (200, 50, 50)       # 赤
STATUS_NEGATIVE = (200, 50, 50)  # 赤（同義語）

# ========================================
# ファイルパス
# ========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
GRAPHICS_DIR = os.path.join(BASE_DIR, "graphics")
SPRITES_DIR = os.path.join(GRAPHICS_DIR, "sprites")
BG_DIR = os.path.join(GRAPHICS_DIR, "backgrounds")
UI_DIR = os.path.join(GRAPHICS_DIR, "ui")

# データファイル
PROVINCES_DATA = os.path.join(DATA_DIR, "provinces.json")
DAIMYO_DATA = os.path.join(DATA_DIR, "daimyo.json")
GENERALS_DATA = os.path.join(DATA_DIR, "generals.json")
EVENTS_DATA = os.path.join(DATA_DIR, "events.json")
SCENARIOS_DATA = os.path.join(DATA_DIR, "scenarios.json")

# ========================================
# ゲームバランス定数 - 経済
# ========================================
# 米生産
BASE_RICE_PRODUCTION = 100  # 開発レベルごとの基本米生産
RICE_PRODUCTION_MULTIPLIER = 1.0  # 地形による乗数

# 税収
BASE_TAX_INCOME = 50  # 町レベルごとの基本税収
TAX_RATE_DEFAULT = 50  # デフォルト税率 (%)
TAX_RATE_MIN = 10
TAX_RATE_MAX = 90

# 内政コスト
CULTIVATION_COST = 200  # 金
CULTIVATION_BOOST = 1.3  # 30%生産増加
CULTIVATION_LOYALTY_PENALTY = -15

TOWN_DEVELOPMENT_COST = 300  # 金
TOWN_DEVELOPMENT_BOOST = 1  # +1レベル

FLOOD_CONTROL_COST = 150  # 金
FLOOD_CONTROL_BOOST = 20  # +20%

GIVE_RICE_AMOUNT = 100  # 米
GIVE_RICE_LOYALTY_BOOST = 10

# ========================================
# ゲームバランス定数 - 軍事
# ========================================
# 徴兵
RECRUIT_COST_PER_SOLDIER = 2  # 金/兵士
RECRUIT_PEASANT_RATIO = 1  # 1農民 = 1兵士
SOLDIER_RICE_CONSUMPTION = 1  # 米/兵士/ターン

# 訓練
TRAINING_COST = 150  # 金
TRAINING_EFFECTIVENESS_BOOST = 1.2  # 20%戦闘力向上

# 戦闘
BASE_DAMAGE = 10  # 100兵士あたりのベースダメージ
FLANKING_BONUS = 1.5  # 側面攻撃ボーナス
PINCER_BONUS = 2.0  # 挟撃ボーナス
CASTLE_DEFENSE_BONUS = 1.2  # 城防御ボーナス 1+50*(BONUS-1)/100
MORALE_COMBAT_MODIFIER = 0.02  # 士気50以上で1ポイントあたり2%ボーナス
GENERAL_SKILL_MODIFIER = 0.01  # 武将戦闘スキル1ポイントあたり1%ボーナス

# ========================================
# ゲームバランス定数 - 忠誠度と士気
# ========================================
LOYALTY_DECAY_RATE = -2  # ターンごとの自然減衰
LOYALTY_RECOVERY_RATE = 5  # 米配布時の回復
LOYALTY_TAX_PENALTY = -0.5  # 税率1%あたりのペナルティ
REVOLT_THRESHOLD = 20  # この値以下で反乱リスク
HIGH_LOYALTY_THRESHOLD = 80
HIGH_LOYALTY_BONUS = 1.1  # 10%生産ボーナス

MORALE_DECAY_RATE = -1  # ターンごとの自然減衰
MORALE_VICTORY_BOOST = 10
MORALE_DEFEAT_PENALTY = -20
MORALE_LOW_RICE_PENALTY = -10  # 米不足時

# ========================================
# ゲームバランス定数 - 外交
# ========================================
GIFT_RELATION_BOOST = 10
GIFT_GOLD_AMOUNT = 500

WAR_RELATION_PENALTY = -30
ALLIANCE_RELATION_THRESHOLD = 50
NON_AGGRESSION_RELATION_THRESHOLD = 20
BETRAYAL_PENALTY = -50

TREATY_DURATION_TURNS = 8  # 2年（季節4つ × 2）

# ========================================
# ゲームバランス定数 - イベント
# ========================================
FLOOD_PROBABILITY = 0.05  # 5%
FLOOD_RICE_PENALTY = -0.3  # 30%減少
FLOOD_PEASANT_LOSS = 100
FLOOD_LOYALTY_PENALTY = -10

GOOD_HARVEST_PROBABILITY = 0.10  # 10%
GOOD_HARVEST_RICE_BOOST = 0.5  # 50%増加

EPIDEMIC_PROBABILITY = 0.03  # 3%
EPIDEMIC_PEASANT_LOSS = 200
EPIDEMIC_SOLDIER_LOSS = 50

# ========================================
# ゲームプレイ定数
# ========================================
# 季節
SEASONS = ["春", "夏", "秋", "冬"]
SEASON_SPRING = 0
SEASON_SUMMER = 1
SEASON_FALL = 2
SEASON_WINTER = 3

# 地形タイプ
TERRAIN_PLAINS = "plains"
TERRAIN_MOUNTAINS = "mountains"
TERRAIN_FOREST = "forest"
TERRAIN_COASTAL = "coastal"

# 地形効果
TERRAIN_EFFECTS = {
    TERRAIN_PLAINS: {
        "rice_multiplier": 1.2,
        "defense_bonus": 1.0
    },
    TERRAIN_MOUNTAINS: {
        "rice_multiplier": 0.7,
        "defense_bonus": 1.5
    },
    TERRAIN_FOREST: {
        "rice_multiplier": 0.9,
        "defense_bonus": 1.2
    },
    TERRAIN_COASTAL: {
        "rice_multiplier": 1.0,
        "defense_bonus": 1.1
    }
}

# 勝利条件
VICTORY_CONTROL_ALL = "all_provinces"
VICTORY_CONTROL_MAJORITY = "majority_provinces"  # 75%
VICTORY_ELIMINATE_RIVALS = "eliminate_all"
VICTORY_TURN_LIMIT = 100  # 25年

MAJORITY_THRESHOLD = 0.75  # 75%
MAJORITY_DURATION = 4  # 4ターン（1年）連続

# ========================================
# UI定数
# ========================================
# フォントサイズ
FONT_SIZE_LARGE = 24
FONT_SIZE_MEDIUM = 18
FONT_SIZE_SMALL = 14

# マージンとパディング
UI_MARGIN = 10
UI_PADDING = 5

# ボタンサイズ
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 150

# パネルサイズ
SIDE_PANEL_WIDTH = 300
BOTTOM_PANEL_HEIGHT = 60

# ========================================
# デバッグ設定
# ========================================
DEBUG_MODE = True
SHOW_FPS = True
