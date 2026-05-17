# 天翔十字フロー検証用テスト案件 進行ログ (2026-05-17)

## 目的

天翔十字フロー (`/init-plan` → `/eval-phase` → `/next-plan` を 3 Phase 反復) が、初回 / 2 回目以降 / フロー終了後の各局面で想定どおりに動くか、実案件に乗せて検証する。

検証用に選んだ題材は **「`prompts/` 配下の索引 + 1 行要約を `docs/prompts_overview.md` として整備し commit 済みにする」** (= 副産物としてリポジトリにも実利のあるドキュメント整備)。

## 開始前の状態

セッション開始時、`UserPromptSubmit` hook が `.claude/phase_state.json` を読み、Phase 情報をプロンプト処理前の context に自動注入する仕掛けが既に稼働していた。状態は `phase_current="_frozen"` (= フロー凍結中) で、本 hook 注入によりこの事実が会話冒頭から見えていた。

## Phase A: 初回 Phase の立ち上げ

ユーザーが `/init-plan` を起動。skill 規約により、`phase_current="_frozen"` であることを前提に動く skill のため、フロー進行中なら拒否される仕組み。Claude 側で以下を判断:

- シンプルゴール (フロー全体不変) の確定
- 全 Phase 数 N の確定 (3 / 5 / 7 の中から最小の 3)
- 初回 Phase ID = A、当 Phase の完了判定

タスク規模が小さいため N=3 として「A: 調査+草案合意 / B: ファイル書き出し / C: 検証+commit」に切り分ける案を提示し、`.claude/plans/phase_A.md` を Write。続けて `scripts/dev_hooks/init_phase_state.py` を自動実行し、`phase_state.json` を atomic に Phase A 用へ初期化 (`phase_current=A / phase_total=3 / phase_remaining=2`)。

skill 規約に従って「承認いただけたら着手します」で停止。ユーザー「承認」発言で Phase A の実作業 (7 ファイル並列 Read → 要約草案テーブル提示) を開始し、再度「承認」を得て完了判定を満たした。

## Phase A 評価

ユーザーが `/eval-phase` を起動。本 skill は **ファイル書き込みを一切行わない** 規約のため、`phase_state.json` も `.claude/plans/` も触らず、`git log` で commit 範囲 (Phase A は会話成果のみのため commit ゼロ) を確認したうえで、3 件の完了判定をすべて ✅ と評価。実績論点として Phase B でのテーブル構造化方針 / 複数タグ表記方法 / 冒頭注記の必要性を引き継ぎ事項として抽出した。

## Phase B: 2 回目の Phase 着手

ユーザーが `/next-plan` を起動。本 skill は「2 回目以降の Phase 専用」「シンプルゴール / N は phase_state.json から転記、書き換え禁止」の規約で動く。`.claude/plans/phase_B.md` を Write し、`scripts/dev_hooks/advance_phase_state.py` を自動実行 (`phase_current=B / phase_remaining=1`)。helper は不変キー (`phase_simple_goal` / `phase_total`) を渡されたら exit 1 で拒否する物理ガード付きだが、本 skill は規約どおり 3 キー (`phase_current` / `phase_remaining` / `latest_plan_path`) のみ渡したためガード発火なしで成功。

ユーザー「承認」で Phase B 着手。`docs/prompts_overview.md` (38 行) を Write し、`awk` でテーブル列数の整合性を自己検証して完了判定を満たした。本 Phase でも commit は行わず Phase C の責務に分離。

## Phase B 評価

`/eval-phase` 起動。6 件の完了判定をすべて ✅。論点として Phase C で扱う commit 対象ファイル群 (`docs/prompts_overview.md` / `.claude/phase_state.json` / `.claude/plans/phase_{A,B,C}.md`) と除外対象 (`conversation.png`) を抽出し、commit メッセージ書式 (`docs(prompts):` プレフィックス) も合意。

## Phase C: 最終 Phase

`/next-plan` 起動 → `.claude/plans/phase_C.md` Write → `advance_phase_state.py` で `phase_current=C / phase_remaining=0` へ前進。ユーザー「承認」で実作業。

Phase C では (1) `docs/prompts_overview.md` と `prompts/` 実 7 ファイルの最終突合、(2) 個別ファイル指定の `git add` (`conversation.png` 除外確認)、(3) `docs(prompts):` 形式の commit を実施。commit `78a9336` が成立し、`git log -1 --stat` で 5 files / 177 insertions / 5 deletions を確認した。ワーキングツリーは本タスク無関係の `conversation.png` のみ untracked で残存し、完了判定の許容範囲どおり。

## Phase C 評価

`/eval-phase` 起動。5 件の完了判定をすべて ✅、シンプルゴール (索引整備 + commit 済み) 達成を宣言。残 Phase 数 0 のため「次案件は freeze 後に `/init-plan`」と案内して締めた。

## 終了後 `/next-plan` の物理ガード検証

ユーザーが意図的に `/next-plan` を再度起動 (フロー終了後の誤作動防止テスト)。Claude 側で skill 規約「`phase_total=3` を超える Phase D を作るのは N の書き換えと等価」を判断し、`advance_phase_state.py` を呼ぶ前に停止。`scripts/dev_hooks/freeze_phase_state.py --freeze` でフロー凍結 → 改めて `/init-plan` で新フローを立ち上げる順路を提示した。

= フロー終了後に `/next-plan` を呼んでも、skill 側の判断で空回りに留まり、`phase_state.json` を破壊しないことを確認。

