"""Engine adapter: drives the bundled omnivoice.cpp CPU binary.

This is the ONLY module that knows the engine's CLI. Everything else
(UI, pipeline) talks to the `Engine` class, so swapping the engine
later (e.g. an Apache-2.0 licensed one) means rewriting this file only.

Exact CLI flags are filled in after engine verification completes.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import MODELS_DIR, DEFAULTS


@dataclass
class SynthRequest:
    text: str
    out_wav: Path
    language: str = "English"
    # Voice cloning: pre-encoded reference (rvq) + its transcript file.
    # Use `encode_reference()` to build these once per voice; omit both
    # for the default voice / voice-design path.
    ref_rvq: Path | None = None
    ref_text_file: Path | None = None
    # Voice design: validated against the engine's fixed allow-list, e.g.
    # "female, young adult".
    voice_description: str | None = None
    threads: int = DEFAULTS["threads"]


class EngineError(RuntimeError):
    pass


def _bin_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "bin"
    # Dev: engine checkout lives next to this project (see README).
    return Path(__file__).resolve().parents[2] / "engine-bin"


def find_tts_binary() -> Path:
    name = "omnivoice-tts" + (".exe" if sys.platform == "win32" else "")
    cand = _bin_dir() / name
    if cand.exists():
        return cand
    found = next((_bin_dir().rglob(name)), None)
    if found:
        return found
    raise EngineError(
        f"TTS engine binary not found under {_bin_dir()}. "
        "Run the first-time setup to download it."
    )


def find_codec_binary() -> Path:
    name = "omnivoice-codec" + (".exe" if sys.platform == "win32" else "")
    cand = _bin_dir() / name
    if cand.exists():
        return cand
    found = next((_bin_dir().rglob(name)), None)
    if found:
        return found
    raise EngineError(
        f"Codec binary not found under {_bin_dir()}. "
        "Run the first-time setup to download it."
    )


def encode_reference(ref_wav: Path, cache_dir: Path) -> tuple[Path, Path]:
    """Pre-encode a cloning reference once: WAV -> .rvq + transcript file.
    Returns (rvq_path, text_path); cached so repeat jobs skip re-encoding."""
    from .config import MODEL_CODEC
    cache_dir.mkdir(parents=True, exist_ok=True)
    rvq = cache_dir / (ref_wav.stem + ".rvq")
    if not rvq.exists():
        cmd = [str(find_codec_binary()),
               "--model", str(MODELS_DIR / MODEL_CODEC),
               "-i", str(ref_wav)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise EngineError(f"Reference encoding failed: {e.stderr[-2000:]}") from e
        produced = next(cache_dir.glob("*.rvq"), None)
        if produced is None or not rvq.exists():
            # codec writes beside input or cwd; locate and move it
            raise EngineError("Codec finished but produced no .rvq file.")
    return rvq, cache_dir / (ref_wav.stem + ".txt")


def models_present() -> bool:
    from .config import REQUIRED_MODELS
    return all((MODELS_DIR / m).exists() for m in REQUIRED_MODELS)


class Engine:
    """Thin wrapper over the omnivoice.cpp CLI (subprocess)."""

    def __init__(self, tts_bin: Path | None = None):
        self.tts_bin = tts_bin or find_tts_binary()
        if not models_present():
            raise EngineError(
                f"Model files missing in {MODELS_DIR}. "
                "Run first-time setup to download them."
            )

    # --- exact CLI invocation; verified against the built binary (2026-09-22) ---
    def _build_command(self, req: SynthRequest) -> list[str]:
        from .config import MODEL_BASE, MODEL_CODEC
        cmd = [
            str(self.tts_bin),
            "--model", str(MODELS_DIR / MODEL_BASE),
            "--codec", str(MODELS_DIR / MODEL_CODEC),
            "--lang", req.language,
            "--steps", "16",
            "-o", str(req.out_wav),
        ]
        if req.ref_rvq and req.ref_text_file:
            cmd += ["--ref-rvq", str(req.ref_rvq),
                    "--ref-text", str(req.ref_text_file)]
        if req.voice_description:
            cmd += ["--instruct", req.voice_description]
        return cmd

    def synthesize(self, req: SynthRequest) -> Path:
        req.out_wav.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_command(req)
        import os
        env = dict(os.environ)
        if sys.platform != "win32":
            # Dev/Linux: engine ships shared libs next to the binary.
            # (On Windows the DLLs sit beside the EXE and resolve automatically.)
            bindir = str(Path(self.tts_bin).resolve().parent)
            env["LD_LIBRARY_PATH"] = bindir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        try:
            # Text goes via stdin (avoids quoting issues, esp. Urdu script).
            subprocess.run(cmd, input=req.text, check=True,
                           capture_output=True, text=True, env=env)
        except subprocess.CalledProcessError as e:
            raise EngineError(f"Engine failed: {e.stderr[-2000:]}") from e
        if not req.out_wav.exists():
            raise EngineError("Engine finished but produced no audio file.")
        return req.out_wav
