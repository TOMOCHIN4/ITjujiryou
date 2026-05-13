# 愛帝十字陵 v2 — Phase 3a 引き継ぎ HANDOFF

最終更新: 2026-05-13
前任セッションの作業範囲: Phase 0 (準備) / Phase 1 (CLAUDE.md 改修) / Phase 2 (物理基盤整備) を完遂

---

## TL;DR

- **v2 が単体構成を初めて上回った** (Run 3 = 19/25 > Run 1 = 18/25)。仕様書 §1.1 の v2 存在意義を Phase 2 完了時点で達成
- 次は **Phase 3a (D1 ユウコ 3 セッション分割 + D13 記憶検索 subagent + D14 物理ガード + D15 HOOK 失敗安全網)** に着手すべき
- Phase 2 で発見・対処したバグ 2 件 (allowlist / send_message client) と既知問題 1 件 (writer/engineer の Write tool 不使用) が記録済
- **コンテキスト引き継ぎで真っ先に読むべきは本ファイル + 末尾の必読 5 件**

---

## 各 Phase 結果サマリ

| Phase | 内容 | 結果 | 主成果物 |
|---|---|---|---|
| Phase 0 | 評価基盤 (Run 1/2) + ワークフロー 5 本 + HOOK 棚卸し | Run 1 = 18/25, Run 2 = 5/25 (実質 0、v1 限界判明) | `benchmarks/cases/` + `benchmarks/rubric.md` + `workflows/originals/` 5 本 + `benchmarks/souther_hook_inventory.md` |
| Phase 1 | D9 (サザン二重構造化) / D11 (Step 0 ヒアリング挿入) / D3 (review_memo) / D17 (brevity hook 退役) | スモーク合格 (4 分でヒアリング送信、TUI 描画再発なし) | `benchmarks/runs/phase1-smoke.md` |
| Phase 2 | D4 (3 階層 README) / D10 (md-hybrid-v1 形式) / D16 (review dirs) + SkillCollection symlink + 申し送り 4 件 + Run 3 自演実行 | **Run 3 = 19/25 で初めて単体を上回った** | `benchmarks/runs/phase2-smoke.md` + `benchmarks/runs/run3-phase2/` + `benchmarks/runs/comparison.md` |

---

## Phase 3a 着手指針 (v2 仕様書 §7.9)

### スコープ

- **D1**: ユウコ 3 セッション分割 (受注/初期案 → 統合 → 振り分け/監督)
- **D13**: 記憶検索 subagent (キャラごとに別 subagent を定義)
- **D14**: 物理ガード (`.claude/settings.json` で 兄弟の Read 権限を制限)
- **D15**: HOOK 失敗安全網 (`_last_write.log` のタイムスタンプチェック)

着手前に確認すべき **Phase 2 観察に基づく優先課題**:

1. **ターン継続性** (Phase 2 で 2 回ナッジ介入が必要だった): Run 3 で観察された Step B (dispatch) / Step E (deliver) 境界での turn closure。**D1 ユウコ 3 セッション分割 (claude -p 都度起動)** で根本対処
2. **writer/engineer の Write tool 不徹底** (Phase 0 §7.5 再発): report のみで実ファイル無しで approve させてしまう。Phase 3b で各兄弟 CLAUDE.md 強化 + Phase 4 で D8 (ユウコ門番) で構造対処

### Phase 3a 実装の鍵 (仕様書 §4.1, §4.2)

- セッション起動形は **(α) `claude -p` 都度起動** (ステートレス短命プロセス、OS レベルで分離)
- ハンドオフは **ファイル経由** (`workflows/cases/{案件ID}/initial_plan.md` → `integrated_plan.md` → `final_plan.md`)
- pane 可視性は失われるため、UI 側の表示は別 issue 化 (仕様書 §10)
- `inbox_watcher.py` の改造が中心

### Phase 3a で気をつけるポイント

- **既存 inbox_watcher は tmux pane へ send-keys する形式**。`claude -p` 起動方式に置き換えるには大きな改造が必要 — 段階的にやる
- **Phase 2 で symlink で SkillCollection 統合済**。Phase 3a でセッション分割するときも同じ `.claude/skills/` がそれぞれの一時セッションから見える設計を維持
- **Phase 2 で導入した propose_plan の MD ファイル経路** (`workflows/cases/{案件ID}/final_plan.md`) はそのまま Phase 3a 統合セッションのハンドオフ媒体として活用
- **記憶検索 subagent (D13)** は **MCP ではなく subagent** として実装 (仕様書 §3.4)。`workspaces/{role}/.claude/agents/` 等で定義

---

## 新セッションで真っ先に読むべき必読 5 件

優先順位順に:

