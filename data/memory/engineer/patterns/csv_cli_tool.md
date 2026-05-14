---
schema: personal-memory/v1
role: engineer
topic: patterns
case_ids: [cb3bde67-4ef2-4a7d-8258-2e21a8c83c0b]
case_type: "csv-cli-tool"
keywords: [CSV, argparse, 依存ゼロ, utf-8-sig, BOM, パイプ連結, 終了コード]
created_at: 2026-05-03
updated_at: 2026-05-03
status: distilled
---

# パターン: CSV系CLIツール (Python標準ライブラリ)

## 適用場面
CSVに対する抽出・加工・変換などをargparseベースのCLIで作るとき。

## 設計指針
- `csv` + `argparse` のみで完結させる（依存ゼロを優先）。
- 入力は `encoding="utf-8-sig"` でBOM付きCSVも取り込めるように。
- 出力は `encoding="utf-8"`、`newline=""` を必ず指定（csvモジュール仕様）。
- `--output` 省略時は `sys.stdout` を使い、パイプ連結を可能にする。
- 列名解決は「無い列を全部集めてから一度に通知」する方が親切（ユーザが何度も再実行せずに済む）。
- 行が短い場合は IndexError を握り、欠損は空文字で埋める。
- 終了コードを用途別に分ける: 0正常 / 1論理エラー / 2 FileNotFound / 3 OSError。
- Python互換性のため `from __future__ import annotations` を入れておく（3.7+で `str | None` 等が書ける）。

## 落とし穴
- 納品先の Python が 3.10 未満のことがあるので、PEP604 union を裸で使わない。
- `csv.reader` で `next()` を直に呼ぶ場合は空ファイルの StopIteration を必ずハンドリング。

## 関連成果物
- outputs/cb3bde67-4ef2-4a7d-8258-2e21a8c83c0b/extract_columns.py
