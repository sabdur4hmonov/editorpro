"""Transkripsiya matnini tuzatadi, vaqtlarga tegmaydi.

    # 1) So'zlarni raqami bilan ko'rish (tuzatishlar faylini yozish uchun)
    python scripts/apply_corrections.py temp/video/orig.words.json --list

    # 2) Tuzatishlarni qo'llash
    python scripts/apply_corrections.py temp/video/orig.words.json temp/video/corrections.json

Natija (asl fayl yonida): orig.words.fixed.json, orig.fixed.srt va orig.fixed.txt (o'qish uchun oddiy matn)
ASL words.json HECH QACHON qayta yozilmaydi.

Eslatma: pipeline.py hozircha words.fixed.json ni o'zi o'qimaydi (u o'z transkripsiyasini ishlatadi).
Bu skript faqat tuzatilgan matnni tayyorlaydi; uni montajga ulash alohida ish.

Tuzatishlar fayli (corrections.json). "index" - so'z raqami (--list dagi kabi, 1 dan boshlanadi):

    {"corrections": [
      {"index": 5,  "was": "kitop",      "text": "kitob"},
      {"index": 9,  "was": "ilmmarkazi", "text": "ilm markazi"},
      {"index": 14, "count": 2, "was": "hech kim", "text": "hechkim"},
      {"index": 20, "was": "shunaqa", "needs_review": true, "note": "ma'nosi aniq emas"},
      {"index": 23, "was": "eee", "text": ""}
    ]}

  text          - yangi matn. Bo'sh ("") bo'lsa so'z olib tashlanadi. Berilmasa matn o'zgarmaydi.
  count         - nechta ketma-ket so'z almashtiriladi (standart 1).
  was           - hozirgi matn (xato raqam yozib qo'ymaslik uchun tekshiriladi). Tavsiya etiladi.
  needs_review  - "foydalanuvchi tekshirsin" belgisi; note - sababi.

Vaqt qoidasi:
  - So'z soni o'zgarmasa (1 ta -> 1 ta, 2 ta -> 2 ta): start va end AYNAN o'sha qoladi.
  - So'z bo'linsa (1 -> 2) yoki birlashsa (2 -> 1): eski so'zlarning umumiy oralig'i (birinchisining
    start'i ... oxirgisining end'i) yangi so'zlarga TENG bo'linadi va shu joy needs_review bo'ladi.
  - Boshqa hech bir so'zning vaqti o'zgarmaydi. Oxirida bu tekshirib isbotlanadi.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import common as C

SPLIT_NOTE = "so'z soni o'zgardi: vaqt teng bo'lingan"


def load_words(path: Path) -> dict:
    data = C.read_json(path, "So'zlar fayli")
    if not isinstance(data, dict) or not isinstance(data.get("words"), list):
        raise C.MontajError(f"{path} transkripsiya fayli emas (ichida \"words\" ro'yxati yo'q).")
    for i, w in enumerate(data["words"], 1):
        if not isinstance(w, dict) or "start" not in w or "end" not in w or "word" not in w:
            raise C.MontajError(f"{path}: {i}-so'zda start, end yoki word yo'q.")
    return data


def print_list(words: list) -> None:
    C.info(f"{len(words)} ta so'z (raqam, vaqt, so'z, whisper ishonchi):")
    for i, w in enumerate(words, 1):
        prob = w.get("prob")
        mark = "  ?" if isinstance(prob, (int, float)) and prob < 0.5 else ""
        C.info(f"  {i:>4}  {C.fmt_time(float(w['start']))}  {w['word']}"
               + (f"  ({prob})" if prob is not None else "") + mark)


def read_corrections(path: Path, total: int) -> list:
    data = C.read_json(path, "Tuzatishlar fayli")
    items = data.get("corrections") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise C.MontajError(f"{path}: \"corrections\" ro'yxati kerak.")
    out, used = [], {}
    for n, it in enumerate(items, 1):
        where = f"{path.name}: {n}-tuzatish"
        if not isinstance(it, dict):
            raise C.MontajError(f"{where} obyekt emas.")
        if "start" in it or "end" in it:
            raise C.MontajError(f"{where}: vaqtni (start/end) bu fayl orqali o'zgartirib bo'lmaydi.")
        unknown = set(it) - {"index", "count", "text", "was", "needs_review", "note"}
        if unknown:
            raise C.MontajError(f"{where}: noma'lum maydon: {', '.join(sorted(unknown))}. "
                                "Mumkin: index, count, text, was, needs_review, note.")
        index, count = it.get("index"), it.get("count", 1)
        for key, val in (("index", index), ("count", count)):
            if isinstance(val, bool) or not isinstance(val, int) or val < 1:
                raise C.MontajError(f"{where}: \"{key}\" 1 yoki undan katta butun son bo'lishi kerak.")
        if index + count - 1 > total:
            raise C.MontajError(f"{where}: so'z raqami chegaradan tashqarida ({index}"
                                + (f"..{index + count - 1}" if count > 1 else "") + f"; jami {total} ta so'z).")
        text = it.get("text")
        if text is not None and not isinstance(text, str):
            raise C.MontajError(f"{where}: \"text\" matn bo'lishi kerak.")
        review = it.get("needs_review", False)
        if not isinstance(review, bool):
            raise C.MontajError(f"{where}: \"needs_review\" true yoki false bo'lishi kerak.")
        if text is None and not review:
            raise C.MontajError(f"{where}: \"text\" ham, \"needs_review\" ham yo'q: bu tuzatish hech narsa qilmaydi.")
        for k in range(index, index + count):
            if k in used:
                raise C.MontajError(f"{where}: {k}-so'z allaqachon {used[k]}-tuzatishda ishlatilgan.")
            used[k] = n
        out.append({"n": n, "index": index, "count": count, "text": text, "was": it.get("was"),
                    "needs_review": review, "note": str(it.get("note", "")).strip()})
    return sorted(out, key=lambda c: c["index"])


def _same(a: str, b: str) -> bool:
    """"was" tekshiruvi: bosh-oxiridagi bo'shliq va tutuq belgisi turi farq qilmaydi."""
    def clean(s):
        s = " ".join(str(s).split())
        for ch in "`´ʻʼ‘’":
            s = s.replace(ch, "'")
        return s
    return clean(a) == clean(b)


