# data/memory/writer/ — ハオウ個人記憶

ハオウ (writer) のみ書き込み可。他人は不可 (ユウコのみ閲覧可)。

## 想定ファイル

```
writer/
├── style_notes/                # 過去案件で学んだコピー作法
├── past_articles/              # 過去執筆記事のスナップショット (既存)
├── review_received/            # ユウコから revise 受領時のメモ (D3、Phase 2 で物理整備)
│   └── <case-id>.md
├── _scratch/                   # 案件中の一時メモ
└── _proposals/                 # 案件終了時の整理 HOOK が生成 (Phase 4)
    └── <case-id>.md
```

## 案件中のルール

- ただ積み上げる (整理しない)
- ユウコから revise (修正指示) を受領した **直後** に `review_received/<case-id>.md` に「何を直したか」「次回への学び」を記録する (D3、Phase 1 で CLAUDE.md に記述ルール / Phase 2 で物理ディレクトリ整備)
- 実体の書込機構は **Phase 3b 以降に導入**。Phase 2 時点ではディレクトリ整備とルール記述のみ
- Phase 3b 以降、レビューセッションと実行セッションが分離されたら `review_received/` を実行セッション側が読んで動く

## 案件後

`scripts/post_deliver_hook.py` (Phase 4) が:
1. `_scratch/<case-id>.md` から再利用価値ある知見を抽出 → `style_notes/` 等へ昇格
2. company への提案を `_proposals/<case-id>.md` に生成
