# data/memory/yuko/ — ユウコ個人記憶

ユウコ自身のみ書き込み可。他人 (兄弟・サザン) は読めない。
ユウコは会社記憶 (`../company/`) と他人記憶 (`../{souther,writer,designer,engineer}/`) を全閲覧できる特権を持つが、書き込みは自身領域 + Task 経由のみ。

## 想定ファイル

```
yuko/
├── client_profiles/            # クライアントごとの応対メモ
│   └── <client>.md
├── operations/                 # 自身の業務改善メモ
│   └── *.md
├── review_notes/               # Step C (evaluate_deliverable) 直後の自己メモ (D3、Phase 2 で物理整備)
│   └── <case-id>.md
├── _scratch/                   # 案件中の一時メモ (案件終了時に整理)
└── _proposals/                 # company への提案 (Phase 4 で HOOK が生成)
    └── <case-id>.md
```

## D3 ルール: review_notes/ への書込

Step C で `evaluate_deliverable` を呼んだ **直後** に `review_notes/<case-id>.md` に修正パターン / 品質基準の詳細化 / クライアント反応を記録する。フォーマットは `workspaces/yuko/_modules/review_memo.md` を参照。

**Phase 1 / Phase 2 では記述ルールのみ整備済。実体の書込機構 (`memory_write` ツール or 直接 Write 経由) は Phase 3b 以降に導入**。

## 注意

- 兄弟記憶を読む時は **業務判断のためのコンテキスト把握** に限る
- 兄弟の私的記述 (前世記憶への動揺、個人的な葛藤) は読んでも口に出さない
- 案件後の整理は本人が手動で行う (Phase 4 の整理 HOOK の対象外)
