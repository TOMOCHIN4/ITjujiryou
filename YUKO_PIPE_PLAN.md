# YUKO_PIPE_PLAN — ユウコ 3 パイプ分割 実装計画

> **このファイルの位置付け**: `docs/v2_carryover_candidates.md §2.7` で提案された「ユウコ自身のセッションを対話パイプ単位で区切る」設計の実装計画。完了後は内容を `SPEC.md` / `workspaces/yuko/_modules/workflow.md` へ昇格させ、本ファイルは削除する。
> **作業ブランチ**: `feat/yuko-3pipe`
> **想定セッション数**: 2–3 セッション (Phase 1 → 2 → 3)

---

## 1. 背景 — なぜやるか

### 1.1 観測された問題 (`docs/case_log_analysis/2026-05-14_15.md` §2.2)

5/15 ログ実測値:

| 指標 | 5/15 ユウコ | 他 role 比較 |
|---|---|---|
| tool_use / 案件 | **53** | サザン 6, writer 17, designer 52, engineer 21 |
| 内訳 | Read ×12 / Write ×6 / evaluate ×6 / record_thought ×5 / Bash ×4 / Agent ×4 / dispatch ×3 / consult_souther ×3 | — |
| 1 ターン重さ | **4–5 分 / 11–14k tokens** | サザン 1 文応答 / 200 tokens |
| 上申本文長 | 30–50 行 (`【概要】【規模】【納期】【担当】【内容】【リスク】【ペルソナ整合】`) | サザン応答は 1–2 文 (`ふん、許す`) |

**根本症状**: ユウコ pane の context が混雑する。原因は 3 つの異質な対話相手 (クライアント / 社長 / 部下) の文脈を同じセッションに積み上げていること。具体的には:

- クライアント向けの敬語・要件確認に費やした context が、その後の部下向け dispatch に残ったまま
- 社長への上申本文は格調と慎重さが要るが、その文体が部下向け directive にも持ち越される
- 納品物確認のための outputs/ 系 Read が積み上がり、後続の社長上申時に context bloat

### 1.2 設計提案 (`v2_carryover_candidates.md §2.7`)

ユウコの対話を 3 パイプに分け、パイプ切替時に context を整理する:

| パイプ | 対話相手 | 主な動作 | 想定 message_type (from/to) |
|---|---|---|---|
| **P1 対クライアント** | UI 経由 visitor | 受注 / 要件確認 / 納品報告 | from=client, to=client (`new_order`, `deliver`) |
| **P2 対社長サザン** | sazan pane | 上申 / curator / 承認受領 | `consult_souther`, `approval_request`, `memory_approval_request`, `curator_request`, `curator_response`, `memory_approval`, `memory_finalized`, `curator_trigger` |
| **P3 対社員三兄弟** | writer/designer/engineer pane | 発注 / report 評価 / 統合 | `dispatch`, `report`, `memory_proposal` |

**設計上の核心**: パイプ切替時に **ハンドオフファイル** で最小情報を受け渡す。context を捨てても次パイプで困らないこと。

### 1.3 既存システムとの関係

| システム | 役割 | 3 パイプとの関係 |
|---|---|---|
| `data/memory/yuko/_scratch/{case_id}/` | 案件中の作業メモ (Step F で整理) | **継続使用**。重複させない |
| `data/memory/company/_proposals/{case_id}.md` | 会社記憶昇格候補 (サザン儀礼承認待ち) | **継続使用**。重複させない |
| `outputs/{task_id}/` | 部下成果物 (deliverable) | **継続使用**。ハンドオフ refs 先 |
| `data/yuko_handoff/{case_id}/` | **新規**。パイプ間引き継ぎ専用 | 追加 |
| SQLite messages | 真実源 (タスクの状態) | **継続使用**。ハンドオフは「読みやすさ + 規律」の補助層 |

ハンドオフファイルは **真実源ではない** (DB が真実源)。ユウコ自身が「次パイプで何を読めば即動けるか」を高速化するための **chunked context cache**。

---

## 2. 実装手段の選択

`v2_carryover_candidates.md §2.7` の 3 案:

