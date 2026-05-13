# サザン HOOK 棚卸し (Phase 0 Track C)

調査日: 2026-05-13
調査対象: `data/office.db` (2026-05-03 〜 2026-05-11 の全イベント・全メッセージ)
目的: 仕様書 v2 第 3 部 3.5「サザン HOOK の棚卸し」予備調査表を実ログで検証し、Phase 4 (整理 HOOK + company_memory_write HOOK + ユウコ門番) 実装の叩き台を確定する。

---

## 1. データの全体像

| 軸 | カウント | 内訳 |
|---|---:|---|
| `messages` (from=yuko, to=souther) | 44 | 全件 `message_type='approval_request'` |
| `messages` (from=souther) | 52 | `approval` 44 / `approval_response` 8 |
| `events.evaluate` | 31 | 仕様書言う `evaluate_deliverable` の実体 |
| `events.delivery` | 34 | client 宛 deliver の足跡 |
| `events.consult` | 5 | `consult_souther` + `consult_peer` 合算 |
| `events.plan` | 3 | `propose_plan` の足跡 |
| `events.dispatch` | 38 | `dispatch_task` の足跡 |

期間内に観察された案件は 43 件 (`messages` の `task_id` distinct)。代表的な案件種は ①短文 (挨拶/俳句/四字熟語) ②ミニ記事 (200-800 字) ③ HTML モック ④ Python スクリプト ⑤メッセージカードコピー の 5 系統。

## 2. ユウコ → サザン報告の出現パターン分類

実ログを 6 タイミングに分類した結果と頻度:

| # | タイミング | 観察頻度 | 代表行 (timestamp / 抜粋) | 仕様書 §3.5 表との照合 |
|---|---|---:|---|---|
| **P1** | 新規案件受注承認上申 | 32 件 (73%) | `2026-05-03T12:14:13` 「新規案件のご相談です…ビジネスメール冒頭…」 | ◯ 一致 |
| **P2** | 値引き/単価半額の裁定 | 7 件 | `2026-05-03T12:30:07` 「既存クライアント…値引きのご相談…価格を半額に」 | ◯ 一致 |
| **P3** | 納品前最終決裁の上申 | 1 件 (note 800 字案件) | `2026-05-03T14:46:56` 「両工程完了…納品前に社長の最終決裁を仰ぎます」 | ◯ 一致 (品質基準で迷う成果物) |
| **P4** | 発注取消 + 粗品要求の対応 | 3 件 | `2026-05-03T21:07:34` 「発注取消…事前準備費用は…加えて…」 | △ 表に未記載 — **新発見** |
| **P5** | ファイナルプラン承認 (v2 新規) | 0 件 | (v1 では概念なし) | — Phase 4 で導入 |
| **P6** | company 提案承認 (v2 新規) | 0 件 | (v1 では概念なし) | — Phase 4 で導入 |
| **P7** | 案件完了報告 (v2 新規) | 0 件 (現状は delivery event のみ) | (v1 では別フローで完結) | — Phase 4 で導入 |

### 2.1 新発見 (P4): 発注取消・粗品要求パターン

仕様書 §3.5 表に存在しないタイミング。3 件すべて同じ構文で発生:

> 「クライアントより発注取消のご連絡。事前準備費用はお支払いいただけるとのことですが、加えて…」

サザン応答も定型化していて、

> 「フ・・取消は許す。準備の血は一滴残らず回収せよ。だが粗品だと・・？ 斬られた側が斬った者に頭を垂れるか。アリの反逆も許さぬ聖帝…」

→ **「事前準備費は回収する／粗品提供は却下する」が確立した経営判断**。Phase 4 では P4 を独立タイミングとして扱い、その判断履歴を `company/memory/cancellation_policy.md` に集約する HOOK が必要。

### 2.2 P3 (品質迷い成果物) の希少性

期間内に 1 件のみ。これは「note 記事 800 字」という比較的大きい案件だったから発生したと推測。20 字挨拶や四字熟語クラスではユウコは決裁を仰がない。Phase 4 で P3 トリガーを HOOK 化するなら、**案件規模 (文字数 / 工程数) 閾値** をユウコ側で持たせる必要がある。

### 2.3 構造化イベント (`event_type`) の現状

| 仕様書記述 | v1 現状 |
|---|---|
| `revisions` 行追加 (escalate_to_president) | **存在しない**。`revisions` テーブルは空。escalate は messages の自由文に統合 |
| `evaluate_deliverable` 行追加 | `events.event_type='evaluate'` で記録 (31 件) |
| `propose_plan` 行追加 | `events.event_type='plan'` で記録 (3 件のみ — propose_plan ツール使用率が低い) |
| `final_plan_approved` 行追加 | **未実装** (v1 にプラン承認イベントなし) |
| `company_memory_write` | **未実装** |

Phase 4 着手時に **event_type の細分化** を先に行う必要あり (`approval_request_new_order` / `approval_request_discount` / `approval_request_cancellation` / `final_plan_proposed` / `final_plan_approved` / `company_proposal_pending` / `company_proposal_approved` / `task_completed`)。これがないと HOOK のトリガが「自由文プレフィックスマッチ」になり脆弱化する。

