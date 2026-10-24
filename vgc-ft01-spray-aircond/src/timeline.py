"""Satu sumber timing untuk visual DAN audio (frame @ 30fps).

Ubah teks / timing di sini, kemudian jalankan ../render.sh semula.
"""

FPS = 30
W, H = 1080, 1920
DURATION_F = 300  # 10.0 saat

# Palet (visual direction: Scrapbook Documentary) — tema sementara, tiada brand diberi
BG = (233, 223, 201)        # #e9dfc9 kertas
INK = (34, 33, 31)          # #22211f teks
ACCENT = (233, 86, 50)      # #e95632
WATER = (47, 111, 126)      # teal kusam untuk air / sejuk
CARD = (248, 244, 234)      # kertas putih kekuningan

# Kawasan selamat untuk Reels/TikTok/Shorts (elak UI platform)
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 230, 1560, 80

# ---- SKRIP (Bahasa Melayu) -------------------------------------------------
TEXT = {
    "s1_l1": "Aircond bilik anak",
    "s1_l2": "penuh habuk?",
    "s1_note": "habuk!",
    "s2_head": "Hanya spray je.",
    "s2_step1": "Spray",
    "s2_step2a": "Bilas dengan",
    "s2_step2b": "air",
    "s3_head": "Jimat upah servis",
    "s3_price": "RM150",
    "s3_note1": "tak perlu panggil",
    "s3_note2": "orang servis",
    "s4_label": "SPRAY PEMBERSIH AIRCOND",   # nama sementara — ganti dengan nama produk sebenar
    "s4_head": "Spray. Bilas. Siap.",
    "s4_cta": "Klik butang sekarang",
}

# ---- BABAK (frame mula, frame tamat eksklusif) -----------------------------
SCENES = {
    "s1": (0, 75),     # 0.0–2.5s  Hook (masalah)
    "s2": (75, 165),   # 2.5–5.5s  Cara guna (produk)
    "s3": (165, 240),  # 5.5–8.0s  USP (jimat)
    "s4": (240, 300),  # 8.0–10.0s CTA
}

# Helaian kertas baharu menyapu masuk (mula, tempoh)
WIPES = {"s2": (70, 9), "s3": (160, 9), "s4": (235, 9)}

# ---- CUE (dikongsi visual + SFX) ------------------------------------------
# jenis: tick = detik kertas kering, slide = helaian kertas, scribble = marker,
#        tape = pita, click = tekan butang
CUES = [
    (0, "tick", "s1 kad aircond"),
    (2, "tick", "s1 tajuk baris 1"),
    (8, "tick", "s1 tajuk baris 2"),
    (14, "scribble", "s1 garis bawah"),
    (30, "scribble", "s1 anak panah habuk"),
    (70, "slide", "wipe ke s2"),
    (84, "tick", "s2 tajuk"),
    (94, "tick", "s2 kad 1 spray"),
    (110, "scribble", "s2 anak panah"),
    (120, "tick", "s2 kad 2 bilas"),
    (160, "slide", "wipe ke s3"),
    (170, "tick", "s3 tajuk"),
    (180, "tape", "s3 nota RM150"),
    (192, "scribble", "s3 bulatan RM150"),
    (208, "tick", "s3 nota tangan"),
    (235, "slide", "wipe ke s4"),
    (246, "tick", "s4 label"),
    (252, "tick", "s4 tajuk"),
    (258, "tape", "s4 butang CTA"),
    (266, "scribble", "s4 anak panah CTA"),
    (276, "click", "s4 tekan butang"),
]


def cue(label):
    for f, _, name in CUES:
        if name == label:
            return f
    raise KeyError(label)
