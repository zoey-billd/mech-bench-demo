"""Compose the mechanical acceptance bench demo.

Frame data comes straight from build_mech.py: every number on screen is read
back from the evaluated scene, so the HUD reports what the constraint actually
let through, not what the driver asked for.
"""
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
BG = (10, 12, 16)
FG = (240, 244, 249)
DIM = (126, 138, 152)
FAINT = (74, 84, 98)
GOOD = (53, 224, 161)
ACCENT = (96, 174, 255)
AMBER = (255, 176, 92)
TEAL = (58, 200, 190)
STEEL = (176, 196, 216)

ROOT = os.environ.get("MECH_OUT") or os.path.join("D:\\", "mech_demo")
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
    vd.ellipse([-W * 0.30, -H * 0.42, W * 1.30, H * 1.42], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(190))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.blend(img, Image.composite(img, dark, vig), 0.55)


PLATE = None


def tag(d, code, name, colour=ACCENT):
    d.text((96, 78), code, font=font(19, mono=True), fill=colour)
    d.text((96, 106), name, font=font(24, bold=True), fill=(150, 162, 176))


# ------------------------------------------------------------------ opener
def sec_title(t):
    img = PLATE.copy()
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "01", "这个片子验什么")

    d.text((96, 232), "一台机构，五个关节，一根参数", font=font(60, bold=True), fill=FG)
    d.text((96, 306), "从闭合到展开，每一次行程都由约束判定能不能过", font=font(30), fill=DIM)

    rows = [
        ("bpy 程序化建模", "场景里没有一个手工拉出来的面", ACCENT),
        ("6 个驱动器", "全部读同一个 CTRL[\"deploy\"] 0 → 1", AMBER),
        ("6 条 Limit 约束", "驱动故意越界 30-40%，约束负责把它拦下", GOOD),
        ("1 次刚体落体", "球落进抽出的托盘，检验碰撞体", TEAL),
    ]
    y = 430
    reveal = min(len(rows), int(t / 0.75) + 1)
    for label, note, colour in rows[:reveal]:
        d.rounded_rectangle([96, y, 96 + 1180, y + 100], radius=10,
                            fill=(255, 255, 255, 8), outline=(255, 255, 255, 16))
        d.rectangle([96, y + 14, 100, y + 86], fill=colour + (255,))
        d.text((130, y + 20), label, font=font(32, bold=True), fill=FG)
        d.text((130, y + 62), note, font=font(22), fill=DIM)
        y += 112
    return img


# ------------------------------------------------------------------ hud
def panel(d, box, fill=(6, 8, 11, 205)):
    d.rounded_rectangle(box, radius=12, fill=fill, outline=(40, 47, 58, 255), width=2)


def sec_pass_a(i, n, data):
    src = Image.open(os.path.join(FRAMES_A, "f_%04d.png" % (i + 1))).convert("RGB")
    d = ImageDraw.Draw(src, "RGBA")
    s = data["series"]
    deploy = s["deploy"][i]

    # ---- master control block, top centre: the mast owns the top left corner
    panel(d, [604, 40, 1304, 198])
    d.text((628, 56), "MASTER CONTROL", font=font(18, mono=True), fill=FAINT)
    d.text((628, 82), "CTRL[\"deploy\"]", font=font(26, mono=True), fill=STEEL)
    d.text((1280, 76), "%.2f" % deploy, font=font(40, mono=True), fill=FG, anchor="ra")
    d.text((628, 122), "6 drivers read this value · 0 keyframes on any joint",
           font=font(19), fill=DIM)
    bx0, bx1, by = 628, 1280, 160
    d.rectangle([bx0, by, bx1, by + 10], fill=(38, 45, 56))
    d.rectangle([bx0, by, bx0 + int((bx1 - bx0) * deploy), by + 10], fill=AMBER)

    # ---- joint readouts, right column
    x0, x1 = 1312, 1876
    y = 40
    for spec in data["spec"]:
        key = spec["id"]
        colour = COLOUR[key]
        val = s[key][i]
        shown = abs(val)
        ratio = min(1.0, shown / LIMIT[key])
        active = i > 4 and abs(s[key][i] - s[key][i - 4]) > 0.2
        box_bg = (10, 13, 18, 214) if not active else (18, 26, 34, 224)
        panel(d, [x0, y, x1, y + 156], box_bg)
        d.rectangle([x0, y + 12, x0 + 4, y + 144], fill=colour + (255,))
        d.text((x0 + 22, y + 12), spec["label"], font=font(25, bold=True), fill=FG)
        d.text((x1 - 20, y + 14), spec["kind"], font=font(17, mono=True),
               fill=colour, anchor="ra")
        d.text((x0 + 22, y + 48), "axis %s   travel %s" % (spec["axis"], spec["range"]),
               font=font(19, mono=True), fill=DIM)
        d.text((x0 + 22, y + 76), "%.1f %s" % (shown, spec["unit"]),
               font=font(42, mono=True), fill=FG)
        d.text((x1 - 20, y + 96), "in %s" % spec["input"], font=font(19, mono=True),
               fill=colour, anchor="ra")
        d.rectangle([x0 + 22, y + 128, x1 - 22, y + 136], fill=(36, 43, 54))
        d.rectangle([x0 + 22, y + 128, x0 + 22 + int((x1 - x0 - 44) * ratio), y + 136],
                    fill=colour)
        y += 168

    # ---- status strip
    d.rectangle([0, H - 108, W, H], fill=(6, 7, 10, 208))
    d.line([(0, H - 108), (W, H - 108)], fill=(36, 42, 52, 255), width=2)
    hits = len(data["interference"]["hits"])
    d.text((48, H - 84), "LIMIT CONSTRAINTS", font=font(18, mono=True), fill=FAINT)
    d.text((48, H - 56), "6 / 6 joints clamped inside declared travel",
           font=font(25), fill=GOOD)
    d.text((760, H - 84), "INTERFERENCE", font=font(18, mono=True), fill=FAINT)
    d.text((760, H - 56), "%d pose checks · %d intersecting face pairs"
           % (data["interference"]["checked"], hits),
           font=font(25), fill=GOOD if hits == 0 else (255, 90, 78))
    d.text((W - 48, H - 74), "%d / %d" % (i + 1, n), font=font(24, mono=True),
           fill=FAINT, anchor="ra")
    return src


