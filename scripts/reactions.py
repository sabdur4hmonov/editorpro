"""Videodagi "reaksiya" joylarini topadi: nutq yo'q, lekin ovoz baland bo'lgan paytlar (kulgu, olqish, shovqin).

    python scripts/reactions.py input/video.mp4 --words temp/video/orig.words.json

Agent ovozni eshita olmaydi. Bu skript eshitish o'rniga o'lchaydi: ovoz balandligini so'z vaqtlari
bilan solishtiradi. So'z aytilmayotgan, lekin ovoz baland joy katta ehtimol bilan tomoshabin kulgusi
yoki olqishi. Shu joylarga emoji otilishi, konfetti, zarba (punch) qo'yish mumkin.

Natija: temp/<nom>/reactions.json  ({"reactions": [{"start", "end", "level", "strength"}], ...})
Bu taxmin: musiqa yoki whisper tashlab ketgan nutq ham shunday ko'rinishi mumkin. Shubhali joyni kadrdan tekshiring.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np

import common as C

HOP = 0.05


def envelope(media: Path, sr: int = 16000) -> np.ndarray:
    """Ovoz balandligi (dBFS), har 50 ms uchun."""
    proc = subprocess.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(media),
                           "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        raise C.MontajError(f"Ovozni o'qib bo'lmadi: {media.name}: " + proc.stderr.decode("utf-8", "replace")[-200:])
    data = np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768.0
    hop = int(sr * HOP)
    n = len(data) // hop
    if n == 0:
        return np.zeros(0, np.float32)
    rms = np.sqrt((data[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    return 20.0 * np.log10(rms)


def find(media: Path, words: list, min_len: float = 0.6, pad: float = 0.12) -> dict:
    db = envelope(media)
    n = len(db)
    if n == 0:
        return {"reactions": [], "speech_db": None, "floor_db": None}
    speech = np.zeros(n, bool)
    for w in words:
        a, b = int(max(0.0, float(w["start"]) - pad) / HOP), int((float(w["end"]) + pad) / HOP) + 1
        speech[a:min(n, b)] = True
    speech_db = float(np.median(db[speech])) if speech.any() else float(np.percentile(db, 80))
    floor_db = float(np.percentile(db, 8))
    # nutqsiz joyda ovoz nutq darajasiga yaqin (yoki undan baland) bo'lsa: reaksiya
    thr = max(floor_db + 8.0, speech_db - 9.0)
    hot = (~speech) & (db > thr)
    out, i = [], 0
    while i < n:
        if not hot[i]:
            i += 1
            continue
        j = i
        while j < n and (hot[j] or (j + 1 < n and hot[j + 1] and not speech[j])):   # 1 kadrlik uzilish kechiriladi
            j += 1
        if (j - i) * HOP >= min_len:
            level = float(db[i:j].mean())
            out.append({"start": round(i * HOP, 2), "end": round(j * HOP, 2), "level": round(level, 1),
                        "strength": round(min(1.0, max(0.0, (level - thr) / 12.0 + 0.3)), 2)})
        i = j
    return {"reactions": out, "speech_db": round(speech_db, 1), "floor_db": round(floor_db, 1), "threshold_db": round(thr, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Nutqsiz, lekin ovoz baland joylarni (kulgu, olqish) topadi.")
    ap.add_argument("media", help="Video yoki audio")
    ap.add_argument("--words", required=True, help="So'zlar fayli (orig.words.json yoki cut.words.json)")
    ap.add_argument("--min", type=float, default=0.6, help="Eng qisqa reaksiya, soniya (standart 0.6)")
    ap.add_argument("-o", "--output", help="Natija JSON (standart: so'zlar fayli yonida reactions.json)")
    args = ap.parse_args()
    media = C.need_file(args.media, "Fayl")
    wpath = C.need_file(args.words, "So'zlar fayli")
    words = C.read_json(wpath).get("words", [])
    res = find(media, words, args.min)
    out = Path(args.output) if args.output else wpath.with_name("reactions.json")
    C.guard_output(out, media)
    C.write_json(dict(res, source=str(media)), out)
    C.info(f"Nutq darajasi: {res['speech_db']} dB, jimlik: {res['floor_db']} dB, chegara: {res.get('threshold_db')} dB")
    if not res["reactions"]:
        C.info("Reaksiya (nutqsiz baland joy) topilmadi.")
    for r in res["reactions"]:
        C.info(f"  {C.fmt_time(r['start'])} - {C.fmt_time(r['end'])}  ({r['end'] - r['start']:.1f}s, {r['level']} dB, kuch {r['strength']})")
    C.info(f"TAYYOR: {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
