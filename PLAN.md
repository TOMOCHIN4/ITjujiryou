# PLAN — 未着手の TODO 置き場

> **このファイルの位置付け**: これから何をするか (= 未来) だけを書く。
> - 現状の仕様 (アーキテクチャ / キャラクター / ツール / 既知の落とし穴) は `SPEC.md`
> - 経緯ログ は `git log` と `~/.claude/projects/.../memory/MEMORY.md`
> - 人間向けの使い方は `README.md`

## 未着手 TODO

### [優先] dontAsk モード切替 (物理ブロック復活)

`scripts/start_office.sh:41` の `claude --dangerously-skip-permissions` を `claude --permission-mode dontAsk` に置換する。

**Why**: bypass モードでは settings.json の `permissions.deny` / `permissions.allow` が全 skip される (公式 [permission-modes.md](https://code.claude.com/docs/en/permission-modes) で確認、2026-05-14)。サウザー化防止 (SPEC.md §7.1) や記憶アクセスガード (§10.1) の物理ブロックが本番では効いておらず、実質ガードは hook 経路のみ。dontAsk モードなら allow に書かれたツール + read-only Bash のみ実行可で、自律駆動 (tmux 監視ゼロ) と物理ブロックを両立できる。

着手前に必ず読む:
- memory: `project_permission_dontask_proposal.md` (切替手順 + 事前チェック項目)
- memory: `feedback_bypass_permissions_pitfall.md` (現状の問題)
- memory: `feedback_permissions_caution.md` (パーミッション変更は実機検証必須)

実機検証必須: 案件 1 件を流して allow リスト不足で auto-deny が出ないか確認、各 hook が引き続き動くか確認。

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
