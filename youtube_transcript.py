#!/usr/bin/env python3
"""Fetch a YouTube transcript through a browser-rendered transcript service."""
import argparse
import asyncio
import html
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote

from playwright.async_api import async_playwright


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def fetch_direct(url):
    video_id = ""
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    elif "youtube.com" in url and "v=" in url:
        video_id = url.split("v=", 1)[1].split("&", 1)[0]
    if not video_id:
        return "", ""

    payload = json.dumps({
        "videoId": video_id,
        "context": {"client": {
            "clientName": "ANDROID", "clientVersion": "20.10.38",
            "androidSdkVersion": 35, "hl": "zh-TW", "gl": "TW",
        }},
    }).encode()
    request = urllib.request.Request(
        "https://www.youtube-nocookie.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "com.google.android.youtube/20.10.38"},
    )
    response = json.loads(urllib.request.urlopen(request, timeout=60).read().decode("utf-8"))
    if response.get("playabilityStatus", {}).get("status") != "OK":
        return "", ""
    title = response.get("videoDetails", {}).get("title", "")
    tracks = response.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    if not tracks:
        return title, ""
    track = next((x for x in tracks if x.get("languageCode", "").startswith("zh")), tracks[0])
    caption_url = track.get("baseUrl", "")
    if caption_url.startswith("/"):
        caption_url = "https://www.youtube-nocookie.com" + caption_url
    caption_request = urllib.request.Request(caption_url, headers={"User-Agent": "Mozilla/5.0"})
    xml_data = urllib.request.urlopen(caption_request, timeout=60).read()
    root = ET.fromstring(xml_data)
    lines = []
    for node in root.iter("p"):
        text = html.unescape("".join(node.itertext())).strip()
        if text:
            lines.append(text)
    return title, "\n".join(lines)


async def fetch(url, language):
    target = f"https://tactiq.io/tools/run/youtube_transcript?yt={quote(url, safe='')}&lang={quote(language)}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        api_errors = []
        page.on("response", lambda response: api_errors.append(f"{response.status} {response.url}") if "transcript" in response.url and response.status >= 400 else None)
        await page.goto(target, wait_until="domcontentloaded", timeout=90_000)
        try:
            await page.wait_for_function(
                """() => {
                    const node = document.querySelector('#transcript');
                    return node && node.innerText.trim().length > 50;
                }""",
                timeout=90_000,
            )
        except Exception:
            pass
        title = await page.title()
        transcript = await page.locator("#transcript").inner_text() if await page.locator("#transcript").count() else ""
        body = (await page.locator("body").inner_text()).strip()
        await browser.close()
        if transcript.strip():
            print(f"标题：{title}")
            print(transcript.strip())
            return 0
        if api_errors:
            print("接口错误：" + "; ".join(api_errors[-3:]), file=sys.stderr)
        if body:
            print("页面信息：" + body[-1000:], file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--language", default="zh-TW")
    args = parser.parse_args()
    try:
        title, transcript = fetch_direct(args.url)
        if transcript:
            if title:
                print(f"标题：{title}")
            print(transcript)
            return 0
    except Exception as exc:
        print(f"播放器字幕读取失败: {exc}", file=sys.stderr)
    return asyncio.run(fetch(args.url, args.language))


if __name__ == "__main__":
    raise SystemExit(main())
