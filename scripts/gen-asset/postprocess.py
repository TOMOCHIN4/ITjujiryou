#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""画像の後処理：透かし除去 → リサイズ → 0.5MB 以下に圧縮。

gen-image / gen-sprites の共通パイプラインで利用される。
"""

import argparse
import json
import sys
from pathlib import Path

from _common import resolve_output, ensure_parent

DEFAULT_MAX_BYTES = 524_288  # 0.5 MB
WATERMARK_CHOICES = ["none", "bottom-right", "bottom-left", "top-right", "top-left"]


def parse_args():
    p = argparse.ArgumentParser(description="画像後処理（透かし除去・リサイズ・圧縮）")
    p.add_argument("--in", dest="src", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--target-size", type=int, default=1024,
                   help="長辺の最終解像度（px）。既定 1024。")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                   help=f"最大ファイルサイズ（bytes）。既定 {DEFAULT_MAX_BYTES}。")
    p.add_argument("--trim-watermark", choices=WATERMARK_CHOICES, default="bottom-right",
                   help="透かしの位置。none で無効化。")
    p.add_argument("--watermark-ratio", type=float, default=0.06,
                   help="透かし矩形の辺長比（画像辺に対する比率）。既定 0.06。")
    p.add_argument("--write-imageset", action="store_true",
                   help="出力先ディレクトリを .imageset として Contents.json も生成。")
    return p.parse_args()


def trim_watermark(img, position: str, ratio: float):
    """透かし部分を内側から少しクロップして除去する。"""
    if position == "none":
        return img
    w, h = img.size
    cw = max(1, int(w * ratio))
    ch = max(1, int(h * ratio))
    if position == "bottom-right":
        return img.crop((0, 0, w - cw, h - ch))
    if position == "bottom-left":
        return img.crop((cw, 0, w, h - ch))
    if position == "top-right":
        return img.crop((0, ch, w - cw, h))
    if position == "top-left":
        return img.crop((cw, ch, w, h))
    return img


def parse_chroma_color(s: str):
    """'00ff00' / '#00ff00' / '0,255,0' を (r,g,b) tuple へ。"""
    if not s:
        return None
    s = s.strip().lstrip("#")
    if "," in s:
        parts = [int(p.strip()) for p in s.split(",")]
        if len(parts) != 3:
            raise ValueError(f"chroma color tuple must be 3 ints: {s!r}")
        return tuple(parts)
    if len(s) == 6:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    raise ValueError(f"chroma color must be HEXHEXHEX or R,G,B: {s!r}")


def find_main_character_bbox(img, target_rgb, tolerance: int = 80, min_area_ratio: float = 0.01):
    """セル内で「target 色から離れた pixel の連結成分」のうち最大ブロブの bbox を返す。

    Gemini が描いたグリッド枠線や隣接セルからの侵入があっても、最大の連結体
    (= 中心の主要キャラクター) だけ抽出して bbox を絞り込める。

    Returns: (left, top, right, bottom) または None (主要ブロブが見つからない場合)
    """
    try:
        import numpy as np
        from scipy.ndimage import label
    except ImportError:
        return None

    rgb = img.convert("RGB")
    arr = np.asarray(rgb)  # (H, W, 3)
    tr, tg, tb = target_rgb
    is_green = (
        (np.abs(arr[:, :, 0].astype(int) - tr) <= tolerance)
        & (np.abs(arr[:, :, 1].astype(int) - tg) <= tolerance)
        & (np.abs(arr[:, :, 2].astype(int) - tb) <= tolerance)
    )
    not_green = ~is_green
    if not not_green.any():
        return None

    labels, n = label(not_green)
    if n == 0:
        return None

    # 各ラベルの pixel 数 (label 0 = 背景)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    main_label = int(sizes.argmax())
    if sizes[main_label] < not_green.size * min_area_ratio:
        return None  # 小さすぎる

    main_mask = labels == main_label
    ys, xs = np.where(main_mask)
    return (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))


def chroma_key_to_alpha(img, target_rgb, tolerance: int = 40):
    """指定 RGB に近い pixel を alpha=0 に置換した RGBA Image を返す (PIL ネイティブ高速版)。

    pixel が target_rgb に近い (各成分 |delta| <= tolerance) なら alpha=0。
    それ以外は alpha=255 (元画像が既に alpha を持つ場合は max を取る)。
    """
    from PIL import Image, ImageChops

    if target_rgb is None:
        return img
    rgba = img.convert("RGBA")
    r, g, b, a = rgba.split()
    tr, tg, tb = target_rgb

    # 各バンドで「target から離れている」を 255、近いを 0 でマスク化
    def _far_band(band, target):
        return band.point(lambda v: 255 if abs(v - target) > tolerance else 0)

    r_far = _far_band(r, tr)
    g_far = _far_band(g, tg)
    b_far = _far_band(b, tb)

    # 「いずれかのバンドが target から離れている」= 不透明
    not_target = ImageChops.lighter(ImageChops.lighter(r_far, g_far), b_far)
    rgba.putalpha(not_target)
    return rgba


def resize_long_edge(img, target: int):
    w, h = img.size
    long_edge = max(w, h)
    if long_edge <= target:
        return img
    scale = target / long_edge
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    from PIL import Image
    return img.resize(new_size, Image.LANCZOS)


def save_under_limit(img, out_path: Path, max_bytes: int) -> int:
    """0.5MB 以下に収まるよう段階的に圧縮して保存。最終ファイルサイズを返す。"""
    from PIL import Image

    ensure_parent(out_path)
    base = img.convert("RGBA") if img.mode != "RGBA" else img

    base.save(out_path, format="PNG", optimize=True)
    if out_path.stat().st_size <= max_bytes:
        return out_path.stat().st_size

    palette = base.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    palette.save(out_path, format="PNG", optimize=True)
    if out_path.stat().st_size <= max_bytes:
        return out_path.stat().st_size

    current = base
    for _ in range(8):
        w, h = current.size
        new_size = (max(64, int(w * 0.85)), max(64, int(h * 0.85)))
        current = current.resize(new_size, Image.LANCZOS)
        pal = current.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        pal.save(out_path, format="PNG", optimize=True)
        if out_path.stat().st_size <= max_bytes:
            return out_path.stat().st_size

    return out_path.stat().st_size


def write_imageset_metadata(image_path: Path):
    """imageset 用の Contents.json を image_path と同じディレクトリに生成。"""
    contents = {
        "images": [
            {"idiom": "universal", "filename": image_path.name, "scale": "1x"},
            {"idiom": "universal", "scale": "2x"},
            {"idiom": "universal", "scale": "3x"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    (image_path.parent / "Contents.json").write_text(
        json.dumps(contents, indent=2), encoding="utf-8"
    )


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

    out = Path(args.out)
    if not out.is_absolute():
        out = resolve_output(args.out, args.out)

    img = Image.open(src)
    sys.stderr.write(f"==> in: {src} ({img.size[0]}x{img.size[1]})\n")

    img = trim_watermark(img, args.trim_watermark, args.watermark_ratio)
    sys.stderr.write(f"==> trim({args.trim_watermark}, ratio={args.watermark_ratio}) -> {img.size[0]}x{img.size[1]}\n")

    img = resize_long_edge(img, args.target_size)
    sys.stderr.write(f"==> resize(<= {args.target_size}px) -> {img.size[0]}x{img.size[1]}\n")

    final_bytes = save_under_limit(img, out, args.max_bytes)
    if final_bytes > args.max_bytes:
        sys.stderr.write(
            f"✗ {final_bytes} bytes > {args.max_bytes}。--target-size を下げるか WebP 化を検討。\n"
        )
        sys.exit(1)

    sys.stderr.write(f"==> out: {out} ({final_bytes} bytes)\n")

    if args.write_imageset:
        write_imageset_metadata(out)
        sys.stderr.write(f"==> imageset Contents.json 生成済み\n")

    print(out)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
