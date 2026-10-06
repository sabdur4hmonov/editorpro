"""Tayyor skript matnini videodagi nutq vaqtlariga tekislaydi.

Whisper o'zbek tilida so'zlarni xato yozadi, lekin so'z QACHON aytilganini yaxshi biladi.
Skript esa to'g'ri yozilgan, lekin vaqti yo'q. Bu skript ikkalasini birlashtiradi:
matn skriptdan, vaqt whisperdan olinadi.

    python scripts/script_align.py temp/video/cut.words.json input/video.txt
    python scripts/script_align.py temp/video/cut.words.json input/video.txt -o temp/video/script.words.json

Skript fayli (oddiy .txt, UTF-8):
  - Har qator bitta gap yoki fikr bo'lsa yaxshi (subtitr shu joyda bo'linadi).
  - Belgilar ishlaydi: *katta*, **katta rangli**, !!juda katta!!, _rangli_.
  - [kvadrat qavs] ichidagi yozuv aytilmaydi, u montaj uchun eslatma:  [rasm: tog'],  [stat: 85%].
    Eslatmaning videodagi vaqti hisoblab beriladi (script.notes.json).
  - # bilan boshlangan qator izoh, o'qilmaydi.

Odatda bu skript pipeline ichidan chaqiriladi:  pipeline.py video.mp4 --script input/video.txt
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import common as C

CYR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
       "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
       "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "",
       "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h"}
WRAP = {"huge": "!!", "big_accent": "**", "big": "*", "accent": "_"}
MATCH = 0.7          # shundan yuqori o'xshashlik "bir xil so'z" hisoblanadi
GAP = -0.45          # tashlab ketilgan so'z uchun jarima


def norm(token: str) -> str:
    """Solishtirish uchun soddalashtirilgan ko'rinish: kichik harf, lotin, tinish belgisiz."""
    out = []
    for ch in token.lower():
        if ch in CYR:
            out.append(CYR[ch])
        elif ch.isalnum():
            out.append(ch)
    return "".join(out)


def read_script(text: str) -> tuple:
    """Skript matnidan so'zlar va eslatmalarni ajratadi.

    Qaytaradi: (tokens, notes). token: {"raw", "norm", "brk"}; note: {"text", "before"} (qaysi so'z oldida).
    """
    tokens, notes = [], []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            if tokens and not line:
                tokens[-1]["brk"] = True
            continue
        # eslatmalar: [rasm: tog'] -> aytilmaydi, vaqti keyingi so'zdan olinadi
        pos = 0
        parts = []
        for m in re.finditer(r"\[([^\[\]\n]{1,200})\]", line):
            parts.append(("text", line[pos:m.start()]))
            parts.append(("note", m.group(1).strip()))
            pos = m.end()
        parts.append(("text", line[pos:]))
        for kind, chunk in parts:
            if kind == "note":
                if chunk:
                    notes.append({"text": chunk, "before": len(tokens)})
                continue
            tokens.extend(_markup_words(chunk))
        if tokens:
            tokens[-1]["brk"] = True
    return tokens, notes


def _markup_words(chunk: str) -> list:
    """Belgilarni har bir so'zga alohida o'tkazadi: "**3 oyda**" -> "**3**", "**oyda**"."""
    chunk = re.sub(r"(?<!\S)_(?=\S)", "\x01", chunk)
    chunk = re.sub(r"(?<=\S)_(?=$|[\s.,!?;:])", "\x01", chunk)
    marks = {"!!": "huge", "**": "big_accent", "*": "big", "\x01": "accent"}
    out, level = [], "normal"
    for tok in re.split(r"(!!|\*\*|\*|\x01|\s+)", chunk):
        if not tok or tok.isspace():
            continue
        if tok in marks:
            level = "normal" if level == marks[tok] else marks[tok]
            continue
        key = norm(tok)
        if not key:
            # tinish belgisi yoki emoji: aytilmaydi, oldingi so'zga yopishadi
            if out:
                glue = "" if all(unicodedata.category(c).startswith("P") for c in tok) else " "
                out[-1]["tail"] = out[-1].get("tail", "") + glue + tok
            continue
        mark = WRAP.get(level, "")
        out.append({"raw": f"{mark}{tok}{mark}", "norm": key, "brk": False})
    for item in out:
        tail = item.pop("tail", "")
        if tail:
            item["raw"] += tail
    return out


