---
name: landing-page-build
description: 採用 LP の構成設計 → コピー → デザイン → 実装 → アクセシビリティ確認 → デザインレビュー
case-id: null
agents: [yuko, haou, toshi, senshirou]
workflows-referenced:
  - recruit-copywriting
  - brand-consistency-check
skills-referenced:
  - marketingskills/customer-research
  - marketingskills/copywriting
  - marketingskills/marketing-psychology
  - marketingskills/page-cro
  - marketingskills/form-cro
  - skills/frontend-design
  - skills/web-design-guidelines
  - skills/baseline-ui
  - skills/react-best-practices
  - skills/fixing-accessibility
  - skills/fixing-motion-performance
  - skills/design-review
version: 1.0
status: original
---

# landing-page-build

採用 LP 1 本を構成設計から実装まで一気通貫で作る WF。recruit-campaign-master のサブ WF として呼び出される、または LP 単独案件で単発実行される。

## 適用範囲

- 1 ページ完結の縦長 LP (スマホファースト)
- 静的 HTML/CSS または React コンポーネント (依頼に応じて)
- 申込フォーム or 外部応募フォームへの遷移を CTA とする

## 入力

- `initial_plan.md` (ターゲット読者 / 訴求軸 4 本 / トーン&マナー / 予算 / 納期)
- ブランドカラー指定 (なければデザイナー提案)
- 既存 Web サイトの URL (参考)
- 競合 LP 3〜5 本のリスト (`marketingskills/competitor-profiling` から)

## 出力

- LP の HTML/CSS (or React コンポーネント一式)
- LP 構成図 (どのセクションがどの訴求軸を担うか)
- スマホ・PC 両対応の確認スクリーンショット
- 申し送り (前提条件 / 修正フロー / CTA 計測の設定方法 / アクセシビリティ基準)

## マクロフロー

### ノード 1: 構成設計 (ユウコ + 兄弟 3 名のキックオフ)

- アクション:
  1. Skill `marketingskills/customer-research` を実行 → ターゲット (徳島大歯学部口腔保健科 3-4 年生) の生活実態・進路意識・情報収集経路を整理
  2. Skill `marketingskills/marketing-psychology` を実行 → 「徳島から大阪へ転居して衛生士になる」決断の心理障壁を抽出
  3. Skill `marketingskills/page-cro` を実行 → セクション構成のベストプラクティスを取得
  4. ユウコがリードして LP セクション構成案を作成
- LP 標準セクション構成 (求人 LP デフォルト):
  - 1. ヒーロー (KV + メインキャッチ + サブコピー + CTA)
  - 2. クリニックの基本紹介 (院長挨拶 + 患者層 + 設備)
  - 3. 訴求軸 4 本 (リコール 60 分 / 個室 9 台 / 子育て両立 / 院長から学べる)
  - 4. 先輩衛生士の声 or 想定インタビュー (架空でも素材として用意 = 申し送りで明示)
  - 5. 労働条件詳細 (給与 / 休日 / 残業 / 家賃補助 / 引越し手当)
  - 6. 1 日の流れ
  - 7. よくある質問 (徳島から転居する不安への回答中心)
  - 8. CTA (応募 / 見学申込み / LINE 質問)
- 出力: セクション構成案 MD

### ノード 2: コピーライティング (ハオウ主担当、サブ WF `recruit-copywriting`)

- 起動契機: ノード 1 のセクション構成案 OK
- アクション:
  1. サブ WF `recruit-copywriting` を起動
  2. メインキャッチ + サブコピー + 各セクションのリード + CTA 文言を生成
  3. 文字数制約: メインキャッチ 20 字以内 / サブコピー 40 字以内 / セクションリード 80 字以内 / CTA 12 字以内
- 出力: 全コピー文言を `outputs/{task_id}/lp_copy.md` に集約

### ノード 3: デザイン (トシ主担当)

