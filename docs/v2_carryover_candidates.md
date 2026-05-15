# v2 設計書からの取り入れ候補 (carry-over)

## 背景

`aitei_juujiryou_v2_master_specification.md` (`ddfdb11` → `261a1a9` で書かれた v2 確定仕様書) は 2026-05-13 の `git reset --hard f8ac85e` で破棄された。破棄の主因は **(α) claude -p 都度起動方式の監視ゼロ問題** (memory: `project_v2_phase_progress.md`) であり、設計そのものが否定されたわけではない。

本書は v2 master spec を全文洗い、**現状 v3.2 安定運用に取り入れても有効そうな** アイデアだけを抽出した carry-over リスト。`master_specification.md` 本体はユーザーが消去予定 (git の `261a1a9` には永続的に残る、必要なら `git show 261a1a9:aitei_juujiryou_v2_master_specification.md` で取り出せる)。

---

## 1. 既に取り入れ済 (引き継ぐ必要なし)

| v2 ID | 項目 | 現状の実装場所 |
|---|---|---|
| D6 | 整理 HOOK (deliver 完了契機) | `src/mcp_server.py:_handle_deliver` の `post_deliver_trigger` event → `inbox_watcher.py` の各 role pane への整理プロンプト |
| D7 | company_memory_write HOOK | `inbox_watcher.py:process_memory_approval` (memory_approval を契機に物理反映 + `_last_write.log` 追記) |
| D8 | ユウコ門番バリデーション (兄弟 company 提案の検証) | yuko workflow.md §Step F (兄弟 memory_proposal を受領 → サザンへ curator_request 転送) |
| D9 | サザン二重構造化 | 2026-05-14 完成 (commit 3eb2a91)。表 Omage Gate + 裏 backstage silent モード |
| D13 | 記憶検索 subagent | 各 role の `.claude/agents/memory-search.md`。yuko 用は `data/memory/**` 全閲覧 + `outputs/**` (2026-05-15 拡張) |
| D14 | 物理ガード (settings.json) | 各 settings.json の `permissions.deny` で他人 personal memory を per-topic deny |
| D15 | HOOK 失敗安全網 | `_last_write.log` (JSONL 追記)、`tests/test_memory_approval_finalization.py` で検証 |
| D16 | 個人記憶ディレクトリ整備 | `data/memory/{souther,yuko,writer,designer,engineer,company}/` 全 6 directory |
| D17 | brevity hook 退役 (旧 v0.13) | 現行 Omage Gate (`scripts/hooks/inject_souther_mode.py`) が代替 |

→ **9 件は v2 設計に対応する形で v3.2 で完了済**。再導入の必要なし。

---

## 2. 取り入れ候補 (有望 + 致命的問題なし)

### 2.1 D4: ワークフロー倉庫 3 階層 (originals / cases / distilled)

```
workflows/
  originals/   # 改変禁止、Studio 出力 or 人間手書き
  cases/{案件ID}/  # 案件ごとのアレンジ
  distilled/   # 案件後の昇格版、再利用可
```

**狙い**: 案件をまたいだ「うまく回った段取り」を蒸留して再利用可能にする。現状は each role の `data/memory/{role}/_scratch/{case_id}/` に案件中のメモが溜まるが、**段取り (= workflow) として再利用可能な単位での蓄積はない**。

**現状からの差分**:
- `workflows/originals/recruit-campaign-master.md` だけ既に復元済 (10 KB)。これを起点に手書きで増やせる
- `cases/` `distilled/` は新規ディレクトリ作成

**取り入れ可否**: ✅ tmux pane を増やさず、yuko CLAUDE.md に「案件着手時は workflows/originals/ から該当 WF を参照」と書くだけで運用開始できる。claude -p 不要。

### 2.2 D5: 蒸留昇格規律 (1 案件 1 兄弟最大 1 本、同原本 派生 3 本上限)

**狙い**: distilled/ の肥大化を防ぐ。

**取り入れ可否**: ✅ D4 の運用ルール。yuko workflow.md に「整理フロー時、各兄弟は再利用価値あり判定で最大 1 本を distill 提案」と書くだけ。コードは不要。

### 2.3 D10: ファイナルプラン形式統一 (frontmatter + CC Workflow Studio 互換)

```markdown
---
name: <workflow-or-plan-name>
description: ...
case-id: 2026-05-13-client-name
agents: [haou, toshi, senshirou]
workflows-referenced: [...]
---
# 本文 (自然言語のマクロフロー)
```

**狙い**:
- 案件横断で検索可能にする (case-id / agents 等)
- 将来 Studio (VSCode 拡張) と互換性確保

**取り入れ可否**: ✅ 既存 `data/memory/company/_proposals/{case_id}.md` の frontmatter スキーマがほぼこの形式 (`schema: proposal/v1`)。案件 final_plan も同じスキーマで `workflows/cases/{案件ID}/final_plan.md` に書くようにすれば自然に統一。

### 2.4 D11: 指示粒度の統一 (ワークフロー名 + 改変指示)

**狙い**: dispatch_task の objective が自由文だと案件横断の比較が難しい。「WF 名 + どこを改変したか」の形式で書けば、同じ WF を何度も回したときの diff が見える。

**取り入れ可否**: ✅ yuko workflow.md §Step B-1 に追記。例:
```
objective: "WF: recruit-copywriting / アレンジ: ターゲット深堀り節を 50 字短縮 + 法令チェックは省略"
```

### 2.5 grill-me による要件確定 (v2 §3.1, §5)

**狙い**: 受注時、ユウコが「何を作るか」を曖昧なまま dispatch せず、grill-me (= 顧客に質問を返して要件を確定するワークフロー) で初期案を固める。

**現状のギャップ**: 現状の yuko workflow.md には「受注時の要件確定プロセス」が明示されていない (yuko が暗黙に判断している)。

