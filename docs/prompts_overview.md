# prompts/ 索引

> **本ドキュメントは社内向け開発資料です**。`internal-only` タグが付いた素材 (北斗世界観・聖帝口調・前世名・社内符丁等) も網羅的に列挙するため、クライアント・外部公開資料への流用は禁止する。

`prompts/` 配下は、株式会社 愛帝十字陵 (本セッションのプロダクト層) に登場する各エージェント・横断素材のプロンプト定義群である。本ファイルはその索引であり、各ファイルの 1 行要約と用途タグを一覧化する。

## タグ凡例

| タグ | 意味 |
|---|---|
| `system-prompt` | エージェント本体の人格・役割・行動規範を定義する system-prompt 本体 |
| `quote-library` | system-prompt に注入される台詞集・参照素材ライブラリ |
| `cross-character` | 特定キャラに紐づかず、全社員横断で参照される共有素材 |
| `internal-only` | クライアント・外部公開資料への露出を厳禁とする社内専用素材 |

複数タグはスラッシュ区切り (例: `system-prompt / internal-only`) で表記する。

## 並び順の根拠

1. **横断素材を先頭**: ファイル名アンダースコア prefix (`_company_motto.md`) を別カテゴリとして冒頭に置く
2. **キャラクター人格定義 (system-prompt)** をユウコ起点の発注順で並べる: 秘書 (ユウコ) → CEO (サザン) → ライター (ハオウ) → デザイナー (トシ) → エンジニア (センシロウ)
3. **キャラ付随リソース (quote-library)** は対応する system-prompt の直後に配置する (例: `souther_quotes.md` は `souther_president.md` の直後)

## 索引

| ファイル | 役割 / 対象 | 1 行要約 | 用途タグ |
|---|---|---|---|
| `_company_motto.md` | 全社員 (横断) | 社訓「わが社にあるのはただ制圧前進のみ」の文言・採用経緯・適用場面の定義 | `cross-character / internal-only` |
| `yuko_secretary.md` | 秘書ユウコ (実質 COO) | 唯一の現代人・対外窓口・三者話法切替・前世引きずりの環境調整役の system-prompt | `system-prompt` |
| `souther_president.md` | CEO サザン (前世: 聖帝サウザー) | 二層構造・YAML voice 制約・era_lock 等を含む CEO の最大規模 system-prompt | `system-prompt / internal-only` |
| `souther_quotes.md` | サザン (付属リソース) | 原作サウザー代表台詞 27 選 + メタデータ (文脈 / 感情核 / 出番 / 変奏ヒント) | `quote-library / internal-only` |
| `writer.md` | ライター・コピー部長ハオウ (前世: ラオウ) | 覇道のコピーライティング哲学・「天に帰る」差戻し作法を持つ writer 人格定義 | `system-prompt` |
| `designer.md` | デザイナー トシ (前世: トキ) | 医療北斗デザイン哲学・慈愛基調・gen-asset 連携手順を持つ designer 人格定義 | `system-prompt` |
| `engineer.md` | リードエンジニア センシロウ (前世: ケンシロウ) | 北斗 SRE 拳哲学・「お前はもう済んでいる」を持つ engineer 人格定義 | `system-prompt` |

## 更新運用

`prompts/` 配下にファイルを追加・削除・改名した際は、本ファイルを同時に更新する。要約は 80 字目安・1 行で、用途タグは上記凡例 4 種から選ぶ (新カテゴリが必要な場合は凡例側を先に拡張)。
