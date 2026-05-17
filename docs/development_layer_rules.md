# 開発レイヤー規律

> **位置付け**: 「開発レイヤー本セッション」の運用規律集。`CLAUDE.md` から参照されることを前提とし、規律本文 (レイヤー定義 / 開発レイヤー作業時の規律 / 天翔十字フロー) はすべてこのファイルに置く。CLAUDE.md は薄く保つ。
>
> **作成日**: 2026-05-16 (Step 0 にて新設)
> **最終改修**: 2026-05-17 (Sub-Step 概念廃止、Phase 単一実装単位化)

---

## 1. レイヤー定義

本プロジェクトには 2 つのレイヤーが存在する。両者は **別の「動き方」** を持ち、混同してはならない。

| | 開発レイヤー | 愛帝十字陵レイヤー |
|---|---|---|
| **目的** | 愛帝十字陵システムの開発・改修 | 案件運用 (顧客対応 → 制作 → 納品) |
| **作業場所** | プロジェクト root (`.claude/settings.json` / `CLAUDE.md`) | `personas/{role}/` (新構成、Step 2 で構築予定) |
| **動作形態** | 1 Claude Code セッション (本セッション) | tmux 2 pane (orchestrator + executor、Step 2 以降で設計) |
| **起動** | `claude` (cwd = project root) | (Step 2 で別途設計) |
| **フロー** | **天翔十字フロー** で動く (本書 §3) | **普遍フロー (A→F + 踊り場 4 つ)** で動く |

本セッション (= Claude Code) が動いているのは **開発レイヤー** である。

---

## 2. 開発レイヤー作業時の規律

開発レイヤー作業中、以下を守る:

1. **愛帝十字陵レイヤーへの介入禁止**
   - `workspaces/` や旧 `mcp_server` に「設計上の理由なく」介入しない。
   - Step 1 (撤退) で設計が決まるまで、愛帝十字陵レイヤー (`personas/` を含む将来構成) には変更を加えない。
2. **不可逆 git 操作は事前確認**
   - `git push --force` / `git reset --hard` / `git branch -D` / `rm -rf` 系 / `--no-verify` / `--no-gpg-sign` は、ユーザーの明示承認なしに実行しない。
   - 承認は「その操作に対して」のみ有効。次回別の不可逆操作を行うときは再確認。
3. **天翔十字フローを守る**
   - 案件着手前に、シンプルゴール / 全 Phase 数 N / 当 Phase の完了判定が承認されたプランが存在することを確認する。
   - 各 Phase 終了時は必ず評価 → 次 Phase 着手承認の順を踏む。

---

## 3. 天翔十字フロー

開発レイヤー作業はすべて以下のフローで動かす。**ただし天翔十字フロー本体・skill・hook・docs・settings の整備自体はこのフローを通さない (§3.4 参照)**。

### 3.1 フロー定義

```
1. ユーザーから指示を受ける
2. シンプルゴール設定 + 全 Phase 数 N (3 / 5 / 7) を判断
3. Phase A のプランを作成 (= 当 Phase の完了判定を含む)
4. ユーザー承認
5. Phase A 実行
6. Phase A 終了後、Claude Code + ユーザーで評価
7. Phase B のプランを作成 → ユーザー承認
8. Phase B 実行 → 評価
9. ... 同様に Phase 最終まで
10. 全 Phase 完了時にシンプルゴール達成
```

### 3.2 整理

- **N は 3 / 5 / 7 から選ぶ** — 案件規模で判断し、確定後変更しない。
- **「N を決める」 = Sub-Step を作らずに収まる粒度に分割すること**。粒度が大きすぎるなら N の取り方を見直して Phase を切り直す。
- **各 Phase は単一の実装単位** — N=3 なら Phase A / B / C それぞれ独立した実装単位として扱う。
- **シンプルゴールは全 Phase 通して不変**。
- **各 Phase 終了時に評価 → 次 Phase 着手承認** の順を必ず踏む。

### 3.3 「Phase 以外作るな」原則

天翔十字フローでは **Phase 以外の構造物を作ってはならない**。Sub-Step / サブフェーズ / 踊り場 / 中間プラン / プラン版数 (v1, v2…) / セカンドプラン (= 次プラン v{M+1}) のいずれも禁止。1 Phase = 1 plan ファイル (`.claude/plans/phase_{ID}.md`) 固定、修正は同ファイル直接編集、来歴は git 履歴。粒度が大きすぎたら N の取り方を見直して Phase を切り直す。

この原則は禁止形で表現される。「Phase 単位で考えろ」ではなく「**Phase 以外作るな**」。

