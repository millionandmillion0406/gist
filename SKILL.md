---
name: video-qa
description: >
  Universal video content Q&A tool. Download any video's audio, transcribe
  with Whisper, and answer questions. Supports 1750+ sites via yt-dlp.
  Works with any AI agent: Claude Code, Codex, ZCode, Cursor, etc.
---

# video-qa: Universal Video Content Q&A

Give it a video URL → downloads audio → transcribes with Whisper →
you ask questions about the content.

## Requirements

```bash
pip install yt-dlp openai-whisper torch
# Also need ffmpeg: winget install ffmpeg / brew install ffmpeg
```

The script auto-detects the correct Python environment.

## Quick Start

```bash
python video_qa.py <video-url>
python video_qa.py <video-url> --model small   # better accuracy
python video_qa.py <video-url> --lang en       # English video
python video_qa.py <video-url> --json           # JSON output
```

## Supported Platforms (1750+)

### 🇨🇳 China (direct access)

| Platform | Type | Notes |
|:---------|:-----|:------|
| **Bilibili** 🎬 | Video/Live/Courses | Fully tested ✅ |
| **Douyin** (抖音) | Short video | Needs 1-time cookie login |
| **Kuaishou** (快手) | Short video | |
| **Xiaohongshu** (小红书) | Video notes | |
| **Weibo** (微博) | Video/Live | |
| **Youku** (优酷) | Long video/Shows | |
| **iQiyi** (爱奇艺) | Long video/Shows | |
| **Tencent Video** (腾讯视频) | Long video/Shows | |
| **Mango TV** (芒果TV) | Variety/Shows | |
| **Xigua Video** (西瓜视频) | Mid-length video | |
| **Sohu Video** (搜狐视频) | Long video | |
| **AcFun** | Video/Anime | |
| **Huya** (虎牙) | Game live | |
| **Douyu** (斗鱼) | Game live | |
| **Zhihu** (知乎) | Video answers | |
| **WeChat Channels** (视频号) | Short video | |

### 🌐 Global (VPN needed for some)

| Platform | Type | Notes |
|:---------|:-----|:------|
| **YouTube** | Video/Shorts/Live | Needs VPN in CN |
| **Netflix** | Movies/Shows | |
| **HBO / Max** | Movies/Shows | |
| **Disney+** | Movies/Shows | |
| **Amazon Prime Video** | Movies/Shows | |
| **Apple TV+** | Movies/Shows | |
| **Hulu** | Shows/Variety | |
| **Paramount+** | Movies/Shows | |
| **Peacock** | Movies/Shows | |
| **Discovery+** | Documentaries | |
| **BBC iPlayer** | UK TV | |
| **ITV / Channel 4** | UK TV | |
| **TF1 / France TV** | French TV | |
| **RAI** | Italian TV | |
| **NHK / Fuji TV / TBS** | Japanese TV | |
| **CBC** | Canadian TV | |

### 📱 Social / Short Video

| Platform | Type |
|:---------|:-----|
| **TikTok** | Short video |
| **Instagram** | Video/Reels/Stories |
| **Facebook** | Video |
| **Twitter / X** | Video |
| **Snapchat** | Spotlight |
| **Reddit** | Video |
| **Pinterest** | Video |
| **LinkedIn** | Video |
| **Tumblr** | Video |

### 🎮 Live / Gaming

| Platform | Type |
|:---------|:-----|
| **Twitch** | Live/VOD/Clips |
| **Kick** | Live/VOD |
| **DLive** | Live/VOD |
| **Steam** | Broadcasts/Community |

### 📚 Education

| Platform |
|:---------|
| **Coursera, Udemy, Skillshare, MasterClass** |
| **Khan Academy, MIT OCW, Ted Talks** |
| **Pluralsight, Frontend Masters, Laracasts** |

### 🎵 Music / Podcasts

| Platform |
|:---------|
| **Spotify, SoundCloud, Bandcamp, Mixcloud** |
| **Apple Podcasts, BBC Radio, NPR** |
| **网易云音乐, QQ音乐** |

### 📺 News

| Platform |
|:---------|
| **BBC, CNN, NBC, ABC, CBS, FOX, NPR, PBS** |
| **Bloomberg, WSJ, NYTimes, Washington Post** |
| **Al Jazeera, France24, DW, CGTN** |
| **Sky News, The Guardian** |

## Cookie Login (for Douyin / Weibo / Twitter)

Some platforms require authentication:

```bash
cd C:/Users/windows/ZCodeProject/douyin-downloader
python tools/cookie_fetcher.py --output config/cookies.json
```
Opens a browser — scan QR code to login. Cookies persist for future use.

## Acknowledgments

This project builds on several amazing open-source projects:

| Project | Role | License |
|:--------|:-----|:--------|
| **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** | Core download engine (1750+ site extractors) | Unlicense |
| **[openai-whisper](https://github.com/openai/whisper)** | Speech-to-text model | MIT |
| **[jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader)** | Douyin cookie login reference | MIT |
| **[PyTorch](https://github.com/pytorch/pytorch)** | Whisper backend | BSD |
| **[FFmpeg](https://ffmpeg.org)** | Audio processing | LGPL/GPL |

## Output

```
🧠 Transcribing with whisper (small)...
  ⏱ Model loaded in 2.0s
  ⏱ Transcribed in 13.9s

Full transcript text...

---
### 📌 Timestamps
[00:00] First segment
[00:15] Second segment
```
