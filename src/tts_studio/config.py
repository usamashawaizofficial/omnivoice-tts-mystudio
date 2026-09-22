"""Central configuration: paths, model catalogue, defaults.

All filesystem locations resolve under a single app-data root so the
packaged app and the dev checkout behave identically.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _app_data_root() -> Path:
    # Packaged (PyInstaller) builds keep writable data next to the exe's
    # parent; dev checkouts use ~/.local/share.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return Path(os.path.expanduser("~")) / ".local" / "share" / "tts-studio"


APP_DATA = _app_data_root()
MODELS_DIR = APP_DATA / "models"
VOICES_DIR = APP_DATA / "voices"
OUTPUT_DIR = APP_DATA / "output"
CACHE_DIR = APP_DATA / "cache"

for _d in (MODELS_DIR, VOICES_DIR, OUTPUT_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Model catalogue: (repo, filename) pairs for first-run download.
MODEL_BASE_URL = "https://huggingface.co/Serveurperso/OmniVoice-GGUF/resolve/main"
# Recommended ship set (verified 2026-09-22). User chose Q8_0 base on
# 2026-09-22 after A/B listening: best quality, ~900 MB total download.
MODEL_BASE = "omnivoice-base-Q8_0.gguf"
MODEL_CODEC = "omnivoice-tokenizer-Q8_0.gguf"
REQUIRED_MODELS = [MODEL_BASE, MODEL_CODEC]

# Synthesis defaults tuned for CPU-only machines.
DEFAULTS = {
    "sample_rate": 24000,
    "threads": max(1, (os.cpu_count() or 4) - 1),
    "chunk_max_chars": 600,      # punctuation-aware chunk target
    "crossfade_ms": 120,         # crossfade between chunks
    "output_format": "mp3",
    "mp3_bitrate": "192k",
}
