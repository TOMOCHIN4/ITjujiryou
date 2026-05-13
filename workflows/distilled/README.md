# workflows/distilled/ — 蒸留昇格 ディレクトリ

案件後の整理 HOOK でユウコが承認した「再利用価値あり」WF の置き場所。再利用可能な普遍化版。

## 蒸留昇格の流れ (Phase 4 以降本格稼働)

1. **案件完了 (deliver) 後**: 各兄弟が「この案件で得た再利用価値あり」と判定した最大 1 本を蒸留昇格提案として `workflows/distilled/_pending/{タイムスタンプ}-{役職}-{案件ID}.md` に置く (Phase 4)
2. **ユウコ統合**: フォーマット検証 + 既存 `distilled/` 内の重複・矛盾チェック
3. **サザン儀礼承認**: ユウコがクリーン提案をキューに置く → サザン承認発話 → HOOK が `_pending/` から `distilled/` 本体へ移動 (Phase 4 で `hook_p6_company_memory_write` 整備)

Phase 2 では **手動運用** (上記フローはルールとして記述、自動化は Phase 4)。

## 昇格規律 (仕様書 §4.5.1)

- **1 案件 1 兄弟あたり 最大 1 本** の昇格提案
- **同原本派生 3 本上限**: 例えば `originals/landing-page-build.md` 由来の昇格は `distilled/` 内に最大 3 本まで
- **4 本目作成時**: 既存 3 本のうち最古/最低使用頻度の 1 本を **退役 (`distilled/_retired/` へ移動)**

## ファイル命名規約

```
distilled/
├── {普遍名}.md               # 例: aggressive-cta-lp-build.md
├── _pending/                 # 昇格待ち (ユウコ統合前)
│   └── {YYYY-MM-DDTHHMMSS}-{role}-{案件ID}.md
└── _retired/                 # 退役した過去蒸留
    └── {普遍名}.md
```

## 普遍名の付け方

- 案件名や客先名を含めない (例: `kataoka-recruit-lp.md` は NG)
- 「何の問題に効くか」「どのスタイルか」を表す (例: `aggressive-cta-lp-build.md`, `print-collateral-with-qr.md`)
- 重複防止のためユウコ統合セッションで既存 `distilled/` を grep してから決める

## アンチパターン

- 1 案件で複数兄弟から複数本同時昇格 (規律違反)
- 同原本派生 4 本目を作って退役処理をしない (3 本上限違反)
- `_pending/` を経由せず直接 `distilled/` に書き込む (ユウコ統合スキップ)
- 客先名・案件 ID を含む普遍名 (普遍化の意味がない)
