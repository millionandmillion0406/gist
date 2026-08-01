#!/usr/bin/env python3
"""扔链接 → 蒸馏（语音+画面）→ 入库
零配置默认走 DeepSeek 官方（DEEPSEEK_API_KEY 环境变量），
也支持配置覆盖（api_base/model），适配任意 OpenAI 兼容服务。
"""
import argparse, base64, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

W = Path(__file__).parent / "tmp"; W.mkdir(exist_ok=True)
COOKIES = Path(__file__).parent / "douyin_cookies.txt"
DATA_DIR = Path(__file__).parent  # 打包版会指向 %LOCALAPPDATA%\LinkDistill
CONFIG_PATH = DATA_DIR / ".link_distill_config.json"
PY = sys.executable

# ---- 配置系统：CLI 参数/配置文件 > 环境变量 > 内置默认（适配所有人） ----
DEFAULT_API_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    except Exception:
        return {}

CONFIG = load_config()

def setting(name, default=""):
    env_map = {"api_key": "DEEPSEEK_API_KEY", "api_base": "DEEPSEEK_API_BASE", "model": "DEEPSEEK_MODEL"}
    env = os.environ.get(env_map.get(name, ""))
    return env or CONFIG.get(name) or default

def normalize_api_base(value):
    value = (value or "").strip().rstrip("/")
    return value if re.match(r"^https?://", value, re.IGNORECASE) else ""

def extract_url(value):
    """从分享口令/文本中提取第一个有效链接"""
    m = re.search(r"https?://[^\s<>\"'，。！？；【】（）]+", value or "", re.IGNORECASE)
    return m.group(0).rstrip('，,。.!！?？:：;；)）]】') if m else ""

def friendly_error(stderr, url, stage):
    """把 yt-dlp/网络错误翻译成人话"""
    err = (stderr or "").lower()
    if "unsupported url" in err: return "这个链接格式不受支持"
    if "requested format is not available" in err: return "没有可用的下载格式"
    if "login" in err or "authentication" in err or "sign in" in err: return "该内容需要登录，请提供登录态 cookie"
    if "georestricted" in err or "geo" in err: return "该内容有地区限制"
    if "private video" in err or "permission" in err: return "该视频是私密/受限内容"
    if "timed out" in err or "timeout" in err: return "网络超时，请稍后重试"
    return f"{stage}失败，请检查链接是否有效"

def tool(name):
    """查找可执行文件（PATH → 打包目录 → 常见安装位置）"""
    found = shutil.which(name)
    if found: return found
    candidates = []
    if name == "ffmpeg":
        candidates += [
            Path(__file__).parent / "ffmpeg.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        ]
    for p in candidates:
        if p.exists(): return str(p)
    return name

def sh(cmd, t=300):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t, encoding="utf-8", errors="replace")
        return r.returncode == 0, r.stdout, r.stderr
    except: return False, "", "timeout/fail"

# 1. 下载
def ytdlp_cmd():
    cmd = ["yt-dlp"]
    if COOKIES.exists(): cmd += ["--cookies",str(COOKIES)]
    return cmd

def download(url):
    print("[下载]", flush=True)
    a = W / "a.mp3"; a.unlink(missing_ok=True)
    cmd = ytdlp_cmd() + ["-x","--audio-format","mp3","-o",str(a),"--no-playlist",url]
    ok, _, e = sh(cmd, 180)
    if not ok or not a.exists():
        print(f"  {friendly_error(e, url, '下载')}", flush=True); return None
    print(f"  {a.stat().st_size//1024}KB", flush=True); return a

def download_browser_audio(url):
    """兜底：yt-dlp 失败时用 headless Edge 抓媒体流（实验性，仅抖音）"""
    if "douyin.com" not in url.lower(): return None
    print("[浏览器视频]", flush=True)
    media_path = W / "browser-video.mp4"; audio_path = W / "a.mp3"
    media_path.unlink(missing_ok=True); audio_path.unlink(missing_ok=True)
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def find_media():
            async with async_playwright() as p:
                browser = await p.chromium.launch(channel="msedge", headless=True)
                context = await browser.new_context(viewport={"width": 1280, "height": 900})
                page = await context.new_page()
                candidates = []
                def capture(response):
                    if response.request.resource_type == "media":
                        candidates.append(response.url)
                page.on("response", capture)
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(5)
                try:
                    srcs = await page.locator("video").evaluate_all("videos => videos.map(v => v.currentSrc || v.src).filter(Boolean)")
                    candidates.extend(srcs)
                    await page.locator("video").first.evaluate("video => video.play().catch(() => {})")
                    await asyncio.sleep(4)
                except Exception: pass
                media_urls = [u for u in dict.fromkeys(reversed(candidates)) if u.startswith("http")]
                cookies = await context.cookies()
                cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                referer = page.url
                await browser.close()
                return media_urls, referer, cookie_header
        media_urls, referer, cookie_header = asyncio.run(find_media())
        if not media_urls:
            print("  页面播放器没有返回视频", flush=True); return None
        headers = f"Referer: {referer}\r\nCookie: {cookie_header}\r\n"
        for media_url in media_urls[:2]:
            audio_path.unlink(missing_ok=True)
            ok, _, _ = sh([tool("ffmpeg"), "-y", "-headers", headers, "-i", media_url,
                           "-vn", "-acodec", "libmp3lame", str(audio_path)], 300)
            if ok and audio_path.exists() and audio_path.stat().st_size > 100_000:
                print(f"  {audio_path.stat().st_size//1024}KB", flush=True)
                return audio_path
        return None
    except Exception as e:
        print(f"  [浏览器兜底失败] {str(e)[:100]}", flush=True)
        return None

