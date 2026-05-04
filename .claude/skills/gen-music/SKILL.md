---
name: gen-music
description: Lyria 3 Pro で BGM（最大3分）を生成し、outputs 配下に配置する。
when_to_use: |
  - ダッシュボードのオープニング/ローディング BGM
  - イベント発生時のジングル背景
---

# Skill: gen-music

## 前提

- プロジェクトルート `.env` に `GEMINI_API_KEY`
- `scripts/gen-asset/setup.sh` 実行済み

## 手順

```bash
set -a && . .env && set +a
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_music.py \
  "calm ambient piano, post-apocalyptic, slow tempo" \
  --duration 60 \
  --out outputs/<task_id>/bgm.mp3
```

主要オプション：
- `--duration`：秒数（最大 180）
- `--out`：出力パス（必ず `outputs/<task_id>/` 配下）

## 関連
- `gen-sfx`：効果音（短尺）
- `gen-voice`：読み上げ
