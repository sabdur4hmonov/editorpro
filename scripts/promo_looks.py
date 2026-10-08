"""Promo uslub yo'nalishlari: tanlash, per-video uslubga qo'llash, kadrdan rang olish, tarixni yozish.

    python scripts/promo_looks.py list                                   # yo'nalishlar va oxirgi promolar
    python scripts/promo_looks.py palette temp/<nom>/<nom>.mp4           # kadrlardan asosiy ranglar va accent taklifi
    python scripts/promo_looks.py apply bold_caps --style temp/<nom>/style.json --accent "#FF5A1F"
    python scripts/promo_looks.py record bold_caps --job <nom> --accent "#FF5A1F"

Yo'nalishlar style/promo_looks.json da (faqat mavjud preset/element/style kalitlari), tarix
style/promo_history.json da. apply oxirgi promo bilan bir xil yo'nalishni rad etadi (--allow-repeat bilan ruxsat).
"""
from __future__ import annotations

import argparse
import colorsys
import datetime
from pathlib import Path
import subprocess

import numpy as np

import common as C

LOOKS_PATH = C.ROOT / "style" / "promo_looks.json"
HISTORY_PATH = C.ROOT / "style" / "promo_history.json"


def load_looks(path: Path | None = None) -> dict:
    path = path or LOOKS_PATH
    data = C.read_json(path, "Promo yo'nalishlari")
    looks = data.get("looks")
    if not isinstance(looks, dict) or not looks:
        raise C.MontajError(f"{path}: \"looks\" bo'sh yoki yo'q.")
    return looks


def load_history(path: Path | None = None) -> list:
    path = path or HISTORY_PATH
    if not path.is_file():
        return []
    return list(C.read_json(path, "Promo tarixi").get("history", []))


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(max(0, min(255, round(v)))) for v in rgb])


def _norm_hex(value: str) -> str:
    v = str(value).strip()
    if not v.startswith("#") or len(v) != 7:
        raise C.MontajError(f"Rang #RRGGBB ko'rinishida bo'lsin: {value!r}")
    int(v[1:], 16)
    return v.upper()


