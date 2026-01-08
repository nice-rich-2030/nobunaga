"""
デバッグログ管理モジュール

ターン終了時のゲーム状態をログファイルに出力する機能を提供
"""
import os
import config
from datetime import datetime


class DebugLogger:
    """デバッグログ出力を管理するクラス"""

    def __init__(self):
        """初期化"""
        self.log_file = None
        self._setup_log_file()

    def _setup_log_file(self):
        """ログファイルを作成（デバッグモードのみ）"""
        if not config.DEBUG_MODE:
            self.log_file = None
            return

        # logsディレクトリを作成
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # 現在時刻からファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/debug_{timestamp}.txt"

        try:
            self.log_file = open(log_filename, "w", encoding="utf-8")
            self.log_file.write(f"=== Nobunaga's Ambition - Debug Log ===\n")
            self.log_file.write(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write(f"Debug Mode: {config.DEBUG_MODE}\n")
            self.log_file.write(f"{'='*80}\n\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Warning: Failed to create log file: {e}")
            self.log_file = None

    def write_log(self, content):
        """デバッグログに書き込み（デバッグモードのみ）"""
        if not config.DEBUG_MODE or not self.log_file:
            return

        try:
            self.log_file.write(content)
            self.log_file.flush()
        except Exception:
            pass

    def log_turn_state(self, game_state, turn_battle_records, turn_manager):
        """ターン終了時のゲーム状態をログに出力

        Args:
            game_state: ゲーム状態オブジェクト
            turn_battle_records: このターンの戦闘記録リスト
            turn_manager: ターンマネージャー（イベント情報取得用）
        """
        if not config.DEBUG_MODE or not self.log_file:
            return

        log = []
        log.append(f"\n{'='*80}\n")
        log.append(f"TURN {game_state.current_turn} - {game_state.get_season_name()} {game_state.get_year()}年\n")
        log.append(f"{'='*80}\n\n")

        # ターンイベント情報
        if turn_manager and hasattr(turn_manager, 'turn_events') and turn_manager.turn_events:
            log.append(f"【ターンイベント】\n")
            for event in turn_manager.turn_events:
                log.append(f"  - {event}\n")
            log.append("\n")

        # 戦闘情報
        if turn_battle_records:
            log.append(f"【戦闘結果】\n")
            for i, battle in enumerate(turn_battle_records, 1):
                self._format_battle_info(log, i, battle)
            log.append("\n")

        # 大名情報
        self._format_daimyo_info(log, game_state)

        # 将軍情報
        self._format_general_info(log, game_state)

        # 領地情報
        self._format_province_info(log, game_state)

        self.write_log(''.join(log))

    def _format_battle_info(self, log, battle_num, battle):
        """戦闘情報をフォーマット"""
        attacker_name = battle.get("attacker_name", "不明")
        defender_name = battle.get("defender_name", "不明")
        origin_province = battle.get("attacker_province", "不明")
        target_province = battle.get("defender_province", "不明")

        attacker_initial = battle.get("attacker_troops", 0)
        defender_initial = battle.get("defender_troops", 0)

        result_obj = battle.get("result")
        if result_obj:
            attacker_remaining = result_obj.attacker_remaining
            defender_remaining = result_obj.defender_remaining
            attacker_casualties = result_obj.attacker_casualties
            defender_casualties = result_obj.defender_casualties
            attacker_won = result_obj.attacker_won
        else:
            attacker_remaining = 0
            defender_remaining = 0
            attacker_casualties = 0
            defender_casualties = 0
            attacker_won = False

        winner = "攻撃側" if attacker_won else "防御側"
        result_text = "勝利" if attacker_won else "敗北"

        attacker_general = battle.get("attacker_general", "なし")
        defender_general = battle.get("defender_general", "なし")

        log.append(f"  戦闘{battle_num}: {origin_province}({attacker_name}) vs {target_province}({defender_name})\n")
        log.append(f"      攻撃側将軍:{attacker_general} / 防御側将軍:{defender_general}\n")
        log.append(f"      攻撃側: 初期兵力{attacker_initial} → 残存{attacker_remaining} (損失{attacker_casualties})\n")
        log.append(f"      防御側: 初期兵力{defender_initial} → 残存{defender_remaining} (損失{defender_casualties})\n")
        log.append(f"      結果: {winner}の{result_text}\n")

        if attacker_won:
            log.append(f"      {target_province}を{attacker_name}が占領\n")
        else:
            log.append(f"      {defender_name}が{target_province}を守り切った\n")

    def _format_daimyo_info(self, log, game_state):
        """大名情報をフォーマット"""
        log.append(f"【大名情報】\n")
        for daimyo in sorted(game_state.daimyo.values(), key=lambda d: d.id):
            status = "生存" if daimyo.is_alive else "死亡"
            log.append(f"  [{daimyo.id}] {daimyo.clan_name} {daimyo.name} ({status})\n")
            log.append(f"      年齢:{daimyo.age} 健康:{daimyo.health} 野心:{daimyo.ambition}\n")
            log.append(f"      魅力:{daimyo.charm} 知力:{daimyo.intelligence} 武力:{daimyo.war_skill}\n")
            log.append(f"      支配領地数:{len(daimyo.controlled_provinces)} 領地ID:{sorted(daimyo.controlled_provinces)}\n")

    def _format_general_info(self, log, game_state):
        """将軍情報をフォーマット"""
        log.append(f"\n【将軍情報】\n")
        for general in sorted(game_state.generals.values(), key=lambda g: g.id):
            serving = f"仕官先:{general.serving_daimyo_id}" if general.serving_daimyo_id else "浪人"
            assigned = f"配置:{general.current_province_id}" if general.current_province_id else "未配置"
            log.append(f"  [{general.id}] {general.name} ({serving}, {assigned})\n")
            log.append(f"      年齢:{general.age} 健康:{general.health}\n")
            log.append(f"      統率:{general.leadership} 武力:{general.war_skill} 知力:{general.intelligence} 政治:{general.politics}\n")

    def _format_province_info(self, log, game_state):
        """領地情報をフォーマット"""
        log.append(f"\n【領地情報】\n")
        for province in sorted(game_state.provinces.values(), key=lambda p: p.id):
            owner_name = "無所属"
            if province.owner_daimyo_id:
                owner = game_state.get_daimyo(province.owner_daimyo_id)
                if owner:
                    owner_name = f"{owner.clan_name}"

            governor_name = "なし"
            if province.governor_general_id:
                if config.DAIMYO_ID_MIN <= province.governor_general_id <= config.DAIMYO_ID_MAX:
                    gov = game_state.get_daimyo(province.governor_general_id)
                    if gov:
                        governor_name = f"大名:{gov.name}"
                elif config.GENERAL_ID_MIN <= province.governor_general_id <= config.GENERAL_ID_MAX:
                    gov = game_state.get_general(province.governor_general_id)
                    if gov:
                        governor_name = f"将軍:{gov.name}"

            log.append(f"  [{province.id:2d}] {province.name} (所有:{owner_name}, 守将:{governor_name})\n")
            log.append(f"      兵:{province.soldiers} 農民:{province.peasants} 金:{province.gold} 米:{province.rice}\n")
            log.append(f"      開発Lv:{province.development_level} 町Lv:{province.town_level} 農民忠誠:{province.peasant_loyalty} 兵士士気:{province.soldier_morale}\n")

    def close(self):
        """ログファイルを閉じる"""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None
