#!/usr/bin/env python3
"""抖音图文提取：自动翻页 + EasyOCR 读文字，给所有人用"""
import asyncio, json, os, sys, subprocess
from pathlib import Path
from playwright.async_api import async_playwright

try:
    import easyocr
    READER = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
except:
    READER = None

WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
COOKIES_JSON = Path(__file__).parent.parent / "douyin-downloader" / "config" / "cookies.json"


def ocr_image(img_path):
    """EasyOCR 读图，返回文本列表"""
    if not READER:
        return []
    from PIL import Image
    import numpy as np
    img = Image.open(img_path)
    results = READER.readtext(np.array(img)[:, :, ::-1], detail=0, paragraph=True)
    return [r for r in results if len(r) > 5]


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("⚠ 请提供抖音图文链接"); return

    print("📖 打开图文...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()

        # 尝试加载 cookies
        if COOKIES_JSON.exists():
            try:
                cd = json.loads(COOKIES_JSON.read_text())
                await ctx.add_cookies([{"name":k,"value":v,"domain":".douyin.com","path":"/"} for k,v in cd.items()])
            except: pass

        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        title = await page.title()
        print(f"  标题: {title}", flush=True)

        # 翻页遍历所有图片
        all_texts = set()
        w, h = 1280, 900

        for i in range(6):  # 最多 6 页
            screenshot = WORK_DIR / f"p{i}.png"
            await page.screenshot(path=str(screenshot))

            texts = ocr_image(screenshot)
            new_texts = [t for t in texts if t not in all_texts]
            if new_texts:
                all_texts.update(new_texts)
                # 过滤 UI 文字
                useful = [t for t in new_texts if not any(k in t[:15] for k in ["登录","扫码","验证码","手机号","下载客户端","协议","隐私"]) and len(t) > 10]
                if useful:
                    print(f"\n📄 第 {len(all_texts)} 页内容:", flush=True)
                    for t in useful:
                        print(f"  {t[:100]}", flush=True)

            # 滑动到下一张
            await page.mouse.move(w // 2 + 200, h // 2)
            await page.mouse.down()
            await page.mouse.move(w // 2 - 300, h // 2)
            await page.mouse.up()
            await asyncio.sleep(2)

        if not all_texts:
            print("\n⚠ 未能提取到内容（可能需要登录抖音）", flush=True)

        await browser.close()

asyncio.run(main())