def palette(video: Path, n_frames: int = 8, k: int = 6) -> dict:
    """Videodan teng oraliqda kadrlar olib asosiy ranglarni topadi va accent taklif qiladi.

    accent_warm: eng to'yingan iliq rang (sariq-to'q sariq), accent_food: eng to'yingan rang,
    caption_zone: subtitr joyi (kadrning 0.55-0.80 qismi) o'rtacha yorqinligi (0..1).
    """
    meta = C.ffprobe_info(video)
    ff = C.need_tool("ffmpeg")
    pixels, zone = [], []
    for i in range(n_frames):
        t = meta["duration"] * (i + 0.5) / n_frames
        raw = subprocess.run([ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                              "-vf", "scale=90:160", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, stdin=subprocess.DEVNULL).stdout
        if len(raw) < 90 * 160 * 3:
            continue
        img = np.frombuffer(raw[:90 * 160 * 3], np.uint8).reshape(160, 90, 3)
        pixels.append(img.reshape(-1, 3))
        zone.append(img[int(160 * 0.55):int(160 * 0.80)].mean())
    if not pixels:
        raise C.MontajError(f"Kadr olib bo'lmadi: {video}")
    import cv2
    data = np.concatenate(pixels).astype(np.float32)
    _, labels, centers = cv2.kmeans(data, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
                                    3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(labels.ravel(), minlength=k) / len(labels)
    colors = []
    for c, s in sorted(zip(centers, share), key=lambda x: -x[1]):
        h, sat, val = colorsys.rgb_to_hsv(*(c / 255.0))
        colors.append({"hex": _hex(c), "share": round(float(s), 3), "hue": round(h * 360), "sat": round(sat, 2),
                       "val": round(val, 2)})

    def boosted(c: dict) -> str:
        r, g, b = colorsys.hsv_to_rgb(c["hue"] / 360.0, max(c["sat"], 0.8), 1.0)
        return _hex((r * 255, g * 255, b * 255))

    vivid = [c for c in colors if c["sat"] >= 0.3 and c["val"] >= 0.25]
    warm = [c for c in vivid if 15 <= c["hue"] <= 60]
    pick = lambda arr: boosted(max(arr, key=lambda c: c["sat"] * c["share"] ** 0.5)) if arr else None
    return {"video": str(video), "colors": colors, "accent_warm": pick(warm), "accent_food": pick(vivid),
            "caption_zone": round(float(np.mean(zone)) / 255.0, 2)}


def apply(name: str, style_path: Path, accent: str | None = None, allow_repeat: bool = False) -> dict:
    looks = load_looks()
    if name not in looks:
        raise C.MontajError(f"Noma'lum promo yo'nalishi: {name}. Mumkin: {', '.join(looks)}")
    history = load_history()
    if history and history[-1].get("look") == name and not allow_repeat:
        raise C.MontajError(f"Oldingi promo ({history[-1].get('job')}) ham {name} edi. Boshqa yo'nalish tanlang "
                            "yoki foydalanuvchi so'rasa --allow-repeat.")
    look = looks[name]
    style = C.read_json(style_path, "Per-video style.json")
    style = C.deep_merge(style, look.get("style", {}))
    style.setdefault("captions", {})["accent"] = _norm_hex(accent or look.get("default_accent", "#FFE600"))
    style["_promo_look"] = name
    C.write_json(style, C.guard_output(style_path))
    C.load_style(style_path)                    # buzilmaganini tekshiradi
    return look


def record(name: str, job: str, accent: str, note: str = "") -> None:
    looks = load_looks()
    if name not in looks:
        raise C.MontajError(f"Noma'lum promo yo'nalishi: {name}")
    data = C.read_json(HISTORY_PATH, "Promo tarixi") if HISTORY_PATH.is_file() else {"history": []}
    data.setdefault("history", []).append({"date": datetime.date.today().isoformat(), "job": job, "look": name,
                                           "accent": _norm_hex(accent), "note": note})
    C.write_json(data, HISTORY_PATH)


def main() -> int:
    ap = argparse.ArgumentParser(description="Promo uslub yo'nalishlari.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Yo'nalishlar va tarix")
    p = sub.add_parser("palette", help="Kadrlardan ranglar va accent taklifi")
    p.add_argument("video")
    p.add_argument("--out", help="Natija JSON (masalan temp/<nom>/palette.json)")
    a = sub.add_parser("apply", help="Yo'nalishni per-video style.json ga qo'llash")
    a.add_argument("name")
    a.add_argument("--style", required=True, help="temp/<nom>/style.json (style/style.json emas)")
    a.add_argument("--accent", help="#RRGGBB (palette taklifidan)")
    a.add_argument("--allow-repeat", action="store_true", help="Oldingi promo bilan bir xil yo'nalishga ruxsat")
    r = sub.add_parser("record", help="Final tayyor bo'lgach yo'nalishni tarixga yozish")
    r.add_argument("name")
    r.add_argument("--job", required=True)
    r.add_argument("--accent", required=True)
    r.add_argument("--note", default="")
    args = ap.parse_args()
    if args.cmd == "list":
        for key, look in load_looks().items():
            C.info(f"  {key:<16} {look.get('title', '')} | namunalar {look.get('samples')} | {look.get('fits', '')}")
        hist = load_history()
        C.info("Oxirgi promolar: " + (", ".join(f"{h['job']}={h['look']}" for h in hist[-5:]) if hist else "yo'q"))
    elif args.cmd == "palette":
        res = palette(C.need_file(args.video, "Video"))
        if args.out:
            C.write_json(res, C.guard_output(args.out))
        C.info("Ranglar: " + ", ".join(f"{c['hex']} {c['share']:.0%}" for c in res["colors"]))
        C.info(f"accent_warm: {res['accent_warm']}  accent_food: {res['accent_food']}  "
               f"subtitr zonasi yorqinligi: {res['caption_zone']} (0.6 dan yuqori: soya/gradiyent kerak)")
    elif args.cmd == "apply":
        if Path(args.style).resolve() == (C.ROOT / "style" / "style.json").resolve():
            raise C.MontajError("Umumiy style/style.json ga emas, per-video temp/<nom>/style.json ga qo'llang.")
        look = apply(args.name, Path(args.style), args.accent, args.allow_repeat)
        C.info(f"Qo'llandi: {args.name} -> {args.style}\n  Belgilar: {look.get('tags')}\n  Elementlar: {look.get('elements')}")
    elif args.cmd == "record":
        record(args.name, args.job, args.accent, args.note)
        C.info(f"Yozildi: {HISTORY_PATH}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
