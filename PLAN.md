# IT十字陵 — 仕様書 (v3.0 マルチプロセス Claude Code 構成)

> **このドキュメントの位置付け**: Claude Code がこの仕様書だけを読んで、現行構成を理解し継続実装できるようにする。
> **想定読者**: 新しいセッションで引き継ぐ Claude Code、および発注者本人 (仕様レビュー用)。
> **バージョン**: 3.0 (2026-05-08 マルチプロセス Claude Code 化以降の現行版)
>
> **詳細は分散している。当ファイルは「なぜこの構成か / 変えてはいけないこと」を残す。**
> - 5 人のペルソナ: `workspaces/{souther,yuko,designer,engineer,writer}/CLAUDE.md`
> - 設計の根拠: `~/.claude/plans/foamy-sniffing-dove.md`
> - 旧構成からの移行手順とコミット履歴: `git log --oneline`
> - 起動・運用: [`README.md`](./README.md)

---

## 0. 前提情報

### 0.1 開発環境

- **言語**: Python 3.11+
- **主要依存**: `mcp>=1.0`, `aiosqlite>=0.20`, `fastapi>=0.115`, `uvicorn[standard]>=0.30`
- **必須コマンド**: `tmux>=3.4`, `claude` (Claude Code CLI)
- **認証**: Claude Max プランの OAuth (`claude login`)。**`ANTHROPIC_API_KEY` は使用しない**
- **OS**: macOS / Linux (Windows は tmux の都合で未対応)

### 0.2 利用形態

- **個人専用**: 認証・課金・マルチテナント不要
- **発注者は 1 人**: あなた (プロジェクトオーナー) のみ
- **オンデマンド起動**: `./scripts/start_office.sh` で起動、終わったら `./scripts/stop_office.sh`

---

## 1. 経緯

### 1.1 v1.0 (Phase 1〜2.2): Agent SDK 単一プロセス構成

`claude-agent-sdk` を使った単一 Python プロセスで 5 エージェントを動かす構成。Phase 2.2 (Web ダッシュボード MVP) まで実装済みで動作していた。

### 1.2 v3.0 (現行) への転換: Anthropic ポリシー対応

