# IT十字陵 (Phase 1 MVP)

5体のAIエージェント（社長 / 営業主任ユウコ / デザイナー / エンジニア / ライター）が
分業して案件を受注・納品する、個人向けの仮想下請け事務所システム。

詳細仕様は [`PLAN.md`](./PLAN.md) を参照してください。

## 認証について

本システムは **Claude Code の OAuth ログイン (Pro/Max サブスク)** を利用します。
事前に以下を済ませておいてください:

```bash
claude login
```

`ANTHROPIC_API_KEY` は **設定不要**（API キー認証を使う場合のみ設定してください）。

## セットアップ

```bash
cd /path/to/ITjujiryou
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# DB 初期化
python -m src.main init
```

## 使い方

```bash
python -m src.main cli
```

対話プロンプトに発注内容を入力 → 空行送信で確定。
事務所内のタイムラインがリアルタイムでターミナルに流れ、最後にユウコからの
クライアント向け応答が表示されます。

`exit` で終了。

## テスト

```bash
pytest
```

主要テスト:
- `test_president_no_tools.py` — 社長が実務ツール（Bash/Edit/Write/WebSearch）を持たないこと
- `test_persona_leak.py` — クライアント向け応答に内部用語が混入しないこと
- `test_dispatch.py` — ユウコの dispatch_task 経路が機能すること
- `test_store.py` — 永続化層の sanity

## ディレクトリ

```
prompts/   各エージェントの system prompt
src/
  agents/  ペルソナ別の options ビルダ
  tools/   カスタム MCP ツール (send_message / dispatch_task / ...)
  memory/  SQLite 永続化
  events/  タイムラインロガー
  reception.py    クライアント窓口（ペルソナ漏れ最終チェックを含む）
  orchestrator.py ユウコ起動の薄いラッパ
  main.py         CLI
data/      ランタイム (gitignore: office.db / memory/ / logs/)
outputs/   納品物 (gitignore)
```

## 動作確認シナリオ (PLAN.md §9.4)

CLI から順に試して動作を確認できます:

1. note記事執筆 (ライター単独)
2. CSV抽出 Python スクリプト (エンジニア単独)
3. ブログ LP モック (デザイナー + ライター + エンジニア複合)
4. 値引き要求 (社長の「ひかぬ」精神テスト)

## Phase 2 / 3

将来 Web ダッシュボード（FastAPI + WebSocket）とピクセルアート UI を追加予定。
本リポジトリは Phase 1 完了時点のスコープ。
