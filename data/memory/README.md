# data/memory/ — 愛帝十字陵 記憶基盤

仕様の本体は `SPEC.md §10`。本ファイルは物理配置と運用ルールの要約。

## ディレクトリ構成

```
data/memory/
├── company/              # 会社記憶 (全員読み、watcher の memory_approval ハンドラのみ書き)
├── souther/              # サザン個人記憶
├── yuko/                 # ユウコ個人記憶
├── writer/               # ハオウ個人記憶
├── designer/             # トシ個人記憶
└── engineer/             # センシロウ個人記憶
```

実装パスはコード識別子 (`souther/yuko/writer/designer/engineer`) を据え置き。
表示名 (サザン / ユウコ / ハオウ / トシ / センシロウ) との対応は SPEC.md §3.2 参照。

各 role 配下は次の構造:

- `{topic}/<slug>.md` — 整理済の個人記憶 (frontmatter 必須、schema: personal-memory/v1)
- `_scratch/{case_id}/<step>.md` — 案件中の作業メモ (frontmatter schema: scratch/v1)
- `_proposals/{case_id}.md` — 会社記憶昇格候補 (frontmatter schema: proposal/v1)

## アクセス権マトリクス

| キャラ | 会社記憶 | 自身の個人記憶 | 他人の個人記憶 |
|---|---|---|---|
| ユウコ | 読み | 読み書き | **全閲覧可** |
| サザン | 読み (会社記憶の物理書込は watcher が担う) | 読み書き | 不可 |
| 三兄弟 (writer / designer / engineer) | 読み | 読み書き | 不可 |

### 物理ガード

各 workspace の `.claude/settings.json` に `Read(${CLAUDE_PROJECT_DIR}/../../data/memory/{他人}/**)` を deny で設定 (`tests/test_memory_access_guards.py` で静的検証)。

## 案件中の積み重ね方

- 案件中: 各人がただ追記する (4 つの節目: 着手 / subtask 完了 / レビュー受領 / 完了報告直前)
- 案件終了時: `deliver` 完了直後に `inbox_watcher.py` が各 role pane に整理プロンプトを投入

## 会社記憶への書き込みフロー

```
兄弟整理 (各 role pane で _proposals/{case_id}.md 生成)
  ↓ send_message(to="yuko", message_type="memory_proposal")
ユウコ統合 (company/_proposals/{case_id}.md に Write)
  ↓ consult_souther(message_type="memory_approval_request")
サザン儀礼承認
  ↓ send_message(to="yuko", message_type="memory_approval", refs={"proposal_path": ...})
scripts/inbox_watcher.py が memory_approval を特殊処理
  ↓ company/{category}/{slug}.md に物理反映
  ↓ company/_last_write.log に JSONL 追記
  ↓ company/_proposals/_archived/{case_id}.md に移動
  ↓ ユウコへ memory_finalized 通知
```

サザン本人はファイルを直接 Write しない (権限なし)。会社記憶の物理反映は watcher が担う。

## 検索

直接 Read より `Task(subagent_type="memory-search")` を推奨。
per-role subagent (`workspaces/{role}/.claude/agents/memory-search.md`) が distilled summary を返す。
生 Read は親 context に届かない (Task tool 境界で担保)。

## メモリ vs Claude Code 組み込み auto-memory

Claude Code 組み込みの `~/.claude/projects/<encoded-path>/memory/` は **人間 (ユーザー本人) の私的領域** として継続。
本会社エージェント網 (`data/memory/`) とは別レイヤー。混同しないこと。

## frontmatter スキーマ

詳細は SPEC.md §10。4 種類:

- `personal-memory/v1` — 個人記憶 (`{role}/{topic}/<slug>.md`)
- `company-memory/v1` — 会社記憶 (`company/{category}/<slug>.md`)
- `scratch/v1` — スクラッチ (`{role}/_scratch/{case_id}/<step>.md`)
- `proposal/v1` — 提案 (`{role}/_proposals/{case_id}.md`)
