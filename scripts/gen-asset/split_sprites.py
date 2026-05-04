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

        cell_resized = resize_long_edge(cell, args.cell_size)
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
