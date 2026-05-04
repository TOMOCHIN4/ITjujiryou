---
name: gen-image
description: Gemini Nano Banana 2 で Web 用画像（ロゴ、ヒーロー、OGP、favicon、ヘッダー、装飾）を生成し、outputs 配下に配置する。
when_to_use: |
  - ロゴ案、ヒーロー画像、OGP、favicon、装飾画像が必要
  - Image to Image（参照画像から再生成・差分修正）
---

# Skill: gen-image

## 前提

- プロジェクトルートの `.env` に `GEMINI_API_KEY` 設定済み（`set -a && . .env && set +a` でロード）
- `scripts/gen-asset/setup.sh` 実行済み

## 重要原則

1. **生成は常に 4K**（`--size 4K`）。中途半端な解像度を指定しない。
2. **Gemini 透かしを除去**：生成画像の右下に透かしが入るため、納品前に必ずトリミング (`postprocess.py --trim-watermark bottom-right`)。
3. **Web 用途の容量目安**：1 ファイル 2MB 以下を目安。OGP/favicon は 0.5MB 以下が望ましい。WebP 化で半減できる。
4. **出力先は `outputs/<task_id>/` 配下**。`src/` や `prompts/` 等のソースディレクトリには絶対に置かない。

## 手順

1. ユウコ／社長から用途と最終解像度を確認（ロゴ / ヒーロー / OGP / favicon / etc）
2. プロンプトと出力パスを決定
3. 4K で生成：

```bash
set -a && . .env && set +a
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_image.py \
  "<プロンプト>" \
  --aspect 1:1 --size 4K --thinking high \
  --out .build/gen-asset/raw/<name>.png
```

### パラメータ注意

- `--thinking`：現行モデル `gemini-3.1-flash-image-preview` は **`high` または `off` のみ対応**。`low`/`medium` は 400 INVALID_ARGUMENT になる
- `--size`：`0.5K` / `1K` / `2K` / `4K`
- `--aspect`：`1:1`（ロゴ・アイコン）/ `16:9`（ヒーロー・OGP）/ `9:16`（モバイル背景）
- 出力は実際には JPEG が返ることがある。Web 用に PNG が欲しければ `sips -s format png <in> --out <out.png>`、サイズを抑えたければ WebP 化

4. 後処理（透かし除去 → リサイズ → 圧縮）：

```bash
scripts/gen-asset/venv/bin/python scripts/gen-asset/postprocess.py \
  --in .build/gen-asset/raw/<name>.png \
  --out outputs/<task_id>/<name>.png \
  --target-size 1024 \
  --max-bytes 2097152 \
  --trim-watermark bottom-right
```

5. 2MB を超えた場合：`--target-size` を縮小、または WebP 変換（`cwebp` / Pillow）。OGP は 1200x630 推奨、favicon は 256x256 → ICO 化を検討。

## Image to Image（参照画像から再生成）

既存画像を参照に再生成する場合は `--reference` で 1 枚渡す。

```bash
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_image.py \
  "同じ構図・色味で、ロゴだけ青系に変更" \
  --aspect 1:1 --size 4K --thinking high \
  --reference outputs/<task_id>/logo_v1.png \
  --out .build/gen-asset/raw/logo_v2.png
```

## gen-image と gen-sprites の使い分け

| 状況 | 選択 |
|---|---|
| 単発（1〜2 枚） | `gen-image` |
| 同テイストで 4 枚以上揃えたい | `gen-sprites`（4K 1 枚で済むので API コスト効率が良い） |
| 3x3 未満の小グリッド | `gen-image` を複数回 |

## 関連
- 派生 Skill：`gen-sprites`（グリッド生成→分割）
