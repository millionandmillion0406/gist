#!/usr/bin/env python3
"""
生成书籍推广视频 — 高级感极简风
用法: python make_video.py
"""
import subprocess, shutil, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).parent / "videos"
OUT.mkdir(exist_ok=True)
TMP = OUT / "frames"
TMP.mkdir(exist_ok=True)

W, H = 1920, 1080  # 横屏 16:9
BG = (0, 0, 0)      # 纯黑
FG = (245, 245, 245) # 接近白色
ACCENT = (180, 150, 100)  # 金色点缀

# 字体
FONT_TITLE = r"C:\Windows\Fonts\Noto Sans SC Bold (TrueType).otf"
FONT_REG = r"C:\Windows\Fonts\Noto Sans SC (TrueType).otf"
FONT_TITLE = r"C:\Windows\Fonts\Noto Sans SC Bold (TrueType).otf"

def make_frame(text, font_path, size, y_center, color=FG, align="center"):
    """生成单帧图片"""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size)
    
    # 分行绘制
    lines = text.split("\n")
    total_h = len(lines) * (size + 20)
    start_y = y_center - total_h // 2
    
    for i, line in enumerate(lines):
        _, _, tw, th = draw.textbbox((0, 0), line, font=font)
        x = (W - tw) // 2 if align == "center" else 100
        y = start_y + i * (size + 20)
        draw.text((x, y), line, font=font, fill=color)
    
    return img


def make_video(movie_title, director, punchline, index=1):
    """生成单个电影推广视频"""
    frames = []
    CY = H // 2  # 垂直居中基准线
    
    # ---- 第1帧：书名 ----
    img = make_frame("如何成为伪文青", FONT_TITLE, 82, CY - 100)
    draw = ImageDraw.Draw(img)
    font_s = ImageFont.truetype(FONT_REG, 36)
    draw.text(((W - draw.textbbox((0,0),"假装看过100部经典电影",font=font_s)[2])//2, CY + 60), "假装看过100部经典电影", font=font_s, fill=ACCENT)
    draw.text(((W - draw.textbbox((0,0),"浮士德猫猫头",font=font_s)[2])//2, CY + 350), "浮士德猫猫头", font=font_s, fill=(150,150,150))
    for _ in range(90):  # 3秒
        frames.append(img)
    
    # ---- 过渡淡入下一帧 ----
    for i in range(30):
        img2 = Image.new("RGB", (W, H), BG)
        draw2 = ImageDraw.Draw(img2)
        title_font = ImageFont.truetype(FONT_TITLE, 64)
        # 电影标题
        tw = draw2.textbbox((0,0), movie_title, font=title_font)[2]
        draw2.text(((W - tw)//2, CY - 60), movie_title, font=title_font, fill=FG)
        # 导演
        dir_font = ImageFont.truetype(FONT_REG, 28)
        tw2 = draw2.textbbox((0,0), director, font=dir_font)[2]
        draw2.text(((W - tw2)//2, CY + 40), director, font=dir_font, fill=ACCENT)
        # 过渡
        blend = Image.blend(img, img2, i/15)
        frames.append(blend)
    
    # ---- 电影标题停留 ----
    for _ in range(45):
        frames.append(img2)
    
    # ---- 金句出现 ----
    for i in range(30):
        img3 = Image.new("RGB", (W, H), BG)
        draw3 = ImageDraw.Draw(img3)
        punch_font = ImageFont.truetype(FONT_TITLE, 44)
        punch_font_s = ImageFont.truetype(FONT_REG, 28)
        
        # 原标题
        _, _, tw, _ = draw3.textbbox((0,0), f"《{movie_title}》", font=punch_font_s)
        draw3.text(((W - tw)//2, CY - 180), f"《{movie_title}》", font=punch_font_s, fill=ACCENT)
        
        # 金句（按长度分行）
        max_chars = 30
        lines = []
        current = ""
        for char in punchline:
            current += char
            if len(current) >= max_chars:
                lines.append(current)
                current = ""
        if current:
            lines.append(current)
        
        line_h = 56
        total_h = len(lines) * line_h
        start_y = CY - total_h // 2 + 40
        for j, line in enumerate(lines):
            tw = draw3.textbbox((0,0), line, font=punch_font)[2]
            draw3.text(((W - tw)//2, start_y + j * line_h), line, font=punch_font, fill=FG)
        
        # 过渡叠加
        alpha = min(1.0, i / 15)
        # 从黑屏过渡到金句
        black = Image.new("RGB", (W, H), BG)
        blend2 = Image.blend(black, img3, alpha)
        frames.append(blend2)
    
    # ---- 金句停留 ----
    for _ in range(120):  # 4秒
        frames.append(img3)
    
    # ---- 结尾：书名 ----
    for i in range(20):
        end = Image.new("RGB", (W, H), BG)
        end_draw = ImageDraw.Draw(end)
        font_end = ImageFont.truetype(FONT_TITLE, 56)
        font_end_s = ImageFont.truetype(FONT_REG, 30)
        tw = end_draw.textbbox((0,0), "如何成为伪文青", font=font_end)[2]
        end_draw.text(((W - tw)//2, CY - 60), "如何成为伪文青", font=font_end, fill=FG)
        tw2 = end_draw.textbbox((0,0), "假装看过100部经典电影", font=font_end_s)[2]
        end_draw.text(((W - tw2)//2, CY + 60), "假装看过100部经典电影", font=font_end_s, fill=ACCENT)
        
        black = Image.new("RGB", (W, H), BG)
        blend3 = Image.blend(img3, end, i/15) if i < 10 else end
        frames.append(blend3)
    
    for _ in range(90):  # 3秒
        frames.append(end)

    # ---- 输出视频 ----
    fps = 30
    video_path = OUT / f"movie_{index:03d}.mp4"
    
    # 先用图片序列生成视频
    for i, frame in enumerate(frames):
        frame.save(TMP / f"f{i:04d}.png")
    
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(TMP / "f%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "slow", "-crf", "16",
        "-vf", "format=yuv420p",
        str(video_path)
    ], capture_output=True)
    
    # 清理临时帧
    for f in TMP.iterdir():
        f.unlink()
    
    print(f"✅ {video_path.name}  ({video_path.stat().st_size/1024/1024:.1f}MB)")
    return video_path


if __name__ == "__main__":
    import re, time
    
    # 支持限制数量：python make_video.py 10 （只生成前10条）
    limit = 100
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    book_path = r"C:\Users\windows\Desktop\如何成为伪文青：假装看过100部经典电影.txt"
    book_text = Path(book_path).read_text(encoding='utf-8')
    entries = re.findall(r'《([^》]+)》\s*([^\n]+)\n([^《\n]+)', book_text)
    entries = entries[:limit]
    
    print(f"📖 共 {len(entries)} 部电影\n")
    t_start = time.time()
    
    for i, (title, director, punchline) in enumerate(entries, 1):
        ti = time.time()
        print(f"[{i:03d}/{len(entries)}] 《{title}》... ", end='', flush=True)
        make_video(title, director.strip(), punchline.strip(), index=i)
        print(f"{time.time()-ti:.0f}s")
    
    total = time.time()-t_start
    print(f"\n🎬 完成! {len(entries)} 条, 共 {total/60:.0f}分钟, 平均 {total/len(entries):.0f}s/条")
    print(f"📁 {OUT}")
