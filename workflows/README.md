# workflows/ — ワークフロー倉庫 (3 階層)

愛帝十字陵 v2 のワークフロー保管庫。設計の全体像は `../aitei_juujiryou_v2_confirmed_decisions.md` §7-8 を参照。

## 階層構成

```
workflows/
├── README.md
├── originals/        # 原本層: Studio 出力 or 人間手書き、改変禁止
├── cases/            # 案件アレンジ層: 案件ごとのスナップショット、案件中のみ書き換え
└── distilled/        # 蒸留層: 案件後の昇格版、再利用可
```

### 1. originals (原本層)

- Studio (将来採用) または人間が手書きで作成した **原本** を配置
- **改変禁止**。バージョンアップは `recruit-campaign-master` → `recruit-campaign-master-v2` として共存
- 物理的に readonly 推奨 (`chmod -w workflows/originals/*.md`)
- Phase 0 Track B で 5 本配置予定:
  - `recruit-campaign-master.md` (案件全体マクロ)
  - `landing-page-build.md` (LP の構成→ライティング→デザイン→実装)
  - `print-collateral-build.md` (パンフ/ポスター制作)
  - `recruit-copywriting.md` (求人特化コピーライティング)
  - `brand-consistency-check.md` (複数納品物間のトーン統一)

### 2. cases (案件アレンジ層)

- 案件ごとに `cases/<case-id>/` ディレクトリを作る (case-id 命名規約は §19 で確定)
- 原本をベースに本案件用にアレンジしたものを配置
- **案件中のみ書き換え可**、案件完了後は freeze
- 90 日経過でアーカイブ領域へ移動 (物理削除はしない、Phase 5 で運用化)

### 3. distilled (蒸留層)

- 案件完了時の整理 HOOK で各兄弟が「再利用価値あり」と判定した 1 本のみ昇格提案
- ユウコ統合セッションが承認したもののみ昇格
- **昇格規律 (Phase 5 で実装)**:
  - 1 案件 1 兄弟あたり最大 1 本まで昇格可
  - 同じ原本から派生した蒸留は 3 本まで。4 本目を作る時は 1 本退役
  - 退役は物理削除せず `distilled/_retired/` へ移動
- 昇格台帳: `distilled/_promotion_log.md` で案件 ID / 兄弟 / 原本派生数を追跡

## ファイル形式

- **Claude Code ネイティブ MD + YAML frontmatter** 形式
- CC Workflow Studio (将来採用候補) のエクスポート形式と互換
- 独自スキーマは発明しない
- 具体的な frontmatter フィールドの確定は **次セッションの宿題 (§19)**

## 指示粒度との関係

ユウコから兄弟への指示は **「ワークフロー名 + どこをどう改変するか」** で統一する (§6)。

例:
> `build-feature-v3` をベースに、ステップ4の `integration-test` を本案件の API 仕様に合わせて差し替え。ステップ 7 はスキップ可。

skill 名指定はしない (兄弟がワークフロー実行時に選ぶ)。

## Claude Code 進化への自動追従

スラッシュコマンド / subagent / skill の仕様が拡張されれば、原本層もそのまま恩恵を受ける。Studio が新機能を吐けばそれも自動的に使える状態を維持。
