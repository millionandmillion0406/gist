---
name: gist
description: 从任何视频链接中提取结构化知识。用户扔链接 → 你分析 → 讨论。
---

# gist — 和 AI 一起从视频中学

用户给你一个链接时，按这个流程走。

## 怎么装

```bash
pip install yt-dlp openai-whisper torch funasr
winget install ffmpeg
```

有 AI 帮我装就行，不用用户操心。

## 怎么用

```bash
cd <gist目录>
python gist.py "<用户给的链接>"
```

输出保存在 `last_analysis.json`，你自己读一下，然后和用户讨论内容。

输出结构：
- 📌 核心主题 — 一句话概括
- 📝 校正全文 — 纠错后的文本
- 🧠 思维模型/框架 — 可迁移的思考结构
- 📏 原则/规则 — 可以直接用的判断标准
- 📖 案例 — 实际操作经验
- ⚠️ 边界/注意 — 容易翻车的地方
- 💡 可执行步骤 — 能照着做的

## 可选功能

| 功能 | 命令 | 需要装 |
|:-----|:-----|:-------|
| 画面分析 | `--vision` | `ollama pull llava:7b` |
| 抖音图文 | `python douyin_note.py <链接>` | `pip install playwright` + `playwright install chromium` |
| 抖音登录 | `python douyin_login.py` | 扫码登录（仅需一次） |

## 原理

```
链接 → yt-dlp（1200+站）→ 音频 → FunASR/Whisper → 3提取器蒸馏 → 你俩聊
```
