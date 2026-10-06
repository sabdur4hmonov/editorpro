"""Bir nechta whisper modelini bitta videoda solishtiradi (qaysi biri o'zbekchani yaxshiroq yozishini ko'rish uchun).

    python scripts/compare_models.py input/video.mp4 --models small,yuldashev222/whisper-small-uz-v1-ct2
    python scripts/compare_models.py input/audio.mp3 --models small,base --seconds 60 --language uz

Nima qiladi:
  1) Faylning faqat birinchi 60 soniyasini oladi (ffmpeg bilan; asl faylga tegmaydi).
  2) Har modelni navbat bilan ishga tushiradi, ishlash vaqtini o'lchaydi.
  3) Har model uchun alohida fayl yozadi: <model>.words.json, <model>.srt, <model>.txt
  4) Yonma-yon jadval yasaydi: compare.html (brauzerda ochiladi) va compare.txt.

Jadvalda farq qiladigan so'zlar belgilanadi (birinchi modelga nisbatan). Sifatga BALL QO'YILMAYDI:
qaysi model yaxshi ekanini foydalanuvchi o'zi ko'rib (va videoni tinglab) tanlaydi.

Natija: temp/compare/<fayl nomi>/
Model kompyuterda bo'lmasa hajmi aytiladi va ruxsatsiz yuklanmaydi (ruxsat: --allow-download).
"""
from __future__ import annotations

import argparse
import gc
import html
import time
from difflib import SequenceMatcher
from pathlib import Path

import common as C
import transcribe as T

APOSTROPHES = "'`´ʻʼ‘’"


def norm(word: str) -> str:
    """Solishtirish uchun: kichik harf, tinish belgisiz, tutuq belgisi farqisiz. Yozuv (lotin/kirill) saqlanadi."""
    return "".join(ch for ch in word.lower() if ch.isalnum() and ch not in APOSTROPHES)


def cyrillic_share(words: list) -> float:
    letters = [ch for w in words for ch in w["word"] if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if "\u0400" <= ch <= "\u04ff") / len(letters)


def mark_differences(runs: list) -> None:
    """Har so'zga "diff" belgisini qo'yadi: birinchi model matni bilan mos kelmagan so'zlar.

    Birinchi modelda: kamida bitta boshqa modeldan farq qilgan so'zlar belgilanadi.
    """
    for run in runs:
        for w in run["words"]:
            w["diff"] = False
    if len(runs) < 2:
        return
    base = runs[0]["words"]
    a = [norm(w["word"]) for w in base]
    for other in runs[1:]:
        b = [norm(w["word"]) for w in other["words"]]
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            for i in range(i1, i2):
                base[i]["diff"] = True
            for j in range(j1, j2):
                other["words"][j]["diff"] = True


def build_rows(runs: list, clip_sec: float) -> list:
    """Jadval qatorlari: birinchi (so'zi bor) model bo'laklari bo'yicha vaqt oraliqlari."""
    ref = next((r for r in runs if r["words"]), None)
    if ref is None:
        return []
    cues = C.words_to_cues([{"start": w["start"], "end": w["end"], "word": w["word"]} for w in ref["words"]],
                           {"max_words_per_line": 7, "max_chars_per_line": 46, "max_cue_duration": 5.0, "gap_break": 0.8})
    edges = [0.0] + [c["start"] for c in cues[1:]] + [max(clip_sec, cues[-1]["end"]) + 1.0]
    rows = []
    for k in range(len(edges) - 1):
        lo, hi = edges[k], edges[k + 1]
        cells = []
        for run in runs:
            cells.append([w for w in run["words"] if lo <= (w["start"] + w["end"]) / 2 < hi])
        rows.append({"start": cues[k]["start"] if k < len(cues) else lo, "cells": cells})
    return rows


