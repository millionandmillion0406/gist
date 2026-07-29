#!/usr/bin/env python3
"""link-distill — 扔链接，AI 自动蒸馏出可复用的经验。
流程：下载 → 转录 → AI蒸馏 → 入库"""
import argparse, json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path

W = Path(__file__).parent / "tmp"; W.mkdir(exist_ok=True)
C = Path(__file__).parent / "douyin_cookies.txt"
KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY: print("⚠ 设置 DEEPSEEK_API_KEY"); sys.exit(1)

# Python 检测（找到带 whisper 的版本）
PY = next((c for c in [sys.executable, "python3", "python"] + [str(p/v/"python.exe") for p in [Path("C:/Users/windows/AppData/Local/Programs/Python"), Path("/c/Users/windows/AppData/Local/Programs/Python")] if p.exists() for v in sorted(p.iterdir(), reverse=True)] if c and subprocess.run([c, "-c", "import whisper"], capture_output=True, timeout=10).returncode == 0), sys.executable)

try:
    HAS_FUNASR = subprocess.run([PY, "-m", "pip", "show", "funasr"], capture_output=True, timeout=5).returncode == 0
except: HAS_FUNASR = False

def sh(cmd, t=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    return r.returncode, r.stdout, r.stderr

def dl(url, *ext):
    cmd = ["yt-dlp", "--cookies", str(C)] + list(ext) + [url] if C.exists() else ["yt-dlp"] + list(ext) + [url]
    return cmd

# ── 下载 ──
def download(url):
    print("📥 下载中...", flush=True)
    a = W / "a.mp3"
    sh(dl(url, "-x", "--audio-format", "mp3", "-o", str(a), "--no-playlist"))
    if not a.exists(): print("❌ 下载失败"); sys.exit(1)
    return a

# ── 转录 ──
def transcribe(path):
    if HAS_FUNASR:
        print("🎤 听写中（FunASR）...", flush=True)
        c = f"from funasr import AutoModel; m=AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch', disable_update=True, disable_progress=True); r=m.generate(input=r'{path.resolve()}'); print(r[0]['text'])"
        rc, out, _ = sh([PY, "-c", c], t=1800)
        if rc == 0 and out.strip():
            return ' '.join(l for l in out.strip().split('\n') if not l.startswith(('Download','Processing','funasr')) and l.strip()).replace(' ','').strip()
    print("🎤 听写中（Whisper）...", flush=True)
    rc, out, _ = sh([PY, "-c", f"import whisper; m=whisper.load_model('tiny'); r=m.transcribe(r'{path.resolve()}',language='zh',verbose=False); print(r['text'])"], t=1800)
    return out.strip() if rc == 0 else ""

# ── 画面分析（可选）──
AUTOGLM = next((p for p in [Path.home()/".openclaw-autoclaw/skills/autoglm-image-recognition", Path.home()/".openclaw/skills/autoglm-image-recognition"] if p.exists()), None)

def analyze_frame(path):
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
    lm = next((m for m in ["llava","minicpm","bakllava"] if m in (r.stdout or "").lower()), None)
    if lm:
        import base64; b64 = base64.b64encode(open(path,"rb").read()).decode()
        try:
            resp = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate",
                json.dumps({"model":f"{lm}:latest","prompt":"简短描述这个画面","images":[b64],"stream":False}).encode(),
                headers={"Content-Type":"application/json"}), timeout=120).read())
            if resp.get("response"): return resp["response"]
        except: pass
    if not AUTOGLM: return ""
    try:
        r1 = subprocess.run([PY, str(AUTOGLM/"upload-mix.py"), str(path)], capture_output=True, text=True, timeout=30)
        if r1.returncode != 0: return ""
        url = json.loads(r1.stdout)["data"]["oss_info"][0]["oss_url"]
        r2 = subprocess.run([PY, str(AUTOGLM/"image-recognition.py"), url], capture_output=True, text=True, timeout=30)
        if r2.returncode != 0: return ""
        return json.loads(r2.stdout)["data"]["text"]
    except Exception as e: print(f"  ⚠️ {e}", flush=True); return ""

