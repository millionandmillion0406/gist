#!/usr/bin/env python3
"""
gist — 扔视频链接，AI自动分析、总结拆解、然后和你交流。

流程：下载 → 转录 → 场景检测 → 视觉分析 → AI蒸馏 → 讨论
"""

import argparse, json, os, subprocess, sys, time, urllib.request, shutil, base64
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

# 检测可用能力
HAS_CV = subprocess.run([PY, "-c", "import cv2"], capture_output=True).returncode == 0
HAS_VLM = False
r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
if "qwen3" in (r.stdout or "") or "minicpm" in (r.stdout or ""):
    HAS_VLM = True


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


# ── 3. 场景检测 + 视觉分析 ──

def detect_scenes(video_path, threshold=0.3, min_dur=2, max_dur=60):
    """HSV 直方图场景检测 - 来自 VideoContextEngine"""
    if not HAS_CV: return []
    code = f"""
import cv2, json, numpy as np
cap = cv2.VideoCapture(r"{video_path}")
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
interval = int(fps)
scenes = []
last_hist = None
start = 0.0
prev = 0.0
idx = 0
while True:
    ret, frame = cap.read()
    if not ret: break
    if idx % interval == 0:
        now = idx / fps
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv],[0,1],None,[50,60],[0,180,0,256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        hist = hist.flatten()
        change = False
        if last_hist is not None:
            score = cv2.compareHist(last_hist, hist, cv2.HISTCMP_CORREL)
            if (1.0 - score) > {threshold}: change = True
        if (change and (now - start) >= {min_dur}) or (now - start) >= {max_dur}:
            scenes.append({{"start": start, "end": prev}})
            start = now
        last_hist = hist
        prev = now
    idx += 1
if prev > start: scenes.append({{"start": start, "end": prev}})
cap.release()
print(json.dumps(scenes, ensure_ascii=False))
"""
    rc, out, _ = sh([PY, "-c", code], timeout=300)
    if rc != 0 or not out.strip(): return []
    try: return json.loads(out.strip())
    except: return []


def analyze_scene(video_path, scene, vlm_model="qwen3-vl:2b"):
    """用 VLM 分析一个场景的关键帧"""
    if not HAS_VLM: return ""
    ts = scene["start"] + (scene["end"] - scene["start"]) / 2
    frame = WORK_DIR / "kf.jpg"
    sh(["ffmpeg", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(frame)], timeout=30)
    if not frame.exists(): return ""

    b64 = base64.b64encode(frame.read_bytes()).decode()
    frame.unlink()

    data = json.dumps({"model": vlm_model, "prompt": "简短描述这个画面", "images": [b64], "stream": False}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
        return resp.get("response", "").strip()
    except:
        return ""


def visual_analysis(video_path, duration):
    """场景检测 + 视觉分析"""
    if not video_path: return []
    print("👁️ 分析画面...", flush=True)

    scenes = detect_scenes(video_path)
    if not scenes:
        # 降级：等间隔抽帧
        scenes = [{"start": i, "end": i + 30} for i in range(0, int(duration), 30)]

    print(f"  📐 {len(scenes)} 个场景", flush=True)

    results = []
    for i, scene in enumerate(scenes):
        if i > 0 and HAS_VLM:
            desc = analyze_scene(video_path, scene)
            if desc:
                results.append({"time": f"{scene['start']:.0f}s", "desc": desc[:100]})

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