| 案 | 内容 | リスク | コスト |
|---|---|---|---|
| (α) `/clear` + パイプ別ロードテンプレ | 同一 pane で `/clear` → 次パイプ初期プロンプト | Claude Code TUI に slash command を tmux send-keys で叩く挙動が未検証 | 中 |
| (β) tmux pane 分離 | yuko を 3 pane に増殖 (P1/P2/P3) | OAuth セッション 3 倍 / watcher routing 全面改修 / 現行設計覆す | **高** |
| (γ) ハンドオフファイル経由の規律ガードのみ | pane も /clear もせず、ユウコが「いまどのパイプか」を意識 | context は完全には切れない (緩和のみ) | **低** |

### 2.1 採用案 — (γ) を Phase 1 で先行、(α) は Phase 3 で検証

理由:

1. **段階的検証**: (γ) はコード変更最小 (watcher の prompt prefix + yuko workflow.md 追記) で、効果が出れば十分。出なければ (α) へ進む
2. **計測可能**: 5/15 ANALYSIS と同じ軸 (Read 数 / トークン / ターン時間) で前後比較できる
3. **(β) は採用しない**: yuko が 1 pane である前提は SPEC.md §2 / start_office.sh / inbox_watcher.py の前提となっており、覆すコストが効果を上回る
4. **(α) は単独運用の挙動検証が要る**: tmux send-keys 経由で `/clear` を投げた時に Claude Code TUI が再ロードする挙動を E2E で確認してから採用

**Phase 1 完了後**: メトリクス測定 → Read 数 / トークンが減らなければ (α) を Phase 3 で検証。

---

## 3. ハンドオフファイル schema

### 3.1 配置

```
data/yuko_handoff/{case_id}/
  to_client.md    # 「次に P1 へ戻る時にユウコ自身が読む」内容
  to_souther.md   # 「次に P2 へ向かう時にユウコ自身が読む」内容
  to_brothers.md  # 「次に P3 へ向かう時にユウコ自身が読む」内容
```

- ファイル名は **3 種類固定** (同パイプには上書き)。案件をまたいで履歴を残したい場合は `data/memory/yuko/_scratch/{case_id}/` 側に書く
- どのファイルも案件単位で完結。`case_id` ディレクトリで隔離
- ユウコ以外は Read しない (兄弟は `outputs/{task_id}/` を見る、サザンは `_proposals/{case_id}.md` を見る)

### 3.2 schema (`schema: yuko-handoff/v1`)

```markdown
---
schema: yuko-handoff/v1
case_id: <UUID>
to_pipe: P1|P2|P3
from_pipe: P1|P2|P3|new
created_at: <ISO8601>
ttl_hint: 24h        # 案件終了から N 時間で stale (GC は Phase 2 以降)
---

## サマリ
<案件の核を 1–3 行で。クライアント名 / 業種 / 規模 / 納期>

## 直前の状態
<どのパイプで何が起きたか。短い箇条書き 2–5 件>

## 次パイプでの必要アクション
<次パイプで実行すべき具体動作。1–3 件の bullet>

## 関連 path
- outputs/{task_id}/...
- data/memory/yuko/_scratch/{case_id}/...
- data/memory/company/_proposals/{case_id}.md (該当時のみ)

## 申し送り (任意)
<次パイプ向け留意事項。FORBIDDEN_TERMS 漏れ警告などはここに書かない — それは persona_guard の仕事>
```

- frontmatter は既存 `_proposal/v1` (mcp_server / inbox_watcher) と同じ簡易 YAML パーサ (`_parse_proposal_frontmatter`) で読めるよう `key: value` / `key: [a,b]` の 2 形式に限定
- 本文 4 セクション固定。「ユウコが書き忘れた節は空欄」を許す (規律ガードは Phase 2 以降で検討)

### 3.3 サイズ目安

- 1 ファイル 30 行以下
- 100 行を超えたら「context cache の意味を失っている」サイン → サマリ過剰の見直し
- 単純な事実 (案件 ID / path) は短く、判断の理由が重要

### 3.4 既存ファイルとの非重複ルール

| 内容 | 書く場所 |
|---|---|
| クライアント要件の生テキスト | SQLite `tasks.client_request` (mcp_server に既存) |
| 構造化チケット | SQLite `tasks.structured_ticket` (既存) |
| 部下成果物 | `outputs/{task_id}/` |
| サザン承認待ち proposal | `data/memory/company/_proposals/{case_id}.md` |
| 案件中の作業メモ (整理対象) | `data/memory/yuko/_scratch/{case_id}/` |
| **パイプ間引き継ぎ (次パイプで即動くための最小要約)** | **`data/yuko_handoff/{case_id}/`** ← 新規 |

