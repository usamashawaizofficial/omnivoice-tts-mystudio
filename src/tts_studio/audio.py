"""Audio post-processing: WAV join with crossfade, MP3 export.

Pure-Python + stdlib only (wave/struct) for the join path so the core
pipeline has zero heavy dependencies. MP3 export shells out to the
bundled ffmpeg binary when available, else keeps WAV.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import wave
from pathlib import Path


def read_wav_mono(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as w:
        n = w.getnframes()
        ch = w.getnchannels()
        sr = w.getframerate()
        raw = w.readframes(n)
    fmt = "<" + "h" * (n * ch)
    samples = struct.unpack(fmt, raw)
    mono = [sum(samples[i * ch:(i + 1) * ch]) / (ch * 32768.0) for i in range(n)]
    return mono, sr


def write_wav_mono(path: Path, samples: list[float], sample_rate: int) -> None:
    clipped = [max(-1.0, min(1.0, s)) for s in samples]
    raw = struct.pack("<" + "h" * len(clipped), *[int(s * 32767) for s in clipped])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(raw)


def join_with_crossfade(
    chunks: list[list[float]],
    sample_rate: int,
    crossfade_ms: int = 120,
) -> list[float]:
    """Concatenate chunk sample-lists with equal-power crossfades."""
    if not chunks:
        return []
    xf = int(sample_rate * crossfade_ms / 1000)
    out = list(chunks[0])
    for nxt in chunks[1:]:
        k = min(xf, len(out), len(nxt))
        if k <= 0:
            out.extend(nxt)
            continue
        import math

        for i in range(k):
            t = i / k
            g_out = math.cos(t * math.pi / 2)
            g_in = math.sin(t * math.pi / 2)
            out[len(out) - k + i] = out[len(out) - k + i] * g_out + nxt[i] * g_in
        out.extend(nxt[k:])
    return out


def export_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "192k",
               ffmpeg: str | None = None) -> Path:
    """Convert WAV to MP3. Returns mp3_path on success, wav_path if no
    ffmpeg is available (caller decides how to report it)."""
    ff = ffmpeg or shutil.which("ffmpeg")
    if not ff:
        return wav_path
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ff, "-y", "-loglevel", "error", "-i", str(wav_path),
         "-b:a", bitrate, str(mp3_path)],
        check=True,
    )
    return mp3_path
