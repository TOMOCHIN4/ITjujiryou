# Phase A プラン

> **作成日**: 2026-05-17
> **シンプルゴール (フロー全体)**: scripts/ ディレクトリの保守性を index・分類・呼出元可視化の観点で底上げする
> **全 Phase 数 N**: 3
> **当 Phase の位置**: A / 3

## 1. 背景

ユーザー指示: 「scripts/ ディレクトリの内容を整理した docs/scripts_index.md を作成してください」

現状の scripts/ 配下は次の 5 系統 + 2 トップファイル構成:
- `dev_hooks/` (天翔十字フロー hook 群: `inject_phase.py`, `update_phase_state.py`)
- `gen-asset/` (アセット生成系)
- `hooks/` (Claude Code hook 系)
- `inbox_watcher.py` (top)
- `start_office.sh` / `stop_office.sh` (top)

どこに何があるか・誰が呼ぶかを 1 枚で把握できるドキュメントが無く、新規 onboarding やスクリプト追加時の判断コストが高い。本フローは、その底上げを 3 Phase で段階的に進める初回案件。Phase A はその起点として **index ドキュメントの新設** に集中する (Phase B/C は別案件相当のため、本 plan では言及せず将来 `/init-plan` で起こす)。

直前まで天翔十字フロー本体改修中 (`phase_state.json = _frozen`)。フロー本体改修は commit `95ca24c` で完了済み。本 Phase が **フロー再開の最初の本番案件**。

## 2. 当 Phase の完了判定

- [ ] `docs/scripts_index.md` が新規作成され、git にコミットされている
- [ ] `scripts/` 配下の全 `.py` / `.sh` / その他実行可能ファイルが網羅的に列挙されている (`__pycache__` 除く)
- [ ] 各エントリに最低 4 項目が記載されている: **パス / 言語 / 主な用途 / 呼び出し元 (or 呼び出し方法)**
- [ ] 分類は最低 3 セクション (例: dev_hooks / asset 生成系 / 運用シェル / その他) で構造化されている
- [ ] 廃止・未使用の疑いがあるスクリプトはその旨を注記している (= grep で参照元 0 件のもの等)

## 3. 成果物

- 新規ファイル: `docs/scripts_index.md`
- commit (1〜2 個想定): `docs(scripts): scripts/ ディレクトリの index を新設` 程度
- phase_state.json は本 Phase 中は `phase_current=A` のまま、Phase 完了後 `/eval-phase` で評価 → 次回 `/init-plan` で B に進める

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| 「呼び出し元」を機械的に grep するだけだと、Claude Code hook / cron / 手動実行などを取りこぼす | settings.json / settings.local.json / docs を併読し、grep だけで判断しない |
| scripts/ 配下に隠れ依存 (import チェーン) があり、表に出ないものを見落とす | `.py` は import 関係も 1 行注記する |
| 1 Phase で完了判定を満たすには列挙対象が多すぎて時間が伸びる | 現状 8 ファイル前後で規模は小さい、リスク低 |
| シンプルゴール「保守性底上げ」が抽象的すぎて Phase B/C の輪郭が読めない | Phase B/C は本 Phase 完了後の `/init-plan` で改めて議論。本 Phase では index 1 本に集中 |

---

**再掲: 本ファイルは Phase A の単一プラン。承認後に着手し、完了したら `/eval-phase` で評価する。**
