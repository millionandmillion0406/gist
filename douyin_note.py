#!/usr/bin/env python3
"""抖音图文提取：定位内容图片 → 下载 → OCR"""
import asyncio, sys, os, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

try:
    import easyocr
    READER = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
except:
    READER = None

TMP = Path(__file__).parent / "tmp"; TMP.mkdir(exist_ok=True)

def ocr(path):
    if not READER: return []
    from PIL import Image; import numpy as np
    r = READER.readtext(np.array(Image.open(path))[:,:,::-1], detail=0, paragraph=True)
    return [t for t in r if len(t) > 5]


async def dl_via_page(page, url, path):
    """用浏览器页面下载图片（带cookies和referer）"""
    resp = await page.context.request.get(url)
    if resp.status == 200:
        path.write_bytes(await resp.body())
        return True
    return False


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url: print("⚠ 请提供链接"); return

    print("📖 打开图文...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 900})
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)
        print(f"  标题: {(await page.title())[:80]}", flush=True)

        # 翻页加载
        for i in range(15):
            await page.keyboard.press("ArrowRight")
            await asyncio.sleep(1.5)

        # 提取内容图片（排除头像/图标/UI元素），保留完整URL含签名
        imgs = await page.evaluate('''() =>
            [...document.querySelectorAll('img')]
                .filter(i => {
                    const w = i.naturalWidth || i.width;
                    const h = i.naturalHeight || i.height;
                    return w >= 300 && h >= 300 && !i.src.includes('avatar') && !i.src.includes('emblem');
                })
                .map(i => i.src)
        ''')
        imgs = list(dict.fromkeys(imgs))  # 去重
        print(f"  内容图片 {len(imgs)} 张", flush=True)

        seen = set()
        for i, src in enumerate(imgs):
            path = TMP / f"n{i}.jpg"
            try:
                if not await dl_via_page(page, src, path): continue
                if os.path.getsize(path) < 5000: continue
                texts = [t for t in ocr(path) if t not in seen]
                for t in texts:
                    seen.add(t)
                    if sum('\u4e00' <= c <= '\u9fff' for c in t) > 3:
                        noise = ["登录","下载","客户端","壁纸","通知","消息","粉丝","获赞"]
                        if not any(k in t[:15] for k in noise):
                            print(f"  {t[:200]}", flush=True)
            except: pass
            finally:
                if path.exists(): path.unlink()

        if not seen: print("\n⚠ 未提取到内容", flush=True)
        await browser.close()

asyncio.run(main())
