## レビュー時 self/memory 書込ルール

> **Phase 1 時点ではこの記述のみ。実体の書込機構 (memory_write ツール、`data/memory/yuko/` への persistence) は Phase 3b 以降に導入予定**。本書は Phase 3b 以降のために**書き方の規約**を先に固めるためのもの。

### なぜ書くか (D3 の意図)

レビュー段階 (Step C: `evaluate_deliverable`) で得た知見 — どの部下が何をどう間違えがちか、どの品質基準が案件タイプ別に効くか、クライアントがどんな反応をするか — は、次回以降の案件で **同じ過ちを繰り返さない / 同じ強みを再現する** ための財産です。これを `record_thought` の独白だけで消費すると、あなたが交代したり別セッションになったときに失われます。

### 書込タイミング

Step C で `evaluate_deliverable(decision=...)` を呼んだ **直後**。decision に関わらず (approve / revise / escalate_to_president) 必ず書きます。

### 書込先 (Phase 3b 以降の予定)

- 自分の個人記憶: `data/memory/yuko/review_notes/{案件ID}.md`
- 会社記憶への提案 (再利用価値が高いと判断したとき): `data/memory/company/_pending/{タイムスタンプ}-yuko-{要約}.md` → サザン儀礼承認後に `data/memory/company/` 本体へ反映 (Phase 4 HOOK P6 で自動化)

### フォーマット (Markdown frontmatter + 本文)

```markdown
---
case-id: 2026-05-13-kataoka-dental
subtask: 採用 LP コピー初稿
担当: writer (ハオウ)
decision: revise
round: 0
date: 2026-05-13
---

## 修正パターン
- 訴求軸 4 本のうち優先順位 1 番 (リコール 60 分) がヒーローで埋もれていた
- ハオウのコピーは詩情強めだが、CTA への接続が弱い傾向 (過去 3 案件中 2 件で同じ指摘)

## 品質基準の詳細化
- 求人 LP のヒーローキャッチは「ターゲット読者のことばで訴求軸 1 番を再現」が最低ライン
- サブコピーは「読者の不安に対する agency 側の答え」を 1 文で

## クライアント反応 (推定 or 実測)
- 院長の好み: 大阪弁混入は不要、ノーマル文体希望 (kataoka-dental の場合)
- 「色は茶色基調」「人柄重視」が頑なな部分 (client_persona §8.1 と整合)

## 次回への申し送り
- ハオウに発注する求人コピーには「ヒーローでの訴求軸 1 番の直接表現」を要件に明示すること
- 印刷物の入稿仕様は当社作業外 (社労士・印刷会社レビュー必須) と申し送りに必ず明記
```

### 書込粒度の目安

- 1 件あたり 100〜300 字。本文は要点のみ
- 1 案件で複数 subtask があれば、それぞれ別ファイル
- 同じ部下に対する同じ指摘パターンが 3 回以上出てきたら、自動で「会社記憶への提案」候補に格上げ (`_pending/` へコピー)

### Phase 1 / Phase 3b / Phase 4 の役割分担

| フェーズ | やること |
|---|---|
| **Phase 1 (今)** | この `review_memo.md` ファイルの存在のみ。実体は書かない。実装着手前に **書き方の規約を固めて** おくのが目的 |
| **Phase 3a** | ユウコ 3 セッション分割 (D1) — 統合セッションでこの規約を参照する |
| **Phase 3b** | 兄弟レビュー/実行分離 (D2) — レビュー段階で生まれた知見をこの規約フォーマットで self/memory に書き込む。`memory_write` ツール (新規) または Write tool を `data/memory/yuko/review_notes/` に直接書く形式 |
| **Phase 4** | HOOK 群 (D7) — `company_memory_write` HOOK が `_pending/` から本体への反映を担う |

### 兄弟 (haou / toshi / senshirou) 側のルール

兄弟は **修正指示を受けた直後** に、`data/memory/{role}/review_received/{案件ID}.md` に「何を直したか」「次回への学び」を 1 件書く。フォーマットは同じ frontmatter 形式で簡素化したもの。詳細は各兄弟の `CLAUDE.md` を参照。

**Phase 1 時点では兄弟側も記述のみ。実体の書込は Phase 3b 以降**。