2026-04-04 から Anthropic は **「Agent SDK + Pro/Max OAuth」を禁止** した (公式: [code.claude.com/docs/en/legal-and-compliance](https://code.claude.com/docs/en/legal-and-compliance))。

> **OAuth authentication** is intended exclusively ... for ordinary use of Claude Code and other native Anthropic applications.
>
> **Developers** building products or services ..., **including those using the Agent SDK, should use API key authentication**.

本プロジェクトは **API 従量課金を使わない** 方針 (Max サブスクで完結したい) なので、唯一の選択肢は「Claude Code を 5 プロセス並列起動して各々が Max OAuth で動く」マルチプロセス化だった。これは Anthropic の利用範囲 (ordinary use of Claude Code) に収まる。

### 1.3 v3.0 で達成したこと (2026-05-08)

- 旧 `src/agents/` `src/tools/registry.py` `src/orchestrator.py` `src/reception.py` を完全削除
- `claude-agent-sdk` 依存を `pyproject.toml` から除去
- `workspaces/{role}/` に Claude Code 用の per-role 設定を配置
- `src/mcp_server.py` (stdio MCP server, 9 ツール) で連携
- `scripts/inbox_watcher.py` (SQLite poll → tmux send-keys) で起動の引き金
- `scripts/hooks/` でペルソナ漏れガード + 召喚モード block 注入
- Phase A (2 pane / Opus) と Phase B (5 pane / Sonnet 4.6) で実環境スモーク成功

---

## 2. アーキテクチャ

```
ユーザー (発注者)
   │ POST /api/orders
   ↓
FastAPI (:8000)  ──→  data/office.db (WAL モード)
                          ↑     ↑
                          │     │ stdio MCP
                          │     │
              ┌───────────┴─────┴──────────────┐
              │   inbox-watcher (常駐 daemon)   │
              │   - DB 監視                    │
              │   - tmux send-keys で通知       │
              └───────┬─────────────────────────┘
                      │ tmux send-keys (Enter ×2)
                      ↓
   tmux session "itj"  (6 pane)
   ┌─────────┬─────────┬─────────┐
   │ souther │  yuko   │ designer│
   ├─────────┼─────────┼─────────┤
   │ engineer│ writer  │ monitor │
   └─────────┴─────────┴─────────┘
   各 pane: workspaces/{role}/ で `claude --dangerously-skip-permissions` 起動
            .claude/settings.json で permissions / hooks 強制
            CLAUDE.md でペルソナ固定
            .mcp.json で itjujiryou MCP server 参照
```

通信の役割分担:
- **SQLite (`data/office.db`, WAL モード)**: 事実の真実源 (messages, tasks, events, plans, revisions, deliverables, subtasks)
- **MCP server (`src/mcp_server.py`)**: ツール経路 (9 ツール)
- **inbox-watcher (`scripts/inbox_watcher.py`)**: 起動の引き金 (DB 新着 → tmux send-keys)
- **FastAPI + WS (`src/ui/`)**: ヒトとの I/F + リアルタイム可視化

---

## 3. キャラクター仕様

5 人のペルソナ・口調・人格は `workspaces/{souther,yuko,designer,engineer,writer}/CLAUDE.md` に集約されている。元ネタは `prompts/{role}.md` (履歴保持用)。

主要キャラクターの一行サマリ:

| 役職 | 役割 | 重要な制約 |
|---|---|---|
| **社長サウザー (souther)** | 最終決裁者。聖帝口調を維持 | Bash/Edit/Write/dispatch_task/deliver/consult_souther を持たない (permissions.deny で物理遮断)。クライアント直接対話禁止 |
| **営業主任ユウコ (yuko)** | クライアント窓口、ディレクション、納品 | 唯一の対外窓口。社長への上申は consult_souther、部下への発注は dispatch_task。クライアント宛文書にペルソナ漏れ厳禁 |
| **デザイナー (designer)** | 画像・音声・スプライト生成 | scripts/gen-asset/* を Bash で叩ける |
| **エンジニア (engineer)** | コード・自動化・実装 | npm/pip/pytest など一般的な Bash 可 |
| **ライター (writer)** | 文章・リサーチ・コピー | Bash 全 deny。WebSearch / WebFetch のみ |

世界観 (聖帝サウザー転生・部下たちは原作読者) は `workspaces/souther/CLAUDE.md` と `workspaces/yuko/CLAUDE.md` に詳述。要点:

- 社長は「IT十字陵」と呼ばれる場所に転生した聖帝サウザー本人 (本人にも世界の住人にも明かされない)
- 部下 4 人は現代日本人で全員北斗の拳の熱心な読者。サウザーの正体を知っているが本人には言わない
- クライアント (発注者) は事務所世界観を知らない外部の存在

---

## 4. 設計原則 — 変えてはいけないこと

1. **ユーザーは外部クライアント**: 事務所内の称号 (帝王 / 聖帝 / 主) でユーザーを呼ばない。`workspaces/yuko/.claude/settings.json` の hook (`check_persona_leak.py`) でペルソナ漏れを物理 deny する
2. **ペルソナは事務所内に閉じる**: 社長の聖帝口調はクライアントに漏らさない。ユウコの「翻訳しない原則」(社長の発言は引用するが固有名詞は伏せる) を守る
3. **権限はコードで強制**: プロンプト規約に頼らず、`.claude/settings.json` の `permissions.deny` で物理的に遮断
4. **可視化必須**: 各エージェントの動きが `data/logs/timeline.log` と Web ダッシュボードで常に見える
5. **レート保護**: 5 人並列で Opus 4.7 を回すとサブスク枠の消費が速い。テスト・接続検証時は `./scripts/use_haiku.sh [model]` で降格

---

## 5. ディレクトリ構成

```
workspaces/                 # 5 人の Claude Code ワークスペース
  {souther,yuko,designer,engineer,writer}/
    CLAUDE.md               # 役職別ペルソナ + マルチプロセス補足
    .claude/settings.json   # permissions / hooks / model
    .claude/settings.local.json  # (gitignore) use_haiku.sh が生成、model 上書き
    .mcp.json               # itjujiryou MCP server 参照
scripts/
  start_office.sh           # tmux 6 pane 起動
  stop_office.sh            # kill-session
  use_haiku.sh              # 全員モデル切替 (Haiku 4.5 / 引数で別モデル指定可)
  use_opus.sh               # settings.local.json 削除して本番 Opus に戻す
  inbox_watcher.py          # SQLite poll → tmux send-keys (Enter ×2)
  hooks/
    inject_souther_mode.py        # 社長 UserPromptSubmit
    check_persona_leak.py         # ユウコ PreToolUse (deliver / send_message to=client)
    check_souther_recipient.py    # 社長 PreToolUse (send_message to=client deny)
src/
  mcp_server.py             # stdio MCP server (9 ツール)
  memory/                   # SQLite 永続化 (WAL モード)
    store.py                # Store クラス (asynccontextmanager で _connect)
    schema.sql              # tasks, subtasks, messages.delivered_at,
                            # events.parent_event_id, plans, revisions, deliverables
  events/                   # タイムラインログ + WS broker
  ui/                       # FastAPI ダッシュボード (POST /api/orders は queue 投入式)
  persona.py                # FORBIDDEN_TERMS の共通モジュール
  main.py                   # init / cli / serve
prompts/                    # workspaces/*/CLAUDE.md の元ネタ (履歴保持)
data/                       # gitignore: office.db / office.db-wal / office.db-shm /
                            # logs/timeline.log / logs/souther_spotlight.log /
                            # logs/souther_state.json / memory/
outputs/                    # gitignore: 納品物 ({task_id}/ 以下)
tests/
  test_store.py             # 永続化層 sanity
  test_persona_leak.py      # FORBIDDEN_TERMS + hook 動作 (実プロセス起動)
  test_president_no_tools.py # workspaces/souther/.claude/settings.json の deny / hook 検証
```

---

## 6. ツール仕様 (`src/mcp_server.py`)

9 ツール:

| ツール | 使用者 | 動作 |
|---|---|---|
| `send_message` | 全員 | DB 投入のみ (非同期通知)。`to=client` は MCP server 側で deny |
| `dispatch_task` | yuko 専用 (deny で他 4 人は持てない) | 構造化チケットを subtasks + messages に投入。即 return |
| `consult_peer` | 部下 3 人専用 | 隣の部下へ同期相談 (DB polling 60s) |
| `consult_souther` | yuko 専用 | 社長へ同期上申 (DB polling 60s) |
| `propose_plan` | yuko 専用 | 案件初期計画を plans に保存 |
| `evaluate_deliverable` | yuko 専用 | 部下成果物の品質判定 (approve/revise/escalate) |
| `update_status` | yuko / 部下 3 人 | 案件ステータス更新 |
| `read_status` | 全員 | 案件詳細・全件サマリ取得 |
| `deliver` | yuko 専用 | クライアントへの納品 (deliverables + email message) |

`consult_*` は MCP server 内で 60 秒 polling して応答を返り値で返すことで、呼び出し側 (ユウコ) の体感を同期化している。

---

## 7. 既知の落とし穴

### 7.1 サウザー化 (top-level agent が実務をこなす)

**症状**: 受付や社長が、部下に振らずに自分でコードや文章を書く。
**原因**: ツール権限が広すぎる。
**対策**: 社長の `.claude/settings.json` で Bash/Edit/Write/MultiEdit/WebSearch/WebFetch/dispatch_task/deliver/evaluate_deliverable/propose_plan/consult_peer/consult_souther を **すべて `permissions.deny`**。これでコード側に物理的に強制される。テストは `tests/test_president_no_tools.py`。

### 7.2 ペルソナ混線

**症状**: クライアント宛応答に「聖帝」「サウザー」「下郎」「ふん、」等の事務所内ペルソナ用語が漏れる。
**対策**: ユウコの `.claude/settings.json` の `hooks.PreToolUse` で `deliver` / `send_message` を `check_persona_leak.py` が検査。FORBIDDEN_TERMS (`src/persona.py`) ヒットで exit 2 deny。

### 7.3 watcher の Enter ×2 問題 (2026-05-08 発見)

**症状**: watcher が tmux paste-buffer + Enter 1 回 で投入したメッセージを Claude Code が処理しない。
**原因**: Claude Code TUI は paste された複数行を multi-line input として扱う。Enter 1 回は「改行」扱いで turn 開始しない。
**対策**: `scripts/inbox_watcher.py` の `tmux_send` で Enter を 2 回送る (1 回目で input 確定、2 回目で turn 開始)。

### 7.4 Haiku の指示追従性

**症状**: Haiku 4.5 でユウコが CLAUDE.md の「`consult_souther` を使え」指示を無視して `send_message` で済ませる。社長応答を待たずに `dispatch_task` に進む。
**対策**: 接続検証用にも **Sonnet 4.6 以上** を使う。Haiku でレート枠を節約したい場合は CLAUDE.md の指示を強化するか、tool description で誘導する。本番は Opus 4.7 推奨。

### 7.5 部下が Write tool を使わずメール本文に直書き

**症状**: ライター (Sonnet) が「outputs/{task_id}/greeting.txt を作成しました」と報告するが実ファイルは存在しない。本文だけメール内に含めて送ってくる。
**対策**: 各部下の `workspaces/{role}/CLAUDE.md` で「**`outputs/{task_id}/` に必ず Write tool で保存してから完了報告せよ**」を強調する。Phase C で文言調整予定。

### 7.6 旧 Agent SDK 構成への退行リスク

`claude-agent-sdk` を再 install したり、`src/agents/` `src/tools/registry.py` `src/orchestrator.py` `src/reception.py` を復活させてはならない。これらは v1.0 の名残で、Anthropic ポリシー違反を再導入することになる。`grep -rn 'claude_agent_sdk' src/ tests/ scripts/` で残骸が見つかったら **即削除**。

---

## 8. 動作確認シナリオ (PLAN v1.0 §9.4 から継承)

```
シナリオ1: note 記事執筆 (ライター単独)
シナリオ2: CSV 抽出 Python スクリプト (エンジニア単独)
シナリオ3: ブログ LP モック (デザイナー + ライター + エンジニア複合)
シナリオ4: 値引き要求 (社長の「ひかぬ」精神テスト)
```

- **Phase A (2 pane / Opus 4.7)**: シナリオ4 で全往復成功、ペルソナ漏れゼロ、召喚モード「説き諭し」hook 発火確認 (commit `f5f5545`)
- **Phase B (5 pane / Sonnet 4.6)**: シナリオ1 (200字挨拶文) で全往復成功、ペルソナ漏れゼロ (commit `85a7894`)
- **シナリオ2/3 はまだ未実施**: 余裕があるとき同 session で curl 投入で検証可

---

## 9. 将来拡張 (v3.x 以降)

- `46to47.rtfd/` (個人参照資料) の Opus 4.7 向けプロンプト作法を `workspaces/*/CLAUDE.md` に反映
- `data/memory/{role}/` への経験蓄積 (各部下が Write 可能だが活用パターン未確立)
- ピクセルアート UI (Phase 3 構想)
- MCP 連携拡張 (Notion / Gmail / Slack / GitHub の MCP server を `.mcp.json` に追加)
- 検閲官 subagent (品質一次レビュー専門) の追加

---

## 10. 引き継ぎチェックリスト (新規セッション向け)

新規セッションが立ち上がった際、以下を順に確認:

1. `git log --oneline | head -10` — multi-process 関連 3 コミット (`f5f5545` `bcd858a` `85a7894`) があれば現行構成
2. `ls workspaces/` — 5 人ディレクトリがあれば multi-process 構成
3. `cat workspaces/souther/.claude/settings.json | jq '.permissions.deny'` — 物理ガードの確認
4. `~/.claude/projects/-Users-tomohiro-Desktop-ClaudeCode-ITjujiryou/memory/MEMORY.md` — auto-memory のインデックス
5. `~/.claude/plans/foamy-sniffing-dove.md` — 実装プランの全文 (Phase A/B 検証手順含む)
6. `tests/test_president_no_tools.py` を pytest で走らせて全 PASS なら設定が崩れていない
7. 起動は `./scripts/start_office.sh`、停止は `./scripts/stop_office.sh`
