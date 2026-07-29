#!/usr/bin/env python3
"""
link-distill — 扔链接，AI 自动蒸馏出可复用的经验

流程：下载 → 转录 → AI蒸馏 → 入库
分工：
  gist.py           管道调度（本文件）
  douyin_note.py    图文 OCR（单独文件）
  memory.py         记忆系统
  kb.py             知识库同步

每个步骤独立，出错会打印 [步骤名] + 错误原因。
"""

import argparse, json, os, subprocess, sys, time, urllib.request
from pathlib import Path

# ── 配置 ──
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
COOKIES = Path(__file__).parent / "douyin_cookies.txt"

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_KEY:
    print("❌ [启动] 需要设置环境变量 DEEPSEEK_API_KEY")
    sys.exit(1)

PY = sys.executable


def log(step, msg):
    """统一日志格式：一眼看出哪一步出了问题"""
    print(f"  [{step}] {msg}", flush=True)


def run(cmd, timeout=300):
    """执行命令，返回 (成功?, 输出, 错误)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"超时 {timeout}s"
    except FileNotFoundError:
        return False, "", f"找不到命令: {cmd[0]}"
    except Exception as e:
        return False, "", str(e)


# ══════════════════════════════════════════════════════════
# 步骤 1：下载音频
# ══════════════════════════════════════════════════════════
def step_download(url):
    log("下载", "开始...")
    audio = WORK_DIR / "a.mp3"
    audio.unlink(missing_ok=True)

    cmd = ["yt-dlp"]
    if COOKIES.exists():
        cmd += ["--cookies", str(COOKIES)]
    cmd += ["-x", "--audio-format", "mp3", "-o", str(audio), "--no-playlist", url]

    ok, out, err = run(cmd, timeout=120)
    if not ok or not audio.exists():
        log("下载", f"失败: {err.strip()[:200]}")
        return None

    log("下载", f"完成 ({audio.stat().st_size // 1024}KB)")
    return audio


# ══════════════════════════════════════════════════════════
# 步骤 2：语音转文字
# ══════════════════════════════════════════════════════════
def step_transcribe(audio):
    # 检查依赖
    ok, _, _ = run([PY, "-m", "pip", "show", "funasr"], timeout=5)
    has_funasr = ok

    text = ""
    if has_funasr:
        log("转录", "FunASR...")
        code = (
            "from funasr import AutoModel;"
            "m=AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',"
            "disable_update=True,disable_progress=True);"
            f"r=m.generate(input=r'{audio.resolve()}');"
            "print(r[0]['text'])"
        )
        ok, out, err = run([PY, "-c", code], timeout=600)
        if ok and out.strip():
            lines = [l for l in out.strip().split("\n")
                     if not l.startswith(("Download", "Processing", "funasr")) and l.strip()]
            text = " ".join(lines).replace(" ", "").strip()
            log("转录", f"FunASR 成功 ({len(text)} 字)")
        else:
            log("转录", f"FunASR 失败，换 Whisper ({err.strip()[:100]})")

    if not text:
        log("转录", "Whisper(tiny)...")
        code = (
            "import whisper;"
            "m=whisper.load_model('tiny');"
            f"r=m.transcribe(r'{audio.resolve()}',language='zh',verbose=False);"
            "print(r['text'])"
        )
        ok, out, err = run([PY, "-c", code], timeout=1800)
        if ok and out.strip():
            text = out.strip()
            log("转录", f"Whisper 成功 ({len(text)} 字)")
        else:
            log("转录", f"Whisper 失败: {err.strip()[:100]}")

    return text


# ══════════════════════════════════════════════════════════
# 步骤 3：AI 蒸馏
# ══════════════════════════════════════════════════════════
def step_distill(text):
    if not text.strip():
        log("蒸馏", "无内容可分析")
        return "⚠ 无内容"

    log("蒸馏", "DeepSeek...")
    prompt = f"""你是一个蒸馏大师。先修正转录错别字，然后只提取可复用的经验。
不要概括内容。

## 核心洞察
## 可复用的思维模型
## 怎么做

