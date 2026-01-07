# 戦闘アニメーションシステム仕様書

戦国時代戦略ゲームの戦闘アニメーションシステムの技術仕様と拡張ガイド

---

## 目次

1. [概要](#概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [実装詳細](#実装詳細)
4. [データフロー](#データフロー)
5. [技術仕様](#技術仕様)
6. [拡張ポイント](#拡張ポイント)

---

## 概要

戦闘アニメーションは、プレイヤーに戦闘の経過と結果を視覚的に伝えるシステムです。2層構造（プレビュー＋詳細アニメーション）で実装されており、約13秒の演出を提供します。

### 主な特徴

- ✅ **2層構造**: プレビュー → 詳細アニメーションの段階的表現
- ✅ **4フェーズアニメーション**: 準備 → 開始 → 交戦 → 結果
- ✅ **スキップ機能**: ユーザーが演出を短縮可能
- ✅ **BGM統合**: 戦闘シーンで自動BGM切り替え
- ✅ **データ駆動**: 柔軟な情報伝達

---

## アーキテクチャ

### 処理フロー

```
戦闘発生
    ↓
【プレビュー層】BattlePreviewScreen
    - 勢力図ベースで進軍ルートを表示
    - 80フレーム (約2.7秒)
    ↓
【詳細演出層】BattleAnimationScreen
    - 4フェーズで戦闘経過を表示
    - 300フレーム (約10秒)
    ↓
戦闘結果適用・次のイベントへ
```

### 設計原則

1. **フェーズベース**: 各段階を明確に分離
2. **タイマー制御**: フレーム単位で安定動作
3. **非破壊的拡張**: 既存構造を維持しながら機能追加可能
4. **パフォーマンス重視**: 図形ベース描画で軽量化

---

## 実装詳細

### 1. BattlePreviewScreen (プレビュー層)

**ファイル**: `ui/battle_preview.py`

**役割**: 戦闘前の予告演出

#### アニメーション構成

| フェーズ | フレーム | 時間 | 演出内容 |
|---------|---------|------|---------|
| フェーズ1 | 0-60 | 2秒 | 矢印アニメーション（攻撃元→防御先） |
| フェーズ2 | 60-80 | 0.7秒 | 静止画（領地ハイライト） |

#### 実装例

```python
class BattlePreviewScreen:
    def __init__(self, screen, font, power_map, sound_manager):
        self.animation_timer = 0
        self.total_duration = 80
        self.arrow_phase_duration = 60

    def update(self, game_state):
        if not self.is_visible:
            return

        self.animation_timer += 1

        # スキップ処理
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]:
            self.hide()
            if self.on_finish_callback:
                self.on_finish_callback()
```

#### 特徴

- 勢力図を背景として利用
- 矢印の動的描画（領地座標変換）
- スペースキー/マウスクリックでスキップ可能

---

### 2. BattleAnimationScreen (詳細演出層)

**ファイル**: `ui/battle_animation.py`

**役割**: 戦闘の詳細な視覚表現

#### 4フェーズ構成

##### フェーズ0: 準備画面 (60フレーム / 2秒)

**背景画像**: `assets/images/battle_vs_background.png`

**表示要素**:
- タイトル: 「⚔ 戦 闘 ⚔」（ゴールド）
- VS表示: 中央配置
- 肖像画: 攻撃側・防御側 (330x330px)
- 情報:
  - 領地名
  - 大名名
  - 兵力数
  - 武将名＆ステータス (武力・統率・知力)

**描画コード例**:
```python
def _draw_phase_0(self):
    # 背景
    self.screen.blit(self.bg_vs, (0, 0))

    # タイトル
    title = self.font_large.render("⚔ 戦 闘 ⚔", True, config.GOLD)

    # 攻撃側肖像画 (330x330px)
    attacker_portrait = self.image_manager.get_portrait_for_battle(...)
    self.screen.blit(attacker_portrait, (150, 200))

    # VS表示
    vs_text = self.font_large.render("VS", True, config.GOLD)

    # 防御側肖像画 (330x330px)
    defender_portrait = self.image_manager.get_portrait_for_battle(...)
    self.screen.blit(defender_portrait, (650, 200))
```

##### フェーズ1: 戦闘開始 (40フレーム / 1.3秒)

**背景画像**: `assets/images/battle_vs_background.png`

**演出**:
- 「戦 闘 開 始 ！」大文字ゴールドテキスト
- 10フレームごとに点滅
- 画面全体の強調表示

**点滅ロジック**:
```python
def _draw_phase_1(self):
    # 点滅効果
    if self.animation_timer // 10 % 2 == 0:
        start_text = self.font_large.render(
            "戦 闘 開 始 ！",
            True,
            config.GOLD
        )
        # 中央配置
        text_rect = start_text.get_rect(
            center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        )
        self.screen.blit(start_text, text_rect)
```

##### フェーズ2: 交戦中 (80フレーム / 2.7秒)

**背景画像**: `assets/images/battle_combat_background.png`

**表示要素**:
- 肖像画: 攻撃側・防御側 (240x240px、左上・右上)
- 中央演出: 交差する刀（赤/青ライン）
- 兵力バー (250x30px):
  - 背景: グレー
  - 現在値: 赤または青
  - 枠: ゴールド
  - テキスト: 「初期兵力 / 現在兵力 (-XX%)」

**エフェクト**:

1. **画面シェイク**
```python
shake_offset = math.sin(self.animation_timer * 0.5) * 5  # ±5ピクセル
```

2. **フラッシュ効果**
```python
if self.animation_timer % 20 == 0:
    self.flash_alpha = 100  # 白フラッシュ

# フラッシュ描画
if self.flash_alpha > 0:
    flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    flash_surface.fill((255, 255, 255))
    flash_surface.set_alpha(self.flash_alpha)
    self.screen.blit(flash_surface, (0, 0))
    self.flash_alpha -= 10  # 徐々にフェード
```

3. **刀の交差アニメーション**
```python
sword_offset = (self.animation_timer % 20) * 2  # 左右往復
```

**兵力バーアニメーション**:
```python
def _animate_troop_bar(self):
    # 初期値から最終値へ滑らかに減少
    progress = self.animation_timer / self.phase_duration[2]

    # 攻撃側
    target_attacker = (self.attacker_remaining / self.attacker_troops) * 100
    self.attacker_bar_value = 100 - (100 - target_attacker) * progress

    # 防御側
    target_defender = (self.defender_remaining / self.defender_troops) * 100
    self.defender_bar_value = 100 - (100 - target_defender) * progress
```

##### フェーズ3: 結果表示 (120フレーム / 4秒)

**背景画像**: `assets/images/battle_result_background.png`

**表示要素**:
- 勝利宣言: 「⚔ [勝者] の勝利！⚔」（ゴールド）
- 肖像画:
  - 勝者: 金枠
  - 敗者: 暗転 (brightness=0.3)
- 戦績: 「勝 X  負 Y」
- 戦闘結果表:
  ```
  攻撃側: 初期XXX → 損失YYY → 残存ZZZ
  防御側: 初期XXX → 損失YYY → 残存ZZZ
  ```
- 領地占領: 「★ [領地] を占領！★」（成功時のみ）
- 継続メッセージ: 「[SPACE/クリック]で続行」（15フレームごと点滅）

**勝敗による表示切り替え**:
```python
def _draw_phase_3(self):
    if self.result.attacker_won:
        winner_name = self.attacker_name
        winner_portrait = self.attacker_portrait
        loser_portrait = self.defender_portrait
    else:
        winner_name = self.defender_name
        winner_portrait = self.defender_portrait
        loser_portrait = self.attacker_portrait

    # 勝者: 通常表示 + 金枠
    pygame.draw.rect(screen, config.GOLD, winner_rect, 5)

    # 敗者: 暗転
    loser_surface = loser_portrait.copy()
    loser_surface.fill((0, 0, 0, 0), special_flags=pygame.BLEND_MULT)
    # brightness = 0.3
```

---

## データフロー

### 戦闘データの生成から表示まで

```
[sequential_turn_manager.py]
_execute_military_commands()
    ↓
[systems/military.py]
military_system.create_attack_army()
    → Army オブジェクト生成
    ↓
[systems/combat.py]
combat_system.resolve_battle(army, target_province)
    → BattleResult オブジェクト生成
    ↓
[sequential_turn_manager.py]
battle_data 辞書を組み立て
    ↓
yield ("battle_animation", battle_data)
    ↓
[main.py]
process_turn_event() が受信
    ↓
1. battle_preview.show(preview_data, on_finish=...)
    ↓
2. show_seq_battle_animation(battle_data)
    ↓
3. on_seq_battle_animation_finished()
    - 戦闘結果を適用
    - メッセージ表示
    - BGM復帰
    ↓
次のイベント処理へ
```

### BattleResult オブジェクト

**定義場所**: `systems/combat.py`

```python
class BattleResult:
    attacker_won: bool              # 攻撃側勝利フラグ
    attacker_casualties: int        # 攻撃側被害数
    defender_casualties: int        # 防御側被害数
    attacker_remaining: int         # 攻撃側残存兵力
    defender_remaining: int         # 防御側残存兵力
    province_captured: bool         # 領地占領フラグ
    battle_log: List[str]          # 戦闘ログ（現在未使用）
```

### battle_data 辞書

**生成場所**: `core/sequential_turn_manager.py` (行822-844)

```python
battle_data = {
    # UI表示用文字列
    "attacker_name": str,              # 攻撃側大名の部族名
    "defender_name": str,              # 防御側大名の部族名
    "attacker_province": str,          # 出陣元領地名
    "defender_province": str,          # 目標領地名
    "attacker_troops": int,            # 出陣兵力（初期）
    "defender_troops": int,            # 防御兵力（初期）
    "attacker_general": str or None,   # 攻撃側武将名
    "defender_general": str or None,   # 防御側武将名

    # オブジェクト参照（詳細表示用）
    "attacker_general_obj": General,
    "defender_general_obj": General,
    "attacker_daimyo_obj": Daimyo,
    "defender_daimyo_obj": Daimyo,
    "attacker_general_id": int or None,
    "defender_general_id": int or None,
    "attacker_daimyo_id": int,
    "defender_daimyo_id": int,

    # 戦闘結果
    "result": BattleResult,

    # ゲーム状態更新用
    "army": Army,
    "target_province_id": int,
    "origin_province_id": int,
    "combat_system": CombatSystem,
}
```

---

## 技術仕様

### タイマー制御

**基本ロジック**:
```python
def update(self):
    if not self.is_visible:
        return

    self.animation_timer += 1

    # フェーズ遷移判定
    if self.animation_timer >= self.phase_duration[self.animation_phase]:
        self.animation_timer = 0
        self.animation_phase += 1

    # 終了判定
    if self.animation_phase >= len(self.phase_duration):
        self.hide()
        if self.on_finish_callback:
            self.on_finish_callback()
```

**FPS設定**: `config.FPS = 30`
- 1フレーム = 33.3ms
- 1秒 = 30フレーム

**フェーズ時間**:
```python
self.phase_duration = [60, 40, 80, 120]  # フレーム数
```

| フェーズ | フレーム | 秒 | 用途 |
|---------|---------|---|------|
| 0 | 60 | 2.0 | 準備画面 |
| 1 | 40 | 1.3 | 戦闘開始 |
| 2 | 80 | 2.7 | 交戦中 |
| 3 | 120 | 4.0 | 結果表示 |
| **合計** | **300** | **10.0** | - |

### 使用アセット

#### 画像ファイル

| ファイルパス | 用途 | サイズ |
|------------|------|-------|
| `assets/images/battle_vs_background.png` | フェーズ0・1背景 | 1024x768 |
| `assets/images/battle_combat_background.png` | フェーズ2背景 | 1024x768 |
| `assets/images/battle_result_background.png` | フェーズ3背景 | 1024x768 |
| 武将肖像画 | 各フェーズ | 可変 (image_manager経由) |
| 大名肖像画 | フォールバック | 可変 |

#### 効果音

**現在実装**:
- `battle` - 戦闘開始時に1回再生

**拡張候補**:
- `sword_clash` - フェーズ2開始時
- `damage_pop` - ダメージ発生時（複数回）
- `victory_fanfare` - 勝利時

#### BGM

**統合仕様**:
- 戦闘開始時: `battle` シーンに自動切り替え (`main.py:573`)
- 戦闘終了後: `ai_turn` シーンに復帰 (`main.py:654`)

---

## 拡張ポイント

### 優先度: 高

#### 1. ラウンド別演出

**現状の課題**:
- 兵力バーが滑らかに減少するだけ
- 戦闘の過程が見えない

**改善案**:
```python
# systems/combat.py で各ラウンドの詳細を記録
battle_log_events = [
    {"round": 1, "attacker_damage": 50, "defender_damage": 40},
    {"round": 2, "attacker_damage": 45, "defender_damage": 35},
    {"round": 3, "attacker_damage": 40, "defender_damage": 30},
]

# ui/battle_animation.py でラウンドごとにアニメーション
for round_data in battle_log_events:
    # ダメージポップアップ表示
    # 兵力バー段階的減少
    # フラッシュエフェクト
    # 効果音再生
```

**期待効果**:
- 戦闘の臨場感向上
- ダメージ量の視覚化
- ラウンド進行の理解しやすさ

#### 2. 効果音の拡充

**実装例**:
```python
class BattleAnimationScreen:
    def __init__(self, ...):
        self.sound_events = {
            "phase_0": None,
            "phase_1": "battle_start",
            "phase_2_start": "sword_clash",
            "phase_2_hit": "damage_pop",      # 複数回
            "phase_3": "victory_fanfare"      # 勝利時のみ
        }

    def update(self):
        # フェーズ開始時
        if self.animation_timer == 0:
            sound = self.sound_events.get(f"phase_{self.animation_phase}")
            if sound:
                self.sound_manager.play(sound)

        # フェーズ2のダメージ音
        if self.animation_phase == 2 and self.animation_timer % 20 == 0:
            self.sound_manager.play("damage_pop")
```

#### 3. 武将対決演出

**コンセプト**:
- 武将同士の能力を視覚的に比較
- 武将スキル発動エフェクト
- 一騎打ちシーン

**実装案**:
```python
def _draw_general_duel(self):
    # 武将ステータス比較
    attacker_stats = {
        "武力": self.attacker_general.war_skill,
        "統率": self.attacker_general.leadership,
        "知力": self.attacker_general.intelligence
    }

    defender_stats = {
        "武力": self.defender_general.war_skill,
        "統率": self.defender_general.leadership,
        "知力": self.defender_general.intelligence
    }

    # バーグラフで比較表示
    # 優位な方を強調
```

### 優先度: 中

#### 4. エフェクト層の追加

**新ファイル**: `ui/battle_effects.py`

```python
class BattleEffectManager:
    """戦闘エフェクト管理クラス"""

    def __init__(self, screen):
        self.screen = screen
        self.effects = []  # アクティブなエフェクトのリスト

    def add_sword_slash(self, pos, direction):
        """刀撃エフェクトを追加"""
        effect = SwordSlashEffect(pos, direction)
        self.effects.append(effect)

    def add_damage_popup(self, value, pos):
        """ダメージ数値ポップアップを追加"""
        effect = DamagePopupEffect(value, pos)
        self.effects.append(effect)

    def add_particle(self, particle_type, pos, velocity):
        """パーティクルエフェクトを追加"""
        effect = ParticleEffect(particle_type, pos, velocity)
        self.effects.append(effect)

    def update(self):
        """全エフェクトを更新"""
        for effect in self.effects[:]:
            effect.update()
            if effect.is_finished():
                self.effects.remove(effect)

    def draw(self):
        """全エフェクトを描画"""
        for effect in self.effects:
            effect.draw(self.screen)
```

#### 5. 設定可能化

**config.pyへの追加**:
```python
# ========================================
# 戦闘アニメーション設定
# ========================================

# アニメーション速度 ("fast", "normal", "slow")
BATTLE_ANIMATION_SPEED = "normal"

# フェーズ別時間設定（フレーム数）
BATTLE_PHASE_DURATIONS = {
    "fast": [30, 20, 40, 60],      # 合計150フレーム (5秒)
    "normal": [60, 40, 80, 120],   # 合計300フレーム (10秒)
    "slow": [90, 60, 120, 180]     # 合計450フレーム (15秒)
}

# エフェクト有効/無効
BATTLE_EFFECTS_ENABLED = True

# 画面シェイク強度 (0-10)
BATTLE_SHAKE_INTENSITY = 5

# フラッシュエフェクト有効/無効
BATTLE_FLASH_ENABLED = True
```

**BattleAnimationScreenでの利用**:
```python
class BattleAnimationScreen:
    def __init__(self, ...):
        # 設定から時間を読み込み
        speed = config.BATTLE_ANIMATION_SPEED
        self.phase_duration = config.BATTLE_PHASE_DURATIONS[speed]

        # エフェクト設定
        self.effects_enabled = config.BATTLE_EFFECTS_ENABLED
        self.shake_intensity = config.BATTLE_SHAKE_INTENSITY
        self.flash_enabled = config.BATTLE_FLASH_ENABLED
```

#### 6. 戦況テキスト

**実装イメージ**:
```python
def _get_battle_commentary(self, round_data):
    """戦況に応じたコメントを生成"""
    attacker_dmg = round_data["attacker_damage"]
    defender_dmg = round_data["defender_damage"]

    if attacker_dmg > defender_dmg * 1.5:
        return "攻撃側、大ダメージ！"
    elif defender_dmg > attacker_dmg * 1.5:
        return "防御側、踏ん張る！"
    elif attacker_dmg > defender_dmg:
        return "攻撃側、優勢！"
    elif defender_dmg > attacker_dmg:
        return "防御側、押し返す！"
    else:
        return "互角の戦い！"
```

### 優先度: 低

#### 7. スプライトアニメーション

- キャラクターの攻撃・防御モーション
- 敗北時のアニメーション
- 勝利ポーズ

#### 8. 天候・時間帯

- 戦闘背景に季節を反映
- 雨・雪などの天候エフェクト
- 昼夜の表現

#### 9. 陣形表現

- 挟撃・包囲などの戦術を視覚化
- 地形効果の表現

---

## ベストプラクティス

### 拡張時の注意点

1. **既存フェーズ構造の維持**
   - 4フェーズの基本構造は変更しない
   - 新機能はフェーズ内で完結させる

2. **タイマー制御の継続**
   - フレームベースのタイマーを維持
   - 新エフェクトもフレーム単位で制御

3. **スキップ機能のサポート**
   - 新演出もスキップ可能に
   - ユーザー体験を損なわない

4. **パフォーマンス配慮**
   - 重い描画処理を避ける
   - 必要に応じてエフェクトON/OFF可能に

### 開発ワークフロー

1. **プロトタイプ作成**
   - 小規模な機能で動作確認
   - 既存コードへの影響を最小化

2. **段階的実装**
   - 1つのフェーズから拡張開始
   - 動作確認後に他フェーズへ展開

3. **設定可能化**
   - config.pyで調整可能に
   - ユーザーが無効化できる

4. **テスト**
   - 様々な戦闘パターンで確認
   - エッジケース（武将なし、大差の戦い）

---

## まとめ

### 現状の評価

**✅ 強み**:
- 明確なフェーズ構造で保守しやすい
- フレームベースで安定動作
- データ駆動で拡張容易
- スキップ機能で柔軟性高い

**⚠️ 改善点**:
- 戦闘ログが未活用
- 効果音が限定的
- 設定項目がハードコード
- エフェクトがシンプル

### 推奨される改善優先順位

1. **ラウンド別演出** → 臨場感向上
2. **効果音拡充** → 迫力向上
3. **設定可能化** → ユーザー体験向上
4. **エフェクト層追加** → 視覚的魅力向上

---

**更新日**: 2025年1月
**バージョン**: 1.0.0
