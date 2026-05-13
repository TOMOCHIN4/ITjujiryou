# PLAN — 未着手の TODO 置き場

> **このファイルの位置付け**: これから何をするか (= 未来) だけを書く。
> - 現状の仕様 (アーキテクチャ / キャラクター / ツール / 既知の落とし穴) は `SPEC.md`
> - 経緯ログ は `git log` と `~/.claude/projects/.../memory/MEMORY.md`
> - 人間向けの使い方は `README.md`

## 未着手 TODO

### [次セッション] 記憶・経験積み上げシステム

5 キャラ (サザン / ユウコ / ハオウ / トシ / センシロウ) が案件を重ねるたびに経験・気づき・修正パターン・クライアント反応を**構造化ファイル**として蓄積し、それを **検索/読込/書込/整理を担う subagent** が運用する。

肝になる要素 (ユーザー発):
1. **構造化されたファイル**: 記憶・経験を記録する場所
2. **subagent**: 検索/読込/書込/整理を担う

着手前に読む:
- `~/.claude/projects/-Users-tomohiro-Desktop-ClaudeCode-ITjujiryou/memory/project_next_session_memory_system.md` (設計骨子・既存サンプル・論点)
- `~/.claude/projects/-Users-tomohiro-Desktop-ClaudeCode-ITjujiryou/memory/feedback_python_guardrail_pattern.md` (Omage Gate で実証した再利用テンプレ)
- `data/memory/{role}/*/*.md` (既存の構造化記憶サンプル 4 件、フォーマット先行例)
- `SPEC.md` §5 (ディレクトリ構成、`data/memory/` 予約) と §9 (将来拡張)

詳細論点 (subagent をどこに置くか、書込トリガ、構造化フォーマット等) は memory の `project_next_session_memory_system.md` を参照。
