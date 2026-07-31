#!/usr/bin/env python3
"""扔链接 → 蒸馏（语音+画面）→ 入库"""
import argparse, json, os, subprocess, sys, time, urllib.request
from pathlib import Path

W = Path(__file__).parent / "tmp"; W.mkdir(exist_ok=True)
COOKIES = Path(__file__).parent / "douyin_cookies.txt"
KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY: print("❌ 需要 DEEPSEEK_API_KEY"); sys.exit(1)
PY = sys.executable

def sh(cmd, t=300):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
        return r.returncode == 0, r.stdout, r.stderr
    except: return False, "", "timeout/fail"

# 1. 下载
def download(url):
    print("[下载]", flush=True)
    a = W / "a.mp3"; a.unlink(missing_ok=True)
    cmd = ["yt-dlp"]
    if COOKIES.exists(): cmd += ["--cookies",str(COOKIES)]
    cmd += ["-x","--audio-format","mp3","-o",str(a),"--no-playlist",url]
    ok, _, e = sh(cmd, 120)
    if not ok or not a.exists(): print(f"  失败: {e[:100]}", flush=True); return None
    print(f"  {a.stat().st_size//1024}KB", flush=True); return a

# 2. 转录
def transcribe(audio):
    text = ""
    ok, _, _ = sh([PY,"-m","pip","show","funasr"],5)
    if ok:
        print("[FunASR]", flush=True)
        ok, out, _ = sh([PY,"-c",f"from funasr import AutoModel; m=AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',disable_update=True,disable_progress=True); r=m.generate(input=r'{audio.resolve()}'); print(r[0]['text'])"],600)
        if ok and out.strip():
            text = ' '.join(l for l in out.strip().split('\n') if not l.startswith(('Download','Processing','funasr')) and l.strip()).replace(' ','').strip()
    if not text:
        print("[Whisper]", flush=True)
        ok, out, _ = sh([PY,"-c",f"import whisper; m=whisper.load_model('tiny'); r=m.transcribe(r'{audio.resolve()}',language='zh',verbose=False); print(r['text'])"],1800)
        if ok and out.strip(): text = out.strip()
    if text: print(f"  {len(text)} 字", flush=True)
    return text

# 3. 画面分析
def local_vision_models():
    """列出本机可用的视觉模型，按质量排序（qwen2.5vl 效果最好）"""
    r = subprocess.run(["ollama","list"], capture_output=True, text=True, timeout=10)
    names = []
    for line in (r.stdout or "").splitlines()[1:]:
        m = line.split()[0] if line.strip() else ""
        if m and any(k in m for k in ["qwen2.5vl","qwen2vl","llava","minicpm","bakllava","llava-llama3"]):
            names.append(m)
    def rank(m):
        base = m.split(":")[0]
        if "qwen2.5vl" in base: return 0
        if "qwen2vl" in base: return 1
        if "llava-llama3" in base: return 2
        if "llava" in base: return 3
        if "minicpm" in base: return 4
        return 5
    return sorted(names, key=rank)

