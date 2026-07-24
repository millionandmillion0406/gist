# gist — 取视频的精要

[![Release](https://img.shields.io/github/v/release/millionandmillion0406/gist)](https://github.com/millionandmillion0406/gist/releases)
[![License](https://img.shields.io/github/license/millionandmillion0406/gist)](LICENSE)

**扔个链接，30 秒看懂一个视频。** 任何 AI Agent 都能用。

```
你给视频链接 → 下载音频 → Whisper 转文字 → 你随便问
```

## ✨ 功能

- 🎤 **音频转录** — Whisper 语音识别，支持 1200+ 网站
- 👁️ **画面 OCR** — EasyOCR 读取视频字幕/文字
- 📖 **jm2pdf** — 输入 JM 本号，自动下载漫画、压缩 PDF、发到邮箱
- 🤖 **跨 Agent** — Claude Code / Codex / ZCode / Cursor 通用

## 🌐 支持平台

**国内**：B站、抖音、快手、小红书、微博、优酷、爱奇艺、腾讯视频、芒果TV、AcFun、虎牙、斗鱼、知乎……

**国外**：YouTube、Netflix、HBO、Disney+、TikTok、Instagram、Twitter/X、Twitch、Vimeo……

**学习**：Coursera、Udemy、Khan Academy、Ted Talks……

## ⚡ 快速开始

```bash
# 装依赖
pip install yt-dlp openai-whisper torch easyocr
winget install ffmpeg

# 视频转文字
python gist.py https://www.bilibili.com/video/BVxxx

# 同时识别画面文字
python gist.py https://www.bilibili.com/video/BVxxx --ocr

# JM 漫画下载
python jm2pdf.py 123456
```

## 🧠 原理

```
链接 → yt-dlp（1200站提取器）→ 下载音频/视频
     → Whisper（语音→文字）→ 全文 + 时间戳
     → EasyOCR（画面文字识别）→ 互补音频盲区
     → 你随便问
```

## 📦 仓库内容

| 文件 | 说明 |
|:-----|:------|
| `gist.py` | 主程序：视频内容问答 |
| `jm2pdf.py` | JM 漫画下载转 PDF |
| `SKILL.md` | AI Agent 使用说明 |
| `PROMOTE.md` | 推广文案模板 |

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 1200+ 网站视频下载引擎
- [openai-whisper](https://github.com/openai/whisper) — 语音识别
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — 画面文字识别
- [jmcomic](https://github.com/hect0x7/JMComic-Crawler-Python) — 漫画下载
