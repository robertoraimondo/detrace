# DeTrace

DeTrace is a local Windows desktop app for separating an MP3 into playable instrument stems, muting or removing tracks, previewing the remaining mix in sync, detecting chords, and exporting a new MP3.

![DeTrace main interface](https://github.com/user-attachments/assets/703b3094-ec08-4825-a868-00c942d9fb94)

![DeTrace upload and controls layout](https://github.com/user-attachments/assets/9d948a30-5fda-4439-beec-8f80f5553428)

![DeTrace stem selection workspace](https://github.com/user-attachments/assets/ae367163-ca4e-4ebd-90ed-cbf67fa20ff7)

## Features

- Local MP3 upload, analysis, preview, and export.
- Default full-instrument separation with a local MVSep Mega 53-stem model.
- Full 53-stem local separation focused on extracting the available instrument tracks from the MVSep Mega model.
- Accordion-focused output helpers, including an accordion stem and a regenerated no-accordion mix.
- Synchronized playback for the original track and selected stems.
- Transport controls for rewind, play selected, pause, stop, loop, seeking, volume, bass, and treble.
- Chord detection with a timeline, current chord display, and piano keyboard note highlighting.
- Audio spectrum visualization during playback.
- Upload history for recently analyzed MP3 files, with a clear action for local workspace cleanup.
- Tool readiness badges for Demucs, MVSep Accordion, FFmpeg, codecs, chords, GPU, CPU, and RAM.
- Desktop App and Web Browser launch modes from the same packaged executable.
- Multilingual interface: English, Italian, Spanish, German, French, Portuguese, Chinese, Japanese, Korean, Arabic, Hindi, and Russian.

The app uses:

- A desktop launcher executable.
- Python standard library for the local app server.
- [Demucs](https://github.com/facebookresearch/demucs) for optional source separation.
- MVSep model files for accordion and full-instrument local separation.
- FFmpeg, or the bundled `imageio-ffmpeg` fallback, for preview/export media handling.
- `librosa` for chord detection when installed.

## Quick start

Build the Windows executable:

```powershell
.\build-exe.ps1
```

Then run:

```text
dist\DeTrace.exe
```

The executable lets you choose **Desktop App** or **Web Browser** mode. It checks the system for Python, installs Python 3.11 with `winget` if needed, creates a local `.detrace-runtime`, installs requirements, codecs, separation tools, and model files, then starts DeTrace in the selected mode.

In web mode, DeTrace starts a hidden local HTTP server and opens the app in your default browser.

The build also creates a local `wheelhouse/` dependency cache and bundles it into the executable. On a user PC, DeTrace installs requirements from those local files first, which makes setup faster and allows dependency installation without downloading packages again.

To build the Windows installer:

```powershell
.\build-installer.ps1
```

## Development

Install the audio tools:

```powershell
python -m pip install -r requirements.txt
```

If system FFmpeg is not installed, DeTrace uses `imageio-ffmpeg`.

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

Open [http://localhost:5180](http://localhost:5180) in your browser.

If that port is busy, DeTrace automatically uses the next available port.

## Render Deployment

Use the Python environment on Render and install dependencies from `requirements.txt`.

Build command:

```bash
pip install -r requirements.txt && python render_setup.py
```

Start command:

```bash
python render_setup.py && gunicorn detrace.wsgi --workers 1 --threads 4 --timeout 1800
```

The included `render.yaml` uses those commands. `render_setup.py` downloads the MVSep source, accordion config/checkpoint, and true multi-stem accordion config/checkpoint during the Render build so the `MVSep Accordion` and `True Accordion` readiness checks can pass in the deployed app.

GPU acceleration on Render requires a service instance that exposes an NVIDIA GPU. If your Render service has a GPU available, set `DETRACE_ENABLE_CUDA=1` so `render_setup.py` installs CUDA-enabled PyTorch. Keep `DETRACE_MVSEP_FORCE_CPU=0`; setting it to `1` forces MVSep to ignore CUDA.

## Fly.io Deployment

The repo includes a `Dockerfile` and `fly.toml` for Fly.io. The container listens on `0.0.0.0:8080`, installs dependencies, and runs the same MVSep setup used by Render.

Deploy:

```bash
flyctl deploy -a detrace
```

If Fly reports `unauthorized` while building or pushing the image, refresh the Fly login and retry:

```bash
flyctl auth logout
flyctl auth login
```

## Separation Models

The app uses **Full instrument stems: MVSep Mega 53 local model** as its separation workflow. It runs the local MVSep model, keeps audible instrument outputs, and lets you preview, mute, remove, and export the selected stems from that full model result.

DeTrace still uses Demucs-related tooling only where the packaged runtime needs it for legacy support or setup compatibility. The user-facing workflow is now the full 53-stem MVSep model.

## Local Model Files

The desktop launcher installs local MVSep support during first-run setup by downloading:

- [ZFTurbo/Music-Source-Separation-Training](https://github.com/ZFTurbo/Music-Source-Separation-Training).
- The MVSep Mega 53-stem accordion config and checkpoint.
- The optional full-instrument MVSep config and checkpoint configured in `models/mvsep_true_accordion/download-urls.txt`.

After setup, the files are stored inside the installed app folder:

```text
.detrace-app/
  tools/
    Music-Source-Separation-Training/
      inference.py
  models/
    mvsep_accordion/
      config.yaml
      bs_mega_53stem_accordion_mvsep.ckpt
    mvsep_true_accordion/
      config.yaml
      checkpoint.ckpt
```

For advanced/manual setups, you can override the automatic paths with environment variables:

```powershell
$env:DETRACE_MVSEP_REPO = "D:\path\to\Music-Source-Separation-Training"
$env:DETRACE_MVSEP_ACCORDION_CONFIG = "D:\path\to\accordion-config.yaml"
$env:DETRACE_MVSEP_ACCORDION_CKPT = "D:\path\to\bs_mega_53stem_accordion_mvsep.ckpt"
$env:DETRACE_MVSEP_TRUE_CONFIG = "D:\path\to\full-model-config.yaml"
$env:DETRACE_MVSEP_TRUE_CKPT = "D:\path\to\full-model-checkpoint.ckpt"
```

Optional:

```powershell
$env:DETRACE_MVSEP_PYTHON = "D:\path\to\python.exe"
$env:DETRACE_MVSEP_FORCE_CPU = "1"
```

## Workflow

1. Drop an MP3 into the app or click **Choose MP3**.
2. DeTrace checks the required tools and installs missing components when launched from the desktop package.
3. DeTrace analyzes the file with the selected local separation model.
4. Review the generated stems, chords, session log, and tool status.
5. Select the stems you want to keep in the mix.
6. Use **Play Selected**, seek, loop, volume, bass, and treble controls to preview the result.
7. Click **Export MP3** to download the selected-stem mix.

Uploads, stems, chord caches, and exports are stored under `workspace/`, which is ignored by git.

## Local API

The app server exposes local-only endpoints for the browser UI:

- `GET /api/status`
- `GET /api/jobs`
- `POST /api/upload`
- `POST /api/separate`
- `POST /api/chords`
- `POST /api/export`
- `POST /api/install-tools`
- `POST /api/shutdown`
- `DELETE /api/jobs`

## License

This project is open source and available under the MIT License.

Author: Roberto Raimondo - IS Senior Systems Engineer II

(c) 2026 All Rights Reserved.
