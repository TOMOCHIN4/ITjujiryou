# Phase C プラン

> **作成日**: 2026-05-17
> **シンプルゴール (フロー全体)**: prompts/ 配下の全ファイルの索引 + 1 行要約を docs/prompts_overview.md として整備し commit 済みにする
> **全 Phase 数 N**: 3
> **当 Phase の位置**: C / 3

## 1. 背景

Phase B で `docs/prompts_overview.md` を Write 済 (新規 38 行)。Phase C は **検証 + commit** によりシンプルゴール「commit 済み」状態を達成する最終 Phase。

Phase B の `/eval-phase` で挙がった論点を本 Phase で吸収する:

- **commit 対象**: `docs/prompts_overview.md` 本体 + `.claude/phase_state.json` (Phase 進行履歴) + `.claude/plans/phase_{A,B,C}.md` (本フローのプラン履歴) の 3 セット。`conversation.png` (本タスク無関係) は除外。
- **commit メッセージ**: 既存スタイル (`docs(scripts): scripts/ ディレクトリの索引を新設`) に倣い `docs(prompts): ...` 形式の Conventional Commits 風。
- **プラン履歴の同梱**: 単一フローの作業記録として `.claude/plans/phase_{A,B,C}.md` も一緒に commit するのが自然 (個別 commit に分割しない)。

## 2. 当 Phase の完了判定

- [ ] `docs/prompts_overview.md` の内容を `prompts/` 配下の実ファイルと最終突合し、要約と実態が乖離していないことを確認
- [ ] 個別ファイル指定で `git add` し、`conversation.png` を含めずに対象ファイル群のみがステージされていることを `git status` で確認
- [ ] commit メッセージは `docs(prompts):` プレフィックス + 1 行件名 + 必要に応じて本文で意図を補足
- [ ] commit 成功後、`git log -1` で commit が記録されていることを確認
- [ ] `git status` でワーキングツリーが clean (もしくは本タスク無関係の `conversation.png` のみ残る) になっていることを確認

## 3. 成果物

- HEAD に新規 commit (`docs(prompts):` 系列のメッセージで `docs/prompts_overview.md` 等を含むもの)
- ワーキングツリー clean (本タスク関連のみ)

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| `git add .` で `conversation.png` を巻き込む | 個別ファイル指定 (`git add docs/prompts_overview.md .claude/phase_state.json .claude/plans/phase_A.md .claude/plans/phase_B.md .claude/plans/phase_C.md`) で対処 |
| 最終突合で要約のズレが発覚 | 同 commit 内で `docs/prompts_overview.md` を直接編集して修正、Phase 内 1 commit を維持 |
| pre-commit hook で blocked | hook の指摘を確認し修正、`--no-verify` は使わない |
| commit メッセージに北斗用語・社内符丁が混入 | 開発レイヤー側の応答として中立な技術メッセージのみで構成 (聖帝口調等を持ち込まない) |

---

**再掲: 本ファイルは Phase C の単一プラン。承認後に着手し、完了したら `/eval-phase` で評価する。**
