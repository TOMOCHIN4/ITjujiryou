---
name: eval-phase
description: 天翔十字フローで Phase 完了時に成果物 (当 Phase の commit 範囲 + 変更ファイル) と完了判定を突き合わせ、✅/⚠️/❌ 表形式の評価レポートを返す。ファイル書き込みなし。
when_to_use: |
  - Phase が完了した時 (例:「Phase A 終わった、評価して」「Phase 評価」「eval phase」「Phase B 評価レポート」)
  - 次 Phase に進む前に直前 Phase の達成度を確認したい時
  - 完了判定を満たしているかの最終チェック
---

# Skill: eval-phase

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- 直近 Phase の作業 commit が存在する
- `.claude/phase_state.json` に現 Phase の情報がある

## 起動契機 (自動 / 手動)

本 skill は以下の 2 経路で起動する:

- **自動**: 当 Phase の完了判定を満たしたと Claude が判断した直後、ユーザーからの明示的な `/eval-phase` 呼出を待たずに、自発的に本 skill の Step 1 から実行する。「完了判定を満たした → ユーザーに承認を求める」までの導線を省略せず、評価レポート出力までを 1 ターンで完結させる。
- **手動**: ユーザーが `/eval-phase` を明示的に呼んだ時。再評価・後追い評価に使う。互換性のため slash command は残存する。

両経路とも skill 本文 (下記「動作」) のステップは同一。

## 動作

### Step 1: 評価対象の特定

`.claude/phase_state.json` を読み、現 Phase (= `phase_current`) を特定する。
ユーザーが「Phase A 評価して」のように明示している場合はそちらを優先。

評価対象プラン: `.claude/phase_state.json.latest_plan_path` (= `.claude/plans/phase_{ID}.md`)。
完了判定は当該 plan ファイルから抽出する。

### Step 2: 成果物の取得

以下を Bash で取得:

```bash
git log --pretty=format:"%H %s" -n 10
git diff --stat HEAD~N HEAD   # N = Phase 内の commit 数
```

当 Phase の commit 範囲 (= `init-plan` 直後から HEAD まで) を確認する。複数 commit にまたがる場合は範囲指定で `git log` する。

### Step 3: 完了判定との突き合わせ

評価対象プランの完了判定一覧を抽出し、各項目について以下を判定:

- ✅ 達成 (成果物 / 実機確認で根拠あり)
- ⚠️ 部分達成 / 未検証 (達成しているが実機テスト不足など)
- ❌ 未達

判定根拠を 1 行で添える (例:「commit abc1234 で `.claude/settings.json` 追加、JSON 検証 OK」)。

### Step 4: 実績から見えた論点抽出

- 計画外で発覚した制約
- 次 Phase に持ち越すべき宿題 (= 次 Phase の `init-plan` 入力)
- プラン文書の更新が必要な箇所

### Step 5: 評価レポート出力

`.claude/phase_state.json.phase_remaining` を確認し、以下 2 系統のテンプレートを使い分ける。

**通常 Phase の場合 (`phase_remaining > 0`)**:

```markdown
## Phase {ID} 評価

### 完了判定

| 判定項目 | 結果 | 根拠 |
|---|---|---|
| ... | ✅ | ... |
| ... | ⚠️ | ... |

### 実績から見えた論点

1. ...
2. ...

### 次の動き

Phase {ID} 完了。次 Phase ({次の ID}) に進みますか？ 進む場合は **初回 Phase なら `/init-plan`、2 回目以降なら `/next-plan`** を呼んでください。
```

**最終 Phase の場合 (`phase_remaining == 0`)**:

```markdown
## Phase {ID} 評価 (最終 Phase)

### 完了判定

| 判定項目 | 結果 | 根拠 |
|---|---|---|
| ... | ✅ | ... |

### 実績から見えた論点

1. ...

### 次の動き

シンプルゴール達成 = 本フロー全体完了。続けて Step 6 で `phase_state.json` を凍結する。
```

### Step 6: 最終 Phase の自動 freeze (条件付き)

`.claude/phase_state.json.phase_remaining == 0` の場合のみ、評価レポート出力の **直後** に以下を実行:

```bash
python3 scripts/dev_hooks/freeze_phase_state.py --freeze
```

成功時は更新後 JSON が stdout に出る。失敗時は stderr を確認しユーザーに報告。

実行後、ユーザーに以下を案内する:

- `phase_state.json` が `phase_current="_frozen"` に凍結されたこと
- 次案件は **`/init-plan`** で立ち上げる順路 (この skill から `/init-plan` を自動起動はしない、ユーザー判断を残す)

`phase_remaining > 0` の通常 Phase 評価では本 Step は実行しない (= 次 Phase への遷移は `/next-plan` の責務であり、本 skill は触らない)。

## 重要

- **ファイル書き込みは原則禁止**。`.claude/phase_state.json` を触る唯一の例外が **Step 6 の最終 Phase 自動 freeze** であり、それも `freeze_phase_state.py` helper 経由 (= 物理ガード越し)。通常 Phase 評価ではいかなるファイルにも書き込まない
- 次 Phase 着手 (`/init-plan` / `/next-plan`) は本 skill の責務外、ユーザー判断に残す
- 推測で ✅ を付けない。根拠が弱いなら ⚠️ にする
- 完了判定が文書に書かれていなければ、その時点でユーザーに完了判定基準を確認する
- **Sub-Step / 踊り場 / v{M+1} の概念は天翔十字フローから廃止された**。評価は常に Phase 単位
- **天翔十字フロー本体・skill・hook・settings の改修は天翔十字フローを使わない**。本 skill はそういった整備案件には起動しない
