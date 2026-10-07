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


def add(text: str, brand: str | None = None, video: str | None = None) -> Path:
    text = " ".join(str(text).split())
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
    s = sub.add_parser("show", help="Eslatmalarni ko'rsatish")
    s.add_argument("--brand")
    args = ap.parse_args()
    if args.cmd == "add":
        C.info(f"Saqlandi: {add(args.text, args.brand, args.video)}")
        return 0
    if args.brand:
        path_for(args.brand)
    if not read_notes(args.brand):
        C.info("Eslatma yo'q.")
    print_notes(args.brand, limit=200)
    return 0


if __name__ == "__main__":
    C.run_main(main)
