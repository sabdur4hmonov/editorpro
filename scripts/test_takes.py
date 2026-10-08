"""Dubl tanlash (scripts/takes.py) sinovlari: fixture holatlar, sintetik aniqlik o'lchovi va media bilan to'liq yo'l.

    python scripts/test_takes.py            # hammasi (aniqlik raqamlari chiqadi)
    python scripts/test_takes.py --quick    # aniqlik sinovida kamroq stsenariy

Whisper ishlatilmaydi: so'zlar qo'lda (whisper xatolariga o'xshatib) beriladi, media sinovida kesh fayliga yoziladi.
Haqiqiy o'zbek nutqi bilan aniqlik bu yerda isbotlanmaydi (docs/TAKES.md: jonli sinov).
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

import common as C
import script_align as SA
import takes as TK

STYLE = C.load_style()
CFG = TK.config(STYLE)
QUICK = False
ACCURACY: dict = {}


def W(text: str, t0: float = 0.0, prob: float = 0.9, gap: float = 1.0) -> list:
    """Matndan whisperga o'xshash so'zlar: har so'z 0.35 s, oralig'i 0.12 s; "|" - uzun pauza."""
    out, t = [], t0
    for w in text.split():
        if w == "|":
            t += gap
            continue
        out.append({"word": w, "start": round(t, 3), "end": round(t + 0.35, 3), "prob": prob})
        t += 0.47
    return out


def clip(name: str, text: str = "", duration: float | None = None, **kw) -> dict:
    words = W(text, **kw) if text else []
    return {"name": name, "kind": "video", "duration": duration or (words[-1]["end"] + 0.6 if words else 4.0),
            "words": words}


def run(clips: list, script: str | None = None, override: dict | None = None, created: dict | None = None) -> dict:
    segs = TK.script_segments(script, CFG) if script else None
    order = TK.order_clips([c["name"] for c in clips], created, override)
    return TK.analyze([dict(c) for c in clips], CFG, segs, override or {}, order)


def chosen(res: dict) -> dict:
    return {l["n"]: l.get("chosen") for l in res["lines"]}


SCRIPT = """Assalomu alaykum, bugun sizga uchta sir aytaman.
Birinchi set: qovurg'a, salat va non.
Ikkinchi set: qovurg'a, salat va choy.
Manzilimiz Chilonzor, o'n to'rtinchi kvartal.
Obuna bo'ling va do'stlaringizga yuboring!"""


class FixtureTests(unittest.TestCase):
    def test_normalisation_apostrophes_cyrillic_numbers(self):
        self.assertEqual(SA.norm("o'zbek"), SA.norm("oʻzbek"))
        self.assertEqual(SA.norm("o‘zbek"), SA.norm("o’zbek"))
        self.assertEqual(SA.norm("oʼzbek"), SA.norm("o`zbek"))
        self.assertEqual(SA.norm("Ўзбек"), SA.norm("o'zbek"))
        M = TK.Matcher(CFG)
        self.assertGreaterEqual(M.sim("20", "yigirma"), 0.7)
        res = run([clip("a.mp4", "har kuni yigirma daqiqa o'qing")], "Har kuni !!20!! daqiqa o'qing.")
        t = next(t for t in res["takes"] if t["id"] == res["lines"][0]["chosen"])
        self.assertEqual(res["lines"][0]["status"], "good")
        self.assertTrue(any("raqam/so'z" in r for r in t["reasons"]), t["reasons"])
        res = run([clip("a.mp4", "ассалому алайкум бугун сизга учта сир айтаман")], "Assalomu alaykum, bugun sizga uchta sir aytaman.")
        self.assertEqual(res["lines"][0]["status"], "good")

    def test_whisper_letter_errors(self):
        clips = [clip("1.mp4", "asalomu aleykum bugun siizga ucta sir aytaman"),
                 clip("2.mp4", "birinci set qovurga salad va non"),
                 clip("3.mp4", "ikkinchi sett qovurqa salat va choy"),
                 clip("4.mp4", "manzilimz chilanzor on tortinchi kvartal"),
                 clip("5.mp4", "obuna buling va dostlarngizga yuboring")]
        res = run(clips, SCRIPT)
        self.assertEqual(chosen(res), {1: "1.mp4 #1", 2: "2.mp4 #1", 3: "3.mp4 #1", 4: "4.mp4 #1", 5: "5.mp4 #1"})
        self.assertEqual([e["lines"] for e in res["entries"]], [[1], [2], [3], [4], [5]])

    def test_dropped_words(self):
        res = run([clip("a.mp4", "assalomu bugun sizga sir aytaman"), clip("b.mp4", "obuna boling dostlaringizga yuboring")],
                  SCRIPT)
        self.assertEqual(chosen(res)[1], "a.mp4 #1")
        self.assertEqual(chosen(res)[5], "b.mp4 #1")
        t = next(t for t in res["takes"] if t["id"] == "a.mp4 #1")
        self.assertLess(t["cover"], 1.0)
        self.assertEqual({l["n"] for l in res["lines"] if l["status"] == "missing"}, {2, 3, 4})

    def test_mixed_order_follows_script(self):
        clips = [clip("zz.mp4", "assalomu alaykum bugun sizga uchta sir aytaman"),
                 clip("aa.mp4", "obuna boling va dostlaringizga yuboring"),
                 clip("mm.mp4", "manzilimiz chilonzor on tortinchi kvartal"),
                 clip("kk.mp4", "ikkinchi set qovurga salat va choy"),
                 clip("bb.mp4", "birinchi set qovurga salat va non")]
        res = run(clips, SCRIPT)
        self.assertEqual([e["clip"] for e in res["entries"]], ["zz.mp4", "bb.mp4", "kk.mp4", "mm.mp4", "aa.mp4"])

    def test_retakes_best_take_and_retake_word(self):
        clips = [clip("01.mp4", "assalomu alaykum bugun ee sizga | qaytadan | assalomu alaykum bugun sizga uchta sir aytaman"),
                 clip("02.mp4", "obuna boling mm va va dostlaringizga yuboring"),
                 clip("03.mp4", "obuna boling va dostlaringizga yuboring")]
        res = run(clips, SCRIPT)
        self.assertEqual(chosen(res)[1], "01.mp4 #2")
        broken = next(t for t in res["takes"] if t["id"] == "01.mp4 #1")
        self.assertTrue(broken["retake_after"])
        self.assertTrue(any("qaytadan" in r for r in broken["reasons"]))
        self.assertEqual(chosen(res)[5], "03.mp4 #1")
        first = next(e for e in res["entries"] if e["clip"] == "01.mp4")
        self.assertGreater(first["in"], 4.0)            # buzilgan urinish va "qaytadan" montajga kirmaydi
        res = run(clips)                                  # skriptsiz ham shunday
        by_text = {l["text"]: l.get("chosen") for l in res["lines"]}
        self.assertIn("01.mp4 #2", by_text.values())
        self.assertIn("03.mp4 #1", by_text.values())
        self.assertEqual(len(res["lines"]), 2)

    def test_two_similar_lines_are_not_retakes(self):
        clips = [clip("1.mp4", "birinchi set qovurga salat va non"), clip("2.mp4", "ikkinchi set qovurga salat va choy")]
        res = run(clips, SCRIPT)
        self.assertEqual((chosen(res)[2], chosen(res)[3]), ("1.mp4 #1", "2.mp4 #1"))
        res = run(clips)
        self.assertEqual(len(res["lines"]), 2)
        self.assertTrue(all(l["status"] == "good" for l in res["lines"]))

    def test_two_lines_in_one_clip(self):
        res = run([clip("x.mp4", "birinchi set qovurga salat va non | ikkinchi set qovurga salat va choy")], SCRIPT)
        self.assertEqual((chosen(res)[2], chosen(res)[3]), ("x.mp4 #1", "x.mp4 #2"))
        self.assertEqual(len(res["entries"]), 1)          # ketma-ket: bitta bo'lak bo'lib qoladi
        self.assertEqual(res["entries"][0]["lines"], [2, 3])

    def test_clip_without_speech_is_proposed_not_guessed(self):
        clips = [clip("01.mp4", "assalomu alaykum bugun sizga uchta sir aytaman"), clip("02.mp4"),
                 clip("03.mp4", "birinchi set qovurga salat va non")]
        res = run(clips, SCRIPT)
        p = res["placements"][0]
        self.assertEqual((p["clip"], p["after_line"], p["confidence"]), ("02.mp4", 1, "low"))
        self.assertEqual([e["clip"] for e in res["entries"]], ["01.mp4", "02.mp4", "03.mp4"])
        self.assertTrue(any("02.mp4 (nutqsiz)" in d for d in res["decisions"]))
        res = run(clips, SCRIPT, {"place": [{"clip": "02.mp4", "after_line": 2}]})
        self.assertEqual([e["clip"] for e in res["entries"]], ["01.mp4", "03.mp4", "02.mp4"])
        self.assertFalse(any("02.mp4" in d for d in res["decisions"]))

    def test_long_paragraph_script(self):
        para = " ".join(SCRIPT.splitlines())
        segs = TK.script_segments(para, CFG)
        self.assertEqual([x["text"][:8] for x in segs], ["Assalomu", "Birinchi", "Ikkinchi", "Manzilim", "Obuna bo"])
        para2 = para.replace("va non.", "va non. [rasm: set]")
        segs2 = TK.script_segments(para2, CFG)
        self.assertTrue(any("[rasm: set]" in s["raw"] for s in segs2))
        clips = [clip("a.mp4", "assalomu alaykum bugun sizga uchta sir aytaman"),
                 clip("b.mp4", "obuna boling va dostlaringizga yuboring")]
        res = run(clips, para)
        self.assertEqual([l["status"] for l in res["lines"]].count("good"), 2)
        self.assertEqual([e["clip"] for e in res["entries"]], ["a.mp4", "b.mp4"])

    def test_no_script_order_sources(self):
        lines = {"hook": "bilasizmi nega bu taom mashhur", "mid": "bu yerda qovurga juda mazali pishadi",
                 "cta": "obuna boling va bizga murojaat qiling"}
        numbered = [clip("clip 3.mp4", lines["cta"]), clip("clip 1.mp4", lines["hook"]), clip("clip 2.mp4", lines["mid"])]
        res = run(numbered)
        self.assertEqual(res["order"]["source"], "fayl nomidagi raqam")
        self.assertEqual([l["text"] for l in res["lines"]], [lines["hook"], lines["mid"], lines["cta"]])
        named = [clip("xa.mp4", lines["cta"]), clip("ya.mp4", lines["hook"]), clip("za.mp4", lines["mid"])]
        res = run(named, created={"xa.mp4": 300.0, "ya.mp4": 100.0, "za.mp4": 200.0})
        self.assertIn("metadata", res["order"]["source"])
        self.assertEqual([l["text"] for l in res["lines"]], [lines["hook"], lines["mid"], lines["cta"]])
        res = run(named)
        self.assertEqual(res["order"]["confidence"], "low")
        self.assertEqual([l["text"] for l in res["lines"]], [lines["hook"], lines["mid"], lines["cta"]])
        self.assertTrue(any("Tartib taxminiy" in d for d in res["decisions"]))
        res = run(named, override={"order": [3, 1, 2]})
        self.assertEqual([e["lines"][0] for e in res["entries"]], [3, 1, 2])

    def test_close_call_is_not_decided_silently(self):
        res = run([clip("1.mp4", "obuna boling va dostlaringizga yuboring"),
                   clip("2.mp4", "obuna boling va dostlaringizga yuboring")], SCRIPT)
        line = res["lines"][4]
        self.assertEqual(line["status"], "close")
        self.assertTrue(any(d.startswith("5-gap [close call]") for d in res["decisions"]))

    def test_override_pin_force_exclude(self):
        clips = [clip("1.mp4", "obuna boling va dostlaringizga yuboring"),
                 clip("2.mp4", "obuna boling ee va dostlaringizga yuboring"),
                 clip("3.mp4", "nimadir boshqa gap aytildi bu yerda")]
        res = run(clips, SCRIPT)
        self.assertEqual(chosen(res)[5], "1.mp4 #1")
        self.assertEqual(res["unmatched"][0]["clip"], "3.mp4")
        res = run(clips, SCRIPT, {"force": [{"line": 5, "clip": "2.mp4", "take": 1}], "exclude": ["3.mp4"]})
        self.assertEqual((chosen(res)[5], res["lines"][4]["status"]), ("2.mp4 #1", "forced"))
        self.assertEqual(res["unmatched"], [])
        res = run(clips, SCRIPT, {"pin": [{"clip": "3.mp4", "line": 4}]})
        self.assertEqual(chosen(res)[4], "3.mp4 #1")
        self.assertEqual(res["lines"][3]["status"], "decide")   # mos emas: tasdiqqa chiqadi
        res = run(clips, SCRIPT, {"clips": {"3.mp4": {"role": "product"}}})
        self.assertEqual((res["unmatched"], res["placements"][0]["clip"]), ([], "3.mp4"))   # qo'lda: nutqsiz klip
        res = run(clips, SCRIPT, {"force": [{"line": 5, "clip": "2.mp4", "in": 0.0, "out": 1.0}]})
        self.assertEqual(res["lines"][4]["status"], "forced")
        self.assertIn("(qo'lda)", chosen(res)[5])

    def test_cut_points_at_word_boundaries_in_silence(self):
        c = clip("a.mp4", "salom ee qaytadan | salom dostlar bugun", t0=0.5)
        audio = np.zeros(int(6 * TK.SR), np.float32)
        for w in c["words"]:
            a, b = int(w["start"] * TK.SR), int(w["end"] * TK.SR)
            audio[a:b] = 0.4 * np.sin(np.arange(b - a) * 2 * np.pi * 220 / TK.SR)
        audio[int(2.0 * TK.SR):int(2.05 * TK.SR)] = 0.0
        c["duration"] = 6.0
        res = TK.analyze([dict(c)], CFG, None, {}, None, {"a.mp4": {"audio": audio, "frames": []}})
        t = next(t for t in res["takes"] if t["id"] == res["lines"][0]["chosen"])
        words = c["words"]
        self.assertGreater(t["cut_in"], words[t["w0"] - 1]["end"])           # oldingi so'zga ("qaytadan") o'tmaydi
        self.assertLess(t["cut_in"], words[t["w0"]]["start"])
        self.assertGreater(t["cut_out"], words[t["w1"]]["end"])
        self.assertEqual(t["cut_warn"], [])
        rms = lambda x: float(np.sqrt(np.mean(audio[int((x - 0.01) * TK.SR):int((x + 0.01) * TK.SR)] ** 2)))
        self.assertLess(rms(t["cut_in"]), 0.01)
        self.assertLess(rms(t["cut_out"]), 0.01)


# ---------------------------------------------------------------- sintetik aniqlik

VOCAB = ("bugun ertaga oshxona taom qovurga salat non choy palov somsa manti shashlik lagmon sho'rva go'sht tovuq "
         "baliq sabzavot meva shirinlik tort qahva sharbat mehmon oila do'st bola ona ota restoran kafe shahar "
         "ko'cha mahalla bozor narx chegirma aksiya yetkazib berish buyurtma telefon manzil vaqt kun hafta oy yil "
         "katta kichik yangi eski issiq sovuq mazali shirin achchiq tez sekin yaxshi zo'r ajoyib chiroyli toza "
         "sifatli arzon qimmat birga hamma har doim hozir keyin oldin albatta faqat yana juda eng ko'p kam "
         "tayyorlaymiz pishiramiz kutamiz taklif qilamiz ko'rasiz tatib ko'ring keling qo'ng'iroq qiling "
         "oshpazimiz ustamiz retseptimiz tandir qozon olov ziravor piyoz sabzi guruch un tuxum sut qaymoq").split()
ORD = ["birinchi", "ikkinchi", "uchinchi", "to'rtinchi"]


def noisy(word: str, rnd: random.Random) -> str:
    """Whisperga o'xshash harf xatosi."""
    ops = rnd.choice(["sub", "del", "dup", "apos", "xh", "none"])
    w = word
    if ops == "sub" and len(w) > 3:
        i = rnd.randrange(1, len(w))
        w = w[:i] + rnd.choice("aeiouxqgkh") + w[i + 1:]
    elif ops == "del" and len(w) > 3:
        i = rnd.randrange(1, len(w))
        w = w[:i] + w[i + 1:]
    elif ops == "dup":
        i = rnd.randrange(len(w))
        w = w[:i] + w[i] + w[i:]
    elif ops == "apos":
        w = w.replace("'", rnd.choice(["ʻ", "‘", "’", ""]))
    elif ops == "xh":
        w = w.replace("x", "h").replace("q", "k")
    return w


