"""Project-original SFX synthesis v2 (numpy only): layered whooshes, impacts, clicks, pops, risers, dings.

    python scripts/sfx_synth.py                 # all categories, 4 variants each -> assets/sfx/<category>/synth_v2_NN.wav
    python scripts/sfx_synth.py --only whoosh --variants 6 --force
    python scripts/sfx_synth.py --out temp/sfx_test   # anywhere inside the project (tests)

Every file is generated from a fixed seed (category + variant number), so a re-run gives the same audio.
Loudness is made consistent by a measured rule: the loudest 100 ms window is set to `TARGET_RMS_DB`
(dBFS RMS) and the sample peak is kept at or below `PEAK_DB`. That is a level match, not a judgement of how
the sound is perceived: the agent cannot listen. A preview per category (all variants with short gaps) goes
to `<out>/_preview/<category>.wav` for the user to audition. Real (licensed, imported) files always win over
these in sound_design.variants(); among synthesized files the highest `synth_version` is used.
"""
from __future__ import annotations

import argparse
import hashlib
import wave
from pathlib import Path

import numpy as np

import common as C

SR = 48000
VERSION = 2
TARGET_RMS_DB = -15.0       # loudest 100 ms window, dBFS RMS
PEAK_DB = -1.0              # sample peak ceiling, dBFS
LICENSE_TEXT = ("Original sound synthesized by this project (scripts/sfx_synth.py, numpy). No external recording "
                "or stock licence. Generated for project use.\n")


# ---------------------------------------------------------------- DSP helpers
def env_exp(n: int, rate: float) -> np.ndarray:
    return np.exp(-np.arange(n) / SR * rate)


def attack(sig: np.ndarray, ms: float) -> np.ndarray:
    k = max(1, int(SR * ms / 1000))
    sig = sig.copy()
    sig[:k] *= np.linspace(0, 1, k) ** 2
    return sig


def fade_out(sig: np.ndarray, ms: float) -> np.ndarray:
    k = max(1, min(len(sig), int(SR * ms / 1000)))
    sig = sig.copy()
    sig[-k:] *= np.linspace(1, 0, k) ** 2
    return sig


def sweep_tone(f0: float, f1: float, n: int, curve: float = 4.0, shape: str = "exp") -> np.ndarray:
    """Phase-continuous sine whose frequency moves f0 -> f1 (exponential decay toward f1, or linear in log)."""
    t = np.arange(n) / SR
    if shape == "exp":
        f = f1 + (f0 - f1) * np.exp(-t * curve)
    else:
        f = f0 * (f1 / f0) ** (t / max(t[-1], 1e-9))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def shaped_noise(n: int, center, width_oct, rng: np.random.Generator, frame: int = 1024, hop: int = 256) -> np.ndarray:
    """White noise through a time-varying log-frequency band (STFT gain, overlap-add).

    center/width_oct: callables of normalised time u in [0, 1] -> Hz / octaves.
    """
    pad = frame
    x = rng.standard_normal(n + 2 * pad)
    win = np.hanning(frame)
    freqs = np.fft.rfftfreq(frame, 1 / SR)
    logf = np.log2(np.maximum(freqs, 1.0))
    out = np.zeros_like(x)
    norm = np.zeros_like(x)
    for s in range(0, len(x) - frame, hop):
        u = min(1.0, max(0.0, (s - pad + frame / 2) / max(1, n)))
        c, w = float(center(u)), max(0.05, float(width_oct(u)))
        gain = np.exp(-0.5 * ((logf - np.log2(max(c, 20.0))) / (w / 2.355)) ** 2)
        spec = np.fft.rfft(x[s:s + frame] * win) * gain
        out[s:s + frame] += np.fft.irfft(spec, frame) * win
        norm[s:s + frame] += win ** 2
    out = out / np.maximum(norm, 1e-6)
    return out[pad:pad + n]


