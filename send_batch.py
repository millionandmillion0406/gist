#!/usr/bin/env python3
"""最终版投稿发送 —— 慎重操作"""

import smtplib, ssl, subprocess, sys, time, json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
from pathlib import Path

# ── 配置 ──
FROM_EMAIL = "2233873332@qq.com"
FROM_PASS = "xyrzharzncuadida"
FROM_NAME = "浮士德猫猫头"
SUBJECT = "投稿《如何成为伪文青:假装看过100部经典电影》 （修正版）"
PDF_PATH = Path("C:/Users/windows/Desktop/如何成为伪文青：假装看过100部经典电影.pdf")
LETTER_PATH = Path("C:/Users/windows/ZCodeProject/video-qa/submission_letter_v2.txt")
LOG_PATH = Path("C:/Users/windows/ZCodeProject/video-qa/submission_log.json")
INTERVAL = 120  # 每封间隔2分钟

BATCHES = {
    1: [
        ("读客文化", "tougao@dookbook.com"),
        ("长江文艺出版社", "cjwytgc@163.com"),
        ("上海文艺出版社", "cslcm@public1.sta.net.cn"),
    ],
    2: [
        ("北京联合出版公司", "bjlhcb@sina.com.cn"),
        ("重庆出版社", "cqcbsnbl@163.com"),
        ("广西师范大学出版社", "abg@bbtpress.com"),
    ],
    3: [
        ("人民文学出版社", "info@rw-cn.com"),
        ("上海译文出版社", "info@yiwen.com.cn"),
        ("生活·读书·新知三联书店", "sdxdushu@vip.sina.com"),
    ],
}


def send_email(to_email, body, pdf_path):
    msg = MIMEMultipart()
    msg["From"] = formataddr([FROM_NAME, FROM_EMAIL])
    msg["To"] = to_email
    msg["Subject"] = SUBJECT

    # 正文
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # PDF附件——纯英文文件名
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment",
                        filename=("utf-8", None, "book.pdf"))
        msg.attach(part)

    ctx = ssl.create_default_context()
    server = smtplib.SMTP_SSL("smtp.qq.com", 465, context=ctx)
    server.login(FROM_EMAIL, FROM_PASS)
    server.sendmail(FROM_EMAIL, [to_email], msg.as_string())
    server.quit()
    return True


def send_batch(batch_num):
    targets = BATCHES[batch_num]
    body = LETTER_PATH.read_text(encoding="utf-8")

    # 加载日志
    if LOG_PATH.exists():
        log = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    else:
        log = {"sent": [], "failed": []}

    print(f"\n{'='*60}")
    print(f"📬 第 {batch_num} 批 — {len(targets)} 家")
    print(f"{'='*60}")

    for i, (name, email) in enumerate(targets, 1):
        # 跳过已发
        if any(s["email"] == email for s in log["sent"]):
            print(f"  [{i}/{len(targets)}] {name} — ⏭ 已发过，跳过")
            continue

        print(f"\n  [{i}/{len(targets)}] {name} <{email}>")
        print(f"  主题: {SUBJECT}")
        print(f"  附件: book.pdf")
        sys.stdout.flush()

        try:
            send_email(email, body, PDF_PATH)
            print(f"  ✅ 成功")
            log["sent"].append({
                "name": name, "email": email,
                "time": datetime.now().isoformat(),
                "batch": batch_num, "status": "sent",
            })
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            log["failed"].append({
                "name": name, "email": email,
                "time": datetime.now().isoformat(),
                "batch": batch_num, "error": str(e),
            })

        LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

        if i < len(targets):
            print(f"  ⏳ 等 {INTERVAL} 秒...")
            sys.stdout.flush()
            time.sleep(INTERVAL)

    s = [x for x in log["sent"] if x.get("batch") == batch_num]
    f = [x for x in log["failed"] if x.get("batch") == batch_num]
    print(f"\n📊 第 {batch_num} 批: ✅ {len(s)} 成功, ❌ {len(f)} 失败")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: batch.py 1|2|3")
        sys.exit(1)
    send_batch(int(sys.argv[1]))
