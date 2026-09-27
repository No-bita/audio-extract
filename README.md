# YouTube Audio Extractor & Clipper

A fast, lightweight, and user-centric tool designed to extract full tracks or precise contiguous audio clips from YouTube videos directly as 192 kbps MP3 files.

---

## 🎯 Features

- **Single-Video Enforcement**: Strips playlist bloat and downloads only the requested track.
- **Source Preservation**: Retains the highest-fidelity native Opus/AAC stream without intermediate lossy re-encoding.
- **Explicit Interval Clipping**: Uses FFmpeg fast seek (`-ss`) and explicit duration (`-t`) to export clean, sample-aligned MP3 clips.
- **Flexible Timestamps**: Supports `SS`, `MM:SS`, `HH:MM:SS`, fractional seconds, and countdown formats (`-MM:SS`).
- **Source Caching & Concurrency Control**: Caches raw audio files per `video_id` for 24 hours to prevent redundant downloads across multiple clips, with per-video concurrency locking.
- **Sleek Single-Page UI**: Luxury obsidian dark-mode interface with instant inspection, discrete honest progress stages, and direct browser download.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.9+ and FFmpeg installed on your system:
```bash
# macOS (via Homebrew)
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt update && sudo apt install ffmpeg
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Server
```bash
# Runs on default port 8765
python main.py

# Or specify any custom port:
python main.py --port 8765
```
Open **[http://127.0.0.1:8765](http://127.0.0.1:8765)** in your browser.

---

## 🧪 Running Tests

The test suite covers URL normalization, timestamp parsing/resolving/validation, FFmpeg command generation, workspace caching, and FastAPI endpoints:

```bash
pytest -v
```

---

## 📂 Architecture Overview

```text
YT_extractor/
├── audio_engine/          # Layer 1: Pure Python core library
│   ├── models.py          # Dataclasses (VideoMetadata, TimestampSpec, JobRecord)
│   ├── errors.py          # Domain exceptions with user-friendly messages
│   ├── downloader.py      # yt-dlp wrapper (inspection & raw audio acquisition)
│   ├── inspector.py       # ffprobe wrapper for stream properties
│   ├── timestamps.py      # TimestampParser, TimestampResolver, ClipValidator
│   ├── processor.py       # FFmpeg full conversion & interval clipping
│   └── workspace.py       # Source cache, job storage, and TTL cleanup
│
├── app/                   # Layer 2: Web Application
│   ├── main.py            # FastAPI application & startup dependency checks
│   ├── schemas.py         # Pydantic request & response schemas
│   ├── routes/
│   │   ├── inspect.py     # POST /api/inspect endpoint
│   │   └── jobs.py        # POST /api/jobs, GET /api/jobs/{id}, /download
│   └── services/
│       └── jobs.py        # In-memory job state & BackgroundTask worker
│
├── web/                   # Frontend SPA
│   ├── index.html         # Single-page 5-state UI shell
│   ├── css/app.css        # Modern obsidian glassmorphism design
│   └── js/app.js          # Reactive state machine & polling logic
│
├── tests/                 # Unit & integration test suite
└── workspace/             # Runtime storage (sources/, jobs/, temp/)
```

---

## 📡 API Reference

### 1. Inspect Video
```http
POST /api/inspect
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response (200 OK):**
```json
{
  "source_id": "yt_dQw4w9WgXcQ",
  "video_id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "channel": "Rick Astley",
  "duration": 212.0,
  "duration_formatted": "03:32",
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

### 2. Create Job
```http
POST /api/jobs
Content-Type: application/json

{
  "source_id": "yt_dQw4w9WgXcQ",
  "operation": "clip",
  "start": "01:05",
  "end": "02:30"
}
```

**Response (200 OK):**
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "queued",
  "stage": "queued",
  "message": "Job queued for processing..."
}
```

### 3. Check Job Status
```http
GET /api/jobs/job_a1b2c3d4
```

**Response (200 OK):**
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "completed",
  "stage": "completed",
  "message": "MP3 ready for download!",
  "download_url": "/api/jobs/job_a1b2c3d4/download",
  "error": null
}
```

### 4. Download MP3
```http
GET /api/jobs/job_a1b2c3d4/download
```
Streams the MP3 file with `Content-Disposition: attachment`.
