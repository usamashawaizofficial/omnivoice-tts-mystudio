"""Voice library: saved reference voices for cloning.

Each voice = reference WAV + its transcript (+ optional label/language).
Stored under the app-data voices dir as:
    voices/<voice_id>/reference.wav
    voices/<voice_id>/meta.json
"""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import VOICES_DIR


@dataclass
class Voice:
    voice_id: str
    name: str
    language: str
    reference_wav: str   # path
    transcript: str
    created: str = ""


def _voice_dir(voice_id: str) -> Path:
    return VOICES_DIR / voice_id


def save_voice(name: str, language: str, reference_wav: Path,
               transcript: str) -> Voice:
    voice_id = uuid.uuid4().hex[:12]
    vdir = _voice_dir(voice_id)
    vdir.mkdir(parents=True, exist_ok=True)
    dest = vdir / "reference.wav"
    shutil.copy2(reference_wav, dest)
    import datetime
    voice = Voice(
        voice_id=voice_id,
        name=name,
        language=language,
        reference_wav=str(dest),
        transcript=transcript,
        created=datetime.datetime.now().isoformat(timespec="seconds"),
    )
    (vdir / "meta.json").write_text(json.dumps(asdict(voice), ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    return voice


def list_voices() -> list[Voice]:
    voices: list[Voice] = []
    if not VOICES_DIR.exists():
        return voices
    for vdir in sorted(VOICES_DIR.iterdir()):
        meta = vdir / "meta.json"
        if meta.exists():
            d = json.loads(meta.read_text(encoding="utf-8"))
            voices.append(Voice(**d))
    return voices


def get_voice(voice_id: str) -> Voice | None:
    meta = _voice_dir(voice_id) / "meta.json"
    if not meta.exists():
        return None
    return Voice(**json.loads(meta.read_text(encoding="utf-8")))


def delete_voice(voice_id: str) -> bool:
    vdir = _voice_dir(voice_id)
    if not vdir.exists():
        return False
    shutil.rmtree(vdir)
    return True
