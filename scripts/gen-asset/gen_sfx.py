#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""Lyria 3 Clip で効果音（SFX）を生成。

Lyria 3 Clip は常に約 30 秒の MP3 を返すため、
--duration が 30 未満なら ffmpeg で末尾フェード付きトリムを行う。
"""

import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile

from _common import get_api_key, resolve_output, ensure_parent, slugify

MODEL = "lyria-3-clip-preview"
NATIVE_DURATION = 30  # Lyria 3 Clip の固定長（秒）


def parse_args():
    p = argparse.ArgumentParser(description="Lyria 3 Clip で SFX 生成")
    p.add_argument("prompt")
    p.add_argument("--out", default=None)
    p.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help=(
            "秒数。30 未満なら ffmpeg で先頭から切り出し＋50ms フェードアウト。"
            "30 以上なら無加工で出力。"
        ),
    )
    p.add_argument(
        "--no-trim",
        action="store_true",
        help="トリムを無効化（生 30 秒をそのまま保存）",
    )
    return p.parse_args()


def trim_with_ffmpeg(src: str, dst: str, duration: float) -> None:
    """ffmpeg で先頭から duration 秒を切り出し、末尾 50ms にフェードアウト。"""
    fade_dur = min(0.05, duration / 4)
    fade_start = max(0.0, duration - fade_dur)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", src,
        "-t", f"{duration:.3f}",
        "-af", f"afade=out:st={fade_start:.3f}:d={fade_dur:.3f}",
        "-c:a", "libmp3lame", "-b:a", "192k",
        dst,
    ]
    subprocess.run(cmd, check=True)


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
    sys.stderr.write(f"==> {MODEL} (生成 {NATIVE_DURATION}s → 出力 {args.duration}s)\n")

    config = types.GenerateContentConfig(response_modalities=["AUDIO"])
    response = client.models.generate_content(
        model=MODEL, contents=[args.prompt], config=config
    )

    default_name = slugify(args.prompt) + ".mp3"
    out_path = resolve_output(args.out, f"scripts/gen-asset/_out/{default_name}")
    ensure_parent(out_path)

    raw_bytes = None
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data:
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            raw_bytes = data
            break

    if raw_bytes is None:
        sys.stderr.write("✗ SFX 未返却\n")
        sys.exit(1)

    need_trim = (not args.no_trim) and args.duration < NATIVE_DURATION
    if not need_trim:
        with open(out_path, "wb") as f:
            f.write(raw_bytes)
        print(out_path)
        return

    if shutil.which("ffmpeg") is None:
        sys.stderr.write(
            "✗ ffmpeg 未インストール。`brew install ffmpeg` 後に再実行するか、\n"
            "  --no-trim で 30 秒のまま保存してください。\n"
        )
        sys.exit(2)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    try:
        trim_with_ffmpeg(tmp_path, out_path, args.duration)
    finally:
        os.unlink(tmp_path)
    print(out_path)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