ハンドオフファイルには「他所で参照可能な情報のサマリ + path」だけ書く。生データは入れない。

---

## 4. パイプ識別ロジック (watcher 側)

### 4.1 messages から pipe を導出するルール

incoming message (to=yuko) の属性から、ユウコが返答するべきパイプを決める:

| from_agent | message_type | 判定 pipe | 備考 |
|---|---|---|---|
| client | new_order / reply | **P1** | UI POST /api/orders 由来 |
| souther | approval / memory_approval / curator_response | **P2** | サザン応答 |
| system | curator_trigger / memory_finalized | **P2** | サザンへの橋渡し系 |
| writer / designer / engineer | report / consult_reply / memory_proposal | **P3** | 部下 report |
| yuko (自分) | thought / 自己メモ | — | 通常 watcher 経由で発生しない |
| (その他) | — | **P2** (デフォルト保守的) | 想定外メッセージは社長に escalation する流れ |

実装: `scripts/inbox_watcher.py` に `_pipe_for_message(msg) -> Literal["P1","P2","P3"]` を追加。`format_prompt()` の出力先頭に `[PIPE:P1]` 等のマーカーを付加 (既存 `[BACKSTAGE:curator]` sentinel と同じパターン)。

### 4.2 prompt prefix 注入

`format_prompt()` を以下に拡張:

```python
def format_prompt(msg: dict) -> str:
    pipe = _pipe_for_message(msg)  # "P1" | "P2" | "P3"
    pipe_tag = f"[PIPE:{pipe}]"
    # 既存形式 + 先頭 pipe_tag
    return (
        f"{pipe_tag}\n"
        f"新着メッセージ (msg_id={msg['id']}):\n"
        f"  from: {msg['from_agent']}\n"
        f"  type: {msg['message_type']}\n"
        f"  task_id: {task_id}\n"
        "---\n"
        f"{content}\n"
        "---\n"
        "このメッセージに対応してください。"
    )
```

**BACKSTAGE との直交**: `format_backstage_curator_prompt` は to=souther で `[BACKSTAGE:curator]` を付ける。P1/P2/P3 は to=yuko の prompt だけに付ける。両者が同じ prompt に混在することはない。

**post_deliver_trigger / curator_trigger の整合**: 
- `format_scratch_consolidation_prompt`: yuko 向け。P2 タグ (整理 → memory_proposal 経由でサザンへ繋がる業務) を付加
- `build_curator_trigger_content`: yuko 向け curator_trigger。P2 タグ
- 配信側 (`tmux_send` 直前) で統一的に `[PIPE:Px]` を付加するか、format 関数ごとに付加するかは Phase 1 詳細設計で確定

---

## 5. ユウコ側の規律 (workflow.md 追記)

### 5.1 新節: 「3 パイプ規律」

`workspaces/yuko/_modules/workflow.md` の `## 業務サイクル` 前後に新節として追加:

```markdown
## 3 パイプ規律 (2026-05-16 導入)

あなたへの prompt 先頭に `[PIPE:P1]` / `[PIPE:P2]` / `[PIPE:P3]` が付いています。これは今回の応答が「どの対話相手」向けかを示します。パイプを意識した上で context を最小化し、必要なら handoff ファイル経由で次パイプに引き継ぎます。

### パイプ別の責務

| パイプ | やる | やらない |
|---|---|---|
| P1 (対クライアント) | 受注 / 要件確認 / 納品メール | 部下指示文をここで起草しない (P3 で書く) |
| P2 (対社長サザン) | consult_souther / curator_* / memory_approval_request | 部下への dispatch をここで起こさない |
| P3 (対社員三兄弟) | dispatch_task / evaluate_deliverable / 部下 report 読解 | クライアント宛文書をここで書かない |

### ハンドオフファイル運用

パイプを切り替える「直前」に、次パイプで自分が読む内容を `data/yuko_handoff/{case_id}/to_{client|souther|brothers}.md` に書きます。schema は `schema: yuko-handoff/v1` (詳細は YUKO_PIPE_PLAN.md §3、後日 SPEC.md 統合)。

**書くタイミング**:
- P1 → P3 (受注完了 → 部下発注): `to_brothers.md` を Write してから dispatch_task
- P3 → P2 (部下 report 出揃った → 整理依頼 or 社長上申): `to_souther.md` を Write してから consult_souther
- P3 → P1 (全 approve → 納品): `to_client.md` を Write してから deliver
- P2 → P3 (サザン承認得た → 発注): `to_brothers.md` を Write してから dispatch_task

**書かないタイミング**:
- 同じパイプ内での連続応答 (例: P3 で writer から report 受領 → designer に追加 dispatch) は handoff 不要
- 単発応答で完結する場合 (例: P1 で受注確認だけして「承知しました、後ほど」で終わる) は不要

### コスト削減効果の見込み

5/15 ANALYSIS で観測された Read 12 / 1 ターン 14k tokens の重さは、主に「outputs/ を本体 Read で都度確認」が原因。3 パイプ規律と直交だが、P3 突入時に `to_brothers.md` で「どの outputs パスを参照すべきか」を整理しておけば、本体 Read が減らせる見込み。
```