内容：
{text}"""

    try:
        data = json.dumps({
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json"
            }
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        result = resp["choices"][0]["message"]["content"]
        if result:
            log("蒸馏", f"完成 ({len(result)} 字)")
            return result
    except Exception as e:
        log("蒸馏", f"API 调用失败: {e}")

    return text  # API 失败时返回原文


# ══════════════════════════════════════════════════════════
# 步骤 4：入库 (INSIGHTS.md + SwarmVault)
# ══════════════════════════════════════════════════════════
def step_save(analysis, text, elapsed):
    base = Path(__file__).parent
    # 保存 JSON
    (base / "last_analysis.json").write_text(
        json.dumps({"text": text, "analysis": analysis, "elapsed": elapsed},
                   ensure_ascii=False, indent=2)
    )
    # 追加到 INSIGHTS.md
    try:
        from datetime import datetime
        now = datetime.now()
        insights = base / "INSIGHTS.md"
        with open(insights, "a", encoding="utf-8") as f:
            f.write(f"\n---\n## {now.strftime('%Y-%m-%d %H:%M')}\n\n{analysis}\n")
        log("入库", "INSIGHTS.md ✅")
    except Exception as e:
        log("入库", f"INSIGHTS.md 写入失败: {e}")

    # 导入 SwarmVault
    try:
        from datetime import datetime
        sv_path = base / "raw" / f"gist-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        sv_path.parent.mkdir(exist_ok=True)
        sv_path.write_text(f"# {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{analysis}", encoding="utf-8")
        run(["npx.cmd", "swarmvault", "ingest", str(sv_path)], timeout=30)
        run(["npx.cmd", "swarmvault", "compile"], timeout=60)
        log("入库", "SwarmVault ✅")
    except Exception as e:
        log("入库", f"SwarmVault 导入失败: {e}")


# ══════════════════════════════════════════════════════════
# 图文提取（单独路径）
# ══════════════════════════════════════════════════════════
def extract_note(url):
    """打开页面读简介，不行就调 douyin_note.py OCR"""
    log("图文", "读页面简介...")
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
                d = await page.evaluate(
                    '() => document.querySelector("meta[name=description]")?.content || ""'
                )
                await browser.close()
                return f"{t}\n{d}" if d.strip() else t

        desc = asyncio.run(get())
        if desc.strip():
            log("图文", f"简介成功 ({len(desc)} 字)")
            return desc.strip()[:3000]
    except Exception as e:
        log("图文", f"读简介失败: {e}")

    log("图文", "调 douyin_note.py OCR...")
    ok, out, err = run([PY, str(Path(__file__).parent / "douyin_note.py"), url], timeout=180)
    if ok and out.strip():
        lines = [l.strip() for l in out.split("\n") if l.strip()
                 and not l.startswith("📖") and not l.startswith("📄")]
        noise = ["下载", "桌面", "快捷", "保存登录", "取消", "保存",
                 "浏览器", "静音", "充钻石", "客户端", "壁纸", "通知",
                 "消息", "粉丝", "获赞"]
        lines = [l for l in lines if not any(k in l[:15] for k in noise)]
        if lines:
            log("图文", f"OCR 成功 ({len(lines)} 行)")
            return "\n".join(lines)[:5000]

    log("图文", "提取失败")
    return ""


# ══════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="link-distill — 链接 → 蒸馏 → 入库")
    ap.add_argument("url", help="抖音/B站/YouTube 等链接")
    args = ap.parse_args()

    t0 = time.time()

    # ── 检测类型 ──
    log("检测", "判断图文/视频...")
    is_note = False
    try:
        import asyncio
        from playwright.async_api import async_playwright

        async def check():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(args.url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.5)
                u = page.url
                await browser.close()
                return u

        final_url = asyncio.run(check())
        is_note = "/note/" in final_url
        log("检测", "图文" if is_note else "视频")
    except Exception as e:
        log("检测", f"跳过（按视频处理）: {e}")

    # ── 图文路径 ──
    if is_note:
        text = extract_note(args.url)
        if not text:
            print("❌ 图文提取失败")
            return
        analysis = step_distill(text)
        step_save(analysis, text, f"{time.time() - t0:.0f}s")
        return

    # ── 视频路径 ──
    audio = step_download(args.url)
    if not audio:
        return

    text = step_transcribe(audio)
    audio.unlink(missing_ok=True)

    if text:
        analysis = step_distill(text)
        step_save(analysis, text, f"{time.time() - t0:.0f}s")
    else:
        print("❌ [转录] 未能转出文字，流程终止")


if __name__ == "__main__":
    main()