def apply(words: list, corrections: list) -> tuple:
    """Tuzatishlarni qo'llaydi. Qaytaradi: (yangi so'zlar, hisobot). Kirish ro'yxati o'zgarmaydi."""
    by_index = {c["index"]: c for c in corrections}
    out, i = [], 1
    report = {"changed": 0, "resplit": [], "deleted": [], "review": [], "untouched": 0}
    while i <= len(words):
        c = by_index.get(i)
        if c is None:
            out.append(dict(words[i - 1]))
            report["untouched"] += 1
            i += 1
            continue
        group = words[i - 1:i - 1 + c["count"]]
        old_text = " ".join(str(w["word"]) for w in group)
        if c["was"] is not None and not _same(c["was"], old_text):
            raise C.MontajError(
                f"{c['n']}-tuzatish: {i}-so'z kutilganidek emas. \"was\": \"{c['was']}\", faylda esa: \"{old_text}\".\n"
                "So'z raqami noto'g'ri bo'lishi mumkin: --list bilan qayta tekshiring.")
        start, end = float(group[0]["start"]), float(group[-1]["end"])
        if c["text"] is None:                        # faqat belgi: matn ham, vaqt ham o'zgarmaydi
            for w in group:
                item = dict(w, needs_review=True)
                if c["note"]:
                    item["note"] = c["note"]
                out.append(item)
            report["review"].append({"index": i, "text": old_text, "note": c["note"] or "tekshirilsin"})
            i += c["count"]
            continue
        new = c["text"].split()
        if not new:                                  # so'z(lar) olib tashlanadi
            report["deleted"].append({"index": i, "text": old_text, "start": start, "end": end})
            i += c["count"]
            continue
        if len(new) == len(group):                   # birma-bir: vaqtlar aynan o'sha
            for w, text in zip(group, new):
                item = dict(w)
                if text != str(w["word"]):
                    item["orig"] = str(w["word"])
                    item["word"] = text
                    report["changed"] += 1
                if c["needs_review"]:
                    item["needs_review"] = True
                    if c["note"]:
                        item["note"] = c["note"]
                out.append(item)
            if c["needs_review"]:
                report["review"].append({"index": i, "text": c["text"], "note": c["note"] or "tekshirilsin"})
        else:                                        # bo'lish yoki birlashtirish: oraliq teng bo'linadi
            step = (end - start) / len(new)
            probs = [w.get("prob") for w in group if isinstance(w.get("prob"), (int, float))]
            for k, text in enumerate(new):
                item = {"start": group[0]["start"] if k == 0 else round(start + step * k, 3),
                        "end": group[-1]["end"] if k == len(new) - 1 else round(start + step * (k + 1), 3),
                        "word": text, "orig": old_text, "needs_review": True,
                        "note": (c["note"] + "; " if c["note"] else "") + SPLIT_NOTE}
                if probs:
                    item["prob"] = round(min(probs), 3)
                out.append(item)
            report["changed"] += len(new)
            report["resplit"].append({"index": i, "from": old_text, "to": c["text"], "start": start, "end": end})
            report["review"].append({"index": i, "text": c["text"], "note": SPLIT_NOTE})
        i += c["count"]
    return out, report


