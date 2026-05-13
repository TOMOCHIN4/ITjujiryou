# workflows/cases/ — 案件アレンジ ディレクトリ

各案件のスナップショット (アレンジされた WF + ファイナルプラン + 案件メタ) を置く場所。

## ディレクトリ命名規約

`{YYYY-MM-DD}-{client-slug}` 形式。

- **YYYY-MM-DD**: 案件受注日 (initial_request 受領日)
- **client-slug**: 半角英小文字 + ハイフン。客先名のローマ字 (`kataoka-dental`) または通称
- 例: `2026-05-13-kataoka-dental` / `2026-06-01-acme-recruit` / `2026-07-15-foo-bar-co`

## 各案件ディレクトリの想定構造

```
workflows/cases/2026-05-13-kataoka-dental/
├── final_plan.md       # D10 ファイナルプラン (YAML frontmatter + 本文 MD)
├── recruit-campaign-master.md  # originals/ から複製したアレンジ版 (任意)
├── landing-page-build.md       # 同上
└── notes.md            # 案件内メモ (ユウコ統合セッション用、任意)
```

## final_plan.md のフォーマット (D10)

仕様書 §4.3 準拠の YAML frontmatter + 本文 MD:

```markdown
---
name: aitei-2026-05-13-kataoka-dental-final-plan
description: かたおか歯科クリニック 歯科衛生士採用クリエイティブ一式
case-id: 2026-05-13-kataoka-dental
agents: [yuko, haou, toshi, senshirou]
workflows-referenced:
  - recruit-campaign-master
  - landing-page-build
  - print-collateral-build
  - recruit-copywriting
  - brand-consistency-check
---

# マクロフロー (自然言語)

(本文 — 各ノードを直列/並列で書く)
```

`name` / `description` / `case-id` / `agents` / `workflows-referenced` は **必須**。`propose_plan` MCP ツールが frontmatter チェックを行い、欠落していると deny される (Phase 2 で実装)。

## アーカイブ規律

90 日間無更新の案件ディレクトリは `cases/_archive/{案件ID}/` へ移動。物理削除はしない。アーカイブ自動化は **Phase 5 で `scripts/archive_cases.py` を整備** (今は手動)。

## 書込権

- ユウコの全 3 セッション (受注 / 統合 / 振り分け) が書き込み可
- 三兄弟は読み取りのみ (案件中のみ、自分の担当 WF を参照)
- サザンは触らない (Bash 等 deny)

## アンチパターン

- 案件 ID 命名規約から逸脱 (`kataoka` 単独、`20260513_dental` 等)
- `final_plan.md` を ファイル名違いで保存 (`plan.md` / `master.md` 等)
- ファイナルプラン frontmatter の必須項目欠落
- 納品完了後の案件ディレクトリを再編集 (読み取り専用ルール違反)