def similarity(a: str, b: str, cache: dict) -> float:
    if a == b:
        return 1.0
    key = (a, b)
    if key not in cache:
        if not a or not b:
            cache[key] = 0.0
        elif abs(len(a) - len(b)) > max(len(a), len(b)) * 0.7:
            cache[key] = 0.0
        else:
            cache[key] = SequenceMatcher(None, a, b, autojunk=False).ratio()
    return cache[key]


def align_pairs(a: list, b: list) -> list:
    """Ikki so'z ro'yxatini tekislaydi (Needleman-Wunsch). Qaytaradi: [(i yoki None, j yoki None)]."""
    n, m = len(a), len(b)
    if not n or not m:
        return [(i, None) for i in range(n)] + [(None, j) for j in range(m)]
    cache: dict = {}
    # uzun matnda faqat diagonal atrofi hisoblanadi (tezlik uchun)
    band = max(40, int(max(n, m) * 0.35)) if n * m > 250_000 else None
    NEG = -1e9
    score = [[NEG] * (m + 1) for _ in range(n + 1)]
    back = [[0] * (m + 1) for _ in range(n + 1)]
    score[0][0] = 0.0
    for j in range(1, m + 1):
        score[0][j], back[0][j] = j * GAP, 2
    for i in range(1, n + 1):
        score[i][0], back[i][0] = i * GAP, 1
        centre = int(i * m / n)
        lo, hi = (1, m) if band is None else (max(1, centre - band), min(m, centre + band))
        row, prev = score[i], score[i - 1]
        ai = a[i - 1]
        for j in range(lo, hi + 1):
            s = similarity(ai, b[j - 1], cache)
            best, move = prev[j - 1] + (2.0 * s - 1.0 if s >= 0.34 else -1.0), 0
            up = prev[j] + GAP
            if up > best:
                best, move = up, 1
            left = row[j - 1] + GAP
            if left > best:
                best, move = left, 2
            row[j], back[i][j] = best, move
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        move = back[i][j] if (i > 0 and j > 0) else (1 if i > 0 else 2)
        if move == 0 and score[i][j] <= NEG / 2:      # band tashqarisi: xavfsiz yo'l
            move = 1 if i > 0 else 2
        if move == 0:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif move == 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    pairs.reverse()
    return pairs


def _spread(idxs: list, tokens: list, start: float, end: float) -> list:
    """So'zlarni [start, end] oralig'iga harf soniga qarab taqsimlaydi. Qaytaradi: [(indeks, boshi, oxiri)]."""
    total = sum(max(1, len(tokens[i]["norm"])) for i in idxs)
    out, pos = [], start
    for i in idxs:
        dur = (end - start) * max(1, len(tokens[i]["norm"])) / total
        out.append((i, pos, pos + dur))
        pos += dur
    return out


