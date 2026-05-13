# 愛帝十字陵 (マルチプロセス Claude Code 構成・v3.1)

5 体の AI エージェントが分業して案件を受注・納品する、個人向けの仮想下請け事務所システム。

| コードID | 表示名 | 役職 | 前世 |
|---|---|---|---|
| souther | **サザン** | CEO・愛帝 | 聖帝サウザー |
| yuko | **ユウコ** | 秘書・COO | (純然たる現代人) |
| writer | **ハオウ** | ライター・コピー部長 | 拳王ラオウ |
| designer | **トシ** | デザイナー | トキ |
| engineer | **センシロウ** | リードエンジニア | ケンシロウ |

社訓: **「わが社にあるのはただ制圧前進のみ！！」** (社内のみ、クライアントには出さない)

> リポジトリ名 `ITjujiryou` および `workspaces/{souther,yuko,designer,engineer,writer}/` の各ディレクトリ名はコード識別子としてそのまま据え置き。社名・人物像のテキスト表現のみ刷新済み。

詳細仕様は [`SPEC.md`](./SPEC.md) を参照。未着手 TODO のみ [`PLAN.md`](./PLAN.md) に書く。

## 構成の前提

- Anthropic が 2026-04-04 から「Agent SDK + Pro/Max OAuth」を禁止 ([code.claude.com/docs/en/legal-and-compliance](https://code.claude.com/docs/en/legal-and-compliance))
- 本プロジェクトは **API 従量課金を使わない** 方針
- そのため Claude Code を **5 プロセス並列起動** し、各々が Max OAuth で動く構成にしている (Anthropic の利用範囲 "ordinary use of Claude Code" に収まる)

## 認証

```bash
claude login
```

Anthropic アカウント (Max プラン) で OAuth ログイン済みであれば OK。`ANTHROPIC_API_KEY` は **使用しません**。

## 必須ツール

- **tmux 3.4 以上** (`brew install tmux` または `apt install tmux`)
- **Claude Code CLI** (`npm install -g @anthropic-ai/claude-code`)
- Python 3.11 以上

## セットアップ

```bash
cd /path/to/ITjujiryou
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m src.main init        # SQLite (WAL モード) 初期化
```

## 起動

```bash
./scripts/start_office.sh
```

これで以下が一括で起動します:

- tmux session `itj` 内に **6 pane** (souther / yuko / designer / engineer / writer / monitor) で各 `claude` プロセス
- watcher window (`scripts/inbox_watcher.py`): SQLite 新着メッセージを polling して該当 pane に tmux send-keys で投入
- api window: FastAPI ダッシュボード ([http://localhost:8000](http://localhost:8000))

各 pane は `workspaces/{role}/` を cwd とし、そこの `.claude/settings.json` で permissions / hooks が物理的に強制される。

```bash
# 直接見たいとき
tmux attach -t itj

# 終了
./scripts/stop_office.sh
```

## 発注

Web ダッシュボードのフォームから、または curl で:

```bash
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"text": "200字程度の挨拶文を1本書いてほしい"}'
```

CLI (`python -m src.main cli`) でも投入できる。いずれも `data/office.db` の messages に投入するだけで、実際の処理は tmux pane の Claude Code が担う。応答は WS 経由でダッシュボードに反映される。

## レート枠保護 (テスト時)

5 人並列で Opus 4.7 を回すと Max 枠の消費が早い。接続検証や開発時は Sonnet / Haiku に切り替えて節約する。

```bash
./scripts/use_haiku.sh                       # 全員 Haiku 4.5 へ
./scripts/use_haiku.sh claude-sonnet-4-6     # 全員 Sonnet 4.6 へ (引数で別モデル指定可)
./scripts/use_opus.sh                        # 本番 Opus 4.7 へ戻す
```

各 workspace に `.claude/settings.local.json` を作って `model` だけを上書きする仕組み。`settings.local.json` は `.gitignore` 済みなので残骸が commit に紛れない。

なお実測の感触として、**Sonnet 4.6 は CLAUDE.md の指示 (consult_souther を使うなど) を守る** が、**Haiku 4.5 は守らないことがある**。連携の正しさを確認するには Sonnet 以上が無難。

## ペルソナ・権限ガード

物理ガードは「`.claude/settings.json` の permissions.deny + hooks」の二重構造。

| 防御層 | 手段 |
|---|---|
| サザンが Bash/Edit/Write を持たない (愛帝化防止) | `permissions.deny` に列挙 |
| サザンが dispatch_task / deliver / consult_souther を持たない | 同上 |
| サザンがクライアントへ直接送らない | `hooks.PreToolUse(send_message)` の `check_souther_recipient.py` で `to=client` を deny |
| ユウコの納品物にペルソナ漏れ | `hooks.PreToolUse(deliver, send_message)` の `check_persona_leak.py` で FORBIDDEN_TERMS を deny。前世名 (サウザー/ラオウ/トキ/ケンシロウ)・社内符丁 (死兆星/天に帰る/お前はもう…済んでいる/激流を制するのは静水) も含む |
| サザン prompt に召喚モード block 注入 | `hooks.UserPromptSubmit` の `inject_souther_mode.py` (確率制御で「亀裂 / 説き諭し / 深い独白 / 強がり」+ 名台詞 21 選から 3 選) |

## テスト

```bash
.venv/bin/pytest -v
```

- `tests/test_president_no_tools.py` — 社長 settings.json の deny / 必須 allow / hook 登録を JSON 検証
- `tests/test_persona_leak.py` — ペルソナ漏れ hook を実プロセス起動して deny / allow 動作確認
- `tests/test_store.py` — 永続化層の sanity

## ディレクトリ構成

```
workspaces/                 # 5 人の Claude Code ワークスペース (新)
  {souther,yuko,designer,engineer,writer}/
    CLAUDE.md               # 役職別ペルソナ + マルチプロセス補足
    .claude/settings.json   # permissions / hooks / model
    .mcp.json               # itjujiryou MCP server 参照
scripts/
  start_office.sh           # tmux 6 pane 起動
  stop_office.sh            # kill-session
  use_haiku.sh / use_opus.sh
  inbox_watcher.py          # SQLite poll → tmux send-keys
  hooks/
    inject_souther_mode.py  # UserPromptSubmit (サザン専用)
    check_persona_leak.py   # PreToolUse (ユウコの deliver/send_message)
    check_souther_recipient.py  # PreToolUse (サザンの send_message)
src/
  mcp_server.py             # stdio MCP server (9 ツール)
  memory/                   # SQLite 永続化 (WAL モード)
  events/                   # タイムラインログ
  ui/                       # FastAPI ダッシュボード
  persona.py                # FORBIDDEN_TERMS の共通モジュール
  main.py                   # init / cli / serve
prompts/                    # workspaces/*/CLAUDE.md の元ネタ (履歴保持用)
data/                       # gitignore: office.db / logs / memory
outputs/                    # gitignore: 納品物
```

## 動作確認シナリオ

SPEC.md §8 にも記載：

1. note 記事執筆 (ハオウ単独)
2. CSV 抽出 Python スクリプト (センシロウ単独)
3. ブログ LP モック (トシ + ハオウ + センシロウ複合)
4. 値引き要求 (サザンの「ひかぬ」精神テスト)

Phase A (2 pane: souther + yuko) で値引き要求案件、Phase B (5 pane / Sonnet 4.6) で挨拶文案件をスモーク済み。両方ともペルソナ漏れゼロで全往復成功 (v3.0 時点)。v3.1 世界観刷新後は再スモーク予定。

## トラブルシュート

| 症状 | 切り分け |
|---|---|
| pane で `command not found: claude` | `which claude` を Bash で確認、必要に応じて npm install -g |
| pane が claude UI 出現後すぐ消える | `claude --dangerously-skip-permissions` 確認画面で「No, exit」を選んだ可能性。`scripts/start_office.sh` は `bash -lc "...; exec bash -i"` でラップ済み |
| watcher が pane に投入したのに claude が反応しない | `tmux send-keys ... Enter` が 1 回だと multi-line input で改行扱い。`scripts/inbox_watcher.py` は Enter 2 回送るよう修正済み |
| consult_souther 60s タイムアウト | 社長 pane を `tmux capture-pane` で確認。UserPromptSubmit hook 出力エラーの可能性あり |
| 納品物が outputs/ に出ない | 部下が Write tool を使わずメール本文に直接書いた可能性。CLAUDE.md の対応指示を強調する |
