# scripts/ 索引

`scripts/` ディレクトリ配下に置かれた全 `.py` / `.sh` を、用途・呼び出し元・依存関係でまとめた索引。新規 onboarding や「これは何が呼んでいるのか」を素早く辿るための一覧。`__pycache__/` および `gen-asset/venv/` は対象外。

最終更新: 2026-05-17 (Phase A)

---

## 1. 天翔十字フロー hook (`scripts/dev_hooks/`)

開発レイヤーの Phase 進行状態を扱う 2 本。詳細仕様は `docs/development_layer_rules.md`。

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `dev_hooks/inject_phase.py` | Python | UserPromptSubmit hook。`.claude/phase_state.json` を読み、各プロンプト処理前に `[Phase X / 残 Y phase]` を context に注入。`phase_current == "_frozen"` のときは注入スキップ。 | `.claude/settings.json:43` (`UserPromptSubmit`) |
| `dev_hooks/update_phase_state.py` | Python | `.claude/phase_state.json` を tempfile → `os.replace()` で atomic 更新。`key=value` 形式 CLI、`phase_total` / `phase_remaining` のみ int 化、`updated_at` は JST ISO 8601 で自動付与。 | `.claude/skills/init-plan/SKILL.md:83` (Step 3) |

---

## 2. multi-process 運用 (`scripts/` トップ)

tmux ベースの 5 人組事務所セッションを起動・常駐させるシェル + watcher。詳細は `SPEC.md §2-§3`, `README.md`。

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `start_office.sh` | bash | tmux session `itj` を立ち上げる。office (souther / yuko ほか) + watcher + api の各 window を起動。`ITJ_PERMISSION_MODE` で claude の permission モード切替 (現行 default = `auto`、2026-05-14 切替済)。 | ユーザー手動実行。README/SPEC.md/`stop_office.sh` のヒントで案内 |
| `stop_office.sh` | bash | `tmux kill-session -t itj`。冪等。 | ユーザー手動実行、README/SPEC.md |
| `inbox_watcher.py` | Python | SQLite `messages` を 1 秒 polling し、`delivered_at IS NULL` の行を該当 role の tmux pane に `tmux send-keys` で投入。`post_deliver_trigger` event の整理プロンプト送信、`memory_approval` の物理反映、cron-based curator trigger 発火 (`maybe_fire_scheduled_curator_triggers`) も担う。 | `start_office.sh:88` (watcher window 内で常駐起動)。tests: `tests/test_inbox_watcher_curator.py`, `tests/test_post_deliver_hook.py`, `tests/test_memory_approval_finalization.py` |

---

## 3. multi-process hook (`scripts/hooks/`)

souther / yuko の Claude Code pane 用フック。Omage Gate (サザン発言制御) と persona 漏れ防止を物理的にガードする。詳細は `SPEC.md §7`, `README.md`。

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `hooks/inject_souther_mode.py` | Python | 社長 (souther) pane の UserPromptSubmit hook。`workspaces/souther/_modules/quotes.md` から 27 名台詞を cooldown 付きで 3 つ抽選、Omage 化指示を additionalContext に注入。`[BACKSTAGE:curator]` sentinel 検出時は silent context のみ注入 (Omage Gate skip)。 | `workspaces/souther/.claude/settings.json:UserPromptSubmit` |
| `hooks/check_souther_recipient.py` | Python | 社長 pane の PreToolUse hook (`mcp__itjujiryou__send_message`)。宛先 `to != "yuko"` を `exit 2` で deny。サザンはユウコとしか会話しない設計を物理的に強制。 | `workspaces/souther/.claude/settings.json:PreToolUse` |
| `hooks/check_persona_leak.py` | Python | ユウコ (yuko) pane の PreToolUse hook (`mcp__itjujiryou__deliver`, `mcp__itjujiryou__send_message`)。`src/persona.find_forbidden_terms` で前世名 / 社内符丁 / 称号などの混入を検出して deny。 | `workspaces/yuko/.claude/settings.json:46,55` |

---

## 4. アセット生成 (`scripts/gen-asset/`)

Gemini / Lyria を呼んで画像・音声・SFX・楽曲を生成する CLI 群。共通基盤 (`_common.py`) と後処理 (`postprocess.py`) を中心に組み合わせて使う。各 skill (`.claude/skills/gen-*`, ユーザー level `asset-maker`) から呼び出される。

