<div align="center">

<h1>OddMinutes</h1>

<p>
  <strong>让沟通的每一分钟，都被听见、被记录、被理解</strong>
</p>

<p>
  Record · Transcribe · Summarize — Your Private AI Meeting Assistant
</p>

<p>
  <a href="https://www.oddmeta.net" target="_blank">🏠 Official Site</a> ·
  <a href="https://minutes.oddmeta.net" target="_blank">🌐 Live Demo</a> ·
  <a href="https://oddmeta.net/docs/oddminutes" target="_blank">📖 Documentation</a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Django-5.0.7-092E20?logo=django&logoColor=white" alt="Django 5.0.7">
  <img src="https://img.shields.io/badge/Vue.js-3.4-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue.js 3.4">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Platform-Windows-blue?logo=windows&logoColor=white" alt="Windows">
</p>

<p>
  <a href="README.md">English</a> <a href="README.chs.md">中文</a>
</p>

</div>

---

## ✨ Features

- 🎙️ **Dual-track Recording** — Simultaneously record microphone + system audio with Automatic Gain Control (AGC)
- 📝 **AI Real-time Transcription** — Powered by OddASR, word-level timestamps, first-word latency as low as 500ms
- 📑 **Live Caption** — Floating caption window, draggable position (disabled by default)
- 🤖 **Smart Summary** — Supports multiple LLM providers: Ollama / OpenAI / Claude / Groq
- 🔗 **Audio-Text Sync** — Click any word to jump to the corresponding audio position; highlighted during playback
- 📤 **Multi-format Export** — Audio, transcript PDF, summary PDF, packaged ZIP download with watermarks
- 🗣️ **Speaker Editing** — Edit speaker names, batch replace the same speaker within a meeting
- 🔍 **Full-text Search** — Search across all meeting transcripts
- ⏱️ **Pause & Resume** — Pause and resume recording at any time during a session
- 🎨 **Multiple Themes** — Modern Light, Tech Dark, Warm Office, Focus Dark
- 🔔 **Notification System** — Desktop notifications + notification history management
- 👤 **User Authentication** — Token-based authentication for all business APIs
- 📋 **System Tray** — Windows system tray integration with quick actions
- 🔄 **Version Check** — Automatically detect new PyPI releases

---

## 🚀 Quick Start

### Option 1: PyPI Install (Recommended)

```bash
# Basic install
pip install OddMinutes

# Windows users (includes system tray and hotkey support)
pip install "OddMinutes[windows]"

# Launch
OddMinutes
```

### Option 2: Run from Source

```bash
git clone https://github.com/oddmeta/oddminutes.git
cd oddminutes
pip install -r requirements.txt
copy .env.example .env
# Edit .env to configure OddASR and LLM
python manage.py migrate
python manage.py init_defaults
python launcher.py
```

Visit `http://127.0.0.1:9011`

---

## 📐 Architecture

```
┌────────────────────────────────────┐
│  Vue 3 Frontend / Vanilla HTML/JS  │
│  Meeting Mgmt · Recording · Sync   │
│  AI Summary · Themes · Notifications│
└──────────────┬─────────────────────┘
               │ HTTP / WebSocket
┌──────────────▼─────────────────────┐
│        Django 5 + DRF + Channels   │
│  core │ meetings │ recording       │
│  transcription │ summary │ users   │
│  system_app                      │
└──────────────┬─────────────────────┘
               │
┌──────────────▼─────────────────────┐
│  OddASR (Speech Recognition)       │
│  127.0.0.1:9002                    │
│                                    │
│  Ollama / OpenAI / Claude          │
│  (LLM Summarization)               │
└────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend Framework | Django 5.0.7 |
| API | Django REST Framework 3.15.2 |
| WebSocket | Django Channels 4.1.0 + Daphne 4.1.2 |
| Frontend | Vue 3.4 / HTML5 + CSS3 + JavaScript |
| Speech Recognition | OddASR (OpenAI-compatible API) |
| AI Summary | pydantic-ai-slim (Ollama / OpenAI / Claude / Groq) |
| Audio Processing | pydub + numpy + scipy + FFmpeg |
| Database | SQLite (default) |
| System Tray | pystray + pywin32 |

---

## 📋 External Dependencies

| Service | Purpose | Status |
|---------|---------|--------|
| **OddASR** | Speech-to-text transcription | **Required** |
| **FFmpeg** | Audio format conversion | **Required** |
| **Ollama / LLM** | AI summary generation | Optional |

Install OddASR:

```bash
pip install oddasr
oddasr-server
```

---

## ⚙️ Configuration

Key environment variables (`.env`):

```ini
DJANGO_SECRET_KEY=your-secret-key
ODDASR_URL=https://asr.oddmeta.net
ODDASR_API_KEY=your-key
ODDASR_MODEL=oddasr2_paraformer
AI_MODEL_CONFIGS=[{"provider":"ollama","model_name":"qwen3:8b","base_url":"http://localhost:11434"}]
```

For more configuration options, see the [Documentation Center](https://oddmeta.net/docs/oddminutes).

---

## 📦 Packaging & Distribution

### Windows Standalone Installer

```bash
# Full build (requires NSIS)
python build_installer.py

