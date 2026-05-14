# company 会社記憶 — INDEX

愛帝十字陵 全社員共通の会社記憶インデックス。

## 配下カテゴリ

- `client_profile/` — クライアント別の方針・契約上の制約・過去判断
- `quality_bar/` — 会社としての品質基準・納品ルール
- `workflow_rule/` — 業務フロー上の決まりごと
- `recurring_pattern/` — 繰り返し現れる案件タイプの定型
- `_proposals/{case_id}.md` — ユウコ統合済みの提案 (サザン儀礼承認待ち)
- `_proposals/_archived/` — サザン承認済 → 物理反映済の提案アーカイブ
- `_last_write.log` — 確定書込ログ (JSONL)

## アクセス

- 書き: `scripts/inbox_watcher.py` が `memory_approval` message を検知して特殊処理 (詳細は SPEC.md §11.3)
- 読み: 全社員 (サザン / ユウコ / 三兄弟)