def extract_youtube_transcript(url):
    """YouTube 字幕直取（失败自动回退正常下载流程）"""
    if not re.search(r"(?:youtube\.com|youtu\.be)", url, re.IGNORECASE): return ""
    print("[YouTube 字幕]", flush=True)
    try:
        from youtube_transcript import fetch_direct
        title, transcript = fetch_direct(url)
        text = f"标题：{title}\n{transcript}".strip() if transcript else ""
    except Exception:
        text = ""
    if text:
        print(f"  {len(text)} 字", flush=True)
        return text
    return ""

def download_video(url):
    """下载视频本体，多策略降级 + 自动重试（应对偶发风控/网络抖动）"""
    v = W / "v.mp4"
    # 策略链：B站等分离流 → 抖音等单文件流 → mp4 兜底
    strategies = [
        ["-f","bv+ba/b","--merge-output-format","mp4"],
        ["-f","b"],
        ["-f","b[ext=mp4]"],
    ]
    for round_no in range(2):
        for s in strategies:
            v.unlink(missing_ok=True)
            ok, _, e = sh(ytdlp_cmd() + s + ["-o",str(v),"--no-playlist",url], 300)
            if ok and v.exists() and v.stat().st_size > 100_000:
                print(f"  {v.stat().st_size//1024//1024}MB", flush=True)
                return v
            # 关键：失败原因必须可见，否则只能靠猜
            if e.strip(): print(f"  [策略 {s[1]} 失败] {e.strip()[-150:]}", flush=True)
        print(f"  第 {round_no+1} 轮失败，重试…", flush=True)
    return None

