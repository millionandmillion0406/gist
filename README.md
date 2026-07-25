# gist — 和 AI 一起从视频中学

**最简单用法：把这个仓库丢给你的 AI Agent，它自己会搞定。**

```text
帮我把这个仓库装好：
https://github.com/millionandmillion0406/gist
```

Claude Code、Codex、ZCode、OpenClaw、Cursor……任何 AI 编码 Agent 都能直接理解这个项目。

## 一条命令

```bash
python gist.py <链接>
python gist.py <链接> --vision   # 加画面分析
```

## 凭什么选 gist

**🌍 1200+ 平台** — B站、抖音、YouTube、Netflix、小红书……市面上主流平台全支持。别的工具大多只支持一两个。

**🔁 不是转文字，是蒸馏** — 拆出模型、原则、案例、边界、步骤，你和 AI 可以直接拿来用。

**🖼️ 抖音图文也能读** — 不只看视频，图文帖子一样处理。

**👁️ 画面分析** — 装个 Ollama 就能让 AI 看懂画面内容（可选）。

## 对人类用户

```bash
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg
python gist.py https://www.bilibili.com/video/BVxxx
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

VideoContextEngine、cangjie-skill、FunASR、yt-dlp、jiji262/douyin-downloader
