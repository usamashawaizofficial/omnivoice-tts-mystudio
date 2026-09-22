"""Dark professional theme (QSS) for the TTS Studio."""
from __future__ import annotations

DARK_QSS = """
QWidget {
    background-color: #1e1e24;
    color: #e8e8ec;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #1e1e24;
}
QTextEdit, QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
    background-color: #26262e;
    border: 1px solid #3a3a44;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #4a6fa5;
}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus {
    border: 1px solid #5b8dd9;
}
QComboBox QAbstractItemView {
    background-color: #26262e;
    border: 1px solid #3a3a44;
    selection-background-color: #4a6fa5;
}
QPushButton {
    background-color: #3a3a44;
    border: 1px solid #4a4a56;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #464652;
}
QPushButton:pressed {
    background-color: #32323a;
}
QPushButton:disabled {
    background-color: #2a2a30;
    color: #77777f;
    border-color: #34343c;
}
QPushButton#generateButton {
    background-color: #2f7d4f;
    border: 1px solid #3a9c64;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 16px;
}
QPushButton#generateButton:hover {
    background-color: #35905a;
}
QPushButton#generateButton:disabled {
    background-color: #2a2a30;
    color: #77777f;
    border-color: #34343c;
}
QPushButton#dangerButton {
    background-color: #7d2f2f;
    border: 1px solid #9c3a3a;
}
QPushButton#dangerButton:hover {
    background-color: #905050;
}
QProgressBar {
    background-color: #26262e;
    border: 1px solid #3a3a44;
    border-radius: 6px;
    text-align: center;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #2f7d4f;
    border-radius: 5px;
}
QLabel#heading {
    font-size: 15px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#dim {
    color: #9a9aa4;
}
QStatusBar {
    background-color: #18181d;
    border-top: 1px solid #33333b;
}
QMenuBar {
    background-color: #18181d;
}
QMenuBar::item:selected, QMenu::item:selected {
    background-color: #3a3a44;
}
QMenu {
    background-color: #26262e;
    border: 1px solid #3a3a44;
}
QSplitter::handle {
    background-color: #33333b;
}
QGroupBox {
    border: 1px solid #3a3a44;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
"""
