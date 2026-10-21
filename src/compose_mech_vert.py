"""Portrait (1080x1920) cut of the mechanical acceptance bench demo.

Same JSON, same frame sequence, same numbers -- only the HUD layout changes:
horizontal uses a right-hand column, portrait stacks the five joint readouts
across the bottom third so the mechanism keeps the top of the frame.
"""
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BG = (10, 12, 16)
FG = (240, 244, 249)
DIM = (126, 138, 152)
FAINT = (74, 84, 98)
GOOD = (53, 224, 161)
ACCENT = (96, 174, 255)
AMBER = (255, 176, 92)
TEAL = (58, 200, 190)
STEEL = (176, 196, 216)
BAD = (255, 90, 78)

ROOT = os.environ.get("MECH_OUT") or os.path.join("D:\\", "mech_demo", "vert")
DATA = os.path.join(ROOT, "mech_data.json")
FRAMES_A = os.path.join(ROOT, "frames_a")
FRAMES_B = os.path.join(ROOT, "frames_b")
OUT_DIR = os.path.join(ROOT, "out")
FONT_DIR = "C:/Windows/Fonts"
BALL_R = 0.055

COLOUR = {"door": ACCENT, "drawer": AMBER, "mast": STEEL,
          "bracket1": TEAL, "bracket2": TEAL}
LIMIT = {"door": 105.0, "drawer": 300.0, "mast": 300.0,
         "bracket1": 80.0, "bracket2": 120.0}

MARGIN = 52


def font(size, bold=False, mono=False, medium=False):
    if mono:
        return ImageFont.truetype(os.path.join(FONT_DIR, "consola.ttf"), size)
    f = ImageFont.truetype(os.path.join(FONT_DIR, "NotoSansSC-VF.ttf"), size)
    f.set_variation_by_name("Bold" if bold else ("Medium" if medium else "Regular"))
    return f


def wallpaper():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 5), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 5), width=1)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.45, -H * 0.28, W * 1.45, H * 1.28], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(190))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.blend(img, Image.composite(img, dark, vig), 0.55)


PLATE = None


def panel(d, box, fill=(6, 8, 11, 205)):
    d.rounded_rectangle(box, radius=14, fill=fill, outline=(40, 47, 58, 255), width=2)


def tag(d, code, name, colour=ACCENT):
    d.text((MARGIN, 62), code, font=font(20, mono=True), fill=colour)
    d.text((MARGIN + 46, 58), name, font=font(26, bold=True), fill=(154, 166, 180))


# ------------------------------------------------------------------ opener
def sec_title(t):
    img = PLATE.copy()
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "01", "这个片子验什么")

    d.text((MARGIN, 152), "一台机构", font=font(78, bold=True), fill=FG)
    d.text((MARGIN, 248), "五个关节", font=font(78, bold=True), fill=FG)
    d.text((MARGIN, 344), "一根参数", font=font(78, bold=True), fill=AMBER)

    d.text((MARGIN, 470), "从闭合到展开，每一步行程", font=font(30), fill=DIM)
    d.text((MARGIN, 512), "都由约束判定能不能过", font=font(30), fill=DIM)

    rows = [
        ("bpy 程序化建模", "场景里没有一个手工拉出来的面", ACCENT),
        ("6 个驱动器", "全部读同一个 CTRL[\"deploy\"] 0 → 1", AMBER),
        ("6 条 Limit 约束", "驱动故意越界 30-40%，约束负责拦下", GOOD),
        ("1 次刚体落体", "球落进抽出的托盘，检验碰撞体", TEAL),
    ]
    y = 632
    reveal = min(len(rows), int(t / 0.42) + 1)
    for label, note, colour in rows[:reveal]:
        d.rounded_rectangle([MARGIN, y, W - MARGIN, y + 148], radius=12,
                            fill=(255, 255, 255, 8), outline=(255, 255, 255, 16))
        d.rectangle([MARGIN, y + 18, MARGIN + 5, y + 130], fill=colour + (255,))
        d.text((MARGIN + 30, y + 28), label, font=font(36, bold=True), fill=FG)
        d.text((MARGIN + 30, y + 88), note, font=font(23), fill=DIM)
        y += 162

    d.line([(MARGIN, 1382), (W - MARGIN, 1382)], fill=(46, 54, 66), width=2)
    for k, (value, label, colour) in enumerate(
            [("0", "手工建模", ACCENT), ("0", "手工 K 帧", AMBER), ("174", "次干涉检查", GOOD)]):
        cx = MARGIN + k * 328
        d.text((cx, 1414), value, font=font(56, mono=True), fill=colour)
        d.text((cx, 1484), label, font=font(23), fill=DIM)

    d.text((MARGIN, 1586), "BLENDER 5.2  ·  EEVEE  ·  bpy / bmesh", font=font(22, mono=True),
           fill=FAINT)
    d.text((MARGIN, 1630), "整个场景由一行行代码搭起来", font=font(28), fill=DIM)
    return img


