#!/usr/bin/env python3
"""扔链接 → 蒸馏 → 入库"""
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
    if not ok or not a.exists(): print(f"  失败: {e[:100]}"); return None
    print(f"  {a.stat().st_size//1024}KB"); return a

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
    if text: print(f"  {len(text)} 字")
    return text

# 3. AI 蒸馏
def distill(text):
    if not text.strip(): return "⚠ 无内容"
    print("[AI]", flush=True)
    p = f"""修正错别字后，做真正的蒸馏——不是概括内容，是把里面的精华炼出来。

每一条输出都要做到：
- 这个经验为什么成立？（讲清楚逻辑）
- 在什么场景下能用？（给一个具体例子）
- 跟已知的常识有什么不同？（点出反直觉的地方）

格式：
## 核心洞察（每一条都要有"为什么成立+应用场景+反直觉点"）
## 思维模型
## 怎么做

内容：
{text}"""
    try:
        d = json.dumps({"model":"deepseek-v4-flash","messages":[{"role":"user","content":p}],"max_tokens":1024}).encode()
        r = urllib.request.Request("https://api.deepseek.com/chat/completions",data=d,headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
        r2 = json.loads(urllib.request.urlopen(r,timeout=60).read())["choices"][0]["message"]["content"]
        if r2: print(f"  {len(r2)} 字"); return r2
    except Exception as e: print(f"  API失败: {e}")
    return text

# 4. 入库
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
    ap = argparse.ArgumentParser(); ap.add_argument("url"); a = ap.parse_args(); t0 = time.time()
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
    text = transcribe(audio); audio.unlink(missing_ok=True)
    if not text: print("❌ 转录失败"); return
    analysis = distill(text); save(text,analysis,t0); print(analysis)

if __name__ == "__main__": main()