**取り入れ可否**: ✅ grill-me の正体は「クライアントに何を聞き返すべきか」を構造化する subagent or workflow。subagent (`workspaces/yuko/.claude/agents/grill-me.md`) を新設して、受注時にユウコが必ず呼ぶ規律にすれば良い。新 tmux pane 不要。

### 2.6 ベンチマーク基盤 (v2 §8)

**狙い**: 改修の効果を定量測定する仕組み。

```
benchmarks/
  cases/kataoka-dental/
    initial_request.md   # 顧客発注書 (fixture、人間起草)
    client_persona.md    # 顧客役の挙動一貫性
  rubric.md              # 評価軸 (要件適合度 / 申し送り精度 / 文字数遵守 / 矛盾の少なさ / そのまま使える度)
  runs/run-<N>/          # 各 Run の納品物
```

**取り入れ可否**: ✅ `docs/case_log_analysis/` の対比表 (5/14 dontAsk vs 5/15 auto) と相性が良い。「改修 X を入れたら Run N+1 で品質が Y % 上がった」を測れるようになる。**ただし Run 実行に時間 + Max OAuth 課金がかかるので、本気でやるなら別セッション計画が必要**。

### 2.7 ユウコ 3 分割の "発想" を別方法で活かす

v2 D1 はそのままだと claude -p 必須 = 監視ゼロ問題が再発する。**ただし狙い (= ユウコ context 膨張の構造的抑制) は ANALYSIS で観察された問題 (Read 12 / 14k tokens) と直結する**。

代替案候補 (どれも tmux 1 pane 維持):
- **(a) /clear + フェーズ別プロンプトテンプレ**: ユウコ pane で「受注 → /clear → 統合 → /clear → 振り分け」と段階別にコンテキストをクリア。各フェーズ前にテンプレ MD を読み込む。Claude Code バージョン依存のリスクは memory に既知 (`project_v2_phase_progress.md` 教訓 1)
- **(b) subagent 経由の段階処理**: 受注時に `yuko-intake` subagent、統合時に `yuko-integrate` subagent、振り分けは本体 pane (本体で実行) という設計。subagent 内で完結する処理は context を本体に持ち込まない
- **(c) 現状 (1 セッション貫通) + dispatch_payload 圧縮 + brevity 原則の徹底だけ**: 2026-05-15 改修で既に達成 (90% 削減)

**取り入れ可否**: ⚠️ (a) は v2 で却下された方式、(b) は新設計、(c) は完了済。**(b) を新たに検討する価値あり** (subagent ベースなら claude -p 監視ゼロ問題を回避できる)。

### 2.8 D2: 兄弟レビュー/実行分離 (発想だけ)

**狙い**: 兄弟が「実行」と「レビュー」で別人のように振る舞える (= 自分の実行物を客観視できる)。

**取り入れ可否**: ⚠️ 兄弟 pane の context が今 何 tokens かを実測してから判断。今は ANALYSIS で yuko しか観察していない。**まず writer/designer/engineer の 1 案件あたり context 食いを測ってから決める**。tmux pane 倍増は重い (5→8 pane)。subagent 化が現実的。

---

## 3. 取り入れない判断

| v2 ID | 項目 | 理由 |
|---|---|---|
| (4.1) | claude -p 都度起動方式 | v2 破棄の主因。監視ゼロ問題 (memory: `project_v2_phase_progress.md` 教訓 1) |
| (4.1) | セッション間 file 経由ハンドオフ | 上の前提なので連帯破棄 |
| (4.8) | Workflow Studio 連携 | v2 でも採用しない判断。スキーマ互換だけ確保で十分 |

---

## 4. 取り入れ優先順位 (推奨)

### 短期 (1 セッションで実装可能)
1. **D11 指示粒度の統一** — yuko workflow.md §Step B-1 に WF 名規約を追記。1 ファイル。
2. **D10 ファイナルプラン形式統一** — 既存 proposal schema と整合化するだけ。
3. **2.5 grill-me subagent 新設** — `workspaces/yuko/.claude/agents/grill-me.md` 1 ファイル + yuko CLAUDE.md 規律追加。

### 中期 (2-3 セッション)
4. **D4 + D5 ワークフロー倉庫 3 階層** — ディレクトリ作成 + yuko workflow.md + 各兄弟 CLAUDE.md の蒸留昇格規律。既存 `workflows/originals/recruit-campaign-master.md` を起点に手書き 5 本配置 (case-by-case で増やす)。
5. **2.7 (b) ユウコ subagent ベース 3 分割** — `yuko-intake` / `yuko-integrate` subagent を新設。本体 pane の context を膨らませずに段階処理を実現。

### 長期 (週単位)
6. **2.6 ベンチマーク基盤** — fixture + rubric + Run 計画。改修の効果測定を定量化。
7. **2.8 兄弟レビュー/実行分離** — 兄弟 context 食いを実測してから判断。

---

## 5. 参照

- 復元元 commit: `git show 261a1a9:aitei_juujiryou_v2_master_specification.md`
- v2 破棄経緯: memory `project_v2_phase_progress.md`
- 既存実装の対応: `SPEC.md`, `workspaces/{role}/CLAUDE.md`, `scripts/inbox_watcher.py`
- ANALYSIS (改修動機): `docs/case_log_analysis/2026-05-14_15.md`
- 復元済関連ファイル:
  - `aitei_juujiryou_v2_confirmed_decisions.md` (議論結果、ユーザーが消去予定)
  - `aitei_juujiryou_v2_master_specification.md` (確定仕様書、ユーザーが消去予定)
  - `workflows/originals/recruit-campaign-master.md` (採用キャンペーン WF 原本、D4 の起点として残す価値あり)
