"""Voice library manager: add / delete / preview cloned voices.

Each voice stores a reference WAV plus its transcript; cloning happens
at generation time via the engine.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .. import voices
from ..voices import Voice
from .worker import TestVoiceWorker

LANGUAGES = ["English", "Urdu", "Hindi", "Korean", "Spanish", "German",
             "Japanese", "Other"]


class AddVoiceDialog(QDialog):
    """Form for adding a new cloned voice."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Cloned Voice")
        self.setModal(True)
        self.setMinimumWidth(440)

        form = QFormLayout(self)

        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. My Narrator Voice")
        form.addRow("Voice name:", self._name)

        self._lang = QComboBox()
        self._lang.addItems(LANGUAGES)
        form.addRow("Language:", self._lang)

        wav_row = QHBoxLayout()
        self._wav_path = QLineEdit()
        self._wav_path.setReadOnly(True)
        self._wav_path.setPlaceholderText("Choose a .wav reference clip (3–30 s)")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._pick_wav)
        wav_row.addWidget(self._wav_path)
        wav_row.addWidget(browse)
        form.addRow("Reference audio:", wav_row)

        self._transcript = QTextEdit()
        self._transcript.setPlaceholderText(
            "Type exactly what is said in the reference audio…")
        self._transcript.setMaximumHeight(90)
        form.addRow("Transcript:", self._transcript)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Voice")
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        form.addRow(btns)

        self.saved_voice: Voice | None = None

    def _pick_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose reference audio", "",
            "WAV audio (*.wav);;All files (*)")
        if path:
            self._wav_path.setText(path)

    def _on_save(self) -> None:
        name = self._name.text().strip()
        wav = self._wav_path.text().strip()
        transcript = self._transcript.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please give the voice a name.")
            return
        if not wav or not Path(wav).is_file():
            QMessageBox.warning(self, "Missing audio",
                                "Please choose a valid .wav reference clip.")
            return
        if not transcript:
            QMessageBox.warning(self, "Missing transcript",
                                "Please type what is said in the reference audio.")
            return
        try:
            self.saved_voice = voices.save_voice(
                name, self._lang.currentText(), Path(wav), transcript)
        except Exception as exc:
            QMessageBox.critical(self, "Could not save", str(exc))
            return
        self.accept()


class VoicesDialog(QDialog):
    """Lists saved voices; add, delete, and preview (test) them."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Library")
        self.setMinimumSize(520, 380)

        layout = QVBoxLayout(self)

        heading = QLabel("Cloned voices")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._refresh_buttons)
        layout.addWidget(self._list)

        row = QHBoxLayout()
        self._add_btn = QPushButton("Add Voice…")
        self._add_btn.clicked.connect(self._on_add)
        self._test_btn = QPushButton("Test Voice")
        self._test_btn.clicked.connect(self._on_test)
        self._del_btn = QPushButton("Delete")
        self._del_btn.setObjectName("dangerButton")
        self._del_btn.clicked.connect(self._on_delete)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(self._add_btn)
        row.addWidget(self._test_btn)
        row.addWidget(self._del_btn)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)

        self._status = QLabel("")
        self._status.setObjectName("dim")
        layout.addWidget(self._status)

        self._player = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_out)

        self._test_worker: TestVoiceWorker | None = None
        self._reload()

    # -- list ----------------------------------------------------------
    def _reload(self) -> None:
        self._list.clear()
        for v in voices.list_voices():
            item = QListWidgetItem(f"{v.name}  —  {v.language}")
            item.setData(Qt.UserRole, v.voice_id)
            self._list.addItem(item)
        self._refresh_buttons()

    def _selected(self) -> Voice | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return voices.get_voice(item.data(Qt.UserRole))

    def _refresh_buttons(self) -> None:
        has = self._selected() is not None
        busy = self._test_worker is not None and self._test_worker.isRunning()
        self._test_btn.setEnabled(has and not busy)
        self._del_btn.setEnabled(has and not busy)

    # -- actions -------------------------------------------------------
    def _on_add(self) -> None:
        dlg = AddVoiceDialog(self)
        if dlg.exec():
            self._reload()
            self._status.setText(f"Voice '{dlg.saved_voice.name}' saved.")

    def _on_delete(self) -> None:
        v = self._selected()
        if v is None:
            return
        if QMessageBox.question(self, "Delete voice",
                               f"Delete '{v.name}' permanently?") \
                != QMessageBox.Yes:
            return
        voices.delete_voice(v.voice_id)
        self._reload()
        self._status.setText(f"Voice '{v.name}' deleted.")

    def _on_test(self) -> None:
        v = self._selected()
        if v is None:
            return
        self._test_btn.setEnabled(False)
        self._status.setText(f"Generating preview for '{v.name}'…")
        self._test_worker = TestVoiceWorker(v, parent=self)
        self._test_worker.finished.connect(self._on_test_done)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.start()

    def _on_test_done(self, path: str) -> None:
        self._refresh_buttons()
        self._status.setText("Playing preview…")
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _on_test_error(self, msg: str) -> None:
        self._refresh_buttons()
        self._status.setText("Preview failed.")
        QMessageBox.warning(self, "Preview failed",
                            f"Could not generate the preview:\n{msg}")
