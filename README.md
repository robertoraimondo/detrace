# DeTrace

DeTrace is a local desktop app for separating an MP3 into vocal and instrument stems, muting/removing individual tracks, previewing the remaining mix, and exporting a new MP3.

<img width="630" height="697" alt="image" src="https://github.com/user-attachments/assets/784606d3-8a4e-40e2-bc17-8476c53391ca" />

<img width="631" height="692" alt="image" src="https://github.com/user-attachments/assets/291986dc-9a14-404a-af31-e86feed1d7bf" />

<img width="1239" height="843" alt="image" src="https://github.com/user-attachments/assets/6fa0e038-7ddd-4a97-b95c-2d782f244b6e" />


<img width="1910" height="866" alt="image" src="https://github.com/user-attachments/assets/9ae9beec-f213-43df-a49c-916bdd41e3c9" />


The app uses:

- A desktop launcher executable.
- Python standard library for the local app server.
- [Demucs](https://github.com/facebookresearch/demucs) for source separation when installed.
- FFmpeg, or the bundled `imageio-ffmpeg` fallback, for mixing/exporting MP3 files.

The interface includes a language selector with English, Italian, Spanish, German, French, Portuguese, Chinese, Japanese, Korean, Arabic, Hindi, and Russian.

## Quick start

Build the Windows executable:

```powershell
.\build-exe.ps1
```

Then run:

```text
dist\DeTrace.exe
```

The executable lets you choose **Desktop App** or **Web Browser** mode. It checks the system for Python, installs Python 3.11 with `winget` if needed, creates a local `.detrace-runtime`, installs requirements/codecs, then starts DeTrace in the selected mode.

In web mode, DeTrace starts a hidden local HTTP server and opens the app in your default browser.

The build also creates a local `wheelhouse/` dependency cache and bundles it into the executable. On a user PC, DeTrace installs requirements from those local files first, which makes setup faster and allows dependency installation without downloading packages again.

For development, use the script launcher:

```powershell
.\setup-and-run.ps1
```

Or double-click:

```text
setup-and-run.bat
```

The launcher checks for Python, installs it with `winget` if possible, installs DeTrace requirements, then starts the app.

You can also run the local server directly:

```powershell
python server.py
```

Open http://localhost:5180 in your browser.

If that port is busy, DeTrace automatically uses the next available port.

## Enable real stem separation

Install the audio tools:

```powershell
python -m pip install -r requirements.txt
```

If system FFmpeg is not installed, DeTrace uses `imageio-ffmpeg`.

By default, DeTrace uses Demucs `htdemucs_6s`, which can produce these stems:

- `vocals`
- `drums`
- `bass`
- `guitar`
- `piano`
- `other`

The app also includes the standard `htdemucs` 4-stem option:

- `vocals`
- `drums`
- `bass`
- `other`

## Workflow

1. Upload an MP3.
2. DeTrace analyzes the file with Demucs.
3. Select the instrument tracks you want to play or export.
4. Preview the selected stems.
5. Click **Export MP3** to choose where to save the new mix.

Files are stored under `workspace/`, which is ignored by git.

## License

This project is open source and available under the MIT License.

Author: Roberto Raimondo - IS Senior Systems Engineer II

© 2026 All Rights Reserved.
