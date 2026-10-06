"""Transkripsiya qismining sinovi: transcribe.py (eski va yangi parametrlar), vaqt tekshiruvi,
apply_corrections.py. selftest.py shu faylni chaqiradi; alohida ham ishlaydi:

    python scripts/test_transcribe.py              # to'liq (whisper bilan)
    python scripts/test_transcribe.py --no-whisper # whisper'siz qismlar

Hech narsa yuklamaydi. Modellarni haqiqiy nutqda solishtirish bu yerda sinalmaydi (o'zbekcha
nutqli video kerak): buning uchun scripts/compare_models.py ni o'z videongizda ishga tushiring.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import common as C

SCRIPTS = Path(__file__).resolve().parent
UZ_MODEL = "yuldashev222/whisper-small-uz-v1-ct2"       # faqat "ruxsatsiz yuklanmaydi" sinovi uchun
OLD_KEYS = {"language", "language_probability", "duration", "model", "elapsed_sec", "segments", "words", "source"}


def _run(name: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], cwd=str(C.ROOT),
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _tail(proc, n: int = 6) -> str:
    return " | ".join(l.strip() for l in (proc.stdout + proc.stderr).strip().splitlines()[-n:])


def run(check, video: Path, work: Path, no_whisper: bool = False) -> None:
    """check(nom, ok, tafsilot) - selftest.py dagi funksiya."""
    import apply_corrections as AC
    import transcribe as T

    # ---- vaqt tekshiruvi (sof mantiq)
    good = [{"start": 0.2, "end": 0.6, "word": "a"}, {"start": 0.7, "end": 0.7, "word": "b"}]
    bad = [{"start": 1.0, "end": 0.8, "word": "a"}, {"start": 0.5, "end": 0.9, "word": "b"},
           {"start": 9.0, "end": 12.0, "word": "c"}]
    problems = T.check_words(bad, 10.0)
    check("so'z vaqtlari tekshiruvi (tartib, end >= start, davomiylik)",
          T.check_words(good, 10.0) == [] and len(problems) == 3
          and [p["index"] for p in problems] == [1, 2, 3], f"buzuq namunada {len(problems)} ta muammo topildi")

    # ---- apply_corrections: vaqtlar o'zgarmasligi
    fix = work / "fix"
    fix.mkdir(parents=True, exist_ok=True)
    words = [{"start": round(0.2 + i * 0.5, 3), "end": round(0.58 + i * 0.5, 3), "word": w, "prob": 0.9}
             for i, w in enumerate("bugun men sizga kitop haqida ilmmarkazi da hech kim bilmagan eee shunaqa narsa".split())]
    src = fix / "orig.words.json"
    C.write_json({"language": "uz", "duration": 8.0, "model": "test", "segments": [], "words": words}, src)
    C.write_json({"corrections": [
        {"index": 4, "was": "kitop", "text": "kitob"},
        {"index": 6, "was": "ilmmarkazi", "text": "ilm markazi"},
        {"index": 8, "count": 2, "was": "hech kim", "text": "hechkim"},
        {"index": 11, "was": "eee", "text": ""},
        {"index": 12, "was": "shunaqa", "needs_review": True, "note": "aniq emas"}]}, fix / "corrections.json")
    before = src.read_bytes()
    for old in fix.glob("orig*fixed*"):
        old.unlink()
    p = _run("apply_corrections.py", src, fix / "corrections.json")
    out = fix / "orig.words.fixed.json"
    ok = p.returncode == 0 and out.is_file() and (fix / "orig.fixed.srt").is_file() and (fix / "orig.fixed.txt").is_file()
    detail = _tail(p, 3) if not ok else ""
    if ok:
        got = C.read_json(out)["words"]
        by = {w["word"]: w for w in got}
        orig = {w["word"]: w for w in words}
        same = all((by[k]["start"], by[k]["end"]) == (orig[k]["start"], orig[k]["end"])
                   for k in ("bugun", "men", "sizga", "haqida", "da", "bilmagan", "shunaqa", "narsa"))
        fixed_1to1 = (by["kitob"]["start"], by["kitob"]["end"]) == (orig["kitop"]["start"], orig["kitop"]["end"])
        split = (by["ilm"]["start"] == orig["ilmmarkazi"]["start"] and by["markazi"]["end"] == orig["ilmmarkazi"]["end"]
                 and by["ilm"]["end"] == by["markazi"]["start"]
                 and abs((by["ilm"]["end"] - by["ilm"]["start"]) - (by["markazi"]["end"] - by["markazi"]["start"])) < 0.002
                 and by["ilm"].get("needs_review") and by["markazi"].get("needs_review"))
        merge = (by["hechkim"]["start"] == orig["hech"]["start"] and by["hechkim"]["end"] == orig["kim"]["end"]
                 and by["hechkim"].get("needs_review"))
        ok = bool(same and fixed_1to1 and split and merge and "eee" not in by and by["shunaqa"].get("needs_review")
                  and len(got) == len(words) - 1)
        detail = (f"8 ta tegilmagan + 1 ta tuzatilgan so'z vaqti aynan o'sha: {same and fixed_1to1}; "
                  f"bo'lish: {bool(split)}; birlashtirish: {bool(merge)}")
    check("apply_corrections: matn tuzatildi, vaqtlar o'zgarmadi", ok, detail)
    check("apply_corrections: asl words.json qayta yozilmadi", src.read_bytes() == before)
    C.write_json({"corrections": [{"index": 4, "was": "boshqa", "text": "x"}]}, fix / "bad.json")
    p1 = _run("apply_corrections.py", src, fix / "bad.json", "-o", fix / "bad.fixed.json")
    p2 = _run("apply_corrections.py", src, fix / "corrections.json", "-o", src)
    check("apply_corrections: noto'g'ri raqam va asl fayl ustiga yozish rad etiladi",
          p1.returncode == 1 and not (fix / "bad.fixed.json").exists() and p2.returncode == 1
          and src.read_bytes() == before)

    if no_whisper:
        C.info("  [--] transcribe.py (whisper) sinovlari o'tkazib yuborildi (--no-whisper)")
        return

    # ---- transcribe.py: eski buyruq va yangi parametrlar
    tr = work / "tr"
    p = _run("transcribe.py", video, "--out-dir", tr / "eski")
    j = tr / "eski" / "orig.words.json"
    ok = p.returncode == 0 and j.is_file() and (tr / "eski" / "orig.srt").is_file()
    data = C.read_json(j) if ok else {}
    check("transcribe.py eski buyruq bilan ishlaydi, chiqish formati o'sha",
          ok and set(data) == OLD_KEYS and isinstance(data["words"], list)
          and all(set(w) == {"start", "end", "word", "prob"} for w in data["words"]),
          f"kalitlar: {', '.join(sorted(data))}" if ok else _tail(p))
    model = str(C.load_style()["whisper"].get("model", "small"))
    p = _run("transcribe.py", video, "--out-dir", tr / "yangi", "--name", "yangi", "--model", model,
             "--language", "uz", "--beam-size", "2", "--compute-type", "int8")
    j = tr / "yangi" / "yangi.words.json"
    ok = p.returncode == 0 and j.is_file()
    check("transcribe.py yangi parametrlar bilan (--model, --language, --beam-size, --compute-type)",
          ok and C.read_json(j).get("model") == model, _tail(p, 2) if not ok else f"model: {model}")
    p = _run("transcribe.py", "--model-info")
    check("transcribe.py --model-info (sozlamadagi model keshda)", p.returncode == 0 and "model.bin" in p.stdout,
          _tail(p, 4) if p.returncode else " ".join(p.stdout.split())[:150])
    p = _run("transcribe.py", video, "--model", "bunday-model-yoq")
    check("noma'lum model nomi tushunarli xato beradi", p.returncode == 1 and "Noma'lum model" in p.stderr)

    # ---- ruxsatsiz yuklanmasligi
    if T.model_status(UZ_MODEL)["cached"]:
        C.info(f"  [--] ruxsatsiz yuklash sinovi o'tkazib yuborildi: {UZ_MODEL} allaqachon kompyuterda")
        return
    p = _run("transcribe.py", video, "--out-dir", tr / "ruxsatsiz", "--model", UZ_MODEL)
    text = p.stdout + p.stderr
    if p.returncode == T.EXIT_NEED_DOWNLOAD:
        size = next((l.strip() for l in text.splitlines() if "Yuklash hajmi" in l), "")
        check("yangi model ruxsatsiz yuklanmaydi (chiqish kodi 4, hajmi ko'rsatiladi)",
              "YUKLASHGA RUXSAT KERAK" in text and not T.model_status(UZ_MODEL)["cached"]
              and not (tr / "ruxsatsiz" / "orig.words.json").exists(), size)
    elif "bilib bo'lmadi" in text:
        # internet yo'q: hajmni so'rab bo'lmadi, lekin baribir hech narsa yuklanmadi
        check("yangi model ruxsatsiz yuklanmaydi (internet yo'q, hajmi so'ralmadi)",
              p.returncode == 1 and not T.model_status(UZ_MODEL)["cached"], "internet yo'q")
    else:
        check("yangi model ruxsatsiz yuklanmaydi (chiqish kodi 4, hajmi ko'rsatiladi)", False, _tail(p))


def main() -> int:
    ap = argparse.ArgumentParser(description="Transkripsiya qismini sinaydi.")
    ap.add_argument("--no-whisper", action="store_true")
    args = ap.parse_args()
    import selftest as ST
    work = C.TEMP_DIR / "selftest"
    work.mkdir(parents=True, exist_ok=True)
    video = work / "test_video.mp4"
    if not video.is_file():
        ST.make_test_video(video)
    run(ST.check, video, work, args.no_whisper)
    failed = [r for r in ST.results if not r[1]]
    C.info(f"\nNATIJA: {len(ST.results) - len(failed)}/{len(ST.results)} tekshiruv o'tdi.")
    return 1 if failed else 0


if __name__ == "__main__":
    C.run_main(main)