### 5.2 既存記述との整合

- `_modules/workflow.md` Step F (記憶整理フロー) は変更なし。但し「Step F は P2 パイプ作業」と注釈追加
- `_modules/persona_guard.md` の FORBIDDEN_TERMS は変更なし。handoff ファイルは内部ファイルなのでクライアント露出しない
- CLAUDE.md (`workspaces/yuko/CLAUDE.md`) には「3 パイプ規律は `_modules/workflow.md` 参照」の 1 行追加だけ

---

## 6. Phase 分割

### Phase 1 — 最小実装 (1 セッション、コード + テスト + 規律ガード)

**ゴール**: ハンドオフファイル schema を確定、watcher が pipe マーカーを注入、yuko workflow.md に規律を追記、unit test 通る状態。

#### Phase 1 作業項目

| # | 内容 | 対象ファイル | 検証 |
|---|---|---|---|
| 1.1 | `data/yuko_handoff/` ディレクトリ追加 + `.gitignore` 設定 | `.gitignore` | ディレクトリ存在 |
| 1.2 | `_pipe_for_message()` 関数追加 + `format_prompt()` で pipe tag 注入 | `scripts/inbox_watcher.py` | unit test (1.5) |
| 1.3 | post_deliver / curator_trigger の prompt にも P2 tag 統一 | 同上 | 同上 |
| 1.4 | `workspaces/yuko/_modules/workflow.md` に「3 パイプ規律」節追加 | 該当ファイル | レビュー読み |
| 1.5 | `tests/test_inbox_watcher_pipe.py` 新規。pipe 判定 + prompt prefix 検証 | テスト追加 | pytest pass |
| 1.6 | (任意) ハンドオフ schema 検証テスト (frontmatter parser を共用) | `tests/test_yuko_handoff_schema.py` | pytest pass |

#### Phase 1 で **やらない** こと

- `/clear` 自動投入 (Phase 3 候補)
- ハンドオフファイルの GC (Phase 2 以降)
- pixel UI でのパイプ可視化 (将来案)

### Phase 2 — 運用 + メトリクス測定 (1 セッション、E2E スモーク)

**ゴール**: 1–2 件の実案件 (シナリオ 1 = 200 字挨拶文 + シナリオ 3 = LP モック複合) を回し、5/15 ベースラインと比較。

#### Phase 2 作業項目

| # | 内容 |
|---|---|
| 2.1 | `./scripts/start_office.sh` で起動、E2E 案件投入 |
| 2.2 | 案件中の `data/yuko_handoff/{case_id}/` 生成有無を確認 |
| 2.3 | tool_use 集計: Read 数 / record_thought 数 / 上申本文長 / 1 ターン時間 / トークン |
| 2.4 | 5/15 ANALYSIS と前後比較表を `docs/case_log_analysis/2026-05-16_pipe.md` に記録 |
| 2.5 | 期待値: yuko Read 12 → ≤ 8、上申本文 30–50 行 → 5–10 行 |

#### Phase 2 で確認すること

- ユウコが prompt の `[PIPE:Px]` タグに気付いて handoff を書くか (Opus 4.7 の指示追従に依存)
- handoff ファイルが冗長化しないか (30 行目安を守れるか)
- 同一案件で `to_brothers.md` を複数回上書きしても規律が崩れないか

### Phase 3 (条件付き) — `/clear` 自動化検証

**発火条件**: Phase 2 で Read 数の削減効果が不十分 (例: 12 → 10 程度) だった場合のみ。

#### Phase 3 仮設計

