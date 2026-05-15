---
name: recruit-campaign-master
description: 求人クリエイティブ案件の全体マスター WF。受注→要件確定→各納品物 WF 起動→統合検収→納品の起点
case-id: null  # 案件アレンジ時に書き込む
agents: [yuko, haou, toshi, senshirou]
workflows-referenced:
  - landing-page-build
  - print-collateral-build
  - recruit-copywriting
  - brand-consistency-check
skills-referenced:
  - marketingskills/customer-research
  - marketingskills/competitor-profiling
  - marketingskills/marketing-psychology
  - skills/grill-me
  - skills/design-review
version: 1.0
status: original  # original / cases / distilled
---

# recruit-campaign-master

求人クリエイティブ案件全体を統括するマスター WF。ユウコが主担当として走らせる。本 WF は他の 4 本 (landing-page-build, print-collateral-build, recruit-copywriting, brand-consistency-check) を子として呼び出す。

## 適用範囲

求人クリエイティブを複数納品物 (LP / パンフ / ポスター / その他) で構成する案件。単一納品物の小案件には適用しない (recruit-copywriting 単体で済む)。

## 入力

- 顧客からの初期発注書 (例: `benchmarks/cases/{案件ID}/initial_request.md`)
- 案件 ID (例: `2026-05-13-kataoka-dental`)
- 兄弟 3 名の稼働可能状況

## 出力

- ファイナルプラン MD (`workflows/cases/{案件ID}/final_plan.md`)
- 統合納品物セット (LP + パンフ + ポスター + 申し送り書) を `outputs/{task_id}/` に配置
- 案件後の蒸留昇格提案 (各兄弟から最大 1 本)

## マクロフロー

### ノード 1: 初期受注 (ユウコ「受注/初期案」セッション)

- 起動契機: 顧客発注メール受信
- 入力: 初期発注書 + 全記憶検索結果 (会社記憶 + ユウコの個人記憶 + 三兄弟の個人記憶を **subagent 経由** で要約取得) + WF 庫 (本 WF 含む)
- アクション:
  1. Skill `marketingskills/customer-research` を実行 → ターゲット読者プロファイル草稿
  2. Skill `marketingskills/competitor-profiling` を実行 → 競合 (他歯科求人 / 衛生士特化サイト) 認識整理
  3. Skill `skills/grill-me` を起動 → 顧客発注書から **意図的に曖昧な部分** を抽出し、顧客への追加質問リストを作成
  4. ユウコが顧客と質疑応答 (1 セッション内で完了。通常 5〜10 ターン)
  5. 引き出すべき要件 (case 毎に変動するが、求人案件のデフォルトは下記参照) を `client_persona §8.3` に倣ったチェックリストで埋める
- 出力: `workflows/cases/{案件ID}/initial_plan.md` (frontmatter + マクロ要件 + 引き出した 14 項目)

#### 求人案件のデフォルト・ヒアリング 14 項目

1. クライアント基本情報 (所在地 / 規模 / 開業年 / スタッフ構成)
2. 経営者プロフィール・経営哲学
3. 求人ターゲット (大学・学部・学年・地域)
4. 募集人数・雇用形態
5. 既存の労働条件 (給与 / 休日 / 残業 / 福利厚生 / 補助制度)
6. 訴求軸の優先順位 (上位 3〜4 本)
7. 理想の応募者像 (人柄 vs 技術 vs 経験)
8. 競合認識
9. 過去の採用での課題・傷
10. 納品物の範囲 (LP / パンフ / ポスター / 動画 / SNS 素材 / 他)
11. ブランドカラー・トーン&マナー (内装写真 / ロゴ / 既存 Web を参考に)
12. 予算感 (1 案件あたり / 広告予算は別か含むか)
13. 納期 (本格採用活動開始からの逆算)
14. 配布・掲出経路 (大学掲示板 / 合説 / SNS / 求人サイト / DM)

### ノード 2: 兄弟レビュー × 3 (haou, toshi, senshirou が並列レビュー)

- 起動契機: ノード 1 完了で `initial_plan.md` 確定
- 入力: `initial_plan.md` + 各自の個人記憶 (subagent 経由) + 会社記憶 (subagent 経由)
- アクション (各兄弟):
  1. 自分の専門領域 (ハオウ=コピー / トシ=デザイン / センシロウ=Web 実装) から実現可能性をチェック
  2. 違和感や代替案があれば指摘
  3. **承認 or 修正案 + 理由を self/memory に書き込む** (D3 ルール)
  4. ユウコに応答メッセージで通知
- 出力: 各兄弟から 1 メッセージ (承認 or 修正案) + self/memory への 1 ファイル追加

### ノード 3: 統合 (ユウコ「統合」セッション)

- 起動契機: 3 兄弟全員のレビュー応答受信
- 入力: `initial_plan.md` + 3 兄弟のレビュー応答 + 記憶検索 subagent (過去類似ケース)
- アクション:
  1. 矛盾を解決 (例: ハオウが「コピーは詩的に」、センシロウが「LP の文字数を絞れ」と言ったら、ユウコが折衷案)
  2. 各納品物の担当を確定 (LP=トシ+センシロウ+ハオウ、パンフ=トシ+ハオウ、ポスター=トシ+ハオウ)
  3. 各納品物の WF を選定 (landing-page-build / print-collateral-build / recruit-copywriting)
  4. マクロフロー (どの納品物を直列/並列で進めるか) を確定
  5. 統合検収用に `brand-consistency-check` を最後に走らせる予定を組む
