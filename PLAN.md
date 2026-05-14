# PLAN — 未着手の TODO 置き場

> **このファイルの位置付け**: これから何をするか (= 未来) だけを書く。
> - 現状の仕様 (アーキテクチャ / キャラクター / ツール / 既知の落とし穴) は `SPEC.md`
> - 経緯ログ は `git log` と `~/.claude/projects/.../memory/MEMORY.md`
> - 人間向けの使い方は `README.md`

## 未着手 TODO

### [次セッション] サザン雑務集中設計

サザンの稼働率が低い (儀礼承認のみ) のを是正し、「案件中に必ず発生・誰がやってもよい・納品の質に直接影響しない」雑務 (ユウコ門番機能の一部、会社記憶の体系化整理、クライアント記録メンテ等) をサザンに集中させる。

肝になる要素:
- Task subagent 経由でサザンが実務を代行 (聖帝が直接手を動かさない原則を維持)
- ユウコ workflow.md Step F の memory_proposal 統合フェーズをサザンに移譲
- 既存 Omage Gate (Python ガードレール) は維持

着手前に読む:
- memory: `project_next_session_souther_chores.md` (設計骨子 / 移管候補 / 論点 4 つ)
- memory: `feedback_subagent_vs_pane.md` (subagent vs pane の判断)
- memory: `feedback_python_guardrail_pattern.md` (Omage Gate の再利用テンプレート)
- `workspaces/souther/CLAUDE.md` + `_modules/persona_narrative.md`
- `workspaces/yuko/_modules/workflow.md` Step F
- `SPEC.md §10.3` (会社記憶確定フローの現状)

### [次セッション ついで] 全 role の effortLevel を xhigh に明示

現状 5 workspaces の settings.json には `"model": "claude-opus-4-7"` のみ指定、`effortLevel` は未設定 (pane status bar の `⚡xhigh` は Claude Code デフォルト由来)。
明示的に `"effortLevel": "xhigh"` を 5 settings.json に追記して固定する。

**注意: キー名は `effortLevel` (settings.json) と `effort` (subagent frontmatter) で異なる**。詳細は memory `feedback_effort_level_key_naming.md` 参照。

- `workspaces/{souther,yuko,writer,designer,engineer}/.claude/settings.json` の最上位に `"effortLevel": "xhigh"` を追加 (camelCase + Level suffix)
- subagent (`workspaces/*/.claude/agents/memory-search.md`) は session の effort を継承するため明示不要 (公式: "Default: inherits from session"。明示する場合は frontmatter キー名 `effort` を使う)
- ホーム階層 (`~/.claude/settings.json`) ではなく role ごとに明示する方が「サザンだけ max にする」等の調整が後でしやすい

### [将来] 記憶システム §7 アーカイブ運用

90 日経過した `data/memory/{role}/_scratch/{case_id}/` を `data/memory/{role}/_archive/{case_id}.tar.gz` に圧縮するバッチを設計・実装する。

肝になる要素:
- 「使われなくなった ≠ 不要」 → 物理削除せずアーカイブ
- 検索 subagent の通常検索範囲からは外し、検索ノイズを下げる
- 復活可能性は残す (tar.gz から個別 case_id を取り出せる経路)

着手前に読む:
- `SPEC.md §10` (記憶システム本体)
- `data/memory/README.md`
- 目的書 §7 (本目的書は 2026-05-14 セッションで実装プラン `~/.claude/plans/v2-serene-marble.md` に反映済、§1-6 は完了)