def band(sig: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Static FFT band-pass (whole-signal; fine for short one-shots)."""
    spec = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(spec, len(sig))


def stereo(mono: np.ndarray, pan_from: float = 0.0, pan_to: float = 0.0, width: float = 0.0,
           rng: np.random.Generator | None = None) -> np.ndarray:
    """Equal-power pan sweep (-1 left .. 1 right) plus optional small decorrelated width."""
    p = np.linspace(pan_from, pan_to, len(mono))
    ang = (p + 1) * np.pi / 4
    left, right = mono * np.cos(ang), mono * np.sin(ang)
    if width and rng is not None:
        d = int(SR * 0.0007)
        side = np.concatenate([np.zeros(d), mono[:-d]]) * width
        left, right = left + side, right - side
    return np.stack([left, right], axis=1) * np.sqrt(2)


def loudest_rms_db(x: np.ndarray, win_sec: float = 0.1) -> float:
    mono = x.mean(axis=1) if x.ndim == 2 else x
    k = max(1, min(len(mono), int(SR * win_sec)))
    c = np.cumsum(np.concatenate([[0.0], mono.astype(np.float64) ** 2]))
    rms = np.sqrt(np.max((c[k:] - c[:-k]) / k))
    return float(20 * np.log10(max(rms, 1e-12)))


def peak_db(x: np.ndarray) -> float:
    return float(20 * np.log10(max(float(np.max(np.abs(x))), 1e-12)))


def normalise(x: np.ndarray, target_rms_db: float = TARGET_RMS_DB, ceiling_db: float = PEAK_DB) -> np.ndarray:
    """Match the loudest 100 ms RMS to the target; tame peaks with a soft clipper, then hard-check the ceiling."""
    x = x * 10 ** ((target_rms_db - loudest_rms_db(x)) / 20)
    ceil = 10 ** (ceiling_db / 20)
    if np.max(np.abs(x)) > ceil:
        x = np.tanh(x / ceil) * ceil                      # soft clip only where the peak exceeds the ceiling
        x = x * 10 ** ((target_rms_db - loudest_rms_db(x)) / 20)
        if np.max(np.abs(x)) > ceil:                      # transient-heavy sound: keep the ceiling, report lower RMS
            x = x * (ceil / np.max(np.abs(x)))
    return x


# ---------------------------------------------------------------- recipes
def whoosh(rng):
    n = int(SR * rng.uniform(0.45, 0.8))
    peak = rng.uniform(0.5, 0.68)
    u = np.linspace(0, 1, n)
    env = np.where(u < peak, (u / peak) ** 2.2, ((1 - u) / (1 - peak)) ** 1.6)
    lo, hi = rng.uniform(250, 450), rng.uniform(1800, 3200)
    body = shaped_noise(n, lambda v: lo + (hi - lo) * np.sin(np.pi * min(1, v / (peak * 1.6))) ** 1.5,
                        lambda v: 1.3, rng) * env
    air = shaped_noise(n, lambda v: 2500 + 4500 * v, lambda v: 0.9, rng) * env ** 1.5 * rng.uniform(0.25, 0.4)
    rumble = shaped_noise(n, lambda v: 110, lambda v: 1.2, rng) * env ** 2 * rng.uniform(0.3, 0.5)
    mono = body + air + rumble
    side = -1 if rng.random() < 0.5 else 1
    return stereo(mono, -0.7 * side, 0.7 * side, 0.15, rng)


def swipe(rng):
    n = int(SR * rng.uniform(0.18, 0.3))
    u = np.linspace(0, 1, n)
    env = u ** 1.4 * (1 - u ** 8)
    mono = shaped_noise(n, lambda v: 3000 + 5000 * v, lambda v: 1.0, rng) * env
    mono += shaped_noise(n, lambda v: 900 + 1200 * v, lambda v: 1.0, rng) * env * 0.35
    return stereo(fade_out(mono, 12), -0.4, 0.4, 0.1, rng)


def pop(rng):
    n = int(SR * rng.uniform(0.12, 0.18))
    f0, f1 = rng.uniform(800, 1100), rng.uniform(260, 360)
    tone = sweep_tone(f0, f1, n, rng.uniform(35, 55))
    tone += 0.25 * sweep_tone(f0 * 2, f1 * 2, n, rng.uniform(35, 55))
    mono = attack(tone * env_exp(n, rng.uniform(24, 34)), 1.5)
    click = band(rng.standard_normal(n), 1500, 6000) * env_exp(n, 900) * 0.25
    return stereo(fade_out(mono + click, 15))


def click(rng):
    n = int(SR * rng.uniform(0.04, 0.06))
    burst = band(rng.standard_normal(n), 2000, 9000) * env_exp(n, rng.uniform(380, 520))
    ping = np.sin(2 * np.pi * rng.uniform(3200, 4800) * np.arange(n) / SR) * env_exp(n, 260) * 0.45
    thock = np.sin(2 * np.pi * rng.uniform(450, 700) * np.arange(n) / SR) * env_exp(n, 160) * 0.3
    return stereo(fade_out(attack(burst + ping + thock, 0.3), 5))


def tick(rng):
    n = int(SR * rng.uniform(0.05, 0.08))
    tone = np.sin(2 * np.pi * rng.uniform(2200, 3400) * np.arange(n) / SR) * env_exp(n, rng.uniform(110, 160))
    tick_ = band(rng.standard_normal(n), 3000, 10000) * env_exp(n, 700) * 0.4
    return stereo(fade_out(attack(tone + tick_, 0.3), 8))


def hit(rng):
    n = int(SR * rng.uniform(0.28, 0.4))
    body = sweep_tone(rng.uniform(220, 300), rng.uniform(110, 160), n, 30) * env_exp(n, rng.uniform(11, 16))
    snap = band(rng.standard_normal(n), 900, 5000) * env_exp(n, 140) * 0.7
    sub = np.sin(2 * np.pi * 60 * np.arange(n) / SR) * env_exp(n, 9) * 0.4
    mono = np.tanh(1.6 * (body + snap + sub)) / np.tanh(1.6)
    return stereo(fade_out(attack(mono, 0.8), 40), width=0.08, rng=rng)


def impact(rng):
    n = int(SR * rng.uniform(0.9, 1.25))
    sub = sweep_tone(rng.uniform(110, 140), rng.uniform(40, 52), n, 9) * env_exp(n, rng.uniform(3.5, 5))
    knock = sweep_tone(rng.uniform(260, 340), 130, n, 40) * env_exp(n, 22) * 0.6
    crash = shaped_noise(n, lambda v: 2600 * (1 - 0.7 * v) + 300, lambda v: 2.4, rng) * env_exp(n, rng.uniform(5, 8)) * 0.35
    mono = np.tanh(2.0 * (sub + knock + crash)) / np.tanh(2.0)
    return stereo(fade_out(attack(mono, 1.0), 120), width=0.2, rng=rng)


def riser(rng):
    n = int(SR * rng.uniform(1.2, 2.0))
    u = np.linspace(0, 1, n)
    env = u ** rng.uniform(2.0, 3.0)
    noise = shaped_noise(n, lambda v: 300 * (20 ** v), lambda v: 1.4, rng) * env
    f0 = rng.uniform(170, 230)
    tone = sum(np.sin(2 * np.pi * k * np.cumsum(f0 * (4 ** u)) / SR) / k for k in range(1, 6)) * env * 0.18
    mono = noise + tone
    return stereo(fade_out(mono, 25), -0.3, 0.3, 0.2, rng)


def ding(rng):
    n = int(SR * rng.uniform(1.0, 1.4))
    f = rng.choice([1046.5, 1174.7, 1318.5, 1568.0])
    t = np.arange(n) / SR
    mono = np.zeros(n)
    for ratio, amp, decay in ((1.0, 1.0, 4.0), (2.0, 0.45, 6.5), (2.76, 0.25, 9.0), (5.4, 0.12, 14.0)):
        mono += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, np.pi)) * np.exp(-t * decay * rng.uniform(0.9, 1.1))
    mono = attack(mono, 2)
    return stereo(fade_out(mono, 120), width=0.1, rng=rng)


def typing(rng):
    n = int(SR * rng.uniform(0.55, 0.8))
    mono = np.zeros(n)
    at = int(SR * 0.01)
    while at < n - int(SR * 0.05):
        m = int(SR * 0.045)
        key = band(rng.standard_normal(m), 1500, 5500) * env_exp(m, rng.uniform(350, 600)) * rng.uniform(0.5, 1.0)
        key += np.sin(2 * np.pi * rng.uniform(180, 260) * np.arange(m) / SR) * env_exp(m, 120) * 0.35
        mono[at:at + m] += key
        at += int(SR * rng.uniform(0.06, 0.13))
    return stereo(fade_out(mono, 10), width=0.05, rng=rng)


RECIPES = {"whoosh": whoosh, "swipe": swipe, "pop": pop, "click": click, "tick": tick, "hit": hit,
           "impact": impact, "riser": riser, "ding": ding, "typing": typing}


# ---------------------------------------------------------------- output
def write_wav(path: Path, x: np.ndarray) -> None:
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    if pcm.ndim == 1:
        pcm = np.stack([pcm, pcm], axis=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise C.MontajError(f"{path.name}: 16-bit PCM kutilgan.")
        data = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768
        return data.reshape(-1, w.getnchannels())


def seed_for(category: str, k: int) -> int:
    return int.from_bytes(hashlib.sha256(f"sfx-v{VERSION}:{category}:{k}".encode()).digest()[:8], "big")


def make(category: str, k: int) -> np.ndarray:
    rng = np.random.default_rng(seed_for(category, k))
    return normalise(RECIPES[category](rng))


def build(out: Path, categories, variants: int = 4, force: bool = False) -> list:
    rows = []
    for cat in categories:
        clips = []
        for k in range(1, variants + 1):
            path = out / cat / f"synth_v{VERSION}_{k:02d}.wav"
            if path.is_file() and not force:
                x = read_wav(path)
            else:
                x = make(cat, k)
                write_wav(path, x)
                C.write_json({"source": f"scripts/sfx_synth.py numpy synthesis v{VERSION} (seed {seed_for(cat, k)})",
                              "license": "Project-original generated audio; no third-party recording",
                              "category": cat, "kind": "synthesized", "synth_version": VERSION},
                             path.with_suffix(".wav.credit.json"))
                path.with_suffix(".wav.LICENSE.txt").write_text(LICENSE_TEXT, encoding="utf-8")
            clips.append(x)
            rows.append({"file": str(path), "category": cat, "duration": round(len(x) / SR, 3),
                         "loudest_100ms_rms_db": round(loudest_rms_db(x), 2), "peak_db": round(peak_db(x), 2)})
        gap = np.zeros((int(SR * 0.35), 2))
        preview = np.concatenate([np.concatenate([c, gap]) for c in clips])
        write_wav(out / "_preview" / f"{cat}.wav", preview)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="assets/sfx", help="Library folder (inside the project)")
    ap.add_argument("--only", action="append", choices=sorted(RECIPES), help="Category (repeatable)")
    ap.add_argument("--variants", type=int, default=4, help="Variants per category (1..12)")
    ap.add_argument("--force", action="store_true", help="Regenerate existing v2 files")
    ap.add_argument("--no-index", action="store_true", help="Do not re-index the library afterwards")
    a = ap.parse_args()
    if not 1 <= a.variants <= 12:
        raise C.MontajError("--variants 1..12 bo'lsin.")
    out = (C.ROOT / a.out).resolve()
    if not C.is_inside(out, C.ROOT):
        raise C.MontajError("--out loyiha papkasi ichida bo'lsin.")
    rows = build(out, a.only or list(RECIPES), a.variants, a.force)
    for r in rows:
        C.info(f"  {Path(r['file']).relative_to(C.ROOT)}  {r['duration']:.2f}s  RMS100 {r['loudest_100ms_rms_db']} dBFS"
               f"  peak {r['peak_db']} dBFS")
    if not a.no_index:
        import sfx_library
        sfx_library.index(out)
    C.info(f"SFX SYNTH v{VERSION}: {len(rows)} fayl; preview: {out / '_preview'}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
