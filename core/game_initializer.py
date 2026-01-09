"""
ゲーム初期化モジュール

ゲームシステムの初期化とUIコンポーネントの作成を担当
"""
import os
import pygame
import config
from core.game_state import GameState
from core.sequential_turn_manager import SequentialTurnManager
from systems.economy import EconomySystem
from systems.internal_affairs import InternalAffairsSystem
from systems.military import MilitarySystem
from systems.combat import CombatSystem
from systems.diplomacy import DiplomacySystem
from systems.ai import AISystem
from systems.events import EventSystem
from systems.transfer_system import TransferSystem
from ui.widgets import Button
from ui.event_dialog import EventDialog
from ui.event_history_screen import EventHistoryScreen
from ui.battle_animation import BattleAnimationScreen
from ui.battle_preview import BattlePreviewScreen
from ui.power_map import PowerMap
from ui.transfer_dialog import TransferDialog
from ui.general_assign_dialog import GeneralAssignDialog
from ui.daimyo_death_screen import DaimyoDeathScreen
from utils.image_manager import ImageManager
from utils.sound_manager import SoundManager
from utils.bgm_manager import BGMManager


def initialize_pygame():
    """Pygameの初期化と画面・フォント設定

    Returns:
        tuple: (screen, clock, font_large, font_medium, font_small)
    """
    pygame.init()

    # 画面の設定
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption(config.WINDOW_TITLE)

    # クロックの設定
    clock = pygame.time.Clock()

    # フォントの設定（日本語対応）
    try:
        font_large = pygame.font.SysFont('meiryo', config.FONT_SIZE_LARGE)
        font_medium = pygame.font.SysFont('meiryo', config.FONT_SIZE_MEDIUM)
        font_small = pygame.font.SysFont('meiryo', config.FONT_SIZE_SMALL)
    except:
        font_large = pygame.font.Font(None, config.FONT_SIZE_LARGE)
        font_medium = pygame.font.Font(None, config.FONT_SIZE_MEDIUM)
        font_small = pygame.font.Font(None, config.FONT_SIZE_SMALL)

    return screen, clock, font_large, font_medium, font_small


def initialize_managers():
    """リソースマネージャーの初期化

    Returns:
        tuple: (image_manager, sound_manager, bgm_manager)
    """
    assets_path = os.path.join(config.BASE_DIR, "assets")

    # 画像管理の初期化
    image_manager = ImageManager(assets_path)
    image_manager.preload_all_portraits()

    # 音声管理の初期化
    sound_manager = SoundManager(assets_path)
    sound_manager.preload_all_sounds()

    # BGM管理の初期化
    bgm_manager = BGMManager()

    return image_manager, sound_manager, bgm_manager


def initialize_game_systems():
    """ゲームシステムの初期化

    Returns:
        dict: 各種ゲームシステムを含む辞書
            - game_state: GameState
            - economy_system: EconomySystem
            - internal_affairs: InternalAffairsSystem
            - turn_manager: SequentialTurnManager
            - military_system: MilitarySystem
            - combat_system: CombatSystem
            - diplomacy_system: DiplomacySystem
            - transfer_system: TransferSystem
            - ai_system: AISystem
            - event_system: EventSystem
    """
    # ゲーム状態の初期化
    game_state = GameState()
    game_state.load_game_data()

    # 基本システムの初期化
    economy_system = EconomySystem(game_state)
    internal_affairs = InternalAffairsSystem(game_state)
    turn_manager = SequentialTurnManager(game_state)

    # 軍事・戦闘・外交システム
    military_system = MilitarySystem(game_state)
    combat_system = CombatSystem(game_state)
    diplomacy_system = DiplomacySystem(game_state)
    transfer_system = TransferSystem(game_state)

    # AIシステム
    ai_system = AISystem(
        game_state,
        internal_affairs,
        military_system,
        diplomacy_system,
        transfer_system
    )

    # イベントシステム
    event_system = EventSystem(game_state)
    event_system.load_events_from_file(config.EVENTS_DATA)
    event_system.general_pool = game_state.general_pool

    # SequentialTurnManagerにシステムを設定
    turn_manager.ai_system = ai_system
    turn_manager.diplomacy_system = diplomacy_system
    turn_manager.event_system = event_system
    turn_manager.internal_affairs = internal_affairs
    turn_manager.military_system = military_system
    turn_manager.transfer_system = transfer_system

    return {
        'game_state': game_state,
        'economy_system': economy_system,
        'internal_affairs': internal_affairs,
        'turn_manager': turn_manager,
        'military_system': military_system,
        'combat_system': combat_system,
        'diplomacy_system': diplomacy_system,
        'transfer_system': transfer_system,
        'ai_system': ai_system,
        'event_system': event_system
    }


