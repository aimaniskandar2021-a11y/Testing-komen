"""Soundtrack instrumental + SFX procedural (numpy). Guna CUES yang sama dengan visual."""
import sys
import wave

import numpy as np

from timeline import CUES, DURATION_F, FPS, SCENES

SR = 48000
N = int(SR * DURATION_F / FPS) + SR // 2  # ekor 0.5s, dipotong ketika mux
rng = np.random.default_rng(3)
BPM = 100
BEAT = 60 / BPM


def t_of(frame):
    return frame / FPS


def env(n, a, d):
    """attack (s), decay eksponen (s)."""
    t = np.arange(n) / SR
    e = np.exp(-t / d)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def onepole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def hp(x, cutoff):
    return x - onepole_lp(x, cutoff)


def add(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------ instruments ---
def pluck(freq, dur=0.9, amp=0.18):
    """Bunyi kayu/marimba lembut."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t / 0.05)
    return amp * s * env(n, 0.004, 0.32)


def pad(freqs, dur, amp=0.05):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t) for f in freqs)
    e = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.4)
    return amp * s * np.clip(e, 0, 1) / len(freqs)


def soft_kick(amp=0.32):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    f = 55 + 60 * np.exp(-t / 0.03)
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.07)


def shaker(amp=0.05):
    n = int(0.06 * SR)
    s = hp(rng.normal(0, 1, n), 5000)
    return amp * s * env(n, 0.006, 0.018)


def bass(freq, dur, amp=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(2 * np.pi * freq * 2 * t)
    return amp * s * env(n, 0.01, 0.35)


# ------------------------------------------------------------ SFX -----------
def sfx_tick():
    n = int(0.035 * SR)
    s = hp(rng.normal(0, 1, n), 2500)
    return 0.22 * s * env(n, 0.0005, 0.007)


def sfx_slide():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    s = hp(onepole_lp(noise, 3500), 600)
    e = np.sin(np.pi * np.minimum(1, t / 0.32)) ** 1.5
    # sedikit "flap" kertas di hujung
    tail = sfx_tick()
    out = 0.32 * s * e
    out[int(0.24 * SR): int(0.24 * SR) + len(tail)] += tail[: n - int(0.24 * SR)]
    return out


def sfx_scribble(dur=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = hp(onepole_lp(rng.normal(0, 1, n), 4500), 1200)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 13 * t)
    e = np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.04)
    return 0.11 * s * am * e


def sfx_tape():
    n = int(0.18 * SR)
    s = hp(rng.normal(0, 1, n), 1800)
    crackle = (rng.random(n) > 0.985) * rng.normal(0, 1, n) * 2
    e = env(n, 0.003, 0.06)
    return 0.13 * (s + crackle) * e


def sfx_click():
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1800 * t) * env(n, 0.0005, 0.008) + \
        0.6 * np.sin(2 * np.pi * 170 * t) * env(n, 0.001, 0.03)
    return 0.3 * s


SFX = {"tick": sfx_tick, "slide": sfx_slide, "scribble": sfx_scribble,
       "tape": sfx_tape, "click": sfx_click}


def build():
    music = np.zeros(N)
    sfx = np.zeros(N)

    # Progresi: Hook (sparse) -> isi (pluck + kick) -> CTA (resolve + chime)
    chords = [  # (bar mula dalam beat, akar MIDI, nada pluck)
        [57, 60, 64, 67],  # Am7
        [53, 57, 60, 64],  # Fmaj7
        [48, 52, 55, 59],  # Cmaj7
        [55, 59, 62, 67],  # G
    ]
    s1_end = t_of(SCENES["s1"][1])
    s4_start = t_of(SCENES["s4"][0])
    total = DURATION_F / FPS
    nbeats = int(total / BEAT) + 1
    for b in range(nbeats):
        tb = b * BEAT
        ch = chords[(b // 4) % 4]
        if b % 4 == 0:
            music_pad = pad([midi(m) for m in ch], min(4 * BEAT + 0.3, total + 0.4 - tb), 0.05)
            add(music, music_pad, tb)
            add(music, bass(midi(ch[0] - 12), 4 * BEAT), tb)
        # shaker sepanjang masa (ringan)
        add(music, shaker(0.035), tb + BEAT / 2)
        if tb >= s1_end - 0.05:
            add(music, soft_kick(0.26 if b % 2 == 0 else 0.16), tb)
            add(music, shaker(0.05), tb + BEAT * 0.75)
            # arpeggio pluck
            add(music, pluck(midi(ch[(b % 4)] + 12), amp=0.10), tb)
            add(music, pluck(midi(ch[((b + 2) % 4)] + 12), amp=0.07), tb + BEAT / 2)
        elif b % 2 == 0:
            add(music, pluck(midi(ch[1] + 12), amp=0.07), tb)
    # CTA: chime resolve ke C major
    for i, m in enumerate([72, 76, 79, 84]):
        add(music, pluck(midi(m), dur=1.6, amp=0.08), s4_start + 0.9 + i * 0.07)

    for f, kind, _ in CUES:
        add(sfx, SFX[kind](), t_of(f))

    # tiada VO — jika VO ditambah, kurangkan muzik ~8 dB di bawah dialog di sini
    mix = music * 0.85 + sfx
    # fade out lembut 0.4s terakhir
    fo = int(0.4 * SR)
    end = int(total * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo) ** 0.8
    mix[end:] = 0
    peak = np.max(np.abs(mix))
    mix = mix / peak * 10 ** (-1.5 / 20)  # puncak -1.5 dBFS
    return mix


def main(path):
    mix = build()
    data = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    stereo = np.stack([data, data], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    print(f"audio: {path}  peak {20 * np.log10(np.max(np.abs(mix))):.2f} dBFS")


if __name__ == "__main__":
    main(sys.argv[1])
