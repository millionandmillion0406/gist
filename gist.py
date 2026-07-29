#!/usr/bin/env python3
"""link-distill — 扔链接，AI 自动蒸馏出可复用的经验"""
import argparse, json, os, subprocess, sys, time, urllib.request
from pathlib import Path

W = Path(__file__).parent / "tmp"; W.mkdir(exist_ok=True)
COOKIES = Path(__file__).parent / "douyin_cookies.txt"
KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY:
    print("⚠ 请设置环境变量 DEEPSEEK_API_KEY"); sys.exit(1)

# ── 找 Python + 检测依赖 ──
PY = sys.executable

def has_funasr():
    try: return subprocess.run([PY, "-m", "pip", "show", "funasr"], capture_output=True, timeout=5).returncode == 0
    except: return False

HAS_FUNASR = has_funasr()

def sh(cmd, t=300):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout {t}s"
    except Exception as e:
        return -1, "", str(e)

# ── 1. 下载音频 ──
def download(url):
    print("📥 下载中...", flush=True)
    a = W / "a.mp3"
    a.unlink(missing_ok=True)
    cmd = ["yt-dlp", "--cookies", str(COOKIES)] if COOKIES.exists() else ["yt-dlp"]
    cmd += ["-x", "--audio-format", "mp3", "-o", str(a), "--no-playlist", url]
    rc, _, err = sh(cmd)
    if rc != 0 or not a.exists():
        print(f"❌ 下载失败: {err[:150]}", flush=True); return None
    print(f"  ✅ {a.stat().st_size//1024}KB", flush=True)
    return a

# ── 2. 转录 ──
def transcribe(path):
    text = ""
    # 先试 FunASR
    if HAS_FUNASR:
        print("🎤 听写中（FunASR）...", flush=True)
        code = f"from funasr import AutoModel; m=AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',disable_update=True,disable_progress=True); r=m.generate(input=r'{path.resolve()}'); print(r[0]['text'])"
        rc, out, _ = sh([PY, "-c", code], t=600)
        if rc == 0 and out.strip():
            text = ' '.join(l for l in out.strip().split('\n') if not l.startswith(('Download','Processing','funasr')) and l.strip()).replace(' ','').strip()
    # 不行就 Whisper
    if not text:
        print("🎤 听写中（Whisper）...", flush=True)
        code = f"import whisper; m=whisper.load_model('tiny'); r=m.transcribe(r'{path.resolve()}',language='zh',verbose=False); print(r['text'])"
        rc, out, _ = sh([PY, "-c", code], t=1800)
        if rc == 0 and out.strip(): text = out.strip()
    if not text: print("⚠ 转录结果为空", flush=True)
    return text

# ── 3. 图文提取 ──
def extract_note(url):
    # 优先读页面简介（快）
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def get():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                t = await page.title()
                d = await page.evaluate('() => document.querySelector("meta[name=description]")?.content || ""')
                await browser.close()
                return f"{t}\n{d}"
        desc = asyncio.run(get())
        if desc.strip(): return desc.strip()[:3000]
    except: pass
    # 后备：OCR
    try:
        rc, out, _ = sh([PY, str(Path(__file__).parent/"douyin_note.py"), url], t=180)
        if rc == 0 and out.strip():
            lines = [l.strip() for l in out.split('\n') if l.strip() and not l.startswith('📖') and not l.startswith('📄')]
            noise = ["下载","桌面","快捷","保存登录","取消","保存","浏览器","静音","充钻石","客户端","壁纸","通知","消息","粉丝","获赞"]
            lines = [l for l in lines if not any(k in l[:15] for k in noise)]
            if lines: return '\n'.join(lines)[:5000]
    except: pass
    return "⚠ 提取失败"

# ── 4. AI 蒸馏 ──
def llm(prompt, mt=1024):
    try:
        data = json.dumps({"model":"deepseek-v4-flash","messages":[{"role":"user","content":prompt}],"max_tokens":mt}).encode()
        req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=data,
            headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠ LLM: {e}", flush=True); return ""

def distill(text):
    if not text.strip(): return "⚠ 无内容"
    print("🧠 AI 分析中...", flush=True)
    p = f"""修正错别字后，只提取能带走的东西。

## 核心洞察
## 可复用的思维模型
## 怎么做

内容：
{text}"""
    return llm(p, 1024) or text

# ── 5. 检测类型 + 自动保存 ──
def save_and_show(analysis, text, t0, is_note=False):
    (Path(__file__).parent/"last_analysis.json").write_text(
        json.dumps({"text":text,"analysis":analysis}, ensure_ascii=False, indent=2))
    # 自动追加到 INSIGHTS.md
    try:
        from datetime import datetime
        insights = Path(__file__).parent / "INSIGHTS.md"
        with open(insights, 'a', encoding='utf-8') as f:
            f.write(f"\n---\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} gist\n\n{analysis}\n")
    except: pass
    # SwarmVault 导入
    try:
        from datetime import datetime
        sv = Path(__file__).parent / "raw" / f"gist-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        sv.parent.mkdir(exist_ok=True)
        sv.write_text(f"# gist {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{analysis}", encoding='utf-8')
        subprocess.run(["npx.cmd","swarmvault","ingest",str(sv)], capture_output=True, timeout=30)
        subprocess.run(["npx.cmd","swarmvault","compile"], capture_output=True, timeout=60)
    except: pass
    # 输出
    elapsed = f"{time.time()-t0:.0f}s"
    print(f"\n{'='*50}")
    print(f"  完成 ⏱ {elapsed}")
    print(f"{'='*50}")
    print(analysis)
    print(f"{'='*50}")
    print(f"  来聊 👊")
    print(f"{'='*50}")

# ── 6. 主流程 ──
def main():
    ap = argparse.ArgumentParser(description="link-distill — 扔链接，AI蒸馏")
    ap.add_argument("url"); ap.add_argument("--json", action="store_true")
    args = ap.parse_args(); t0 = time.time()

    # 检测图文还是视频
    is_note = False
    try:
        import asyncio
        from playwright.async_api import async_playwright
        async def detect():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(args.url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.5)
                u = page.url; await browser.close(); return u
        final_url = asyncio.run(detect())
        is_note = "/note/" in final_url
    except: pass

    if is_note:
        text = extract_note(args.url)
        if text.startswith("⚠"):
            print(text, flush=True); return
        analysis = distill(text)
        save_and_show(analysis, text, t0, is_note=True)
        return

    # 视频流程
    a = download(args.url)
    if not a: return
    text = transcribe(a)
    a.unlink()
    if text:
        analysis = distill(text)
        save_and_show(analysis, text, t0)
    else:
        print("⚠ 未能提取任何内容", flush=True)

if __name__ == "__main__":
    main()