def create_ui_components(screen, font_large, font_medium, font_small,
                         image_manager, sound_manager, power_map):
    """UIコンポーネント（ダイアログ、画面など）の作成

    Args:
        screen: Pygameスクリーン
        font_large: 大フォント
        font_medium: 中フォント
        font_small: 小フォント
        image_manager: 画像マネージャー
        sound_manager: 音声マネージャー
        power_map: 勢力マップ

    Returns:
        dict: UIコンポーネントを含む辞書
    """
    return {
        'event_dialog': EventDialog(screen, font_medium, sound_manager),
        'event_history_screen': EventHistoryScreen(screen, font_medium, sound_manager),
        'battle_preview': BattlePreviewScreen(screen, font_medium, power_map),
        'battle_animation': BattleAnimationScreen(screen, font_medium, image_manager, sound_manager),
        'daimyo_death_screen': DaimyoDeathScreen(screen, font_medium, image_manager, sound_manager),
        'transfer_dialog': TransferDialog(screen, font_medium, sound_manager),
        'general_assign_dialog': GeneralAssignDialog(screen, font_medium, sound_manager),
        'power_map': power_map
    }


def create_buttons(font_medium, font_small, sound_manager, game_instance):
    """ゲームボタンの作成

    Args:
        font_medium: 中フォント
        font_small: 小フォント
        sound_manager: 音声マネージャー
        game_instance: Gameインスタンス（コールバック用）

    Returns:
        dict: ボタンオブジェクトを含む辞書
    """
    button_y = config.SCREEN_HEIGHT - 50
    buttons = {}

    # ターン終了ボタン
    buttons['end_turn'] = Button(
        1100, button_y, 150, 40,
        "ターン終了",
        font_medium,
        game_instance.end_turn,
        sound_manager,
        "decide"
    )

    # 行動決定終了ボタン（プレイヤーの番終了用）
    buttons['confirm_actions'] = Button(
        1100, button_y, 150, 40,
        "行動決定終了",
        font_medium,
        game_instance.confirm_player_actions,
        sound_manager,
        "decide"
    )

    # 戻るボタン（行動決定ボタンと同じ位置に配置）
    buttons['close_detail'] = Button(
        1100, button_y, 150, 40,
        "戻る",
        font_medium,
        game_instance.close_province_detail,
        sound_manager,
        "cancel"
    )

    # 内政コマンドボタン
    buttons['cultivate'] = Button(
        540, 270-60, 180, 35,
        "開墾 (金200)",
        font_small,
        lambda: game_instance.execute_command("cultivate"),
        sound_manager,
        "decide"
    )

    buttons['develop_town'] = Button(
        540, 315-60, 180, 35,
        "町開発 (金300)",
        font_small,
        lambda: game_instance.execute_command("develop_town"),
        sound_manager,
        "decide"
    )

    buttons['flood_control'] = Button(
        540, 360-60, 180, 35,
        "治水 (金150)",
        font_small,
        lambda: game_instance.execute_command("flood_control"),
        sound_manager,
        "decide"
    )

    buttons['give_rice'] = Button(
        540, 405-60, 180, 35,
        "米配布 (米100)",
        font_small,
        lambda: game_instance.execute_command("give_rice"),
        sound_manager,
        "decide"
    )

    # 軍事コマンドボタン
    buttons['recruit'] = Button(
        540, 540-60, 180, 35,
        "100人徴兵 (金200)",
        font_small,
        lambda: game_instance.execute_command("recruit"),
        sound_manager,
        "decide"
    )

    buttons['attack'] = Button(
        540, 585-60, 180, 35,
        "攻撃",
        font_small,
        lambda: game_instance.execute_command("attack"),
        sound_manager,
        "decide"
    )

    # 転送コマンドボタン
    buttons['transfer_soldiers'] = Button(
        790, 270-60, 180, 35,
        "兵士転送",
        font_small,
        lambda: game_instance.execute_command("transfer_soldiers"),
        sound_manager,
        "decide"
    )

    buttons['transfer_gold'] = Button(
        790, 315-60, 180, 35,
        "金送付",
        font_small,
        lambda: game_instance.execute_command("transfer_gold"),
        sound_manager,
        "decide"
    )

    buttons['transfer_rice'] = Button(
        790, 360-60, 180, 35,
        "米運搬",
        font_small,
        lambda: game_instance.execute_command("transfer_rice"),
        sound_manager,
        "decide"
    )

    # 将軍配置ボタン
    buttons['assign_general'] = Button(
        790, 405-60, 180, 35,
        "将軍配置",
        font_small,
        lambda: game_instance.execute_command("assign_general"),
        sound_manager,
        "decide"
    )

    # 攻撃対象選択画面用のボタン
    buttons['confirm_attack'] = Button(
        config.SCREEN_WIDTH // 2 - 160, config.SCREEN_HEIGHT - 120,
        150, 40,
        "決定",
        font_medium,
        game_instance._confirm_attack,
        sound_manager,
        "decide"
    )

    buttons['cancel_attack'] = Button(
        config.SCREEN_WIDTH // 2 + 10, config.SCREEN_HEIGHT - 120,
        150, 40,
        "戻る",
        font_medium,
        game_instance._cancel_attack,
        sound_manager,
        "cancel"
    )

    # 兵力選択ボタン（攻撃画面用）
    btn_y = config.SCREEN_HEIGHT - 180
    btn_width = 120
    btn_spacing = 10
    start_x = (config.SCREEN_WIDTH - (btn_width * 4 + btn_spacing * 3)) // 2

    buttons['attack_25'] = Button(
        start_x, btn_y, btn_width, 35,
        f"小規模 ({int(config.ATTACK_RATIO_OPTIONS[0]*100)}%)",
        font_small,
        lambda: game_instance._set_attack_ratio(config.ATTACK_RATIO_OPTIONS[0]),
        sound_manager,
        "decide"
    )

    buttons['attack_50'] = Button(
        start_x + (btn_width + btn_spacing) * 1, btn_y, btn_width, 35,
        f"中規模 ({int(config.ATTACK_RATIO_OPTIONS[1]*100)}%)",
        font_small,
        lambda: game_instance._set_attack_ratio(config.ATTACK_RATIO_OPTIONS[1]),
        sound_manager,
        "decide"
    )

    buttons['attack_75'] = Button(
        start_x + (btn_width + btn_spacing) * 2, btn_y, btn_width, 35,
        f"大規模 ({int(config.ATTACK_RATIO_OPTIONS[2]*100)}%)",
        font_small,
        lambda: game_instance._set_attack_ratio(config.ATTACK_RATIO_OPTIONS[2]),
        sound_manager,
        "decide"
    )

    buttons['attack_100'] = Button(
        start_x + (btn_width + btn_spacing) * 3, btn_y, btn_width, 35,
        f"全軍 ({int(config.ATTACK_RATIO_OPTIONS[3]*100)}%)",
        font_small,
        lambda: game_instance._set_attack_ratio(config.ATTACK_RATIO_OPTIONS[3]),
        sound_manager,
        "decide"
    )

    return buttons
