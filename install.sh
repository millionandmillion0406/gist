#!/usr/bin/env bash
# gist 一键安装脚本
set -e

echo "📦 安装 gist 依赖..."

# Python 包
echo "  🐍 Python 包..."
pip install yt-dlp openai-whisper torch funasr 2>&1 | tail -1

# ffmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo "  🎬 ffmpeg..."
  winget install ffmpeg 2>/dev/null || brew install ffmpeg 2>/dev/null || echo "  ⚠ 请手动安装 ffmpeg"
fi

# Ollama（可选）
if ! command -v ollama &>/dev/null; then
  echo "  🦙 Ollama（可选，用于画面分析）..."
  echo "    去 https://ollama.com/download 安装"
fi

echo ""
echo "✅ 安装完成"
echo "运行: python gist.py <视频链接>"
