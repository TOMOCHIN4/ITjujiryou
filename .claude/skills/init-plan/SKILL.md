---
name: init-plan
description: 天翔十字フローで **初回 Phase 着手時のみ** プラン雛形を生成し、project-local .claude/plans/phase_{ID}.md に書き出して phase_state.json を初回 Phase 用に atomic 初期化する。シンプルゴール / 全 Phase 数 N の確定はこの skill 限定。
when_to_use: |
  - フロー凍結状態 (`phase_state.json` の `phase_current="_frozen"`) から、初回 Phase を立ち上げる時 (例:「Phase A はじめよう」「Phase 1 着手」「init plan」)
  - 新しいフローの起点でシンプルゴール / N を確定したい時
  - **2 回目以降の Phase 着手は対象外** (= `/next-plan` を使う)
---

# Skill: init-plan

> **2 回目以降の Phase 着手なら `/next-plan` を使うこと**。本 skill は初回 Phase 専用。

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- `.claude/phase_state.json` の `phase_current` が `"_frozen"` (= フロー凍結中)
- 進行中フローがあれば init は helper 側で拒否される (本 skill ではフローを潰せない)
- 天翔十字フローの基本ルール:
  - シンプルゴール + N 個の Phase だけ
  - シンプルゴール / N は **本 skill で確定したらフロー終了まで不変** (`advance_phase_state.py` が物理的に書換不可)
  - **Phase 以外作るな** (Sub-Step / 踊り場 / v{M+1} プラン更新は禁止)
  - 各 Phase は単一の実装単位

## 動作

### Step 1: ユーザーから初回 Phase の情報を確認

初回 Phase 着手時に必ず確定する 4 項目:

- **Phase ID** (例: `A`, `1`)
- **シンプルゴール** (= フロー全体で達成される一文、全 Phase 不変)
- **N** (= 全 Phase 数、3 / 5 / 7 から選ぶ)
- 当 Phase の完了判定 (= 当 Phase の終わりに何が成立すれば終わったと言えるか)

未指定なら確認質問する。**Phase を Sub-Step 等に分割してはならない**。粒度が大きすぎるなら N の取り方を見直して Phase を切り直す。

シンプルゴール / N は本 skill でしか確定できない。フロー途中で変えたくなった場合は、`freeze_phase_state.py --freeze` でフローを凍結し、別案件 (フロー本体改修扱い、フロー外) で再設計してから `--unfreeze-to-init` で再起動する手順を取る。

### Step 2: プラン雛形を生成

以下構成で `.claude/plans/phase_{ID}.md` を Write する:

```markdown
# Phase {ID} プラン

> **作成日**: {YYYY-MM-DD}
> **シンプルゴール (フロー全体)**: {不変}
> **全 Phase 数 N**: {3 or 5 or 7}
> **当 Phase の位置**: {ID} / {N}

## 1. 背景

(ユーザーから受けた指示の要約 + フロー全体の位置付け)

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

完了判定とリスクは、ユーザーから提供された要件から埋める。**不明箇所は推測で埋めず、ユーザーに確認質問**。

**禁止事項**:
- Sub-Step 表 / 詳細像表を作らない
- 「踊り場」節を作らない
- v1 / v2 等の版数を付けない (1 Phase = 1 ファイル、修正は同ファイル直接編集 + git 履歴で来歴管理)

### Step 3: phase_state.json を atomic 初期化

`scripts/dev_hooks/init_phase_state.py` を呼ぶ。本 helper は既存 `phase_current` が `_frozen` 以外なら exit 1 で拒否する (= 進行中フローを潰さない物理ガード):

```bash
python3 scripts/dev_hooks/init_phase_state.py \
  phase_current={ID} \
  phase_simple_goal="{シンプルゴール}" \
  phase_total={N の数値} \
  phase_remaining={残 Phase 数 = N - 1} \
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
- **2 回目以降の Phase 着手は `/next-plan`**。本 skill で 2 回目以降を立ち上げようとしても helper が `_frozen` 判定で拒否する
- **天翔十字フロー本体・skill・hook・settings の改修は天翔十字フローを使わない**。本 skill はそういった整備案件には起動しない
