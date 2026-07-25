# gist — 和 AI 一起从视频中学

```
你扔链接 → AI 自动分析 → 结构化蒸馏 → 你们一起讨论 → 学到东西
```

## 一条命令

```bash
python gist.py <链接>
python gist.py <链接> --vision   # 加画面分析
```

## 全流程

```
📥 下载 — yt-dlp，1200+ 平台
🎤 转录 — FunASR（中文优先）→ Whisper 兜底
👁️ 视觉 — 场景检测 + Ollama/AutoGLM 画面分析（--vision）
🧠 蒸馏 — 3 提取器并行：纠错 + 框架 + 洞察
💬 讨论 — 你和 AI 一起聊内容
```

## 需要装什么

### 核心依赖

| 工具 | 用途 | 获取方式 |
|:-----|:-----|:---------|
| **Python 3.10+** | 运行环境 | python.org 或 winget install python |
| **yt-dlp** | 视频/音频下载 | pip install yt-dlp |
| **FunASR** | 中文语音识别（阿里通义） | pip install funasr |
| **openai-whisper** | 语音识别兜底 | pip install openai-whisper torch |
| **ffmpeg** | 音视频处理 | winget install ffmpeg |

### 画面分析（可选 --vision）

本地方案（二选一）：
- **Ollama + llava**：ollama pull llava:7b（4.7GB）
- **Ollama + minicpm-v4.6**：ollama pull minicpm-v4.6（1.3GB）

云端方案（无需安装，首次运行自动检测）：
- **AutoGLM 图片识别**（需智谱 API 环境）

### 图文分析（可选）

| 工具 | 用途 | 获取方式 |
|:-----|:-----|:---------|
| **playwright** | 浏览器自动化 | pip install playwright + playwright install chromium |

### 录音频分析（抖音等需登录平台）

| 工具 | 用途 | 获取方式 |
|:-----|:-----|:---------|
| **douyin-downloader** | 抖音 cookie 获取 | git clone https://github.com/jiji262/douyin-downloader.git |

## 一键安装

```bash
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg
# 画面分析（可选）
ollama pull llava:7b
```

## 参考与致谢

本项目在开发过程中参考了以下开源项目：

| 项目 | ⭐ | 借鉴了什么 |
|:-----|:-:|:-----------|
| **[VideoContextEngine](https://github.com/dolphin-creator/VideoContext-Engine)** | 34 | HSV 场景检测、视觉分析管线设计 |
| **[cangjie-skill](https://github.com/kangarooking/cangjie-skill)** | 4.6K | 多提取器并行蒸馏、RIA-TV++ 方法论 |
| **[FunASR](https://github.com/modelscope/FunASR)** | 19K | 中文语音识别模型（阿里通义） |
| **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** | 100K+ | 视频/音频下载引擎 |
| **[jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader)** | 9K | 抖音登录 cookie 获取参考 |
| **[openai-whisper](https://github.com/openai/whisper)** | 75K+ | 语音识别兜底方案 |

## 输出示例

```
🧠 AI 分析中（3 提取器并行）...

## 📌 核心主题
[一句话概括]

## 📝 校正全文
[纠错后的完整文本]

## 🧠 思维模型/框架
- ...

## 📏 原则/规则
- ...

## 📖 案例
- ...

## ⚠️ 边界/注意
- ...

## 💡 可执行步骤
- ...
```