def visual_analysis(video, dur):
    if not video or dur <= 0: return []
    print("👁️ 分析画面...", flush=True)
    r = subprocess.run([PY, "-c", f"""
import cv2,json,numpy as np
c=cv2.VideoCapture(r"{video}"); fps=c.get(cv2.CAP_PROP_FPS) or 25; n=int(fps); s=[]; lh=None; st=0.0; pv=0.0; i=0
while True:
    ret,f=c.read()
    if not ret: break
    if i%n==0:
        now=i/fps; h=cv2.cvtColor(f,cv2.COLOR_BGR2HSV)
        h2=cv2.calcHist([h],[0,1],None,[50,60],[0,180,0,256]); cv2.normalize(h2,h2,0,1,cv2.NORM_MINMAX); h2=h2.flatten()
        ch=False
        if lh is not None and (1.0-cv2.compareHist(lh,h2,cv2.HISTCMP_CORREL))>0.3: ch=True
        if (ch and (now-st)>=2) or (now-st)>=60: s.append({{"start":st,"end":pv}}); st=now
        lh=h2; pv=now
    i+=1
if pv>st: s.append({{"start":st,"end":pv}})
c.release(); print(json.dumps(s))
"""], capture_output=True, text=True, timeout=300)
    scenes = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else [{"start":0,"end":min(int(dur),300)}]
    print(f"  📐 {len(scenes)} 个场景", flush=True)
    results = []
    for i, s in enumerate(scenes[:6]):
        ts = s["start"] + (s["end"]-s["start"])/2
        f = W / f"s{i:02d}.jpg"
        subprocess.run(["ffmpeg","-ss",str(ts),"-i",str(video),"-vframes","1","-q:v","2",str(f)], capture_output=True, timeout=30)
        if f.exists():
            d = analyze_frame(f)
            if d: results.append({"time":f"{int(s['start'])}s","desc":d})
            f.unlink()
    return results

# ── 抖音图文 ──
def extract_note(url):
    """提取图文内容：优先 OCR 图片文字，后备读页面简介"""
    # 优先 OCR
    try:
        rc, out, _ = sh([PY, str(Path(__file__).parent/"douyin_note.py"), url], t=180)
        if rc == 0 and out.strip():
            lines = [l.strip() for l in out.split("\n") if l.strip() and not l.startswith("📖") and not l.startswith("📄")]
            # 过滤 UI 干扰
            noise = ["下载","桌面","快捷","保存登录","取消","保存","浏览器","静音","充钻石","客户端","壁纸","通知","消息","粉丝","获赞"]
            lines = [l for l in lines if not any(k in l[:15] for k in noise)]
            if lines:
                return "\n".join(lines)[:5000]
    except: pass
    
    # 后备：读页面简介
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def get_desc():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                t = await page.title()
                d = await page.evaluate('() => document.querySelector("meta[name=description]")?.content || ""')
                await browser.close()
                return f"{t}\n{d}"
        desc = asyncio.run(get_desc())
        if desc.strip(): return desc[:2000]
    except: pass
    
    return "⚠ 提取失败"

# ── AI 蒸馏 ──
def llm(prompt, mt=4096):
    try:
        resp = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.deepseek.com/chat/completions",
            json.dumps({"model":"deepseek-v4-flash","messages":[{"role":"user","content":prompt}],"max_tokens":mt}).encode(),
            headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}), timeout=60).read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e: print(f"⚠ LLM: {e}", flush=True); return ""

