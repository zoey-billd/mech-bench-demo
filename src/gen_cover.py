"""Render a 3:4 cover still for the portrait cut (Xiaohongshu friendly)."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1440
BG = (10, 12, 16)
FG = (240, 244, 249)
DIM = (126, 138, 152)
FAINT = (74, 84, 98)
AMBER = (255, 176, 92)
GOOD = (53, 224, 161)
FONT_DIR = "C:/Windows/Fonts"

ROOT = os.environ.get("MECH_OUT") or os.path.join("D:\\", "mech_demo", "vert")
SRC = os.path.join(ROOT, "frames_a", "f_0110.png")
OUT = os.path.join(ROOT, "out", "cover.png")


def font(size, bold=False, mono=False):
    if mono:
        return ImageFont.truetype(os.path.join(FONT_DIR, "consola.ttf"), size)
    f = ImageFont.truetype(os.path.join(FONT_DIR, "NotoSansSC-VF.ttf"), size)
    f.set_variation_by_name("Bold" if bold else "Regular")
    return f


def main():
    shot = Image.open(SRC).convert("RGB")
    # the bench runs from z=0.02 to the mast tip at z=1.45, which lands between
    # rows 340 and 1480 of the portrait render; crop exactly that and rescale to
    # the 1000 px slot under the headline
    band = shot.crop((0, 340, W, 1580)).resize((W, 888), Image.LANCZOS)
    band = ImageEnhance.Brightness(band).enhance(1.18)
    band = ImageEnhance.Contrast(band).enhance(1.06)
    TOP = 432

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, 5), width=1)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(255, 255, 255, 5), width=1)

    d.text((64, 62), "01  MECHANICAL ACCEPTANCE", font=font(20, mono=True), fill=GOOD)
    d.text((W - 56, 62), "BLENDER 5.2 · bpy", font=font(19, mono=True),
           fill=FAINT, anchor="ra")
    d.text((64, 104), "一台机构", font=font(82, bold=True), fill=FG)
    d.text((64, 196), "五个关节", font=font(82, bold=True), fill=FG)
    d.text((64, 288), "一根参数", font=font(82, bold=True), fill=AMBER)
    d.text((64, 392), "开合 · 旋转 · 滑动 · 伸缩 · 折叠 全验一遍",
           font=font(27), fill=DIM)

    # fade the still into the plate at the seam
    mask = Image.new("L", (W, 888), 255)
    md = ImageDraw.Draw(mask)
    for i in range(120):
        md.line([(0, i), (W, i)], fill=int(255 * (i / 120.0)))
    img.paste(band, (0, TOP), mask)

    grad = Image.new("L", (1, H), 0)
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        if y < TOP:
            gd.point((0, y), 0)
        else:
            gd.point((0, y), int(min(70, (y - TOP) * 0.10)))
    shade = Image.new("RGB", (W, H), (6, 7, 10))
    img = Image.composite(shade, img, grad.resize((W, H)))

    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, H - 112, W, H], fill=(6, 7, 10, 236))
    d.line([(0, H - 112), (W, H - 112)], fill=(40, 47, 58, 255), width=2)
    for k, (value, label) in enumerate([("6", "驱动器"), ("6", "Limit 约束"),
                                        ("0", "手工 K 帧"), ("174", "次干涉检查")]):
        cx = 64 + k * 250
        d.text((cx, H - 96), value, font=font(36, mono=True), fill=FG)
        d.text((cx, H - 50), label, font=font(20), fill=DIM)

    # paper grain, keeps it from looking like a flat UI export
    noise = np.random.default_rng(7).normal(0, 3.2, (H, W, 1))
    arr = np.clip(np.asarray(img, dtype=np.float32) + noise, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.save(OUT)
    print("wrote", OUT, out.size)


if __name__ == "__main__":
    main()