def scenario(rnd: random.Random, numbered: bool) -> dict:
    """Tasodifiy skript, dubllar (biri toza, qolganlari buzuq), kliplar, nutqsiz klip. Haqiqiy javoblar bilan."""
    n = rnd.randint(4, 7)
    lines = [[rnd.choice(VOCAB) for _ in range(rnd.randint(5, 9))] for _ in range(n)]
    if rnd.random() < 0.5:                       # ikki o'xshash gap (faqat tartib so'zi boshqa)
        k = rnd.randrange(n - 1)
        a, b = rnd.sample(ORD, 2)
        lines[k] = [a] + lines[k][1:]
        lines[k + 1] = [b] + lines[k][1:]
    rec = []                                     # yozilish tartibi: (gap, turi, so'zlar)
    for li, line in enumerate(lines):
        kinds = rnd.choice([["clean"], ["broken", "clean"], ["fillers", "clean"], ["clean", "broken"],
                            ["broken", "fillers", "clean"]])
        for kind in kinds:
            if kind == "clean":
                words = [noisy(w, rnd) if rnd.random() < 0.25 else w for w in line if rnd.random() > 0.06]
            elif kind == "broken":
                cut = max(1, int(len(line) * rnd.uniform(0.3, 0.6)))
                words = [noisy(w, rnd) if rnd.random() < 0.25 else w for w in line[:cut]] + ["ee", "|", "qaytadan"]
            else:
                words = list(line)
                words.insert(rnd.randrange(1, len(words)), "ee")
                i = rnd.randrange(len(words) - 1)
                words.insert(i, words[i])
                words.insert(rnd.randrange(1, len(words)), "mm")
                words = [noisy(w, rnd) if rnd.random() < 0.25 and w not in ("ee", "mm") else w for w in words]
            rec.append((li, kind, words))
    # kliplar: ketma-ket yozuvlar 1-3 tadan bitta klipga
    clips, truth, i = [], [], 0
    while i < len(rec):
        size = rnd.choice([1, 1, 2, 3])
        chunk = rec[i:i + size]
        text = " | ".join(" ".join(ws) for _, _, ws in chunk)
        clips.append({"text": text, "chunk": chunk})
        i += size
    clips.insert(rnd.randrange(len(clips) + 1), {"text": "", "chunk": []})
    names = [f"klip_{k + 1:02d}.mp4" if numbered else f"{rnd.getrandbits(32):08x}.mp4" for k in range(len(clips))]
    out = []
    for name, c in zip(names, clips):
        out.append(clip(name, c["text"]))
        c["name"] = name
    clean, spans = {}, {}
    for c in clips:
        pos = 0                                      # yozuvning klipdagi so'z oralig'i (haqiqat shu bo'yicha)
        for li, kind, ws in c["chunk"]:
            n = sum(1 for w in ws if w != "|")
            spans.setdefault(c["name"], []).append((pos, pos + n, li, kind))
            pos += n
    script = "\n".join(" ".join(w.capitalize() if j == 0 else w for j, w in enumerate(l)) + "." for l in lines)
    if not numbered:
        rnd.shuffle(out)
    return {"clips": out, "script": script, "spans": spans, "lines": lines,
            "nospeech": next(c["name"] for c in clips if not c["chunk"])}