### 3.4 フロー自体の整備はフロー外

天翔十字フロー本体 (本ドキュメント / skill / hook / `.claude/settings.json` / phase_state スキーマ等) の改修は、**天翔十字フローを通さずに直接実行する**。

理由:
- フロー本体の改修中はフロー駆動状態を「中断」とする方が安全 (自己言及回避)。
- 改修中の状態は `phase_state.json` の `phase_current: "_frozen"` で表現する (この間 hook は注入をスキップする)。
- 改修完了後、最初の本番案件 (envPlan mainline Phase 1 など) を新しい仕様で立ち上げる。

フロー外作業への切替は `python3 scripts/dev_hooks/freeze_phase_state.py --freeze` で凍結、復帰は `--unfreeze-to-init` で空白化してから初回 `/init-plan` を呼ぶ。`phase_state.json` を手で編集せず、必ず helper を経由すること。

`freeze_phase_state.py --freeze` の起動契機は **自動** と **手動** の 2 種類:

- **自動**: 最終 Phase (`phase_remaining=0`) の `/eval-phase` 完了時、skill が評価レポート出力直後に自動実行する。シンプルゴール達成と同時にフローを凍結し、次案件への切替準備を完了させる
- **手動**: フロー本体の改修に入る前、ユーザー意思でフロー中断する時、ユーザーが直接コマンドを叩く

### 3.5 skill による自動化

天翔十字フロー上の典型作業は 3 つの skill で自動化されている:

| skill | 起動 | 用途 |
|---|---|---|
| `/init-plan` | 手動 | **初回 Phase 着手時のみ**。`.claude/plans/phase_{ID}.md` 雛形を生成 + `phase_state.json` を初回 Phase 用に atomic 初期化 (シンプルゴール / N の確定はこの skill 限定) |
| `/next-plan` | 手動 | **2 回目以降の Phase 着手時**。`.claude/plans/phase_{ID}.md` 雛形を生成 + `phase_state.json` を次 Phase 用に atomic 遷移 (シンプルゴール / N は継承して書き換えない) |
| `/eval-phase` | **自動** (+ 手動互換) | Phase 完了判定を満たした直後、skill 側で**自発的に**起動して評価レポートを返す。最終 Phase (`phase_remaining=0`) では評価出力直後に `freeze_phase_state.py --freeze` を実行してフロー凍結まで自動化。明示的な `/eval-phase` 呼出 (再評価用途) も互換で残存 |

phase_state.json の atomic 更新は責務ごとに分かれた 3 helper が temp file → `os.replace()` で行う:

- `scripts/dev_hooks/init_phase_state.py` — 初回 Phase 専用。既存 `phase_current` が `_frozen` 以外なら exit 1
- `scripts/dev_hooks/advance_phase_state.py` — 2 回目以降専用。受理キーは `phase_current` / `phase_remaining` / `latest_plan_path` のみ。`phase_simple_goal` / `phase_total` を渡すと exit 1 (= シンプルゴール / N の物理ガード)
- `scripts/dev_hooks/freeze_phase_state.py` — フロー外作業用。`--freeze` / `--unfreeze-to-init`

---

## 4. Phase 進行状態の参照

「いま何の Phase を進行中か」の真実源は **`.claude/phase_state.json`** である。

スキーマ:

| キー | 意味 |
|---|---|
| `phase_current` | 現在の Phase ID (例: `"A"` / `"1"`)。フロー外作業中は `"_frozen"` |
| `phase_simple_goal` | フロー全体のシンプルゴール (不変) |
| `phase_total` | 全 Phase 数 N (3 / 5 / 7)。凍結中は `0` |
| `phase_remaining` | 残 Phase 数。凍結中は `0` |
| `latest_plan_path` | 最新の Phase プラン (project-local パス、`.claude/plans/phase_{ID}.md`) |
| `updated_at` | 直近更新日時 (ISO 8601) |

UserPromptSubmit hook (`scripts/dev_hooks/inject_phase.py`) がこのファイルを読み、各プロンプト処理前に context 先頭へ Phase 情報を注入する。状態の更新は Phase 着手時 (`/init-plan`) に行う。`phase_current` が `"_frozen"` のときは hook は注入をスキップする。

---

## 5. このファイルの位置

- `CLAUDE.md` は薄く保ち、本ファイル (`docs/development_layer_rules.md`) を参照する形にする。
- 規律の更新は本ファイルを直接編集する。CLAUDE.md は参照リンクのみ。
- 本ファイルは Phase 1 以降の作業基盤として継続利用される。
- 本ファイル自身の更新も §3.4 に従い天翔十字フロー外で実施する。
