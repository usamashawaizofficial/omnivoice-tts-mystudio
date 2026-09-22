# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for OmniVoice TTS Studio (Windows 64-bit).

Build (on the Windows CI runner):
    pyinstaller packaging/tts-studio.spec

Output: dist/OmniVoiceTTSStudio/OmniVoiceTTSStudio.exe  (one-folder bundle)
The engine DLLs + EXEs are collected from ../engine-bin-win/ — the GitHub
Actions workflow compiles omnivoice.cpp on Windows and drops the results
there before calling PyInstaller.
"""
from pathlib import Path

ROOT = Path(SPECPATH)                 # packaging/
SRC = ROOT.parent / "src"             # src/  (tts_studio package lives here)
ENGINE_BIN = ROOT / "engine-bin-win"  # omnivoice-tts.exe, omnivoice-codec.exe, *.dll

a = Analysis(
    [str(ROOT / "app_launcher.py")],
    pathex=[str(SRC)],
    binaries=[
        (str(ENGINE_BIN / "omnivoice-tts.exe"), "bin"),
        (str(ENGINE_BIN / "omnivoice-codec.exe"), "bin"),
        (str(ENGINE_BIN / "*.dll"), "bin"),
    ],
    datas=[],
    hiddenimports=[
        "tts_studio",
        "tts_studio.ui",
        "tts_studio.ui.app",
        "tts_studio.ui.main_window",
        "tts_studio.ui.voices_dialog",
        "tts_studio.ui.setup_dialog",
        "tts_studio.ui.worker",
        "tts_studio.ui.theme",
        "mutagen",
        "mutagen.mp3",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OmniVoiceTTSStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app — no console window
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="OmniVoiceTTSStudio",
)
