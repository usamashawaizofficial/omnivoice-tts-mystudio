"""Punctuation-aware text chunking for long-form synthesis.

Long scripts are split at sentence/paragraph boundaries so each chunk
is short enough for the engine, then re-joined with crossfades.
Splitting on punctuation (never mid-word) keeps prosody natural.
"""
from __future__ import annotations

import re

# Strong boundaries first, weak ones last.
_BOUNDARY_RE = re.compile(
    r"(?<=[.!?…؟。！])\s+|"      # sentence enders (incl. Urdu/Arabic/CJK)
    r"\n{2,}|"                   # paragraph breaks
    r"(?<=[,،؛:;—–])\s+",        # clause breaks as fallback
)


def split_text(text: str, max_chars: int = 600) -> list[str]:
    """Split *text* into chunks of at most *max_chars*, preferring
    sentence boundaries. Never splits inside a word."""
    text = re.sub(r"[ \t]+", " ", text.strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    pieces = [p for p in _BOUNDARY_RE.split(text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current).strip())
            current, current_len = [], 0

    for piece in pieces:
        # A single over-long piece gets hard-split at word boundaries.
        while len(piece) > max_chars:
            cut = piece.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            chunks.append(piece[:cut].strip())
            piece = piece[cut:].strip()
        if current_len + len(piece) + 1 > max_chars:
            flush()
        current.append(piece)
        current_len += len(piece) + 1
    flush()
    return [c for c in chunks if c]


def estimate_chunks(text: str, max_chars: int = 600) -> int:
    return len(split_text(text, max_chars))
