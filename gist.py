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


# ── 2. 转录（FunASR + Whisper 兜底）──

HAS_FUNASR = subprocess.run([PY, "-m", "pip", "show", "funasr"],
    capture_output=True, timeout=10).returncode == 0

def transcribe(audio_path):
    """优先 FunASR（中文更准），没有则用 Whisper"""
    if HAS_FUNASR:
        print("🎤 听写中（FunASR）...", flush=True)
        code = f"""
from funasr import AutoModel
model = AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    disable_update=True, disable_progress=True)
r = model.generate(input=r'{audio_path}')
print(r[0]['text'])
"""
        rc, out, _ = sh([PY, "-c", code], timeout=1800)
        if rc == 0 and out.strip():
            # 清理 FunASR 进度输出，只保留中文文本
            lines = out.strip().split("\n")
            text = ' '.join(l for l in lines if not l.startswith('Download') and not l.startswith('Processing') and not l.startswith('funasr') and l.strip())
            return text.replace(" ", "").strip()

    print("🎤 听写中（Whisper）...", flush=True)
    code = f"import whisper; m=whisper.load_model('base'); r=m.transcribe(r'{audio_path}',language='zh',verbose=False); print(r['text'])"
    rc, out, _ = sh([PY, "-c", code], timeout=1800)
    return out.strip() if rc == 0 else ""


# ── 3. 视觉分析（自动选择引擎）──

AUTOGLM_SKILL_DIR = Path("C:/Users/windows/.openclaw-autoclaw/skills/autoglm-image-recognition")

def has_local_vision():
    """检查本地是否有可用的视觉模型"""
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
    for m in ["llava", "minicpm", "bakllava"]:
        if m in (r.stdout or "").lower():
            return m
    return None

def analyze_frame(frame_path, local_model=None):
    """分析单帧画面——优先本地，兜底云端"""
    if local_model:
        import base64
        b64 = base64.b64encode(open(frame_path, "rb").read()).decode()
        data = json.dumps({"model": f"{local_model}:latest", "prompt": "简短描述这个画面", "images": [b64], "stream": False}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=data,
            headers={"Content-Type": "application/json"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            desc = resp.get("response", "").strip()
            if desc: return desc
        except: pass

    # 兜底：AutoGLM 云端
    try:
        r1 = subprocess.run([PY, str(AUTOGLM_SKILL_DIR / "upload-mix.py"), str(frame_path)],
            capture_output=True, text=True, timeout=30)
        if r1.returncode != 0: return ""
        url = json.loads(r1.stdout)["data"]["oss_info"][0]["oss_url"]
        r2 = subprocess.run([PY, str(AUTOGLM_SKILL_DIR / "image-recognition.py"), url],
            capture_output=True, text=True, timeout=30)
        if r2.returncode != 0: return ""
        return json.loads(r2.stdout)["data"]["text"]
    except:
        return ""


def visual_analysis(video_path, duration):
    """场景检测 + 逐镜分析 — 基于 VideoContextEngine 的 HSV 直方图方案"""
    if not video_path or duration <= 0: return []
    print("👁️ 分析画面...", flush=True)

    local_model = has_local_vision()
    if local_model:
        print(f"  🖥️ 本地模型: {local_model}", flush=True)
    else:
        print(f"  ☁️ 云端识别", flush=True)

    # 场景检测：HSV 直方图对比，画面变了才算新场景
    scenes = []
    try:
        code = """
import cv2, json, numpy as np
cap = cv2.VideoCapture(r"VIDEO_PATH")
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
            if (1.0 - score) > 0.3: change = True
        if (change and (now - start) >= 2) or (now - start) >= 60:
            scenes.append({"start": start, "end": prev})
            start = now
        last_hist = hist
        prev = now
    idx += 1
if prev > start: scenes.append({"start": start, "end": prev})
cap.release()
print(json.dumps(scenes))
""".replace("VIDEO_PATH", str(video_path))
        rc, out, _ = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=300)
        if rc == 0 and out.strip():
            scenes = json.loads(out.strip())
    except:
        pass

    if not scenes:
        scenes = [{"start": 0, "end": min(int(duration), 300)}]
    print(f"  📐 {len(scenes)} 个场景", flush=True)

    # 逐场景分析关键帧
    results = []
    for i, s in enumerate(scenes):
        if i > 5: break  # 最多看 6 个场景
        ts = s["start"] + (s["end"] - s["start"]) / 2
        frame = WORK_DIR / f"s{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(frame)],
            capture_output=True, timeout=30)
        if frame.exists():
            desc = analyze_frame(frame, local_model)
            if desc: results.append({"time": f"{int(s['start'])}s", "desc": desc})
            frame.unlink()

    return results


