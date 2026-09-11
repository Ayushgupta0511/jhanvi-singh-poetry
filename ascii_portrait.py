#!/usr/bin/env python3
"""
ascii_portrait.py - Turns any photo into ASCII art.
"""

import argparse
import os
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    os.path.join(_HERE, "JetBrainsMono-Regular.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "C:\\Windows\\Fonts\\consola.ttf",
    "C:\\Windows\\Fonts\\cour.ttf",
]

def resolve_font(explicit_path=None):
    candidates = ([explicit_path] if explicit_path else []) + FONT_CANDIDATES
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("No monospace .ttf font found.")

_DENSE_TO_LIGHT = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
RAMP = _DENSE_TO_LIGHT[::-1]

def apply_vignette(img, strength=0.55, cx_frac=0.5, cy_frac=0.42, radius_frac=0.6):
    w, h = img.size
    arr = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * cx_frac, h * cy_frac
    dist = np.sqrt(((xx - cx) / (w * radius_frac)) ** 2 + ((yy - cy) / (h * radius_frac)) ** 2)
    falloff = 1.0 - strength * np.clip(dist - 0.3, 0, None) ** 1.3
    falloff = np.clip(falloff, 0.0, 1.0)
    return Image.fromarray(np.clip(arr * falloff, 0, 255).astype(np.uint8))

def load_and_prep(path, contrast=1.15, equalize=True, autocontrast_cutoff=0.5, vignette=0.55):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")
    if equalize:
        img = ImageOps.equalize(img)
    img = ImageOps.autocontrast(img, cutoff=autocontrast_cutoff)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    if vignette:
        img = apply_vignette(img, strength=vignette)
    return img

def build_brightness_grid(img, columns, char_w, char_h):
    w, h = img.size
    char_aspect = char_w / char_h
    rows = max(1, round((h / w) * columns * char_aspect))
    small = img.resize((columns, rows), Image.LANCZOS)
    arr = np.asarray(small)
    return arr.tolist()

def pixel_to_char(v):
    idx = int(v / 255 * (len(RAMP) - 1))
    return RAMP[idx]

def grid_to_text(grid):
    return "\n".join("".join(pixel_to_char(v) for v in row) for row in grid)

def render_png(grid, font_path, font_size=14, bg=(6, 6, 9), min_glow=35):
    font = ImageFont.truetype(font_path, font_size)
    bbox = font.getbbox("M")
    char_w = font.getlength("M")
    char_h = (bbox[3] - bbox[1]) * 1.18
    rows, cols = len(grid), len(grid[0])
    img_w = int(char_w * cols) + int(char_w)
    img_h = int(char_h * rows) + int(char_h)
    canvas = Image.new("RGB", (img_w, img_h), bg)
    draw = ImageDraw.Draw(canvas)
    for r, row in enumerate(grid):
        y = r * char_h
        for c, v in enumerate(row):
            ch = pixel_to_char(v)
            if ch == " ":
                continue
            tone = int(min_glow + (v / 255) * (255 - min_glow))
            draw.text((c * char_w, y), ch, font=font, fill=(tone, tone, tone))
    return canvas, char_w, char_h

def main():
    ap = argparse.ArgumentParser(description="Convert a photo into ASCII art.")
    ap.add_argument("image", help="path to source photo")
    ap.add_argument("--columns", type=int, default=140, help="characters per row")
    ap.add_argument("--font", default=None, help="path to a .ttf monospace font")
    ap.add_argument("--font-size", type=int, default=14)
    ap.add_argument("--contrast", type=float, default=1.15)
    ap.add_argument("--out", default="portrait", help="output filename prefix")
    args = ap.parse_args()
    font_path = resolve_font(args.font)
    img = load_and_prep(args.image, contrast=args.contrast)
    probe_font = ImageFont.truetype(font_path, args.font_size)
    probe_w = probe_font.getlength("M")
    probe_bbox = probe_font.getbbox("M")
    probe_h = (probe_bbox[3] - probe_bbox[1]) * 1.18
    grid = build_brightness_grid(img, args.columns, probe_w, probe_h)
    text = grid_to_text(grid)
    with open(f"{args.out}.txt", "w") as f:
        f.write(text + "\n")
    png, _, _ = render_png(grid, font_path, font_size=args.font_size)
    png.save(f"{args.out}.png")
    print(f"columns={args.columns} rows={len(grid)}")
    print(f"Wrote {args.out}.txt and {args.out}.png")

if __name__ == "__main__":
    main()
