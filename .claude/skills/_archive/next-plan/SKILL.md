> ※ これは Sub-Step 廃止前の旧仕様。現役は `.claude/skills/next-plan/` を参照のこと (commit 98bf428 以降、Phase 単一実装単位化済)。

---
name: next-plan
description: 天翔十字フローの踊り場で次プラン (v{M+1}) を生成、project-local .claude/plans/phase_{N}_plan_v{M+1}.md に書き出して phase_state.json (sub_step_current / sub_step_remaining / latest_plan_path / updated_at) を atomic 更新する。
when_to_use: |
  - 直前 Sub-Step の評価が終わり、次プラン (= 残ステップ向け詳細像更新) が必要な時 (例:「次プラン作って」「セカンドプラン作成」「サードプラン作成」「next plan」「v3 作成」)
  - 踊り場 X 通過時の正式プラン文書を残したい時
  - 評価レポートで挙がった論点を次プランに吸収する時
---

# Skill: next-plan

## 前提

- 直前 Sub-Step の `/eval-step` 評価が完了している
- `.claude/phase_state.json` が現状を保持している
- 評価で抽出した論点 (実績から見えた制約・宿題) がユーザーと共有済み

## 動作

### Step 1: 現状の取得

`.claude/phase_state.json` を読み、以下を取得:
- 現 Phase 番号
- 現 Sub-Step (= 直前完了した Sub-Step)
- 残ステップ数
- 最新プランのパス (= 前 v{M} ファイル)

新プランは `v{M+1}`。次に進む Sub-Step (= 残ステップから 1 つ消化した次のもの) を決定。

### Step 2: 入力収集

- 評価レポート (= 直前 `/eval-step` の出力)
- 前プラン v{M} の §3 / §4 (= 残 Sub-Step の旧詳細像)
- 評価で挙がった論点 (吸収先を v{M+1} に明記する)

### Step 3: v{M+1} を生成

以下構成で `.claude/plans/phase_{N}_plan_v{M+1}.md` を Write する:

```markdown
# Phase {N} {セカンド|サード|...}プラン (v{M+1})

> **位置付け**: v{M} の改訂。Sub-Step {N}-{直前} 完了後の踊り場で作成。残り {残数} Sub-Step の詳細像を、{N}-{直前} 実績で見えた論点を吸収して更新する。
> **作成日**: {YYYY-MM-DD}
> **対象**: Sub-Step {N}-{次}{以降ある場合は続き}
> **不変**: シンプルゴール「{不変}」/ N={N の数値}

## 1. {N}-{直前} 実績サマリ

| 項目 | 結果 |
|---|---|
| 成果物 | ... |
| commit | ... |
| push | ... |
| 完了判定 | ... |

## 2. {N}-{直前} で見えた論点と v{M+1} での解決方針

| # | 論点 | 解決方針 |
|---|---|---|
| 1 | ... | ... |

## 3. Sub-Step {N}-{次}: ... (詳細像 v{M+1})

### 3.1 目的
...

### 3.2 成果物
| パス | 種別 | 内容 |
|---|---|---|
| ... | 新規 | ... |

### 3.3 完了判定
...

### 3.4 想定リスク
| リスク | 対処 |
|---|---|
| ... | ... |

## 4. (残 Sub-Step が複数あれば) Sub-Step {N}-{次の次}: ... (詳細像 v{M+1})
...

## 5. 踊り場 (残り) と次の動き
...

---

**再掲: 本ファイルは Phase {N} {セカンド|...}プラン (v{M+1})。承認後 {N}-{次} 着手。**
```

詳細像は前プラン v{M} を踏襲しつつ、評価論点を §2 に吸収する形で必ず明示。**不明箇所は推測で埋めず、ユーザーに確認質問**。

### Step 4: phase_state.json を atomic 更新

`scripts/dev_hooks/update_phase_state.py` を呼ぶ:

```bash
python3 scripts/dev_hooks/update_phase_state.py \
  sub_step_current="{N}-{次}" \
  sub_step_remaining={残数 - 1} \
  latest_plan_path=".claude/plans/phase_{N}_plan_v{M+1}.md"
```

成功時は更新後 JSON が stdout。失敗時は stderr を確認しユーザーへ報告。

### Step 5: ユーザー承認待ち

- v{M+1} の主要ポイント (吸収した論点 / 次 Sub-Step 詳細像 / 完了判定) を提示
- 「承認いただけたら {N}-{次} 着手します」で止まる
- 自動で {N}-{次} に進まない (天翔十字フロー §3.4 踊り場原則)

## 注意

- 書き出し先は **必ず project-local** `.claude/plans/`
- 既に同名 v{M+1} があれば overwrite せず確認
- シンプルゴールは Phase 全体のもの、Sub-Step ごとに書き換えない
- 評価論点 § が空でも、表自体は残す (「論点なし」とユーザーが確認できる状態にする)
