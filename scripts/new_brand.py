"""Yangi brend profilini yaratadi: brands/<nom>/ (brand.json, logo, papkalar) va samples/<nom>/.

Misol:
    python scripts/new_brand.py ilm-markazi --title "Ilm markazi" --handle @ilm_markazi --logo C:\\yo'l\\logo.png
    python scripts/new_brand.py ilm-markazi --accent "#1E5BFF" --preset glow --update

Rang berilmasa, logotipdagi eng ko'p uchraydigan yorqin rang olinadi (natijani tekshiring).
Bor brend ustidan faqat --update bilan yoziladi (unda ko'rsatilgan maydonlargina o'zgaradi).
"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
from pathlib import Path

import common as C

PRESETS = ("clean", "glow", "box", "serif")


def dominant_color(image_path: Path) -> str | None:
    """Rasmdagi asosiy yorqin rang (#RRGGBB). Rangli piksel bo'lmasa None."""
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.open(image_path).convert("RGBA").resize((96, 96))
    buckets: dict = {}
    raw = img.tobytes()
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.35 or v < 0.3:
            continue  # oq, qora va kulrang hisobga olinmaydi
        key = int(h * 24)
        acc = buckets.setdefault(key, [0, 0, 0, 0, 0.0])
        acc[0] += 1
        acc[1] += r
        acc[2] += g
        acc[3] += b
        acc[4] += s * v
    if not buckets:
        return None
    n, r, g, b, _ = max(buckets.values(), key=lambda x: x[4])
    return "#%02X%02X%02X" % (round(r / n), round(g / n), round(b / n))


def main() -> int:
    ap = argparse.ArgumentParser(description="Yangi brend profilini yaratadi (brands/<nom>/).")
    ap.add_argument("name", help="Papka nomi: faqat lotin harf, raqam, - va _ (masalan ilm-markazi)")
    ap.add_argument("--title", help="Brendning ko'rinadigan nomi (oxirgi kadrda chiqadi)")
    ap.add_argument("--handle", help="Instagram manzili (masalan @ilm_markazi)")
    ap.add_argument("--logo", help="Logotip fayli (shaffof fonli PNG ma'qul)")
    ap.add_argument("--accent", help="Urg'u rangi #RRGGBB (berilmasa logotipdan olinadi)")
    ap.add_argument("--preset", choices=PRESETS, help="Subtitr uslubi (standart: clean)")
    ap.add_argument("--font", help="Shrift oilasi (masalan Inter, Montserrat, Oswald)")
    ap.add_argument("--update", action="store_true", help="Bor brendni yangilash")
    args = ap.parse_args()

    name = args.name.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name) or name.startswith("_"):
        raise C.MontajError(f"Brend nomi noto'g'ri: {name!r}. Faqat lotin harf, raqam, - va _ (masalan ilm-markazi).")
    bdir = C.BRANDS_DIR / name
    bfile = bdir / "brand.json"
    if bfile.is_file() and not args.update:
        raise C.MontajError(f"Bu brend allaqachon bor: {bdir}\nYangilash uchun --update qo'shing.")
    if args.accent and not re.fullmatch(r"#[0-9a-fA-F]{6}", args.accent):
        raise C.MontajError(f"Rang noto'g'ri: {args.accent!r}. To'g'ri ko'rinish: #RRGGBB")

    if bfile.is_file():
        data = C.read_json(bfile, "brand.json")
    else:
        template = C.BRANDS_DIR / "_shablon" / "brand.json"
        data = C.read_json(template, "Brend shabloni") if template.is_file() else {"style": {}}
        data.pop("_izoh", None)
        data["name"] = args.title or name
    style = data.setdefault("style", {})
    cap, logo, end = style.setdefault("captions", {}), style.setdefault("logo", {}), style.setdefault("endcard", {})
    for folder in ("fonts", "music", "sfx", "assets"):
        (bdir / folder).mkdir(parents=True, exist_ok=True)
    (C.SAMPLES_DIR / name).mkdir(parents=True, exist_ok=True)

    notes = []
    if args.title:
        data["name"] = args.title
        end["text"] = args.title
    elif not bfile.is_file():
        end["text"] = data["name"]
    if args.handle:
        end["handle"] = args.handle if args.handle.startswith("@") else "@" + args.handle
    elif not bfile.is_file():
        end["handle"] = ""
    if args.logo:
        src = C.need_file(args.logo, "Logotip")
        try:
            from PIL import Image
            Image.open(src).convert("RGBA").save(bdir / "logo.png")
        except ImportError:
            raise C.MontajError("Logotipni saqlash uchun Pillow kerak: pip install pillow") from None
        except Exception as exc:
            raise C.MontajError(f"Logotipni o'qib bo'lmadi ({src.name}): {exc}") from exc
        logo["file"] = "logo.png"
    elif not (bdir / "logo.png").is_file():
        logo["file"] = ""
        if not bfile.is_file():
            notes.append("Logotip berilmadi: logo.png ni shu papkaga tashlang va brand.json da logo.file ni \"logo.png\" qiling.")
    accent = args.accent
    if not accent and args.logo:
        accent = dominant_color(bdir / "logo.png")
        if accent:
            notes.append(f"Urg'u rangi logotipdan olindi: {accent} (to'g'riligini tekshiring).")
        else:
            notes.append("Logotipda yorqin rang topilmadi, urg'u rangi o'zgarmadi.")
    if accent:
        cap["accent"] = accent.upper()
    if args.preset:
        cap["preset"] = args.preset
    if args.font:
        cap["font"] = args.font
    end.setdefault("enabled", bool(end.get("text") or logo.get("file")))

    bfile.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    C.load_style(brand=name)  # yozilgan fayl o'qilishini tekshirish
    C.info(f"Brend tayyor: {bdir}")
    C.info(f"  nom: {data['name']}, uslub: {cap.get('preset', 'clean')}, rang: {cap.get('accent', '-')}, "
           f"logotip: {logo.get('file') or 'yoq'}, manzil: {end.get('handle') or '-'}")
    C.info(f"  namunalar uchun papka: {C.SAMPLES_DIR / name}")
    for note in notes:
        C.info("  ! " + note)
    C.info(f"Ishlatish: python scripts/pipeline.py input/video.mp4 --brand {name}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
