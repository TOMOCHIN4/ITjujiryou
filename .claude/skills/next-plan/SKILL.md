---
name: next-plan
description: 天翔十字フローで **2 回目以降の Phase 着手時** にプラン雛形を生成し、project-local .claude/plans/phase_{ID}.md に書き出して phase_state.json を次 Phase 用に atomic 更新する。シンプルゴール / 全 Phase 数 N は phase_state.json から継承して書き換えない。
when_to_use: |
  - 前 Phase の `/eval-phase` 完了後、次 Phase に進む指示を受けた時 (例:「Phase B 着手」「次の Phase 始める」「next plan」)
  - 2 回目以降の Phase 着手で plan 雛形が必要な時
  - **初回 Phase 着手は対象外** (= `/init-plan` を使う)
---

# Skill: next-plan

> **初回 Phase 着手なら `/init-plan` を使うこと**。本 skill は 2 回目以降の Phase 専用。

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- `.claude/phase_state.json` の `phase_current` が `_frozen` 以外 (= 進行中フロー)
- 直前 Phase の `/eval-phase` 評価が完了している
- UserPromptSubmit hook で Phase 情報が context に注入されている
- 天翔十字フローの基本ルール:
  - シンプルゴール + N 個の Phase だけ
  - **シンプルゴール / N はフロー全体不変** (本 skill は絶対に書き換えない)
  - **Phase 以外作るな** (Sub-Step / 踊り場 / v{M+1} プラン更新は禁止)
  - 各 Phase は単一の実装単位

## 動作

### Step 1: 現状の取得と次 Phase ID の決定

`.claude/phase_state.json` を読み、以下を取得:
- `phase_current` (= 直前完了した Phase ID)
- `phase_remaining` (= 残 Phase 数、本 Phase 着手前)
- `phase_simple_goal` (= シンプルゴール、**書き換えない**)
- `phase_total` (= 全 Phase 数 N、**書き換えない**)

次 Phase ID を機械的に決定:
- アルファベット系: `A → B`, `B → C`, ...
- 数字系: `1 → 2`, `2 → 3`, ...

**ユーザーがシンプルゴールや N の変更を要求しても無視する**。「フロー再設計の必要があるなら一度フローを凍結 (`freeze_phase_state.py --freeze`) してフロー外で改修してほしい」旨を伝えて停止する。

未指定で必要なのは:
- 当 Phase の完了判定 (= 当 Phase の終わりに何が成立すれば終わったと言えるか)

完了判定が未指定なら確認質問する。**Phase を Sub-Step 等に分割してはならない**。

### Step 2: プラン雛形を生成

以下構成で `.claude/plans/phase_{ID}.md` を Write する (シンプルゴール / N は phase_state.json から **転記** する。書き換えない):

```markdown
# Phase {ID} プラン

> **作成日**: {YYYY-MM-DD}
> **シンプルゴール (フロー全体)**: {phase_state.json から転記}
> **全 Phase 数 N**: {phase_state.json から転記}
> **当 Phase の位置**: {ID} / {N}

## 1. 背景

(ユーザーから受けた指示の要約 + 前 Phase からの引き継ぎ事項 / `/eval-phase` で挙がった論点の吸収)

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

完了判定とリスクは、ユーザーから提供された要件 + 前 Phase の評価論点から埋める。**不明箇所は推測で埋めず、ユーザーに確認質問**。

**禁止事項**:
- Sub-Step 表 / 詳細像表を作らない
- 「踊り場」節を作らない
- v1 / v2 等の版数を付けない (1 Phase = 1 ファイル)
- シンプルゴール / N を書き換えない (本 skill の Step 3 helper が物理的に拒否する)

### Step 3: phase_state.json を atomic 更新

`scripts/dev_hooks/advance_phase_state.py` を呼ぶ。**渡せるキーは 3 つだけ** (`phase_simple_goal` / `phase_total` を渡すと helper が exit 1 で拒否する):

```bash
python3 scripts/dev_hooks/advance_phase_state.py \
  phase_current={次 Phase ID} \
  phase_remaining={残 Phase 数 = phase_remaining - 1} \
  latest_plan_path=".claude/plans/phase_{次 Phase ID}.md"
```

成功時は更新後 JSON が stdout に出る。失敗時 (不変キー渡し / `_frozen` 状態など) は stderr を確認しユーザーに報告。

### Step 4: ユーザー承認待ち

- 生成したプランの主要ポイント (継承したシンプルゴール / N / 完了判定一覧) をユーザーへ提示
- 「承認いただけたら Phase {ID} 着手します」で止まる
- 自動で実装に進まない

## 注意

- 書き出し先は **必ず project-local** `.claude/plans/`。`~/.claude/plans/` には書かない
- 既に同名ファイル (`phase_{ID}.md`) があれば overwrite せず、ユーザーに上書き可否を確認
- **シンプルゴール / N は phase_state.json の値を絶対に書き換えない** (本 skill の責務外)
- **Sub-Step / 踊り場 / v{M+1} の概念は天翔十字フローから廃止された**。Phase 単位で考える
- **天翔十字フロー本体・skill・hook・settings の改修は天翔十字フローを使わない**。本 skill はそういった整備案件には起動しない
