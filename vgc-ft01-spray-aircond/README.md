# VGC-FT01 — Motion Ad: Spray Pembersih Aircond (PREVIEW)

Portrait 9:16 · 1080×1920 · 30fps · 10.0s · 100% motion · tiada VO (preview text-led)

## Direction
Scrapbook Documentary: kertas hangat, kad koyak, pita, anotasi marker. Satu fokus setiap babak,
gerakan stop-start ("on twos") kemudian hold supaya teks sempat dibaca. Parallax kecil sahaja.

| Masa | Babak | Teks |
|---|---|---|
| 0.0–2.5s | Hook (masalah) | Aircond bilik anak / **penuh habuk?** + nota "habuk!" |
| 2.5–5.5s | Cara guna | Hanya spray je. → ① Spray → ② Bilas dengan air |
| 5.5–8.0s | USP | Jimat upah servis · **RM150** (dibulatkan) · "tak perlu panggil orang servis" |
| 8.0–10.0s | CTA | SPRAY PEMBERSIH AIRCOND · Spray. Bilas. Siap. · **[Klik butang sekarang]** |

Tema sementara (tiada brand diberi): kertas `#e9dfc9`, teks `#22211f`, aksen `#e95632`, air `#2f6f7e`.

## Struktur
- `src/timeline.py` — **edit di sini**: skrip teks, timing babak, cue (dikongsi visual + SFX)
- `src/visuals.py` — renderer (Python PIL + numpy → ffmpeg). Ilustrasi aircond/spray/titisan dilukis dengan kod.
- `src/audio.py` — soundtrack instrumental + SFX procedural (numpy)
- `assets/fonts/` — Inter Display (OFL), Permanent Marker (Apache 2.0); lesen disertakan
- `out/preview.mp4` — preview · `out/contact_sheet.png` — frame semakan

## Render semula
```
./render.sh
```
Keperluan: python3 + numpy + Pillow, ffmpeg. Tiada pemasangan global/servis berbayar digunakan.
