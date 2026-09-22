"""Main window: script editor, voice selection, generation, output library."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QDateTime, Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import chunker, voices
from ..config import DEFAULTS, OUTPUT_DIR
from ..engine import EngineError
from ..voices import Voice
from .voices_dialog import VoicesDialog
from .worker import GenerateWorker

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a"}
_DESIGN_SENTINEL = "__design__"


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w\- ]+", "", name.strip()).strip().replace(" ", "_")
    return name or "voiceover"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OmniVoice TTS Studio")
        self.resize(1080, 680)

        self._worker: GenerateWorker | None = None
        self._player = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_out)

        self._build_menu()
        self._build_central()
        self.setStatusBar(QStatusBar(self))
        self._refresh_voice_combo()
        self._refresh_outputs()
        self.statusBar().showMessage("Ready.")

    # -- construction --------------------------------------------------
    def _build_menu(self) -> None:
        bar = self.menuBar()
        voices_menu = bar.addMenu("&Voices")
        manage = QAction("Manage voices…", self)
        manage.triggered.connect(self._open_voices)
        voices_menu.addAction(manage)

        help_menu = bar.addMenu("&Help")
        about = QAction("About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._build_editor_panel())
        splitter.addWidget(self._build_side_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

    def _build_editor_panel(self) -> QWidget:
        box = QGroupBox("Script")
        layout = QVBoxLayout(box)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText(
            "Paste your script here — in Urdu, English, Hindi, Korean, "
            "Spanish, German, Japanese…\n\nLong scripts are handled "
            "automatically: the studio splits them into chunks and joins "
            "the audio seamlessly.")
        self._editor.textChanged.connect(self._update_counter)
        layout.addWidget(self._editor)

        bottom = QHBoxLayout()
        self._counter = QLabel("0 chars · 0 words · 0 chunks")
        self._counter.setObjectName("dim")
        bottom.addWidget(self._counter)
        bottom.addStretch(1)
        for label, slot in (("Load .txt…", self._load_txt),
                            ("Save .txt…", self._save_txt),
                            ("Clear", self._editor.clear)):
            b = QPushButton(label)
            b.clicked.connect(slot)
            bottom.addWidget(b)
        layout.addLayout(bottom)
        return box

    def _build_side_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Voice selection
        vg = QGroupBox("Voice")
        vl = QVBoxLayout(vg)
        self._voice_combo = QComboBox()
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        vl.addWidget(self._voice_combo)
        self._design_edit = QLineEdit()
        self._design_edit.setPlaceholderText(
            "Describe the voice, e.g. 'a warm female narrator, slightly raspy'")
        self._design_edit.setEnabled(False)
        vl.addWidget(self._design_edit)
        manage_btn = QPushButton("Manage voices…")
        manage_btn.clicked.connect(self._open_voices)
        vl.addWidget(manage_btn)
        layout.addWidget(vg)

        # Output options
        og = QGroupBox("Output")
        ol = QVBoxLayout(og)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("File name:"))
        self._name_edit = QLineEdit(
            f"voiceover_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmm')}")
        name_row.addWidget(self._name_edit)
        ol.addLayout(name_row)
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format:"))
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["mp3", "wav"])
        self._fmt_combo.setCurrentText(DEFAULTS["output_format"])
        fmt_row.addWidget(self._fmt_combo)
        fmt_row.addStretch(1)
        ol.addLayout(fmt_row)
        layout.addWidget(og)

        # Generate controls
        self._generate_btn = QPushButton("Generate Voiceover")
        self._generate_btn.setObjectName("generateButton")
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        layout.addWidget(self._bar)
        self._stage = QLabel("")
        self._stage.setObjectName("dim")
        layout.addWidget(self._stage)

        # Output library
        out = QGroupBox("Generated audio")
        out_l = QVBoxLayout(out)
        self._outputs = QListWidget()
        self._outputs.itemDoubleClicked.connect(lambda _: self._play_selected())
        out_l.addWidget(self._outputs)
        orow = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._play_btn.clicked.connect(self._play_selected)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.clicked.connect(self._player.stop)
        folder_btn = QPushButton("Open folder")
        folder_btn.clicked.connect(self._open_folder)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_outputs)
        orow.addWidget(self._play_btn)
        orow.addWidget(self._stop_btn)
        orow.addWidget(folder_btn)
        orow.addWidget(refresh_btn)
        out_l.addLayout(orow)
        layout.addWidget(out, 1)
        return panel

    # -- editor helpers ------------------------------------------------
    def _update_counter(self) -> None:
        text = self._editor.toPlainText()
        chars = len(text)
        words = len(text.split())
        chunks = chunker.estimate_chunks(text, DEFAULTS["chunk_max_chars"]) if text.strip() else 0
        self._counter.setText(f"{chars} chars · {words} words · {chunks} chunks")

    def _load_txt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load script", "",
                                              "Text files (*.txt);;All files (*)")
        if path:
            try:
                self._editor.setPlainText(Path(path).read_text(encoding="utf-8"))
            except Exception as exc:
                QMessageBox.warning(self, "Could not load", str(exc))

    def _save_txt(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save script", "script.txt",
                                              "Text files (*.txt)")
        if path:
            try:
                Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
            except Exception as exc:
                QMessageBox.warning(self, "Could not save", str(exc))

    # -- voices --------------------------------------------------------
    def _open_voices(self) -> None:
        dlg = VoicesDialog(self)
        dlg.exec()
        self._refresh_voice_combo()

    def _refresh_voice_combo(self) -> None:
        combo = self._voice_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Default voice", None)
        for v in voices.list_voices():
            combo.addItem(f"{v.name} ({v.language})", v.voice_id)
        combo.addItem("Design from description…", _DESIGN_SENTINEL)
        combo.blockSignals(False)
        self._on_voice_changed(combo.currentIndex())

    def _on_voice_changed(self, index: int) -> None:
        self._design_edit.setEnabled(
            self._voice_combo.itemData(index) == _DESIGN_SENTINEL)

    def _selected_voice(self) -> Voice | None:
        data = self._voice_combo.currentData()
        if data in (None, _DESIGN_SENTINEL):
            return None
        return voices.get_voice(data)

    # -- generation ----------------------------------------------------
    def _on_generate(self) -> None:
        text = self._editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty script",
                                "Please paste a script first.")
            return
        design_active = self._voice_combo.currentData() == _DESIGN_SENTINEL
        description = self._design_edit.text().strip() if design_active else None
        if design_active and not description:
            QMessageBox.warning(self, "Missing description",
                                "Describe the voice you want, or pick another voice.")
            return

        self._generate_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._bar.setValue(0)
        self._stage.setText("Starting…")
        self.statusBar().showMessage("Generating…")

        self._worker = GenerateWorker(
            text=text,
            output_name=_safe_name(self._name_edit.text()),
            voice=self._selected_voice(),
            voice_description=description,
            output_format=self._fmt_combo.currentText(),
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_progress(self, done: int, total: int, stage: str) -> None:
        self._bar.setValue(int(done * 100 / max(total, 1)))
        self._stage.setText(stage)
        self.statusBar().showMessage(f"Generating… {stage}")

    def _generation_done_common(self) -> None:
        self._generate_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._worker = None

    def _on_finished(self, path: str) -> None:
        self._generation_done_common()
        self._bar.setValue(100)
        self._stage.setText("Done.")
        self.statusBar().showMessage(f"Saved: {path}")
        self._refresh_outputs()
        QMessageBox.information(self, "Done", f"Voiceover saved:\n{path}")

    def _on_error(self, msg: str) -> None:
        self._generation_done_common()
        self._stage.setText("Failed.")
        self.statusBar().showMessage("Generation failed.")
        if "binary not found" in msg or "Model files missing" in msg:
            detail = (f"{msg}\n\nThe voice engine is not set up yet. "
                      "Restart the app to run first-time setup.")
        else:
            detail = msg
        QMessageBox.critical(self, "Generation failed", detail)

    def _on_cancelled(self) -> None:
        self._generation_done_common()
        self._bar.setValue(0)
        self._stage.setText("Cancelled.")
        self.statusBar().showMessage("Generation cancelled.")

    def _on_cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._stage.setText("Cancelling…")

    # -- output library ------------------------------------------------
    def _refresh_outputs(self) -> None:
        self._outputs.clear()
        if not OUTPUT_DIR.exists():
            return
        files = sorted(
            (p for p in OUTPUT_DIR.iterdir()
             if p.is_file() and p.suffix.lower() in AUDIO_EXTS
             and not p.name.startswith("_voice_preview")),
            key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files:
            size_mb = p.stat().st_size / (1024 * 1024)
            item = QListWidgetItem(f"{p.name}  ({size_mb:.1f} MB)")
            item.setData(Qt.UserRole, str(p))
            self._outputs.addItem(item)

    def _play_selected(self) -> None:
        item = self._outputs.currentItem()
        if item is None:
            return
        self._player.setSource(QUrl.fromLocalFile(item.data(Qt.UserRole)))
        self._player.play()
        self.statusBar().showMessage(f"Playing: {Path(item.data(Qt.UserRole)).name}")

    def _open_folder(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(OUTPUT_DIR)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])

    # -- misc ----------------------------------------------------------
    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About OmniVoice TTS Studio",
            "OmniVoice TTS Studio\n\n"
            "Offline, CPU-only text-to-speech with voice cloning.\n"
            "Paste a script, pick a voice, get a finished voiceover.\n\n"
            "No accounts, no API keys, no internet needed after setup.")

    def closeEvent(self, event) -> None:  # noqa: D102 - Qt API
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(5000)
        self._player.stop()
        super().closeEvent(event)