def write_text_table(path: Path, runs: list, rows: list, header: list) -> None:
    lines = list(header) + ["", "Belgilangan [[so'z]] = birinchi model bilan farq qiladi.", ""]
    for row in rows:
        lines.append(f"--- {C.fmt_time(row['start'])}")
        for run, cell in zip(runs, row["cells"]):
            text = " ".join(f"[[{w['word']}]]" if w["diff"] else w["word"] for w in cell) or "(bo'sh)"
            lines.append(f"  {run['label']:<12} {text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html_table(path: Path, runs: list, rows: list, title: str, summary: list) -> None:
    esc = html.escape
    out = ["<!doctype html><html lang=\"uz\"><head><meta charset=\"utf-8\">",
           f"<title>Modellarni solishtirish: {esc(title)}</title>",
           "<style>",
           "body{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#fafafa;color:#1a1a1a}",
           "h1{font-size:20px} table{border-collapse:collapse;width:100%;background:#fff}",
           "th,td{border:1px solid #d6d6d6;padding:8px 10px;vertical-align:top;text-align:left;font-size:16px;line-height:1.5}",
           "th{background:#f0f0f0;font-size:14px} td.t{white-space:nowrap;color:#666;font-size:13px;width:70px}",
           "mark{background:#ffe08a;padding:1px 3px;border-radius:3px} .empty{color:#aaa}",
           ".sum td,.sum th{font-size:14px} .note{color:#555;font-size:14px;max-width:900px}",
           "</style></head><body>",
           f"<h1>Modellarni solishtirish: {esc(title)}</h1>",
           "<p class=\"note\">Sariq bilan belgilangan so'zlar birinchi ustundagi model bilan <b>farq qiladi</b> "
           "(qaysi biri to'g'ri ekani ko'rsatilmaydi). Videoni tinglab, qaysi model to'g'ri yozganini o'zingiz "
           "tanlang. Bu jadvalda sifatga ball qo'yilmagan.</p>",
           "<table class=\"sum\"><tr><th>Model</th><th>Yuklash</th><th>Transkripsiya</th><th>Tezlik</th>"
           "<th>So'zlar</th><th>Farq qilgan so'zlar</th><th>Til</th><th>Yozuv</th></tr>"]
    for s in summary:
        out.append("<tr>" + "".join(f"<td>{esc(str(v))}</td>" for v in s) + "</tr>")
    out.append("</table><br><table><tr><th>Vaqt</th>" + "".join(f"<th>{esc(r['name'])}</th>" for r in runs) + "</tr>")
    for row in rows:
        cells = []
        for cell in row["cells"]:
            if cell:
                cells.append("<td>" + " ".join(f"<mark>{esc(w['word'])}</mark>" if w["diff"] else esc(w["word"])
                                               for w in cell) + "</td>")
            else:
                cells.append("<td class=\"empty\">(bo'sh)</td>")
        out.append(f"<tr><td class=\"t\">{esc(C.fmt_time(row['start']))}</td>" + "".join(cells) + "</tr>")
    out.append("</table></body></html>")
    path.write_text("\n".join(out), encoding="utf-8")


def compare(media: Path, models: list, style: dict, out_dir: Path, seconds: float = 60.0,
            allow_download: bool | None = None) -> dict:
    meta = C.ffprobe_info(media)
    if not meta["has_audio"]:
        raise C.MontajError(f"Faylda ovoz yo'q: {media}")
    # avval hamma modelni tekshiramiz: yuklash kerak bo'lsa ish boshlanmasdan ma'lum bo'lsin
    wcfg = dict(style["whisper"])
    need = []
    for name in models:
        st = T.model_status(name)
        if not st["cached"]:
            need.append((name, T.remote_size(st["repo"])["total"]))
    if need and allow_download is not True:
        text = "\n".join(f"  - {name}: {T.gb(size)}" for name, size in need)
        answer = C.confirm(f"Bu modellar kompyuterda yo'q:\n{text}\nYuklaymi? [y/N]: ") if allow_download is None else None
        if not answer:
            raise T.DownloadNeeded(
                "YUKLASHGA RUXSAT KERAK. Bu modellar kompyuterda yo'q, hech narsa yuklanmadi:\n" + text + "\n"
                "  Foydalanuvchi rozi bo'lsa shu buyruqni --allow-download bilan qayta ishga tushiring.")
        allow_download = True

    out_dir.mkdir(parents=True, exist_ok=True)
    wav = C.guard_output(out_dir / "clip.wav", media)
    T.extract_audio(media, wav, seconds)          # faqat birinchi N soniya; asl fayl o'qiladi, o'zgarmaydi
    clip_sec = C.ffprobe_info(wav)["duration"]
    C.info(f"Namuna: {media.name}, birinchi {clip_sec:.1f} soniya, til: {wcfg.get('language')}, "
           f"{wcfg.get('device', 'cpu')}/{wcfg.get('compute_type', 'int8')}, beam {wcfg.get('beam_size', 5)}")

    runs = []
    for n, name in enumerate(models, 1):
        C.info(f"\n[{n}/{len(models)}] Model: {name}")
        cfg = dict(wcfg, model=name)
        t0 = time.time()
        model = T.load_model(cfg, allow_download)
        load_sec = time.time() - t0
        res = T.transcribe_audio(wav, cfg, model=model)
        del model
        gc.collect()                                # keyingi model uchun xotirani bo'shatish
        slug = C.slugify(name.replace("/", "_"))
        res["source"] = str(media)
        res["clip_seconds"] = round(clip_sec, 3)
        res["load_sec"] = round(load_sec, 2)
        C.write_json(res, out_dir / f"{slug}.words.json")
        C.write_srt(C.words_to_cues(res["words"], C.cue_style(style)), out_dir / f"{slug}.srt")
        (out_dir / f"{slug}.txt").write_text(" ".join(w["word"] for w in res["words"]) + "\n", encoding="utf-8")
        issues = T.check_words(res["words"], clip_sec)
        T.print_issues(issues)
        speed = clip_sec / max(res["elapsed_sec"], 0.01)
        C.info(f"  yuklash {load_sec:.1f}s, transkripsiya {res['elapsed_sec']}s (tezlik {speed:.1f}x), "
               f"so'zlar: {len(res['words'])}")
        runs.append({"name": name, "label": f"model {n}", "slug": slug, "words": [dict(w) for w in res["words"]],
                     "load_sec": load_sec, "sec": res["elapsed_sec"], "speed": speed,
                     "language": res["language"], "issues": len(issues)})

    mark_differences(runs)
    rows = build_rows(runs, clip_sec)
    summary, header = [], [f"Modellarni solishtirish: {media.name} (birinchi {clip_sec:.1f} soniya)", ""]
    for run in runs:
        cyr = cyrillic_share(run["words"])
        script = "kirill" if cyr > 0.6 else "lotin" if cyr < 0.1 else f"aralash ({cyr:.0%} kirill)"
        diff = sum(1 for w in run["words"] if w["diff"])
        summary.append((run["name"], f"{run['load_sec']:.1f} s", f"{run['sec']} s", f"{run['speed']:.1f}x",
                        len(run["words"]), diff, run["language"], script if run["words"] else "-"))
        header.append(f"{run['label']}: {run['name']} | yuklash {run['load_sec']:.1f}s, transkripsiya {run['sec']}s "
                      f"({run['speed']:.1f}x) | so'zlar {len(run['words'])}, farq qilgani {diff} | yozuv: {script}")
    write_text_table(out_dir / "compare.txt", runs, rows, header)
    write_html_table(out_dir / "compare.html", runs, rows, f"{media.name} (birinchi {clip_sec:.0f} s)", summary)
    wav.unlink(missing_ok=True)
    C.write_json({"source": str(media), "clip_seconds": clip_sec,
                  "models": [{"name": r["name"], "files": r["slug"], "load_sec": round(r["load_sec"], 2),
                              "transcribe_sec": r["sec"], "speed_x": round(r["speed"], 2), "words": len(r["words"]),
                              "different_words": sum(1 for w in r["words"] if w["diff"]),
                              "language": r["language"], "timing_issues": r["issues"]} for r in runs]},
                 out_dir / "compare.json")
    return {"dir": out_dir, "runs": runs, "rows": rows, "header": header}


def main() -> int:
    ap = argparse.ArgumentParser(description="Whisper modellarini bitta faylda yonma-yon solishtiradi.")
    ap.add_argument("media", help="Video yoki audio fayl (haqiqiy nutq bo'lishi kerak)")
    ap.add_argument("--models", required=True,
                    help="Modellar, vergul bilan: small,yuldashev222/whisper-small-uz-v1-ct2")
    ap.add_argument("--seconds", type=float, default=60, help="Boshidan necha soniya olinsin (standart 60)")
    ap.add_argument("--language", help="Til: uz, ru, en, auto (standart: style.json dagi)")
    ap.add_argument("--beam-size", type=int, help="Qidiruv kengligi (standart: style.json dagi)")
    ap.add_argument("--out-dir", help="Natija papkasi (standart: temp/compare/<fayl nomi>/)")
    ap.add_argument("--allow-download", action="store_true",
                    help="Yo'q modellarni internetdan yuklashga ruxsat (foydalanuvchi rozi bo'lgach)")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    media = C.need_file(args.media, "Fayl")
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise C.MontajError("--models bo'sh. Misol: --models small,yuldashev222/whisper-small-uz-v1-ct2")
    if len(set(models)) != len(models):
        raise C.MontajError("--models ichida bir xil model ikki marta yozilgan.")
    if len(models) > 5:
        raise C.MontajError("Bir martada ko'pi bilan 5 ta model solishtiriladi.")
    if not 5 <= args.seconds <= 600:
        raise C.MontajError("--seconds 5 dan 600 gacha bo'lishi kerak.")
    style = C.load_style(args.style)
    if args.language:
        style["whisper"]["language"] = args.language
    if args.beam_size is not None:
        if not 1 <= args.beam_size <= 20:
            raise C.MontajError("--beam-size 1 dan 20 gacha bo'lishi kerak.")
        style["whisper"]["beam_size"] = args.beam_size
    out_dir = Path(args.out_dir) if args.out_dir else C.TEMP_DIR / "compare" / C.slugify(media.stem)
    C.guard_output(out_dir / "compare.html", media)
    try:
        res = compare(media, models, style, out_dir, args.seconds, True if args.allow_download else None)
    except T.DownloadNeeded as exc:
        C.info(f"\n{exc}")
        return T.EXIT_NEED_DOWNLOAD
    C.info("\n" + "\n".join(res["header"]))
    C.info(f"\nJADVAL TAYYOR (brauzerda oching): {res['dir'] / 'compare.html'}\n"
           f"  Matn ko'rinishi: {res['dir'] / 'compare.txt'}\n"
           "  Har model uchun alohida: <model>.words.json, .srt, .txt\n"
           "Qaysi model yaxshiroq ekanini jadvalni videoni tinglab solishtirib o'zingiz tanlang.")
    return 0


if __name__ == "__main__":
    C.run_main(main)
