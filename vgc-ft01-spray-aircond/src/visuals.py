"""Renderer visual Scrapbook Documentary — PIL + numpy, frame dipaip terus ke ffmpeg."""
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from timeline import (ACCENT, BG, CARD, DURATION_F, FPS, H, INK, SAFE_BOTTOM,
                      SAFE_SIDE, SAFE_TOP, SCENES, TEXT, W, WATER, WIPES, cue)

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


BLACK = "InterDisplay-Black.otf"
XBOLD = "InterDisplay-ExtraBold.otf"
BOLD = "InterDisplay-Bold.otf"
MARKER = "PermanentMarker-Regular.ttf"

LAYOUT_LOG = []  # (nama, x0, y0, x1, y1) untuk semakan kawasan selamat


# ---------------------------------------------------------------- easing ----
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    return 1 - (1 - t) ** 3


def hop(f, start, dur):
    """Gerak stop-start: lompat 80%, berhenti sekejap, kemudian mendarat."""
    f = (f // 2) * 2  # stop-motion "on twos" untuk lapisan kertas
    t = clamp((f - start) / dur)
    if t < 0.45:
        return 0.8 * ease_out(t / 0.45)
    if t < 0.6:
        return 0.8
    return 0.8 + 0.2 * ease_out((t - 0.6) / 0.4)


def drift(f, depth):
    """Parallax kecil sahaja."""
    return (depth * 4 * math.sin(f / 37.0), depth * 3 * math.cos(f / 49.0))


# ---------------------------------------------------------------- paper -----
_rng_np = np.random.default_rng(7)


def paper_texture(w, h, color, seed=0, grain=7):
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    n1 = rng.normal(0, 1, (h // 4 + 1, w // 4 + 1)).astype(np.float32)
    n1 = np.array(Image.fromarray(n1).resize((w, h), Image.BICUBIC))
    n2 = rng.normal(0, 1, (h, w)).astype(np.float32)
    tex = n1 * grain * 0.8 + n2 * grain * 0.35
    out = np.clip(base + tex[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def torn_polygon(w, h, pad, torn, seed, amp=9):
    """torn: set sisi koyak {'t','b','l','r'}."""
    rng = random.Random(seed)
    pts = []

    def edge(x0, y0, x1, y1, side):
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(length / 7))
        nx, ny = (y1 - y0) / length, -(x1 - x0) / length
        a = amp if side in torn else 1.2
        for i in range(n):
            t = i / n
            j = rng.uniform(-a, a) * (0.6 + 0.4 * math.sin(i * 0.7 + seed))
            pts.append((x0 + (x1 - x0) * t + nx * j, y0 + (y1 - y0) * t + ny * j))

    x0, y0, x1, y1 = pad, pad, pad + w, pad + h
    edge(x0, y0, x1, y0, "t")
    edge(x1, y0, x1, y1, "r")
    edge(x1, y1, x0, y1, "b")
    edge(x0, y1, x0, y0, "l")
    return pts


def paper_card(w, h, color=CARD, torn=("t", "b", "l", "r"), seed=1, shadow=True,
               amp=9):
    """Kertas dengan tepi koyak + bayang. Pulangkan (RGBA, offset kandungan)."""
    pad = 40
    W2, H2 = w + pad * 2, h + pad * 2
    poly = torn_polygon(w, h, pad, set(torn), seed, amp)
    mask = Image.new("L", (W2 * 2, H2 * 2), 0)
    ImageDraw.Draw(mask).polygon([(x * 2, y * 2) for x, y in poly], fill=255)
    mask = mask.resize((W2, H2), Image.LANCZOS)
    tex = paper_texture(W2, H2, color, seed=seed, grain=5)
    card = tex.convert("RGBA")
    card.putalpha(mask)
    # gentian putih di tepi koyak
    rim = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ImageDraw.Draw(rim).line(poly + [poly[0]], fill=(255, 253, 246, 150), width=3)
    rim.putalpha(Image.fromarray(np.minimum(np.array(rim.getchannel("A")),
                                            np.array(mask))))
    card = Image.alpha_composite(card, rim)
    if not shadow:
        return card, pad
    sh = Image.new("RGBA", (W2, H2), (40, 30, 20, 0))
    sh.putalpha(mask.point(lambda v: v * 0.42))
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    out = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    out.alpha_composite(sh, (6, 11))
    out.alpha_composite(card)
    return out, pad


def tape(w=190, h=56, seed=3, angle=0):
    rng = random.Random(seed)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pts = []
    for i in range(9):
        pts.append((rng.uniform(0, 6), h * i / 8))
    right = [(w - rng.uniform(0, 6), h * (8 - i) / 8) for i in range(9)]
    ImageDraw.Draw(img).polygon(pts + right, fill=(244, 236, 206, 185))
    n = np.array(img).astype(np.int16)
    n[..., :3] += _rng_np.integers(-8, 8, n[..., :3].shape, dtype=np.int16)
    img = Image.fromarray(np.clip(n, 0, 255).astype(np.uint8), "RGBA")
    return img.rotate(angle, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- text ------
def text_img(txt, fnt, color=INK, stroke=0, stroke_fill=None):
    l, t, r, b = fnt.getbbox(txt, stroke_width=stroke)
    img = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - l, 4 - t), txt, font=fnt, fill=color,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def fit_font(txt, name, size, max_w):
    while size > 20:
        f = font(name, size)
        l, _, r, _ = f.getbbox(txt)
        if r - l <= max_w:
            return f
        size -= 2
    return font(name, size)


# ---------------------------------------------------------------- compose ---
_cache = {}


def place(canvas, key, img, cx, cy, rot=0.0, scale=1.0, alpha=1.0, log=None):
    rot = round(rot, 1)
    scale = round(scale, 3)
    ck = (key, rot, scale)
    if ck not in _cache:
        im = img
        if scale != 1.0:
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                           Image.LANCZOS)
        if rot:
            im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        _cache[ck] = im
    im = _cache[ck]
    if alpha < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    canvas.paste(im, (x, y), im)
    if log:
        LAYOUT_LOG.append((log, x, y, x + im.width, y + im.height))


def marker_stroke(canvas, pts, progress, width=12, color=INK, alpha=235):
    """Lukis garisan marker secara progresif (anti-alias 2x)."""
    if progress <= 0 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * clamp(progress)))
    sub = pts[:n]
    xs, ys = [p[0] for p in sub], [p[1] for p in sub]
    x0, y0 = int(min(xs)) - width * 2, int(min(ys)) - width * 2
    x1, y1 = int(max(xs)) + width * 2, int(max(ys)) + width * 2
    ov = Image.new("RGBA", ((x1 - x0) * 2, (y1 - y0) * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    sp = [((x - x0) * 2, (y - y0) * 2) for x, y in sub]
    d.line(sp, fill=color + (alpha,), width=width * 2, joint="curve")
    r = width
    for x, y in (sp[0], sp[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color + (alpha,))
    ov = ov.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas.paste(ov, (x0, y0), ov)


def wobbly_line(p0, p1, n=30, wob=4, seed=0):
    rng = random.Random(seed)
    out = []
    for i in range(n + 1):
        t = i / n
        out.append((p0[0] + (p1[0] - p0[0]) * t + rng.uniform(-1, 1) * wob * math.sin(t * math.pi),
                    p0[1] + (p1[1] - p0[1]) * t + rng.uniform(-1, 1) * wob * math.sin(t * math.pi)))
    return out


def curve(p0, c, p1, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    return out


def arrow_head(tip, frm, size=34):
    ang = math.atan2(tip[1] - frm[1], tip[0] - frm[0])
    a1 = (tip[0] - size * math.cos(ang - 0.5), tip[1] - size * math.sin(ang - 0.5))
    a2 = (tip[0] - size * math.cos(ang + 0.5), tip[1] - size * math.sin(ang + 0.5))
    return [a1, tip, a2]


def hand_ellipse(cx, cy, rx, ry, turns=1.12, n=90, seed=5):
    rng = random.Random(seed)
    pts = []
    for i in range(n + 1):
        t = i / n * turns * 2 * math.pi - 2.2
        k = 1 + 0.03 * math.sin(i * 0.4) + rng.uniform(-0.01, 0.01)
        pts.append((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t) + i * 0.25))
    return pts


# ---------------------------------------------------------------- illustrations
def draw_aircond(w, h, dusty=True):
    """Ilustrasi unit aircond split (dilukis 2x untuk AA)."""
    S = 2
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bx0, by0, bx1, by1 = 20 * S, 40 * S, (w - 20) * S, (h - 50) * S
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=40 * S, fill=(250, 250, 246),
                        outline=INK, width=5 * S)
    # panel atas
    d.line((bx0 + 30 * S, by0 + 70 * S, bx1 - 30 * S, by0 + 70 * S), fill=(205, 200, 190), width=3 * S)
    # lampu
    d.ellipse((bx1 - 80 * S, by0 + 32 * S, bx1 - 64 * S, by0 + 48 * S), fill=(120, 190, 140))
    # sirip (fins) kelihatan di bawah
    fy0, fy1 = by0 + 95 * S, by1 - 70 * S
    d.rectangle((bx0 + 40 * S, fy0, bx1 - 40 * S, fy1), fill=(222, 222, 214))
    for x in range(bx0 + 48 * S, bx1 - 40 * S, 14 * S):
        d.line((x, fy0 + 6 * S, x, fy1 - 6 * S), fill=(170, 170, 162), width=3 * S)
    # louver
    d.rounded_rectangle((bx0 + 30 * S, by1 - 55 * S, bx1 - 30 * S, by1 - 25 * S), radius=12 * S,
                        fill=(236, 236, 230), outline=INK, width=4 * S)
    if dusty:
        rng = random.Random(11)
        dust = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(dust)
        for _ in range(700):
            x = rng.uniform(bx0 + 45 * S, bx1 - 45 * S)
            y = rng.uniform(fy0 + 4 * S, fy1 - 4 * S)
            r = rng.uniform(2, 8) * S
            g = rng.randint(95, 140)
            dd.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=(g, g - 6, g - 14, rng.randint(90, 190)))
        dust = dust.filter(ImageFilter.GaussianBlur(3 * S))
        img.alpha_composite(dust)
    return img.resize((w, h), Image.LANCZOS)


def draw_spray(w, h):
    S = 2
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = int(w * 0.68) * S
    bw = 120 * S
    top = 130 * S
    bot = (h - 20) * S
    d.rounded_rectangle((cx - bw // 2, top, cx + bw // 2, bot), radius=26 * S, fill=ACCENT,
                        outline=INK, width=5 * S)
    d.rectangle((cx - bw // 2 + 5 * S, top + 70 * S, cx + bw // 2 - 5 * S, top + 150 * S),
                fill=(250, 246, 236))
    d.text((cx, top + 110 * S), "SPRAY", font=font(BLACK, 30 * S), fill=INK, anchor="mm")
    # bahu + kepala
    d.rounded_rectangle((cx - 42 * S, top - 46 * S, cx + 42 * S, top + 8 * S), radius=14 * S,
                        fill=(250, 246, 236), outline=INK, width=5 * S)
    d.rectangle((cx - 64 * S, top - 30 * S, cx - 40 * S, top - 14 * S), fill=INK)
    # semburan
    rng = random.Random(4)
    for _ in range(90):
        a = rng.uniform(-0.45, 0.45) + math.pi
        r = rng.uniform(25, 150) * S
        x = cx - 64 * S + r * math.cos(a)
        y = top - 22 * S + r * math.sin(a)
        rr = rng.uniform(3, 8) * S
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=WATER + (rng.randint(110, 220),))
    return img.resize((w, h), Image.LANCZOS)


def draw_drops(w, h):
    S = 2
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for cx, cy, s in [(0.38, 0.32, 1.0), (0.66, 0.52, 0.8), (0.42, 0.72, 0.7)]:
        x, y, r = cx * w * S, cy * h * S, 58 * s * S
        d.polygon([(x, y - r * 1.9), (x - r * 0.92, y - r * 0.2), (x + r * 0.92, y - r * 0.2)],
                  fill=WATER)
        d.ellipse((x - r, y - r, x + r, y + r), fill=WATER)
        d.ellipse((x - r * 0.45, y - r * 0.5, x - r * 0.15, y - r * 0.05), fill=(200, 230, 236))
    return img.resize((w, h), Image.LANCZOS)


def step_badge(d, cx, cy, n):
    r = 46
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT)
    d.text((cx, cy + 2), n, font=font(BLACK, 62), fill=(255, 250, 242), anchor="mm")


# ---------------------------------------------------------------- assets ----
class A:
    pass


def build_assets():
    a = A()
    a.sheets = {
        "s1": paper_texture(W + 60, H + 60, BG, seed=1),
        "s2": paper_texture(W + 60, H + 60, (236, 228, 209), seed=2),
        "s3": paper_texture(W + 60, H + 60, (230, 219, 194), seed=3),
        "s4": paper_texture(W + 60, H + 60, BG, seed=4),
    }
    # helaian untuk wipe (tepi koyak di sisi hadapan)
    a.wipe = {}
    for k, side, seed in (("s2", "l", 21), ("s3", "r", 22), ("s4", "t", 23)):
        tex = a.sheets[k]
        ww, hh = tex.size
        pad = 40
        poly = torn_polygon(ww, hh, pad, {side}, seed, amp=16)
        mask = Image.new("L", (ww + pad * 2, hh + pad * 2), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(0.8))
        sheet = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        sheet.paste(tex, (pad, pad))
        sheet.putalpha(mask)
        sh = Image.new("RGBA", mask.size, (40, 30, 20, 0))
        sh.putalpha(mask.point(lambda v: v * 0.5))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        off = {"l": (-12, 0), "r": (12, 0), "t": (0, -12)}[side]
        out.alpha_composite(sh, (max(0, off[0]), max(0, off[1])))
        out.alpha_composite(sheet)
        a.wipe[k] = (out, side)

    maxw = W - 2 * SAFE_SIDE
    # S1
    card, pad = paper_card(900, 600, seed=31)
    ac = draw_aircond(840, 500)
    card.alpha_composite(ac, (pad + 30, pad + 50))
    card.alpha_composite(tape(200, 58, 1, 4), (pad + 330, 10))
    a.s1_card = card
    a.s1_l1 = text_img(TEXT["s1_l1"], fit_font(TEXT["s1_l1"], BLACK, 112, maxw))
    a.s1_l2 = text_img(TEXT["s1_l2"], fit_font(TEXT["s1_l2"], BLACK, 132, maxw), ACCENT)
    a.s1_note = text_img(TEXT["s1_note"], font(MARKER, 92))
    # S2
    a.s2_head = text_img(TEXT["s2_head"], fit_font(TEXT["s2_head"], BLACK, 124, maxw))
    c1, pad = paper_card(860, 420, seed=41)
    c1.alpha_composite(draw_spray(380, 400), (pad - 10, pad + 10))
    d = ImageDraw.Draw(c1)
    step_badge(d, pad + 470, pad + 130, "1")
    d.text((pad + 430, pad + 265), TEXT["s2_step1"], font=font(BLACK, 116), fill=INK, anchor="lm")
    a.s2_c1 = c1
    c2, pad = paper_card(860, 420, seed=42)
    c2.alpha_composite(draw_drops(360, 380), (pad + 10, pad + 20))
    d = ImageDraw.Draw(c2)
    step_badge(d, pad + 440, pad + 95, "2")
    d.text((pad + 400, pad + 225), TEXT["s2_step2a"], font=font(XBOLD, 70), fill=INK, anchor="lm")
    d.text((pad + 400, pad + 320), TEXT["s2_step2b"], font=font(BLACK, 108), fill=WATER, anchor="lm")
    a.s2_c2 = c2
    # S3
    a.s3_head = text_img(TEXT["s3_head"], fit_font(TEXT["s3_head"], BLACK, 120, maxw))
    note, pad = paper_card(800, 470, color=(252, 249, 240), seed=51, torn=("b",))
    d = ImageDraw.Draw(note)
    d.text((pad + 400, pad + 245), TEXT["s3_price"], font=font(BLACK, 196), fill=ACCENT, anchor="mm")
    note.alpha_composite(tape(220, 62, 2, -6), (pad + 290, 6))
    a.s3_note = note
    a.s3_n1 = text_img(TEXT["s3_note1"], font(MARKER, 78))
    a.s3_n2 = text_img(TEXT["s3_note2"], font(MARKER, 78))
    # S4
    lab = text_img(TEXT["s4_label"], font(BOLD, 44), (250, 246, 236))
    strip, pad = paper_card(lab.width + 70, lab.height + 44, color=INK, seed=61, torn=("l", "r"),
                            amp=6)
    strip.alpha_composite(lab, (pad + 35, pad + 22))
    a.s4_label = strip
    a.s4_head = text_img(TEXT["s4_head"], fit_font(TEXT["s4_head"], BLACK, 116, maxw))
    btn = Image.new("RGBA", (880 * 2, 230 * 2), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((16, 24, 880 * 2 - 16, 230 * 2 - 8), radius=110, fill=(120, 40, 20, 255))
    bd.rounded_rectangle((16, 8, 880 * 2 - 16, 230 * 2 - 24), radius=110, fill=ACCENT,
                         outline=INK, width=10)
    btn = btn.resize((880, 230), Image.LANCZOS)
    f = fit_font(TEXT["s4_cta"], BLACK, 78, 760)
    ImageDraw.Draw(btn).text((440, 108), TEXT["s4_cta"], font=f, fill=(255, 250, 242), anchor="mm")
    btn.alpha_composite(tape(170, 52, 5, 8), (30, 0))
    a.s4_btn = btn
    return a


# ---------------------------------------------------------------- scenes ----
def enter(f, start, dur, frm, to, rot0=0.0, rot1=0.0):
    p = hop(f, start, dur)
    return (frm[0] + (to[0] - frm[0]) * p, frm[1] + (to[1] - frm[1]) * p,
            rot0 + (rot1 - rot0) * p, p)


def bg(canvas, a, key, f):
    dx, dy = drift(f, 0.5)
    canvas.paste(a.sheets[key], (int(-30 + dx), int(-30 + dy)))


def scene1(c, a, f):
    bg(c, a, "s1", f)
    dx, dy = drift(f, 1.0)
    x, y, r, p = enter(f, cue("s1 kad aircond") - 4, 12, (540, 1500), (540, 1060), 8, -2)
    if p > 0:
        place(c, "s1_card", a.s1_card, x + dx, y + dy, r, log="s1 kad" if p == 1 else None)
    # habuk terapung keluar dari sirip
    if f >= 8:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        rng = random.Random(99)
        for i in range(46):
            sx = rng.uniform(230, 850)
            spd = rng.uniform(2.2, 4.5)
            t = (f - 8) * spd + rng.uniform(0, 140)
            yy = 1240 + (t % 300)
            xx = sx + 18 * math.sin((t + i * 20) / 40)
            rr = rng.uniform(3, 8)
            al = int(150 * (1 - (t % 300) / 300))
            d.ellipse((xx - rr, yy - rr, xx + rr, yy + rr), fill=(110, 104, 94, al))
        c.paste(ov, (0, 0), ov.filter(ImageFilter.GaussianBlur(1.2)))
    hx, hy = drift(f, 1.4)
    for key, img, start, ty in (("s1_l1", a.s1_l1, cue("s1 tajuk baris 1"), 330),
                                ("s1_l2", a.s1_l2, cue("s1 tajuk baris 2"), 470)):
        x, y, r, p = enter(f, start - 2, 8, (-600, ty), (540, ty), -6, 0)
        if p > 0:
            place(c, key, img, x + hx, y + hy, r, log=key if p == 1 else None)
    # garis bawah marker di bawah "penuh habuk?"
    s = cue("s1 garis bawah")
    w2 = a.s1_l2.width
    marker_stroke(c, wobbly_line((540 - w2 / 2 + hx, 560 + hy), (540 + w2 / 2 + hx, 552 + hy), seed=2),
                  (f - s) / 8, width=9, color=INK)
    # nota tangan + anak panah ke sirip
    s = cue("s1 anak panah habuk")
    if f >= s:
        place(c, "s1_note", a.s1_note, 250 + hx, 1500 + hy, 6, log="s1 nota")
        pts = curve((330, 1435), (400, 1330), (480, 1245))
        marker_stroke(c, [(x + hx, y + hy) for x, y in pts], (f - s) / 9, width=9)
        if f >= s + 9:
            marker_stroke(c, [(x + hx, y + hy) for x, y in arrow_head((480, 1245), pts[-6])], 1, width=9)


def scene2(c, a, f):
    bg(c, a, "s2", f)
    hx, hy = drift(f, 1.4)
    x, y, r, p = enter(f, cue("s2 tajuk") - 2, 8, (540, 120), (540, 360), 0, -1)
    if p > 0:
        place(c, "s2_head", a.s2_head, x + hx, y + hy, r, log="s2 tajuk" if p == 1 else None)
    dx, dy = drift(f, 1.0)
    x, y, r, p = enter(f, cue("s2 kad 1 spray") - 2, 10, (1500, 760), (540, 760), 10, -2.5)
    if p > 0:
        place(c, "s2_c1", a.s2_c1, x + dx, y + dy, r, log="s2 kad1" if p == 1 else None)
    x, y, r, p = enter(f, cue("s2 kad 2 bilas") - 2, 10, (-500, 1250), (540, 1250), -10, 2)
    if p > 0:
        place(c, "s2_c2", a.s2_c2, x + dx, y + dy, r, log="s2 kad2" if p == 1 else None)
    s = cue("s2 anak panah")
    pts = curve((930, 900), (1010, 1010), (950, 1100))
    pts = [(x + hx, y + hy) for x, y in pts]
    marker_stroke(c, pts, (f - s) / 8, width=9, color=ACCENT)
    if f >= s + 8:
        marker_stroke(c, arrow_head(pts[-1], pts[-6], 30), 1, width=9, color=ACCENT)


def scene3(c, a, f):
    bg(c, a, "s3", f)
    hx, hy = drift(f, 1.4)
    x, y, r, p = enter(f, cue("s3 tajuk") - 2, 8, (540, 120), (540, 400), 0, 0)
    if p > 0:
        place(c, "s3_head", a.s3_head, x + hx, y + hy, r, log="s3 tajuk" if p == 1 else None)
    dx, dy = drift(f, 1.0)
    st = cue("s3 nota RM150") - 3
    x, y, r, p = enter(f, st, 10, (540, 1700), (540, 920), -6, 2.5)
    sc = 1.0 + 0.06 * (1 - p) if p > 0 else 1
    if p > 0:
        place(c, "s3_note", a.s3_note, x + dx, y + dy, r, sc, log="s3 nota" if p == 1 else None)
    s = cue("s3 bulatan RM150")
    marker_stroke(c, [(x + dx, y + dy) for x, y in hand_ellipse(540, 930, 330, 140)], (f - s) / 14,
                  width=10, color=INK)
    s = cue("s3 nota tangan")
    for i, (key, img, ty) in enumerate((("s3_n1", a.s3_n1, 1330), ("s3_n2", a.s3_n2, 1440))):
        x, y, r, p = enter(f, s + i * 3, 6, (540, ty + 40), (540, ty), -2, -2)
        if p > 0:
            place(c, key, img, x + hx, y + hy, r, alpha=min(1, p * 1.5), log=key if p == 1 else None)


def scene4(c, a, f):
    bg(c, a, "s4", f)
    hx, hy = drift(f, 1.4)
    x, y, r, p = enter(f, cue("s4 label") - 2, 8, (-500, 400), (540, 400), -4, -1.5)
    if p > 0:
        place(c, "s4_label", a.s4_label, x + hx, y + hy, r, log="s4 label" if p == 1 else None)
    x, y, r, p = enter(f, cue("s4 tajuk") - 2, 8, (540, 420), (540, 600), 0, 0)
    if p > 0:
        place(c, "s4_head", a.s4_head, x + hx, y + hy, r, log="s4 tajuk" if p == 1 else None)
    dx, dy = drift(f, 1.0)
    x, y, r, p = enter(f, cue("s4 butang CTA") - 2, 10, (540, 1900), (540, 1080), 6, -1)
    press = cue("s4 tekan butang")
    sc = 1.0
    if press <= f < press + 6:
        sc = 0.94 + 0.06 * ((f - press) / 6)
    if p > 0:
        place(c, "s4_btn", a.s4_btn, x + dx, y + dy, r, sc, log="s4 butang" if p == 1 else None)
    s = cue("s4 anak panah CTA")
    pts = curve((540, 1250), (600, 1370), (540, 1500))
    pts = [(x + hx, y + hy) for x, y in pts]
    marker_stroke(c, pts, (f - s) / 8, width=11, color=INK)
    if f >= s + 8:
        marker_stroke(c, arrow_head(pts[-1], pts[-6], 40), 1, width=11, color=INK)


SCENE_FN = {"s1": scene1, "s2": scene2, "s3": scene3, "s4": scene4}


def wipe(c, a, key, f):
    start, dur = WIPES[key]
    if not (start <= f < start + dur + 1):
        return False
    img, side = a.wipe[key]
    p = hop(f, start, dur)
    if p >= 1:
        return False
    ox, oy = -30 - 40, -30 - 40  # pad tepi
    if side == "l":
        x, y = ox + (W + 120) * (1 - p), oy
    elif side == "r":
        x, y = ox - (W + 120) * (1 - p), oy
    else:
        x, y = ox, oy + (H + 120) * (1 - p)
    c.paste(img, (int(x), int(y)), img)
    return True


def render_frame(a, f):
    c = Image.new("RGB", (W, H), BG)
    # babak semasa: babak terakhir yang wipe-nya sudah tamat
    cur = "s1"
    for k in ("s2", "s3", "s4"):
        st, du = WIPES[k]
        if f >= st + du:
            cur = k
    SCENE_FN[cur](c, a, f)
    for k in ("s2", "s3", "s4"):
        st, du = WIPES[k]
        if st <= f < st + du:
            wipe(c, a, k, f)
    return c


def main(out_path, stills_dir=None):
    a = build_assets()
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "17", "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    for f in range(DURATION_F):
        LAYOUT_LOG.clear()
        img = render_frame(a, f)
        if stills_dir and f in (0, 3, 12, 60, 74, 100, 150, 164, 200, 230, 238, 280, 299):
            img.save(os.path.join(stills_dir, f"f{f:03d}.png"))
        if f in (69, 159, 234, 299):  # frame akhir setiap babak: semak kawasan selamat
            for name, x0, y0, x1, y1 in LAYOUT_LOG:
                ok = x0 >= SAFE_SIDE - 60 and x1 <= W - SAFE_SIDE + 60 and y0 >= SAFE_TOP - 60 \
                    and y1 <= SAFE_BOTTOM + 60
                print(f"[layout f{f}] {name:12s} x{x0}-{x1} y{y0}-{y1} {'OK' if ok else 'LUAR KAWASAN SELAMAT'}")
        proc.stdin.write(img.tobytes())
        if f % 50 == 0:
            print(f"frame {f}/{DURATION_F}", file=sys.stderr)
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
