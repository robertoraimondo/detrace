# DeTrace

<img width="1912" height="1001" alt="image" src="https://github.com/user-attachments/assets/deec9bcd-0cf8-43d0-a01a-d0267b9eea4d" />

<img width="1912" height="1025" alt="image" src="https://github.com/user-attachments/assets/ef252d02-5099-4ff9-9146-204970936e16" />

DeTrace is a local Windows app for turning an MP3 into playable instrument stems, previewing a custom mix, removing instruments, detecting chords, and exporting a new MP3. It runs from a desktop launcher and can open either as a native desktop window or in the default web browser.

## What is new

- Single separation workflow built around the local MVSep Mega 53 model.
- First-run launcher that prepares the app runtime, copies bundled files, installs missing tools, and starts Desktop App or Web Browser mode.
- App, setup executable, and launcher form icon support from the shared DeTrace icon assets.
- Accordion-aware Mega 53 output with accordion, piano, and generated other/no-accordion handling when the model provides the needed stems.
- Tool and performance status badges for MVSep, FFmpeg, codecs, chords, GPU, CPU, and RAM.
- Upload history, cached analysis results, and local workspace cleanup from the UI.
- Chord timeline, current chord display, piano keyboard highlighting, and spectrum visualization.
- Multilingual UI with English, Italian, Spanish, German, French, Portuguese, Chinese, Japanese, Korean, Arabic, Hindi, and Russian.

## Features

- Drag-and-drop or file-picker MP3 upload.
- Local full-instrument stem separation with MVSep Mega 53.
- Synchronized playback for selected stems.
- Stem mute/keep selection and MP3 export.
- Volume, bass, treble, seeking, play, pause, and stop controls.
- Chord detection through `librosa`.
- FFmpeg export with `imageio-ffmpeg` fallback when system FFmpeg is unavailable.
- Local-only HTTP API used by the desktop and browser interfaces.
- Packaged Windows executable and installer build scripts.

## Quick start

Build the Windows executable:

```powershell
.\build-exe.ps1
```

Run the app:

```text
dist\DeTrace.exe
```

On first launch, DeTrace checks for Python, creates a private runtime under the user data folder, installs requirements from the bundled `wheelhouse`, installs MVSep support, verifies the Mega 53 model files, and then opens the selected mode.

Build the installer:

```powershell
.\build-installer.ps1
```

The installer output is written to:

```text
installer\DeTraceSetup.exe
```

## Build-time signing

Builds are signed at build time by `sign-app.ps1`. For repeatable signing, keep one DeTrace code-signing certificate and import its private-key PFX on each build machine instead of generating a new certificate on user machines.

The build scripts pass `-NoCreate`, so a build fails if the reusable signing certificate is missing. This prevents accidentally shipping builds signed by different self-signed certificates.

Recommended build-machine setup:

```powershell
$env:DETRACE_SIGN_CERT_PFX = "D:\secure\DeTrace-CodeSigning.pfx"
$env:DETRACE_SIGN_CERT_PASSWORD = "your-pfx-password"
.\build-installer.ps1
```

If the certificate is already installed in `Cert:\CurrentUser\My`, use its thumbprint:

```powershell
$env:DETRACE_SIGN_CERT_THUMBPRINT = "THUMBPRINT_WITHOUT_SPACES"
.\build-installer.ps1
```

Private certificate files (`*.pfx`, `*.p12`) are ignored by git. The installer does not generate or install trusted certificates on end-user machines.

## Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the setup launcher from source:

```powershell
.\setup-and-run.ps1
```

Or start the local server directly:

```powershell
python server.py
```

Then open:

```text
http://localhost:5180
```

If port `5180` is busy, the server automatically tries the next available port unless `PORT` is explicitly set.

## Model files

DeTrace uses the full-instrument MVSep Mega 53 model from:

```text
models\mvsep_true_accordion\
```

The launcher reads download URLs from:

```text
models\mvsep_true_accordion\download-urls.txt
```

After setup, the installed app keeps runtime files under the user's local DeTrace data directory:

```text
.detrace-app\
  tools\Music-Source-Separation-Training\
  models\mvsep_true_accordion\
    config.yaml
    checkpoint.ckpt
.detrace-runtime\
```

Advanced overrides:

```powershell
$env:DETRACE_MVSEP_REPO = "D:\path\to\Music-Source-Separation-Training"
$env:DETRACE_MVSEP_TRUE_CONFIG = "D:\path\to\config.yaml"
$env:DETRACE_MVSEP_TRUE_CKPT = "D:\path\to\checkpoint.ckpt"
$env:DETRACE_MVSEP_PYTHON = "D:\path\to\python.exe"
$env:DETRACE_MVSEP_FORCE_CPU = "1"
$env:DETRACE_CPU_THREADS = "8"
$env:DETRACE_ACCORDION_REDUCTION = "0.65"
```

## Workflow

1. Launch DeTrace and choose Desktop App or Web Browser mode.
2. Drop an MP3 into the app or choose one from disk.
3. DeTrace analyzes the file with the local MVSep Mega 53 model.
4. Review stems, chords, tool status, and the session log.
5. Select the stems to keep and preview the mix.
6. Export the selected stems to MP3.

Uploads, stems, chord caches, and exports are stored under `workspace\`, which is ignored by git.

## Local API

The local server exposes these endpoints for the UI:

- `GET /api/status`
- `GET /api/jobs`
- `GET /api/jobs/{jobId}`
- `POST /api/upload`
- `POST /api/separate`
- `POST /api/chords`
- `POST /api/export`
- `POST /api/install-tools`
- `POST /api/shutdown`
- `DELETE /api/jobs`
- `DELETE /api/jobs/{jobId}`

## Build outputs

Generated folders are ignored by git:

- `build\`
- `dist\`
- `installer\`
- `wheelhouse\`
- `workspace\`
- `__pycache__\`

## License

This project is open source and available under the MIT License.

Author: Roberto Raimondo - IS Senior Systems Engineer II

(c) 2026 All Rights Reserved.