- 出力: `workflows/cases/{案件ID}/final_plan.md` (ファイナルプラン MD、frontmatter + マクロ + ミクロ WF 参照)

### ノード 4: サザン儀礼承認

- 起動契機: ノード 3 完了
- 入力: `final_plan.md`
- アクション:
  1. ユウコがサザンに `consult_souther` で「ファイナルプラン承認の上申」
  2. サザンが「制圧前進」儀礼応答 (中身は審査せず承認)
  3. 内部 HOOK `hook_p5_plan_validator` が frontmatter を必須項目チェック (不備なら deny)
- 出力: 承認 ack。ユウコは応答受領時点で次ノードに進む (HOOK 完了を待たない)

### ノード 5: 振り分け / 監督 (ユウコ「振り分け/監督」セッション)

- 起動契機: サザン承認応答受領
- 入力: `final_plan.md` + 実行状態
- アクション:
  1. ファイナルプラン本文を LLM が解釈 (パーサ・実行エンジンは使わない、§4.4)
  2. 各納品物の WF (landing-page-build / print-collateral-build / recruit-copywriting) を **子 WF として起動**
  3. 並列実行可能なノードは並列に、依存関係のあるノードは直列に
  4. 各兄弟の進捗を SQLite の messages / reports / status_change から監視
  5. 兄弟から「クライアントへの追加質問が必要」と上がってきたら、ユウコがクライアントに代行で質問 (顧客との窓口は常にユウコ)
- 出力: 各納品物が `outputs/{task_id}/` に揃った状態

### ノード 6: 統合検収

- 起動契機: 全納品物揃った
- 入力: 全納品物 + ファイナルプラン
- アクション:
  1. WF `brand-consistency-check` を起動
  2. トーン&マナー、訴求軸の一貫性、求人法令上の表記、転居前提との整合性を横串チェック
  3. 不整合あれば該当兄弟に差し戻し (最大 2 ラウンドで決着)
- 出力: 検収 OK 済み納品物セット

### ノード 7: 申し送り書作成 + 納品

- 起動契機: ノード 6 検収 OK
- アクション:
  1. ユウコが申し送り書を作成 (各納品物の意図 / 前提条件 / 修正フロー / 印刷入稿時の注意 / 求人法令の留意点 / 後続施策の提案 — `rubric.md` 軸 2 の 7 項目を満たすこと)
  2. `deliver` ツールで顧客にメール送信
- 出力: 納品完了 (deliver event 記録)

### ノード 8: 整理 HOOK (deliver 完了契機、別プロセス)

- 起動契機: ノード 7 の deliver 完了 (`scripts/post_deliver_hook.py` で別プロセス起動)
- アクション (各兄弟役を順次 `claude -p` で起動):
  1. self/memory に案件総括を追記
  2. 再利用価値ありと判定する WF を最大 1 本、蒸留昇格提案として `workflows/distilled/_pending/` に置く
  3. ユウコが昇格提案を統合バリデーション → サザン承認 → `workflows/distilled/` 反映
- 出力: 個人記憶更新 + (場合により) 蒸留 WF 1 本昇格

## エラーハンドリング

- 兄弟レビューで 1 名以上が大幅修正案を出した場合 → ユウコは統合セッション中に再度該当兄弟と consult_peer (subagent 経由でも可) → 修正版 initial_plan を再レビューに回す (最大 2 ラウンド)
- サザン儀礼承認の HOOK でプラン MD が frontmatter 不備で deny された場合 → ユウコは統合セッションに戻り frontmatter を修正
- 統合検収で 2 ラウンド差し戻ししても整合性が取れない場合 → ユウコがクライアントに状況説明し納期見直しを提案

## 「穴」の取り扱い

求人クリエイティブの専門領域には現在のスキルセットでカバーしきれない領域がある。本 WF では以下を **注釈付きで通過** させる:

- **印刷入稿仕様 (CMYK / トンボ / 解像度)**: 印刷会社のオペレーターレビューを前提と申し送りに明記
- **求人法令 (職業安定法・男女雇用機会均等法・健康保険適用範囲)**: 軽い禁則チェックのみ。専門家レビューを推奨と申し送りに明記
- **動画素材・SNS 運用**: 範囲外。希望があれば別案件で

## 案件アレンジ時の改変ガイド

このマスター WF を案件にコピーする時 (workflows/cases/{案件ID}/ への配置時) は、frontmatter の `case-id` を埋めて、ノード 1 の 14 項目のうち **本案件で特に重みのある項目を太字に** してアレンジする。ノードの追加や削除は許容するが、ノード 4 (サザン儀礼承認) とノード 8 (整理 HOOK) は外さない。

## 互換性ノート (Workflow Studio)

本 WF の frontmatter は CC Workflow Studio エクスポート形式に互換性を持たせている。`name / description / agents / workflows-referenced / skills-referenced` は Studio フィールドに対応。Phase 6 以降 Studio 採用時に movein コストゼロを意図。
