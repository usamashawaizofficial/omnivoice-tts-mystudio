"""Background workers: generation, voice test, and model download.

Everything long-running executes in a QThread so the UI never blocks.
Progress is reported through Qt signals (thread-safe by design).
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .. import pipeline
from ..config import MODEL_BASE_URL, MODELS_DIR, REQUIRED_MODELS
from ..voices import Voice


class GenerationCancelled(Exception):
    """Raised inside the progress callback to abort a running generation."""


class GenerateWorker(QThread):
    """Runs pipeline.generate_voiceover off the UI thread."""

    progress = Signal(int, int, str)   # done, total, stage label
    finished = Signal(str)            # final file path (str)
    error = Signal(str)               # human-readable error
    cancelled = Signal()

    def __init__(
        self,
        text: str,
        output_name: str,
        voice: Voice | None = None,
        voice_description: str | None = None,
        output_format: str = "mp3",
        parent=None,
    ):
        super().__init__(parent)
        self._text = text
        self._output_name = output_name
        self._voice = voice
        self._voice_description = voice_description
        self._output_format = output_format
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _on_progress(self, done: int, total: int, stage: str) -> None:
        if self._cancel_requested:
            raise GenerationCancelled()
        self.progress.emit(done, total, stage)

    def run(self) -> None:  # noqa: D102 - QThread API
        try:
            result = pipeline.generate_voiceover(
                self._text,
                self._output_name,
                voice=self._voice,
                voice_description=self._voice_description,
                output_format=self._output_format,
                on_progress=self._on_progress,
            )
        except GenerationCancelled:
            self.cancelled.emit()
        except Exception as exc:  # surface as message, never crash
            self.error.emit(str(exc))
        else:
            self.finished.emit(str(result))


class TestVoiceWorker(GenerateWorker):
    """Short fixed-sample synthesis to preview a saved/cloned voice."""

    SAMPLE_TEXT = (
        "Hello! This is a short preview of the cloned voice, "
        "so you can check the quality before generating a full voiceover."
    )

    def __init__(self, voice: Voice, output_name: str = "_voice_preview", parent=None):
        super().__init__(
            self.SAMPLE_TEXT,
            output_name,
            voice=voice,
            output_format="wav",  # skip MP3 encode for a fast preview
            parent=parent,
        )


class DownloadWorker(QThread):
    """First-run model download with progress. Network use is limited to this."""

    progress = Signal(str, int, int)  # filename, bytes_done, bytes_total
    finished = Signal()
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _download_one(self, filename: str) -> None:
        url = f"{MODEL_BASE_URL}/{filename}"
        dest = MODELS_DIR / filename
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "tts-studio/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    if self._cancel_requested:
                        raise GenerationCancelled()
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    self.progress.emit(filename, done, total)
        tmp.replace(dest)

    def run(self) -> None:  # noqa: D102 - QThread API
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            for name in REQUIRED_MODELS:
                if (MODELS_DIR / name).exists():
                    continue
                self._download_one(name)
        except GenerationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(f"Download failed: {exc}")
        else:
            self.finished.emit()
