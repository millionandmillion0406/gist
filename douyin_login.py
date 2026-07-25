#!/usr/bin/env python3
"""
抖音扫码登录工具 — 弹浏览器，你扫码，cookies 自动保存
"""
import asyncio, json, sys, os
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_PATH = Path(__file__).parent / "douyin-downloader" / "config" / "cookies.json"

async def main():
    print("🌐 打开浏览器，请扫码登录抖音...")
    print("   登录成功后浏览器会自动关闭，cookies 自动保存。")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded")

        # 等待登录成功（检测特定 cookie）
        logged_in = False
        for i in range(300):  # 最多等 5 分钟
            await asyncio.sleep(1)
            cookies = await context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            # 登录成功的标志：sessionid 或 sid_tt
            if cookie_dict.get("sessionid") or cookie_dict.get("sid_tt"):
                logged_in = True
                break

            if i % 30 == 0 and i > 0:
                print(f"   等待中... ({i//30}分钟)")

        if logged_in:
            # 保存 cookies
            COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
            all_cookies = {c["name"]: c["value"] for c in await context.cookies()}
            with open(COOKIES_PATH, "w", encoding="utf-8") as f:
                json.dump(all_cookies, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 登录成功！cookies 已保存到: {COOKIES_PATH}")
            print(f"   共 {len(all_cookies)} 个 cookies")
        else:
            print("\n⏰ 等待超时，未检测到登录")

        await browser.close()

asyncio.run(main())
