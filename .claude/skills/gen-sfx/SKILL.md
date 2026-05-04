---
name: gen-sfx
description: Lyria 3 Clip で効果音（タップ音、通知音、UI フィードバック）を生成し、outputs 配下に配置する。
when_to_use: |
  - ボタンタップ・通知・成功・エラー音
  - 案件完了時のジングル
---

# Skill: gen-sfx

## 前提

- プロジェクトルート `.env` に `GEMINI_API_KEY`
- `scripts/gen-asset/setup.sh` 実行済み
- **`ffmpeg` インストール済み**（`brew install ffmpeg`）。トリムを行うため必須。

## 重要原則

1. **Lyria 3 Clip は常に約 30 秒の MP3 を返す**。`--duration` は後処理 ffmpeg トリムで実現する。
2. UI SFX は **0.1〜1.0 秒** が一般的。`--duration 0.5` 程度から試す。
3. 末尾に **50ms のフェードアウト**を自動付与（プチノイズ防止）。

## 手順

```bash
set -a && . .env && set +a
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_sfx.py \
  "soft button tap, short ui click feedback, clean and crisp" \
  --duration 0.5 \
  --out outputs/<task_id>/tap.mp3
```

主要オプション：

| 引数 | 既定 | 用途 |
|---|---|---|
| `--duration` | `1.0` | 出力秒数。30 未満なら ffmpeg でトリム＋フェード。 |
| `--no-trim` | off | 生 30 秒をそのまま保存（ループ素材用） |
| `--out` | `_out/<slug>.mp3` | 出力パス（必ず `outputs/<task_id>/` 配下） |

## 用途別の目安

| 用途 | duration | プロンプト例 |
|---|---|---|
| ボタンタップ | 0.1〜0.3 | `"soft ui tap, single click, short and crisp"` |
| 通知 | 0.5〜1.0 | `"gentle notification chime, two short tones"` |
| 成功 | 0.5〜1.5 | `"success ping, ascending two notes, bright"` |
| エラー | 0.3〜0.8 | `"error buzz, low tone, short"` |
| 環境音ループ | 30（`--no-trim`） | `"ambient cafe background, loopable"` |

## 関連
- `gen-music`（BGM 用、Lyria 3 Pro / 最大 3 分）
- `gen-voice`（TTS）
