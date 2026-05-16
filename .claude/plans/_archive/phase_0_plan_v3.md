# Phase 0 サードプラン (v3)

> **位置付け**: Step 0 セカンドプラン (v2) の改訂。Sub-Step 0-2 完了後の踊り場で作成。残り 1 Sub-Step (0-3 SKILLS) の詳細像を、0-2 実績で見えた論点を吸収して更新する。
>
> **作成日**: 2026-05-17 (踊り場 2: 0-2 評価後)
> **対象**: Sub-Step 0-3 (SKILLS)
> **不変**: シンプルゴール「開発レイヤーが天翔十字フローで動く環境が整っている」/ N=3

---

## 1. 0-2 実績サマリ

| 項目 | 結果 |
|---|---|
| 成果物 | `.claude/settings.json` / `.claude/phase_state.json` / `scripts/dev_hooks/inject_phase.py` / `.claude/plans/v1` (envPlan コピー) / `.claude/plans/v2` / `docs/development_layer_rules.md` §3.3 §4 改訂 / `CLAUDE.md` 微調整 |
| commit | `86267af feat(step-0-2): permission + UserPromptSubmit hook + phase_state 整備` |
| push | `9d8d19f..86267af` 反映済 |
| hook 即時発火 | ✅ 同一セッション内で `[Phase 0, Sub-Step 0-2 / 残 1 step]` 注入確認 |
| envPlan §4.2 完了判定 | ✅ 4/5 達成 (deny 実機検証のみ未) |

## 2. 0-2 で見えた論点と v3 での解決方針

| # | 論点 | v3 解決方針 |
|---|---|---|
| 1 | `phase_state.json` の atomic 更新手順が未確立 (0-2 完了 push 後も `sub_step_current=0-2` のまま) | **`/next-plan` skill に「phase_state.json を atomic 更新する」動作を必須化**。書き込みは temp → `os.replace()` の atomic rename。skill 完了時に `latest_plan_path` / `sub_step_current` / `sub_step_remaining` / `updated_at` を一括更新 |
| 2 | `updated_at` が手動値 | skill 内で `datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")` を必須化 (JST 固定) |
| 3 | `.claude/settings.json` deny ルール未検証 | **0-3 着手 1 手目で `git push --force --dry-run origin chore/step-0-env` を試行し、deny でブロックされることを実機確認**。確認後ログを `.claude/plans/v3.md` の verification 欄に追記 |
| 4 | hook 即時発火確認済 → v2 §3.4「実機確認」要件は既達 | v3 では追加要件なし。0-3 では hook の動作前提で skill を組む |

---

## 3. Sub-Step 0-3: SKILLS (詳細像 v3)

### 3.1 目的

天翔十字フロー上の典型作業 3 つ (初期プラン / 評価 / 次プラン作成) を skill 化し、毎回手書きの構造化を不要にする。**project-local `.claude/plans/` への書き出し** と **`.claude/phase_state.json` の atomic 更新** を skill 側で吸収して、`~/.claude/plans/` (= Claude Code plan mode 自動生成先) との二重管理を解消する。

### 3.2 成果物

| パス | trigger 例 | 動作要旨 |
|---|---|---|
| `.claude/skills/init-plan/SKILL.md` | 「Phase 1 はじめよう」「Phase 2 着手」 | シンプルゴール + N (3/5/7) + イニシャルプラン (詳細像含む) のテンプレを生成 → `.claude/plans/phase_{N}_plan_v1.md` に書き出し → `.claude/phase_state.json` を新 Phase 用に atomic 更新 → ユーザー承認待ち |
| `.claude/skills/eval-step/SKILL.md` | 「0-X 終わった、評価して」「Sub-Step 評価」 | 直近 commit + 変更ファイル差分を `git log -1` / `git show --stat` で取得 → envPlan or 最新 plan の完了判定と突き合わせ → ✅/⚠️/❌ 表で評価レポート出力 → ユーザーへの示談だけで終了 (ファイル書き込みなし) |
| `.claude/skills/next-plan/SKILL.md` | 「次プラン作って」「サードプラン作成」 | シンプルゴール + 既往実績 + 残ステップから新プランを生成 → `.claude/plans/phase_{N}_plan_v{M+1}.md` に書き出し → `.claude/phase_state.json` の `latest_plan_path` / `sub_step_current` / `sub_step_remaining` / `updated_at` を atomic 更新 → ユーザー承認待ち |

### 3.3 skill 共通仕様

- **形式**: 既存 `gen-*` skill と同じ Claude Code 標準形式 (`SKILL.md` に YAML frontmatter `name` / `description` + 本文)
- **description**: trigger 文言の複数バリエーションを列挙 (memory: subagent description のキーワード列挙パターン)
- **書き出し先**: 必ず project-local `.claude/plans/`。`~/.claude/plans/` は触らない
- **phase_state.json 連動**: temp file → `os.replace()` atomic rename で書き換え。`updated_at` は JST ISO 8601
- **ユーザー承認待ちで止まる**: 自動で次 Sub-Step に進まない (envPlan §3.4 踊り場原則)
- **エラー時動作**: phase_state.json 読込失敗時は skill 自体を中止しユーザーに知らせる (init-plan / next-plan は書き込む側なのでエラー隠蔽は危険)

