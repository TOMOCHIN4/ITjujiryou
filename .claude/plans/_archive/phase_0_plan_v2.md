# Phase 0 セカンドプラン (v2)

> **位置付け**: Step 0 イニシャルプラン (= `envPlan.md`) の v2 改訂。Sub-Step 0-1 完了後の踊り場で作成。残り 2 Sub-Step (0-2 / 0-3) の詳細像を、0-1 実績で見えた論点を吸収して更新する。
>
> **作成日**: 2026-05-17 (踊り場 1: 0-1 評価後)
> **対象**: Sub-Step 0-2 (PERMISSION + HOOKS) / Sub-Step 0-3 (SKILLS)
> **不変**: シンプルゴール「開発レイヤーが天翔十字フローで動く環境が整っている」/ N=3

---

## 1. 0-1 実績サマリ

| 項目 | 結果 |
|---|---|
| 成果物 | `docs/development_layer_rules.md` 新規 (90 lines) / `CLAUDE.md` 改訂 (7 lines) |
| commit | `9d8d19f docs(step-0-1): 開発レイヤー規律ドキュメント新設 + CLAUDE.md 参照化` |
| push | `origin/chore/step-0-env` 反映済 |
| envPlan §4.1 完了判定 | ✅ 達成 (規律本文への導線 + Phase 状態参照導線あり) |

## 2. 0-1 で見えた論点と v2 での解決方針

| # | 論点 | v2 解決方針 |
|---|---|---|
| 1 | Claude Code plan mode が plans を `~/.claude/plans/{random}.md` に自動生成 → project-local `.claude/plans/phase_{N}_plan_v{M}.md` 命名と乖離 | **project-local `.claude/plans/` を真実源**と確定。global plan は drafting buffer 扱い。0-3 の `/init-plan` / `/next-plan` skill で project-local に書き出す動作にする |
| 2 | `docs/development_layer_rules.md` §4 に書いた「未整備時 fallback (`envPlan.md` / `.claude/plans/`)」記述は 0-2 完了後に陳腐化 | **0-2 完了時に §4 を改訂**し、`.claude/phase_state.json` が真実源である旨だけ残す (fallback 段落削除) |
| 3 | `envPlan.md` §6 のパス記述と現実運用の整合 | envPlan.md は Step 0 完了時 archive 対象なので §6 は触らない。現実運用は `docs/development_layer_rules.md` に集約済 (§3.3 で版数管理ルール記載済) |

---

## 3. Sub-Step 0-2: PERMISSION + HOOKS (詳細像 v2)

### 3.1 目的

開発レイヤー専用の permission 集と、天翔十字フローを忘れさせない UserPromptSubmit hook を整備。Phase 進行状態を機械可読の真実源 (`.claude/phase_state.json`) に確定させる。

### 3.2 成果物

| パス | 種別 | 内容 |
|---|---|---|
| `.claude/settings.json` | 新規 (commit対象) | permissions.allow / deny + hooks.UserPromptSubmit |
| `.claude/phase_state.json` | 新規 (commit対象) | Phase 進行状態の真実源 |
| `scripts/dev_hooks/inject_phase.py` | 新規 (commit対象) | UserPromptSubmit hook 本体 |
| `.claude/plans/phase_0_plan_v1.md` | 新規 | envPlan.md と同期したコピー (履歴起点として置く) |
| `.claude/plans/phase_0_plan_v2.md` | 新規 (本ファイル) | 既に存在 |
| `docs/development_layer_rules.md` | 改訂 | §4 fallback 段落削除 + §3.3 文言調整 |

### 3.3 各成果物の詳細

**`.claude/settings.json`**:
- `permissions.allow`:
  - Edit / Write (project root 配下)
  - Bash: `git status` / `git diff` / `git log` / `git add` / `git commit` / `git push origin chore/step-0-env` / `git fetch` / `python3 scripts/dev_hooks/*.py` / `ls` / `cat` / `grep` / `find`
  - その他開発作業に必要な read-only 系
- `permissions.deny`:
  - `Bash(git push --force*)` / `Bash(git push -f*)`
  - `Bash(rm -rf /*)` / `Bash(rm -rf ~*)`
  - `Bash(*--no-verify*)` / `Bash(*--no-gpg-sign*)`
  - `Bash(git reset --hard*)` (sub-step 完了時の特例運用は事前承認)
