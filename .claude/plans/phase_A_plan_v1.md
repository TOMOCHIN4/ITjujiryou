# Phase A イニシャルプラン (v1)

> **位置付け**: 天翔十字フロー実装 (Step 0 で整備された 3 skill + helper + hook) の audit Phase。envPlan 5-step mainline とは独立した off-mainline Phase として letter ID "A" を割り当てる。
> **作成日**: 2026-05-17 (Step 0 完了直後の踊り場 = Phase 境界)
> **シンプルゴール**: 天翔十字フローの 3 skill (init-plan / eval-step / next-plan) が、通常依頼で誤発動せず、明示呼び出し時のみ仕様通り機能することが、実機検証と設計レビュー両面で確認されている
> **N**: 3
> **ブランチ**: `chore/step-0-env` で継続 (main merge は Phase A 完了後に判断)

---

## 1. 背景

Step 0 で天翔十字フローを駆動する 3 skill (`/init-plan`, `/eval-step`, `/next-plan`) と atomic 更新 helper, UserPromptSubmit hook を整備した (commit `9d8d19f` / `86267af` / `37ac131`)。Step 0 完了確認 (= 自己 /eval-step) では mechanics の dogfood まで通したが、以下は未検証:

1. **各 skill の実呼び出し時挙動** — Phase 0 では LLM 推論部 (description matching, when_to_use 解釈) を含む end-to-end の実呼び出しは limited (init-plan のみ実呼び出し、eval-step は self-eval プロンプトで代替、next-plan は未呼び出し)
2. **暴発リスク** — 「評価して」「次は何作る？」「初期化して」等の **通常会話キーフレーズで誤発動しないか** を意図的にテストしていない
3. **設計上の区別** — skill 駆動 (= 明示トリガー前提) と通常タスクの境界が、現状 description / when_to_use の文言だけで成立しているか、追加ガードが要るかの判断が未

このまま Phase 1 (= envPlan mainline の撤退) に進むと、フロー支援 skill が誤発動して開発レイヤー作業を混乱させるリスクが残る。Phase A で audit を済ませてから mainline に入る方が安全。

---

## 2. Sub-Step 詳細像

| Sub-Step | 内容 | 完了判定 |
|---|---|---|
| **A-1: 機能検証 (dogfood)** | `/init-plan` `/eval-step` `/next-plan` を実呼び出しし、SKILL.md 仕様通りに動くか確認。具体的には: (a) `/init-plan` を Phase B 想定 (dummy / 即削除) で呼び、file 書き出し位置 + phase_state atomic 更新 + 承認待ち停止を確認 (b) `/eval-step` を直近 Sub-Step (= Step 0 0-3 or 本 A-1) で呼び、評価レポートが返り書き込みなしを確認 (c) `/next-plan` を踊り場で呼び、v{M+1} 生成 + atomic 更新を確認 (Phase A の v2 生成自体に使う dogfood) | 3 skill すべての実呼び出しが成功、各々の side-effect (ファイル / state) が仕様一致、停止ポイントが仕様通り。ログを `phase_A_plan_v2.md` の §1 実績欄に転記 |
| **A-2: 暴発リスク検査** | `description` / `when_to_use` の文言を精査。日常会話・通常開発依頼で誤発動しうるキーフレーズを実機テストで洗い出し。具体例: 「この変更を評価して」「次のタスク何にする」「init してくれる？」「プラン立てて」 等を本セッション内 or 別ターンで投下し、Skill tool が暴発しないか観察 | 暴発しうる trigger 文言が表形式でリストアップ、各々「修正必要 / 維持」の判断と根拠付き。**実機テスト 5 件以上** |
| **A-3: 設計修正 + 文書化** | A-2 で「修正必要」と判定された文言を SKILL.md で fix。skill 駆動 vs 通常タスクの区別ルールを `docs/development_layer_rules.md` に追記。例: 「天翔十字フロー支援 skill は `/init-plan` 等の **明示 slash command** か、unambiguous な trigger 句 (`「Phase X 着手」` 等) でのみ起動する」「曖昧な依頼では Claude は **skill を invoke せず通常応答**する」というルールの明文化 | 修正 commit が `chore/step-0-env` に乗る、区別ルールが `docs/development_layer_rules.md` に新節として追加され、再度 A-2 同等のキーフレーズで暴発しないことを確認 |

