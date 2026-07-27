#!/usr/bin/env python3
"""
投稿邮件群发脚本 — 分批发送，控制频率防封
用法: python send_submissions.py [批次号]
  批次号: 1=第一批, 2=第二批, 3=第三批
  不指定则显示计划
"""

import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path

# ── 配置 ──
SEND_SCRIPT = Path.home() / ".openclaw-autoclaw/skills/send-email/send_email.py"
FROM_EMAIL = "2233873332@qq.com"
FROM_PASS = "xyrzharzncuadida"

BOOK_PDF = Path("C:/Users/windows/Desktop/如何成为伪文青：假装看过100部经典电影.pdf")
LETTER_FILE = Path(__file__).parent / "submission_letter_v2.txt"
LOG_FILE = Path(__file__).parent / "submission_log.json"
SUBJECT = "投稿《如何成为伪文青:假装看过100部经典电影》 （修正版）"

# ── 目标列表（分组） ──
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

INTERVAL = 120  # 每封间隔2分钟


def load_letter():
    with open(LETTER_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def send_one(to_name, to_email):
    """用 send_email.py 发一封（先复制为ASCII文件名防编码问题）"""
    body = load_letter()
    
    # 复制为纯ASCII文件名，避免中文在邮件头里变成 .bin
    tmp_pdf = Path(__file__).parent / "_tmp_attachment.pdf"
    import shutil
    shutil.copy2(BOOK_PDF, tmp_pdf)
    
    env = {
        "EMAIL_SMTP_SERVER": "smtp.qq.com",
        "EMAIL_SMTP_PORT": "465",
        "EMAIL_SENDER": FROM_EMAIL,
        "EMAIL_SMTP_PASSWORD": FROM_PASS,
    }
    cmd = [
        sys.executable, str(SEND_SCRIPT),
        to_email, SUBJECT, body, str(tmp_pdf)
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=60, env={**env})
    out = r.stdout.decode('utf-8', errors='replace') + r.stderr.decode('utf-8', errors='replace')
    
    # 清理临时文件
    tmp_pdf.unlink(missing_ok=True)
    
    return r.returncode == 0, out


def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sent": [], "failed": []}


def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def send_batch(batch_num):
    if batch_num not in BATCHES:
        print(f"❌ 无效批次号: {batch_num}，可选: {list(BATCHES.keys())}")
        return

    targets = BATCHES[batch_num]
    log = load_log()

    print(f"\n{'='*60}")
    print(f"📬 第 {batch_num} 批 — {len(targets)} 家出版社")
    print(f"{'='*60}")

    for i, (name, email) in enumerate(targets, 1):
        # 跳过已发的
        if any(s["email"] == email for s in log["sent"]):
            print(f"  [{i}/{len(targets)}] {name} — ⏭ 已发过，跳过")
            continue

        print(f"\n  [{i}/{len(targets)}] {name} <{email}>")
        sys.stdout.flush()

        ok, msg = send_one(name, email)
        if ok:
            print(f"  ✅ 发送成功")
            log["sent"].append({
                "name": name, "email": email,
                "time": datetime.now().isoformat(),
                "batch": batch_num, "status": "sent",
            })
        else:
            print(f"  ❌ 失败: {msg.strip()}")
            log["failed"].append({
                "name": name, "email": email,
                "time": datetime.now().isoformat(),
                "batch": batch_num, "error": msg.strip(),
            })
        save_log(log)

        if i < len(targets):
            print(f"  ⏳ 等 {INTERVAL} 秒...")
            sys.stdout.flush()
            time.sleep(INTERVAL)

    # 总结
    s = [x for x in log["sent"] if x["batch"] == batch_num]
    f = [x for x in log["failed"] if x["batch"] == batch_num]
    print(f"\n📊 第 {batch_num} 批: ✅ {len(s)} 成功, ❌ {len(f)} 失败")
    print(f"{'='*60}\n")


def show_plan():
    print("\n📋 ===== 投稿发送计划 =====\n")
    for bn in sorted(BATCHES):
        print(f"📦 第 {bn} 批 ({len(BATCHES[bn])} 家):")
        for n, e in BATCHES[bn]:
            print(f"   • {n} — {e}")
        print()
    log = load_log()
    print(f"📈 已发送: {len([s for s in log['sent'] if s['status']=='sent'])}")
    print(f"   已失败: {len(log['failed'])}")
    print(f"\n使用: python send_submissions.py <批次号>  (1|2|3)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_plan()
        sys.exit(0)
    try:
        send_batch(int(sys.argv[1]))
    except ValueError:
        print(f"❌ 无效批次号")
        sys.exit(1)