def truth_of(t: dict, sc: dict) -> tuple:
    """Natijadagi dubl qaysi haqiqiy yozuvga tushadi: (gap, turi) yoki (None, None)."""
    for a, b, li, kind in sc["spans"].get(t["clip"], []):
        if a <= t["w0"] < b:
            return li, kind
    return None, None


def measure(n: int, seed: int, with_script: bool) -> dict:
    """Gapga moslash: toza dubl to'g'ri gapga tushdi. Eng yaxshi dubl: har gapda toza dubl tanlandi.
    Tartib: montajdagi gaplar ketma-ketligi skript/yozilish tartibiga teng. Nutqsiz klip topildi va taklif qilindi."""
    rnd = random.Random(seed)
    lines_total = line_ok = best_ok = order_ok = nospeech_ok = 0
    for _ in range(n):
        sc = scenario(rnd, numbered=not with_script)
        res = run(sc["clips"], sc["script"] if with_script else None)
        by_id = {t["id"]: t for t in res["takes"]}
        lines_total += len(sc["lines"])
        # natijadagi har gap -> haqiqiy gap (dubllarining ko'pchiligi bo'yicha)
        mapped = []
        for l in res["lines"]:
            real = [truth_of(by_id[i], sc)[0] for i in l.get("takes", [])]
            real = [r for r in real if r is not None]
            mapped.append(max(set(real), key=real.count) if real else None)
        for li in range(len(sc["lines"])):
            rows = [k for k, m in enumerate(mapped) if m == li]
            if with_script:
                rows = [li] if li < len(res["lines"]) else []
            cleans = [t for t in res["takes"] if truth_of(t, sc) == (li, "clean")]
            line_ok += bool(rows) and all(res["lines"][r].get("takes") and t["id"] in res["lines"][r]["takes"]
                                          for t in cleans for r in rows[:1])
            best_ok += bool(rows) and any(truth_of(by_id[res["lines"][r]["chosen"]], sc) == (li, "clean")
                                          for r in rows if res["lines"][r].get("chosen"))
        seq = [truth_of(by_id[i], sc)[0] for e in res["entries"] if e["kind"] == "take" for i in e["take"].split(" + ")]
        seq = [x for k, x in enumerate(seq) if k == 0 or x != seq[k - 1]]
        order_ok += seq == list(range(len(sc["lines"])))
        nospeech_ok += any(p["clip"] == sc["nospeech"] for p in res["placements"])
    return {"scenarios": n, "lines": lines_total, "line_match": round(line_ok / lines_total, 3),
            "best_take": round(best_ok / lines_total, 3), "order": round(order_ok / n, 3),
            "no_speech_found": round(nospeech_ok / n, 3)}


