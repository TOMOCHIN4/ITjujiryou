## ワークフロー庫 — 案件タイプ別マッピング

`workflows/originals/` 配下にある原本 WF を、案件タイプから引くためのインデックスです。

### 案件タイプ別マッピング

| 案件タイプ | 該当 WF (原本パス) | 主担当 | Step 0 ヒアリング標準項目数 |
|---|---|---|---:|
| 求人クリエイティブ複合 (LP + パンフ + ポスター 等) | `workflows/originals/recruit-campaign-master.md` | yuko + haou + toshi + senshirou | 14 項目 |
| 採用 LP 単発 | `workflows/originals/landing-page-build.md` | yuko + haou + toshi + senshirou | 10 項目 |
| 印刷物制作 (パンフ / ポスター / フライヤー) | `workflows/originals/print-collateral-build.md` | yuko + haou + toshi | 8 項目 |
| 求人コピーライティング単発 | `workflows/originals/recruit-copywriting.md` | yuko + haou | 6 項目 |
| 複数納品物の横串チェック (案件後半で起動) | `workflows/originals/brand-consistency-check.md` | yuko + haou + toshi | - (Step 0 不要、検収段階で起動) |

### 案件タイプ判定の早見表

| 顧客発注書のキーワード | 想定 WF |
|---|---|
| 「LP + パンフ + ポスター」「採用クリエイティブ一式」「求人キャンペーン」 | recruit-campaign-master |
| 「採用 LP」「リクルート LP」「LP 単体」 | landing-page-build |
| 「パンフレット」「ポスター」「印刷物」「合説で配る」 | print-collateral-build |
| 「キャッチコピー」「求人コピー」「広告文」 | recruit-copywriting |
| 「複数納品物のトーン統一」「ブランド整合性」 | brand-consistency-check |

### 求人案件の標準ヒアリング 14 項目 (Step 0 で必ず通す)

複合求人案件 (recruit-campaign-master) で利用する標準項目リスト。`benchmarks/cases/kataoka-dental/client_persona.md` §8.3 が出典。

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
11. ブランドカラー・トーン&マナー
12. 予算感 (1 案件あたり / 広告予算は別か含むか)
13. 納期 (本格採用活動開始からの逆算)
14. 配布・掲出経路 (大学掲示板 / 合説 / SNS / 求人サイト / DM)

### WF の利用ルール (D11 / D4 整合)

- **原本は改変禁止**: `workflows/originals/` の MD は読み取り専用。案件アレンジは `workflows/cases/{案件ID}/` にコピーして触る (Phase 2 D4)
- **案件 ID 命名**: `YYYY-MM-DD-client-slug` 形式 (例: `2026-05-13-kataoka-dental`)。仕様書 §10 で正式確定までは暫定形を採用
- **Step 0 でこのファイルを Read してから WF 本体を選ぶこと**
- **Step A でファイナルプランを書くときは `workflows/cases/{案件ID}/final_plan.md` に YAML frontmatter + 本文 MD で書く** (D10 ハイブリッド形式、詳細は `_modules/workflow.md` Step A)
- 各 README (`workflows/README.md` / `workflows/cases/README.md` / `workflows/distilled/README.md`) を Phase 2 完了時点で確認可

### cases/{案件ID}/ の運用フロー (Phase 2 から有効)

1. 受注決定後、ユウコが `workflows/cases/{案件ID}/` ディレクトリを作る
2. このマッピング表で該当 WF (originals/ 配下) を選定し、必要なら `cases/{案件ID}/` にコピーして案件用にアレンジ (色味・文字数制約・締切などを書き換え)
3. ファイナルプランは `cases/{案件ID}/final_plan.md` (D10 形式必須)
4. 納品完了後は案件ディレクトリ全体を読み取り専用扱い (再編集禁止)
5. 90 日無更新で `cases/_archive/{案件ID}/` へ移動 (Phase 5 で自動化)

### distilled/ の運用 (Phase 4 以降本格稼働)

- 案件後、各兄弟が再利用価値ありと判定した最大 1 本を `distilled/_pending/` に置く
- ユウコが統合検証 → サザン儀礼承認 → HOOK が `distilled/` 本体へ反映
- 詳細は `workflows/distilled/README.md`
- **Phase 2 では distilled/ は手動運用 (HOOK は Phase 4)**

### 案件タイプ未列挙のときの判断

このマッピング表に無い案件タイプ (例: ブランディング案件、製品 LP、技術ブログ運用代行) の場合は、最も近い WF をベースに案件アレンジ。判断に迷ったら `record_thought` で「迷い」を 1 文残してから判定。
