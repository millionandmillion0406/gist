#!/usr/bin/env python3
"""
gist: Download video audio + transcribe with Whisper + optional OCR.

Usage:
  python gist.py <video-url>                 # 音频转文字
  python gist.py <video-url> --ocr           # 音频 + 画面文字识别
  python gist.py <video-url> --model small   # 更准
  python gist.py <video-url> --json          # JSON 输出
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Config ──
WORK_DIR = Path(__file__).parent / "tmp"
WORK_DIR.mkdir(exist_ok=True)
WHISPER_MODEL = "base"
LANG = "zh"
OCR_INTERVAL = 5  # seconds between frames for OCR


def find_python():
    """Find Python 3.12+ with whisper & torch."""
    candidates = [
        sys.executable,
        r"C:\Users\windows\AppData\Local\Programs\Python\Python312\python.exe",
        "python3", "python",
    ]
    for c in candidates:
        if not c:
            continue
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
HAS_EASYOCR = False
try:
    subprocess.run(
        [PYTHON, "-c", "import easyocr; print('ok')"],
        capture_output=True, text=True, timeout=10
    )
    HAS_EASYOCR = True
except Exception:
    pass


# ── Audio ──

def download_audio(url: str) -> Path:
    """Download audio from video URL."""
    print(f"🎵 Downloading audio...", flush=True)
    output = WORK_DIR / "%(id)s.%(ext)s"
    result = subprocess.run([
        "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "-o", str(output), "--no-playlist", url,
    ], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ yt-dlp failed:\n{result.stderr}", flush=True)
        sys.exit(1)
    for f in WORK_DIR.glob("*.mp3"):
        return f
    for f in WORK_DIR.glob("*"):
        if f.is_file() and f.suffix not in (".json", ".txt"):
            return f
    print("❌ No audio file found", flush=True)
    sys.exit(1)


def download_video(url: str) -> tuple[Path, float]:
    """Download video and return (video_path, duration_seconds)."""
    print(f"🎬 Downloading video...", flush=True)

    # First get duration
    duration = 0
    try:
        dur_result = subprocess.run([
            "yt-dlp", "--print", "%(duration)s",
            "--no-playlist", url,
        ], capture_output=True, text=True, timeout=30)
        if dur_result.returncode == 0:
            duration = float(dur_result.stdout.strip().split("\n")[0])
    except Exception:
        pass

    # Then download (no --print flag, it prevents download)
    result = subprocess.run([
        "yt-dlp", "-f", "bv+ba/b",
        "-o", str(WORK_DIR / "video_%(id)s.%(ext)s"),
        "--no-playlist",
        "--merge-output-format", "mp4",
        url,
    ], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ yt-dlp failed:\n{result.stderr[:500]}", flush=True)
        sys.exit(1)

    files = list(WORK_DIR.iterdir())
    for f in files:
        if "video_" in f.name and f.suffix != ".mp3":
            return f, duration

    print("❌ No video file found", flush=True)
    print(f"stdout: {result.stdout[:200]}", flush=True)
    sys.exit(1)


# ── Transcribe ──

def transcribe(audio_path: Path, model_name: str, lang: str) -> dict:
    """Transcribe audio with Whisper."""
    print(f"🧠 Transcribing with whisper ({model_name})...", flush=True)
    code = f"""
import whisper, json, time
t0 = time.time()
model = whisper.load_model("{model_name}")
print(f"  ⏱ Model loaded in {{time.time()-t0:.1f}}s", flush=True)
t1 = time.time()
result = model.transcribe(
    r"{audio_path}", language={f'"{lang}"' if lang != "auto" else "None"}, verbose=False,
)
print(f"  ⏱ Transcribed in {{time.time()-t1:.1f}}s", flush=True)
print("===TRANSCRIPT_START===", flush=True)
print(result["text"].strip(), flush=True)
print("===TRANSCRIPT_END===", flush=True)
if result.get("segments"):
    segs = [{{"start": s["start"], "end": s["end"], "text": s["text"].strip()}} for s in result["segments"] if s["text"].strip()]
    print("===SEGMENTS_START===", flush=True)
    print(json.dumps(segs, ensure_ascii=False), flush=True)
    print("===SEGMENTS_END===", flush=True)
"""
    result = subprocess.run(
        [PYTHON, "-c", code], capture_output=True, text=True, timeout=3600
    )
    if result.returncode != 0:
        print(f"❌ Whisper failed:\n{result.stderr}", flush=True)
        sys.exit(1)

    output = {"text": "", "segments": []}
    in_text = in_segs = False
    for line in result.stdout.split("\n"):
        if "===TRANSCRIPT_START===" in line: in_text = True; continue
        if "===TRANSCRIPT_END===" in line: in_text = False; continue
        if "===SEGMENTS_START===" in line: in_segs = True; continue
        if "===SEGMENTS_END===" in line: in_segs = False; continue
        if in_text: output["text"] += line + "\n"
        if in_segs:
            try: output["segments"] = json.loads(line)
            except json.JSONDecodeError: pass
    for line in result.stdout.split("\n"):
        if "Model loaded" in line or "Transcribed" in line:
            print(f"  {line.strip()}", flush=True)
    if result.stderr:
        for line in result.stderr.split("\n"):
            if "warning" in line.lower():
                print(f"  ⚠ {line.strip()}", flush=True)
    return output


# ── OCR ──

def ocr_frames(video_path: Path, duration: float, interval: int) -> list:
    """Extract frames from video and run OCR. Returns list of (time_sec, text)."""
    if not HAS_EASYOCR:
        print("⚠ EasyOCR not installed. Run: pip install easyocr", flush=True)
        return []

    print(f"👁️  OCR: extracting frames every {interval}s...", flush=True)

    # Step 1: Extract frames with ffmpeg
    frames_dir = WORK_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)
    # Clear old frames
    for f in frames_dir.glob("*.jpg"):
        f.unlink()

    # Calculate frame timestamps
    timestamps = list(range(0, int(duration), interval))
    if timestamps and timestamps[-1] < int(duration) - 2:
        timestamps.append(int(duration))

    # Extract frames using ffmpeg
    for ts in timestamps:
        frame_path = frames_dir / f"frame_{ts:04d}.jpg"
        subprocess.run([
            "ffmpeg", "-ss", str(ts), "-i", str(video_path),
            "-vframes", "1", "-q:v", "2", str(frame_path),
        ], capture_output=True, text=True, timeout=30)

    extracted = list(frames_dir.glob("*.jpg"))
    print(f"  📸 Extracted {len(extracted)} frames", flush=True)

    if not extracted:
        return []

    # Step 2: OCR each frame
    print(f"  🔍 Running OCR...", flush=True)
    code = f"""
