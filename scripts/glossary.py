"""Lug'at: whisper doim xato yozadigan so'zlarni avtomatik to'g'rilaydi (brend nomi, ismlar, atamalar).

    python scripts/glossary.py add "milyon" "Million" --brand million    # brend lug'atiga
    python scripts/glossary.py add "instagram" "Instagram"               # umumiy lug'atga (hamma videoga)
    python scripts/glossary.py list --brand million
    python scripts/glossary.py remove "milyon" --brand million

Fayllar:
    style/glossary.json           - umumiy (brendsiz videolarga ham qo'llanadi)
    brands/<nom>/glossary.json    - shu brend uchun (umumiydan ustun turadi)

Format: {"replace": [{"from": "milyon", "to": "Million"}, {"from": "ilm markazi", "to": "Ilm Markazi"}]}

pipeline.py har transkripsiyadan keyin lug'atni o'zi qo'llaydi (o'chirish: --no-glossary).
Solishtirishda katta-kichik harf, tinish belgisi va tutuq belgisi turi farq qilmaydi. So'z oxiridagi
tinish belgisi saqlanadi. So'z VAQTLARI o'zgarmaydi (so'z soni o'zgarsa oraliq teng bo'linadi).
Lug'at faqat aniq yozilgan so'zni almashtiradi: qo'shimcha qo'shilgan shakllar (milyonni) alohida yoziladi.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import common as C

APOSTROPHES = "'`´ʻʼ‘’"
GENERAL = C.ROOT / "style" / "glossary.json"


def norm(word: str) -> str:
    return "".join(ch for ch in str(word).lower() if ch.isalnum() and ch not in APOSTROPHES)


def path_for(brand: str | None) -> Path:
    if not brand:
        return GENERAL
    folder = C.BRANDS_DIR / brand
    if not folder.is_dir():
        raise C.MontajError(f"Brend topilmadi: {brand!r}. Mavjudlari: {', '.join(C.list_brands()) or 'hali yoq'}")
    return folder / "glossary.json"


def read_file(path: Path) -> list:
    if not path.is_file():
        return []
    data = C.read_json(path, "Lug'at")
    items = data.get("replace", []) if isinstance(data, dict) else data
    out = []
    for n, it in enumerate(items if isinstance(items, list) else [], 1):
        if not isinstance(it, dict) or not str(it.get("from", "")).strip() or "to" not in it:
            raise C.MontajError(f"{path}: {n}-yozuv noto'g'ri. Kerak: {{\"from\": \"xato\", \"to\": \"to'g'ri\"}}")
        key = [norm(w) for w in str(it["from"]).split()]
        if not all(key) or not str(it["to"]).strip():
            raise C.MontajError(f"{path}: {n}-yozuvda \"from\" yoki \"to\" bo'sh.")
        out.append({"from": str(it["from"]).strip(), "to": str(it["to"]).strip(), "key": tuple(key)})
    return out


def load(style: dict | None = None, brand: str | None = None) -> list:
    """Umumiy + brend lug'ati (brenddagisi ustun). Uzun iboralar oldin tekshiriladi."""
    brand = brand if brand is not None else (style or {}).get("_brand") or None
    merged = {e["key"]: e for e in read_file(GENERAL)}
    if brand:
        merged.update({e["key"]: e for e in read_file(C.BRANDS_DIR / brand / "glossary.json")})
    return sorted(merged.values(), key=lambda e: -len(e["key"]))


def _edges(word: str) -> tuple:
    """So'z boshidagi va oxiridagi tinish belgilari (saqlab qolish uchun)."""
    i, j = 0, len(word)
    while i < j and not (word[i].isalnum() or word[i] in APOSTROPHES):
        i += 1
    while j > i and not (word[j - 1].isalnum() or word[j - 1] in APOSTROPHES):
        j -= 1
    return word[:i], word[j:]


def corrections_for(words: list, entries: list) -> list:
    """Lug'at bo'yicha tuzatishlar ro'yxati (apply_corrections formatida)."""
    if not entries:
        return []
    keys = [norm(w.get("word", "")) for w in words]
    out, i = [], 0
    while i < len(words):
        hit = None
        for e in entries:
            n = len(e["key"])
            if tuple(keys[i:i + n]) == e["key"]:
                hit = e
                break
        if hit is None:
            i += 1
            continue
        n = len(hit["key"])
        old = " ".join(str(w["word"]) for w in words[i:i + n])
        lead, _ = _edges(str(words[i]["word"]))
        _, trail = _edges(str(words[i + n - 1]["word"]))
        new = lead + hit["to"] + trail
        if new != old:
            out.append({"n": len(out) + 1, "index": i + 1, "count": n, "text": new, "was": old,
                        "needs_review": False, "note": "lug'at"})
        i += n
    return out


def apply_to_words(words: list, entries: list) -> tuple:
    """So'zlarga lug'atni qo'llaydi. Qaytaradi: (yangi so'zlar, [(vaqt, eski, yangi)])."""
    import apply_corrections as AC
    corr = corrections_for(words, entries)
    if not corr:
        return words, []
    fixed, _ = AC.apply(words, corr)
    AC.verify(words, fixed, corr)
    return fixed, [(float(words[c["index"] - 1]["start"]), c["was"], c["text"]) for c in corr]


def main() -> int:
    ap = argparse.ArgumentParser(description="Lug'at: doim xato yoziladigan so'zlarni avtomatik to'g'rilash.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="Yozuv qo'shish yoki yangilash")
    a.add_argument("wrong", help="Whisper yozadigan (xato) shakl")
    a.add_argument("right", help="To'g'ri yozilishi")
    a.add_argument("--brand", help="Brend nomi (berilmasa umumiy lug'at)")
    r = sub.add_parser("remove", help="Yozuvni o'chirish")
    r.add_argument("wrong")
    r.add_argument("--brand")
    l = sub.add_parser("list", help="Lug'atni ko'rsatish")
    l.add_argument("--brand")
    args = ap.parse_args()

    path = path_for(args.brand)
    if args.cmd == "list":
        entries = load(brand=args.brand)
        if not entries:
            C.info("Lug'at bo'sh.")
        for e in entries:
            C.info(f"  {e['from']}  ->  {e['to']}")
        return 0
    items = [{"from": e["from"], "to": e["to"]} for e in read_file(path)]
    key = tuple(norm(w) for w in args.wrong.split())
    if not key or not all(key):
        raise C.MontajError("Xato shakl bo'sh.")
    rest = [it for it in items if tuple(norm(w) for w in it["from"].split()) != key]
    if args.cmd == "add":
        if not args.right.strip():
            raise C.MontajError("To'g'ri shakl bo'sh.")
        rest.append({"from": args.wrong.strip(), "to": args.right.strip()})
        C.info(f"Qo'shildi ({'brend: ' + args.brand if args.brand else 'umumiy'}): {args.wrong} -> {args.right}")
    elif len(rest) == len(items):
        raise C.MontajError(f"Lug'atda bunday yozuv yo'q: {args.wrong}")
    else:
        C.info(f"O'chirildi: {args.wrong}")
    C.write_json({"_izoh": "Whisper doim xato yozadigan so'zlar: from (xato) -> to (to'g'ri). "
                           "Boshqarish: python scripts/glossary.py add|remove|list",
                  "replace": sorted(rest, key=lambda x: x["from"].lower())}, path)
    return 0


if __name__ == "__main__":
    C.run_main(main)
