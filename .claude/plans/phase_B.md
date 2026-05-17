# Phase B プラン

> **作成日**: 2026-05-17
> **シンプルゴール (フロー全体)**: prompts/ 配下の全ファイルの索引 + 1 行要約を docs/prompts_overview.md として整備し commit 済みにする
> **全 Phase 数 N**: 3
> **当 Phase の位置**: B / 3

## 1. 背景

Phase A で `prompts/` 配下 7 ファイルの要約草案 (ファイル名 / 役割 / 1 行要約 / 用途タグ) とタグ体系 4 種、並び順方針について合意を取得済み。Phase B では合意済草案を実ファイル `docs/prompts_overview.md` として書き出す。

Phase A の `/eval-phase` で挙がった論点を本 Phase で吸収する:

- 構造: テーブル形式 + 冒頭にタグ凡例 + 並び順の根拠 (1-2 段落)
- 複数タグの表記: スラッシュ区切り (`system-prompt / internal-only`) に統一
- 冒頭注記: 「本ドキュメントは社内向け開発資料」を明記

なお `docs/` ディレクトリは既に存在 (`development_layer_rules.md` 等が配置済) のため新規作成は不要。

## 2. 当 Phase の完了判定

- [ ] `docs/prompts_overview.md` が新規作成されている
- [ ] 冒頭に「社内向け開発資料」である旨の注記がある
- [ ] タグ凡例 (4 種: `system-prompt` / `quote-library` / `cross-character` / `internal-only`) と並び順の根拠が 1-2 段落で書かれている
- [ ] 7 ファイル全てが 1 行テーブルに含まれており、Phase A 草案のテーブル列 (ファイル名 / 役割 / 1 行要約 / 用途タグ) と一致している
- [ ] 複数タグはスラッシュ区切り (例: `system-prompt / internal-only`) で統一されている
- [ ] Markdown のテーブル記法が崩れていない (列数一致 / セパレータ行有り)

## 3. 成果物

- `docs/prompts_overview.md` (新規ファイル、Phase A 合意内容を反映した索引ドキュメント)

commit は Phase C で行うため、本 Phase は Write までで止める。

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| Phase A 合意草案からの表記ブレ | 草案テーブル本文を機械的に転記、自由記述箇所は冒頭の凡例段落のみに限定 |
| `docs/` 既存ファイルとのスタイル乖離 | 他 `docs/*.md` (例: `development_layer_rules.md`) と同じ Markdown スタイル (H1/H2 + テーブル) に合わせる |
| 将来 `prompts/` にファイル追加した時の更新責務が不明 | 末尾に「prompts/ にファイルを追加した際は本ファイルを更新する」旨の 1 行運用注記を添える |
| `internal-only` タグの存在が docs/ 配下で誤解されないか | 冒頭注記で「社内向け資料につき `internal-only` の素材も列挙する」と先回り明記 |

---

**再掲: 本ファイルは Phase B の単一プラン。承認後に着手し、完了したら `/eval-phase` で評価する。**
