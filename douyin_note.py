#!/usr/bin/env python3
"""抖音图文内容提取 — 先用 cookies 登录，无法访问时报错不瞎编"""
import asyncio, json, os, sys, subprocess, re
from pathlib import Path
from playwright.async_api import async_playwright

AUTOGLM_SKILL_DIR = Path("C:/Users/windows/.openclaw-autoclaw/skills/autoglm-image-recognition")
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
COOKIES_JSON = Path(__file__).parent.parent / "douyin-downloader" / "config" / "cookies.json"


def auto_ocr(img_path):
    r = subprocess.run([sys.executable, str(AUTOGLM_SKILL_DIR / "upload-mix.py"), str(img_path)],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0: return ""
    url = json.loads(r.stdout)["data"]["oss_info"][0]["oss_url"]
    r2 = subprocess.run([sys.executable, str(AUTOGLM_SKILL_DIR / "image-recognition.py"), url],
        capture_output=True, text=True, timeout=30)
    if r2.returncode != 0: return ""
    return json.loads(r2.stdout)["data"]["text"]


def is_login_page(title, ocr_text):
    """判断页面是否被登录墙挡住"""
    keywords = ["登录", "验证码", "captcha", "安全验证", "login"]
    combined = (title + " " + ocr_text).lower()
    for k in keywords:
        if k.lower() in combined:
            return True
    # 如果页面没有正文内容只有 UI，也是被挡住了
    if len(ocr_text) < 50:
        return True
    return False


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("⚠ 请提供抖音图文链接", flush=True)
        return

    print(f"📖 打开图文...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()

        # 加载 cookies
        if COOKIES_JSON.exists():
            try:
                cookies_data = json.loads(COOKIES_JSON.read_text())
                cookies = [{"name": k, "value": v, "domain": ".douyin.com", "path": "/"} for k, v in cookies_data.items()]
                await ctx.add_cookies(cookies)
            except: pass

        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        title = await page.title()
        print(f"  页面标题: {title}", flush=True)

        # 截整体图 OCR 判断是否登录墙
        full_img = WORK_DIR / "full.png"
        await page.screenshot(path=str(full_img))
        ocr_text = auto_ocr(full_img) or ""
        
        if is_login_page(title, ocr_text):
            print("  ❌ 需要登录才能查看图文内容", flush=True)
            print("  运行 python douyin_login.py 扫码登录后重试", flush=True)
            await browser.close()
            return

        # 提取页面中的真实图片
        img_urls = await page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            return [...imgs].map(i => i.src).filter(s => s && s.startsWith('http') && !s.includes('log') && !s.includes('avatar'));
        }""")

        texts = []
        if img_urls:
            print(f"  📸 {len(img_urls)} 张图片", flush=True)
            for i, img_url in enumerate(img_urls[:10]):
                img_path = WORK_DIR / f"p{i}.jpg"
                subprocess.run(["curl", "-s", "-L", img_url, "-o", str(img_path), "--max-time", "15"], capture_output=True)
                if img_path.exists() and img_path.stat().st_size > 5000:
                    text = auto_ocr(img_path)
                    if text: texts.append(f"[图{i+1}] {text[:200]}")
                    img_path.unlink()

        if texts:
            print(f"\n📝 图文内容：\n" + "\n".join(texts), flush=True)
        else:
            print("  ⚠ 未能提取到图文内容", flush=True)

        await browser.close()

asyncio.run(main())
