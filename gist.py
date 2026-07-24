#!/usr/bin/env python3
"""gist — 全平台视频内容分析。一条命令，自动干完。"""

import argparse, json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path

WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
COOKIES = Path(__file__).parent / "douyin_cookies.txt"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY") or "sk-9a32ad9e076e4af48cb6d8b42e539c93"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 找 Python
PY = sys.executable
for c in [sys.executable, r"C:\Users\windows\AppData\Local\Programs\Python\Python312\python.exe"]:
    if subprocess.run([c, "-c", "import whisper"], capture_output=True).returncode == 0:
        PY = c; break


def sh(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def main():
    ap = argparse.ArgumentParser(description="gist — 全平台视频分析")
    ap.add_argument("url", help="视频链接")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    vid = "video"

    # 1. 下载音频
    print("📥 下载中...", flush=True)
    audio = WORK_DIR / f"{vid}.mp3"
    sh(["yt-dlp", *( ["--cookies", str(COOKIES)] if COOKIES.exists() else []),
        "-x", "--audio-format", "mp3", "-o", str(audio), "--no-playlist", args.url])
    if not audio.exists():
        print("❌ 下载失败"); sys.exit(1)

    # 2. 转录
    print("🎤 听写中...", flush=True)
    code = f"import whisper; r=whisper.load_model('base').transcribe(r'{audio}', language='zh', verbose=False); print(r['text'])"
    _, text, _ = sh([PY, "-c", code], timeout=1800)
    text = text.strip()

    # 3. AI 分析
    print("🧠 AI 分析中...", flush=True)
    prompt = f"""你是一个视频内容蒸馏助手。下面是一段视频的语音识别结果。

请做两件事：

**一、纠错**：修正错别字和不通顺的地方。

**二、结构化提取**：像专业分析师一样，从内容里拆出以下东西（没有的就不写）：

1. **🧠 思维模型/框架** — 视频里提到的思考方法、决策框架、分析模型
2. **📏 原则/规则** — 明确提出的"应该/不应该"的断言、判断标准
3. **📖 案例** — 作者亲自用过的具体例子
4. **⚠️ 边界/注意** — 提到的限制条件、反例、容易出错的地方
5. **💡 可执行步骤** — 可以直接照着做的操作流程
6. **📌 核心主题** — 一句话概括

**关键是：不要说"这个视频讲了什么"，而是拆出"这里面有什么可以用的"。**

识别结果：
{text}

按这个格式输出：

## 📌 核心主题
[一句话]

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
- ..."""
    data = json.dumps({"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096}).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=data, headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    analysis = ""
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        analysis = resp["choices"][0]["message"]["content"]
    except Exception as e:
        analysis = f"⚠ AI分析失败: {e}\n\n{text}"

    # 4. 保存 + 输出
    result = {"text": text, "analysis": analysis, "elapsed": f"{time.time()-t0:.0f}s"}
    Path(Path(__file__).parent / "last_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"  gist 分析完成 ⏱ {result['elapsed']}")
        print(f"{'='*50}\n{analysis}\n{'='*50}\n  现在我们可以聊这个视频了 👊\n{'='*50}")

    # 清理
    audio.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
