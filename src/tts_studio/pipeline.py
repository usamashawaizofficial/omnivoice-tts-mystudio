"""Generation pipeline: long script -> single finished audio file.

Steps: chunk text -> synthesize each chunk with the same voice ->
join with crossfades -> export MP3. Reports progress via callback so
the UI can show a live progress bar.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from . import audio, chunker
from .config import DEFAULTS, OUTPUT_DIR
from .engine import Engine, SynthRequest
from .voices import Voice

ProgressCb = Callable[[int, int, str], None]  # (done, total, stage)


def generate_voiceover(
    text: str,
    output_name: str,
    voice: Voice | None = None,
    voice_description: str | None = None,
    language: str = "English",
    output_format: str = DEFAULTS["output_format"],
    on_progress: ProgressCb | None = None,
) -> Path:
    """Generate a full voiceover. Returns the final audio file path."""
    from .engine import encode_reference
    from .config import CACHE_DIR

    chunks = chunker.split_text(text, DEFAULTS["chunk_max_chars"])
    if not chunks:
        raise ValueError("No text to synthesize.")

    engine = Engine()

    # Cloning: pre-encode the reference once, reuse for every chunk.
    ref_rvq = ref_txt = None
    if voice:
        vdir = Path(voice.reference_wav).parent
        ref_txt = vdir / "reference.txt"
        if not ref_txt.exists():
            ref_txt.write_text(voice.transcript, encoding="utf-8")
        ref_rvq, ref_txt = encode_reference(Path(voice.reference_wav), vdir)

    total_steps = len(chunks) + 2  # chunks + join + export

    def prog(done: int, stage: str) -> None:
        if on_progress:
            on_progress(done, total_steps, stage)

    wav_parts: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="tts_studio_") as tmp:
        tmpdir = Path(tmp)
        for i, chunk in enumerate(chunks):
            part = tmpdir / f"part_{i:04d}.wav"
            req = SynthRequest(
                text=chunk,
                out_wav=part,
                language=voice.language if voice else language,
                ref_rvq=ref_rvq,
                ref_text_file=ref_txt,
                voice_description=voice_description,
            )
            engine.synthesize(req)
            wav_parts.append(part)
            prog(i + 1, f"chunk {i + 1}/{len(chunks)}")

        prog(len(chunks), "joining audio")
        samples: list[list[float]] = []
        sr = DEFAULTS["sample_rate"]
        for p in wav_parts:
            s, file_sr = audio.read_wav_mono(p)
            sr = file_sr
            samples.append(s)
        mixed = audio.join_with_crossfade(samples, sr, DEFAULTS["crossfade_ms"])

        final_wav = OUTPUT_DIR / f"{output_name}.wav"
        audio.write_wav_mono(final_wav, mixed, sr)

        prog(len(chunks) + 1, "exporting")
        if output_format == "mp3":
            final = audio.export_mp3(final_wav, OUTPUT_DIR / f"{output_name}.mp3",
                                     DEFAULTS["mp3_bitrate"])
            if final != final_wav:
                final_wav.unlink(missing_ok=True)
        else:
            final = final_wav
        prog(total_steps, "done")
        return final
