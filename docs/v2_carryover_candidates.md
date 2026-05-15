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

### 2.7 ユウコ 3 パイプ別セッション分割

v2 D1 の "3 分割" の本質は **subagent 3 体ではなく、ユウコ自身のセッションを「対話相手 (パイプ) 」単位で区切る** こと。ユウコには明確に 3 種類の対話パイプがある:

| パイプ | 相手 | 主な動作 | 持ち込む context |
|---|---|---|---|
| **P1 対クライアント** | 顧客 (UI 側 visitor) | 受注 / 要件確認 / 納品報告 | クライアントプロフィール、案件要件、納品物サマリ |
| **P2 対社長サザン** | サザン pane | 上申 / curator_request / 承認受領 | 案件要件、整理候補メモ、決裁待ち事項 |
| **P3 対社員三兄弟** | writer / designer / engineer pane | dispatch_task / report 受領 / 統合 | WF 名、各兄弟の役割と納品 spec、進捗状態 |

**狙い**: パイプが切り替わるタイミングで context を整理することで、ユウコ pane 全体の肥大化 (ANALYSIS で観測: Read 12 / 14k tokens / 1 ターン) を構造的に抑制する。同じセッションに 3 パイプ分の文脈を混在させないことで、各パイプでの判断精度も上がる。

**設計上の核心 = パイプ切替時の引き継ぎ装置**:

context を捨てても次のパイプで困らないよう、**パイプ間で受け渡す最小情報** をファイル化する。例:

- P1 → P3 切替時: `data/yuko_handoff/{case_id}/to_brothers.md` (案件 ID / 要件サマリ / WF 名 / 各兄弟への objective)
- P3 → P2 切替時: `data/yuko_handoff/{case_id}/to_souther.md` (兄弟成果サマリ / 整理候補メモ / 上申事項)
- P2 → P1 切替時: `data/yuko_handoff/{case_id}/to_client.md` (納品物パス / 申し送り事項)

ハンドオフファイル自体は既存の `data/memory/yuko/_scratch/{case_id}/` や `data/memory/company/_proposals/{case_id}.md` と統合する余地がある (重複を作らないこと)。

**セッション区切りの実装手段** (どれを採るかは別途検討、ここでは選択肢のみ):
- **(α) /clear + パイプ別ロードテンプレ**: 同一 pane で `/clear` → 次パイプの初期プロンプト + 該当ハンドオフファイル読込。最小コスト、Claude Code バージョン依存リスクは既知 (`project_v2_phase_progress.md` 教訓 1)
- **(β) tmux pane 分離 (P1/P2/P3 で別 pane)**: 同時並行性は最高だが、OAuth セッション数 / 監視負荷が増える。yuko 1 pane の前提 (現行設計) を覆す
- **(γ) ハンドオフファイル経由の擬似分割 (現行の延長)**: pane も /clear もせず、各パイプ突入時に「これからは P3 モード」と明示しつつハンドオフファイルを再読込。context は完全には切れないが、ユウコ自身が「今どのパイプか」を意識する規律ガード

**取り入れ可否**: ⚠️ 現段階では設計のみ。実装着手前に、(α) (β) (γ) どれを採るか / ハンドオフファイル schema / 既存 `_scratch` `_proposals` との重複整理 を決める必要あり。v2 D1 が破棄されたのは claude -p 都度起動方式が原因なので、**セッション分割の発想自体は生かしてよい** (claude -p を使わずに実現する手段が上記 (α)〜(γ))。

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
5. **2.7 ユウコ 3 パイプ別セッション分割** — ハンドオフファイル schema を先に決め、(α) /clear + パイプ別ロードテンプレ / (β) pane 分離 / (γ) 規律ガードのみ のいずれかで実装。subagent 化ではなくユウコ自身のセッションを区切る方向。

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
