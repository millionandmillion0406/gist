---
name: gist
description: >
  扔视频链接，下载音频，转文字，你随便问。
  支持 1750+ 网站。任何 Agent 都能用。
---

# gist: 视频内容问答

## 原理

```
你给链接 → yt-dlp 下载音频 → Whisper 转文字 → 你随便问
```

yt-dlp 内置了 1750 个网站的提取器，每个提取器知道对应网站的视频藏在哪里、怎么下。Whisper 是 OpenAI 的语音识别模型，把音频转成文字。两个都是成熟的开源项目，我只需要把它们串起来。

## 装啥

```bash
pip install yt-dlp openai-whisper torch
# 还要装 ffmpeg: winget install ffmpeg
```

脚本自动找 Python 环境。

## 咋用

```bash
python gist.py <链接>
python gist.py <链接> --model small   # 更准
python gist.py <链接> --lang en       # 英文
python gist.py <链接> --json          # JSON 输出
```

## 支持哪些站

### 国内
B站、抖音（需登录）、快手、小红书、微博、优酷、爱奇艺、腾讯视频、
芒果TV、西瓜视频、搜狐、AcFun、虎牙、斗鱼、知乎、视频号……

### 国外主流
YouTube、Netflix、HBO、Disney+、Amazon Prime、Apple TV+、
Hulu、BBC iPlayer、TikTok、Instagram、Facebook、Twitter/X、
Twitch、Reddit、Spotify、SoundCloud、Vimeo、Dailymotion……

### 成人（大部分）
PornHub、XVideos、XNXX、xHamster、YouPorn、RedTube、Tube8、
SpankBang、TNAFlix、Chaturbate、Stripchat、BongaCams、
ManyVids、Eporner、Txxx、XXXYMovies……以及其他几十个。

### 学习
Coursera、Udemy、Khan Academy、MasterClass、Ted Talks……

## 📖 jm2pdf — JM 本号 → 压缩 PDF → 邮箱

另一条线：输入 JM 漫画本号，自动下载、压缩、生成 PDF，发到 QQ 邮箱。

```bash
python jm2pdf.py 123456           # 下载 JM123456 并发邮件
python jm2pdf.py JM289490         # JM 前缀也行
python jm2pdf.py 123456 --no-send # 只生成 PDF，不发邮件
```

依赖：`pip install jmcomic img2pdf Pillow`

## 抖音登录

```bash
cd douyin-downloader
python tools/cookie_fetcher.py --output config/cookies.json
```
弹浏览器，扫码登录一次，之后不用再登。

## 用到了啥

| 项目 | 干啥的 |
|:-----|:-------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 1750 个网站的视频/音频下载 |
| [openai-whisper](https://github.com/openai/whisper) | 语音转文字 |
| [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader) | 抖音登录参考 |
| PyTorch + FFmpeg | 跑模型 + 处理音频 |
