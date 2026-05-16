# envPlan — Step 0: 開発レイヤー環境整備

> **位置付け**: 愛帝十字陵システム本道 (5 ステップ) に着手する前の Step 0。「開発レイヤー (本 Claude Code セッション)」を **天翔十字フロー** で動かす環境を整える。
>
> **メタ的意義**: Step 0 自体を天翔十字フローで実行することで、ユウコ (オーケストレーター) 構築前にフローを「人間 ⇔ Claude Code」のペアで動かす実証実験となる。Step 1 以降 (= 愛帝十字陵本体構築) ではこの環境を使って作業する。
>
> **作成日**: 2026-05-16

---

## 1. 背景

### 1.1 レイヤーを分けない問題

現状の `.claude/` には個人用 `settings.local.json` と skills (gen-*) があるのみ。**開発レイヤー** (= 本セッションで愛帝十字陵を開発する作業) と **愛帝十字陵レイヤー** (= 案件運用する各 persona pane) を分離する規律も hook も存在しない。

このまま Step 1 (撤退) に入ると:
- 開発作業中に誤って愛帝十字陵レイヤーの設定 (旧 workspaces/) に手を出す
- 天翔十字フロー (= シンプルゴール + N + 詳細像) を守らずダラダラ進める
- どのステップにいるのか自分でも見失う

→ Step 0 で土台を整える。

### 1.2 レイヤー定義

| | 開発レイヤー | 愛帝十字陵レイヤー |
|---|---|---|
| **目的** | 愛帝十字陵システムの開発・改修 | 案件運用 (顧客対応 → 制作 → 納品) |
| **作業場所** | プロジェクト root (`.claude/settings.json` / `CLAUDE.md`) | `personas/{role}/` (新構成、Step 2 で構築) |
| **動作形態** | 1 Claude Code セッション (本セッション) | tmux 2 pane (orchestrator + executor、Step 2 以降) |
| **起動** | `claude` (cwd = project root) | (Step 2 で別途設計) |
| **フロー** | **天翔十字フロー** で動く | **普遍フロー (A→F + 踊り場 4 つ)** で動く |

両者は **別の「動き方」** を持つ。混同しない。

---

## 2. 天翔十字フロー (Step 0 で守る運用規律)

ユーザー指定:

```
1. ユーザーから指示を受ける
2. シンプルゴール設定 + 到達 N (3 / 5 / 7) を判断 + 詳細ゴールを含むイニシャルプラン作成
3. ユーザー承認
4. ステップ 1 実行
5. ステップ 1 終了後、Claude Code + ユーザーで評価
6. シンプルゴール + イニシャルプラン + 実績 + 残ステップから、セカンドプラン (1 ステップ減) 作成 → ユーザー承認
7. ステップ 2 実行
8. ... 同様に最終ステップまで
9. 設定ステップ数終了時にシンプルゴール達成
```

整理:

- **N は 3 / 5 / 7 から選ぶ** (案件規模で判断、確定後変更不可)
- **詳細ゴールはステップごとに更新** (1 ステップ減るたびにプラン再作成)
- **シンプルゴールは不変**
- **各ステップ終了時に評価 → 次プラン承認 → 次ステップ**

これが本セッションで以降必ず守るべき作業様式。

---

## 3. Step 0 自体の天翔十字フロー設定

### 3.1 Step 0 シンプルゴール

**「開発レイヤー (本セッション) が天翔十字フローで動く環境が整っている」**

### 3.2 Step 0 ステップ数

**N = 3** (最小単位で実証)

### 3.3 Step 0 イニシャルプラン (詳細ゴール)

| Sub-Step | 内容 | 完了判定 |
|---|---|---|
| **0-1: RULES** | `CLAUDE.md` 改訂 + レイヤー分離規律 + 天翔十字フロー定義の明文化 | プロジェクト level CLAUDE.md に天翔十字フロー規律が記述され、開発レイヤー作業時に常時参照可能 |
| **0-2: PERMISSION + HOOKS** | `.claude/settings.json` (commit対象) + hook スクリプト整備 | UserPromptSubmit hook が「現在のフェーズ + 残ステップ」を prompt 先頭に注入する。状態は `.claude/phase_state.json` で永続化 |
| **0-3: SKILLS** | `/init-plan` `/eval-step` `/next-plan` の 3 skill を `.claude/skills/` 配下に新設 | 各 skill が定型フォーマットで該当フェーズの文書を生成できる |

### 3.4 踊り場 (= 評価 + 次プラン承認)

