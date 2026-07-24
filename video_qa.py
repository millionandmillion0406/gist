#!/usr/bin/env python3
"""
video-qa: Download video audio + transcribe with Whisper.
Universal — works with any AI agent (Claude Code, Codex, ZCode, etc.)

Usage:
  python video_qa.py <video-url> [--model base|small|medium] [--lang zh|en]

Examples:
  python video_qa.py https://www.bilibili.com/video/BV1GJ411x7e7
  python video_qa.py https://www.bilibili.com/video/xxx --model small
  python video_qa.py https://www.douyin.com/video/xxx --lang zh
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Config ──────────────────────────────────────────
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
WHISPER_MODEL = "base"  # base | small | medium | large
LANG = "zh"  # zh | en | auto

# ── Platform detection ──────────────────────────────
# Find the right Python (this script may be invoked by any agent)
def find_python():
    """Find Python 3.12+ with whisper & torch installed."""
    candidates = [
        sys.executable,
        r"C:\Users\windows\AppData\Local\Programs\Python\Python312\python.exe",
        r"C:\Users\windows\AppData\Local\Programs\Python\Python313\python.exe",
        "python3", "python",
    ]
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            out = subprocess.run(
                [c, "-c", "import whisper, torch; print('ok')"],
                capture_output=True, text=True, timeout=10
            )
            if out.returncode == 0:
                return c
        except Exception:
            continue
    return sys.executable

PYTHON = find_python()


# ── Core functions ──────────────────────────────────

def download_audio(url: str) -> Path:
    """Download audio from video URL using yt-dlp."""
    print(f"🎵 Downloading audio from: {url}", flush=True)
    output = WORK_DIR / "%(id)s.%(ext)s"
    result = subprocess.run([
        "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "-o", str(output),
        "--no-playlist",
        url,
    ], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ yt-dlp failed:\n{result.stderr}", flush=True)
        sys.exit(1)

    # Find the downloaded file
    for f in WORK_DIR.glob("*.mp3"):
        return f
    for f in WORK_DIR.glob("*"):
        if f.is_file() and f.suffix not in (".json", ".txt"):
            return f
    print("❌ No audio file found after download", flush=True)
    sys.exit(1)


def transcribe(audio_path: Path, model_name: str, lang: str) -> dict:
    """Transcribe audio with Whisper (runs in subprocess to keep deps isolated)."""
    print(f"🧠 Transcribing with whisper ({model_name})...", flush=True)

    code = f"""
import whisper, json, time
t0 = time.time()
model = whisper.load_model("{model_name}")
print(f"Model loaded in {{time.time()-t0:.1f}}s", flush=True)
t1 = time.time()
result = model.transcribe(
    r"{audio_path}",
    language={f'"{lang}"' if lang != "auto" else "None"},
    verbose=False,
)
print(f"Transcribed in {{time.time()-t1:.1f}}s", flush=True)
print("===TRANSCRIPT_START===", flush=True)
print(result["text"].strip(), flush=True)
print("===TRANSCRIPT_END===", flush=True)
if result.get("segments"):
    segs = []
    for s in result["segments"]:
        segs.append({{"start": s["start"], "end": s["end"], "text": s["text"].strip()}})
    print("===SEGMENTS_START===", flush=True)
    print(json.dumps(segs, ensure_ascii=False), flush=True)
    print("===SEGMENTS_END===", flush=True)
"""
    result = subprocess.run(
        [PYTHON, "-c", code],
        capture_output=True, text=True, timeout=1800
    )
    if result.returncode != 0:
        print(f"❌ Whisper failed:\n{result.stderr}", flush=True)
        sys.exit(1)

    output = {"text": "", "segments": []}
    in_text = False
    in_segs = False
    for line in result.stdout.split("\n"):
        if line.strip() == "===TRANSCRIPT_START===":
            in_text = True
            continue
        if line.strip() == "===TRANSCRIPT_END===":
            in_text = False
            continue
        if line.strip() == "===SEGMENTS_START===":
            in_segs = True
            continue
        if line.strip() == "===SEGMENTS_END===":
            in_segs = False
            continue
        if in_text:
            output["text"] += line + "\n"
        if in_segs:
            try:
                output["segments"] = json.loads(line)
            except json.JSONDecodeError:
                pass

    # Also capture model loading / timing info
    for line in result.stdout.split("\n"):
        if "Model loaded" in line or "Transcribed" in line:
            print(f"  ⏱ {line.strip()}", flush=True)

    if result.stderr:
        for line in result.stderr.split("\n"):
            if "warning" in line.lower() or "error" in line.lower():
                print(f"  ⚠ {line.strip()}", flush=True)

    return output


def format_output(transcript: dict, title: str = "") -> str:
    """Format transcript for display."""
    lines = []
    if title:
        lines.append(f"# 🎬 {title}")
        lines.append("")
    lines.append(transcript["text"].strip())
    lines.append("")
    if transcript.get("segments"):
        lines.append("---")
        lines.append("### 📌 Timestamps")
        for seg in transcript["segments"]:
            if seg["text"]:
                start = time.strftime("%M:%S", time.gmtime(seg["start"]))
                lines.append(f"[{start}] {seg['text']}")
    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="video-qa: Download + transcribe any video")
    parser.add_argument("url", help="Video URL (Bilibili, Douyin, YouTube, etc.)")
    parser.add_argument("--model", default=WHISPER_MODEL, choices=["base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--lang", default=LANG, help="Language code (zh, en, auto)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--title", default="", help="Optional video title")
    args = parser.parse_args()

    print(f"🔧 Using Python: {PYTHON}", flush=True)

    # Step 1: Download audio
    audio_path = download_audio(args.url)
    print(f"  ✅ Audio: {audio_path.name} ({audio_path.stat().st_size / 1024:.0f}KB)", flush=True)

    # Step 2: Transcribe
    transcript = transcribe(audio_path, args.model, args.lang)

    # Step 3: Output
    if args.json:
        output = {
            "title": args.title or "",
            "text": transcript["text"].strip(),
            "segments": transcript.get("segments", []),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + format_output(transcript, args.title))

    # Cleanup
    audio_path.unlink(missing_ok=True)
    print(f"\n✅ Done — audio cleaned up", flush=True)


if __name__ == "__main__":
    main()
