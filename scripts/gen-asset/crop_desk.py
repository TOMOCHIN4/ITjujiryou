#!/usr/bin/env python3
"""rembg 透過済み cell PNG から、bbox + target アスペクトで center crop → resize。

asset-maker が出力する 1:1 cell PNG (中央に横長/凹型デスクが描かれている) を、
scene.js で stretch せずに済むように、target アスペクト (3:1, 3:2, 2:1 等) の
最小外接矩形で crop してから target サイズへリサイズする。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_aspect(s: str) -> tuple[int, int]:
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"--aspect must be 'W:H' (e.g. 3:1), got {s!r}")
    return int(parts[0]), int(parts[1])


def main() -> int:
    p = argparse.ArgumentParser(description="bbox + target-aspect crop + resize")
    p.add_argument("--in", dest="src", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--aspect", required=True, help="target aspect 'W:H' (e.g. 3:1)")
    p.add_argument("--target-w", type=int, required=True, help="final width in px")
    p.add_argument("--padding", type=float, default=0.04,
                   help="extra padding ratio around bbox (default 4%)")
    args = p.parse_args()

    try:
        from PIL import Image
    except ImportError:
        sys.stderr.write("Pillow not installed\n")
        return 2

    aw, ah = parse_aspect(args.aspect)
    target_w = args.target_w
    target_h = round(target_w * ah / aw)

    im = Image.open(args.src).convert("RGBA")
    W, H = im.size

    # bbox = alpha != 0 の最小外接矩形
    bbox = im.getbbox()
    if bbox is None:
        sys.stderr.write(f"empty (fully transparent): {args.src}\n")
        return 1
    bx0, by0, bx1, by1 = bbox

    # padding を bbox に追加
    pad_x = int((bx1 - bx0) * args.padding)
    pad_y = int((by1 - by0) * args.padding)
    bx0 = max(0, bx0 - pad_x)
    by0 = max(0, by0 - pad_y)
    bx1 = min(W, bx1 + pad_x)
    by1 = min(H, by1 + pad_y)
    bw = bx1 - bx0
    bh = by1 - by0
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2

    # bbox を内包する最小の target aspect 矩形を計算 (中心固定で短辺を伸ばす)
    target_ratio = aw / ah
    bbox_ratio = bw / bh if bh > 0 else target_ratio
    if bbox_ratio > target_ratio:
        # bbox が target より横長 → 高さを伸ばす
        new_w = bw
        new_h = bw / target_ratio
    else:
        # bbox が target より縦長 → 幅を伸ばす
        new_h = bh
        new_w = bh * target_ratio

    # crop 範囲 (画像端を超えないようクランプ)
    cx0 = max(0, int(cx - new_w / 2))
    cy0 = max(0, int(cy - new_h / 2))
    cx1 = min(W, int(cx + new_w / 2))
    cy1 = min(H, int(cy + new_h / 2))

    cropped = im.crop((cx0, cy0, cx1, cy1))
    sys.stderr.write(f"==> in: {args.src} ({W}x{H}), bbox=({bx0},{by0},{bx1},{by1})\n")
    sys.stderr.write(f"==> crop=({cx0},{cy0},{cx1},{cy1}) -> {cropped.size[0]}x{cropped.size[1]} aspect~{cropped.size[0]/cropped.size[1]:.2f}\n")

    resized = cropped.resize((target_w, target_h), Image.LANCZOS)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    resized.save(args.out, format="PNG", optimize=True)
    sys.stderr.write(f"==> out: {args.out} ({target_w}x{target_h}, {args.out.stat().st_size} bytes)\n")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