def analyze_frame(frame, model):
    """用 Ollama 分析单帧画面（num_ctx 8192 保证放得下图像 token）"""
    import base64, io
    try:
        from PIL import Image
        img = Image.open(frame); img.thumbnail((720, 720))
        buf = io.BytesIO(); img.convert("RGB").save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        data = json.dumps({
            "model": model,
            "prompt": "这是视频的一帧截图。详细描述：画面里有什么（人物/物体/动作）、环境氛围、以及画面语言（构图、色调、镜头角度）。200字以内。",
            "images": [b64], "stream": False, "options": {"num_ctx": 8192}
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=data,
            headers={"Content-Type":"application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
        return resp.get("response","").strip()
    except Exception as e:
        print(f"  [视觉失败] {e}")
        return ""

def visual_analysis(url):
    """双通道画面分析：浏览器元数据 + 视频逐场景抽帧"""
    print("[画面]", flush=True)
    models = local_vision_models()
    if not models:
        print("  无本地视觉模型，跳过画面分析")
        return []
    print(f"  Ollama: {', '.join(models)}")

    results = []

    # 通道1：浏览器拿元数据+封面（补充上下文）
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def get_meta():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                desc = await page.evaluate('() => document.querySelector("meta[name=description]")?.content || ""')
                await browser.close()
                return desc
        desc = asyncio.run(get_meta())
        if desc:
            results.append({"time":"简介","desc":desc[:300]})
    except: pass

    # 通道2：下载视频，场景检测，逐场景抽帧分析
    try:
        print("  📥 下载视频...", flush=True)
        v = W / "v.mp4"
        sh(["yt-dlp","-f","bv+ba/b","-o",str(v),"--no-playlist","--merge-output-format","mp4",url],120)
        if not v.exists():
            print("  视频下载失败，只用元数据")
            return results

        # 场景检测：ffmpeg 抽 1fps 小图 → HSV 直方图比较。
        # （直接 OpenCV 逐帧 c.read() 会软解全部帧，长视频要 10 分钟+）
        fd = W / "frames"; fd.mkdir(exist_ok=True)
        sh(["ffmpeg","-i",str(v),"-vf","fps=1,scale=160:90","-q:v","6",str(fd/"fr_%04d.jpg")],300)
        ok, out, _ = sh([PY,"-c",f"""
import cv2,json,glob,os
frames=sorted(glob.glob(r"{fd}"+os.sep+"fr_*.jpg"))
s=[]; lh=None; st=0.0; pv=0.0
for i,fp in enumerate(frames):
    now=float(i)  # fps=1，第 i 张 = 第 i 秒
    h=cv2.cvtColor(cv2.imread(fp),cv2.COLOR_BGR2HSV)
    h2=cv2.calcHist([h],[0,1],None,[50,60],[0,180,0,256]); cv2.normalize(h2,h2,0,1,cv2.NORM_MINMAX); h2=h2.flatten()
    ch=False
    if lh is not None and (1.0-cv2.compareHist(lh,h2,cv2.HISTCMP_CORREL))>0.3: ch=True
    if (ch and (now-st)>=2) or (now-st)>=60: s.append({{"start":st,"end":pv}}); st=now
    lh=h2; pv=now
if pv>st: s.append({{"start":st,"end":pv}})
print(json.dumps(s))
"""],300)
        for f in fd.glob("fr_*.jpg"): f.unlink()
        fd.rmdir()
        scenes = json.loads(out) if ok and out.strip() else [{"start":0,"end":60}]
        print(f"  {len(scenes)} 个场景", flush=True)

        # 场景多时均匀采样 8 个，覆盖整条视频（避免全挤在前几秒）
        picks = scenes
        if len(scenes) > 8:
            total = scenes[-1]["end"]
            picks = []
            for k in range(8):
                target = (k + 0.5) * total / 8
                picks.append(min(scenes, key=lambda s: abs((s["start"]+s["end"])/2 - target)))

        # 逐场景抽帧分析（模型失败自动降级到下一个）
        for i, sc in enumerate(picks):
            ts = sc["start"] + (sc["end"]-sc["start"])/2
            frame = W / f"s{i:02d}.jpg"
            sh(["ffmpeg","-ss",str(ts),"-i",str(v),"-frames:v","1","-q:v","2",str(frame)],30)
            if frame.exists():
                for m in models:
                    d = analyze_frame(frame, m)
                    if d:
                        results.append({"time":f"{int(sc['start'])}s","desc":d})
                        print(f"  [{int(sc['start'])}s] {d[:40]}", flush=True)
                        break
                frame.unlink()
        v.unlink()
    except Exception as e:
        print(f"  [视频分析失败] {e}")

    return results

# 4. AI 蒸馏（语音+画面）
def distill(text, vision=None):
    if not text.strip(): return "⚠ 无内容"
    print("[AI]", flush=True)
    vis = ""
    if vision:
        vis = "\n\n画面信息：\n" + "\n".join(f"[{v['time']}] {v['desc']}" for v in vision)
    p = f"""修正错别字后，做真正的蒸馏——不是概括内容，是把里面的精华炼出来。
结合语音内容和画面内容综合分析。

每一条输出都要做到：
- 这个经验为什么成立？（讲清楚逻辑）
- 在什么场景下能用？（给一个具体例子）
- 跟已知的常识有什么不同？（点出反直觉的地方）

格式：
## 核心洞察（每一条都要有"为什么成立+应用场景+反直觉点"）
## 思维模型
## 怎么做

语音内容：
{text}{vis}"""
    try:
        # 用 deepseek-chat（非推理模型，稳定输出）。v4-flash 是推理模型，
        # 对长 prompt 会陷入超长思考，max_tokens 全被 thinking 占掉，正文为空
        d = json.dumps({"model":"deepseek-chat","messages":[{"role":"user","content":p}],"max_tokens":8192}).encode()
        r = urllib.request.Request("https://api.deepseek.com/chat/completions",data=d,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
        r2 = json.loads(urllib.request.urlopen(r,timeout=60).read())["choices"][0]["message"]["content"]
        if r2: print(f"  {len(r2)} 字", flush=True); return r2
    except Exception as e: print(f"  API失败: {e}", flush=True)
    return text

# 5. 入库
def save(text, analysis, t0):
    b = Path(__file__).parent
    (b/"last_analysis.json").write_text(json.dumps({"text":text,"analysis":analysis,"elapsed":f"{time.time()-t0:.0f}s"},ensure_ascii=False,indent=2))
    from datetime import datetime; n = datetime.now()
    (b/"INSIGHTS.md").open("a",encoding="utf-8").write(f"\n---\n## {n.strftime('%Y-%m-%d %H:%M')}\n\n{analysis}\n")
    try:
        sv = b/"raw"/f"gist-{n.strftime('%Y%m%d-%H%M%S')}.md"; sv.parent.mkdir(exist_ok=True)
        sv.write_text(f"# {n.strftime('%Y-%m-%d %H:%M')}\n\n{analysis}",encoding="utf-8")
        subprocess.run(["npx.cmd","swarmvault","ingest",str(sv)],capture_output=True,timeout=30)
        subprocess.run(["npx.cmd","swarmvault","compile"],capture_output=True,timeout=60)
    except: pass
    print(f"✅ {time.time()-t0:.0f}s")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--vision", action="store_true", help="启用画面分析")
    a = ap.parse_args(); t0 = time.time()
    # 判断图文/视频
    is_note = False
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def f():
            async with async_playwright() as p:
                b = await p.chromium.launch(headless=True); page = await b.new_page()
                await page.goto(a.url,wait_until="domcontentloaded",timeout=15000); await asyncio.sleep(1.5)
                u = page.url; await b.close(); return u
        is_note = "/note/" in asyncio.run(f())
    except: pass

    if is_note:
        print("[图文]", flush=True)
        text = ""
        try:
            import asyncio
            from playwright.async_api import async_playwright
            async def g():
                async with async_playwright() as p:
                    b = await p.chromium.launch(headless=True); page = await b.new_page()
                    await page.goto(a.url,wait_until="domcontentloaded",timeout=20000); await asyncio.sleep(2)
                    t = await page.title(); d = await page.evaluate('() => document.querySelector("meta[name=description]")?.content||""')
                    await b.close(); return f"{t}\n{d}" if d.strip() else t
            text = asyncio.run(g())
        except: pass
        if not text:
            ok,out,_ = sh([PY,str(Path(__file__).parent/"douyin_note.py"),a.url],180)
            if ok and out.strip():
                lines = [l.strip() for l in out.split('\n') if l.strip() and not l.startswith(('📖','📄'))]
                noise = ["下载","桌面","快捷","保存登录","取消","保存","浏览器","静音","充钻石","客户端","壁纸","通知","消息","粉丝","获赞"]
                lines = [l for l in lines if not any(k in l[:15] for k in noise)]
                if lines: text = '\n'.join(lines)[:5000]
        if not text: print("❌ 无内容"); return
        analysis = distill(text); save(text,analysis,t0); print(analysis); return

    audio = download(a.url)
    if not audio: return
    text = transcribe(audio)
    
    vision = []
    if a.vision:
        vision = visual_analysis(a.url)
    
    audio.unlink(missing_ok=True)
    if not text: print("❌ 转录失败"); return
    analysis = distill(text, vision); save(text,analysis,t0); print(analysis)

if __name__ == "__main__": main()