def distill(text, vision=None):
    if not text.strip(): return "⚠ 无内容"
    print("🧠 AI 分析中...", flush=True)
    vis = ""
    if vision:
        lines = [f"[{v['time']}] {v['desc']}" for v in vision if len(v['desc']) > 20 and not any(k in v['desc'][:20] for k in ["界面","按钮","图标","截图"])]
        if lines: vis = "\n画面：\n" + "\n".join(lines[:2])
    content = text
    p = f"""你是蒸馏大师。修正错别字后，只提取能带走的东西。
不要概括视频内容。

格式：
## 核心洞察
## 可复用的思维模型
## 怎么做

内容：
{content}{vis}"""
    return llm(p, 800) or text

# ── 主流程 ──
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--vision", action="store_true")
    args = ap.parse_args(); t0 = time.time()

    # 自动检测是图文还是视频
    import asyncio
    try:
        from playwright.async_api import async_playwright
        async def detect():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(args.url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                url = page.url
                await browser.close()
                return url
        final_url = asyncio.run(detect())
        is_note = "/note/" in final_url
    except:
        is_note = False

    if is_note:
        text = extract_note(args.url)
        analysis = distill(text)
        (Path(__file__).parent/"last_analysis.json").write_text(json.dumps({"text":text,"analysis":analysis}, ensure_ascii=False, indent=2))
        print(f"\n{'='*50}\n  完成 ⏱ {time.time()-t0:.0f}s\n{'='*50}\n{analysis}\n{'='*50}\n  来聊 👊\n{'='*50}")
        return

    a = download(args.url); print(f"  ✅ {a.stat().st_size//1024}KB", flush=True)
    text = transcribe(a); a.unlink()
    vision = []
    if args.vision:
        print("📥 下载视频...", flush=True)
        v = W / "v.mp4"
        sh(dl(args.url, "-f", "bv+ba/b", "-o", str(v), "--no-playlist", "--merge-output-format", "mp4"))
        r = subprocess.run(dl(args.url, "--print", "%(duration)s", "--no-playlist"), capture_output=True, text=True, timeout=30)
        dur = float(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 0
        if v.exists() and dur > 0: vision = visual_analysis(v, dur); v.unlink()

    analysis = distill(text, vision)
    # 保存到文件
    (Path(__file__).parent/"last_analysis.json").write_text(json.dumps({"text":text,"analysis":analysis,"vision":vision,"elapsed":f"{time.time()-t0:.0f}s"}, ensure_ascii=False, indent=2))
    
    # 自动追加到 INSIGHTS.md
    try:
        insights = Path(__file__).parent / "INSIGHTS.md"
        now = __import__('datetime').datetime.now()
        with open(insights, 'a', encoding='utf-8') as f:
            f.write(f"\n---\n## {now.strftime('%Y-%m-%d %H:%M')} gist 蒸馏\n\n{analysis}\n")
        print(f"  📝 已追加到 INSIGHTS.md", flush=True)
    except: pass

    # 自动导入知识库
    try:
        sv_path = Path(__file__).parent / "raw" / f"gist-{now.strftime('%Y%m%d-%H%M%S')}.md"
        sv_path.parent.mkdir(exist_ok=True)
        sv_path.write_text(f"# 视频蒸馏 {now.strftime('%Y-%m-%d %H:%M')}\n\n{analysis}", encoding='utf-8')
        subprocess.run(["swarmvault", "ingest", str(sv_path)], capture_output=True, timeout=30)
        subprocess.run(["swarmvault", "compile"], capture_output=True, timeout=60)
        print(f"  📚 已导入 SwarmVault 知识库", flush=True)
    except: pass

    for f in W.iterdir():
        if f.is_file() and f.suffix in ['.mp3','.mp4','.jpg','.webp']: f.unlink()
    if args.json: print(json.dumps({"analysis":analysis}, ensure_ascii=False, indent=2))
    else: print(f"\n{'='*50}\n  gist 完成 ⏱ {time.time()-t0:.0f}s\n{'='*50}\n{analysis}\n{'='*50}\n  来聊这个视频 👊\n{'='*50}")

if __name__ == "__main__": main()
