#!/usr/bin/env python3
# >>> Claude Code Init >>>
"""Gemini 3.1 Flash TTS で音声を生成。PCM 24kHz → WAV 出力。"""

import argparse
import base64
import struct
import sys
from pathlib import Path

from _common import get_api_key, resolve_output, ensure_parent, slugify

MODEL = "gemini-3.1-flash-tts-preview"


def parse_args():
    p = argparse.ArgumentParser(description="Gemini 3.1 Flash TTS")
    p.add_argument("text")
    p.add_argument("--out", default=None)
    p.add_argument("--voice", default="Kore")
    p.add_argument("--style", default=None)
    return p.parse_args()


def write_wav(pcm: bytes, out_path: Path, sample_rate: int = 24000) -> None:
    n_channels = 1
    sampwidth = 2
    n_frames = len(pcm) // (sampwidth * n_channels)
    byte_rate = sample_rate * n_channels * sampwidth
    block_align = n_channels * sampwidth
    data_size = n_frames * block_align

    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    fmt = b"fmt " + struct.pack(
        "<IHHIIHH", 16, 1, n_channels, sample_rate, byte_rate, block_align, sampwidth * 8
    )
    data = b"data" + struct.pack("<I", data_size) + pcm

    with open(out_path, "wb") as f:
        f.write(header + fmt + data)


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
    text = f"Say in {args.style}: {args.text}" if args.style else args.text

    sys.stderr.write(f"==> {MODEL} (voice={args.voice})\n")

    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=args.voice)
            )
        ),
    )

    response = client.models.generate_content(model=MODEL, contents=[text], config=config)

    default_name = slugify(args.text) + ".wav"
    out_path = resolve_output(args.out, f"scripts/gen-asset/_out/{default_name}")
    ensure_parent(out_path)

    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data:
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            write_wav(data, out_path)
            print(out_path)
            return

    sys.stderr.write("✗ 音声未返却\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
# <<< Claude Code Init <<<
