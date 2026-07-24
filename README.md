# gist — 视频内容分析

一条命令，全自动。扔链接，聊内容。

```bash
python gist.py <B站/抖音/YouTube/任何视频链接>
```

自动完成：下载 → 听写 → AI纠错 → 结构化分析

然后直接跟我聊这个视频的内容。

## 依赖

```bash
pip install yt-dlp openai-whisper torch
```

## 原理

```
链接 → yt-dlp（1200站）→ 音频 → Whisper → DeepSeek AI → 结构化分析 → 聊
```
