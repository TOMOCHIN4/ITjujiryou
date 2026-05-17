# 愛帝十字陵 大改修 要件整理

> **位置付け**: 愛帝十字陵システムの大改修を行うにあたり、user が達成したい要件のみを整理したドキュメント。シンプルゴール / N / Phase 構成は **天翔十字フロー (`/init-plan`)** で別途確定する想定で、本ドキュメントは **要件素材** に専念する。
>
> **議論経緯の参照元**: `docs/2026-05-16_system_rethink_discussion.md`
>
> **作成日**: 2026-05-17

---

## 1. 改修の本質的目標

愛帝十字陵システムを **「自前ハーネスへの過剰投資」状態から脱し、Claude Code 標準機能 + filesystem memory + ワークフロー文書だけで動く軽量構成** に置き換える。これにより:

- 個人プロジェクトとしてメンテ可能な複雑度に収まる
- Claude Code / Opus の進化に乗りやすいクラシカルな構造になる
- 記憶層 (= 資産) と専門人格 (= 資産) は維持・継承される

---

## 2. 残したい要素 (= 改修後も存続)

- **`data/memory/` の積み上げ層**: 会社記憶 + 個人記憶 + 過去案件履歴。これがシステム最大の資産
- **各役職の人格・専門知識ファイル群**: 既存の `workspaces/{role}/CLAUDE.md` + `_modules/*.md` + `prompts/*.md` の内容資産 (構成は新形式に再配置可)
- **世界観 (= 北斗の拳ベース)**: 人格ファイルに含めて残す。ただし運用への強制 (= hook 等) は外す、おまけ要素として扱う
- **天翔十字フロー**: 開発レイヤーで磨いた現行 form (= `v0.16-flow-auto-eval` 時点) をユウコへ伝承する

---

## 3. 捨てたい要素 (= 改修で削除)

- **tmux 5 pane 並列起動構成** (= `start_office.sh` 現行版)
- **`scripts/inbox_watcher.py`** (SQLite poll → tmux send-keys の watcher)
- **`src/mcp_server.py` の連携系ツール**: `dispatch_task` / `consult_souther` / `consult_peer` / `propose_plan` / `evaluate_deliverable` / `update_status` / `read_status` / `deliver`
- **`scripts/hooks/` の自動連携系**: `inject_souther_mode.py` / `check_persona_leak.py` / `check_souther_recipient.py`
- **SQLite messages / tasks / subtasks / events / revisions / deliverables テーブル**経由のエージェント間通信
- **`src/persona.py` の FORBIDDEN_TERMS 強制**: 世界観のおまけ化と整合
- **サザン二重構造 / backstage sentinel** 等の自動 routing 補助
- **既存 pixel UI** (= `src/ui/static/pixel/`): 撤退対象、後で新仕様で作り直し

---

## 4. 新構成の合意点

- **ユウコ = オーケストレーター** (= user のパートナー、案件中セッション継続、案件単位で /clear)
- **サザン = 形骸化 subagent** (儀式承認のみ、user 後付け実装)
- **実行役 (writer / designer / engineer) = 都度呼び出し** (tmux pane で persona swap、別途構築)
- **半自律モデル** (= 段は自動、踊り場で人間判断)
- **天翔十字フロー** をユウコが操作系として運用
- **自動連携なし** (= user が Claude Code 経由で指示、watcher 不要)
- **構成**: tmux 2 pane (orchestrator + executor swap)
- **モデル**: 全エージェント `claude-opus-4-7` + 最低 medium thinking 固定 (Sonnet / Haiku 禁止、`feedback_model_opus_only.md` 参照)
- **UI**: 新仕様で刷新 (= 既存 pixel UI は撤退後に再設計)
- **スプライト gif アニメ**: 遊び要素として残したい、ただし実装は最後

---

## 5. 制約条件

- **作業ブランチ**: 現状 `chore/flow-simplification` で改修進行、**main マージは大改修完遂後**
- **`feat/yuko-3pipe` ブランチは凍結**、議論メモまでで放置 (削除しない)
- **天翔十字フロー本体・skill・hook・settings は触らない** (= 開発レイヤー資産として既に完成済、`v0.16-flow-auto-eval` 状態を維持)
- **`docs/development_layer_rules.md` も触らない** (= 同上)
- **手戻りが起きにくいよう小さく切る** (= 例えば撤退 → 新構成 PoC → 実案件検証 → UI の順で、後戻りコストが小さい流れにする)

---

## 6. スコープ外 / 触らない領域

- **`.claude/skills/` の gen-* (gen-image / gen-music / gen-sfx / gen-sprites / gen-voice)**: 独立ツールとして既に動く、本改修では触らない
- **`outputs/` 配下の納品物 (gitignore 済)**: 本改修と無関係
- **将来案件**: 本改修中の本番案件運用は想定しない (= 改修期間中は愛帝十字陵自体が稼働しない前提)

---

## 7. 達成判定の素材

「シンプルゴール達成」は以下が同時に満たされた状態:

- 旧自前ハーネス (= §3) が repo から削除済
- 新構成 (= §4) が tmux 2 pane で起動可能、最低 1 件の試金石案件 (例: 200 字挨拶文) を end-to-end で回せる
- `SPEC.md` が新構成を反映 (= 旧記述が残らない)
- 既存 memory 層 (= §2) が新構成からも参照可能
- 新 UI が新構成での進行状態を可視化できる (= スプライトアニメ等の遊び要素は除外可)

---

## 8. 既知の未確定事項 (= /init-plan 時に user 確認推奨)

- **user の Claude Code と tmux session の中継方法**: Bash で `tmux send-keys` / `tmux capture-pane` ベースか、filesystem 経由か
- **Web UI が担う機能**: 可視化専用 (= 表示のみ) か、入力経路にもなるか
- **persona ファイルの新配置**: `workspaces/{role}/` を `personas/{role}/` に rename するか、別構成か
- **撤退対象の最終確認**: §3 のリストで漏れなしか
- **スプライトアニメの優先度**: いつ作るか、撤退完了とどう関係させるか

---

## 9. 別セッションへの渡し方 (案)

新規 Claude Code セッションを `chore/flow-simplification` ブランチで起動し、以下を指示する:

```
docs/2026-05-16_system_rethink_discussion.md (議論経緯) と
docs/2026-05-17_overhaul_requirements.md (達成要件) を読み、
愛帝十字陵の大改修を天翔十字フローに乗せて取り組んでください。

シンプルゴール / N / 詳細像はあなたが提案してください
(= /init-plan で起動し、user 承認を得る形)。

未確定事項 (§8) は /init-plan 時に user に確認してください。
```

---

## 10. 参照ドキュメント

- `docs/2026-05-16_system_rethink_discussion.md` — 議論経緯 (= シンプルゴール / 半自律 / 踊り場 / N / 詳細像 モデルが固まった経過)
- `SPEC.md` — 改修前の現状仕様 (= 改修で書き換える対象)
- `docs/development_layer_rules.md` — 天翔十字フロー定義 (= 触らない、ユウコ伝承時に参照する)
- `docs/case_log_analysis/2026-05-14_15.md` — 旧構成の複雑性実測根拠
- `.claude/plans/_archive/phase_0_plan_v{1,2,3}.md` — Step 0 で経た議論履歴 (削除済、git history で取得可)
