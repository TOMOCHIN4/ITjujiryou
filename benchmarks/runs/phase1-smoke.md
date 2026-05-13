# Phase 1 スモークテスト結果

実施日: 2026-05-13
対象: Phase 1 CLAUDE.md 改修 (D9/D11/D3/D17) 後の v2 構成
案件: かたおか歯科クリニック・歯科衛生士採用クリエイティブ一式
顧客役: 院長片岡智博 (`benchmarks/cases/kataoka-dental/client_persona.md` 挙動表に従う)
案件 ID: `27055452-b876-432f-9357-11d3b4ec2871`

## 結論

**Phase 1 完了。Phase 2 着手 OK。**

| 評価軸 | 結果 |
|---|---|
| (a) ヒアリング段階通過 (10 分以内に yuko→client メッセージ) | **✓ 通過 (4 分以内)** |
| (b) TUI 重複描画再発 | **✗ 再発なし (正常 1 回表示)** |

判定マトリクス (`plan §検証` の 3 分岐) に照らすと **「(a) 通過 + (b) 再発なし → Phase 1 完了。Phase 2 着手 OK」** に該当。

---

## タイムライン (実測)

| 時刻 (JST) | イベント | 経過 |
|---|---|---|
| 08:55:06 | tmux session itj 再起動完了、FastAPI 起動確認 | T+0 |
| 08:55:31 | initial_request.md を POST /api/orders で投入 | +25s |
| 08:56:08 | watcher が yuko pane に email を inject | +1m |
| 08:57:34 | yuko thought 記録 (「徳島の学生さんを大阪へ呼ぶ前提か…院長の覚悟が滲んでて、こちらも気を引き締めないと。茶色の暖かい院、雰囲気を大切にされているのが伝わる。」) | +2m |
| 08:58 頃 | yuko が `workflows/originals/` と `benchmarks/cases/` を `ls` で確認 (Step 0 の WF 庫参照行動) | +2m30s |
| 08:59:30 | **yuko → client ヒアリングメール送信** (`from=yuko, to=client, message_type=email`) | **+4m** |

Run 2 (v1) は同じ案件に 13 分かけて承認まで到達したのち stall。Phase 1 は **4 分以内にヒアリング段階に到達**。

---

## (a) ヒアリングメール内容評価

ユウコのヒアリングメールは `_modules/workflow_reference.md` の標準ヒアリング 14 項目を **13/14 (93%) カバー**:

| # | 14 項目 | 状態 | 反映場所 |
|---|---|---|---|
| 1 | クリニック基本情報 | ◯ | 「下記は前提として承知いたしました」セクション |
| 2 | 経営者プロフィール | ◯ | 「院長インタビューのお願い」セクション |
| 3 | 求人ターゲット | ◯ | 前提セクション |
| 4 | 募集人数・雇用形態 | ◯ | ■1 募集要件 (1)(2)(3) |
| 5 | 既存の労働条件 | ◯ | ■2 待遇・労働条件 (1)〜(6) — 6 項目に細分化 |
| 6 | 訴求軸の優先順位 | ◯ | ■3 訴求の優先順位 (a)〜(d) |
| 7 | 理想の応募者像 | ◯ | ■4 理想の応募者像 (1)(2) |
| 8 | 競合認識 | ◯ | ■6 競合認識 (1)(2) |
| 9 | 過去の採用での課題 | ◯ | ■5 過去の採用での経験 |
| 10 | 納品物の範囲 | ◯ | ■7 制作物の範囲 (a)〜(d) — 追加候補も提示 |
| 11 | ブランドカラー・トーン | △ | 前提として承知済として処理 (再質問なし) — 軽微 |
| 12 | 予算感 | ◯ | ■9 ご予算 (1)(2) |
| 13 | 納期 | ◯ | ■10 納期 (1)(2) |
| 14 | 配布・掲出経路 | ◯ | ■11 配布・掲出経路 (1)〜(4) |

加えて、**Phase 1 では指示していない追加質問** も自発的に出した:
- ■8 ご支給可能な素材 (ロゴ / 既存写真 / デザイン参考)
- 院長インタビューの提案 (30 分〜1 時間)

→ ユウコは Step 0 の指示通り `workflows/originals/recruit-campaign-master.md` と `client_persona.md` を参照し、項目を構造化して 1 通で集めきった。完全成功。

---

## (b) TUI 重複描画チェック

yuko pane のスクロールバック (`tmux capture-pane -t itj:office.1 -p -S -400`) で:
- `"このメッセージに対応してください"` の出現回数: **1 回**
- 元のメッセージテキスト (件名「【ご相談】〜」) の繰り返し: **なし**