# Generate executable folder only
pyinstaller OddMinutes.spec --clean -y
```

---

## 📁 Project Structure

```
OddMinutes/
├── core/                 # Homepage, base models, audio utils
├── meetings/             # Meeting CRUD, search, export
├── recording/            # Recording control, WebSocket level push
├── transcription/        # ASR transcription, real-time transcription
├── summary/              # AI summary, template config
├── system_app/           # System settings, tray, notifications
├── users/                # User authentication
├── utils/                # PDF generation, audio processing, punctuation
├── meeting_minutes/      # Django project configuration
├── oddminutes-frontend/  # Vue 3 frontend
└── docs/                 # Documentation and manuals
```

---

## 📂 User Data Directory

After PyPI installation, user data and configuration files are stored at:

| OS | Path |
|----|------|
| **Windows** | `%APPDATA%\Local\OddMeta\OddMinutes` |
| **Linux** | `~/.local/share/OddMeta/OddMinutes` |
| **macOS** | `~/Library/Application Support/OddMeta/OddMinutes` |

This directory contains:
- `.env` — Environment configuration file
- `db.sqlite3` — SQLite database file
- `media/` — Audio file storage directory
- `logs/` — Log files directory

During development, set `ODDMINUTES_DATA_DIR` to point to the project root directory.

---

## 🖥️ Frontend Features

### Audio-Text Sync

The frontend implements bidirectional linkage between audio playback and text:
- **Highlight on Playback** — When audio plays to a specific timestamp, the corresponding word and segment are automatically highlighted
- **Click to Jump** — Click any word to jump the audio to that timestamp and start playing
- **Drag to Sync** — Drag the audio progress bar to automatically scroll to the corresponding text position

### Transcript Editing Mode

- Edit transcript text segment by segment (edit button appears on hover)
- Modify speaker names, with batch replacement support for the same speaker within a meeting
- Batch save changes

### Real-time Level Monitoring

Real-time microphone and system audio level display via WebSocket:
- Real-time level bar visualization
- AGC gain information tooltip
- Peak monitoring

### Search

Full-text search across all meeting transcripts, returning matching meeting lists with context.

### Theme System

- **modern-light** — Modern light theme
- **tech-dark** — Tech dark theme
- **warm-office** — Warm office theme
- **focus-dark** — Focus dark theme

### Notification System

- Desktop notifications (when page is not visible)
- Notification history (up to 200 entries)
- Unread notification count, mark as read / mark all as read
- Notification titles prefixed with meeting name for easy identification

### Live Caption

Real-time caption feature available during recording:
- Powered by OddASR real-time transcription, first-word latency as low as 500ms
- Floating caption window, draggable position
- Three-line scrolling display, distinguishing confirmed text from in-progress recognition
- Disabled by default, enable in system settings (`ENABLE_LIVE_CAPTION`)

### Export

- Audio files (MP3)
- Transcript PDF (with product watermark and header/footer)
- AI Summary PDF (with product watermark and header/footer)
- Smart PDF cache check to avoid redundant generation
- Auto-packaged ZIP download, filename uses meeting name
- Export API requires login

---

## 📋 System Tray Features

Windows system tray supports the following actions:
- **Show Window** — Open browser to access the app
- **New Meeting** — Create a new meeting record
- **Start Recording** — Start recording (auto-creates a meeting)
- **Pause Recording** — Pause current recording
- **Resume Recording** — Resume paused recording
- **Stop Recording** — Stop recording and process audio
- **Exit** — Stop service and exit

---

## ⚠️ Notes

1. **OddASR Service**: Ensure OddASR service is running before use
2. **FFmpeg**: Make sure FFmpeg is installed and added to system PATH before installing pydub
3. **Ollama**: When using local LLM for summaries, run `ollama pull qwen3:8b` to download the model first
4. **Audio Device Permission**: Grant microphone permission on first use of recording
5. **System Audio Recording**: On Windows, recording system audio requires enabling Stereo Mix or using a virtual audio cable
6. **Data Directory**: Default data is stored in the user directory; set `ODDMINUTES_DATA_DIR` to specify project root during development
7. **Development Mode**: When using `python manage.py runserver`, add `--noreload` to avoid multi-process state issues

---

## 📬 Contact Us

| Channel | Handle |
|---------|--------|
| WeChat Official Account | 奥德元 |
| WeChat | oddmeta |
| Weibo | [oddmeta](https://weibo.com/oddmeta) |
| Twitter / X | [oddmet](https://x.com/oddmet) |

---

## 📄 License

MIT License

---

<div align="center">

Made with ❤️ by [OddMeta](https://oddmeta.net)

</div>


