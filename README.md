# link-distill — AI 视频内容蒸馏工具

> **视频分析 · 语音转文字 · 内容蒸馏 · 知识提取 · 多平台下载**
> 支持 B站、抖音、YouTube、小红书、快手、微博、优酷、爱奇艺等 1200+ 平台

扔链接，AI 自动拆解精华，你和 AI 一起消化、复用。

```bash
python link-distill.py <链接>
python link-distill.py <链接> --vision   # 加画面分析
```

**最简单用法：把这个仓库丢给你的 AI Agent，它自己会搞定。**

---

## 凭什么选 link-distill

### 🌍 1200+ 平台，一个命令通吃
别的工具：只支持 YouTube，最多加个 B站
link-distill：B站、抖音、快手、小红书、微博、优酷、爱奇艺、腾讯视频、YouTube、Netflix、TikTok……

### 🔁 不是转文字，是"蒸馏"
别的工具：给你一段逐字稿
link-distill：拆出**思维模型、原则、案例、边界、可执行步骤**——你和 AI 可以直接拿来用

### 🖼️ 抖音图文也能读
别的工具：只能处理视频
link-distill：图文帖子一样提取内容

### 👁️ 画面也分析
别的工具：纯音频转录
link-distill：装个 Ollama 就能让 AI 看懂画面内容（可选）

### 🤖 任何 Agent 都能用
别的工具：绑定特定平台
link-distill：Claude Code、Codex、ZCode、OpenClaw、Cursor……全兼容

---

## 竞品对比

| 功能 | **link-distill** | BiliNote | video-parse-transcribe | cangjie-skill |
|:-----|:--------:|:--------:|:----------------------:|:-------------:|
| 平台数 | **1200+** | 3 | 20+ | 0（需外部输入）|
| 音频转录 | ✅ FunASR+Whisper | ✅ Whisper | ✅ Whisper tiny | ❌ |
| 画面分析 | ✅ 可选 | ✅ | ❌ | ❌ |
| 结构化蒸馏 | ✅ 5 维度 | ⚠️ 笔记 | ❌ | ✅ RIA-TV++ |
| 抖音图文 | ✅ | ❌ | ❌ | ❌ |
| AI 纠错 | ✅ DeepSeek | ❌ | ⚠️ 基础 | ❌ |
| 场景检测 | ✅ HSV | ❌ | ❌ | ❌ |
| 安装复杂度 | pip 搞定 | Docker 全家桶 | pip | skill 文件 |
| CLI 支持 | ✅ | ❌ Web/桌面 | ✅ | ❌ |
| 跨 Agent | ✅ | ❌ | ✅ | ✅ |

---

## 管线

```
📥 yt-dlp 下载（1200+平台）
   ↓
🎤 FunASR 转录（中文场景最优）→ Whisper 兜底
   ↓
👁️ HSV 场景检测 + 视觉分析（--vision）
   ↓
🧠 DeepSeek AI 结构化蒸馏
   ↓
💬 你和 AI 一起聊、一起学
```

## 装什么

```bash
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg
# 画面分析（可选）
ollama pull llava:7b
```

## 输出

```
## 📌 核心主题
## 📝 校正全文
## 🧠 思维模型/框架
## 📏 原则/规则
## 📖 案例
## ⚠️ 边界/注意
## 💡 可执行步骤  ← 直接拿去用
```

## 致谢

VideoContextEngine（场景检测）、cangjie-skill（蒸馏方法论）、FunASR（中文语音识别）、yt-dlp（视频下载）、jiji262/douyin-downloader（抖音登录参考）
