"""Foydalanuvchi fikrlarini saqlaydi, keyingi montajlar shuni hisobga oladi.

    python scripts/feedback.py add "Subtitr pastroq tursin" --brand million --video input/video.mp4
    python scripts/feedback.py add "Effektlar nutqqa halaqit bermasin"        # umumiy (hamma videoga)
    python scripts/feedback.py show --brand million                           # umumiy + brend eslatmalari

Fayllar:
    style/notes.md            - umumiy eslatmalar (brendsiz videolarga ham tegishli)
    brands/<nom>/notes.md     - shu brendga tegishli eslatmalar

pipeline.py har ishga tushganda shu eslatmalarni ko'rsatadi: agent ularni o'qib, montajda amal qiladi.
Sozlamaga aylanadigan fikr (rang, joy, o'lcham, balandlik) eslatmadan tashqari brand.json yoki
style.json ga ham yoziladi: eslatma "nega" ni saqlaydi, sozlama esa uni har safar bajaradi.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import common as C

GENERAL = C.ROOT / "style" / "notes.md"
HEADER = ("# {title}\n\nFoydalanuvchi bergan fikrlar. Har montajdan oldin o'qiladi. "
          "Yangi fikr: `python scripts/feedback.py add \"...\"`\n\n")


def path_for(brand: str | None) -> Path:
    if not brand:
        return GENERAL
    folder = C.BRANDS_DIR / brand
    if not folder.is_dir():
        raise C.MontajError(f"Brend topilmadi: {brand!r}. Mavjudlari: {', '.join(C.list_brands()) or 'hali yoq'}")
    return folder / "notes.md"


def read_notes(brand: str | None = None) -> list:
    """Eslatmalar ro'yxati: [(manba, matn)]. Avval umumiy, keyin brend."""
    out = []
    for label, path in (("umumiy", GENERAL), (brand, C.BRANDS_DIR / brand / "notes.md" if brand else None)):
        if path is None or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("- "):
                out.append((label, line[2:].strip()))
    return out


def parse_rule(text: str) -> tuple:
    """"motion.min_exit_frames=6" -> ("motion.min_exit_frames", 6); JSON values, otherwise a string."""
    import json
    key, sep, raw = str(text).partition("=")
    key = key.strip()
    if not sep or not key or any(not part.isidentifier() for part in key.split(".")):
        raise C.MontajError(f"Qoida KALIT=QIYMAT bo'lsin (masalan motion.min_exit_frames=6): {text!r}")
    try:
        return key, json.loads(raw)
    except ValueError:
        return key, raw.strip()


def add_rules(rules: list, note: str, brand: str | None, at: list | None, video: str | None) -> Path:
    """Repeatable editor note -> rule the next render follows (style/rules.json or brands/<b>/rules.json).
    Applied by common.load_style to the shared/brand style only; approved per-video styles never change."""
    path = (C.BRANDS_DIR / brand / "rules.json") if brand else (C.ROOT / "style" / "rules.json")
    path_for(brand)
    data = C.read_json(path) if path.is_file() else {"rules": []}
    for text in rules:
        key, value = parse_rule(text)
        data["rules"] = [r for r in data["rules"] if r["key"] != key] + [
            {"key": key, "value": value, "note": note, "at": at or [], "video": Path(video).name if video else None,
             "date": time.strftime("%Y-%m-%d")}]
    C.write_json(data, path)
    test = C.load_style(None, brand)                # the rule must load; a broken value fails here, not at render
    for text in rules:
        key, value = parse_rule(text)
        cur = test
        for k in key.split("."):
            cur = cur[k]
        if cur != value:
            raise C.MontajError(f"Qoida qo'llanmadi: {key}")
    return path


def add(text: str, brand: str | None = None, video: str | None = None, at: list | None = None,
        editor: str | None = None, rules: list | None = None) -> Path:
    text = " ".join(str(text).split())
    if at:
        text = "[" + ", ".join(C.fmt_time(float(t)) for t in at) + "] " + text
    if editor:
        text = f"{text} — muharrir: {editor}"
    if rules:
        text = f"{text} (qoida: {'; '.join(rules)})"
    if not text:
        raise C.MontajError("Fikr matni bo'sh.")
    path = path_for(brand)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(HEADER.format(title=f"Eslatmalar: {brand}" if brand else "Umumiy eslatmalar"), encoding="utf-8")
    line = f"- {time.strftime('%Y-%m-%d')}: {text}" + (f" (video: {Path(video).name})" if video else "")
    body = path.read_text(encoding="utf-8-sig")
    path.write_text(body.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    return path


def print_notes(brand: str | None = None, limit: int = 40) -> None:
    notes = read_notes(brand)
    if not notes:
        return
    C.info("\n=== Eslatmalar (foydalanuvchi fikrlari, montajda amal qiling) ===")
    for label, text in notes[-limit:]:
        C.info(f"  [{label}] {text}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Foydalanuvchi fikrlarini saqlash va ko'rsatish.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="Yangi fikr qo'shish")
    a.add_argument("text")
    a.add_argument("--brand", help="Brend nomi (berilmasa umumiy)")
    a.add_argument("--video", help="Qaysi video haqida (ixtiyoriy)")
    a.add_argument("--at", help="Vaqt kodlari, soniya: 12.3,45 (muharrir izohi)")
    a.add_argument("--editor", help="Izoh muallifi (muharrir nomi)")
    a.add_argument("--rule", action="append", help="Takrorlanadigan izohni qoidaga aylantirish: motion.min_exit_frames=6")
    s = sub.add_parser("show", help="Eslatmalarni ko'rsatish")
    s.add_argument("--brand")
    args = ap.parse_args()
    if args.cmd == "add":
        at = [float(x) for x in args.at.split(",") if x.strip()] if args.at else None
        C.info(f"Saqlandi: {add(args.text, args.brand, args.video, at, args.editor, args.rule)}")
        if args.rule:
            C.info(f"Qoida yozildi (keyingi render shunga amal qiladi): {add_rules(args.rule, args.text, args.brand, at, args.video)}")
        return 0
    if args.brand:
        path_for(args.brand)
    if not read_notes(args.brand):
        C.info("Eslatma yo'q.")
    print_notes(args.brand, limit=200)
    return 0


if __name__ == "__main__":
    C.run_main(main)
