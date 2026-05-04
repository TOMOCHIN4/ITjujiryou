---
name: gen-sprites
description: Gemini Nano Banana 2 でスプライト／アイコンセットを 4K グリッドで一括生成し、透かし除去・分割・圧縮して outputs 配下に配置する。
when_to_use: |
  - キャラ・UI アイコンなどを揃ったテイストでまとめて生成したい
  - 5x5 等のグリッド画像から個別アセットを切り出したい
  - gen-image を 1 枚ずつ呼ぶより効率が良いケース
---

# Skill: gen-sprites

gen-image の派生。**1 枚の 4K グリッド画像を生成 → 透かし除去 → セル分割 → 個別圧縮 → outputs 配置** までを自動化する。

## 前提

- プロジェクトルート `.env` に `GEMINI_API_KEY`
- `scripts/gen-asset/setup.sh` 実行済み（Pillow 含む）

## 重要原則

1. **生成は常に 4K**（`--size 4K`）
2. **Gemini 透かしを除去**（4K 画像の右下にウォーターマーク）
3. **Web 用途の容量目安：2MB / セル**（一般 UI アイコンなら 256〜512px 程度で十分軽い）
4. **出力先は `outputs/<task_id>/` 配下**

## 推奨グリッド

- **最小 3x3**。2x2 は右下 1 セルを空ける透かし回避運用が成立しない。
- **既定 5x5**。10x10 を超えるとセルあたり解像度が落ちて品質劣化が顕著。

## 入力パラメータ

| 名前 | 必須 | 例 |
|---|---|---|
| `prompt` | yes | "ピクセルアート、灰色背景、各セル中央配置" |
| `grid` | yes | `5x5` |
| `cells` | no | `["souther","yuko","designer","engineer","writer", ...]`（省略時はモデル任せ） |
| `style` | no | `pixel-art` / `flat-icon` / `silhouette` |
| `pack_name` | yes | `Members`（出力サブディレクトリ名） |
| `cell_target` | no | 256（最終セル解像度、既定 256） |

## 手順

1. ユウコから `prompt` / `grid` / `pack_name` / セル内容を確認
2. プロンプトを組み立て：「`grid` 等分グリッドで `cells` を順に配置、グリッド線で明確に区切る、背景は均一」を必ず含める
3. 4K で 1 枚生成：

```bash
set -a && . .env && set +a
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_image.py \
  "<組み立て済みプロンプト>" \
  --aspect 1:1 --size 4K --thinking high \
  --out .build/gen-asset/raw/<pack_name>.png
```

4. パイプライン実行（透かし除去 → グリッド分割 → リサイズ → 圧縮 → outputs 配置）：

```bash
scripts/gen-asset/venv/bin/python scripts/gen-asset/split_sprites.py \
  --in .build/gen-asset/raw/<pack_name>.png \
  --grid 5x5 \
  --names "souther,yuko,designer,engineer,writer,..." \
  --trim-watermark bottom-right \
  --cell-size 256 \
  --max-bytes 2097152 \
  --out outputs/<task_id>/<pack_name>/
```

> Note: `split_sprites.py` は元々 iOS Asset Catalog の `*.imageset/` 構造で出力するオプションを持つが、Web 用途では **既定のフラット PNG 配置**で良い（imageset サブディレクトリ生成は不要）。`--write-imageset` フラグは付けないこと。

5. 検証：
   - 生成された全 PNG が **2MB 以下** か
   - 欠けセル・空セルが無いか（pixel variance が閾値以下なら警告）
6. 2MB 超過セルがあれば `--cell-size` を縮小して再実行、または個別に WebP 化
7. 想定通りでないセルがあれば、該当セルだけ `gen-image` で個別再生成して差し替え

## 個別セルの再生成フロー

```bash
scripts/gen-asset/venv/bin/python scripts/gen-asset/gen_image.py \
  "<キャラ単体の詳細プロンプト>、灰色背景、中央配置" \
  --aspect 1:1 --size 4K --thinking high \
  --out .build/gen-asset/raw/<Name>_v2.png

scripts/gen-asset/venv/bin/python scripts/gen-asset/postprocess.py \
  --in .build/gen-asset/raw/<Name>_v2.png \
  --out outputs/<task_id>/<pack_name>/<Name>.png \
  --target-size 256 --max-bytes 2097152 --trim-watermark bottom-right
```

## 空セルを意図的に確保

`--names` で `_` 始まりのトークンを渡すと出力ファイルを生成しない。透かし回避のため右下 1 セルは空にする運用が安全。

```bash
--names "souther,yuko,...,_empty"
```

## 出力構造

```
outputs/<task_id>/<pack_name>/
  souther.png
  yuko.png
  designer.png
  ...
```

## 関連
- `gen-image`：単発画像生成
