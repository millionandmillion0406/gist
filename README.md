# gist — 取视频的精要

**扔个链接，3 秒看懂一个视频。**

```
你给视频链接 → 下载音频 → Whisper 转文字 → 你随便问
```

## 它能干嘛

```bash
# 视频转文字
python gist.py https://www.bilibili.com/video/BVxxx

# 同时识别画面文字
python gist.py https://www.bilibili.com/video/BVxxx --ocr

# 英语视频
python gist.py https://www.youtube.com/watch?v=xxx --lang en

# JSON 输出
python gist.py https://www.bilibili.com/video/BVxxx --json
```

## 支持哪些站

**国内**：B站、抖音、快手、小红书、微博、优酷、爱奇艺、腾讯视频、芒果TV、AcFun、虎牙、斗鱼……

**国外**：YouTube、Netflix、HBO、TikTok、Instagram、Twitter/X、Twitch、Vimeo、Dailymotion……

**学习**：Coursera、Udemy、Khan Academy、Ted Talks、MasterClass……

**成人**：PornHub、XVideos、xHamster、YouPorn……

**总计 1200+ 网站**，全部一条命令搞定。

## 装啥

```bash
pip install yt-dlp openai-whisper torch
# OCR 的话再加：
pip install easyocr
# 还要装 ffmpeg
winget install ffmpeg
```

## 还有一条线

同一目录下还有个 `jm2pdf.py` — 输入 JM 本号，自动下载漫画、压缩、生成 PDF，发到 QQ 邮箱。

```bash
python jm2pdf.py 123456
```

## 原理

```
视频链接 → yt-dlp（1200站提取器）→ 下载音频
       → Whisper（语音转文字）→ 全文 + 时间戳
       → EasyOCR（画面文字识别）→ 互补音频盲区
       → 你随便问
```

## 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 下载引擎
- [openai-whisper](https://github.com/openai/whisper) — 语音识别
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — 画面文字识别
- [jmcomic](https://github.com/hect0x7/JMComic-Crawler-Python) — 漫画下载
