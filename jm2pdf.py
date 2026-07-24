#!/usr/bin/env python3
"""
jm2pdf: JM 本号 → 压缩 PDF → 发送到 QQ 邮箱

Usage:
  python jm2pdf.py <本号>
  python jm2pdf.py 123456
  python jm2pdf.py JM289490
"""

import argparse
import os
import smtplib
import subprocess
import sys
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def find_python():
    """Find Python with jmcomic installed."""
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
                [c, "-c", "import jmcomic; print('ok')"],
                capture_output=True, text=True, timeout=10
            )
            if out.returncode == 0:
                return c
        except Exception:
            continue
    return sys.executable


PYTHON = find_python()
print(f"🔧 Using Python: {PYTHON}", flush=True)


# ── 配置 ──
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
FROM_EMAIL = "2233873332@qq.com"
FROM_PASS = "xyrzharzncuadida"
TO_EMAIL = "3277681859@qq.com"

JM2COMIC_DIR = Path(__file__).resolve().parent.parent / "jm2comic"
OUTPUT_DIR = Path(__file__).resolve().parent / "jm_output"


def get_album_id(raw: str) -> str:
    """从输入里提取纯数字本号"""
    raw = raw.strip().lower().replace("jm", "").replace(" ", "")
    return raw


def download(album_id: str) -> dict:
    """下载漫画，返回图片列表"""
    print(f"📥 下载 JM{album_id} ...", flush=True)
    sys.path.insert(0, str(JM2COMIC_DIR))
    from core.downloader import Downloader

    dl = Downloader(output_dir=str(OUTPUT_DIR))
    result = dl.download_album(album_id)
    print(f"  ✅ {result['title']} — {len(result['images'])} 页", flush=True)
    return result


def compress_and_pdf(result: dict, quality: int = 85, max_size: int = 2000) -> str:
    """压缩图片并生成 PDF"""
    print(f"🗜️  压缩图片 (quality={quality}, max={max_size}px)...", flush=True)
    sys.path.insert(0, str(JM2COMIC_DIR))
    from core.exporter import Exporter

    exporter = Exporter()
    compressed = exporter.compress_images(result["images"], quality=quality, max_size=max_size)
    print(f"  ✅ 压缩完成: {len(compressed)} 页", flush=True)

    pdf_path = str(OUTPUT_DIR / f"JM{result['album_id']}.pdf")
    print(f"📄 生成 PDF ...", flush=True)
    exporter.images_to_pdf(compressed, pdf_path)
    print(f"  ✅ PDF: {pdf_path}", flush=True)

    # 清理压缩临时文件
    exporter.cleanup_temp_files(compressed)

    return pdf_path


def send_email(pdf_path: str, album_id: str, title: str):
    """通过 QQ 邮箱发送 PDF"""
    print(f"📧 发送到 {TO_EMAIL} ...", flush=True)

    pdf_size = os.path.getsize(pdf_path) / 1024 / 1024

    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = f"JM{album_id} {title}"

    body = MIMEText(
        f"JM{album_id} · {title}\n"
        f"大小: {pdf_size:.1f}MB\n"
        f"发送时间: {time.strftime('%Y-%m-%d %H:%M')}",
        "plain", "utf-8"
    )
    msg.attach(body)

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
        msg.attach(part)

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(FROM_EMAIL, FROM_PASS)
        server.send_message(msg)
        server.quit()
        print(f"  ✅ 已发送 ({pdf_size:.1f}MB)", flush=True)
    except Exception as e:
        print(f"  ❌ 发送失败: {e}", flush=True)
        sys.exit(1)


def cleanup(album_id: str):
    """清理下载目录和 PDF"""
    import shutil
    album_dir = OUTPUT_DIR / album_id
    if album_dir.exists():
        shutil.rmtree(album_dir)
    pdf_path = OUTPUT_DIR / f"JM{album_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    print(f"  🧹 清理完成", flush=True)


def main():
    parser = argparse.ArgumentParser(description="jm2pdf: JM 本号 → PDF → 邮箱")
    parser.add_argument("id", help="JM 本号 (如 123456 或 JM289490)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG 压缩质量 (1-100, 默认85)")
    parser.add_argument("--max-size", type=int, default=2000, help="最大边长像素 (默认2000)")
    parser.add_argument("--no-send", action="store_true", help="只生成 PDF，不发邮件")
    parser.add_argument("--no-clean", action="store_true", help="保留下载文件")
    args = parser.parse_args()

    album_id = get_album_id(args.id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 查看信息
    print(f"\n🔍 查询 JM{album_id} ...", flush=True)
    sys.path.insert(0, str(JM2COMIC_DIR))
    from core.downloader import Downloader
    dl = Downloader(output_dir=str(OUTPUT_DIR))
    info = dl.get_album_info(album_id)
    if "error" in info:
        print(f"  ❌ {info['error']}", flush=True)
        sys.exit(1)
    print(f"  📖 {info['title']} · {info['photo_count']} 页", flush=True)

    # 2. 下载
    result = download(album_id)

    # 3. 压缩 + PDF
    pdf_path = compress_and_pdf(result, quality=args.quality, max_size=args.max_size)

    # 4. 发送
    if not args.no_send:
        send_email(pdf_path, album_id, result.get("title", ""))
    else:
        print(f"  📁 PDF 保存在: {pdf_path}", flush=True)

    # 5. 清理
    if not args.no_clean:
        cleanup(album_id)

    print(f"\n✅ 完成", flush=True)


if __name__ == "__main__":
    main()
