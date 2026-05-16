---
name: eval-phase
description: 天翔十字フローで Phase 完了時に成果物 (当 Phase の commit 範囲 + 変更ファイル) と完了判定を突き合わせ、✅/⚠️/❌ 表形式の評価レポートを返す。ファイル書き込みなし。
when_to_use: |
  - Phase が完了した時 (例:「Phase A 終わった、評価して」「Phase 評価」「eval phase」「Phase B 評価レポート」)
  - 次 Phase に進む前に直前 Phase の達成度を確認したい時
  - 完了判定を満たしているかの最終チェック
---

# Skill: eval-phase

## 前提

- 本セッションは **開発レイヤー** で動いている (`docs/development_layer_rules.md` 参照)
- 直近 Phase の作業 commit が存在する
- `.claude/phase_state.json` に現 Phase の情報がある

## 動作

### Step 1: 評価対象の特定

`.claude/phase_state.json` を読み、現 Phase (= `phase_current`) を特定する。
ユーザーが「Phase A 評価して」のように明示している場合はそちらを優先。

評価対象プラン: `.claude/phase_state.json.latest_plan_path` (= `.claude/plans/phase_{ID}.md`)。
完了判定は当該 plan ファイルから抽出する。

### Step 2: 成果物の取得

以下を Bash で取得:

```bash
git log --pretty=format:"%H %s" -n 10
git diff --stat HEAD~N HEAD   # N = Phase 内の commit 数
```

当 Phase の commit 範囲 (= `init-plan` 直後から HEAD まで) を確認する。複数 commit にまたがる場合は範囲指定で `git log` する。

### Step 3: 完了判定との突き合わせ

評価対象プランの完了判定一覧を抽出し、各項目について以下を判定:

- ✅ 達成 (成果物 / 実機確認で根拠あり)
- ⚠️ 部分達成 / 未検証 (達成しているが実機テスト不足など)
- ❌ 未達

判定根拠を 1 行で添える (例:「commit abc1234 で `.claude/settings.json` 追加、JSON 検証 OK」)。

### Step 4: 実績から見えた論点抽出

- 計画外で発覚した制約
- 次 Phase に持ち越すべき宿題 (= 次 Phase の `init-plan` 入力)
- プラン文書の更新が必要な箇所

### Step 5: 評価レポート出力

以下フォーマットで Claude のメッセージとしてユーザーに提示:

```markdown
## Phase {ID} 評価

### 完了判定

| 判定項目 | 結果 | 根拠 |
|---|---|---|
| ... | ✅ | ... |
| ... | ⚠️ | ... |

### 実績から見えた論点

1. ...
2. ...

### 次の動き

Phase {ID} 完了。次 Phase ({次の ID}) に進みますか？ 進む場合は `/init-plan` を呼んでください。
```

## 重要

- **ファイル書き込みを一切行わない**。`phase_state.json` も触らない (次 Phase 着手は `/init-plan` の責務)
- 推測で ✅ を付けない。根拠が弱いなら ⚠️ にする
- 完了判定が文書に書かれていなければ、その時点でユーザーに完了判定基準を確認する
- **Sub-Step / 踊り場 / v{M+1} の概念は天翔十字フローから廃止された**。評価は常に Phase 単位