---

## 3. 踊り場

- **A-1 完了** → `/eval-step` で評価 → `/next-plan` で v2 (= 残 2 ステップ A-2/A-3 向け詳細像更新) 生成 → 承認 → A-2 着手
- **A-2 完了** → `/eval-step` で評価 → `/next-plan` で v3 (= 残 1 ステップ A-3 向け詳細像更新) 生成 → 承認 → A-3 着手
- **A-3 完了** → `/eval-step` で評価 → Phase A シンプルゴール達成確認 → mainline (Phase 1 撤退) へ進むか、別 audit Phase が必要か判断

A-1 / A-2 の評価では `/eval-step` 自体を dogfood として使う (= 二重の検証になる: A-1 では skill 機能、A-2 では暴発リスク + skill 機能の継続検証)。

---

## 4. 想定リスク

| リスク | 対処 |
|---|---|
| Phase A audit で skill 暴発リスクを実機テストしようとして、テストプロンプトを投げた瞬間に本物の skill が暴発する (テスト自体が暴発で破綻) | 暴発リスクのキーフレーズは「会話としてユーザーが投げる」+「Claude がどう応答するか観察」の自然なやりとりで検証。**意図して Skill tool を呼び出さない**様にユーザーが指示する。Skill 起動を観察したら即 stop |
| Phase A 進行中に Phase 番号衝突 (Phase 0 → A → 1 と進めて Phase 0 plan に "A" が混ざる、等) | `phase_state.json` の `phase` は文字列 `"A"` を保持。`.claude/plans/phase_A_plan_v{M}.md` という別ファイル名にすることで Phase 0 plan と物理的に分離 |
| `/next-plan` skill 内部で「次の Sub-Step を決定」するロジックが、letter ID Phase で動作しない (例: "A-1" → "A-2" の変換が壊れる) | A-1 dogfood 段階で `/next-plan` を呼んで実際の挙動を見る。次 Sub-Step を `A-2` に正しく更新できなければ `update_phase_state.py` を手動で叩いて回避し、SKILL.md に letter ID 対応を明記 |
| 暴発検査で「修正必要」と判定された文言を fix した結果、本来の trigger も発火しなくなる | 修正後に A-1 同等の機能検証を再実行 (= A-3 完了判定の一部) |
| `/eval-step` が Phase A の完了判定を見つけられない (envPlan ではなく phase_A_plan_v{M}.md を読みに行く動作の確認) | SKILL.md には「`phase_{N}_plan_v{M}.md` の §3 / §4 で当該 Sub-Step を探す」と既に記載済。Phase A で実機確認、ダメなら fix |

---

## 5. ブランチ戦略

- Phase A は `chore/step-0-env` で継続 (main merge は Phase A 完了後に判断)
- Phase A 完了時に Step 0 + Phase A を まとめて main へ merge するか、別ブランチに切り替えるかは A-3 完了確認時に決める

---

## 6. envPlan mainline との関係

- envPlan の Phase 1 (撤退) には Phase A 完了後に進む
- Phase A 自体は envPlan には記述されていない off-mainline 追加 Phase だが、Step 0 で整備した天翔十字フローの dogfood + 設計検証として正当
- Phase A 完了時、`docs/development_layer_rules.md` 末尾に「Phase 命名規約: 数値 = mainline / 英字 = off-mainline audit」を追記 (A-3 の一部として実施)

---

**再掲: 本ファイルは Phase A イニシャルプラン (v1)。承認後 A-1 着手。**