- watcher が pipe を切り替える際、tmux send-keys で `/clear` を投入してから prompt を流す
- yuko 側は `/clear` 後に CLAUDE.md / workflow.md / handoff ファイルを再ロードする (Claude Code の通常起動シーケンス + handoff Read)
- 未検証部分: tmux send-keys で送った `/clear` を Claude Code TUI が slash command として認識するか、ただの文字列として扱うか
- 検証手順: 1 pane で手動実験 → うまく動けば watcher に組込

このフェーズに進む判断は Phase 2 メトリクス結果を見てから。

---

## 7. リスクと対策

| リスク | 影響度 | 対策 |
|---|---|---|
| ユウコが `[PIPE:Px]` タグを無視して旧フロー継続 | 中 | workflow.md の優先順位を上げる。本プロジェクトは Opus 4.7 固定 (SPEC.md §4-5「モデル固定」) なので指示追従性は最低限担保される前提 |
| handoff ファイルが冗長化して 100 行超え | 低 | Phase 2 で観測、超過なら schema に「セクションごと行数上限」を追記 |
| pipe 識別の取りこぼし (想定外 message_type) | 中 | デフォルト P2 (社長 escalation) に倒す。新規 message_type 追加時はテストで死ぬ |
| `/clear` がうまく動かず (Phase 3) | 低 | Phase 3 は条件付き。動かなければ (γ) のままで運用継続 |
| handoff schema が `_proposal/v1` と紛らわしい | 低 | schema 名を `yuko-handoff/v1` で完全に分離。既存パーサは共用しない (分けて書く) |
| 既存テスト (test_inbox_watcher_curator) との衝突 | 低 | `format_prompt()` 変更で `test_format_prompt_does_not_have_sentinel` が落ちる可能性 → pipe tag は `[PIPE:Px]` 形式で `[BACKSTAGE` を含まないので一旦 OK。回帰テストで確認 |

---

## 8. 変更ファイル一覧 (Phase 1 のみ)

```
scripts/inbox_watcher.py            # _pipe_for_message + format_prompt 拡張
workspaces/yuko/_modules/workflow.md  # 「3 パイプ規律」節追加
tests/test_inbox_watcher_pipe.py    # 新規 (pipe 判定 + prompt prefix)
tests/test_yuko_handoff_schema.py   # 新規 (frontmatter 検証、任意)
.gitignore                          # data/yuko_handoff/ を追記 (必要なら)
YUKO_PIPE_PLAN.md                   # 本ファイル (Phase 1 完了で更新)
```

予想差分行数: +250 / -10 行 (テスト含む)

---

## 9. 検証手順 (E2E)

```bash
# Phase 1 完了後
.venv/bin/pytest -v tests/test_inbox_watcher_pipe.py tests/test_inbox_watcher_curator.py

# Phase 2 (実案件)
./scripts/start_office.sh
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"text": "200字程度の挨拶文を1本書いてほしい"}'
# data/logs/dev/2026-05-16_pipe_phase2/ に jsonl + pane.txt を採取
# tool_use 集計し YUKO_PIPE_PLAN.md (or docs/case_log_analysis/2026-05-16_pipe.md) に記録

./scripts/stop_office.sh
```

---

## 10. 完了条件

| Phase | 完了条件 |
|---|---|
| 1 | pytest 全 pass、`format_prompt` に pipe tag、workflow.md 更新済 |
| 2 | E2E 案件 1 件以上完遂、handoff ファイル生成確認、メトリクス前後比較記録 |
| 3 (条件付き) | `/clear` 経路の E2E 動作確認、または不採用判断の記録 |

最終的に Phase 1–2 が完了した時点で、本ファイルの内容を `SPEC.md` (記憶システム §10 同等の章) と `workspaces/yuko/_modules/workflow.md` に統合し、本ファイルは削除。`PLAN.md` から本 PLAN への参照リンクも撤去する。

---

## 11. 参照

- `docs/v2_carryover_candidates.md §2.7` — 設計提案の原典
- `docs/case_log_analysis/2026-05-14_15.md` §2.2 — context bloat の実測根拠
- `SPEC.md` §10 — 記憶システム (既存の二重構造との整合先)
- `workspaces/yuko/_modules/workflow.md` — ユウコ業務サイクル本体
- `scripts/inbox_watcher.py:format_prompt / format_backstage_curator_prompt` — prompt 整形の既存パターン
- `tests/test_inbox_watcher_curator.py` — テスト雛形
- 旧 v2 master spec D1 (`git show 261a1a9:aitei_juujiryou_v2_master_specification.md` で参照可) — 「3 分割」の原型
