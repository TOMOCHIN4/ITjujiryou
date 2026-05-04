#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""Lyria 3 Pro で BGM（最大3分）を生成。"""

import argparse
import base64
import sys

from _common import get_api_key, resolve_output, ensure_parent, slugify

MODEL = "lyria-3-pro-preview"


def parse_args():
    p = argparse.ArgumentParser(description="Lyria 3 Pro で楽曲生成")
    p.add_argument("prompt")
    p.add_argument("--out", default=None)
    p.add_argument("--duration", type=int, default=60, help="秒数（最大180）")
    return p.parse_args()


def main():
    args = parse_args()
    api_key = get_api_key()

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.stderr.write("✗ google-genai 未インストール\n")
        sys.exit(2)

    client = genai.Client(api_key=api_key)
    sys.stderr.write(f"==> {MODEL} ({args.duration}s)\n")

    config = types.GenerateContentConfig(response_modalities=["AUDIO"])
    response = client.models.generate_content(
        model=MODEL, contents=[args.prompt], config=config
    )

    default_name = slugify(args.prompt) + ".mp3"
    out_path = resolve_output(args.out, f"scripts/gen-asset/_out/{default_name}")
    ensure_parent(out_path)

    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data:
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            with open(out_path, "wb") as f:
                f.write(data)
            print(out_path)
            return

    sys.stderr.write("✗ 音楽未返却\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
