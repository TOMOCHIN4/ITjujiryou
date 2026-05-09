#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""4K グリッド画像をセル分割して Asset Catalog に配置する。

パイプライン：
  入力 1 枚 → 透かし除去 → NxM 等分割 → 各セルをリサイズ＆圧縮（≤0.5MB）
            → <pack>/<Name>.imageset/<Name>.png + Contents.json
"""

import argparse
import json
import sys
from pathlib import Path

from _common import resolve_output, ensure_parent
from postprocess import (
    DEFAULT_MAX_BYTES,
    WATERMARK_CHOICES,
    trim_watermark,
    resize_long_edge,
    save_under_limit,
    write_imageset_metadata,
    chroma_key_to_alpha,
    parse_chroma_color,
    find_main_character_bbox,
    detect_blobs_whole_image,
)


def parse_grid(s: str):
    try:
        cols, rows = s.lower().split("x")
        return int(cols), int(rows)
    except Exception:
        raise argparse.ArgumentTypeError(f"--grid は 'CxR' 形式（例 5x5）。受領: {s}")


def parse_args():
    p = argparse.ArgumentParser(description="グリッド画像の分割と Asset Catalog 生成")
    p.add_argument("--in", dest="src", required=True)
    p.add_argument("--grid", required=True, type=parse_grid,
                   help="グリッド (CxR)。例 5x5")
    p.add_argument("--names", default="",
                   help="セル名のカンマ区切り（左上から右下へ走査）。空セルは空文字で。")
    p.add_argument("--trim-watermark", choices=WATERMARK_CHOICES, default="bottom-right")
    p.add_argument("--watermark-ratio", type=float, default=0.06)
    p.add_argument("--cell-size", type=int, default=256,
                   help="各セルの最終長辺解像度。既定 256。")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    p.add_argument("--out", required=True,
                   help="Asset Catalog 内のパックディレクトリ。例 .../Assets.xcassets/Heroes/")
    p.add_argument("--cell-margin", type=float, default=0.0,
                   help="セルの内側マージン比率（枠線除去用）。既定 0。")
    p.add_argument("--chroma-key", default=None,
                   help="クロマキーする色 (例: '00ff00' / '#00FF00' / '0,255,0')。"
                        "セル分割後・リサイズ前に適用し、target に近い pixel を alpha=0 化。"
                        "未指定なら適用しない (後方互換)。")
    p.add_argument("--chroma-tolerance", type=int, default=40,
                   help="クロマキーの許容差 (RGB 各成分)。既定 40。")
    p.add_argument("--smart-crop", action="store_true",
                   help="セル内で chroma-key 色から離れた最大連結成分を見つけて、その bbox + パディングで"
                        "再クロップする。Gemini のグリッド枠線や隣接セル侵入を排除できる。"
                        "--chroma-key と併用前提。")
    p.add_argument("--smart-crop-padding", type=int, default=8,
                   help="--smart-crop bbox の四辺に追加する余白 px (resize 前)。既定 8。")
    p.add_argument("--auto-detect", action="store_true",
                   help="grid 等分割を無視し、画像全体の chroma-key 後 blob を自動検出して "
                        "上位 (cols×rows) 個を bbox 抽出する。Gemini が grid を不均等に描いたり "
                        "1 セルに 2 体並べたりした場合に有効。--chroma-key 必須。")
    p.add_argument("--auto-detect-min-area", type=float, default=0.001,
                   help="--auto-detect で blob の最小面積比 (画像全体に対する)。既定 0.001。")
    return p.parse_args()


def split_cells(img, cols: int, rows: int, margin: float):
    w, h = img.size
    cell_w = w // cols
    cell_h = h // rows
    mx = int(cell_w * margin)
    my = int(cell_h * margin)
    cells = []
    for r in range(rows):
        for c in range(cols):
            left = c * cell_w + mx
            top = r * cell_h + my
            right = (c + 1) * cell_w - mx
            bottom = (r + 1) * cell_h - my
            cells.append(img.crop((left, top, right, bottom)))
    return cells


def main():
    args = parse_args()
    try:
        from PIL import Image
    except ImportError:
        sys.stderr.write("✗ Pillow 未インストール。setup.sh を実行。\n")
        sys.exit(2)

    src = Path(args.src)
    if not src.is_absolute():
        src = resolve_output(args.src, args.src)
    if not src.exists():
        sys.stderr.write(f"✗ 入力が存在しない: {src}\n")
        sys.exit(1)

    pack_dir = Path(args.out)
    if not pack_dir.is_absolute():
        pack_dir = resolve_output(args.out, args.out)
    pack_dir.mkdir(parents=True, exist_ok=True)

    cols, rows = args.grid
    total = cols * rows
    names_raw = [n.strip() for n in args.names.split(",")] if args.names else []
    if names_raw and len(names_raw) != total:
        sys.stderr.write(
            f"△ --names の数 ({len(names_raw)}) が grid ({total}) と不一致。"
            f"不足分は cell_<idx> で補完。\n"
        )
    names = [
        (names_raw[i] if i < len(names_raw) and names_raw[i] else f"cell_{i:02d}")
        for i in range(total)
    ]

    img = Image.open(src)
    sys.stderr.write(f"==> in: {src} ({img.size[0]}x{img.size[1]})\n")

    img = trim_watermark(img, args.trim_watermark, args.watermark_ratio)
    sys.stderr.write(f"==> trim -> {img.size[0]}x{img.size[1]}\n")

    # クロマキー設定 (任意)
    chroma_rgb = parse_chroma_color(args.chroma_key) if args.chroma_key else None
    if chroma_rgb is not None:
        sys.stderr.write(
            f"==> chroma-key {chroma_rgb} (tolerance {args.chroma_tolerance}) — alpha 抽出有効\n"
        )

    if args.auto_detect:
        if chroma_rgb is None:
            sys.stderr.write("✗ --auto-detect は --chroma-key が必須\n")
            sys.exit(1)
        bboxes = detect_blobs_whole_image(
            img, chroma_rgb, args.chroma_tolerance,
            min_area_ratio=args.auto_detect_min_area,
            max_blobs=total,
        )
        sys.stderr.write(
            f"==> auto-detect: found {len(bboxes)} blobs (expected {total})\n"
        )
        cells = []
        pad = args.smart_crop_padding
        for (l, t, r, b) in bboxes:
            l = max(0, l - pad)
            t = max(0, t - pad)
            r = min(img.size[0], r + pad)
            b = min(img.size[1], b + pad)
            cells.append(img.crop((l, t, r, b)))
        # 不足分は緑空セルで埋める (名前との一致を保つため)
        while len(cells) < total:
            cells.append(Image.new("RGB", (img.size[0] // cols, img.size[1] // rows),
                                    color=chroma_rgb))
    else:
        cells = split_cells(img, cols, rows, args.cell_margin)
        sys.stderr.write(f"==> split {cols}x{rows} = {len(cells)} cells\n")

    pack_contents = {"info": {"author": "xcode", "version": 1}, "properties": {"provides-namespace": True}}
    (pack_dir / "Contents.json").write_text(json.dumps(pack_contents, indent=2), encoding="utf-8")

    failed = []
    saved = []
    for i, (cell, name) in enumerate(zip(cells, names)):
        if not name or name.startswith("_"):
            continue
        imageset_dir = pack_dir / f"{name}.imageset"
        imageset_dir.mkdir(parents=True, exist_ok=True)
        out_path = imageset_dir / f"{name}.png"

        # smart-crop: 最大連結成分の bbox に絞り込む (Gemini のグリッド/隣接侵入対策)
        if args.smart_crop and chroma_rgb is not None:
            bbox = find_main_character_bbox(cell, chroma_rgb, args.chroma_tolerance)
            if bbox is not None:
                pad = args.smart_crop_padding
                w, h = cell.size
                left = max(0, bbox[0] - pad)
                top = max(0, bbox[1] - pad)
                right = min(w, bbox[2] + pad)
                bottom = min(h, bbox[3] + pad)
                cell = cell.crop((left, top, right, bottom))

        # chroma-key は smart-crop 後 / resize 前に適用 (端の anti-alias を保つ)
        cell_alpha = (
            chroma_key_to_alpha(cell, chroma_rgb, args.chroma_tolerance)
            if chroma_rgb is not None
            else cell
        )
        cell_resized = resize_long_edge(cell_alpha, args.cell_size)
        size_bytes = save_under_limit(cell_resized, out_path, args.max_bytes)
        write_imageset_metadata(out_path)

        if size_bytes > args.max_bytes:
            failed.append((name, size_bytes))
            sys.stderr.write(f"  [{i:02d}] {name}: {size_bytes}B  超過\n")
        else:
            saved.append((name, size_bytes))
            sys.stderr.write(f"  [{i:02d}] {name}: {size_bytes}B\n")

    sys.stderr.write(f"==> saved={len(saved)} failed={len(failed)} total={total}\n")
    if failed:
        sys.stderr.write(
            "✗ 0.5MB 超のセルあり。--cell-size を下げるか WebP 化を検討。\n"
        )
        sys.exit(1)

    print(pack_dir)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