- 起動契機: ノード 2 完了
- アクション:
  1. Skill `skills/web-design-guidelines` でブランドガイドラインを確認 → 既存サイトの茶色基調 + 暖色アクセントを継承
  2. Skill `skills/baseline-ui` で基本コンポーネント (ボタン / カード / フォーム) のトーンを揃える
  3. Skill `skills/frontend-design` で各セクションのレイアウト草案を作成
  4. KV (ヒーロー画像) は **既存写真があれば優先**、なければ Skill `marketingskills/image` で生成
  5. アクセント色: 暖色系 (オレンジ系 #E6A45F あたりが候補、院長確認推奨)
- 出力: デザイン草案 (Markdown のレイアウト指示 + 画像素材 placeholder + CSS スタイル候補)

### ノード 4: 実装 (センシロウ主担当)

- 起動契機: ノード 3 完了
- アクション:
  1. Skill `skills/frontend-design` で実装パターンを取得
  2. 静的 LP の場合: HTML/CSS で実装。ファイル構成は `outputs/{task_id}/lp/index.html` + `style.css`
  3. React 必須の場合: Skill `skills/react-best-practices` + `skills/composition-patterns` を遵守
  4. Skill `skills/fixing-motion-performance` で初期表示パフォーマンスを最適化 (画像最適化 / lazy load / above-the-fold CSS)
  5. CTA フォームは Skill `marketingskills/form-cro` のベストプラクティスに沿って実装 (必須項目最小化、入力時バリデーション、サンキューページ)
- 出力: HTML/CSS or React コンポーネント一式

### ノード 5: アクセシビリティ確認 (センシロウ + トシ)

- 起動契機: ノード 4 完了
- アクション:
  1. Skill `skills/fixing-accessibility` を実行
  2. WCAG 2.2 AA レベルをチェック (コントラスト / alt / ランドマーク / フォーカス / キーボード操作)
  3. 修正必要箇所は実装に戻して直す
- 出力: アクセシビリティチェック結果 MD (passed / failed 内訳)

### ノード 6: デザインレビュー (トシ + ユウコ)

- 起動契機: ノード 5 完了
- アクション:
  1. Skill `skills/design-review` を実行
  2. デスクトップ + モバイル両方のスクリーンショットを生成
  3. 訴求軸 4 本が視覚的に通っているかを review
  4. クライアントの「茶色基調 + 暖かい」要望に合っているかを review
- 出力: スクリーンショット 2 枚 + レビューコメント MD

### ノード 7: ハオウ最終校正 (コピー)

- 起動契機: ノード 6 完了
- アクション:
  1. 実装で文字数が崩れていないかチェック
  2. 全コピーの最終校正 (誤字脱字 / 求人法令禁則 / 転居前提との整合性)
- 出力: 校正済み LP

### ノード 8: ユウコ統合バリデーション

- 起動契機: ノード 7 完了
- アクション:
  1. 14 項目チェックリストで LP がカバーした項目を集計
  2. ペルソナ漏れチェック (`scripts/hooks/check_persona_leak.py` 想定)
  3. 求人法令上の禁止表現チェック
- 出力: バリデーション結果 + LP 完成版

## 申し送り書 (本 WF が常に生成する)

- LP セクション構成と各セクションの意図
- 訴求軸 4 本の各セクションへの割り付け
- 文字数制約と遵守状況
- ブランドカラー (使用コード一覧)
- アクセシビリティチェック結果
- CTA 計測の設定方法 (Google Analytics or LINE 公式アカウント連携 推奨)
- スマホ / PC 確認スクリーンショット
- 修正フロー (テキスト微修正は折返し 1 営業日 / レイアウト変更は 3 営業日)

## 「穴」の取り扱い

- **A/B テスト**: 範囲外。Skill `marketingskills/ab-test-setup` の追加採用は本案件では未実施
- **本格的な分析タグ実装**: Skill `marketingskills/analytics-tracking` は導入手順だけ申し送りに添える
- **動画素材**: 静止画のみ。動画は別案件

## 案件アレンジ時の改変ガイド

- 訴求軸の数や中身は frontmatter の `agents` 直下に `case-emphasis: [...]` を追記して明示
- セクション構成は **増減可** だが、ヒーロー / 訴求軸 / 労働条件 / CTA の 4 セクションは外さない
- 求人案件以外で本 WF を流用する場合は `recruit-copywriting` を別 WF に差し替える
