# benchmarks/ — IT十字陵 v2 ベンチマーク基盤

愛帝十字陵 v2 の主張 (**「Opus 4.7 + 厳選 SKILLS の単体構成を上回る納品物を出す」**) を、構造変化の効果として数字で検証するための基盤。

設計の全体像は `../aitei_juujiryou_v2_confirmed_decisions.md` §15-17 を参照。

## 目的

- 単体構成 (ベースライン) と IT十字陵 (各 Phase 構成) で **同じ案件** を実行し、納品物の品質を比較
- Phase ごとの増分実行により「どの Phase が品質に効いたか」を切り分ける
- **構造の違いによる差** だけを測るため、両構成は同一の SkillCollection を共用

## ベンチマーク案件

1 件のロングラン複合案件で増分評価する。

- **案件**: かたおか歯科クリニック 歯科衛生士求人セット
- **求人者**: 大阪府枚方市 かたおか歯科クリニック
- **ターゲット**: 徳島大学歯学部 口腔保健科の学生 (卒後は歯科衛生士)
- **想定納品物**: LP、パンフレット、ポスター 他 (確定範囲は案件中 grill-me で決定)

## ディレクトリ構成

```
benchmarks/
├── README.md                         # 本ファイル
├── rubric.md                         # 評価軸 (5 軸、Phase 0 Track A で本文確定)
└── cases/
    └── kataoka-dental/               # ベンチマーク案件 fixture
        ├── initial_request.md        # 顧客発注 (人間担当、300-500字)
        ├── client_persona.md         # 顧客役の一貫性メモ (人間担当)
        └── runs/                     # Run 1〜6 の納品物ログ (Run 実行時に生成)
            ├── run1-baseline-single/
            ├── run2-v1-current/
            ├── run3-phase2/
            ├── run4-phase3a/
            ├── run5-phase3b/
            └── run6-phase4/
```

## Run 計画

| Run | 構成 | タイミング | 目的 |
|---|---|---|---|
| **Run 1** | 単体 Opus 4.7 + SkillCollection | Phase 0 中 | ベースライン |
| **Run 2** | 現行 v1 IT十字陵 | Phase 0 中 | v1 比較 + サザン HOOK 棚卸しのログ源 |
| **Run 3** | Phase 2 完了時点 (workflows + memory) | Phase 2 完了後 | 基盤の効果 |
| **Run 4** | Phase 3a 完了時点 (ユウコ分割のみ) | Phase 3a 完了後 | ユウコ分割の効果 |
| **Run 5** | Phase 3b 完了時点 (兄弟分割含む) | Phase 3b 完了後 | **v2 の最終勝負点** |
| **Run 6** (任意) | Phase 4 完了時点 (HOOK 群含む) | Phase 4 完了後 | HOOK の効果 |

**Run 1 vs Run 5/6** が v2 の最終結論。Run 3/4/5 の差分で「どの Phase が効いたか」を切り分け。

## SkillCollection の取り扱い

- 場所: `/Users/tomohiro/Desktop/ClaudeCode/SkillCollection`
- 単体構成と IT十字陵 の両方からアクセス可
- 兄弟役は各々の職能に該当する Skill を選んで使う
- ユウコは Skill を直接使わない (ノードは社員、Skill は兄弟のノード)

## 顧客役の運用

- 各 Run で人間 (ユーザー本人) が顧客役を担う
- `initial_request.md` を起点に、毎 Run 同じ発注メッセージから始める
- `client_persona.md` を参照して各 Run 間で「同程度の厳しさ・同程度の方向修正幅」を心がける
- 完全な再現性は諦め、揺らぎは許容前提

## 評価方法

- 各 Run 完了時に納品物一式を `cases/kataoka-dental/runs/<run>/` に保存
- `rubric.md` の 5 軸でブラインド評価 (どの構成か知らない状態で採点)
- 評価結果は `cases/kataoka-dental/scores/<run>.md` に記録 (実装は Phase 0 Track A で確定)