def align(words: list, script_text: str) -> dict:
    """Asosiy ish. words: whisper so'zlari [{word, start, end, prob}]. Qaytaradi: {words, notes, report}."""
    tokens, notes = read_script(script_text)
    if not tokens:
        raise C.MontajError("Skript fayli bo'sh (yoki ichida faqat izoh va eslatmalar bor).")
    heard = [dict(w, norm=norm(str(w.get("word", "")))) for w in words]
    heard = [w for w in heard if w["norm"]]
    if not heard:
        raise C.MontajError("Videoda nutq topilmadi: skriptni tekislab bo'lmaydi.")

    pairs = align_pairs([t["norm"] for t in tokens], [w["norm"] for w in heard])
    cache: dict = {}
    # langarlar: bir-biriga aniq mos kelgan so'zlar
    anchors = [(i, j) for i, j in pairs
               if i is not None and j is not None and similarity(tokens[i]["norm"], heard[j]["norm"], cache) >= MATCH]
    anchor_i = {i for i, _ in anchors}
    coverage = len(anchors) / len(tokens)
    if coverage < 0.35:
        raise C.MontajError(
            f"Skript bu videoga mos kelmayapti: {len(tokens)} so'zdan faqat {len(anchors)} tasi nutqda topildi "
            f"({coverage:.0%}). To'g'ri skript fayli berilganini tekshiring.")

    out, problems = [], {"changed": [], "extra": [], "missing": []}
    timed: dict = {}                       # token indeksi -> (start, end, ishonch)
    bounds = [(-1, -1)] + anchors + [(len(tokens), len(heard))]
    for (i0, j0), (i1, j1) in zip(bounds, bounds[1:]):
        if 0 <= i1 < len(tokens):
            w = heard[j1]
            timed[i1] = (float(w["start"]), float(w["end"]), 1.0)
        run = list(range(i0 + 1, i1))                      # langarlar orasidagi skript so'zlari
        loose = heard[j0 + 1:j1]                           # ular orasidagi eshitilgan so'zlar
        if not run and not loose:
            continue
        if run and loose:
            said = " ".join(str(w["word"]).strip() for w in loose)
            want = " ".join(C.strip_markup(tokens[i]["raw"]) for i in run)
            close = SequenceMatcher(None, norm(said), norm(want), autojunk=False).ratio()
            span = float(loose[-1]["end"]) - float(loose[0]["start"])
            if len(run) >= 3 and len(loose) >= 2 and close < 0.35:
                # butunlay boshqa gap aytilgan: skriptdagisi qo'yilmaydi, eshitilgani (whisper matni) qoladi
                for w in loose:
                    out.append({"word": str(w["word"]).strip(), "start": float(w["start"]), "end": float(w["end"]),
                                "prob": min(0.3, float(w.get("prob", 0.3))), "extra": True})
                problems["extra"].append({"at": round(float(loose[0]["start"]), 2), "heard": said})
                problems["missing"].append({"at": round(float(loose[0]["start"]), 2), "script": want})
                continue
            # so'z boshqacha eshitilgan: matn skriptdan, vaqt eshitilgan so'zlardan
            for i, s, e in _spread(run, tokens, float(loose[0]["start"]), max(float(loose[-1]["end"]),
                                                                              float(loose[0]["start"]) + 0.05)):
                timed[i] = (s, e, 0.45)
            if norm(said) != norm(want):
                problems["changed"].append({"at": round(float(loose[0]["start"]), 2), "script": want, "heard": said})
        elif run:
            # eshitilgan so'z yo'q: yo qo'shni so'z bilan yopishib eshitilgan, yo aytilmagan
            prev_end = float(heard[j0]["end"]) if j0 >= 0 else 0.0
            next_start = float(heard[j1]["start"]) if j1 < len(heard) else prev_end
            room = next_start - prev_end
            need = sum(max(1, len(tokens[i]["norm"])) for i in run) * 0.045
            if room >= need and j0 >= 0 and j1 < len(heard):
                for i, s, e in _spread(run, tokens, prev_end, next_start):
                    timed[i] = (s, e, 0.3)
            elif len(run) <= 2 and (0 <= i1 < len(tokens) or i0 >= 0):
                # qo'shni langarning vaqtini bo'lishadi ("ilm markazi" <-> "ilmmarkazi")
                host = i1 if 0 <= i1 < len(tokens) else i0
                group = run + [host] if host == i1 else [host] + run
                hs, he, _ = timed[host]
                for i, s, e in _spread(group, tokens, hs, he):
                    timed[i] = (s, e, 0.4)
            else:
                problems["missing"].append({"at": round(prev_end, 2),
                                            "script": " ".join(C.strip_markup(tokens[i]["raw"]) for i in run)})
        elif len(loose) >= 2 and float(loose[-1]["end"]) - float(loose[0]["start"]) >= 0.5:
            # skriptda yo'q, lekin aytilgan: yo'qotmaymiz, whisper matni bilan qoladi
            for w in loose:
                out.append({"word": str(w["word"]).strip(), "start": float(w["start"]), "end": float(w["end"]),
                            "prob": min(0.3, float(w.get("prob", 0.3))), "extra": True})
            problems["extra"].append({"at": round(float(loose[0]["start"]), 2),
                                      "heard": " ".join(str(w["word"]).strip() for w in loose)})

    for i, tok in enumerate(tokens):
        if i in timed:
            s, e, conf = timed[i]
            out.append({"word": tok["raw"], "start": s, "end": e, "prob": conf, "brk": bool(tok["brk"])})
    out.sort(key=lambda w: (w["start"], w["end"]))
    # vaqtlar ustma-ust tushmasin
    for k in range(1, len(out)):
        if out[k]["start"] < out[k - 1]["end"]:
            mid = max(out[k - 1]["start"] + 0.02, min(out[k]["start"], out[k - 1]["end"]))
            out[k - 1]["end"] = mid
            out[k]["start"] = mid
        out[k]["end"] = max(out[k]["end"], out[k]["start"] + 0.02)
    for w in out:
        w["start"], w["end"] = round(w["start"], 3), round(w["end"], 3)

    # eslatmalar vaqti: keyingi so'z boshlanishi
    marks = []
    for note in notes:
        at = None
        for i in range(note["before"], len(tokens)):
            if i in timed:
                at = timed[i][0]
                break
        if at is None:
            at = out[-1]["end"] if out else 0.0
        marks.append({"at": round(at, 2), "note": note["text"]})

    return {"words": out, "notes": marks, "report": {
        "script_words": len(tokens), "heard_words": len(heard), "matched": len(anchors),
        "coverage": round(coverage, 3), **problems}}


