---
name: gist
description: >
  扔视频/图文链接，自动分析、总结拆解、提取可复用知识。
  支持 1200+ 平台：B站、抖音、YouTube、小红书、快手……
  任何 AI Agent 都能用（Claude Code、Codex、ZCode、OpenClaw、Cursor）。
---

# gist — 和 AI 一起从视频中学

用户给你一个视频链接时，按这个流程走。

## 安装

```bash
# 克隆
git clone https://github.com/millionandmillion0406/gist.git ~/gist
cd ~/gist

# 装依赖
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg          # Windows
# brew install ffmpeg          # Mac

# 可选：画面分析（--vision）
# ollama pull llava:7b
```

## 用法

```bash
# 视频/音频分析
python gist.py <视频链接>

# 加画面分析
python gist.py <视频链接> --vision

# 抖音图文
python gist.py <抖音图文链接> --note
```

## 输出

运行后自动保存到 `last_analysis.json`，同时打印结构化分析：
- 核心主题 / 校正全文
- 思维模型/框架 / 原则规则
- 案例 / 边界注意 / 可执行步骤

你自己读一下，然后和用户讨论内容。

## 依赖清单

| 工具 | 用途 | 获取 |
|:-----|:-----|:------|
| yt-dlp | 视频下载 | pip install yt-dlp |
| FunASR | 中文语音识别 | pip install funasr |
| openai-whisper | 语音识别（兜底）| pip install openai-whisper torch |
| ffmpeg | 音视频处理 | winget/brew install |
| playwright | 抖音图文提取（--note）| pip install playwright + playwright install chromium |

## 参考

- VideoContextEngine — 场景检测
- cangjie-skill — 结构化蒸馏方法论
- FunASR — 阿里通义中文语音识别
- yt-dlp — 视频下载引擎
