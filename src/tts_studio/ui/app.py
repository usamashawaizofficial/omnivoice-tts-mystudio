"""Application entry point.

Launch (dev):
    python -m tts_studio.ui.app        (from the src/ directory)
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .theme import DARK_QSS
    from .main_window import MainWindow
    from .setup_dialog import SetupDialog

    app = QApplication(sys.argv)
    app.setApplicationName("OmniVoice TTS Studio")
    app.setOrganizationName("TTS Studio")
    app.setStyleSheet(DARK_QSS)

    try:
        if not SetupDialog.ensure_models():
            QMessageBox.information(
                None, "Setup incomplete",
                "Model files are required to run the studio. "
                "The app will now exit.")
            return 1
    except Exception as exc:  # never crash on startup checks
        QMessageBox.critical(None, "Startup error", str(exc))
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
