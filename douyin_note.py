#!/usr/bin/env python3
"""抖音图文内容提取 — 优先用 Chrome 登录态，没有则用 cookies"""
import asyncio, json, os, sys, subprocess, re
from pathlib import Path
from playwright.async_api import async_playwright

AUTOGLM = Path("C:/Users/windows/.openclaw-autoclaw/skills/autoglm-image-recognition")
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
COOKIES_JSON = Path(__file__).parent.parent / "douyin-downloader" / "config" / "cookies.json"


def auto_ocr(img_path):
    r = subprocess.run([sys.executable, str(AUTOGLM / "upload-mix.py"), str(img_path)],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0: return ""
    url = json.loads(r.stdout)["data"]["oss_info"][0]["oss_url"]
    r2 = subprocess.run([sys.executable, str(AUTOGLM / "image-recognition.py"), url],
        capture_output=True, text=True, timeout=30)
    if r2.returncode != 0: return ""
    return json.loads(r2.stdout)["data"]["text"]


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url: print("⚠ 请提供链接", flush=True); return

    print(f"📖 打开图文...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        to_close = browser

        # 从 json cookies 设置登录态
        if COOKIES_JSON.exists():
            try:
                cd = json.loads(COOKIES_JSON.read_text())
                douyin_cookies = []
                for k, v in cd.items():
                    douyin_cookies.append({"name": k, "value": v, "domain": ".douyin.com", "path": "/"})
                    douyin_cookies.append({"name": k, "value": v, "domain": ".amemv.com", "path": "/"})
                await ctx.add_cookies(douyin_cookies)
            except Exception as e:
                print(f"  ⚠ cookies 加载失败: {e}", flush=True)

        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

            title = await page.title()
            print(f"  页面标题: {title}", flush=True)

            # 截图检测是否登录墙
            full_img = WORK_DIR / "full.png"
            await page.screenshot(path=str(full_img))
            ocr_text = auto_ocr(full_img) or ""

            if "登录" in title and ("注册" in title or "密码" in title):
                print("  ❌ 需要登录抖音后才能查看", flush=True)
                print("  提示：在 Chrome 中登录抖音后重试", flush=True)
                return

            # 从页面直接提取正文文字
            text = await page.evaluate("""() => {
                // 尝试多种选择器找正文
                const selectors = ['article', '[class*="content"]', '[class*="text"]', 'main', '.note-text', '[class*="article"]'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.length > 50) return el.textContent;
                }
                // 兜底：取页面可见文本
                const body = document.body;
                const clone = body.cloneNode(true);
                // 移除脚本、样式等
                clone.querySelectorAll('script,style,nav,header,footer,[class*="nav"],[class*="header"],[class*="footer"]').forEach(e => e.remove());
                return clone.textContent.replace(/\\s+/g, ' ').trim();
            }""") or ""

            if text and len(text) > 50:
                print(f"\n📝 图文内容：\n{text[:500]}", flush=True)
            else:
                # 兜底：截图 OCR
                img = WORK_DIR / "page.png"
                await page.screenshot(path=str(img), full_page=True)
                ocr_text = auto_ocr(img) or ""
                lines = ocr_text.split("\n")
                content = [l for l in lines if len(l) > 15 and not any(k in l for k in ["界面", "按钮", "图标", "布局", "截图", "导航"])]
                print(f"\n📝 图文内容：\n" + "\n".join(content[:5]) if content else ocr_text[:300], flush=True)

        finally:
            await to_close.close()

asyncio.run(main())