class AccuracyTests(unittest.TestCase):
    def test_accuracy_with_script(self):
        m = measure(25 if QUICK else 80, 7, True)
        ACCURACY["skript bilan"] = m
        self.assertGreaterEqual(m["line_match"], 0.97, m)
        self.assertGreaterEqual(m["best_take"], 0.95, m)
        self.assertGreaterEqual(m["order"], 0.95, m)
        self.assertEqual(m["no_speech_found"], 1.0, m)

    def test_accuracy_without_script(self):
        m = measure(25 if QUICK else 80, 11, False)
        ACCURACY["skriptsiz"] = m
        self.assertGreaterEqual(m["line_match"], 0.93, m)
        self.assertGreaterEqual(m["best_take"], 0.93, m)
        self.assertGreaterEqual(m["order"], 0.85, m)
        self.assertEqual(m["no_speech_found"], 1.0, m)


# ---------------------------------------------------------------- media bilan to'liq yo'l

WORK = C.TEMP_DIR / "takes_fixture"                  # papka nomi = ish nomi: temp/takes_fixture_src/takes_fixture


def make_clip(path: Path, words: list, duration: float, speech: bool = True, color: str | None = None) -> None:
    """Sintetik klip: so'z vaqtlarida ton (yumshoq boshlanadi), orasi jim; tasvir testsrc (yoki rang)."""
    sr = 48000
    audio = np.zeros(int(duration * sr), np.float32)
    if speech:
        for w in words:
            a, b = int(w["start"] * sr), int(w["end"] * sr)
            env = np.minimum(1.0, np.minimum(np.arange(b - a), np.arange(b - a)[::-1]) / (0.005 * sr))
            audio[a:b] = 0.35 * np.sin(np.arange(b - a) * 2 * np.pi * 200 / sr) * env
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((audio * 32767).astype("<i2").tobytes())
    src = f"color=c={color}:s=540x960:r=30:d={duration}" if color else f"testsrc=size=540x960:rate=30:duration={duration}"
    C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src,
           "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           str(path)])
    wav.unlink()


