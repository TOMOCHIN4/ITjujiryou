---
name: eval-step
description: 天翔十字フローで Sub-Step 完了時に成果物 (直近 commit + 変更ファイル) と完了判定を突き合わせ、✅/⚠️/❌ 表形式の評価レポートを返す。ファイル書き込みなし。
when_to_use: |
  - Sub-Step が完了した時 (例:「0-1 終わった、評価して」「Sub-Step 評価」「eval step」「0-3 評価レポート」)
  - 踊り場に入る前に直前 Sub-Step の達成度を確認したい時
  - 次プラン (v{M+1}) 作成の入力として実績整理が必要な時
---

# Skill: eval-step

## 前提

- 本セッションは **開発レイヤー** で動いている
- 直近 Sub-Step の作業 commit が存在する
- `.claude/phase_state.json` に現 Phase の情報がある

## 動作

### Step 1: 評価対象の特定

`.claude/phase_state.json` を読み、現 Phase と直前 Sub-Step を特定する。
ユーザーが「0-1 評価して」のように明示している場合はそちらを優先。

評価対象プラン: `.claude/phase_state.json.latest_plan_path` (= 当踊り場プラン)。
完了判定は `phase_{N}_plan_v{M}.md` の §3 / §4 で当該 Sub-Step を探す (Phase 0 については `docs/archive/envPlan.md` も初回 v1 として参照可)。

### Step 2: 成果物の取得

以下を Bash で取得:

```bash
git log -1 --pretty=format:"%H %s" HEAD
git show --stat HEAD
git diff HEAD~1 HEAD --stat
```

直前 commit が当 Sub-Step のものか確認 (commit message に `step-{N}-{M}` 等が含まれることを期待)。複数 commit にまたがる場合は範囲指定で `git log` する。

### Step 3: 完了判定との突き合わせ

評価対象プランの完了判定一覧 (チェックリスト or 表) を抽出し、各項目について以下を判定:

- ✅ 達成 (成果物 / 実機確認で根拠あり)
- ⚠️ 部分達成 / 未検証 (達成しているが実機テスト不足など)
- ❌ 未達

判定根拠を 1 行で添える (例:「commit 86267af で `.claude/settings.json` 追加、JSON 検証 OK」)。

### Step 4: 実績から見えた論点抽出

- 計画外で発覚した制約 (例: hook 即時発火、permission rule glob 形式)
- 次 Sub-Step に持ち越すべき宿題
- プラン文書の更新が必要な箇所 (例: §3.3 削除済段落)

### Step 5: 評価レポート出力

以下フォーマットで Claude のメッセージとしてユーザーに提示:

```markdown
## Sub-Step {N}-{M} 評価

### 完了判定

| 判定項目 | 結果 | 根拠 |
|---|---|---|
| ... | ✅ | ... |
| ... | ⚠️ | ... |

### 実績から見えた論点

1. ...
2. ...

### 次の動き

踊り場 X (= 残り N ステップ向け詳細像更新 = v{M+1} 作成) です。`/next-plan` で進みますか？
```

## 重要

- **ファイル書き込みを一切行わない**。phase_state.json も触らない (それは `/next-plan` の責務)
- 推測で ✅ を付けない。根拠が弱いなら ⚠️ にする
- 完了判定が文書に書かれていなければ、その時点でユーザーに完了判定基準を確認する
