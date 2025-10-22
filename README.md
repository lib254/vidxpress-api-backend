# VidXpress API

VidXpress API is a small FastAPI service that downloads videos from supported platforms using yt-dlp, converts them (MP4/MP3) via FFmpeg, and exposes endpoints to fetch metadata, start conversions, stream progress, and download results.

## Features

- Fetch video metadata (title, thumbnail, duration, available formats)
- Download and convert videos to MP4 or extract audio to MP3
- Background conversion with progress streaming (SSE)
- Temporary file storage with periodic cleanup
- Docker-ready and simple local run using Uvicorn

## Important notice

VidXpress API is intended for personal use only. Users are responsible for respecting copyright and intellectual property rights. Downloading copyrighted content without permission may violate DMCA and local laws. This project provides tools — it is your responsibility to comply with applicable laws.

## Requirements

- Python 3.10+
- System: ffmpeg installed (binary available on PATH)
- The Python dependencies are listed in `requirements.txt` and include: fastapi, uvicorn, yt-dlp, ffmpeg-python, apscheduler, shortuuid, python-multipart

## Quick start — Docker (recommended)

1. Build the image:

```bash
docker build -t vidxpress-api .
```

2. Run the container (the service listens on port 8000 by default):

```bash
docker run -e PORT=8000 -p 8000:8000 vidxpress-api
```

This container image installs `ffmpeg` and the Python dependencies. Temporary files are stored in `/tmp/files` inside the container.

## Quick start — Local

1. Install system `ffmpeg` (Ubuntu/Debian):

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

2. Create a virtual environment and install Python deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the API locally:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

All endpoints are prefixed with `/api`.

- GET `/api/status` — Simple health endpoint. Returns status and a DMCA-style disclaimer.

- POST `/api/fetch` — Extract metadata for a video.
  - Body (JSON): { "video_url": "<VIDEO_URL>" }
  - Returns: title, thumbnail, duration, available formats (mp4 resolutions and audio ext)

- POST `/api/convert` — Start a background conversion task.
  - Body (JSON):
    - `video_url` (string) — source URL
    - `format` (string) — `mp3` or `mp4`
    - `quality` (string, optional) — for mp4 (e.g., `360p`, `720p`, `1080p`)
  - Returns: { "status": "started", "task_id": "..." }
  - Progress is tracked server-side and can be streamed.

- GET `/api/progress/{task_id}` — Server-sent events (SSE) stream for real-time progress updates for a task.

- GET `/api/download/` — Download route (query params): `?url=<VIDEO_URL>&format=mp4`
  - Example: `/api/download/?url=https://youtu.be/xxxxx&format=mp4`

## Supported Platforms / Domains

The service restricts downloads to a whitelist of domains for basic safety. Supported domains (as of this release):

- youtube.com, youtu.be
- tiktok.com
- facebook.com
- instagram.com
- twitter.com / x.com
- vimeo.com
- dailymotion.com

If you need to support additional sites, update `api/utils/downloader.py`'s `ALLOWED_DOMAINS` list.

## Temporary files and cleanup

Downloaded and converted files are placed in `/tmp/files`. A background scheduler (APScheduler) runs every hour to delete files older than one hour. You can adjust `CLEANUP_INTERVAL` in `api/utils/cleanup.py`.

## Cookies / Authenticated downloads

If you need to use authenticated downloads (for private or region-restricted content), place a `cookies.txt` file in `api/utils/` (yt-dlp cookie format). The downloader will automatically use it if present.

## File size limits and safety

The `/api/convert` route currently enforces a 100 MB max file size (see `MAX_FILE_SIZE` in `api/routes/convert.py`). Large files will be removed and the task will return an error.

## Development notes

- The main application entry is `api/main.py`.
- Route handlers live in `api/routes/` and helper logic is in `api/utils/`.
- Conversion uses `ffmpeg` via subprocess calls in `api/utils/converter.py` and yt-dlp via `api/utils/downloader.py`.

## Troubleshooting

- FFmpeg errors: make sure the `ffmpeg` binary is installed and accessible in PATH.
- yt-dlp errors: check `api/utils/cookies.txt` for authenticated downloads. Also verify the domain is in the allowed list.
- Permission issues writing to `/tmp/files`: ensure the process has write permission. The Dockerfile sets this directory to be writable.

## License

This repository does not include a license file. Add one if you plan to publish or share this project.

## Contributing

If you'd like to contribute, please open an issue describing the feature or bug. Small, focused pull requests are welcome.

---

If you'd like any additional sections (example client code, Postman collection, or CI setup), tell me which one and I can add it.