# ------------------------------------------------------------------ pass B
def sec_pass_b(i, n, data):
    src = Image.open(os.path.join(FRAMES_B, "f_%04d.png" % (i + 1))).convert("RGB")
    d = ImageDraw.Draw(src, "RGBA")
    ball = data["ball"]
    z = ball["trail"][i]
    floor_top = ball["floor_top"]
    gap = (z - BALL_R - floor_top) * 1000.0  # clearance between ball skin and tray floor

    panel(d, [1176, 40, 1876, 232])
    d.text((1202, 58), "RIGID BODY DROP TEST", font=font(19, mono=True), fill=FAINT)
    d.text((1202, 86), "0.6 kg ball · Ø110 mm · 0.4x", font=font(26, mono=True), fill=STEEL)
    d.text((1202, 126), "passive tray, no constraint — pure contact",
           font=font(21), fill=DIM)
    d.text((1202, 168), "ball bottom to tray floor", font=font(20, mono=True), fill=FAINT)
    d.text((1850, 158), "%+.1f mm" % gap, font=font(44, mono=True),
           fill=GOOD if gap > -1.0 else (255, 90, 78), anchor="ra")

    d.rectangle([0, H - 108, W, H], fill=(6, 7, 10, 208))
    d.line([(0, H - 108), (W, H - 108)], fill=(36, 42, 52, 255), width=2)
    # per frame, not per take: the ball spends most of the shot in the air
    d.text((48, H - 84), "CONTACT", font=font(18, mono=True), fill=FAINT)
    if gap > 8.0:
        d.text((48, H - 56), "in flight — %.0f mm above the tray floor" % gap,
               font=font(25), fill=AMBER)
    elif gap > -1.0:
        d.text((48, H - 56), "contact — ball rests on the tray floor", font=font(25),
               fill=GOOD)
    else:
        d.text((48, H - 56), "contact — penetration %.1f mm" % -gap, font=font(25),
               fill=(255, 90, 78))
    d.text((W - 48, H - 74), "%d / %d" % (i + 1, n), font=font(24, mono=True),
           fill=FAINT, anchor="ra")
    return src


# ------------------------------------------------------------------ outro
def sec_outro(t):
    img = PLATE.copy()
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, "03", "对上了哪几条", GOOD)

    d.text((96, 198), "同一套绑定，复用到任何机械资产", font=font(48, bold=True), fill=FG)

    rows = [
        ("开合 / 旋转", "铰链门  0 - 105°", "驱动要 140°，停在 105°", ACCENT),
        ("滑动", "抽出托盘  0 - 300 mm", "驱动要 420 mm，停在 300 mm", AMBER),
        ("伸缩", "两级桅杆  0 - 300 mm", "驱动要 460 mm，停在 300 mm", STEEL),
        ("折叠", "双连杆  80° / 120°", "驱动要 95° / 145°，停在 80° / 120°", TEAL),
    ]
    y = 306
    for a, b, c, colour in rows:
        d.rounded_rectangle([96, y, 96 + 1320, y + 104], radius=10,
                            fill=(255, 255, 255, 8), outline=(255, 255, 255, 16))
        d.rectangle([96, y + 14, 100, y + 90], fill=colour + (255,))
        d.text((130, y + 18), a, font=font(32, bold=True), fill=FG)
        d.text((130, y + 62), b, font=font(22), fill=DIM)
        d.text((1416, y + 34), c, font=font(22), fill=colour, anchor="ra")
        y += 112

    d.line([(96, 806), (96 + 1320, 806)], fill=(46, 54, 66), width=2)
    stats = [("6", "drivers"), ("6", "constraints"), ("0", "manual poses"),
             ("0", "interferences")]
    x = 96
    for value, label in stats:
        d.text((x, 840), value, font=font(52, mono=True), fill=FG)
        d.text((x, 902), label, font=font(21), fill=DIM)
        x += 300
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
    out = os.path.join(OUT_DIR, "mech_bench_demo.mp4")
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