- 0-1 完了 → 評価 → セカンドプラン (= 残り 2 ステップ向けに詳細像更新) 承認 → 0-2 着手
- 0-2 完了 → 評価 → サードプラン (= 残り 1 ステップ向けに詳細像更新) 承認 → 0-3 着手
- 0-3 完了 → シンプルゴール達成確認 → Step 0 完了

---

## 4. 各 Sub-Step の詳細仕様

### 4.1 Sub-Step 0-1: RULES

**目的**: 開発レイヤーと愛帝十字陵レイヤーの区別 + 天翔十字フロー規律を Claude Code 起動時に必ず読み込ませる。

**作成・改訂対象**:

- `CLAUDE.md` (プロジェクト root)
  - 既存 1 行 (「同階層の SPEC.md に必ず従う」) を残しつつ、以下を追加:
    1. レイヤー定義 (= §1.2 の表)
    2. 開発レイヤー作業時の規律
       - workspaces/ や旧 mcp_server に「設計上の理由なく」介入しない
       - 設計が決まるまで愛帝十字陵レイヤーには変更を加えない
    3. 天翔十字フロー定義 (= §2)
    4. 現在進行中の Phase 情報 (`.claude/phase_state.json` 参照を指示)
- `docs/development_layer_rules.md` (新規) — CLAUDE.md が肥大化する場合に切り出し先として用意

**完了判定**:

- 新しい Claude Code セッションを起動した時、CLAUDE.md (= 自動読込) で天翔十字フロー規律が見える
- 「いま何のステップを進行中か」を CLAUDE.md 経由で `.claude/phase_state.json` を参照させて把握できる

### 4.2 Sub-Step 0-2: PERMISSION + HOOKS

**目的**: 開発レイヤー専用の permission 集と、天翔十字フローを忘れさせない hook を整備。

**作成対象**:

- `.claude/settings.json` (新規、commit 対象、project-shared)
  - **permissions.allow**: 開発作業に必要な操作 (Edit/Write/Bash の主要セット、git, pytest, .venv/, etc)
  - **permissions.deny**: 不可逆操作 (`git push --force` / `rm -rf /` 系 / `--no-verify` / `--no-gpg-sign`)
  - **hooks.UserPromptSubmit**: `scripts/dev_hooks/inject_phase.py` を発火
- `scripts/dev_hooks/inject_phase.py` (新規)
  - `.claude/phase_state.json` を読み、現在の Phase / Sub-Step / 残ステップ数 / シンプルゴールを prompt 先頭に注入
  - フォーマット例:
    ```
    [Phase 0, Sub-Step 0-2 / 残 1 step]
    シンプルゴール: 開発レイヤーが天翔十字フローで動く環境が整っている
    詳細像 (現プラン版): ...
    ---
    (ユーザー prompt 本文)
    ```
- `.claude/phase_state.json` (新規、commit 対象)
  - スキーマ例:
    ```json
    {
      "phase": "0",
      "phase_simple_goal": "開発レイヤーが天翔十字フローで動く環境が整っている",
      "phase_total_steps": 3,
      "sub_step_current": "0-2",
      "sub_step_remaining": 1,
      "latest_plan_path": ".claude/plans/phase_0_plan_v2.md",
      "updated_at": "2026-05-16T..."
    }
    ```
- `.claude/plans/` (新規ディレクトリ、commit 対象)
  - 各踊り場で更新されるプランを `phase_{N}_plan_v{M}.md` で保存
  - 履歴として残す (vM は踊り場通過のたびに増える)

**完了判定**:

- 任意の prompt を投げると、自動で「現在 Phase X / Sub-Step Y / 残 Z step」が context に注入される
- `.claude/phase_state.json` が現在の状態を正しく保持

### 4.3 Sub-Step 0-3: SKILLS

**目的**: 天翔十字フロー上の典型作業 (初期プラン / 評価 / 次プラン) を skill 化して、構造を毎回手書きしないで済むようにする。

**作成対象**:

- `.claude/skills/init-plan/SKILL.md` (新規)
  - **trigger**: ユーザーから新規 Phase 着手指示を受けた時 (例: 「Phase 1 はじめよう」)
  - **動作**: シンプルゴール + N + イニシャルプラン (詳細ゴール含む) のテンプレを生成し、`.claude/plans/phase_{N}_plan_v1.md` として書き出す。ユーザー承認待ち
- `.claude/skills/eval-step/SKILL.md` (新規)
  - **trigger**: Sub-Step 完了時 (例: 「0-1 終わった、評価して」)
  - **動作**: 該当 Sub-Step の成果物・実績を整理し、評価レポートを返す。次プラン作成準備の入口