### 追記 (2026-05-17): `phase_remaining=0` 物理ガード追加 (commit `53ca16f`)

本検証当時は「skill 規律 (AI 判断) で停止」のみだったため、AI 判断を経由しない直接呼び出しに対しては素通りする余地が残っていた。これを塞ぐため、`scripts/dev_hooks/advance_phase_state.py` に **既存 state の `phase_remaining == 0` なら exit 1** という物理ガードを追加した。

- 位置: `_frozen` ガード直下 (state 読込後、`new_state` 構築前)
- メッセージ: 「`phase_total` を超える Phase の追加と等価のため拒否」「`freeze_phase_state.py --freeze` → `init_phase_state.py` で立ち上げ直せ」
- 検証: 一時 state ファイル (`ITJ_PHASE_STATE_PATH` env) で 4 ケース実機確認
  - `phase_remaining=0` → 新ガード発火 ✅
  - `phase_remaining=2` → 正常遷移 (回帰 OK) ✅
  - `_frozen` → 既存ガード発火 (回帰 OK) ✅
  - 不変キー `phase_total` 渡し → 既存ガード発火 (回帰 OK) ✅

これにより、フロー終了後の `/next-plan` は **skill 規律 + helper 物理ガード** の二重化で停止する。

### 追記 (2026-05-17): eval-phase 自動化 + 最終 Phase 自動 freeze

`/eval-phase` の起動契機を「ユーザー明示呼出」から「Phase 完了判定を満たした直後の自発起動 (+手動互換)」に拡張し、さらに最終 Phase (`phase_remaining=0`) 評価時は出力直後に `freeze_phase_state.py --freeze` を自動実行する仕様に変更。

変更箇所:
- `.claude/skills/eval-phase/SKILL.md`: 「起動契機 (自動 / 手動)」セクション新設、Step 5 を通常 / 最終で 2 系統に分岐、Step 6 (自動 freeze) を追加、「重要」セクションの「ファイル書き込み禁止」を「最終 Phase freeze のみ例外」に緩和
- `docs/development_layer_rules.md` §3.4: freeze の自動 / 手動の区別を明記
- `docs/development_layer_rules.md` §3.5: skill 表に「起動」列を新設し、`/eval-phase` の自動化を反映

検証 (dogfood):
- 既存 pytest: 89 passed (回帰なし)
- N=3 軽い試金石案件 (一時 state ファイルで実機検証) 7 ステップ:
  1. `_frozen → init Phase A → advance B → advance C` で state 遷移が想定通り
  2. 最終 Phase (C, `phase_remaining=0`) 状態で `freeze --freeze` を実行 → `phase_current=_frozen` へ凍結成功
  3. 凍結状態から `advance` を呼ぶと `_frozen` 既存ガードで拒否 (回帰なし)
  4. `unfreeze-to-init → init` で別案件 (`phase_current=1`, シンプルゴール別) を再立ち上げ可能
  5. 別ルート (フロー途中ではなく直接 `phase_remaining=0` state を作って `advance` を呼ぶ) でも新物理ガードで拒否 (回帰なし)

5 項目確認結果:
- **通常 Phase 自発 eval**: SKILL.md 仕様レビュー (起動契機セクション + テンプレ分岐) で確認 ✅
- **最終 Phase 自動 freeze**: 上記 Step 2 で実機通過 ✅
- **state 遷移**: 上記 Step 1 で通常遷移、Step 2 で凍結遷移を確認 ✅
- **再 init 可能**: 上記 Step 4 で確認 ✅
- **既存規約退行なし**: pytest 89 passed + Step 3 / 5 の物理ガード回帰確認 ✅

## 自動発火 / 承認求め / ガードの俯瞰

- **自動発火**:
  - `UserPromptSubmit` hook (各プロンプト前に Phase 情報を context へ自動注入)
  - `init_phase_state.py` / `advance_phase_state.py` (各 skill 内で自動実行、`phase_state.json` を atomic 更新)
  - `/eval-phase` skill (Phase 完了判定を満たした直後に自発起動。手動 `/eval-phase` 呼出も互換で残存)
  - `freeze_phase_state.py --freeze` (最終 Phase 評価直後、`/eval-phase` skill が自動実行)
- **ユーザー起動が必要なもの**:
  - `/init-plan` / `/next-plan` (skill 本体、Phase 着手は常にユーザー判断)
  - 各 Phase 着手前の「承認」発言 (skill が「承認待ち」で停止する設計)
  - `freeze_phase_state.py --freeze` の手動実行 (フロー本体改修などフロー中断時)
- **物理ガード**:
  - `init_phase_state.py` は `_frozen` 以外で起動すると exit 1 (進行中フローを潰さない)
  - `advance_phase_state.py` は不変キー (`phase_simple_goal` / `phase_total`) を渡すと exit 1
  - `advance_phase_state.py` は既存 `phase_remaining == 0` でも exit 1 (commit `53ca16f` で追加。詳細は「追記」セクション参照)
  - `phase_remaining=0` の状態で `/next-plan` を呼んだ際は、skill 規律レベルでも停止 (規律 + 物理の二重化)

## 達成事項

- `docs/prompts_overview.md` (索引ドキュメント) を新設、commit `78a9336` に格納
- `.claude/plans/phase_{A,B,C}.md` 3 ファイルが履歴として残存、フロー再現可能
- 天翔十字フローが「初回 → 2 回目以降 → フロー終了後」の各局面で規約どおり動くことを実機確認