### 4.1 セットアップ

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `gen-asset/setup.sh` | bash | Python 3.10+ を検出して `gen-asset/venv` を作成、`requirements.txt` (google-genai, pillow) を install。ffmpeg の有無を warn 表示。 | `workspaces/designer/.claude/settings.json:22` で `Bash(scripts/gen-asset/setup.sh:*)` 許可。各 `.claude/skills/gen-*/SKILL.md` 前提として案内 |
| `gen-asset/_common.py` | Python | 共通関数: `get_api_key()` / `resolve_output()` / `ensure_parent()` / `slugify()` / `project_root()`。他の gen-asset スクリプトから `from _common import ...` で参照される共通モジュール。 | `gen_image.py` / `gen_music.py` / `gen_sfx.py` / `gen_tts.py` / `postprocess.py` / `split_sprites.py` (同ディレクトリ内 import) |

### 4.2 生成 CLI

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `gen-asset/gen_image.py` | Python | Gemini Nano Banana 2 (`gemini-3.1-flash-image-preview`) で画像生成。aspect / size / thinking / reference / grounding を CLI フラグで指定。 | `.claude/skills/gen-image/SKILL.md:31,62` |
| `gen-asset/gen_music.py` | Python | Lyria 3 Pro (`lyria-3-pro-preview`) で BGM 生成 (最大 180 秒)。 | `.claude/skills/gen-music/SKILL.md:20` |
| `gen-asset/gen_sfx.py` | Python | Lyria 3 Clip (`lyria-3-clip-preview`) で SFX 生成。常に 30 秒返るので `--duration` < 30 のときは ffmpeg で末尾フェード付きトリム。 | `.claude/skills/gen-sfx/SKILL.md:27` |
| `gen-asset/gen_tts.py` | Python | Gemini 3.1 Flash TTS (`gemini-3.1-flash-tts-preview`) で TTS 生成。PCM 24kHz → WAV 出力。Skill 名は `gen-voice` だがファイル名は `gen_tts.py`。 | `.claude/skills/gen-voice/SKILL.md:21,38` |

### 4.3 後処理 / 派生

| パス | 言語 | 主な用途 | 呼び出し元 |
|---|---|---|---|
| `gen-asset/postprocess.py` | Python | 画像の透かし除去 / リサイズ / 0.5MB 以下圧縮 / chroma-key alpha / bbox 検出 / blob 検出。`gen_image` / `asset-maker` の共通パイプライン。`split_sprites.py` から関数 import される基盤。 | `.claude/skills/gen-image/SKILL.md:47` (`--trim-watermark`)、`split_sprites.py:16-27` (関数 import) |
| `gen-asset/split_sprites.py` | Python | 4K グリッド画像をセル分割し、Asset Catalog (`<pack>/<Name>.imageset/`) に配置。透かし除去 → NxM 分割 → 各セルをリサイズ＆圧縮 → metadata 生成までを 1 本のパイプラインで実行。 | プロジェクト内 grep ヒット 0。ユーザー level の `asset-maker` skill 経由で **手動 / 都度直接実行** される運用 (memory `reference_split_sprites_modes.md` 参照) |
| `gen-asset/crop_desk.py` | Python | rembg 透過済み 1:1 cell PNG を、bbox + target アスペクト (3:1, 3:2 等) で center crop してから target size へリサイズ。scene.js 側で stretch するのを避けるための前処理。 | **プロジェクト内 grep ヒット 0 / 廃止疑い**。memory `feedback_asset_aspect_handling.md` に手法が記録されているが、現状どの skill / hook からも呼ばれていない。実運用で利用しているなら呼出元の明文化 or 削除判断が必要 |

---

## 補足

- `scripts/gen-asset/venv/` は `setup.sh` が作る Python venv。git で追跡しない前提。本索引の対象外。
- `scripts/__pycache__/` および各サブディレクトリの `__pycache__/` も対象外。
- `scripts/gen-asset/requirements.txt` (`google-genai>=0.3.0`, `pillow>=10.0.0`) は `setup.sh` が `pip install -r` で読む依存リスト。

## 廃止候補 / 要判断

- `gen-asset/crop_desk.py`: 呼び出し元 0 件。利用継続なら呼び出し場所を明記、不要なら削除。