# ------------------------------------------------------------------ hud
def sec_pass_a(i, n, data):
    src = Image.open(os.path.join(FRAMES_A, "f_%04d.png" % (i + 1))).convert("RGB")
    d = ImageDraw.Draw(src, "RGBA")
    s = data["series"]
    deploy = s["deploy"][i]

    # ---- master control strip, top
    panel(d, [MARGIN, 56, W - MARGIN, 210])
    d.text((MARGIN + 26, 74), "MASTER CONTROL", font=font(18, mono=True), fill=FAINT)
    d.text((MARGIN + 26, 102), "CTRL[\"deploy\"]", font=font(28, mono=True), fill=STEEL)
    d.text((W - MARGIN - 26, 92), "%.2f" % deploy, font=font(46, mono=True), fill=FG,
           anchor="ra")
    bx0, bx1, by = MARGIN + 26, W - MARGIN - 26, 158
    d.rectangle([bx0, by, bx1, by + 10], fill=(38, 45, 56))
    d.rectangle([bx0, by, bx0 + int((bx1 - bx0) * deploy), by + 10], fill=AMBER)
    d.text((MARGIN + 26, 176), "6 drivers  ·  0 keyframes on any joint",
           font=font(20), fill=DIM)

    # ---- joint grid, bottom: two columns so the bench keeps the top 2/3
    cw, gap = 480, 16
    top = 1528
    for k, spec in enumerate(data["spec"]):
        key = spec["id"]
        colour = COLOUR[key]
        val = s[key][i]
        shown = abs(val)
        ratio = min(1.0, shown / LIMIT[key])
        active = i > 4 and abs(s[key][i] - s[key][i - 4]) > 0.2
        cx = MARGIN + (k % 2) * (cw + gap)
        cy = top + (k // 2) * 114
        box_bg = (10, 13, 18, 218) if not active else (19, 27, 36, 228)
        panel(d, [cx, cy, cx + cw, cy + 106], box_bg)
        d.rectangle([cx + 2, cy + 10, cx + 6, cy + 96], fill=colour + (255,))
        d.text((cx + 22, cy + 12), spec["label"], font=font(21, bold=True), fill=FG)
        d.text((cx + cw - 16, cy + 15), spec["kind"], font=font(13, mono=True),
               fill=colour, anchor="ra")
        d.text((cx + 22, cy + 42), "%.1f %s" % (shown, spec["unit"]),
               font=font(29, mono=True), fill=FG)
        d.text((cx + cw - 16, cy + 52), "want %s" % spec["input"], font=font(16),
               fill=DIM, anchor="ra")
        d.rectangle([cx + 22, cy + 84, cx + cw - 16, cy + 92], fill=(36, 43, 54))
        d.rectangle([cx + 22, cy + 84, cx + 22 + int((cw - 38) * ratio), cy + 92],
                    fill=colour)

    # ---- summary cell fills the remaining slot, so the grid stays a rectangle
    hits = len(data["interference"]["hits"])
    sx = MARGIN + cw + gap
    sy = top + 2 * 114
    panel(d, [sx, sy, sx + cw, sy + 106], (8, 11, 15, 224))
    d.rectangle([sx + 2, sy + 10, sx + 6, sy + 96], fill=GOOD + (255,))
    d.text((sx + 22, sy + 12), "6 / 6", font=font(24, mono=True), fill=GOOD)
    d.text((sx + 22, sy + 44), "clamped in travel", font=font(18), fill=DIM)
    d.text((sx + 250, sy + 12), "%d / %d" % (data["interference"]["checked"], hits),
           font=font(24, mono=True), fill=GOOD)
    d.text((sx + 250, sy + 44), "checks / hits", font=font(18), fill=DIM)

    # ---- thin status strip
    d.rectangle([0, H - 56, W, H], fill=(6, 7, 10, 210))
    d.line([(0, H - 56), (W, H - 56)], fill=(36, 42, 52, 255), width=2)
    d.text((MARGIN, H - 38), "BLENDER 5.2  ·  EEVEE  ·  bpy", font=font(17, mono=True),
           fill=FAINT)
    d.text((W - MARGIN, H - 38), "%02d" % (i + 1), font=font(18, mono=True),
           fill=FAINT, anchor="ra")
    return src


# ------------------------------------------------------------------ pass B
def sec_pass_b(i, n, data):
    src = Image.open(os.path.join(FRAMES_B, "f_%04d.png" % (i + 1))).convert("RGB")
    d = ImageDraw.Draw(src, "RGBA")
    ball = data["ball"]
    z = ball["trail"][i]
    floor_top = ball["floor_top"]
    gap = (z - BALL_R - floor_top) * 1000.0

    panel(d, [MARGIN, 56, W - MARGIN, 264])
    d.text((MARGIN + 26, 74), "RIGID BODY DROP TEST", font=font(18, mono=True), fill=FAINT)
    d.text((MARGIN + 26, 102), "0.6 kg ball · Ø110 mm · 0.4x",
           font=font(24, mono=True), fill=STEEL)
    d.text((MARGIN + 26, 142), "passive tray, no constraint — pure contact",
           font=font(21), fill=DIM)
    d.text((MARGIN + 26, 186), "ball bottom to tray floor", font=font(19, mono=True),
           fill=FAINT)
    d.text((W - MARGIN - 26, 176), "%+.1f mm" % gap, font=font(48, mono=True),
           fill=GOOD if gap > -1.0 else BAD, anchor="ra")

    d.rectangle([0, H - 128, W, H], fill=(6, 7, 10, 210))
    d.line([(0, H - 128), (W, H - 128)], fill=(36, 42, 52, 255), width=2)
    d.text((MARGIN, H - 104), "CONTACT", font=font(17, mono=True), fill=FAINT)
    if gap > 8.0:
        d.text((MARGIN, H - 76), "in flight — %.0f mm above floor" % gap,
               font=font(26), fill=AMBER)
    elif gap > -1.0:
        d.text((MARGIN, H - 76), "contact — rests on the tray floor",
               font=font(26), fill=GOOD)
    else:
        d.text((MARGIN, H - 76), "contact — penetration %.1f mm" % -gap,
               font=font(26), fill=BAD)
    d.text((W - MARGIN, H - 84), "%02d" % (i + 1), font=font(22, mono=True),
           fill=FAINT, anchor="ra")
    return src


# ------------------------------------------------------------------ outro
def sec_outro(t):
    img = PLATE.copy()
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "03", "对上了哪几条", GOOD)

    d.text((MARGIN, 148), "同一套绑定", font=font(68, bold=True), fill=FG)
    d.text((MARGIN, 228), "复用到任何机械资产", font=font(68, bold=True), fill=FG)

    rows = [
        ("开合 / 旋转", "铰链门  0 - 105°", "要 140°，停 105°", ACCENT),
        ("滑动", "抽出托盘  0 - 300 mm", "要 420，停 300", AMBER),
        ("伸缩", "两级桅杆  0 - 300 mm", "要 460，停 300", STEEL),
        ("折叠", "双连杆  80° / 120°", "要 95° / 145°", TEAL),
    ]
    y = 372
    for a, b, c, colour in rows:
        d.rounded_rectangle([MARGIN, y, W - MARGIN, y + 150], radius=12,
                            fill=(255, 255, 255, 8), outline=(255, 255, 255, 16))
        d.rectangle([MARGIN, y + 18, MARGIN + 5, y + 132], fill=colour + (255,))
        d.text((MARGIN + 30, y + 22), a, font=font(36, bold=True), fill=FG)
        d.text((MARGIN + 30, y + 80), b, font=font(24), fill=DIM)
        d.text((W - MARGIN - 24, y + 84), c, font=font(24), fill=colour, anchor="ra")
        y += 164

    d.line([(MARGIN, 1058), (W - MARGIN, 1058)], fill=(46, 54, 66), width=2)
    stats = [("6", "drivers"), ("6", "constraints"), ("0", "manual poses"),
             ("0", "interferences")]
    for k, (value, label) in enumerate(stats):
        cx = MARGIN + (k % 2) * 496
        cy = 1096 + (k // 2) * 176
        d.text((cx, cy), value, font=font(72, mono=True), fill=FG)
        d.text((cx, cy + 88), label, font=font(24), fill=DIM)

    d.line([(MARGIN, 1560), (W - MARGIN, 1560)], fill=(46, 54, 66), width=2)
    d.text((MARGIN, 1592), "开合 · 旋转 · 滑动 · 伸缩 · 折叠",
           font=font(30, bold=True), fill=STEEL)
    d.text((MARGIN, 1642), "源码全部 bpy 生成，没有一个手工拉的面", font=font(23),
           fill=FAINT)
    return img


# ------------------------------------------------------------------ main
def main():
    global PLATE
    PLATE = wallpaper()
    data = json.load(open(DATA, encoding="utf-8"))
    a_files = sorted(f for f in os.listdir(FRAMES_A) if f.startswith("f_"))
    b_files = sorted(f for f in os.listdir(FRAMES_B) if f.startswith("f_"))
    print("pass A %d frames, pass B %d frames" % (len(a_files), len(b_files)))

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "mech_bench_vertical.mp4")
    proc = subprocess.Popen([
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)

    n = 0

    def emit(img):
        nonlocal n
        proc.stdin.write(np.asarray(img.convert("RGB"), dtype=np.uint8)[:, :, ::-1].tobytes())
        n += 1

    def hold(seconds, fn):
        for i in range(int(seconds * FPS)):
            emit(fn(i / FPS))

    def cut():
        for _ in range(6):
            emit(Image.new("RGB", (W, H), (0, 0, 0)))

    hold(3.6, sec_title)
    cut()
    for i in range(len(a_files)):
        emit(sec_pass_a(i, len(a_files), data))
    cut()
    for i in range(len(b_files)):
        emit(sec_pass_b(i, len(b_files), data))
    cut()
    hold(4.2, sec_outro)

    proc.stdin.close()
    proc.wait()
    print("wrote %s  frames=%d  %.1f s  %.1f MB"
          % (out, n, n / FPS, os.path.getsize(out) / 1048576.0))


if __name__ == "__main__":
    main()
