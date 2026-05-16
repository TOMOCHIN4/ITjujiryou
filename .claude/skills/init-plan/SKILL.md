---
name: init-plan
description: 天翔十字フローで新規 Phase 着手時にプラン雛形を生成し、project-local .claude/plans/phase_{ID}.md に書き出して phase_state.json を新 Phase 用に atomic 更新する。
when_to_use: |
  - 新しい Phase に着手する指示を受けた時 (例:「Phase 1 はじめよう」「Phase B 着手」「次の Phase 始める」「init plan」)
  - Phase 着手時のプラン雛形が必要な時
  - 前 Phase の eval-phase 完了後、次 Phase に進む時
---

# Skill: init-plan

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- `.claude/phase_state.json` が存在し、UserPromptSubmit hook で Phase 情報が context に注入されている
- 天翔十字フローの基本ルール:
  - シンプルゴール + N 個の Phase だけ
  - **Phase 以外作るな** (Sub-Step / 踊り場 / v{M+1} プラン更新は禁止)
  - 各 Phase は単一の実装単位

## 動作

### Step 1: ユーザーから着手 Phase を確認

- Phase ID (例: A, B, C, 1, 2, ...)
- シンプルゴール (= フロー全体で達成される一文、全 Phase 不変)
  - 初回 Phase 着手時のみ確認、以降は phase_state.json から継承
- N (= 全 Phase 数、3 / 5 / 7 から選ぶ)
  - 初回 Phase 着手時のみ確認、以降は phase_state.json から継承
- 当 Phase の完了判定 (= 当 Phase の終わりに何が成立すれば終わったと言えるか)

未指定なら確認質問する。**Phase を Sub-Step 等に分割してはならない**。粒度が大きすぎるなら N の取り方を見直して Phase を切り直す。

### Step 2: プラン雛形を生成

以下構成で `.claude/plans/phase_{ID}.md` を Write する:

```markdown
# Phase {ID} プラン

> **作成日**: {YYYY-MM-DD}
> **シンプルゴール (フロー全体)**: {不変}
> **全 Phase 数 N**: {3 or 5 or 7}
> **当 Phase の位置**: {ID} / {N}

## 1. 背景

(ユーザーから受けた指示の要約 + 前 Phase からの引き継ぎ事項 / 上位プランからの位置付け)

## 2. 当 Phase の完了判定

- [ ] {判定項目 1}
- [ ] {判定項目 2}
- ...

## 3. 成果物

- {ファイル / commit / 動作結果 など、Phase 完了時に存在しているべきもの}

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| ... | ... |

---

**再掲: 本ファイルは Phase {ID} の単一プラン。承認後に着手し、完了したら `/eval-phase` で評価する。**
```

完了判定とリスクは、ユーザーから提供された要件 + 過去 Phase の経験から埋める。**不明箇所は推測で埋めず、ユーザーに確認質問**。

**禁止事項**:
- Sub-Step 表 / 詳細像表を作らない
- 「踊り場」節を作らない
- v1 / v2 等の版数を付けない (1 Phase = 1 ファイル、修正は同ファイル直接編集 + git 履歴で来歴管理)

### Step 3: phase_state.json を atomic 更新

`scripts/dev_hooks/update_phase_state.py` を呼び、新 Phase 用に書き換える:

```bash
python3 scripts/dev_hooks/update_phase_state.py \
  phase_current={ID} \
  phase_simple_goal="{シンプルゴール}" \
  phase_total={N の数値} \
  phase_remaining={残 Phase 数 = N - 当 Phase 位置} \
  latest_plan_path=".claude/plans/phase_{ID}.md"
```

成功時は更新後 JSON が stdout に出る。失敗時は stderr を確認しユーザーに報告。

### Step 4: ユーザー承認待ち

- 生成したプランの主要ポイント (シンプルゴール / N / 完了判定一覧) をユーザーへ提示
- 「承認いただけたら Phase {ID} 着手します」で止まる
- 自動で実装に進まない

## 注意

- 書き出し先は **必ず project-local** `.claude/plans/`。`~/.claude/plans/` には書かない
- 既に同名ファイル (`phase_{ID}.md`) があれば overwrite せず、ユーザーに上書き可否を確認
- シンプルゴールは「当 Phase 完了時」ではなく「フロー全体完了時」のもの
- **天翔十字フロー本体・skill・hook・settings の改修は天翔十字フローを使わない**。本 skill はそういった整備案件には起動しない