import easyocr, json, sys, os, time
from pathlib import Path
t0 = time.time()
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
print(f"  ⏱ OCR model loaded in {{time.time()-t0:.1f}}s", flush=True)
frames_dir = r"{frames_dir}"
results = []
for f in sorted(os.listdir(frames_dir)):
    if not f.endswith('.jpg'): continue
    ts = int(f.split('_')[1].split('.')[0])
    path = os.path.join(frames_dir, f)
    try:
        txts = reader.readtext(path, detail=0, paragraph=True)
        text = ' '.join(txts).strip()
        if text and len(text) > 2:
            results.append({{"time": ts, "text": text}})
    except:
        pass
print("===OCR_START===", flush=True)
print(json.dumps(results, ensure_ascii=False), flush=True)
print("===OCR_END===", flush=True)
"""
    result = subprocess.run(
        [PYTHON, "-c", code], capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        print(f"  ⚠ OCR error: {result.stderr[:200]}", flush=True)
        return []

    for line in result.stdout.split("\n"):
        if "OCR model loaded" in line:
            print(f"  {line.strip()}", flush=True)

    results = []
    in_ocr = False
    for line in result.stdout.split("\n"):
        if "===OCR_START===" in line: in_ocr = True; continue
        if "===OCR_END===" in line: in_ocr = False; continue
        if in_ocr:
            try: results = json.loads(line); break
            except json.JSONDecodeError: pass

    # Cleanup frames
    for f in frames_dir.glob("*.jpg"):
        f.unlink()

    print(f"  ✅ OCR found text in {len(results)} frames", flush=True)
    return results


# ── Format ──

def format_output(transcript: dict, ocr_results: list, title: str = "") -> str:
    lines = []
    if title:
        lines.append(f"# 🎬 {title}")
        lines.append("")
    # Audio transcript
    lines.append("## 🎤 音频转录")
    lines.append(transcript["text"].strip())
    lines.append("")
    # Timestamps
    if transcript.get("segments"):
        lines.append("### 📌 时间戳")
        segs = transcript["segments"][:50]
        for seg in segs:
            if seg["text"]:
                start = time.strftime("%M:%S", time.gmtime(seg["start"]))
                lines.append(f"[{start}] {seg['text']}")
        if len(transcript["segments"]) > 50:
            lines.append(f"... 共 {len(transcript['segments'])} 段")
        lines.append("")
    # OCR text
    if ocr_results:
        lines.append("## 👁️ 画面文字（OCR）")
        for r in ocr_results:
            ts = time.strftime("%M:%S", time.gmtime(r["time"]))
            lines.append(f"[{ts}] {r['text']}")
    return "\n".join(lines)


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(description="gist: Video → text + OCR")
    parser.add_argument("url", help="视频链接")
    parser.add_argument("--model", default=WHISPER_MODEL, choices=["base", "small", "medium", "large"])
    parser.add_argument("--lang", default=LANG, help="zh / en / auto")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--ocr", action="store_true", help="启用画面文字识别（需 easyocr）")
    parser.add_argument("--ocr-interval", type=int, default=OCR_INTERVAL, help="OCR 抽帧间隔（秒）")
    args = parser.parse_args()

    print(f"🔧 Using Python: {PYTHON}", flush=True)

    # Step 1: Download audio (always)
    audio_path = download_audio(args.url)
    print(f"  ✅ Audio: {audio_path.name} ({audio_path.stat().st_size // 1024}KB)", flush=True)

    # Step 2: Transcribe
    transcript = transcribe(audio_path, args.model, args.lang)

    # Step 3: OCR (optional)
    ocr_results = []
    if args.ocr:
        video_path, duration = download_video(args.url)
        print(f"  ✅ Video: {video_path.name} ({duration}s)", flush=True)
        ocr_results = ocr_frames(video_path, duration, args.ocr_interval)
        video_path.unlink(missing_ok=True)

    # Step 4: Output
    if args.json:
        output = {
            "title": args.title or "",
            "transcript": transcript["text"].strip(),
            "segments": transcript.get("segments", []),
            "ocr": ocr_results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + format_output(transcript, ocr_results, args.title))

    # Cleanup
    audio_path.unlink(missing_ok=True)
    print(f"\n✅ Done", flush=True)


if __name__ == "__main__":
    main()
