---
name: video-qa
description: >
  扔视频链接，下载音频，转文字，你随便问。
  支持 1750+ 网站。任何 Agent 都能用。
---

# video-qa: 视频内容问答

扔链接 → 下载音频 → Whisper 转文字 → 你问啥我答啥

## 装啥

```bash
pip install yt-dlp openai-whisper torch
# 还要装 ffmpeg: winget install ffmpeg
```

脚本会自动找 Python 环境，不用配置。

## 咋用

```bash
python video_qa.py <视频链接>
python video_qa.py <视频链接> --model small    # 更准但慢点
python video_qa.py <视频链接> --lang en        # 英文视频
python video_qa.py <视频链接> --json            # JSON 输出
```

## 支持哪些站

### 国内（直连）

B站、抖音、快手、小红书、微博、优酷、爱奇艺、腾讯视频、
芒果TV、西瓜视频、搜狐、AcFun、虎牙、斗鱼、知乎、视频号……

> 抖音需要先跑一次 cookie 登录

### 国外（部分需代理）

YouTube、Netflix、HBO、Disney+、Amazon Prime、Apple TV+、
Hulu、BBC iPlayer、TikTok、Instagram、Facebook、Twitter、
Twitch、Reddit、Spotify、SoundCloud……

### 学习

Coursera、Udemy、Khan Academy、MasterClass、Ted Talks……

**总共 1750+ 个网站，都是 yt-dlp 在维护，不用我操心。**

## 抖音登录

有些站要登录才能下（抖音、微博等）：

```bash
cd douyin-downloader
python tools/cookie_fetcher.py --output config/cookies.json
```
会弹浏览器，扫码登录，之后就不用再登了。

## 用到了啥

| 项目 | 干啥的 |
|:-----|:-------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 下载视频/音频（核心） |
| [openai-whisper](https://github.com/openai/whisper) | 语音转文字 |
| [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader) | 抖音登录参考 |
| PyTorch + FFmpeg | 跑模型 + 处理音频 |