- `hooks.UserPromptSubmit`:
  ```json
  {
    "UserPromptSubmit": [
      {
        "command": "python3 ${CLAUDE_PROJECT_DIR}/scripts/dev_hooks/inject_phase.py"
      }
    ]
  }
  ```
- 既存 `.claude/settings.local.json` (個人 / .gitignore 済) との和集合動作を実機検証。

**`.claude/phase_state.json` 初期値**:
```json
{
  "phase": "0",
  "phase_simple_goal": "開発レイヤーが天翔十字フローで動く環境が整っている",
  "phase_total_steps": 3,
  "sub_step_current": "0-2",
  "sub_step_remaining": 1,
  "latest_plan_path": ".claude/plans/phase_0_plan_v2.md",
  "updated_at": "2026-05-17T00:00:00+09:00"
}
```

**`scripts/dev_hooks/inject_phase.py`**:
- stdin から hook 入力 (JSON) を受け取り、`additionalContext` フィールドで Phase 情報を返す UserPromptSubmit hook。
- 動作:
  1. `.claude/phase_state.json` を読み、欠損時は空文字を出力して exit 0
  2. テンプレに沿って Phase / Sub-Step / 残ステップ / シンプルゴール / latest_plan_path を整形
  3. stdout に JSON で `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}` を出力
- 出力テンプレ例:
  ```
  [Phase 0, Sub-Step 0-2 / 残 1 step]
  シンプルゴール: 開発レイヤーが天翔十字フローで動く環境が整っている
  最新プラン: .claude/plans/phase_0_plan_v2.md
  ```
- 例外時は stderr に短文出してプロセス成功 (= 開発作業を止めない、envPlan §7 想定リスク欄に準拠)。

**`.claude/plans/phase_0_plan_v1.md`**:
- `envPlan.md` の現スナップショットをそのままコピー。今後 envPlan.md と内容が乖離した場合は v1 のほうが「Step 0 着手時の状態」を表す。

**`docs/development_layer_rules.md` §4 改訂**:
- 「`.claude/phase_state.json` が真実源」のみ残す
- 「未整備の暫定段階では...」段落 (= 現状の fallback 案内) を削除
- §3.3 の版数管理は「project-local `.claude/plans/` に書く」と明示

### 3.4 完了判定

- 任意 prompt を投下すると context 先頭に Phase 情報が注入される (実機確認)
- `python3 scripts/dev_hooks/inject_phase.py < sample.json` で正しい JSON が返る
- `.claude/phase_state.json` が現在状態を正しく保持 (0-2 着手時点では `sub_step_current: "0-2"`, 完了 commit 後に 0-3 へ更新)
- `.claude/plans/v1.md` と `v2.md` が並んでいる
- `docs/development_layer_rules.md` §4 から fallback 段落が消えている
- `.claude/settings.json` の deny ルールが想定通り発火する (代表 1 件を実機で当てる)

### 3.5 想定リスク

| リスク | 対処 |
|---|---|
| hook の Python 環境問題で UserPromptSubmit が落ちる | hook 内部で全例外 catch + stderr に短文 + exit 0。Phase 情報なしでも作業継続できる |
| permission の `${CLAUDE_PROJECT_DIR}` 展開が permission rule で効かない (memory: feedback_permission_rule_glob_format) | hook の `command` は環境変数展開される側 (settings.json hooks フィールド)。permission rule (allow/deny の path) では `${CLAUDE_PROJECT_DIR}` を使わず相対パス or `//abs` 形式に倒す |
| `settings.json` と `settings.local.json` の allow/deny 衝突 | 実機で「片方 allow / 片方 deny」のケースを 1 件試して合算挙動を確認 |
| 既存 `.claude/settings.local.json` を上書き / 破壊 | settings.local には触らない。settings.json を新設するだけ |

---

## 4. Sub-Step 0-3: SKILLS (詳細像 v2)

### 4.1 目的

天翔十字フロー上の典型作業 (初期プラン / 評価 / 次プラン作成) を skill 化し、毎回手書きの構造化を不要にする。project-local `.claude/plans/` への書き出しを skill で吸収して、Claude Code plan mode との二重管理を解消する。