def print_report(res: dict) -> None:
    rep = res["report"]
    C.info(f"  Skript: {rep['script_words']} so'z, nutqda: {rep['heard_words']} so'z, "
           f"aniq mos keldi: {rep['matched']} ({rep['coverage']:.0%})")
    for item in rep["changed"][:25]:
        C.info(f"    {C.fmt_time(item['at'])}  skriptda: \"{item['script']}\"  |  eshitildi: \"{item['heard']}\"")
    if len(rep["changed"]) > 25:
        C.info(f"    ... yana {len(rep['changed']) - 25} ta farq")
    for item in rep["extra"]:
        C.warn(f"{C.fmt_time(item['at'])} da skriptda YO'Q gap aytilgan (whisper matni qoldirildi, tekshiring): "
               f"\"{item['heard']}\"")
    for item in rep["missing"]:
        C.warn(f"{C.fmt_time(item['at'])} atrofida skriptdagi gap nutqda TOPILMADI (subtitrga qo'yilmadi): "
               f"\"{item['script']}\"")
    for mark in res["notes"]:
        C.info(f"    eslatma {C.fmt_time(mark['at'])}: [{mark['note']}]")


def read_script_file(path: str | Path) -> str:
    p = C.need_file(path, "Skript fayli")
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    raise C.MontajError(f"Skript faylini o'qib bo'lmadi (UTF-8 qilib saqlang): {p}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Tayyor skript matnini whisper vaqtlariga tekislaydi.")
    ap.add_argument("words", help="Whisper so'zlari (temp/<nom>/cut.words.json yoki orig.words.json)")
    ap.add_argument("script", help="Skript matni (.txt)")
    ap.add_argument("-o", "--output", help="Natija (standart: so'zlar fayli yonida script.words.json)")
    args = ap.parse_args()
    words_path = C.need_file(args.words, "So'zlar fayli")
    res = align(C.read_json(words_path).get("words", []), read_script_file(args.script))
    out = Path(args.output) if args.output else words_path.with_name("script.words.json")
    C.guard_output(out)
    C.write_json(res, out)
    print_report(res)
    C.info(f"\nTAYYOR: {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