class MediaTests(unittest.TestCase):
    def test_folder_to_assembled_video_and_verify(self):
        import assemble as A
        src = C.TEMP_DIR / "takes_fixture_src" / "takes_fixture"
        shutil.rmtree(WORK, ignore_errors=True)
        shutil.rmtree(src, ignore_errors=True)
        src.mkdir(parents=True)
        (src / "script.txt").write_text("Assalomu alaykum, bugun sizga uchta sir aytaman.\n"
                                        "Obuna bo'ling va do'stlaringizga yuboring!\n", encoding="utf-8")
        c1 = W("assalomu alaykum bugun ee | qaytadan | assalomu alaykum bugun sizga uchta sir aytaman", t0=0.4)
        c2 = W("obuna boling va dostlaringizga yuboring", t0=0.5)
        make_clip(src / "01.mp4", c1, c1[-1]["end"] + 0.8)
        make_clip(src / "02.mp4", [], 2.0, speech=False, color="orange")
        make_clip(src / "03.mp4", c2, c2[-1]["end"] + 0.8)
        segs = TK.script_segments((src / "script.txt").read_text(encoding="utf-8"), CFG)
        wcfg = TK.whisper_cfg(STYLE, CFG, segs)
        self.assertIn("hotwords", wcfg)                    # o'rnatilgan faster-whisper hotwords ni qo'llaydi
        tdir = WORK / "takes"
        tdir.mkdir(parents=True)
        for name, ws in (("01.mp4", c1), ("02.mp4", []), ("03.mp4", c2)):
            C.write_json({"words": ws, "takes_key": TK.cache_key(src / name, wcfg)}, TK.words_path(tdir, src / name))
        res = TK.prepare(src, STYLE)
        data = C.read_json(WORK / "takes.json")
        self.assertEqual(res["mode"], "script")
        self.assertEqual([e["clip"] for e in data["entries"]], ["01.mp4", "02.mp4", "03.mp4"])
        self.assertTrue((WORK / "report.html").is_file())
        self.assertIn("Tasdiq kerak", (WORK / "report.html").read_text(encoding="utf-8"))
        manifest = C.read_json(res["manifest"])
        self.assertEqual([c["role"] for c in manifest["clips"]], ["speech", "product", "speech"])
        self.assertGreater(manifest["clips"][0]["in"], c1[3]["end"])          # "qaytadan" dan keyin
        self.assertEqual(Path(res["script_lines"]).read_text(encoding="utf-8").count("\n"), 2)
        built = A.build(res["manifest"], STYLE)
        # yig'ilgan video so'zlari: tanlangan dubllar so'zlari yangi vaqtga ko'chiriladi (whisper o'rniga)
        words, by = [], {"01.mp4": c1, "03.mp4": c2}
        for seg, item in zip(built["segments"], manifest["clips"]):
            for w in by.get(Path(item["file"]).name, []):
                if item["in"] <= w["start"] and w["end"] <= item["out"]:
                    words.append(dict(w, start=w["start"] - item["in"] + seg["start"], end=w["end"] - item["in"] + seg["start"]))
        v = TK.verify(WORK, words, STYLE)
        self.assertEqual(v["coverage"], 1.0, v)
        self.assertEqual((v["missing"], v["out_of_order"]), ([], []))
        self.assertTrue(all(j["ok"] for j in v["junctions"]), v["junctions"])
        self.assertEqual(len(v["junctions"]), 2)
        # qo'lda: nutqsiz klip tashlansin -> keyingi ishga tushirishda ustun
        C.write_json({"place": [{"clip": "02.mp4", "skip": True}]}, WORK / "takes.override.json")
        res = TK.prepare(src, STYLE)
        self.assertEqual([Path(c["file"]).name for c in C.read_json(res["manifest"])["clips"]], ["01.mp4", "03.mp4"])
        # qo'lda tahrirlangan clips.json ustidan yozilmaydi
        hand = C.read_json(WORK / "clips.json")
        hand["clips"][0]["focus_x"] = 0.3
        C.write_json(hand, WORK / "clips.json")
        res = TK.prepare(src, STYLE)
        self.assertEqual(Path(res["manifest"]).name, "clips.json")
        self.assertEqual(C.read_json(WORK / "clips.json")["clips"][0]["focus_x"], 0.3)
        self.assertTrue((WORK / "takes.clips.json").is_file())

    def test_junction_checks_find_click_black_and_cut_word(self):
        sr, path = 48000, WORK / "bad_join.mp4"
        WORK.mkdir(parents=True, exist_ok=True)
        t = np.arange(2 * sr) / sr
        audio = 0.6 * np.sin(2 * np.pi * 220 * t)
        audio[sr:] = 0.6 * np.cos(2 * np.pi * 220 * t[sr:])  # 1.0 s: keskin sakrash (fade yo'q)
        wav = WORK / "bad_join.wav"
        with wave.open(str(wav), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes((audio * 32767).astype("<i2").tobytes())
        C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
               "color=c=black:s=320x568:r=30:d=1", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=30:duration=1",
               "-i", str(wav), "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(path.with_suffix(".mov"))])
        res = TK.check_junctions(path.with_suffix(".mov"), [1.0], [{"word": "salom", "start": 0.8, "end": 1.3}], CFG)[0]
        text = "; ".join(res["problems"])
        self.assertFalse(res["ok"])
        for key in ("so'z ulanish ustida", "qora kadr", "chertish"):
            self.assertIn(key, text)


def main() -> int:
    global QUICK
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="Aniqlik sinovida kamroq stsenariy")
    args = ap.parse_args()
    QUICK = args.quick
    suite = unittest.TestSuite()
    for case in (FixtureTests, AccuracyTests, MediaTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    C.info("\nAniqlik (sintetik, whisperga o'xshash xatolar bilan):")
    for name, m in ACCURACY.items():
        C.info(f"  {name}: {m['scenarios']} stsenariy, {m['lines']} gap | gapga moslash {m['line_match']:.1%} | "
               f"eng yaxshi dubl {m['best_take']:.1%} | tartib {m['order']:.1%} | nutqsiz klip topildi {m['no_speech_found']:.0%}")
    C.write_json(ACCURACY, C.TEMP_DIR / "takes_accuracy.json")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