---

## 3. HOOK 候補 (Phase 4 実装の叩き台)

| タイミング | HOOK 名 (案) | 起動契機 | 処理内容 |
|---|---|---|---|
| P1 | `hook_p1_intake_sanitize` | `event_type='approval_request_new_order'` | client_request 文字列のサニタイズ + 過去類似案件のキーワード抽出 → ユウコの subagent に渡す |
| P2 | `hook_p2_discount_history` | `event_type='approval_request_discount'` | `data/memory/company/discount_decisions.jsonl` に <案件ID, 要求%, サザン判定, 日時> を append。直近 30 日の却下率を集計 |
| P3 | `hook_p3_quality_escalation` | `event_type='approval_request_quality_escalation'` | 直近 N 件の品質判定履歴を `data/memory/company/quality_calls.md` に集約しサザンに添える |
| P4 | `hook_p4_cancellation_policy` | `event_type='approval_request_cancellation'` (**新規追加**) | `data/memory/company/cancellation_policy.md` に判断履歴を append。粗品提供可否のルール抽出 |
| P5 | `hook_p5_plan_validator` | `event_type='final_plan_proposed'` | プラン MD の frontmatter (name/description/case-id/agents/workflows-referenced) を必須チェック。不備 → exit 2 deny |
| P6 | `hook_p6_company_memory_write` | `event_type='company_proposal_approved'` | ユウコがクリーン提案した MD を `data/memory/company/{name}.md` へ反映 + `data/memory/company/_last_write.log` にタイムスタンプ記録 |
| P7 | `hook_p7_post_deliver_cleanup` | `event_type='task_completed'` (deliver 後) | 各兄弟役を順次 `claude -p` で起動し self/memory 整理 + 蒸留昇格提案を促す。**deliver 完了を契機にした別プロセス起動**で `SessionEnd` 不可問題を回避 |

### 3.1 HOOK 失敗安全網 (仕様書 D15)

P6 後の `_last_write.log` タイムスタンプを、ユウコの次セッション (振り分け) 起動時にチェック。想定範囲 (例: 過去 5 分以内) に書き込みがなければ stderr に警告を出す。スクリプト案:

```bash
# scripts/hooks/check_company_memory_write.py
threshold_sec = 300
last = read_timestamp("data/memory/company/_last_write.log")
if (now - last) > threshold_sec:
    print(f"[WARN] company_memory_write HOOK may have failed (last write {now-last}s ago)", file=sys.stderr)
```

---

## 4. v1 → v2 移行で消える/変わるもの

- **brevity hook (`inject_souther_mode.py`)**: v0.13 の英語化禁止 + cap 注入。新ペルソナでは不要 (D17 退役)。撤廃と同時に `data/logs/souther_state.json` / `souther_spotlight.log` も Phase 1 で整理する
- **`check_persona_leak.py`**: 維持 (ペルソナ漏れ防止はクライアント向け納品で常時必要)
- **`check_souther_recipient.py`**: 維持 (社長 → client 直接送信の deny)
- **`inject_souther_mode.py` の SOUTHER_MODES テーブル**: 撤廃。代わりに「ユウコの伝令種別 → 対応 HOOK」マッピング表を `scripts/hooks/souther_dispatcher.py` で定義する

---

## 5. Phase 4 着手前の準備項目 (本書からの申し送り)

1. **event_type 細分化マイグレーション**: 現状の `approval_request` 単一型を 4 種に分割 (`_new_order` / `_discount` / `_cancellation` / `_quality_escalation`)。`src/memory/store.py` と `src/mcp_server.py` 両方の更新が必要
2. **追加テーブル**: `data/memory/company/discount_decisions.jsonl`, `cancellation_policy.md`, `quality_calls.md`, `_last_write.log` の生成スクリプト
3. **`scripts/post_deliver_hook.py`**: deliver イベント発火後に各兄弟役を `claude -p` で順次起動するエントリポイント。`inbox_watcher.py` から呼び出す形が現実的
4. **HOOK レジストリ**: `scripts/hooks/souther_dispatcher.py` がイベント種別を見て P1〜P7 の HOOK を呼び分ける単一エントリ。これがあると個別 hook ファイルが疎結合になる

---

## 6. 棚卸しの結論

- 仕様書 §3.5 の予備調査表は **5 タイミング中 3 タイミング (P1/P2/P3) を実ログで確認**。残り 2 (P5/P6/P7 = v2 新規) は当然未観測
- **追加発見 1 件 (P4: 発注取消・粗品要求パターン)** — 仕様書表に追加すべき
- 現状 v1 は **event_type 設計が粗く**、Phase 4 着手前に event_type 細分化マイグレーションが必須
- 撤廃対象 (brevity hook) と維持対象 (persona leak guard / recipient deny) を識別済み

Phase 1 着手時に本書を `workspaces/souther/_modules/` の補助資料として参照すれば、D9 (サザン二重構造化) の実装が「裏側 HOOK 群が何を担うか」明確になる。