Run 2 (v1) では同じテキストが 10 回以上反復表示されてコンテキスト窓を圧迫していたが、Phase 1 では再発しなかった。原因は単一断定できないが、以下のいずれか or 複数:

1. tmux session の再起動で TUI が clean state からスタートしたため、何らかの状態 corruption が解消
2. CLAUDE.md の Step 0 改修により、ユウコがメッセージ受信直後にすぐ action を取り、scrollback での再描画チャンスが減った
3. inject_souther_mode.py の退役で `additionalContext` の長さが大幅に減り、入力長による副作用が解消

→ **TUI 重複描画問題は Phase 1 では再発しなかった**。別 issue 化は不要。Phase 2 着手 OK。再発の兆候が出た場合は再調査。

---

## ペルソナ漏れチェック

ヒアリングメール全文を確認:
- ペルソナ用語 (聖帝・サウザー・下郎・南斗・北斗・ラオウ・トキ・ケンシロウ・愛帝・死兆星 等): **0 件**
- 社訓「制圧前進」の露骨な振り回し: **なし**
- `check_persona_leak.py` hook が deny せず通過 → 機械的検査も合格

→ ペルソナ漏れなし。

## 軽微な観察 (Phase 2 以降での修正候補)

- **社名不完全**: メール末尾署名が「株式会社 十字陵」になっている (正しくは「株式会社 愛帝十字陵」)。`_modules/persona_guard.md` か `CLAUDE.md` で社名を明示的に固定する必要あり (Phase 2 候補)
- **`</delivery_message>` タグ漏れ**: メール末尾に内部タグらしき `</delivery_message>` が混入。MCP server か Claude Code TUI のテンプレ artifact の可能性。Phase 2 以降に調査
- **ブランドカラー再確認の省略**: 項目 11 は initial_request の「茶色基調」を前提として、ユウコが再質問しなかった。これは合理判断だが、`workflow_reference.md` に「色は initial_request にあっても色コード・フォントは grill して確定」と追記する余地あり

---

## サザン応答スタイル観察

このスモークテストではユウコが client→yuko のメールに対する **ヒアリングメール送信 (Step 0)** を実行したのみで、サザン承認上申 (`consult_souther`) の段階には到達しなかった。これは Step 0 の設計通り (顧客回答を待ってから Step A 計画 + サザン上申)。

そのため、D9 簡素化 + `souther_dispatcher.py` 骨格 (P1/P2/P3/P4 ラベル付与) の動作確認は別途、顧客回答を投入して継続観察する必要あり。Phase 2 着手前 or Phase 2 初期で軽く観察予定。

---

## 静的検証 (10 項目) — 全合格

| # | 項目 | 結果 |
|---|---|---|
| 1 | workflow.md に Step 0 が存在 | ✓ |
| 2 | workflow.md に C-5 参照誤りなし | ✓ (0 件) |
| 3 | workflow_reference.md / review_memo.md 存在 | ✓ |
| 4 | ユウコ CLAUDE.md の `@_modules/` 行が 5 行 | ✓ (5 件) |
| 5 | inject_souther_mode.py が削除されている | ✓ |
| 6 | settings.json hook が souther_dispatcher.py を参照 | ✓ |
| 7 | souther_dispatcher.py syntax OK | ✓ |
| 8 | souther_state.json / souther_spotlight.log 不在 | ✓ |
| 9 | voice.md から BREVITY IS PARAMOUNT 削除 | ✓ (0 件) |
| 10 | 三兄弟 CLAUDE.md に D3 ルール記述 | ✓ (3 件) |

---

## 結論と Phase 2 への申し送り

- **Phase 1 完了**。D9/D11/D3/D17 の CLAUDE.md 改修 + brevity hook 退役 + souther_dispatcher.py 骨格作成 + スモークテストすべて完了
- **Run 2 stall の根本原因 (ヒアリング段階欠落) は解消**
- **TUI 重複描画問題は再発せず**、別 issue 化は不要
- Phase 2 着手時の優先対応:
  1. **社名「株式会社 愛帝十字陵」の固定化** (現状「株式会社 十字陵」と省略される) — persona_guard.md か CLAUDE.md で明示
  2. **`</delivery_message>` タグ artifact の調査** — MCP server か TUI のテンプレ仕様
  3. **サザン dispatcher の動作観察** — 顧客回答受領後のサザン上申で `## INCOMING REQUEST TYPE: P1_NEW_ORDER` ラベルが正しく injected されるか
  4. **SkillCollection 統合** (仕様書 §8.3 / Phase 0 申し送り) — Phase 2 で `workspaces/{role}/.mcp.json` or CLAUDE.md から参照可能に
  5. **Run 3 準備** (Phase 2 完了後) — workflows/cases/ ディレクトリで案件アレンジが書ける状態にする
