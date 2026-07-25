#!/usr/bin/env python3
"""抖音图文内容提取"""
import asyncio, json, os, sys, subprocess, re
from pathlib import Path
from playwright.async_api import async_playwright

AUTOGLM_SKILL_DIR = Path("C:/Users/windows/.openclaw-autoclaw/skills/autoglm-image-recognition")
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)

def auto_ocr(img_path):
    """AutoGLM 读图"""
    r = subprocess.run([sys.executable, str(AUTOGLM_SKILL_DIR / "upload-mix.py"), str(img_path)],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0: return ""
    url = json.loads(r.stdout)["data"]["oss_info"][0]["oss_url"]
    r2 = subprocess.run([sys.executable, str(AUTOGLM_SKILL_DIR / "image-recognition.py"), url],
        capture_output=True, text=True, timeout=30)
    if r2.returncode != 0: return ""
    return json.loads(r2.stdout)["data"]["text"]

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://v.douyin.com/6WMrsyQuU_E/"
    
    print(f"📖 打开图文...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)
        
        # 1. 提取页面中的图片 URL
        img_urls = await page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            return [...imgs].map(i => i.src).filter(s => s && s.match(s => s.startsWith('http'))).slice(0, 20);
        }""")
        
        texts = []
        if img_urls:
            print(f"  📸 {len(img_urls)} 张图片", flush=True)
            for i, img_url in enumerate(img_urls[:10]):
                # 下载图片
                img_path = WORK_DIR / f"note_{i}.jpg"
                subprocess.run(["curl", "-s", img_url, "-o", str(img_path), "--max-time", "10"], capture_output=True)
                if img_path.exists() and img_path.stat().st_size > 1000:
                    text = auto_ocr(img_path)
                    if text: texts.append(f"[图{i+1}] {text[:200]}")
                    img_path.unlink()
        
        # 2. 取内容区域截图兜底
        if not texts:
            await page.screenshot(path=str(WORK_DIR / "note.png"))
            text = auto_ocr(WORK_DIR / "note.png")
            if text:
                # 只取内容部分（跳过导航描述）
                lines = text.split("。")
                texts = [l for l in lines if len(l) > 10][:5]
        
        print(f"\n📝 图文内容：\n" + "\n".join(texts) if texts else "⚠ 无法读取", flush=True)
        await browser.close()

asyncio.run(main())
