#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""Gemini Nano Banana 2 (gemini-3.1-flash-image-preview) で画像を生成。"""

import argparse
import base64
import sys
from pathlib import Path

from _common import get_api_key, resolve_output, ensure_parent, slugify

MODEL = "gemini-3.1-flash-image-preview"
ASPECT_CHOICES = [
    "1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
]
SIZE_CHOICES = ["0.5K", "1K", "2K", "4K"]
THINKING_CHOICES = ["off", "low", "medium", "high"]


def parse_args():
    p = argparse.ArgumentParser(description="Gemini Nano Banana 2 画像生成")
    p.add_argument("prompt")
    p.add_argument("--out", default=None)
    p.add_argument("--aspect", choices=ASPECT_CHOICES, default="1:1")
    p.add_argument("--size", choices=SIZE_CHOICES, default="4K")
    p.add_argument("--thinking", choices=THINKING_CHOICES, default="high")
    p.add_argument("--reference", action="append", default=[])
    p.add_argument("--grounding", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    api_key = get_api_key()

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.stderr.write("✗ google-genai 未インストール。setup.sh を実行。\n")
        sys.exit(2)

    client = genai.Client(api_key=api_key)
    contents = [args.prompt]

    if args.reference:
        from PIL import Image
        for ref in args.reference[:14]:
            contents.append(Image.open(ref))

    image_config = types.ImageConfig(aspect_ratio=args.aspect, image_size=args.size)
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=image_config,
    )

    if args.thinking != "off":
        try:
            config.thinking_config = types.ThinkingConfig(thinking_level=args.thinking.upper())
        except Exception:
            pass

    if args.grounding:
        try:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]
        except Exception:
            sys.stderr.write("△ grounding 設定失敗\n")

    sys.stderr.write(
        f"==> {MODEL} ({args.aspect}, {args.size}, thinking={args.thinking})\n"
    )

    response = client.models.generate_content(model=MODEL, contents=contents, config=config)

    default_name = slugify(args.prompt) + ".png"
    out_path = resolve_output(args.out, f"scripts/gen-asset/_out/{default_name}")
    ensure_parent(out_path)

    saved = 0
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data:
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            with open(out_path, "wb") as f:
                f.write(data)
            saved += 1
            break
        elif getattr(part, "text", None):
            sys.stderr.write(f"[model] {part.text}\n")

    if saved == 0:
        sys.stderr.write("✗ 画像未返却\n")
        sys.exit(1)

    print(out_path)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
