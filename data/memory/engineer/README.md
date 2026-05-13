# data/memory/engineer/ — センシロウ個人記憶

センシロウ (engineer) のみ書き込み可。他人は不可 (ユウコのみ閲覧可)。

## 想定ファイル

```
engineer/
├── code_notes/                 # 過去案件で確立した実装パターン
├── infra_notes/                # 環境構築・運用の勘所
├── patterns/                   # 設計パターン (既存)
├── review_received/            # ユウコから revise 受領時のメモ (D3、Phase 2 で物理整備)
│   └── <case-id>.md
├── _scratch/                   # 案件中の一時メモ
└── _proposals/                 # 案件終了時の整理 HOOK が生成 (Phase 4)
    └── <case-id>.md
```

## ルール

- 案件中はただ積み上げる
- ユウコから revise (修正指示) を受領した **直後** に `review_received/<case-id>.md` に「何を直したか」「次回への学び」を記録 (D3、Phase 1 で CLAUDE.md に記述ルール / Phase 2 で物理ディレクトリ整備)
- 実体の書込機構は **Phase 3b 以降に導入**。Phase 2 時点ではディレクトリとルール記述のみ
- 案件後は `post_deliver_hook.py` が `_proposals/` を生成 (Phase 4)
