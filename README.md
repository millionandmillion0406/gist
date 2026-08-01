# link-distill — 扔链接，AI 自动蒸馏

把任意视频/图文链接扔过来，自动分析内容，提炼可复用的经验。

```
抖音、B站、YouTube、小红书、快手、微博、优酷、爱奇艺… 1200+ 平台通吃
```

## 快速开始（2 分钟）

1. 注册 [DeepSeek](https://platform.deepseek.com)（送免费额度），复制 API Key
2. 设置环境变量：

```bash
# Windows PowerShell
setx DEEPSEEK_API_KEY "你的key"
# macOS / Linux
export DEEPSEEK_API_KEY="你的key"
```

3. 扔链接：

```bash
python gist.py "https://v.douyin.com/xxxxx"
```

支持粘贴**平台分享口令**（"复制打开抖音…"整段文本直接扔进来，自动提取链接）。

## 用法

```bash
# 基本用法：自动判断图文还是视频
python gist.py "https://v.douyin.com/xxxxx"

# 只提取内容，不调用 AI（没有 API Key 也能用）
python gist.py "https://... " --extract-only

# 画面分析（本地 Ollama 视觉模型，可选）
python gist.py "https://..." --vision

# 使用自定义 API（中转站等任意 OpenAI 兼容服务）
python gist.py "https://..." --api-base "https://中转站/v1" --api-key "key" --model "模型名"
```

**没了，就这一行。** 链接扔进去，等几十秒，出来：你的想法 + 以后可以怎么做 + 有什么例子。

## 配置优先级

`命令行参数 / 配置文件` > `环境变量（DEEPSEEK_API_KEY / DEEPSEEK_API_BASE / DEEPSEEK_MODEL）` > `内置默认（DeepSeek 官方 deepseek-chat）`

零配置用户直接用官方默认；有自己 API 的用户覆盖即可。

## 演示

```bash
python gist.py "https://v.douyin.com/V6kMas01YWg/"
```

输出：

```
[下载]  3736KB
[FunASR]  2917 字
[AI]  1303 字
✅ 134s

## 核心洞察
(每条带"为什么成立 + 应用场景 + 反直觉点")
## 思维模型
## 怎么做
```

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
# 画面分析（可选，装一个就行，自动按质量排序选择）
ollama pull qwen2.5vl:3b   # 效果最好，推荐
ollama pull llava:7b       # 老模型，当备用
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

## 桌面版（实验性）

社区贡献的 Windows 图形界面在 [`gui/`](gui/) 目录（WebView2 + pywebview）。
当前为实验性状态，登录功能未实现，不参与 CI 发布。核心功能请用 CLI。

## 开源协议

[MIT](LICENSE)

## 贡献

你的 issue 比 star 更重要。提需求、报 bug、交 PR 都欢迎。
