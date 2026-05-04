---
name: gen-voice
description: Gemini 3.1 Flash TTS で音声（ナレーション・読み上げ・キャラ台詞）を生成し、outputs 配下に配置する。
when_to_use: |
  - ダッシュボード起動時のナレーション
  - 聖帝・ユウコのキャラボイス
  - アクセシビリティ用の音声説明
---

# Skill: gen-voice

## 前提

- プロジェクトルート `.env` に `GEMINI_API_KEY`
- `scripts/gen-asset/setup.sh` 実行済み

## 手順

```bash
set -a && . .env && set +a
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_tts.py \
  "ふん、許す。" \
  --voice Kore \
  --out outputs/<task_id>/souther_approve.wav
```

> Note: スクリプトファイル名は `gen_tts.py`（IOS_app から踏襲）だが、Skill 名としては `gen-voice`。

## 音声タグ

プロンプト内に挿入できる演出タグの例：
- `[whispers]` — ささやき
- `[happy]` — 明るく
- `[slow]` — ゆっくり
- `[pause]` — 一拍空ける

```bash
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_tts.py \
  "[slow] 帝王に・・・[pause] 逃走はないのだ。" \
  --voice Charon \
  --out outputs/<task_id>/souther_decree.wav
```

## 関連
- `gen-sfx`：効果音
- `gen-music`：BGM
