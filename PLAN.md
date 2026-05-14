# PLAN — 未着手の TODO 置き場

> **このファイルの位置付け**: これから何をするか (= 未来) だけを書く。
> - 現状の仕様 (アーキテクチャ / キャラクター / ツール / 既知の落とし穴) は `SPEC.md`
> - 経緯ログ は `git log` と `~/.claude/projects/.../memory/MEMORY.md`
> - 人間向けの使い方は `README.md`

## 未着手 TODO

### [次セッション] 2026-05-14/15 案件ログ分析

UI E2E + verify-003 シリーズで取得したログを最初から最後まで分析し、改善候補を洗い出す。

**対象ログ** (`data/` は `.gitignore` 配下、ローカル参照):

- `data/logs/dev/2026-05-14_ui_e2e_permission/` (dontAsk 下の deny 事例)
  - 5 jsonl (souther/yuko/writer/designer/engineer session log)
  - 6 pane txt (tmux capture)
  - `SUMMARY.md` (deny 状況サマリ)
- `data/logs/dev/2026-05-15_auto_mode_e2e/` (auto モード成功時)
  - 5 jsonl + 7 pane txt + watcher.txt + api.txt
  - `messages.csv` (3 task_id 統合、184 rows)
  - `outputs_listing.txt`

**分析観点**:

1. **キャラ言動の質** — 聖帝口調 / 慈愛 / 覇道調 / 北斗SRE拳 等の演じ分け、ペルソナ漏れの有無、社内符丁の妥当な発火
2. **規律遵守** — memory-curator.md (`{case_id}.md` 命名), persona_narrative.md §6.6 (裏側 silent), workflow.md Step F (二重構造 5 段階), 各 role の納品ファイル内容ルール
3. **完遂性** — workaround 発生箇所、stuck の有無、auto モード vs dontAsk モードの完遂率比較
4. **二重構造の発火タイミング** — 表 omage vs 裏 silent の切替が正しく行われたか、curator_request → curator_response → memory_approval_request の連鎖
5. **pixel UI への露出** — 心のうち (record_thought) / 会話パネル / spotlight log に出るべき情報 vs 隠すべき情報 (= 裏側痕跡なし) の整理
6. **改善候補** — 次セッション以降で根本修正したい事象 (新規 feedback memory に切り出すべきもの)

**起点**: `data/logs/dev/2026-05-15_auto_mode_e2e/messages.csv` で時系列を把握 → 興味ある段階の該当 jsonl を Read で深掘り、対応する pane txt と突き合わせ。

### [次セッション] サザン二重構造 4 operation のうち未配線 3 つ

本セッション (2026-05-14) で `integrate_proposal` operation の発火経路 + workflow / hooks / watcher / subagent / settings は完成し、verify-003 v7 で全 8 段階を workaround 無しで通過確認済。残るのは 3 つの未配線 operation のトリガー設計:

a. **`cross_review`** — company/{category}/ 横断レビュー、矛盾検出。発火タイミング案: 月次 cron / 100 案件 deliver ごと
b. **`archive_judge`** — 90 日経過 `_scratch/` のアーカイブ候補判定、下の §7 アーカイブ運用と統合。発火タイミング案: 90 日 cron
c. **`client_profile_maintenance`** — クライアント別案件 N 件溜まったらユウコが手動 or 自動上申

memory-curator.md §3 で 4 operation の subagent 側 handler は既に配置済 (`{case_id}.md` 厳命化済)、必要なのはユウコ側のトリガー経路。

### [次セッション or 将来] subagent Write glob 公式 fix の追跡

`workspaces/souther/.claude/settings.json` の Write allow は現状 bare `Write` (verify-003 で limited glob が subagent 継承時の path normalization 不整合で auto-deny されることを確認、Anthropic fix 待ち)。Claude Code の release notes に subagent permission inheritance 修正が出たら limited glob `Write(//.../company/_proposals/**)` に復帰検討。
- 関連 memory: `feedback_subagent_write_glob_inheritance.md`
- 関連 memory: `feedback_solo_use_pragmatism.md` (個人利用なので fix が出るまで bare Write + 規律ガードで OK)

### [将来] 記憶システム §7 アーカイブ運用

90 日経過した `data/memory/{role}/_scratch/{case_id}/` を `data/memory/{role}/_archive/{case_id}.tar.gz` に圧縮するバッチを設計・実装する。memory-curator subagent の `archive_judge` operation で既にアーカイブ **候補判定** は実装済 (本セッション §3.3)。残りは物理 tar.gz 化バッチと、`_archive/` 配下の検索範囲設定。

肝になる要素:
- 「使われなくなった ≠ 不要」 → 物理削除せずアーカイブ
- 検索 subagent の通常検索範囲からは外し、検索ノイズを下げる
- 復活可能性は残す (tar.gz から個別 case_id を取り出せる経路)
- memory-curator の `archive_judge` 出力 (`data/memory/company/_proposals/{case_id}.md`) を batch スクリプトの入力にする

着手前に読む:
- `SPEC.md §10` (記憶システム本体)
- `data/memory/README.md`
- `workspaces/souther/.claude/agents/memory-curator.md` (archive_judge operation の出力フォーマット)
