# workflows/ — ワークフロー倉庫 (3 階層)

仕様書 §4.5 / D4 で定義された 3 階層のワークフロー倉庫。Phase 2 で運用開始。

## 階層構造

```
workflows/
├── originals/      # 原本: Studio 出力または人間手書き。改変禁止
├── cases/          # 案件アレンジ: 案件 ID 単位の作業ディレクトリ
│   └── {案件ID}/
│       ├── (originals/ から複製した WF 群)
│       └── final_plan.md  ← D10 ファイナルプラン (YAML frontmatter + 本文)
└── distilled/      # 蒸留昇格: 案件後の昇格版、再利用可
```

## 各階層の役割と規約

### originals/ (改変禁止)

- **何を置くか**: Workflow Studio エクスポート、または人間が手書きした **原本**
- **改変可否**: **改変禁止**。バージョンアップは `v3` → `v4` のように別ファイルとして共存
- **削除条件**: 90 日無参照で削除候補
- **現状の収納物 (Phase 0 配置)**: `recruit-campaign-master.md`, `landing-page-build.md`, `print-collateral-build.md`, `recruit-copywriting.md`, `brand-consistency-check.md`

### cases/{案件ID}/ (案件中のみ書き換え可)

- **何を置くか**: 案件ごとのアレンジ済 WF、`final_plan.md`、その他案件スナップショット
- **改変可否**: **案件中のみ書き換え可**。納品後は読み取り専用
- **アーカイブ**: 90 日無更新で `cases/_archive/{案件ID}/` へ移動 (Phase 5 で `scripts/archive_cases.py` を整備)
- **詳細**: `cases/README.md` 参照

### distilled/ (昇格時のみ書き込み)

- **何を置くか**: 案件後の整理 HOOK でユウコが承認した「再利用価値あり」 WF
- **昇格規律**: 1 案件 1 兄弟あたり **最大 1 本**、同原本派生 **3 本上限**、4 本目作成時は 1 本退役
- **詳細**: `distilled/README.md` 参照

## ユウコ業務サイクルとの接続

ユウコの `_modules/workflow.md` Step 0 (ヒアリング) / Step A (初期計画) で本ディレクトリを参照する。具体的な利用パスは ユウコ `_modules/workflow_reference.md` (案件タイプ別マッピング) に集約済。

## 案件 ID 命名規約

`YYYY-MM-DD-{client-slug}` 形式。slug は半角英小文字とハイフン (例: `2026-05-13-kataoka-dental`)。仕様書 §10 で正式化が未確定だが、Phase 2 以降は暫定形を採用。詳細は `cases/README.md`。

## アンチパターン (やってはいけないこと)

- `originals/` を直接編集 (改変禁止)
- `distilled/` への昇格規律 (1 案件 1 兄弟 1 本、3 本上限) を破る
- 案件 ID 命名規約から逸脱した名前で `cases/` 配下に書く
- `final_plan.md` を `cases/{案件ID}/` の外に書く (D10 形式違反)