- `.claude/skills/next-plan/SKILL.md` (新規)
  - **trigger**: 評価完了後、次プラン作成指示を受けた時 (例: 「次プラン作って」)
  - **動作**: シンプルゴール + 実績 + 残ステップから新しいプランを生成し `.claude/plans/phase_{N}_plan_v{M+1}.md` として書き出す。ユーザー承認待ち

**完了判定**:

- 各 skill が `/init-plan` `/eval-step` `/next-plan` でユーザー操作から呼び出せる
- Step 1 (撤退) 着手時に `/init-plan` を呼んで Phase 1 のイニシャルプランを生成できる

---

## 5. ブランチ戦略

- Step 0 は別ブランチ `chore/step-0-env` で作業 (現在の `feat/yuko-3pipe` は議論メモを残して merge 戦略は Step 4 で決める)
- Step 0 完了時に `chore/step-0-env` を main に merge
- 以降 Step 1 (撤退) は別ブランチ `chore/step-1-retreat` を新規切り出し

---

## 6. 成果物 (Step 0 完了時に存在するもの)

```
.claude/
  settings.json              # 新規 (commit 対象)
  phase_state.json           # 新規 (commit 対象、Phase 進行状態の真実源)
  plans/                     # 新規
    phase_0_plan_v1.md       # Step 0 イニシャルプラン (= 本ファイル相当)
    phase_0_plan_v2.md       # 0-1 後の更新版
    phase_0_plan_v3.md       # 0-2 後の更新版
  skills/
    init-plan/SKILL.md       # 新規
    eval-step/SKILL.md       # 新規
    next-plan/SKILL.md       # 新規
    (既存 gen-* は触らない)
CLAUDE.md                    # 改訂 (レイヤー定義 + 天翔十字フロー規律 + phase_state 参照指示)
docs/
  development_layer_rules.md # 新規 (必要なら、CLAUDE.md 切り出し先)
scripts/
  dev_hooks/
    inject_phase.py          # 新規 (UserPromptSubmit hook)
envPlan.md                   # 本ファイル (Step 0 完了後は archived 扱い)
```

---

## 7. 想定リスクと対処

| リスク | 対処 |
|---|---|
| Step 0 自体が脱線して N=3 で着地しない | 各 Sub-Step ごとに必ず評価 → 次プラン承認 → 着手の手順を守る。Sub-Step 内部の作業に「もう一段の細分化」をしたくなったら、それは詳細像更新であって N の延長ではない |
| hook の不安定 (Python 環境問題等) で UserPromptSubmit が動かない | hook なしでも CLAUDE.md だけで規律保持可能。hook はあくまで「忘れさせない補助」。落ちても深刻でない |
| 既存 `.claude/settings.local.json` (個人用) と新 `.claude/settings.json` (project-shared) の競合 | settings.local が settings を上書きする標準仕様を確認。allow/deny が和集合で動作することを Sub-Step 0-2 で実機検証 |
| 開発レイヤー Hook が愛帝十字陵レイヤー (将来の persona pane) にまで波及 | persona pane は別 cwd で起動する想定なので、project root の `.claude/settings.json` が pane に継承されないように workspaces/personas 側で settings 上書きする (Step 2 で設計) |

---

## 8. Step 0 着手前確認事項 (2026-05-16 全項目確定)

| 項目 | 確定内容 |
|---|---|
| **ブランチ戦略** | `feat/yuko-3pipe` から分岐して `chore/step-0-env` を新規切り出し、Step 0 完了時に main へ merge。`feat/yuko-3pipe` は議論メモまでの状態で凍結 |
| **規律ドキュメント** | `docs/development_layer_rules.md` を独立ファイルとして作成、`CLAUDE.md` からは参照のみ記載 (CLAUDE.md は薄く保つ) |
| **hook 言語** | Python (`scripts/dev_hooks/inject_phase.py`)。既存 hook 群と統一 |
| **skill 形式** | `.claude/skills/{name}/SKILL.md` の Claude Code 標準形式 (既存 `gen-*` skill と同じ) |

---

## 9. Step 0 完了後の接続点

- 完了時点で Phase 1 (= 愛帝十字陵本道のステップ 1 = 撤退) の `/init-plan` 呼び出しが可能になる
- envPlan.md は Step 0 完了時に内容を `docs/archive/` に移動 (履歴保存)、root には残さない
- 開発レイヤー規律 (`CLAUDE.md`) + Phase 進行状態 (`.claude/phase_state.json`) + フロー支援 skill (`/init-plan` 等) が以降の Phase 1〜5 の作業全体を支える基盤になる

---

**再掲: 本プランは Step 0 のイニシャルプラン (v1) として位置付ける。0-1 完了後に評価し、v2 として 0-2 / 0-3 の詳細像を更新する。**
