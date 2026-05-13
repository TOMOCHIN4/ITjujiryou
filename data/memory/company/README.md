# data/memory/company/ — 会社記憶

全員が読める共通記憶。書き込みは **`company_memory_write` HOOK 経由のみ** (Phase 4 で実装)。

## 書き込みルール

- サザン本人は Write を持たない (`.claude/settings.json` で deny)
- ユウコ統合セッションが検証 → サザン儀礼承認 → HOOK が物理反映
- 直接 `vim company/foo.md` する手動運用は緊急時のみ (痕跡を `_emergency_log.md` に残す)

## 想定ファイル

```
company/
├── INDEX.md                    # Phase 4 で生成、メモリの目次
├── company_motto.md            # 「わが社にあるのはただ制圧前進のみ！！」とその由来
├── client_history/             # 過去案件の総括 (案件 ID 単位)
│   └── <case-id>.md
├── playbook/                   # 繰り返し型業務の進め方
│   └── *.md
└── _emergency_log.md           # 緊急手動書き込みの痕跡
```

Phase 4 で初期化される (現時点は空)。
