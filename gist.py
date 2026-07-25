#!/usr/bin/env python3
"""
gist — 扔视频链接，AI自动分析、总结拆解、然后和你交流。

流程：下载 → 转录 → 场景检测 → 视觉分析 → AI蒸馏 → 讨论
"""

import argparse, hashlib, json, mimetypes, os, subprocess, sys, time, urllib.request, uuid
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

AUTOGLM_APP_ID = "100003"
AUTOGLM_APP_KEY = "38d2391985e2369a5fb8227d8e6cd5e5"
AUTOGLM_TOKEN_URL = "http://127.0.0.1:18432/get_token"
AUTOGLM_UPLOAD_URL = "https://autoglm-api.zhipuai.cn/agentdr/v1/assistant/upload-mix"
AUTOGLM_RECOG_URL = "https://autoglm-api.zhipuai.cn/agentdr/v1/assistant/images-recognition"


def sh(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def dl_cmd(url, extra=None):
    cmd = ["yt-dlp"]
    if COOKIES.exists(): cmd += ["--cookies", str(COOKIES)]
    if extra: cmd += extra
    cmd += [url]
    return cmd


# ── 1. 下载 ──

def download(url):
    print("📥 下载中...", flush=True)
    audio = WORK_DIR / "a.mp3"
    sh(dl_cmd(url, ["-x", "--audio-format", "mp3", "-o", str(audio), "--no-playlist"]))
    if not audio.exists():
        print("❌ 下载失败"); sys.exit(1)
    return audio


# ── 2. 转录 ──

def transcribe(audio_path):
    print("🎤 听写中...", flush=True)
    code = f"import whisper; m=whisper.load_model('base'); r=m.transcribe(r'{audio_path}',language='zh',verbose=False); print(r['text'])"
    rc, out, _ = sh([PY, "-c", code], timeout=1800)
    return out.strip() if rc == 0 else ""


# ── 3. 视觉分析（AutoGLM 云端识别）──

AUTOGLM_SKILL_DIR = Path("C:/Users/windows/.openclaw-autoclaw/skills/autoglm-image-recognition")

def analyze_frame_auto(frame_path):
    """用 AutoGLM 识别画面内容"""
    try:
        # 上传
        r1 = subprocess.run([PY, str(AUTOGLM_SKILL_DIR / "upload-mix.py"), str(frame_path)],
            capture_output=True, text=True, timeout=30)
        if r1.returncode != 0: return ""
        url = json.loads(r1.stdout)["data"]["oss_info"][0]["oss_url"]

        # 识别
        r2 = subprocess.run([PY, str(AUTOGLM_SKILL_DIR / "image-recognition.py"), url],
            capture_output=True, text=True, timeout=30)
        if r2.returncode != 0: return ""
        return json.loads(r2.stdout)["data"]["text"][:100]
    except Exception as e:
        return ""


def visual_analysis(video_path, duration):
    """每隔 30 秒分析一帧画面"""
    if not video_path or duration <= 0: return []
    print("👁️ 分析画面...", flush=True)
    results = []
    for ts in range(0, min(int(duration), 300), 30):  # 最多看 5 分钟
        frame = WORK_DIR / f"f{ts:04d}.jpg"
        subprocess.run(["ffmpeg", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(frame)],
            capture_output=True, timeout=30)
        if frame.exists():
            desc = analyze_frame_auto(frame)
            if desc: results.append({"time": f"{ts}s", "desc": desc})
            frame.unlink()
    return results


# ── 4. AI 蒸馏 ──

def distill(transcript, vision=None):
    if not transcript.strip():
        return "⚠ 未检测到语音内容"
    print("🧠 AI 分析中...", flush=True)

    vis = ""
    if vision:
        vis = "\n画面内容：\n" + "\n".join([f"[{v['time']}] {v['desc']}" for v in vision])

    prompt = f"""你是一个视频内容蒸馏助手。下面是一段视频的语音识别结果{vis}。
请：1.纠错 2.提取结构化内容（模型/框架、原则、案例、边界、步骤、主题）
识别结果：
{transcript}{vis}"""

    data = json.dumps({"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4096}).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=data,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ AI分析失败: {e}\n\n{transcript}"


# ── 主流程 ──

def main():
    ap = argparse.ArgumentParser(description="gist — 全平台视频分析")
    ap.add_argument("url", help="视频链接")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--vision", action="store_true", help="启用画面分析（需 Ollama + 视觉模型）")
    args = ap.parse_args()

    t0 = time.time()

    # 1. 下载
    audio = download(args.url)
    print(f"  ✅ {audio.stat().st_size//1024}KB", flush=True)

    # 2. 转录
    text = transcribe(audio)
    audio.unlink()

    # 3. 视觉（可选）
    vision = []
    if args.vision:
        print("📥 下载视频...", flush=True)
        video = WORK_DIR / "v.mp4"
        sh(dl_cmd(args.url, ["-f", "bv+ba/b", "-o", str(video), "--no-playlist", "--merge-output-format", "mp4"]))
        dur = 0
        rc, out, _ = sh(dl_cmd(args.url, ["--print", "%(duration)s", "--no-playlist"]))
        if rc == 0:
            try: dur = float(out.strip())
            except: pass
        if video.exists() and dur > 0:
            vision = visual_analysis(video, dur)
            video.unlink()

    # 4. AI 蒸馏
    analysis = distill(text, vision)
    elapsed = f"{time.time()-t0:.0f}s"

    # 5. 保存 + 输出
    result = {"text": text, "analysis": analysis, "vision": vision, "elapsed": elapsed}
    (Path(__file__).parent / "last_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"  gist 完成 ⏱ {elapsed}")
        if vision:
            for v in vision:
                print(f"  👁️ [{v['time']}] {v['desc'][:60]}")
        print(f"{'='*50}\n{analysis}\n{'='*50}\n  来聊这个视频 👊\n{'='*50}")


if __name__ == "__main__":
    main()
