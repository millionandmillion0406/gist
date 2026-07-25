---
name: gist
description: 扔视频链接，AI自动分析、总结拆解，然后你和AI一起交流学习。
---

# gist: 和 AI 一起从视频中学

用户扔视频链接 → 你跑 gist → 一起讨论

## 一条命令

```bash
python gist.py <链接>
python gist.py <链接> --vision   # 加画面分析
```

## 管线

下载（yt-dlp）→ 转录（FunASR/Whisper）→ 视觉分析（可选）→ AI蒸馏（3提取器并行）→ 讨论

## 在哪

```
C:\Users\windows\ZCodeProject\video-qa\
├── gist.py       ← 主程序
├── douyin_note.py ← 抖音图文提取
├── douyin_login.py ← 抖音登录脚本
├── README.md     ← 给人看的说明
└── SKILL.md      ← 给你看的说明
```

## 参考项目

- VideoContextEngine — 场景检测
- cangjie-skill — 多提取器蒸馏
- FunASR — 阿里通义中文语音识别
- yt-dlp — 视频下载
- jiji262/douyin-downloader — 抖音登录
