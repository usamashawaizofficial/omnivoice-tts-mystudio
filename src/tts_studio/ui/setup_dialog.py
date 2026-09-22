"""First-run setup dialog: downloads model files with progress.

Shown modally at startup when engine.models_present() is False.
The rest of the app only opens after models are ready (or the user
explicitly quits).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import engine
from ..config import REQUIRED_MODELS
from .worker import DownloadWorker


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First-Time Setup — OmniVoice TTS Studio")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Welcome! The voice engine needs to download its model files once "
            f"({len(REQUIRED_MODELS)} files). After this, the app works "
            "100% offline — no internet needed ever again."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._status = QLabel("Ready to download.")
        self._status.setObjectName("dim")
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        layout.addWidget(self._bar)

        row = QHBoxLayout()
        row.addStretch(1)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._start_btn = QPushButton("Download Models")
        self._start_btn.setDefault(True)
        self._start_btn.clicked.connect(self._on_start)
        row.addWidget(self._cancel_btn)
        row.addWidget(self._start_btn)
        layout.addLayout(row)

        self._worker: DownloadWorker | None = None
        self.setup_ok = engine.models_present()

    # -- slots ---------------------------------------------------------
    def _on_start(self) -> None:
        self._start_btn.setEnabled(False)
        self._worker = DownloadWorker(self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_progress(self, filename: str, done: int, total: int) -> None:
        if total > 0:
            self._bar.setValue(int(done * 100 / total))
        mb_done = done / (1024 * 1024)
        mb_total = total / (1024 * 1024) if total else 0
        self._status.setText(f"{filename}: {mb_done:.1f} / {mb_total:.1f} MB")

    def _on_finished(self) -> None:
        self.setup_ok = engine.models_present()
        if self.setup_ok:
            QMessageBox.information(self, "Setup complete",
                                   "Models downloaded. The studio is ready!")
            self.accept()
        else:
            self._on_error("Download finished but models are still missing.")

    def _on_error(self, msg: str) -> None:
        self._start_btn.setEnabled(True)
        self._status.setText("Error — you can retry the download.")
        QMessageBox.warning(self, "Setup failed", msg)

    def _on_cancelled(self) -> None:
        self._start_btn.setEnabled(True)
        self._status.setText("Download cancelled.")

    def _on_cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(3000)
        self.reject()

    @staticmethod
    def ensure_models(parent=None) -> bool:
        """Returns True when models are present (downloading if needed)."""
        if engine.models_present():
            return True
        dlg = SetupDialog(parent)
        dlg.exec()
        return dlg.setup_ok
