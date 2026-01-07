# 戦国時代戦略ゲーム 実装計画

## 概要

初期の「信長の野望」(1983-1990年代)をベースとした、pygameによるターン制戦略シミュレーションゲームを開発します。

**スコープ:**
- 初期作品のシンプルなターン制システム
- 標準版（内政、戦闘、武将、外交の全機能を含む）
- 小規模マップ（10-20地域）
- シングルプレイヤー + AIプレイヤー

## コアゲームメカニクス

### リソース管理
- **金**: 兵士雇用、装備購入、建設に使用
- **米**: 軍の維持、農民忠誠度、交易に使用
- **農民**: 人口（税収を生み、兵士に徴用可能）
- **兵士**: 農民から徴用される軍事力

### 重要な設計原則
**「大名本人以外に、グローバルリソースは存在しない。全てはローカル」**

各領地が独自に管理:
- 金の蓄え
- 米の備蓄
- 農民人口
- 軍事力
- 開発レベル
- 忠誠度/士気

### ターン構造
- **季節ベースのターン** (春、夏、秋、冬 = 1年)
- **1領地につき1ターン1コマンド** (戦略的選択が重要)
- **加齢システム**: 大名と武将が年を取り、最終的に死亡
- **ランダムイベント**: 自然災害、反乱、機会

## プロジェクト構造

```
nobunaga/
├── main.py                      # エントリーポイント、ゲームループ
├── config.py                    # グローバル定数、設定
├── requirements.txt             # 依存関係 (pygame等)
│
├── core/                        # コアゲームエンジン
│   ├── __init__.py
│   ├── game_state.py           # メインゲーム状態マネージャー
│   ├── turn_manager.py         # ターン/季節進行
│   ├── event_manager.py        # イベントシステム
│   └── save_load.py            # セーブ/ロード
│
├── models/                      # データモデル
│   ├── __init__.py
│   ├── province.py             # 領地データ
│   ├── daimyo.py               # 大名クラス
│   ├── general.py              # 武将クラス
│   ├── army.py                 # 軍隊/軍事ユニット
│   └── diplomacy.py            # 関係、条約、同盟
│
├── systems/                     # ゲームシステム
│   ├── __init__.py
│   ├── economy.py              # 金/米管理、交易
│   ├── military.py             # 徴用、訓練、移動
│   ├── combat.py               # 戦闘解決システム
│   ├── diplomacy.py            # 外交行動と関係
│   ├── internal_affairs.py     # 開発、耕作、忠誠度
│   └── events.py               # ランダムイベント、災害
│
├── ai/                          # AI対戦相手ロジック
│   ├── __init__.py
│   ├── ai_controller.py        # メインAI意思決定
│   ├── strategy.py             # 戦略計画
│   └── tactics.py              # 戦闘戦術
│
├── ui/                          # ユーザーインターフェース
│   ├── __init__.py
│   ├── screen_manager.py       # 画面状態管理
│   ├── main_map.py             # 領地マップビュー
│   ├── province_detail.py      # 領地管理画面
│   ├── battle_screen.py        # 戦闘インターフェース
│   ├── diplomacy_screen.py     # 外交インターフェース
│   ├── status_screen.py        # 大名/武将ステータス
│   ├── command_menu.py         # コマンド選択UI
│   └── widgets.py              # 再利用可能なUIコンポーネント
│
├── graphics/                    # ビジュアルアセット
│   ├── sprites/                # 領地アイコン、ユニット、肖像
│   ├── backgrounds/            # 画面背景
│   └── ui/                     # UI要素、ボタン、フレーム
│
├── data/                        # ゲームデータファイル
│   ├── provinces.json          # 領地定義
│   ├── daimyo.json             # 歴史的大名データ
│   ├── generals.json           # 武将プール
│   ├── events.json             # ランダムイベント定義
│   └── scenarios.json          # 開始シナリオ
│
└── utils/                       # ユーティリティ関数
    ├── __init__.py
    ├── pathfinding.py          # 領地の隣接、距離
    ├── math_utils.py           # 計算、公式
    └── constants.py            # ゲームバランス定数
```

## データモデル

### Province (領地)
```python
class Province:
    # アイデンティティ
    id: int
    name: str
    position: tuple[int, int]
    adjacent_provinces: list[int]

    # 所有権
    owner_daimyo_id: int | None
    governor_general_id: int | None

    # 人口
    peasants: int
    max_peasants: int
    peasant_loyalty: int  # 0-100

    # 軍事
    soldiers: int
    soldier_morale: int  # 0-100

    # 経済
    gold: int
    rice: int
    tax_rate: int  # 0-100

    # 開発
    development_level: int  # 1-10
    town_level: int  # 1-10
    flood_control: int  # 0-100

    # 地形
    terrain_type: str
    has_castle: bool
    castle_defense: int
```

### Daimyo (大名)
```python
class Daimyo:
    id: int
    name: str
    clan_name: str

    # 能力値
    age: int
    health: int  # 0-100
    ambition: int  # 0-100 (AI攻撃性)
    luck: int  # 0-100
    charm: int  # 0-100 (外交、忠誠度)
    intelligence: int  # 0-100 (経済、戦略)
    war_skill: int  # 0-100

    # 領土
    capital_province_id: int
    controlled_provinces: list[int]

    # 関係 (他大名との関係値)
    relations: dict[int, int]  # -100 to +100
```

### General (武将)
```python
class General:
    id: int
    name: str
    age: int

    # 忠誠度
    loyalty_to_daimyo: int  # 0-100
    serving_daimyo_id: int | None

    # 能力値
    war_skill: int  # 0-100
    leadership: int  # 0-100
    politics: int  # 0-100
    intelligence: int  # 0-100

    # ステータス
    current_province_id: int | None
```

## ターンフロー（11フェーズ）

1. **ターン開始**: 季節進行、加齢、死亡判定
2. **収入と生産**: 米生産、税収
3. **維持費**: 兵士の米消費、士気変化
4. **ランダムイベント**: 災害、機会イベント
5. **プレイヤーコマンドフェーズ**: 各領地で1コマンド選択
6. **AIコマンドフェーズ**: AI大名がコマンド選択
7. **コマンド解決**: 全コマンドを順番に実行
8. **戦闘解決**: 宣戦布告された戦闘を解決
9. **外交更新**: 関係値更新、条約期限
10. **勝利判定**: 勝利条件チェック
11. **ターン終了**: 状態保存、次ターン準備

## 実装フェーズ

### フェーズ1: 基盤構築 ✓
**目標**: 基本的なゲーム構造とデータモデル

### フェーズ2: ターンシステムと経済
**目標**: ターンベースのゲームループと経済メカニクス

### フェーズ3: 軍事と戦闘
**目標**: 軍事および戦闘システムの完成

### フェーズ4: 外交とAI
**目標**: 外交システムとAI対戦相手

### フェーズ5: イベントと仕上げ
**目標**: ランダムイベント、UI強化、ゲーム感触

### フェーズ6: バランスとテスト
**目標**: ゲームバランスとバグ修正
