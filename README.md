# gist — 和 AI 一起从视频中学

扔链接，AI 自动拆解精华，你和 AI 一起消化、复用。

```bash
python gist.py <链接>
python gist.py <链接> --vision   # 加画面分析
```

## 凭什么选 gist

### 🌍 1200+ 平台，一个命令通吃
国内 B站、抖音、快手、小红书、微博、优酷、爱奇艺、腾讯视频……
国外 YouTube、Netflix、TikTok、Instagram、Twitter/X、Twitch、Vimeo……
**只有 gist 覆盖这么全，别的工具大多只支持 YouTube 或 B站。**

### 🔁 不只是转文字，是"蒸馏"
别的工具：告诉你了"这个视频讲了什么"
gist：拆出了**模型、原则、案例、边界、步骤**——你和 AI 可以直接拿来用。

### 🖼️ 抖音图文也能读
不只看视频，抖音图文帖子也能提取内容，市面上独一份。

### 👁️ 画面也分析（可选）
装个 Ollama，或者用云端，gist 能"看"视频画面描述内容。

## 管线

```
📥 下载 — yt-dlp，1200+ 平台
🎤 转录 — FunASR（中文场景最优）→ Whisper 兜底
👁️ 视觉 — 场景检测 + 画面分析（--vision）
🧠 蒸馏 — 3 个提取器并行跑：纠错 / 框架 / 洞察
💬 讨论 — 你和 AI 一起聊、一起学
```

## 装什么

```bash
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg
# 画面分析（可选）
ollama pull llava:7b
```

## 输出长这样

```
## 📌 核心主题
[一句话]

## 📝 校正全文
[纠错后的文本]

## 🧠 思维模型/框架
- ...

## 📏 原则/规则
- ...

## 📖 案例
- ...

## ⚠️ 边界/注意
- ...

## 💡 可执行步骤
- ...          ← 直接拿去用
```

## 参考项目

| 项目 | 借鉴了什么 |
|:-----|:-----------|
| **VideoContextEngine** | HSV 场景检测 |
| **cangjie-skill** | 多提取器并行蒸馏 |
| **FunASR** | 阿里通义中文语音识别 |
| **yt-dlp** | 视频/音频下载引擎 |
| **jiji262/douyin-downloader** | 抖音登录参考 |
