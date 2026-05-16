同階層の SPEC.md に必ず従う (現状仕様書)。PLAN.md は未着手 TODO の置き場で、空のことが多い。

## 開発レイヤーで動いている

本セッションは **開発レイヤー** (= 愛帝十字陵システムの開発・改修) で動く。レイヤー定義 / 開発レイヤー作業時の規律 / 天翔十字フローの本文は `docs/development_layer_rules.md` を参照すること。

現在の Phase 進行状態は `.claude/phase_state.json` を真実源とする (UserPromptSubmit hook が各プロンプト処理前に context へ注入する)。現役の Phase プランは `.claude/plans/phase_{ID}.md`、退避済の旧プランは `.claude/plans/_archive/` 配下。
