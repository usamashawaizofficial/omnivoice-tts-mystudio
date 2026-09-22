# OmniVoice TTS Studio

Offline, CPU-only text-to-speech studio for Windows 10/11 (64-bit).
Type or paste a script, pick a voice (or clone your own), and render
long-form voiceovers with automatic chunking and crossfades — no internet,
no API keys, no accounts after the first-run model download.

**Engine:** [omnivoice.cpp](https://github.com/ServeurpersoCom/omnivoice.cpp)
(CPU inference for k2-fsa OmniVoice). Model: OmniVoice Q8 (best quality).

## Build the Windows installer (free, via GitHub Actions)

1. Upload this repo to GitHub.
2. Open the **Actions** tab → **Build Windows installer** → **Run workflow**.
3. When it finishes, download `OmniVoiceTTSStudio-win64.zip` from the run's
   artifacts (or from Releases, if you ran it on a `v*` tag).
4. Unzip on the Windows PC and run `OmniVoiceTTSStudio.exe`.
5. First launch downloads ~900 MB of model files, then works fully offline.

See `docs/REQUIREMENTS.md` for end-user system requirements.

## Project layout

- `src/tts_studio/` — the app (`ui/`: PySide6 interface, `pipeline.py`:
  chunk → synthesize → join → export, `engine.py`: engine adapter,
  `voices.py`: cloned-voice library, `config.py`: paths & settings)
- `packaging/tts-studio.spec` — PyInstaller build spec
- `.github/workflows/build-windows.yml` — CI build (engine + installer)

## License note

For **personal use**. The OmniVoice model weights are non-commercial —
do not sell or redistribute builds containing them. The app code is
structured so the engine can be swapped later.
