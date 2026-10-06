"""Belgilar (ikonkalar): 1500+ tayyor vektor belgi (Phosphor Icons, MIT).

    python scripts/icons.py find rocket            # nomi bo'yicha qidirish
    python scripts/icons.py sheet rocket star -o temp/icons.jpg   # ko'rib tanlash uchun rasm
    python scripts/icons.py png rocket -o temp/video/images/rocket.png --color "#FFE600" --size 512

Videoda ishlatish (elements.json):
    {"type": "icon", "name": "rocket", "start": 2, "end": 5, "x": 0.5, "y": 0.3, "size": 0.2, "bg": "circle"}

Uslub: fill (to'ldirilgan, standart) yoki bold (qalin chiziq).
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import common as C

ICON_DIR = C.ROOT / "assets" / "icons"
FONTS = {"fill": "Phosphor-Fill.ttf", "bold": "Phosphor-Bold.ttf"}
_index: dict = {}
_fonts: dict = {}


def index() -> dict:
    if not _index:
        path = ICON_DIR / "icons.json"
        if not path.is_file():
            raise C.MontajError(f"Belgilar ro'yxati topilmadi: {path}")
        _index.update(C.read_json(path)["icons"])
    return _index


def find(query: str, limit: int = 40) -> list:
    """Nomida so'z qatnashgan belgilar; topilmasa o'xshashlari."""
    names = sorted(index())
    q = query.lower().strip().replace(" ", "-")
    hits = [n for n in names if q in n]
    if not hits:
        hits = difflib.get_close_matches(q, names, n=limit, cutoff=0.75)
    hits.sort(key=lambda n: (not n.startswith(q), len(n), n))
    return hits[:limit]


def render(name: str, size: int, color: tuple = (255, 255, 255, 255), style: str = "fill") -> Image.Image:
    """Belgini shaffof fonli kvadrat rasm qilib chizadi (size x size)."""
    icons = index()
    if name not in icons:
        near = find(name, 8)
        raise C.MontajError(f"Bunday belgi yo'q: {name!r}." + (f" O'xshashlari: {', '.join(near)}" if near else "")
                            + "  Qidirish: python scripts/icons.py find SO'Z")
    if style not in FONTS:
        raise C.MontajError(f"Belgi uslubi noto'g'ri: {style!r}. Mumkin: fill, bold")
    key = (style, int(size))
    if key not in _fonts:
        path = ICON_DIR / FONTS[style]
        if not path.is_file():
            raise C.MontajError(f"Belgi shrifti topilmadi: {path}")
        _fonts[key] = ImageFont.truetype(str(path), int(size))
    font, glyph = _fonts[key], chr(icons[name])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box = draw.textbbox((0, 0), glyph, font=font)
    x = (size - (box[2] - box[0])) / 2 - box[0]
    y = (size - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), glyph, font=font, fill=tuple(color))
    return img


def sheet(names: list, out: Path, cell: int = 180) -> Path:
    """Belgilarni nomi bilan bitta rasmga teradi (agent ko'rib tanlashi uchun)."""
    cols = min(6, max(1, len(names)))
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rows * (cell + 34)), (24, 24, 28))
    draw = ImageDraw.Draw(img)
    try:
        label = ImageFont.truetype(str(C.ROOT / "style" / "fonts" / "Inter.ttf"), 17)
    except OSError:
        label = ImageFont.load_default()
    for n, name in enumerate(names):
        cx, cy = (n % cols) * cell, (n // cols) * (cell + 34)
        icon = render(name, cell - 60)
        img.paste(icon, (cx + 30, cy + 22), icon)
        text = name if len(name) <= 20 else name[:19] + "…"
        tw = draw.textlength(text, font=label)
        draw.text((cx + (cell - tw) / 2, cy + cell - 12), text, font=label, fill=(210, 210, 215))
    C.guard_output(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=90)
    return out


def hex_rgba(value: str) -> tuple:
    v = value.lstrip("#")
    if len(v) not in (6, 8):
        raise C.MontajError(f"Rang noto'g'ri: {value!r}. Misol: #FFE600")
    try:
        return tuple(int(v[i:i + 2], 16) for i in range(0, len(v), 2)) + ((255,) if len(v) == 6 else ())
    except ValueError:
        raise C.MontajError(f"Rang noto'g'ri: {value!r}. Misol: #FFE600") from None


def main() -> int:
    ap = argparse.ArgumentParser(description="Belgilarni qidirish va rasm qilib chiqarish.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find", help="Nomi bo'yicha qidirish (inglizcha: rocket, star, phone, chart ...)")
    f.add_argument("query")
    s = sub.add_parser("sheet", help="Bir nechta belgini bitta rasmga terib ko'rsatish")
    s.add_argument("names", nargs="+", help="Belgi nomlari yoki qidiruv so'zlari")
    s.add_argument("-o", "--output", default=str(C.TEMP_DIR / "icons.jpg"))
    p = sub.add_parser("png", help="Bitta belgini shaffof PNG qilib saqlash")
    p.add_argument("name")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--size", type=int, default=512)
    p.add_argument("--color", default="#FFFFFF")
    p.add_argument("--style", default="fill", choices=sorted(FONTS))
    args = ap.parse_args()

    if args.cmd == "find":
        hits = find(args.query)
        if not hits:
            C.info(f"'{args.query}' bo'yicha belgi topilmadi. Inglizcha so'z bilan sinab ko'ring.")
            return 0
        C.info(f"{len(hits)} ta belgi: " + ", ".join(hits))
        return 0
    if args.cmd == "sheet":
        names = []
        for q in args.names:
            names += [q] if q in index() else find(q, 12)
        names = list(dict.fromkeys(names))[:60]
        if not names:
            raise C.MontajError("Hech qanday belgi topilmadi.")
        C.info(f"RASM TAYYOR ({len(names)} belgi): {sheet(names, Path(args.output))}")
        return 0
    out = Path(args.output)
    C.guard_output(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render(args.name, args.size, hex_rgba(args.color), args.style).save(out)
    C.info(f"TAYYOR: {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
