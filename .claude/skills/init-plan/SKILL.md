---
name: init-plan
description: 天翔十字フローで新規 Phase 着手時にイニシャルプラン (v1) 雛形を生成し、project-local .claude/plans/phase_{N}_plan_v1.md に書き出して phase_state.json を新 Phase 用に atomic 更新する。
when_to_use: |
  - 新しい Phase に着手する指示を受けた時 (例:「Phase 1 はじめよう」「Phase 2 着手」「次の Phase 始める」「init plan」)
  - イニシャルプラン作成・新 Phase 開始時の雛形が必要な時
  - Step 0 → Phase 1 (撤退) のように Phase 境界を越える時
---

# Skill: init-plan

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- `.claude/phase_state.json` が存在し、UserPromptSubmit hook で Phase 情報が context に注入されている

## 動作

### Step 1: ユーザーから着手 Phase を確認

- Phase 番号 (例: 1, 2, ...)
- シンプルゴール (= 当 Phase 完了時に達成される一文、不変項目)
- N (= ステップ数、3 / 5 / 7 から選ぶ。確定後変更不可)

未指定なら確認質問する。

### Step 2: イニシャルプラン v1 を生成

以下構成で `.claude/plans/phase_{N}_plan_v1.md` を Write する:

```markdown
# Phase {N} イニシャルプラン (v1)

> **位置付け**: Phase {N} 着手時のイニシャルプラン。
> **作成日**: {YYYY-MM-DD}
> **シンプルゴール**: {不変}
> **N**: {3 or 5 or 7}

## 1. 背景

(ユーザーから受けた指示の要約 + envPlan / 上位プランからの位置付け)

## 2. Sub-Step 詳細像

| Sub-Step | 内容 | 完了判定 |
|---|---|---|
| **{N}-1: ...** | ... | ... |
| **{N}-2: ...** | ... | ... |
| ... | ... | ... |

## 3. 踊り場

- {N}-1 完了 → 評価 → v2 (= 残 N-1 ステップ向け詳細像更新) 承認 → {N}-2 着手
- ... (同様に)

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| ... | ... |

---

**再掲: 本ファイルは Phase {N} イニシャルプラン (v1)。承認後 {N}-1 着手。**
```

Sub-Step 詳細像と完了判定は、ユーザーから提供された要件 + 過去 Phase の経験から埋める。**不明箇所は推測で埋めず、ユーザーに確認質問**。

### Step 3: phase_state.json を atomic 更新

`scripts/dev_hooks/update_phase_state.py` を呼び、新 Phase 用に書き換える:

```bash
python3 scripts/dev_hooks/update_phase_state.py \
  phase={N} \
  phase_simple_goal="{シンプルゴール}" \
  phase_total_steps={N の数値} \
  sub_step_current="{N}-1" \
  sub_step_remaining={N-1} \
  latest_plan_path=".claude/plans/phase_{N}_plan_v1.md"
```

成功時は更新後 JSON が stdout に出る。失敗時は stderr を確認しユーザーに報告。

### Step 4: ユーザー承認待ち

- 生成したプランの主要ポイント (シンプルゴール / N / Sub-Step 名一覧) をユーザーへ提示
- 「承認いただけたら {N}-1 着手します」で止まる
- 自動で {N}-1 に進まない (天翔十字フロー §3.4 踊り場原則)

## 注意

- 書き出し先は **必ず project-local** `.claude/plans/`。`~/.claude/plans/` には書かない
- 既に同名ファイル (`phase_{N}_plan_v1.md`) があれば overwrite せず、ユーザーに上書き可否を確認
- シンプルゴールは「{N}-1 完了時」ではなく「Phase {N} 全体完了時」のもの
