# data/memory/souther/ — サザン個人記憶

サザン (souther) のみ書き込み可。他人は不可 (ユウコのみ閲覧可)。

## 想定ファイル

```
souther/
├── monologue/                  # 案件中の独白 (pixel UI 心のうち表示と整合)
├── review_received/            # (Phase 2 で整備、サザン用は通常空。全 role 整合性のため作成)
│   └── .gitkeep
└── _scratch/                   # 案件中の一時メモ
```

## 会社記憶への書き込み

サザンが書くのは **個人記憶のみ**。会社記憶 (`../company/`) への書き込みは
**`company_memory_write` HOOK 経由のみ** (サザンの儀礼承認セッション完了がトリガ、Phase 4)。

サザン本人は会社記憶ファイルへの直接 Write を持たない (`.claude/settings.json` で deny)。
これは「サザンに嘘をつかせない設計」(§2.3) の核 — クリーンな提案だけがサザンに届き、HOOK が黙々と反映する。