def verify(original: list, fixed: list, corrections: list) -> dict:
    """Vaqtlar buzilmaganini isbotlaydi. Buzilgan bo'lsa xato beradi (natija yozilmaydi)."""
    by_index = {c["index"]: c for c in corrections}
    same, regrouped, i, j = 0, 0, 1, 0
    while i <= len(original):
        c = by_index.get(i)
        count = c["count"] if c else 1
        group = original[i - 1:i - 1 + count]
        new_n = count if (c is None or c["text"] is None) else len(c["text"].split())
        chunk = fixed[j:j + new_n]
        if new_n == count:
            for a, b in zip(group, chunk):
                if (a["start"], a["end"]) != (b["start"], b["end"]):
                    raise C.MontajError(f"ICHKI XATO: {i}-so'z vaqti o'zgarib qoldi "
                                        f"({a['start']}-{a['end']} -> {b['start']}-{b['end']}). Natija yozilmadi.")
                same += 1
        elif new_n:
            lo, hi = float(group[0]["start"]), float(group[-1]["end"])
            if float(chunk[0]["start"]) != lo or float(chunk[-1]["end"]) != hi:
                raise C.MontajError(f"ICHKI XATO: {i}-so'zdagi oraliq chegarasi o'zgarib qoldi. Natija yozilmadi.")
            edges = [float(chunk[0]["start"])] + [float(w["end"]) for w in chunk]
            if any(b < a for a, b in zip(edges, edges[1:])) or any(
                    float(a["end"]) != float(b["start"]) for a, b in zip(chunk, chunk[1:])):
                raise C.MontajError(f"ICHKI XATO: {i}-so'zdagi bo'lingan vaqtlar tartibsiz. Natija yozilmadi.")
            regrouped += 1
        i += count
        j += new_n
    if j != len(fixed):
        raise C.MontajError("ICHKI XATO: natijadagi so'zlar soni hisobga to'g'ri kelmadi. Natija yozilmadi.")
    return {"same_timing": same, "regrouped": regrouped}


def fixed_paths(words_path: Path, output: str | None) -> tuple:
    if output:
        json_path = Path(output)
    else:
        name = words_path.name
        base = name[:-len(".words.json")] if name.endswith(".words.json") else words_path.stem
        json_path = words_path.with_name(f"{base}.words.fixed.json")
    if json_path.resolve() == words_path.resolve():
        raise C.MontajError("Natija asl fayl ustiga yozilmaydi: boshqa nom bering (-o).")
    name = json_path.name
    srt_base = name[:-len(".words.fixed.json")] if name.endswith(".words.fixed.json") else json_path.stem
    srt_path = json_path.with_name(f"{srt_base}.fixed.srt")
    txt_path = json_path.with_name(f"{srt_base}.fixed.txt")
    return C.guard_output(json_path), C.guard_output(srt_path), C.guard_output(txt_path)


