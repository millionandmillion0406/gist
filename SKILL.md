---
name: video-qa
description: >
  Download any video's audio, transcribe with Whisper, and answer questions
  about the content. Supports Bilibili, Douyin (with cookies), YouTube,
  and 1000+ sites supported by yt-dlp.
---

# video-qa: Video Content Q&A

Give it a video URL → it downloads the audio → transcribes with Whisper →
you ask questions about the content.

## Requirements

- Python 3.12+
- `yt-dlp` — `pip install yt-dlp`
- `ffmpeg` — `winget install ffmpeg` or `brew install ffmpeg`
- `openai-whisper` + `torch` — `pip install openai-whisper torch`

Everything is checked automatically. The script finds the right Python.

## Usage

```bash
# Basic: transcribe a video
python video_qa.py <video-url>

# Better accuracy (slower)
python video_qa.py <video-url> --model small

# English video
python video_qa.py <video-url> --lang en

# JSON output for programmatic use
python video_qa.py <video-url> --json
```

## Examples

```bash
# Bilibili (works in China)
python video_qa.py https://www.bilibili.com/video/BV1GJ411x7e7

# Douyin (requires cookies — run cookie login first)
python video_qa.py https://www.douyin.com/video/7665535066596065359

# YouTube (outside China)
python video_qa.py https://www.youtube.com/watch?v=xxxx
```

## Agent Instructions

1. User gives you a video URL
2. Run `python <path>/video_qa.py <url> --model small`
3. Read the transcript output
4. Answer the user's questions about the content

## Cookie Login (for Douyin/抖音)

```bash
cd C:/Users/windows/ZCodeProject/douyin-downloader
python tools/cookie_fetcher.py --output config/cookies.json
```
Opens a browser — scan the QR code to login. Cookies persist for future downloads.

## What it outputs

```
🧠 Transcribing with whisper (small)...
  ⏱ Model loaded in 12.3s
  ⏱ Transcribed in 8.2s

# 🎬 Video Title

Full transcript text...

---
### 📌 Timestamps
[00:00] First segment...
[00:15] Second segment...
```