# 2. 转录
def transcribe(audio):
    text = ""
    # 可选：百炼在线 ASR（配置了 DASHSCOPE_API_KEY 才启用，默认走本地 FunASR）
    asr_key = os.environ.get("DASHSCOPE_API_KEY") or setting("asr_api_key")
    if asr_key:
        print("[百炼 ASR]", flush=True)
        try:
            send_audio = audio
            compressed = W / "asr-small.mp3"
            if audio.stat().st_size > 7_000_000:
                compressed.unlink(missing_ok=True)
                ok, _, _ = sh([tool("ffmpeg"), "-y", "-i", str(audio), "-ac", "1", "-ar", "16000",
                               "-b:a", "32k", str(compressed)], 180)
                if ok and compressed.exists(): send_audio = compressed
            encoded = base64.b64encode(send_audio.read_bytes()).decode("ascii")
            payload = json.dumps({
                "model": "qwen3-asr-flash",
                "messages": [{"role": "user", "content": [{"type": "input_audio",
                    "input_audio": {"data": f"data:audio/mpeg;base64,{encoded}"}}]}],
                "stream": False, "asr_options": {"language": "zh", "enable_itn": True},
            }, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                data=payload, headers={"Authorization": f"Bearer {asr_key}", "Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=300).read())
            text = resp["choices"][0]["message"]["content"].strip()
            if text: print(f"  {len(text)} 字", flush=True)
        except Exception as e:
            msg = str(e).lower()
            tip = "在线识别失败" + ("（Key 不正确）" if "401" in msg or "unauthorized" in msg else
                  "（音频太长）" if "413" in msg else "（请求过多/额度不足）" if "429" in msg else "")
            print(f"  {tip}，改用本地识别", flush=True)
    if not text:
        ok, _, _ = sh([PY,"-m","pip","show","funasr"],5)
        if ok:
            print("[FunASR]", flush=True)
            ok, out, _ = sh([PY,"-c",f"from funasr import AutoModel; m=AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',disable_update=True,disable_progress=True); r=m.generate(input=r'{audio.resolve()}'); print(r[0]['text'])"],600)
            if ok and out.strip():
                text = ' '.join(l for l in out.strip().split('\n') if not l.startswith(('Download','Processing','funasr')) and l.strip()).replace(' ','').strip()
    if not text:
        try:
            import whisper  # noqa
            ok = True
        except ImportError:
            ok = False
        if ok:
            print("[Whisper]", flush=True)
            ok, out, _ = sh([PY,"-c",f"import whisper; m=whisper.load_model('tiny'); r=m.transcribe(r'{audio.resolve()}',language='zh',verbose=False); print(r['text'])"],1800)
            if ok and out.strip(): text = out.strip()
    if text: print(f"  {len(text)} 字", flush=True)
    else: print("  ⚠️ 本地转录不可用：请运行 pip install funasr torch（推荐）或 openai-whisper torch", flush=True)
    return text

# 3. 画面分析
def local_vision_models():
    """列出本机可用的视觉模型，按质量排序（qwen2.5vl 效果最好）"""
    if not shutil.which("ollama"): return []
    try:
        r = subprocess.run(["ollama","list"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
    except Exception:
        return []
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

def analyze_frame(frame, model, prompt=None):
    """用 Ollama 分析单帧画面（num_ctx 8192 保证放得下图像 token）
    prompt 可覆盖：图文作品传读文字指令，视频帧用画面描述"""
    import base64, io
    try:
        from PIL import Image
        img = Image.open(frame); img.thumbnail((720, 720))
        buf = io.BytesIO(); img.convert("RGB").save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        data = json.dumps({
            "model": model,
            "prompt": prompt or "这是视频的一帧截图。详细描述：画面里有什么（人物/物体/动作）、环境氛围、以及画面语言（构图、色调、镜头角度）。200字以内。",
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
                browser = await p.chromium.launch(channel="msedge", headless=True)
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
        v = download_video(url)
        if not v:
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

# 4. AI 分析（语音+画面直接丢给 AI 思考，不搞格式化蒸馏）
def distill(text, vision=None):
    if not text.strip(): return "⚠ 无内容"
    print("[AI]", flush=True)
    vis = ""
    if vision:
        vis = "\n\n画面信息：\n" + "\n".join(f"[{v['time']}] {v['desc']}" for v in vision)
    p = f"""这是视频的语音转录（可能有些错别字，请自行理解修正）和画面描述。
请认真读完并思考这段内容，然后直接告诉我你的想法，最后一定要回答这两块：
- 以后可以怎么做？（把这段内容里的经验/启发用到以后的工作和生活中，要具体可执行）
- 有什么例子？（给具体的例子，最好是身边真实能碰到的场景）

不要概括复述内容，不要套固定格式，就像朋友看完视频后跟你说"这视频有点东西"那样，说你真正觉得有料的地方。

视频内容：
{text}{vis}"""
    try:
        # 三级 fallback：配置/环境变量 > 内置默认（deepseek-chat 官方，非推理稳定）
        api_key = setting("api_key")
        api_base = normalize_api_base(setting("api_base")) or DEFAULT_API_BASE
        model = setting("model") or DEFAULT_MODEL
        if not api_key:
            print("  API失败: 未设置 DEEPSEEK_API_KEY（可注册 deepseek.com 免费获取）", flush=True)
            return text
        d = json.dumps({"model":model,"messages":[{"role":"user","content":p}],"max_tokens":8192}).encode()
        r = urllib.request.Request(f"{api_base}/chat/completions",data=d,headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"})
        r2 = json.loads(urllib.request.urlopen(r,timeout=120).read())["choices"][0]["message"]["content"]
        if r2: print(f"  {len(r2)} 字", flush=True); return r2
    except Exception as e:
        msg = str(e).lower()
        tip = ("API Key 不正确" if "401" in msg or "unauthorized" in msg else
               "API 地址或模型名不正确" if "404" in msg or "not found" in msg else
               "请求过多或额度不足" if "429" in msg else
               "网络超时" if "timeout" in msg or "timed out" in msg else
               "无法连接 API 服务器，请检查 api-base 地址和网络" if "getaddrinfo" in msg or "connection" in msg or "failed to establish" in msg else
               str(e)[:80])
        print(f"  API失败: {tip}", flush=True)
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
    ap.add_argument("--extract-only", action="store_true", help="只提取转录/图文内容，不调用 AI")
    ap.add_argument("--api-key", help="覆盖 API Key")
    ap.add_argument("--api-base", help="覆盖完整的 http/https API 地址")
    ap.add_argument("--model", help="覆盖模型名")
    a = ap.parse_args(); t0 = time.time()
    if a.api_key: CONFIG["api_key"] = a.api_key
    if a.api_base: CONFIG["api_base"] = a.api_base
    if a.model: CONFIG["model"] = a.model
    a.url = extract_url(a.url)
    if not a.url:
        print("❌ 没有找到有效的 http/https 链接")
        sys.exit(1)
    if not a.extract_only and not shutil.which("ffmpeg") and not Path(tool("ffmpeg")).exists():
        print("❌ 缺少 ffmpeg，请先运行: winget install ffmpeg")
        sys.exit(1)
    if not shutil.which("yt-dlp"):
        print("❌ 缺少 yt-dlp，请先运行: pip install yt-dlp")
        sys.exit(1)
    # 判断图文/视频
    is_note = False
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def f():
            async with async_playwright() as p:
                b = await p.chromium.launch(channel="msedge", headless=True); page = await b.new_page()
                await page.goto(a.url,wait_until="domcontentloaded",timeout=15000); await asyncio.sleep(1.5)
                u = page.url; await b.close(); return u
        is_note = "/note/" in asyncio.run(f())
    except: pass

    def finish(text, vision=None):
        if a.extract_only or not setting("api_key"):
            print(text)
            if not a.extract_only:
                print("\n[提示] 内容已提取；设置 DEEPSEEK_API_KEY 后可继续 AI 分析。")
            return
        analysis = distill(text, vision or [])
        save(text, analysis, t0)
        print(analysis)

    if is_note:
        print("[图文]", flush=True)
        text = ""
        try:
            import asyncio
            from playwright.async_api import async_playwright
            async def g():
                async with async_playwright() as p:
                    b = await p.chromium.launch(channel="msedge", headless=True); page = await b.new_page()
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
        if not text:
            print("❌ 没有读到正文，请确认链接能正常打开")
            sys.exit(1)
        # 图片视觉分析：下载图文图片，用本地视觉模型描述画面内容
        vision = []
        try:
            import asyncio
            from playwright.async_api import async_playwright
            models = local_vision_models()
            if models:
                print("  📷 下载图片...", flush=True)
                async def grab_images():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(channel="msedge", headless=True)
                        page = await browser.new_page(viewport={"width": 1200, "height": 900})
                        await page.goto(a.url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(4)
                        for _ in range(15):  # 翻页加载全部图片
                            await page.keyboard.press("ArrowRight")
                            await asyncio.sleep(1.0)
                        imgs = await page.evaluate('''() =>
                            [...document.querySelectorAll('img')]
                                .filter(i => (i.naturalWidth || i.width) >= 400 && (i.naturalHeight || i.height) >= 400)
                                .map(i => i.src)''')
                        seen = set(); unique = []
                        for u in imgs:
                            base = u.split('?')[0]
                            if base not in seen: seen.add(base); unique.append(u)
                        paths = []
                        for i, src in enumerate(unique[:5]):  # 最多 5 张
                            try:
                                resp = await page.context.request.get(src, timeout=15000)
                                if resp.status != 200: continue
                                data = await resp.body()
                                if len(data) < 5000: continue
                                fp = W / f"n{i}.jpg"
                                fp.write_bytes(data)
                                paths.append(fp)
                            except Exception: pass
                        await browser.close()
                        return paths
                for fp in asyncio.run(grab_images()):
                    for m in models:
                        # 图文核心在图片文字上：先读字，再简述画面
                        d = analyze_frame(str(fp), m, prompt="这是一张图文卡片/海报。请1)完整读出图片中的所有文字内容（标题、正文、金句，逐条列出，看不清的字标注[模糊]）2)一句话简述画面。不要遗漏文字。")
                        if d:
                            vision.append({"time": "图", "desc": d})
                            print(f"  [图] {d[:80]}", flush=True)
                            break
                    fp.unlink(missing_ok=True)
                print(f"  {len(vision)} 张图分析完成", flush=True)
        except Exception as e:
            print(f"  [图片分析失败] {str(e)[:80]}", flush=True)
        finish(text, vision); return

    youtube_text = extract_youtube_transcript(a.url)
    if youtube_text:
        finish(youtube_text); return

    audio = download(a.url)
    if not audio:
        audio = download_browser_audio(a.url)
    if not audio:
        print("❌ 提取失败，请确认链接有效")
        sys.exit(1)
    text = transcribe(audio)
    
    vision = []
    if a.vision:
        vision = visual_analysis(a.url)
    
    audio.unlink(missing_ok=True)
    if not text:
        print("❌ 没有识别出语音，请确认视频是否有人声")
        sys.exit(1)
    finish(text, vision)

if __name__ == "__main__": main()
