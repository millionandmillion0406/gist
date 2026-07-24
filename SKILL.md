---
name: gist
description: >
  用户扔视频链接 → 你自动分析内容 → 和用户讨论。
  一条命令，不用用户操心的全自动流程。
---

# gist: 视频内容分析工作流

用户给你一个视频链接时，按这个流程走。

## 第一步：下载 + 转录

```bash
python gist.py <链接>
```

这步自动完成：
- 下载音频 → Whisper 转文字
- 下载视频 → OCR 读画面文字
- DeepSeek AI 纠错 + 结构化分析
- 输出保存到 `last_analysis.json`

## 第二步：你自己看结果

运行完后，自己读 `last_analysis.json` 里的内容。

## 第三步：和用户讨论

基于分析结果，主动和用户交流，不要只丢文本。

好的交流方式：
- 先给一个一句话概括
- 再问用户想深入了解哪个点
- 或者直接提出你的观察和疑问

## 原理

```
链接 → yt-dlp（1200站）→ 音频 + 视频
     → Whisper（语音→文字）
     → EasyOCR（画面文字）
     → DeepSeek AI（纠错+结构化分析）
     → 你和用户聊
```

## 依赖

```bash
pip install yt-dlp openai-whisper torch easyocr
winget install ffmpeg
# DeepSeek API key 已配好
```