### 3.4 phase_state.json atomic 更新 helper

3 skill で共通使用する更新 helper を `scripts/dev_hooks/update_phase_state.py` に実装する (もしくは各 skill 内に inline)。決定は 0-3 着手時に判断 (skill が SKILL.md だけで完結するなら inline、shell 経由なら別ファイル)。

helper の責務:
- 現 phase_state.json を読む
- 引数で渡された差分 (`sub_step_current` / `latest_plan_path` 等) を適用
- `updated_at` を JST 現在時刻に置換
- 一時ファイルに書き → atomic rename
- 失敗時は stderr に短文 + exit 1

### 3.5 完了判定 (実機検証 3 + 文書 2)

実機:
1. `.claude/settings.json` の deny ルールが効いている — **0-3 着手 1 手目で `git push --force --dry-run origin chore/step-0-env` が deny される**ことを確認、結果を記録
2. `/init-plan` を投下 → Phase 1 用イニシャルプラン雛形が生成され、`.claude/plans/phase_1_plan_v1.md` が project-local に書かれる (= dogfood、ただし Phase 1 本着手はしない、雛形ファイルは即削除)
3. `/eval-step` を 0-3 完了時に呼んで自己評価レポートが返る (dogfood、これは Step 0 完了確認に活用)

文書:
4. 各 skill `SKILL.md` が存在し、description に trigger 例 2 件以上が記載されている
5. `docs/development_layer_rules.md` §3.3 末尾に「skill 化されたフロー支援」一文を追記

### 3.6 想定リスク

| リスク | 対処 |
|---|---|
| skill の trigger 文言が曖昧で発火しない / 別 skill と衝突 | description に複数の言い回し例を列挙、既存 `gen-*` skill の description と被らない形容詞を使う |
| skill が phase_state.json を上書き破壊 (race / 中断) | temp file + os.replace() で atomic、書き込み前に schema 検証 (`phase` / `phase_total_steps` 必須キーの存在) |
| `.claude/plans/` への書き込みが deny で止まる | `.claude/settings.json` allow に `Write(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/**)` が既にあるので OK、念のため 0-3 着手時に確認 |
| `/init-plan` dogfood で Phase 1 を誤って着手 | dogfood は雛形ファイル生成のみで実コードには触れない。生成後即削除する手順をプランに明記 |

---

## 4. 0-3 着手手順 (承認後)

1. **deny 実機確認** (論点 3 解決): `git push --force --dry-run origin chore/step-0-env` を試行、deny の様子を記録
2. `.claude/skills/init-plan/SKILL.md` を Write
3. `.claude/skills/eval-step/SKILL.md` を Write
4. `.claude/skills/next-plan/SKILL.md` を Write
5. (atomic 更新 helper が別ファイル必要なら) `scripts/dev_hooks/update_phase_state.py` を Write
6. dogfood: `/init-plan` を Phase 1 想定で呼び、`.claude/plans/phase_1_plan_v1.md` 雛形が生成されることを確認 → 即削除
7. dogfood: `/eval-step` を 0-3 完了時に呼び自己評価レポートを得る (Step 0 完了確認の入力にもなる)
8. `docs/development_layer_rules.md` §3.3 末尾に skill 化された旨を 1 行追記
9. commit + push
10. Step 0 完了確認 (シンプルゴール達成 → envPlan §9 に従い envPlan.md を `docs/archive/` へ移動も同 commit に含める)

---

## 5. Step 0 完了後の状態

```
.claude/
  settings.json              (0-2)
  phase_state.json           (0-2, 0-3 完了時に sub_step_current="0-3" / sub_step_remaining=0)
  plans/
    phase_0_plan_v1.md       (0-2, envPlan コピー)
    phase_0_plan_v2.md       (0-2 セカンドプラン)
    phase_0_plan_v3.md       (本ファイル、サードプラン)
  skills/
    init-plan/SKILL.md       (0-3)
    eval-step/SKILL.md       (0-3)
    next-plan/SKILL.md       (0-3)
    (既存 gen-* は不変)
CLAUDE.md                    (0-1, 0-2 微調整済)
docs/
  development_layer_rules.md (0-1, 0-2, 0-3 末尾追記)
  archive/
    envPlan.md               (0-3 完了時に root から移動)
scripts/
  dev_hooks/
    inject_phase.py          (0-2)
    update_phase_state.py    (0-3, 必要なら)
```

---

**再掲: 本ファイルは Phase 0 サードプラン (v3)。承認後 0-3 着手 → Step 0 完了 → Phase 1 (撤退) へ進む。**