# ── 4. AI 蒸馏（3 提取器并行）──

def llm_call(prompt, max_tokens=2048):
    """调 DeepSeek API"""
    data = json.dumps({"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=data,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f""


# ── 5. 抖音图文提取（调用 douyin_note.py）──

def extract_note(url):
    """调用 douyin_note.py 提取图文"""
    note_py = Path(__file__).parent / "douyin_note.py"
    pw_py = r"C:\Users\windows\AppData\Local\Programs\Python\Python312\python.exe"
    try:
        rc, out, _ = sh([pw_py, str(note_py), url], timeout=60)
        if rc != 0: return "⚠ 提取失败"
        lines = out.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("📝 图文内容："):
                # 内容在下一行
                if i + 1 < len(lines):
                    content = lines[i + 1].strip()
                    # 去掉 markdown 标记
                    content = content.replace("**", "").replace("## ", "")
                    return content[:500]
                return line[len("📝 图文内容："):].strip()
        # 尝试从输出中找正文
        lines = [l for l in out.split("\n") if len(l) > 20 and "界面" not in l[:8]]
        return "\n".join(lines[:5]) if lines else "⚠ 未能提取内容"
    except Exception as e:
        return f"⚠ 需要 playwright：pip install playwright && playwright install chromium"


def distill(transcript, vision=None):
    if not transcript.strip():
        return "⚠ 未检测到语音内容"
    print("🧠 AI 分析中...", flush=True)

    # 精简画面描述：去掉 UI 描述，只保留内容
    vis = ""
    if vision:
        lines = []
        for v in vision:
            t = v['desc']
            # 跳过纯 UI 描述
            if len(t) < 20 or any(k in t[:20] for k in ["界面", "按钮", "图标", "截图", "布局"]):
                continue
            lines.append(f"[{v['time']}] {t}")
        if lines:
            vis = "\n画面：\n" + "\n".join(lines[:2])

    prompt = f"""分析整段视频内容（从头到尾都要覆盖），做 3 件事：

1. 纠错：修正错別字和不通顺的地方，保留口语气质
2. 一句话概括核心主题
3. 提取结构化内容（没有就不写）：
   - 🧠 思维模型/框架
   - 📏 原则/规则  
   - 📖 案例
   - ⚠️ 边界/注意
   - 💡 可执行步骤

内容：
{transcript}{vis}"""

    result = llm_call(prompt, max_tokens=4096)
    return result if result else transcript


# ── 主流程 ──

def main():
    ap = argparse.ArgumentParser(description="gist — 全平台视频分析")
    ap.add_argument("url", help="视频链接")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--vision", action="store_true", help="启用画面分析（需 Ollama + 视觉模型）")
    ap.add_argument("--note", action="store_true", help="抖音图文模式（需 Chrome 登录抖音）")
    args = ap.parse_args()

    t0 = time.time()

    # 图文模式（跳过视频管线）
    if args.note:
        print("📖 图文模式...", flush=True)
        text = extract_note(args.url)
        analysis = distill(text)
        elapsed = f"{time.time()-t0:.0f}s"
        result = {"text": text, "analysis": analysis, "elapsed": elapsed}
        (Path(__file__).parent / "last_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n{'='*50}")
        print(f"  gist 完成 ⏱ {elapsed}")
        print(f"{'='*50}\n{analysis}\n{'='*50}\n  来聊 👊\n{'='*50}")
        return

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
                print(f"  👁️ [{v['time']}] {v['desc']}")
        print(f"{'='*50}\n{analysis}\n{'='*50}\n  来聊这个视频 👊\n{'='*50}")


if __name__ == "__main__":
    main()
