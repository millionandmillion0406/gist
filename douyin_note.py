#!/usr/bin/env python3
"""抖音图文提取：下载每张图片 → OCR → 输出文字"""
import asyncio, sys, os, re
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

        # 翻页加载所有图片
        for i in range(15):
            await page.keyboard.press("ArrowRight")
            await asyncio.sleep(1.5)

        # 获取所有图片URL（不做过滤，只看大小）
        imgs = await page.evaluate('''() =>
            [...document.querySelectorAll('img')]
                .filter(i => (i.naturalWidth || i.width) >= 200 && (i.naturalHeight || i.height) >= 200)
                .map(i => i.src)
        ''')
        # 去重
        seen_urls = set()
        unique = []
        for u in imgs:
            base = u.split('?')[0]
            if base not in seen_urls:
                seen_urls.add(base)
                unique.append(u)

        print(f"  图片 {len(unique)} 张", flush=True)

        all_text = set()
        for i, src in enumerate(unique[:10]):  # 最多10张
            path = TMP / f"n{i}.jpg"
            try:
                # 用 Playwright 下载（带 cookies）
                resp = await page.context.request.get(src, timeout=15000)
                if resp.status != 200: continue
                data = await resp.body()
                if len(data) < 5000: continue
                with open(path, 'wb') as f: f.write(data)
                texts = ocr(path)
                for t in texts:
                    cn = sum(1 for c in t if '\u4e00' <= c <= '\u9fff')
                    if cn > 3 and t not in all_text:
                        all_text.add(t)
                        noise = ["登录","下载","客户端","壁纸","通知","消息","粉丝","获赞","充钻石"]
                        if not any(k in t[:15] for k in noise):
                            print(f"  {t[:200]}", flush=True)
            except: pass
            finally:
                if path.exists(): path.unlink()

        if not all_text:
            # 没有图片文字，读简介
            desc = await page.evaluate('() => document.querySelector("meta[name=description]")?.content || ""')
            if desc:
                print(f"  (无图文字，来自简介) {desc[:300]}", flush=True)

        await browser.close()

asyncio.run(main())
