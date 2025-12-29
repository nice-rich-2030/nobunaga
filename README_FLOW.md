# ターン処理フロー詳細ドキュメント

## 概要

このドキュメントでは、信長の野望スタイル戦略ゲームにおける1ターンの処理フローを詳細に説明します。
ターンは11のフェーズに分かれており、年齢処理、イベント処理、コマンド処理（AI/プレイヤー）、戦闘処理などが順序立てて実行されます。

## ターン処理の全体構造

1ターンは以下の11フェーズで構成されます（[core/turn_manager.py:26-68](core/turn_manager.py#L26-L68)）:

```
Phase 1: ターン開始処理（年齢更新、年開始イベント）
Phase 2: ランダムイベント（災害、一揆など）
Phase 3: 収入フェーズ（税収、米生産）
Phase 4: イベント実行フェーズ（プレイヤー選択 or AI自動処理）
Phase 5: プレイヤーコマンド受付
Phase 6: AIコマンド実行
Phase 7: 内政効果適用
Phase 8: 戦闘計算（結果は未適用）
Phase 9: ターン終了処理（忠誠度・士気更新）
Phase 10: 死亡判定（領地喪失による滅亡）
Phase 11: 勝利条件判定
```

**重要な設計方針**:
- Phase 8で戦闘結果を「計算」するが、この時点では結果は**適用されない**
- 実際の結果適用は、UIでの戦闘アニメーション後に行われる（[main.py:634-689](main.py#L634-L689)）
- これにより、全ての戦闘は**ターン開始時の領地状態**を基準に計算される

---

## Phase 1: ターン開始処理

**実行タイミング**: ターン開始直後
**実装場所**: [core/turn_manager.py:70-84](core/turn_manager.py#L70-L84)

### 処理内容

1. **ターンカウンタ増加**
   ```python
   self.current_turn += 1
   ```

2. **春の処理（年齢更新）**
   - 3ターンごと（春）に実行
   - 全ての大名と武将の年齢を1増加
   - 健康値を1減少
   ```python
   if self.current_turn % 3 == 1:  # 春
       for daimyo in self.game_state.daimyo.values():
           daimyo.age += 1
           daimyo.health = max(0, daimyo.health - 1)
       for general in self.game_state.generals.values():
           general.age += 1
           general.health = max(0, general.health - 1)
   ```

3. **年開始イベント通知**
   ```python
   if self.current_turn % 3 == 1:
       year = self.current_year
       self.turn_events.append(f"=== {year}年 春 ===")
   ```

4. **プレイヤーコマンドの保存と復元**
   - `execute_turn()`開始時にプレイヤーコマンドを一時保存（[core/turn_manager.py:28-30](core/turn_manager.py#L28-L30)）
   - Phase 1実行後に復元（[core/turn_manager.py:37-38](core/turn_manager.py#L37-L38)）
   - これにより、UIで入力したプレイヤーコマンドが`turn_events.clear()`で消えないようにする

### 対象範囲

- **全ての大名**: alive状態に関わらず処理
- **全ての武将**: alive状態に関わらず処理

---

## Phase 2: ランダムイベント

**実行タイミング**: Phase 1直後
**実装場所**: [core/turn_manager.py:86-121](core/turn_manager.py#L86-L121)

### 処理内容

各大名の各領地に対して、確率的にランダムイベントを発生させます。

### イベント種類

1. **災害（洪水）** - 5%の確率
   - 米が50%減少
   - 農民忠誠度が-10
   - 治水値が影響（高いほど被害軽減）

2. **豊作** - 10%の確率
   - 米が50%増加
   - 農民忠誠度が+5

3. **一揆** - 忠誠度30未満で5%の確率
   - 農民が20%減少
   - 忠誠度がさらに-10

4. **疫病** - 5%の確率
   - 兵士が20%減少
   - 士気が-15

### 処理順序

```
for 各大名 in alive大名:
    for 各領地 in 大名の領地:
        ランダムイベント抽選
        → 発生したら turn_events に記録
```

---

## Phase 3: 収入フェーズ

**実行タイミング**: Phase 2直後
**実装場所**: [core/turn_manager.py:123-161](core/turn_manager.py#L123-L161)

### 処理内容

各大名の各領地で、税収と米生産を計算して適用します。

### 計算式

1. **税収**（[models/province.py:91-100](models/province.py#L91-L100)）:
   ```
   税収 = BASE_TAX_INCOME × 町レベル × 税率 × 農民比率
   ```

2. **米生産**（[models/province.py:74-89](models/province.py#L74-L89)）:
   ```
   米生産 = BASE_RICE_PRODUCTION × 開発レベル × 地形倍率 × 忠誠度ボーナス
   ```

3. **兵士の米消費**（[models/province.py:102-104](models/province.py#L102-L104)）:
   ```
   消費米 = 兵士数 × SOLDIER_RICE_CONSUMPTION
   ```

### 処理順序

```
for 各大名 in alive大名:
    for 各領地 in 大名の領地:
        税収を計算・加算
        米生産を計算・加算
        兵士の米消費を減算

        もし米が負になったら:
            兵士士気 -10
            turn_events に記録
```

---

## Phase 4: イベント実行フェーズ

**実行タイミング**: Phase 3直後
**実装場所**: [core/turn_manager.py:163-214](core/turn_manager.py#L163-L214)

### 処理内容

Phase 2で発生したランダムイベントや、特別イベント（健康悪化、死亡など）を処理します。

### イベントタイプ

1. **健康悪化イベント**
   - 健康値30未満の大名/武将に対して発生
   - プレイヤー: UIで選択肢を表示（治療 or 放置）
   - AI: 自動で治療を選択

2. **老齢死イベント**
   - 年齢60以上 かつ 健康値10未満で発生
   - 大名が死亡した場合、後継者を選定

### プレイヤーとAIの違い

**プレイヤー大名**:
- イベントを`pending_events`に追加
- UI側で選択肢を表示（[main.py:260-310](main.py#L260-L310)）
- プレイヤーの選択を待つ

**AI大名**:
- イベントを自動処理
- 最適な選択を自動的に実行

### 後継者選定ロジック

大名が死亡した場合（[core/turn_manager.py:193-213](core/turn_manager.py#L193-L213)）:

```
1. 死亡大名の全領地を取得
2. 最も能力値の高い武将を選出:
   - 戦闘力 + 統率力 + 政治力 + 知力 の合計値で評価
3. 選出された武将を新大名に昇格:
   - 武将リストから削除
   - 大名リストに追加
   - 全領地の所有権を移譲
```

---

## Phase 5: プレイヤーコマンド受付

**実行タイミング**: Phase 4直後
**実装場所**: [core/turn_manager.py:216-221](core/turn_manager.py#L216-L221)

### 処理内容

**このフェーズではTurnManager側では何も処理しません。**

実際のプレイヤーコマンド処理はUI側で行われます（[main.py:350-422](main.py#L350-L422)）:

1. プレイヤーが「出陣」「徴兵」などのコマンドをUIで選択
2. コマンドが実行される
3. 攻撃コマンドの場合:
   ```python
   # 戦闘をキューに追加
   battle = {
       "attacker_province_id": origin_province_id,
       "defender_province_id": target_province_id,
       "attack_force": attack_force,
       "general_id": general_id
   }
   self.turn_manager.pending_battles.append(battle)

   # ターンイベントに記録
   event_msg = f"【{daimyo.clan_name}】{origin_province.name}から{defender_name}の{target_province.name}へ出陣（兵力{attack_force}人）"
   self.turn_manager.turn_events.append(event_msg)
   ```

### 重要な特徴

- プレイヤーコマンドは`turn_events`に記録される
- 攻撃コマンドは`pending_battles`キューに追加される
- **この時点では戦闘は実行されない**（Phase 8で計算）

---

## Phase 6: AIコマンド実行

**実行タイミング**: Phase 5直後
**実装場所**: [core/turn_manager.py:223-228](core/turn_manager.py#L223-L228)

### 処理内容

全てのAI大名に対して、AIシステムがコマンドを自動実行します（[systems/ai.py:25-152](systems/ai.py#L25-L152)）。

### AI意思決定フロー

```
for 各AI大名:
    for 各領地:
        if 統治武将がいない:
            → 武将を自動配置

        戦略を決定:
            - 攻撃的: 隣接敵領地への攻撃
            - 守備的: 兵力が少ない場合は徴兵
            - 開発: 内政コマンド実行
```

### AI攻撃処理

AI大名が攻撃を決定した場合（[systems/ai.py:96-107](systems/ai.py#L96-L107)）:

```python
# 戦闘をキューに追加
battle = {
    "attacker_province_id": province.id,
    "defender_province_id": target_id,
    "attack_force": attack_force,
    "general_id": general_id
}
self.turn_manager.pending_battles.append(battle)

# イベント記録
event_msg = f"【{daimyo.clan_name}】{province.name}から{target_name}へ出陣（兵力{attack_force}）"
self.turn_manager.turn_events.append(event_msg)
```

### プレイヤーとの違い

- **プレイヤー**: UI操作で1コマンドずつ実行
- **AI**: 全領地を自動で判断して最適コマンドを実行

---

## Phase 7: 内政効果適用

**実行タイミング**: Phase 6直後
**実装場所**: [core/turn_manager.py:230-259](core/turn_manager.py#L230-L259)

### 処理内容

プレイヤーまたはAIが実行した内政コマンドの効果を適用します。

### 適用される効果

1. **開発投資**
   - 開発レベル +1（最大10）
   - 米生産量が向上

2. **町発展**
   - 町レベル +1（最大10）
   - 税収が向上

3. **治水工事**
   - 治水値 +10（最大100）
   - 災害被害を軽減

4. **訓練**
   - 兵士訓練度 +0.1（最大2.0）
   - 戦闘力が向上

### 処理順序

```
for 各大名 in alive大名:
    for 各領地 in 大名の領地:
        コマンドフラグをリセット
```

---

## Phase 8: 戦闘計算（結果未適用）

**実行タイミング**: Phase 7直後
**実装場所**: [core/turn_manager.py:321-413](core/turn_manager.py#L321-L413)

### **最重要ポイント**

Phase 8では戦闘結果を「計算」しますが、**この時点では結果は適用されません**。

コード内のコメント（[core/turn_manager.py:340-342](core/turn_manager.py#L340-L342)）:
```python
# 注意: この時点では戦闘結果は未適用なので、
#       現在の領地状態で計算される
```

### 処理フロー

```
for 各戦闘 in pending_battles:
    1. 攻撃側・防御側の情報を取得
    2. 戦闘を計算（systems/combat.py:resolve_battle）
    3. 結果を battle_results に格納
    4. turn_events に戦闘結果を記録
```

### 戦闘計算の詳細

戦闘は[systems/combat.py:39-108](systems/combat.py#L39-L108)で計算されます:

```python
def resolve_battle(
    attacker_province: Province,
    defender_province: Province,
    attack_force: int,
    general_id: Optional[int] = None
) -> dict:
    # 1. 基礎戦力計算
    攻撃力 = attack_force × 訓練度 × 士気補正 × 武将補正
    防御力 = 守備兵 × 訓練度 × 士気補正 × 地形補正 × 城補正

    # 2. 勝敗判定（確率的）
    if ランダム値 < 攻撃力 / (攻撃力 + 防御力):
        勝者 = 攻撃側
    else:
        勝者 = 防御側

    # 3. 損害計算
    攻撃側損害 = attack_force × ダメージ率
    防御側損害 = 守備兵 × ダメージ率

    # 4. 結果を辞書で返す
    return {
        "attacker_won": 勝敗,
        "attacker_casualties": 攻撃側損害,
        "defender_casualties": 防御側損害,
        ...
    }
```

### 結果の保存

計算された結果は`battle_results`リストに保存されます:

```python
self.battle_results.append({
    "attacker_province_id": attacker_province_id,
    "defender_province_id": defender_province_id,
    "attack_force": attack_force,
    "general_id": general_id,
    "result": result  # resolve_battleの返り値
})
```

---

## 戦闘結果の適用（Phase 8の後、UIでのアニメーション後）

**実行タイミング**: 戦闘アニメーション終了後
**実装場所**: [main.py:634-689](main.py#L634-L689)

### 処理フロー

```python
def on_battle_animation_finished(self):
    # 1. 現在の戦闘結果を取得
    current_battle = self.pending_battle_animations[self.current_battle_index]

    # 2. 戦闘結果を実際に適用
    self.combat_system.apply_battle_result(
        current_battle["result"],
        attacker_province,
        defender_province,
        current_battle["attack_force"],
        current_battle["general_id"]
    )

    # 3. 次の戦闘へ
    self.current_battle_index += 1

    # 4. 全戦闘終了後
    if 全戦闘完了:
        # 領地喪失による死亡判定
        self.turn_manager._phase_10_check_deaths()

        # デバッグログ出力（全結果適用後）
        if self.need_log_turn_state:
            self.log_turn_state()
            self.need_log_turn_state = False
```

### 戦闘結果適用の詳細

[systems/combat.py:110-148](systems/combat.py#L110-L148)で実装:

```python
def apply_battle_result(self, result: dict, ...):
    # 1. 損害を適用
    attacker_province.soldiers -= attacker_casualties
    defender_province.soldiers -= defender_casualties

    # 2. 勝者の処理
    if result["attacker_won"]:
        # 領地占領
        self._capture_province(defender_province, attacker_daimyo, general_id)

        # 敗北した武将を討ち取る
        if defender_general_id:
            del self.game_state.generals[defender_general_id]
    else:
        # 攻撃失敗
        if general_id:
            general.health -= 10  # 健康値減少
```

### 領地占領処理

[systems/combat.py:149-218](systems/combat.py#L149-L218)で実装:

```python
def _capture_province(self, province, new_owner_daimyo, conquering_general_id):
    old_owner_id = province.owner_daimyo_id

    # 1. 所有権変更
    province.owner_daimyo_id = new_owner_daimyo.id
    province.governor_general_id = conquering_general_id

    # 2. 旧所有者の領地リストを更新
    if old_owner_id:
        old_daimyo.provinces.remove(province.id)

    # 3. 新所有者の領地リストを更新
    new_owner_daimyo.provinces.append(province.id)

    # 4. 忠誠度・士気を低下
    province.peasant_loyalty = max(0, province.peasant_loyalty - 20)
    province.soldier_morale = max(0, province.soldier_morale - 10)
```

---

## 複数大名が同じ領地を攻撃する場合の処理

### シナリオ

```
大名A: 領地X を所有
大名B: 領地X を攻撃
大名C: 領地X を攻撃
```

### Phase 5-6: 戦闘キューへの追加

```python
pending_battles = [
    {
        "attacker": B,
        "defender": X (所有者: A),
        "attack_force": 1000,
        ...
    },
    {
        "attacker": C,
        "defender": X (所有者: A),
        "attack_force": 800,
        ...
    }
]
```

### Phase 8: 戦闘計算

**重要**: 両方の戦闘とも、**ターン開始時の領地X（所有者: A）**の状態で計算されます。

```python
# 戦闘1: B vs A（領地X）
result_1 = resolve_battle(
    attacker = B,
    defender = X (owner: A, soldiers: 500)  # ← 初期状態
)
# 結果: Bが勝利、Aの兵500 → 200

# 戦闘2: C vs A（領地X）
result_2 = resolve_battle(
    attacker = C,
    defender = X (owner: A, soldiers: 500)  # ← 同じ初期状態
)
# 結果: Cが勝利、Aの兵500 → 100
```

**この時点ではまだ結果は適用されていない**ため、戦闘2も「Aが所有する領地X（兵力500）」に対する攻撃として計算されます。

### アニメーション後: 結果適用（順次）

```python
# 1. 戦闘1の結果を適用
apply_battle_result(result_1)
→ 領地Xの所有者: A → B
→ 領地Xの兵力: 500 → 200
→ Bの領地リスト: [..., X]
→ Aの領地リスト: [X削除]

# 2. 戦闘2の結果を適用
apply_battle_result(result_2)
→ 領地Xの所有者: B → C  # ← ここで上書き！
→ 領地Xの兵力: 200 → 100
→ Cの領地リスト: [..., X]
→ Bの領地リスト: [X削除]  # ← せっかく得た領地を即失う
```

### 結果

- **最終的な所有者**: 大名C
- **戦闘1で勝利した大名B**: 一瞬所有するが、すぐにCに奪われる
- **元の所有者A**: 2回攻撃を受けたが、戦闘計算上は1回分の損害のみ

### 論理的問題点

1. **Bの立場**: 戦闘に勝利して領地を得たのに、即座に失う
2. **Cの立場**: 実際には「Bの領地」を攻撃したことになる（計算時はAだったが）
3. **Aの立場**: 2つの軍に攻撃されたが、兵力損害は最後の戦闘結果のみ反映

### 現在の仕様

この動作は**仕様通り**です。ゲームデザイン上、以下のような解釈が可能です:

- 複数の軍が同時に攻撃した場合、最後に到着した軍が領地を占領する
- 先に到着した軍は、後から来た軍に領地を奪われる可能性がある

### 改善案（実装されていない）

より現実的にする場合:

1. **戦闘順序の決定**: 攻撃力や距離で戦闘順序を決める
2. **逐次計算**: 戦闘1の結果を適用してから戦闘2を計算
3. **連合戦**: 複数攻撃者を1つの連合軍として扱う

---

## Phase 9: ターン終了処理

**実行タイミング**: Phase 8直後
**実装場所**: [core/turn_manager.py:415-459](core/turn_manager.py#L415-L459)

### 処理内容

各領地の状態を更新します。

```
for 各大名 in alive大名:
    for 各領地 in 大名の領地:
        # 1. 忠誠度の自然回復
        if 忠誠度 < 50:
            忠誠度 += 2

        # 2. 士気の自然回復
        if 士気 < 70:
            士気 += 5

        # 3. 農民の自然増加
        if 農民 < 最大農民:
            増加数 = max_peasants × 0.02
            農民 += 増加数
```

---

## Phase 10: 死亡判定

**実行タイミング**: Phase 9直後（通常）、または全戦闘結果適用後
**実装場所**: [core/turn_manager.py:461-505](core/turn_manager.py#L461-L505)

### 処理内容

領地を全て失った大名を滅亡させます。

```python
def _phase_10_check_deaths(self):
    for daimyo in alive大名:
        if len(daimyo.provinces) == 0:
            # 領地喪失による滅亡
            daimyo.alive = False
            daimyo.cause_of_death = "territory_loss"

            # 全武将も失う
            for general_id in 大名配下の武将:
                general.daimyo_id = None

            # イベント記録
            turn_events.append(f"{daimyo.clan_name}家滅亡")
```

### 実行タイミングの特殊性

Phase 10は2箇所で呼ばれます:

1. **通常のターン処理**: [core/turn_manager.py:65](core/turn_manager.py#L65)
2. **戦闘結果適用後**: [main.py:681](main.py#L681)

これは、戦闘で領地を全て失った大名を正しく検出するためです。

---

## Phase 11: 勝利条件判定

**実行タイミング**: Phase 10直後
**実装場所**: [core/turn_manager.py:507-558](core/turn_manager.py#L507-L558)

### 勝利条件（4種類）

1. **Complete Control（完全統一）**
   - 1人の大名が全領地を支配

2. **Dominant Power（優勢勝利）**
   - 1人の大名が80%以上の領地を支配

3. **Eliminate All Rivals（全敵排除）**
   - 生存大名が1人のみ

4. **Turn Limit（ターン制限）**
   - 最大ターン数に到達（未実装）

### 判定結果

いずれかの条件を満たした場合:

```python
self.game_over = True
self.victory_daimyo_id = winner_id
turn_events.append(f"【{winner.clan_name}】天下統一達成！")
```

---

## 戦闘状況の表示タイミング

**実装場所**: [main.py:427-633](main.py#L427-L633), [ui/battle_preview.py](ui/battle_preview.py), [ui/battle_animation.py](ui/battle_animation.py)

### 実行タイミング

戦闘演出は**Phase 11終了後、UIに制御が戻った後**に実行されます。

```
Phase 11: 勝利条件判定（TurnManager内）
  ↓
execute_turn() 終了（main.py:429）
  ↓
end_turn() の続き（main.py:431-455）
  ├─ ターンイベントを取得
  ├─ 戦闘結果の有無を確認
  └─ 戦闘ありの場合 → show_next_battle() 呼び出し
  ↓
【ここから戦闘演出ループ開始】
```

**重要**: TurnManagerの11フェーズは全て完了しており、戦闘計算（Phase 8）も終わっています。戦闘演出はあくまで「結果の視覚化と適用」のためのUI処理です。

### 表示フロー

戦闘の視覚的表示は、以下の3段階で行われます:

```
Phase 8終了（戦闘計算完了）
  ↓
[UIへ戻る]
  ↓
1. 戦闘プレビュー（BattlePreviewScreen）
   - 勢力図上で攻撃経路をアニメーション表示
   - 攻撃側→防御側への矢印アニメーション
   - 期間: 80フレーム（約2.7秒 at 30FPS）
  ↓
2. 戦闘アニメーション（BattleAnimationScreen）
   - 戦闘の詳細をアニメーション表示
   - 4つのフェーズで構成
   - 期間: 300フレーム（約10秒 at 30FPS）
  ↓
3. 戦闘結果の適用（apply_battle_result）
   - 領地所有権の変更
   - 兵力の損害反映
   - 武将の討死処理
  ↓
次の戦闘へ（または全戦闘完了）
```

### 1. 戦闘プレビュー画面

**実装**: [ui/battle_preview.py](ui/battle_preview.py)
**表示タイミング**: 各戦闘の直前
**期間**: 80フレーム

#### アニメーションフェーズ

```python
# Phase 1 (0-60フレーム): 攻撃経路アニメーション
- 勢力図を背景に表示
- 攻撃側領地から防御側領地への矢印を描画
- 矢印が徐々に伸びるアニメーション

# Phase 2 (60-80フレーム): 戦闘準備
- 矢印が完成した状態で静止
- 「vs」テキスト表示
- 「スペース/クリックでスキップ」表示
```

#### 表示内容

- **背景**: 勢力図（各領地の所有者を色分け表示）
- **矢印**: 攻撃経路（赤色の矢印）
- **テキスト**:
  - 「【大名名】 vs 【大名名】」
  - 「【攻撃側領地名】 → 【防御側領地名】」
  - スキップ指示

#### スキップ機能

- スペースキーまたはマウスクリックでスキップ可能
- スキップすると即座に戦闘アニメーションへ

### 2. 戦闘アニメーション画面

**実装**: [ui/battle_animation.py](ui/battle_animation.py)
**表示タイミング**: プレビュー画面終了後
**期間**: 300フレーム（4フェーズ）

#### アニメーションフェーズ

```python
# Phase 0 (0-60フレーム): 準備フェーズ
- 背景のフェードイン
- 大名・武将の肖像画表示
- 兵力情報の表示
- 戦力バー: 両軍とも100%

# Phase 1 (60-100フレーム): 戦闘開始
- 「戦闘開始！」テキスト表示
- 画面シェイク効果
- 戦闘音再生

# Phase 2 (100-180フレーム): 交戦中
- 戦力バーが減少アニメーション
- 損害に応じてバーが減る
- フラッシュ効果（攻撃の演出）
- 画面シェイク継続

# Phase 3 (180-300フレーム): 結果表示
- 勝敗結果の表示
- 「【勝者名】の勝利！」
- 損害情報の表示
- 領地占領の場合は「【領地名】を占領！」
```

#### 表示内容

1. **肖像画**:
   - 攻撃側: 武将または大名の肖像（左側）
   - 防御側: 武将または大名の肖像（右側）
   - サイズ: 220x220ピクセル
   - 位置: 画面上部

2. **兵力情報**:
   ```
   【織田信長】          【斎藤道三】
   兵力: 1000           兵力: 800
   武将: 柴田勝家        武将: 竹中半兵衛
   ```

3. **戦力バー**:
   - 攻撃側: 赤色（左から右へ）
   - 防御側: 青色（右から左へ）
   - Phase 2で損害に応じて減少

4. **結果テキスト**:
   ```
   【織田信長】の勝利！

   損害:
     攻撃側: 200人
     防御側: 500人

   美濃を占領！
   ```

#### スキップ機能

- スペースキーまたはマウスクリックでスキップ可能
- スキップすると即座にPhase 3（結果表示）へジャンプ

### 3. 戦闘結果の適用

**実装**: [main.py:634-689](main.py#L634-L689), [systems/combat.py:110-218](systems/combat.py#L110-L218)
**タイミング**: 戦闘アニメーション終了後

#### 処理内容

```python
def on_battle_animation_finished(self):
    # 1. 戦闘結果を取得
    battle_data = self.pending_battle_animations[self.current_battle_index - 1]

    # 2. 戦闘結果を実際に適用
    combat_system.apply_battle_result(
        result,
        attacker_province,
        defender_province,
        attack_force,
        general_id
    )

    # 3. 次の戦闘へ
    self.current_battle_index += 1
    self.show_next_battle()
```

#### 適用される変更

1. **兵力の損害**:
   ```python
   attacker_province.soldiers -= attacker_casualties
   defender_province.soldiers -= defender_casualties
   ```

2. **領地占領**（攻撃側勝利の場合）:
   ```python
   # 所有権変更
   province.owner_daimyo_id = attacker_daimyo.id
   province.governor_general_id = conquering_general_id

   # 忠誠度・士気低下
   province.peasant_loyalty -= 20
   province.soldier_morale -= 10
   ```

3. **武将の討死**:
   ```python
   # 防御側武将が討ち取られる
   if defender_general_id:
       if config.DAIMYO_ID_MIN <= general_id <= config.DAIMYO_ID_MAX:
           # 大名の場合
           daimyo.is_alive = False
       elif config.GENERAL_ID_MIN <= general_id <= config.GENERAL_ID_MAX:
           # 武将の場合
           del self.game_state.generals[general_id]
   ```

### 複数戦闘がある場合の処理順序

```
戦闘1: プレビュー → アニメーション → 結果適用
  ↓
戦闘2: プレビュー → アニメーション → 結果適用
  ↓
戦闘3: プレビュー → アニメーション → 結果適用
  ↓
全戦闘完了
  ↓
Phase 10: 領地喪失による死亡判定（第2回）
  ↓
デバッグログ出力
  ↓
大名死亡演出（あれば）
  ↓
ターンメッセージ表示
```

### 重要な設計ポイント

1. **表示と処理の分離**:
   - Phase 8で全戦闘を計算
   - UI表示は1戦闘ずつ順次実行
   - 結果適用は各アニメーション終了後

2. **ユーザー体験の最適化**:
   - プレビュー画面で戦闘の文脈を把握
   - アニメーションで戦闘の過程を体感
   - スキップ機能で時間調整可能

3. **非同期処理**:
   - 各戦闘のアニメーションは独立
   - コールバック関数で次の処理へ連鎖
   - `on_finish`コールバックで制御フロー管理

### コールバックチェーン（戦闘演出ループの実装）

戦闘演出ループは、コールバック関数を使った再帰的な処理で実装されています。

```python
# main.py:427-633 での処理フロー

# ステップ1: ターン終了処理（end_turn）
end_turn()  # main.py:427
  ↓
  execute_turn()  # Phase 1～11を全て実行
  ↓
  戦闘結果を pending_battle_animations にコピー (main.py:450)
  ↓
  show_next_battle() を呼び出し (main.py:455)

# ステップ2: 戦闘演出ループ（再帰的に実行）
show_next_battle()  # main.py:588
  ↓
  if current_battle_index < len(pending_battle_animations):
    ↓
    battle_preview.show(
      on_finish=lambda: show_battle_animation()  # main.py:602
    )
    ↓
    [戦闘プレビュー表示 - 80フレーム]
    ↓
    show_battle_animation()  # main.py:630
    ↓
    battle_animation.show(
      on_finish=on_battle_animation_finished  # main.py:632
    )
    ↓
    [戦闘アニメーション表示 - 300フレーム]
    ↓
    on_battle_animation_finished()  # main.py:634
    ↓
    apply_battle_result()  # 結果適用 (main.py:641-677)
    ↓
    current_battle_index += 1  # 次の戦闘へ (main.py:679)
    ↓
    show_next_battle()  # 再帰呼び出し (main.py:688)
    ↓
  else:
    # 全戦闘完了
    ↓
    _phase_10_check_deaths()  # 領地喪失判定 (main.py:608)
    ↓
    log_turn_state()  # デバッグログ (main.py:611-613)
    ↓
    show_next_daimyo_death()  # 大名死亡演出 (main.py:620)
```

**重要な設計ポイント**:
- `show_next_battle()`は再帰的に自分自身を呼び出す
- `current_battle_index`で進捗を管理
- コールバック関数でアニメーション終了を待ってから次へ進む
- 全戦闘完了時（else節）にループを抜ける

---

## デバッグログ出力

**実装場所**: [main.py:477-578](main.py#L477-L578)

### 出力タイミング

デバッグログは、**全ての戦闘結果が適用された後**に出力されます。

```python
# main.py:474-475
if config.DEBUG_MODE:
    self.need_log_turn_state = True

# main.py:604-607 (全戦闘終了後)
if self.need_log_turn_state:
    self.log_turn_state()
    self.need_log_turn_state = False
```

### 出力内容

```
=== Turn N State ===

【大名情報】
  織田信長 (alive): Age 26, Health 95, Provinces 3

【領地情報】
  尾張 (Owner: 織田信長)
    Peasants: 4000, Loyalty: 50
    Soldiers: 1200, Morale: 70
    Gold: 800, Rice: 500

【戦闘情報】
  織田信長 vs 斎藤道三（美濃）
    攻撃兵力: 1000
    損害: 攻撃側 200, 防御側 300
    結果: 勝利 → 美濃占領
```

---

## まとめ: 1ターンの時系列

```
[ターン開始]
  ↓
Phase 1: ターン開始、加齢処理（春のみ）
  - 年齢+1
  - 年齢に応じた健康減少（確率的）
  - 健康0で自然死判定
  - 大名死亡 → pending_daimyo_deaths に追加（全戦闘後に演出表示）
  - 武将死亡 → turn_events に追加（ターン終了時にメッセージ表示）
  ↓
Phase 2: ランダムイベント抽選
  ↓
Phase 3: 税収・米生産
  ↓
Phase 4: イベント実行（プレイヤー選択 or AI自動）
  ↓
Phase 5: プレイヤーコマンド（UI）
  ├→ 攻撃コマンド → pending_battles に追加（Phase 8で計算）
  └→ 内政コマンド → 実行
  ↓
Phase 6: AIコマンド
  ├→ 攻撃コマンド → pending_battles に追加（Phase 8で計算）
  └→ 内政コマンド → 実行
  ↓
Phase 7: 内政効果適用
  ↓
Phase 8: 戦闘計算（結果未適用）
  ├→ pending_battles 内の全戦闘を計算
  │   - 各戦闘について resolve_battle() を呼び出し
  │   - 全て「ターン開始時の領地状態」で計算
  │   - この時点では領地所有権や兵力は変更されない
  └→ battle_results に結果を保存（戦闘演出ループで使用）
  ↓
Phase 9: 忠誠度・士気回復、農民増加
  ↓
Phase 10: 領地喪失による死亡判定（第1回）
  ↓
Phase 11: 勝利条件判定
  ↓
[TurnManager処理完了 - UIへ制御が戻る]
  ↓
[main.py:end_turn()の続き]
  ↓
戦闘結果の有無を確認
  ├─ 戦闘あり → 戦闘演出ループ開始
  └─ 戦闘なし → メッセージ表示へ
  ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━
【戦闘演出ループ】（main.py:show_next_battle）
各戦闘ごとに以下を繰り返し:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓
  戦闘プレビュー画面（80フレーム）
    - 勢力図表示
    - 攻撃経路アニメーション
    - スペース/クリックでスキップ可能
  ↓
  戦闘アニメーション画面（300フレーム）
    Phase 0: 準備（肖像画・兵力表示）
    Phase 1: 戦闘開始（画面シェイク）
    Phase 2: 交戦中（戦力バー減少）
    Phase 3: 結果表示（勝敗・損害表示）
    - スペース/クリックでPhase 3へスキップ可能
  ↓
  戦闘結果適用（apply_battle_result）
    - 兵力損害反映
    - 領地所有権変更
    - 武将討死処理
  ↓
  次の戦闘へ（または全戦闘完了へ）
━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓
[全戦闘完了]
  ↓
Phase 10: 領地喪失による死亡判定（第2回）
  ↓
デバッグログ出力（DEBUG_MODE時）
  ↓
大名死亡演出（あれば）
  - Phase 1の自然死（老衰）
  - 戦闘での討死（combat.py）
  ↓
ターンメッセージ表示
  ↓
[ターン終了]
```

---

## 重要な設計上の注意点

1. **戦闘計算と適用の分離**
   - Phase 8で計算、アニメーション後に適用
   - 全ての戦闘は「ターン開始時の状態」で計算される
   - **Phase 8とPhase 11の間に戦闘演出は実行されない**（全Phase完了後）

2. **戦闘演出ループの実行タイミング**
   - TurnManagerの11フェーズが全て完了した後
   - `execute_turn()`から制御がUIに戻った後
   - `show_next_battle()`の再帰呼び出しで実装
   - 各戦闘のアニメーション終了ごとに結果を適用

3. **イベント処理の非同期性**
   - プレイヤーイベントは`pending_events`経由でUI待機
   - AIイベントは即座に自動処理

4. **プレイヤーコマンドの保存**
   - `execute_turn()`開始時に保存、Phase 1後に復元
   - これにより、UIで入力したコマンドが消えない

5. **死亡判定の2回実行**
   - Phase 10で通常判定（execute_turn内）
   - 全戦闘適用後に再度判定（UI側で呼び出し）
   - 戦闘で領地を失った大名を正しく検出するため

6. **デバッグログの遅延出力**
   - `need_log_turn_state`フラグで制御
   - 全戦闘結果適用後に出力
   - 戦闘がない場合は即座に出力

---

## ファイル参照

- **ターン管理**: [core/turn_manager.py](core/turn_manager.py)
- **UI・アニメーション**: [main.py](main.py)
- **戦闘処理**: [systems/combat.py](systems/combat.py)
- **AI処理**: [systems/ai.py](systems/ai.py)
- **領地モデル**: [models/province.py](models/province.py)
- **大名モデル**: [models/daimyo.py](models/daimyo.py)
- **武将モデル**: [models/general.py](models/general.py)

このドキュメントは、現在のプログラムの実装を正確に反映しています。