1. `/Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/aitei_juujiryou_v2_master_specification.md` — v2 全体仕様書 (Phase 0〜5 の全体地図)
2. **本ファイル** (`benchmarks/HANDOFF.md`) — 前任セッションの達成と Phase 3a 着手点
3. `benchmarks/runs/comparison.md` — Run 1/2/3 比較、Phase 3a で取り組むべき項目の根拠
4. `/Users/tomohiro/.claude/plans/users-tomohiro-desktop-claudecode-itjuj-cozy-hamster.md` — Phase 2 実行プラン (Phase 3a でも構造を参考に)
5. `workspaces/yuko/_modules/workflow.md` — ユウコ業務サイクル現状 (Step 0〜E + ヒアリング)

参考に応じて読む:

- `benchmarks/souther_hook_inventory.md` — Phase 4 で本実装する HOOK 候補 (P1-P7 ラベル付き)
- `workflows/originals/` 5 本 — ワークフロー資産
- `workflows/cases/2026-05-13-kataoka-dental/final_plan.md` — D10 md-hybrid-v1 形式の実例
- `workspaces/yuko/_modules/review_memo.md` — D3 書き方規約 (Phase 3b 以降で実体化)
- `workspaces/yuko/_modules/workflow_reference.md` — 案件タイプ別 WF マッピング

---

## Phase 2 で発見し対処したバグ 2 件 + 既知問題 1 件

| # | 内容 | 対処 |
|---|---|---|
| B1 | `FORBIDDEN_TERMS` の「愛帝」と社名フル表記 (株式会社 愛帝十字陵) の衝突 | `src/persona.py` の `_ALLOWED_PHRASES` allowlist で対処済 |
| B2 | `send_message(to=client)` が一律 deny で Step 0 ヒアリングが送れない | `src/mcp_server.py` の `_handle_send_message` でユウコの `message_type=email` のみ許可済 |
| B3 | writer/engineer が Write tool を使わず report 本文に直書き (Phase 0 §7.5 既知再発) | 未対処 — Phase 3b/4 で構造対処予定 |

---

## v2 構成の物理状態 (Phase 2 完了時点)

### 編集された主要ファイル

- `src/mcp_server.py` (propose_plan 拡張 + deliver sanitize + send_message client 許可)
- `src/persona.py` (FORBIDDEN_TERMS に XML タグ + `_ALLOWED_PHRASES` allowlist)
- `scripts/hooks/check_persona_leak.py` (FORBIDDEN_TERMS の効果を介して XML タグも捕捉)
- `scripts/hooks/souther_dispatcher.py` (新規、Phase 4 で本処理する HOOK 骨格)
- `workspaces/yuko/CLAUDE.md` + `_modules/{workflow,workflow_reference,review_memo,persona_guard}.md`
- `workspaces/{souther,writer,designer,engineer}/CLAUDE.md` (D3 記録ルール + 参照可能スキル)
- `workspaces/souther/.claude/settings.json` (UserPromptSubmit hook 切替)
- `workspaces/souther/_modules/{voice,persona_narrative}.md` (brevity 由来記述削除)

### 削除されたファイル

- `scripts/hooks/inject_souther_mode.py` (D17 退役、git rm 済)
- `data/logs/souther_state.json` + `souther_spotlight.log` (D17 退役、未追跡だったため rm 済)

### 新規ディレクトリ (symlink + ファイル)

- `.claude/skills/{_core,_marketing}` (SkillCollection への symlink)
- `workspaces/{role}/.claude/skills` (× 5、親への相対 symlink)
- `data/memory/{role}/review_received/` (× 5、.gitkeep)
- `data/memory/yuko/review_notes/` (.gitkeep)
- `workflows/{README,cases/README,distilled/README}.md`
- `workflows/cases/2026-05-13-kataoka-dental/final_plan.md` (Run 3 実例)
- `benchmarks/runs/{phase2-smoke,run3-phase2/,comparison}.md` (更新)

### 起動コマンド (変更なし)

- 起動: `./scripts/start_office.sh`
- 停止: `./scripts/stop_office.sh`
- API: `http://localhost:8000` (FastAPI)
- 発注: `POST /api/orders` with `{"text": "...", "task_id": "..."}`
- DB: `data/office.db` (SQLite, WAL モード)

---

## Phase 3a 開始時に確認すべき git の状態

`git status` で Phase 2 改変が一括見える。コミットしていない場合は、Phase 3a 着手前に **Phase 2 の単一コミット** を切ると後の比較がしやすい (例: `feat(phase2): D4 + D10 + D16 + SkillCollection 統合 + Run 3 (19/25, v2 が単体を初突破)`)。本セッションでは未コミット。

---

## 引き継ぎでよくある罠

- **`workflows/cases/2026-05-13-kataoka-dental/`** には Run 3 の案件残骸あり。新規 Run 4 で kataoka-dental を再投入するときは ディレクトリ削除 or 別案件 ID で
- **`outputs/{Run3 の task_id}/`** にも 17 ファイル残存。Run 4 で同案件再投入時に上書きされない構造なので、削除しても問題ないが歴史保持なら残置可
- **`benchmarks/runs/run3-phase2/deliverables/` は Run 3 のスナップショット** で、Phase 3a/3b の Run 4/5 では上書きしないこと

新セッションは **本ファイル冒頭 + 必読 5 件** で 5 分以内に文脈を取り戻せるはず。