def run(words_path: Path, corr_path: Path, output: str | None = None, style: dict | None = None) -> dict:
    words_path = C.need_file(words_path, "So'zlar fayli")
    corr_path = C.need_file(corr_path, "Tuzatishlar fayli")
    before = words_path.read_bytes()
    data = load_words(words_path)
    corrections = read_corrections(corr_path, len(data["words"]))
    fixed, report = apply(data["words"], corrections)
    proof = verify(data["words"], fixed, corrections)
    json_path, srt_path, txt_path = fixed_paths(words_path, output)
    style = style or C.load_style()
    out = dict(data)
    out["words"] = fixed
    out["corrected_from"] = str(words_path)
    out["corrections_file"] = str(corr_path)
    out["needs_review"] = report["review"]
    C.write_json(out, json_path)
    cues = C.words_to_cues(fixed, C.cue_style(style))
    C.write_srt(cues, srt_path)
    # oddiy matn (har bo'lak alohida qatorda): foydalanuvchiga ko'rsatish uchun
    txt_path.write_text("\n".join(c["text"] for c in cues) + "\n", encoding="utf-8")
    if words_path.read_bytes() != before:
        raise C.MontajError("ICHKI XATO: asl so'zlar fayli o'zgarib qoldi.")
    return {"json": json_path, "srt": srt_path, "txt": txt_path, "report": report, "proof": proof,
            "words": fixed, "total_before": len(data["words"])}


def main() -> int:
    ap = argparse.ArgumentParser(description="Transkripsiya matnini tuzatadi (vaqtlarga tegmaydi).")
    ap.add_argument("words", help="Transkripsiya natijasi (masalan temp/video/orig.words.json)")
    ap.add_argument("corrections", nargs="?", help="Tuzatishlar fayli (corrections.json)")
    ap.add_argument("-o", "--output", help="Natija JSON (standart: <nom>.words.fixed.json, asl fayl yonida)")
    ap.add_argument("--list", action="store_true", help="So'zlarni raqami bilan ko'rsat va chiq")
    ap.add_argument("--style", help="Boshqa style.json fayli (SRT bo'laklari uchun)")
    args = ap.parse_args()

    words_path = C.need_file(args.words, "So'zlar fayli")
    if args.list:
        print_list(load_words(words_path)["words"])
        return 0
    if not args.corrections:
        ap.error("tuzatishlar fayli kerak (yoki --list)")
    res = run(words_path, Path(args.corrections), args.output, C.load_style(args.style))
    rep, proof = res["report"], res["proof"]
    C.info(f"Tuzatildi: {rep['changed']} ta so'z matni o'zgardi, {len(rep['deleted'])} ta olib tashlandi "
           f"({res['total_before']} -> {len(res['words'])} so'z).")
    C.info(f"Vaqt tekshiruvi: {proof['same_timing']} ta so'zning start/end vaqti asl fayl bilan AYNAN bir xil; "
           f"{proof['regrouped']} ta joyda so'z soni o'zgargani uchun oraliq teng bo'lindi (chegaralari o'sha).")
    for it in rep["resplit"]:
        C.info(f"    #{it['index']} {C.fmt_time(it['start'])}-{C.fmt_time(it['end'])}: "
               f"\"{it['from']}\" -> \"{it['to']}\"")
    for it in rep["deleted"]:
        C.info(f"    #{it['index']} {C.fmt_time(it['start'])}: \"{it['text']}\" olib tashlandi")
    if rep["review"]:
        C.info(f"\nFOYDALANUVCHI TEKSHIRSIN ({len(rep['review'])} ta joy, needs_review):")
        for it in rep["review"]:
            C.info(f"    #{it['index']} \"{it['text']}\": {it['note']}")
    C.info(f"\n  JSON: {res['json']}\n  SRT:  {res['srt']}\n  Matn: {res['txt']}\n  Asl fayl o'zgarmadi: {words_path}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