### 4.2 成果物

| パス | trigger | 動作要旨 |
|---|---|---|
| `.claude/skills/init-plan/SKILL.md` | 新規 Phase 着手指示 (例: 「Phase 1 はじめよう」) | シンプルゴール + N + イニシャルプラン雛形を生成 → `.claude/plans/phase_{N}_plan_v1.md` に書き出し → `.claude/phase_state.json` を更新 → ユーザー承認待ち |
| `.claude/skills/eval-step/SKILL.md` | Sub-Step 完了時 (例: 「0-1 終わった、評価して」) | 該当 Sub-Step の成果物 (git diff + 新規ファイル) を整理 → envPlan/v1/v2 の完了判定と突き合わせ → 評価レポート出力 |
| `.claude/skills/next-plan/SKILL.md` | 評価後の次プラン作成指示 (例: 「次プラン作って」) | シンプルゴール + 0-1..N 実績 + 残ステップから新プランを生成 → `.claude/plans/phase_{N}_plan_v{M+1}.md` に書き出し → `.claude/phase_state.json` の `latest_plan_path` 更新 → ユーザー承認待ち |

### 4.3 skill 共通仕様

- **形式**: 既存 `gen-*` skill と同じ Claude Code 標準形式 (`SKILL.md` に frontmatter + 本文)。
- **書き出し先**: 必ず project-local `.claude/plans/`。`~/.claude/plans/` は触らない。
- **phase_state.json 連動**: 各 skill 完了時に `latest_plan_path` / `sub_step_current` / `sub_step_remaining` / `updated_at` を atomic に更新。
- **ユーザー承認待ちで止まる**: 自動で次 Sub-Step に進まない (envPlan §3.4 踊り場原則)。

### 4.4 完了判定

- `/init-plan` `/eval-step` `/next-plan` の 3 skill がユーザー操作から呼べる
- 各 skill が project-local `.claude/plans/` に対して書き込む (`~/.claude/plans/` には書かない)
- `/init-plan` を Phase 1 (撤退) 着手時に呼んで `.claude/plans/phase_1_plan_v1.md` が生成できる
- `/eval-step` を 0-3 完了時に呼んで 0-3 評価レポートが返る (自己 dogfood)
- `/next-plan` は Phase 0 では使う機会がない (もう v3 = サードプラン分しか作らないが、それは 0-2 完了後の踊り場で生成する想定なので 0-3 と並行ではない)

### 4.5 想定リスク

| リスク | 対処 |
|---|---|
| skill の trigger 文言が曖昧で発火しない | description に複数の言い回し例を列挙 (memory: subagent description のキーワード列挙パターン) |
| skill が phase_state.json を上書き破壊 | 書き込みは temp → rename の atomic 化、書き込み前に schema 検証 |
| `.claude/plans/` への書き込みが permission deny に引っかかる | 0-2 で `.claude/plans/**` を allow に明示 |

---

## 5. 踊り場 (残り) と次の動き

| 踊り場 | タイミング | 生成物 | 着手対象 |
|---|---|---|---|
| 踊り場 2 (= 本踊り場) | 0-1 完了直後 | **v2 (本ファイル)** | 0-2 |
| 踊り場 3 | 0-2 完了後 | サードプラン v3 (= 残り 1 Sub-Step 0-3 向け詳細像更新) | 0-3 |
| Step 0 完了確認 | 0-3 完了後 | (プランは作らない) | Phase 1 (撤退) 着手準備 |

---

## 6. 承認後の最初の動き (0-2 着手 1 手目)

1. `.claude/plans/phase_0_plan_v1.md` (= envPlan.md コピー) を Write
2. `.claude/phase_state.json` を Write (`sub_step_current: "0-2"`)
3. `scripts/dev_hooks/inject_phase.py` を Write
4. `.claude/settings.json` を Write (allow/deny + hook 登録)
5. 動作確認: `python3 scripts/dev_hooks/inject_phase.py < <(echo '{}')` で JSON 出力
6. `docs/development_layer_rules.md` §4 改訂 (fallback 段落削除)
7. commit + push

---

**再掲: 本ファイルは Phase 0 セカンドプラン (v2)。承認後 0-2 着手。0-2 完了時に v3 (サードプラン) を作成して 0-3 へ進む。**
