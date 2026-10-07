"""Tizim ishlayotganini tekshiradi: test video yasaydi va butun zanjirni sinaydi.

    python scripts/selftest.py              # to'liq sinov (whisper ham)
    python scripts/selftest.py --no-whisper # whisper o'rnatilmagan bo'lsa

Test video: 10 soniya, 1280x720, testsrc + sine (ichida 2 ta jim joy bor).
Hamma fayl temp/selftest/ va output/ ga yoziladi.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import common as C

WORK = C.TEMP_DIR / "selftest"
SCRIPTS = Path(__file__).resolve().parent
results: list = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    C.info(f"  [{'OK' if ok else 'XATO'}] {name}{(' - ' + detail) if detail else ''}")
    return ok


def script(name: str, *args, expect: int = 0) -> subprocess.CompletedProcess:
    """Skriptni xuddi foydalanuvchi kabi buyruq qatoridan ishga tushiradi."""
    # stdin yopiq: skript "y/N" deb so'rab, ko'rinmaydigan savolda osilib qolmasligi uchun
    proc = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], cwd=str(C.ROOT),
                          stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != expect:
        C.info("    --- chiqish ---\n" + "\n".join(
            "    " + l for l in (proc.stdout + proc.stderr).strip().splitlines()[-25:]))
    return proc


def make_test_video(path: Path) -> None:
    """10 s test video. Ovoz: 0-2.5 s ton, 2.5-4 jim, 4-6.5 ton, 6.5-8 jim, 8-10 ton."""
    C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=10",
           "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=10",
           "-af", "volume='if(lt(mod(t,4),2.5),0.5,0)':eval=frame",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-shortest", path])


def main() -> int:
    ap = argparse.ArgumentParser(description="Montaj tizimini test video bilan sinaydi.")
    ap.add_argument("--no-whisper", action="store_true", help="Whisper bosqichini sinama")
    ap.add_argument("--offline", action="store_true", help="Internet kerak bo'lgan sinovni (rasm qidirish) o'tkazib yubor")
    args = ap.parse_args()

    style = C.load_style()
    W, H = style["video"]["width"], style["video"]["height"]
    WORK.mkdir(parents=True, exist_ok=True)

    C.info("1. Dasturlar")
    ffmpeg = C.need_tool("ffmpeg")
    C.need_tool("ffprobe")
    version = C.run([ffmpeg, "-hide_banner", "-version"]).stdout.splitlines()[0]
    check("ffmpeg va ffprobe topildi", True, version)
    for flt in ("subtitles", "loudnorm", "silencedetect", "sidechaincompress"):
        check(f"ffmpeg filtri: {flt}", C.has_filter(flt))
    check("Python versiyasi", sys.version_info >= (3, 9), sys.version.split()[0])

    C.info("\n2. Test video")
    video = WORK / "test_video.mp4"
    make_test_video(video)
    src = C.ffprobe_info(video)
    check("test video yaratildi", src["has_video"] and src["has_audio"] and abs(src["duration"] - 10) < 0.3,
          f"{src['width']}x{src['height']}, {src['duration']:.2f}s")
    before = (video.stat().st_size, video.stat().st_mtime_ns)

    C.info("\n3. auto_cut.py (jim joylarni kesish)")
    job = C.job_dir(video)
    cut = job / "cut.mp4"
    cut.unlink(missing_ok=True)  # oldingi sinovdan qolgan oraliq fayl (temp/ ichida)
    p = script("auto_cut.py", video)
    check("faqat ro'yxat rejimi (kesmasdan)", p.returncode == 0 and "jim" in p.stdout and not cut.exists())
    p = script("auto_cut.py", video, "--apply")
    if check("kesish bajarildi", p.returncode == 0 and cut.is_file()):
        meta = C.ffprobe_info(cut)
        # 2 ta 1.5 s jimlik, har biridan 2 x padding qoladi
        expected = 10 - 2 * (1.5 - 2 * float(style["cut"].get("padding", 0.1)))
        check("kesilgan video uzunligi", abs(meta["duration"] - expected) < 0.35,
              f"{meta['duration']:.2f}s (kutilgan ~{expected:.2f}s)")
        check("kesilgan videoda ovoz bor", meta["has_audio"])

    C.info("\n4. subtitles.py (subtitr, Windows yo'l muammosi shu yerda tekshiriladi)")
    srt = WORK / "sample.srt"
    C.write_srt([
        {"start": 0.3, "end": 2.0, "text": "Salom, bu sinov"},
        {"start": 2.2, "end": 4.0, "text": "O'zbek tili: g'oya, o'quvchi"},
        {"start": 4.2, "end": 6.5, "text": "Привет, это тест"},
    ], srt)
    base = cut if cut.is_file() else video
    p = script("subtitles.py", base, srt, "--approved", "-o", C.OUTPUT_DIR / "selftest_sub.mp4")
    check("subtitr videoga yozildi", p.returncode == 0 and (C.OUTPUT_DIR / "selftest_sub.mp4").is_file())
    p = script("subtitles.py", base, srt, "-o", C.OUTPUT_DIR / "selftest_sub2.mp4", expect=3)
    check("tasdiqsiz subtitr yozilmaydi (kod 3)", p.returncode == 3 and not (C.OUTPUT_DIR / "selftest_sub2.mp4").exists())

    C.info("\n5. render.py (9:16, loudnorm, subtitr)")
    ass = WORK / "sample.ass"
    p = script("subtitles.py", base, srt, "--ass-only", "--ass", ass)
    check("ASS fayl yaratildi (--ass-only)", p.returncode == 0 and ass.is_file())
    import subtitles as S
    S.make_ass(base, srt, ass, style, target_size=(W, H))  # yakuniy o'lcham (1080x1920) uchun qayta yasaladi
    final = C.OUTPUT_DIR / "selftest_render.mp4"
    p = script("render.py", base, "--subs", ass, "-o", final)
    if check("render bajarildi", p.returncode == 0 and final.is_file()):
        meta, problems = C.verify_video(final, W, H, C.ffprobe_info(base)["duration"])
        check("natija formati", not problems,
              f"{meta['width']}x{meta['height']}, {meta['duration']:.2f}s, ovoz: {meta['acodec']}"
              + (("; " + "; ".join(problems)) if problems else ""))

    C.info("\n6. compose.py (motion: subtitr animatsiyasi, elementlar, brend, oxirgi kadr)")
    msrt = WORK / "motion.srt"
    msrt.write_text("1\n00:00:00,300 --> 00:00:02,000\nbugun *sinov* qilamiz\n\n"
                    "2\n00:00:02,200 --> 00:00:04,000\n**3 oyda** natija bo'ladi\n\n"
                    "3\n00:00:04,200 --> 00:00:06,000\n\u041f\u0440\u0438\u0432\u0435\u0442, !!100%!! \u2705\n", encoding="utf-8")
    mel = WORK / "elements.json"
    C.write_json({"elements": [
        {"type": "title", "start": 0.0, "end": 1.5, "text": "TOP 3\n**sinov**"},
        {"type": "list", "start": 1.5, "end": 4.0, "items": [{"at": 1.6, "text": "birinchi"}, {"at": 2.2, "text": "ikkinchi"}]},
        {"type": "stat", "start": 4.0, "end": 6.0, "value": 90, "label": "natija"},
        {"type": "choice", "start": 2.0, "end": 4.0, "y": 0.8, "items": [{"at": 2.0, "text": "to'g'ri javob", "ok": True}]},
        {"type": "voice", "start": 0.5, "end": 3.0, "y": 0.1},
        {"type": "callout", "start": 4.0, "end": 6.0, "text": "shisha panel \U0001F525", "y": 0.2},
        {"type": "lower_third", "start": 0.3, "end": 2.5, "name": "Ism Familiya", "role": "lavozim"},
        {"type": "emoji", "start": 4.5, "end": 6.0, "emoji": "\U0001F680", "x": 0.8, "y": 0.35},
        {"type": "icon", "start": 0.3, "end": 2.5, "name": "rocket-launch", "x": 0.75, "y": 0.45, "size": 0.14,
         "bg": "circle", "text": "belgi"},
        {"type": "sfx", "at": 1.6, "name": "pop"},
        {"type": "burst", "at": 4.2, "emoji": ["\U0001F602", "\U0001F44F"], "count": 6},
        {"type": "confetti", "at": 4.4, "count": 40},
    ]}, mel)
    # ijodiy joylashuv: video kartochkada, orqada chizilgan harakatli fon
    sel = WORK / "stage_elements.json"
    C.write_json({"elements": [
        {"type": "stage", "crop": [0, 0.3, 1, 0.7], "width": 0.9, "y": 0.42, "footer": {"text": "@sinov", "from": 1.0},
         "punch": [{"at": 1.0}], "shake": [{"at": 2.0}], "flash": [{"at": 1.0}], "progress": True},
        {"type": "emoji", "emoji": "\U0001F4B0", "start": 0.8, "end": 3, "x": 0.2, "y": 0.2, "size": 0.14,
         "sticker": True, "rotate": -12, "wiggle": 6},
        {"type": "title", "start": 0.1, "end": 6, "text": "SINOV \U0001F602", "y": 0.12, "stagger": 0.12, "loop": "bob"},
        {"type": "burst", "at": 2.0, "count": 8},
        {"type": "confetti", "at": 1.0, "origin": "top"},
    ]}, sel)
    sshot = WORK / "stage_stills.jpg"
    sshot.unlink(missing_ok=True)
    p = script("compose.py", base, "--subs", msrt, "--elements", sel, "--stills", "1.1,2.3", "--stills-out", sshot)
    check("ijodiy joylashuv (stage, burst, confetti, sarlavha animatsiyasi)",
          p.returncode == 0 and sshot.is_file() and sshot.stat().st_size > 20000)
    # namuna uslubi: har xil presetlar, marker, yulduzcha, bo'lak belgisi, sahna, oq-qora, obuna kartochkasi
    nsrt = WORK / "namuna.srt"
    # 9 bo'lak 0.2..6.9 s oralig'ida: sinov klipi ~7.4 s, preflight klipdan tashqaridagi bo'lakni rad etadi
    ncues = ["**\\*3 oyda Rus tilini** o'rgana olaman deb o'ylaysizmi?", "{caps,y=0.2}**KELINGLAR** hozir sizlarga",
             "{heavy,y=0.3}==Kamerani== *sekin* yaqinlashtirsangiz", "{marker}sohasiga ==kirib kelishimga== asosiy ~~sabab~~",
             "{italic}**Vapsheee** tez chiqish uchun", "{serif}Men *Farruh*", "{single}odam deb", "{karaoke}mening ismim",
             "{clean,anim_main=flicker,anim_sub=bar}*10 yil* orqaga qaytganingizda"]
    nsrt.write_text("".join(
        f"{i + 1}\n{C.srt_time(0.2 + i * 0.75)} --> {C.srt_time(0.2 + i * 0.75 + 0.7)}\n{text}\n\n"
        for i, text in enumerate(ncues)), encoding="utf-8")
    nel = WORK / "namuna_elements.json"
    C.write_json({"elements": [
        {"type": "grade", "mode": "bw", "start": 0, "end": 0.9},
        {"type": "flash", "at": 0.9},
        {"type": "scene", "start": 5.4, "end": 6.2, "background": {"color1": "#0B2A8F", "color2": "#0A1F6B", "pattern": "grid"}},
        {"type": "follow", "start": 6.25, "end": 7.3, "handle": "@sinov_sahifa", "name": "Sinov", "tap": 0.6},
    ]}, nel)
    nshot = WORK / "namuna_stills.jpg"
    nshot.unlink(missing_ok=True)
    p = script("compose.py", base, "--subs", nsrt, "--elements", nel,
               "--stills", "0.6,1.3,2.1,2.8,3.6,4.3,5.1,5.8,6.6,7.1", "--stills-out", nshot)
    check("namuna uslubi: 9 xil subtitr uslubi, marker, sahna, oq-qora, obuna kartochkasi",
          p.returncode == 0 and nshot.is_file() and nshot.stat().st_size > 20000,
          (p.stderr.strip().splitlines() or [""])[-1][:160])
    p = script("compose.py", base, "--subs", WORK / "bad_tag.srt", "--stills", "0.5", "--stills-out", WORK / "bad_tag.jpg") \
        if (WORK / "bad_tag.srt").write_text("1\n00:00:00,100 --> 00:00:01,000\n{yoq-uslub}salom\n", encoding="utf-8") else None
    check("noma'lum subtitr uslubi tushunarli xato beradi", p.returncode == 1 and "noma'lum" in p.stderr)
    import elements as E
    cues = C.words_to_cues([{"start": i * 0.4, "end": i * 0.4 + 0.3, "word": w} for i, w in enumerate(
        "**3 oyda Rus tilini** o'rgana olaman deb o'ylaysizmi? {caps}**KELINGLAR** hozir sizlarga. oddiy gap bu yerda davom etadi va uzun bo'ladi.".split())], {})
    check("blok: urg'uli qisqa gap bitta bo'lakda, {uslub} yangi bo'lak boshlaydi, oddiy gap bo'linadi",
          cues[0]["text"] == "**3 oyda Rus tilini** o'rgana olaman deb o'ylaysizmi?" and cues[1]["text"].startswith("{caps}**KELINGLAR**")
          and len(cues) >= 4 and E.split_cue_tag("{caps,y=0.2} MATN") == ("caps", {"y": "0.2"}, "MATN")
          and [lvl for _, lvl, _ in E.parse_markup("a ==b== ~~c~~ \\*d")] == ["normal", "mark", "mark2", "normal"]
          and E.parse_markup("\\*3")[0][0] == "*3" and C.strip_markup("{caps}**\\*3** ==x==") == "3 x",
          " | ".join(c["text"] for c in cues)[:200])
    shot = WORK / "motion_stills.jpg"
    shot.unlink(missing_ok=True)
    p = script("compose.py", base, "--subs", msrt, "--elements", mel, "--brand", "demo",
               "--stills", "0.8,2.6,5.0", "--stills-out", shot)
    check("tez ko'rish rasmlari (--stills)", p.returncode == 0 and shot.is_file() and shot.stat().st_size > 20000)
    mout = C.OUTPUT_DIR / "selftest_motion.mp4"
    p = script("compose.py", base, "--subs", msrt, "--elements", mel, "--brand", "demo", "-o", mout, expect=3)
    check("tasdiqsiz motion render yozilmaydi (kod 3)", p.returncode == 3)
    p = script("compose.py", base, "--subs", msrt, "--elements", mel, "--brand", "demo", "--approved", "-o", mout)
    check("ovoz: nutq alohida me'yorlandi, effektlar nutqdan past", p.returncode == 0 and (
        "nutq paytida qo'shimchalar nutqdan" in p.stdout or "ustma-ust tushmadi" in p.stdout),
        next((l.strip() for l in p.stdout.splitlines() if "qo'shimchalar" in l), ""))
    if check("motion render bajarildi", p.returncode == 0 and mout.is_file()):
        brand = C.load_style(brand="demo")
        want = C.ffprobe_info(base)["duration"] + float(brand["endcard"]["duration"])
        meta, problems = C.verify_video(mout, W, H, want)
        check("motion natija formati (oxirgi kadr bilan)", not problems,
              f"{meta['width']}x{meta['height']}, {meta['duration']:.2f}s"
              + (("; " + "; ".join(problems)) if problems else ""))

    C.info("\n7. Skript, belgilar, HTML grafika, rasm qidirish")
    import script_align as SA
    heard = [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3, "prob": 0.8} for i, w in enumerate(
        "Bugun sizga uchta sir aytaman birinchisi har kuni yigirma daqiqa oqing ilmmarkazi yordam beradi".split())]
    try:
        res = SA.align(heard, "Bugun sizga **3 ta** sir aytaman.\n[rasm: kitob]\n"
                              "Birinchisi: har kuni !!20 daqiqa!! o'qing, ilm markazi yordam beradi.")
        texts = [w["word"] for w in res["words"]]
        check("skript nutq vaqtlariga tekislandi",
              "**3**" in texts and "!!20!!" in texts and "markazi" in texts and len(res["notes"]) == 1
              and abs(res["notes"][0]["at"] - 2.0) < 0.05 and all(b["start"] >= a["start"] for a, b in zip(res["words"], res["words"][1:])),
              f"{res['report']['matched']}/{res['report']['script_words']} so'z aniq mos, eslatma {res['notes'][0]['at']}s da")
    except Exception as exc:
        check("skript nutq vaqtlariga tekislandi", False, f"{type(exc).__name__}: {exc}")
    ipng = WORK / "icon.png"
    ipng.unlink(missing_ok=True)
    p = script("icons.py", "png", "rocket", "-o", ipng, "--size", "256")
    check("belgi (ikonka) chizildi", p.returncode == 0 and ipng.is_file() and ipng.stat().st_size > 800)
    page = WORK / "karta.html"
    page.write_text((C.ROOT / "assets" / "html" / "shablon.html").read_text(encoding="utf-8"), encoding="utf-8")
    hpng = WORK / "karta.png"
    hpng.unlink(missing_ok=True)
    p = script("html_render.py", page, "-o", hpng, "--trim")
    ok = p.returncode == 0 and hpng.is_file()
    detail = ""
    if ok:
        from PIL import Image
        with Image.open(hpng) as im:
            lo, hi = im.convert("RGBA").getchannel("A").getextrema()
            ok = 600 < im.width <= W and im.height > 400 and hi == 255
            detail = f"{im.width}x{im.height}, shaffoflik {lo}..{hi}"
    check("HTML grafika rasmga aylandi (brauzer orqali)", ok, detail)
    if args.offline:
        C.info("  [--] rasm qidirish: o'tkazib yuborildi (--offline)")
    else:
        idir = WORK / "images"
        p = subprocess.run([sys.executable, str(SCRIPTS / "images.py"), "search", "mountain landscape", "--n", "4",
                            "--source", "openverse,wikimedia", "--out", str(idir)], cwd=str(C.ROOT),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines = [l for l in (p.stdout + p.stderr).strip().splitlines() if l.strip()]
        if p.returncode == 0 and (idir / "candidates.jpg").is_file():
            n = len(C.read_json(idir / "candidates.json").get("candidates", []))
            check("internetdan rasm qidirish (Openverse, Wikimedia)", n > 0, f"{n} ta nomzod; "
                  + "; ".join(l.strip() for l in lines if l.strip().startswith("(")))
            pk = script("images.py", "pick", "1", "--name", "selftest_rasm", "--out", idir)
            got = list(idir.glob("selftest_rasm.*"))
            check("tanlangan rasm yuklandi va manbasi yozildi",
                  pk.returncode == 0 and any(g.suffix in (".jpg", ".png") for g in got)
                  and any(g.name.endswith(".credit.json") for g in got))
        else:
            # internet yo'qligi tizim xatosi emas: sinov yiqilmaydi, lekin sababi ko'rsatiladi
            C.info("  [--] rasm qidirish ishlamadi (internet yoki manba javob bermadi):\n      "
                   + "\n      ".join(lines[-6:]))

    C.info("\n8. pipeline.py (hammasi bitta buyruq bilan)")
    extra = ["--no-subs", "--no-repeats"] if args.no_whisper else []
    out = C.OUTPUT_DIR / "test_video_final.mp4"
    p = subprocess.run([sys.executable, str(SCRIPTS / "pipeline.py"), str(video), "--force", *extra],
                       cwd=str(C.ROOT), stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    note = "whisper bilan" if not args.no_whisper else "whispersiz"
    if p.returncode == 3:
        # whisper tonni "nutq" deb o'ylab matn chiqardi va pipeline tasdiq so'rab to'xtadi (to'g'ri xulq).
        # Bu sinov bo'lgani uchun tasdiqlab davom etamiz.
        note += ", tasdiq bosqichi ham ishladi"
        p = script("pipeline.py", video, "--approve-subs", *extra)
    elif p.returncode != 0:
        C.info("    --- chiqish ---\n" + "\n".join(
            "    " + l for l in (p.stdout + p.stderr).strip().splitlines()[-25:]))
    if check("pipeline tugadi", p.returncode == 0 and out.is_file(), note):
        meta, problems = C.verify_video(out, W, H)
        check("pipeline natijasi", not problems and meta["duration"] < 9.5,
              f"{meta['width']}x{meta['height']}, {meta['duration']:.2f}s, ovoz: {'bor' if meta['has_audio'] else 'yoq'}")
        C.info("    " + "\n    ".join(p.stdout.strip().splitlines()[-9:]))

    C.info("\n9. Transkripsiya (model tanlash, vaqt tekshiruvi, tuzatish)")
    import test_transcribe
    test_transcribe.run(check, video, WORK, args.no_whisper)

    C.info("\n10. Xavfsizlik qoidalari")
    # bir vaqtda bitta og'ir ish: boshqa agent ishlayotgan bo'lsa ikkinchisi tushunarli xato bilan to'xtaydi
    import json as _json
    import time as _time
    C.BUSY_FILE.write_text(_json.dumps({"pid": 1, "agent": "boshqa agent", "what": "sinov", "started": _time.time(),
                                        "alive_at": _time.time()}), encoding="utf-8")
    p = script("pipeline.py", video, "--stills", "1", expect=1)
    blocked = p.returncode == 1 and "boshqa ish ketyapti" in p.stderr
    C.BUSY_FILE.write_text(_json.dumps({"pid": 1, "agent": "boshqa agent", "what": "sinov", "started": 0, "alive_at": 0}),
                           encoding="utf-8")
    # haqiqiy HOLAT.md sinov paytida yo'qolmasligi kerak: baytma-bayt saqlab, oxirida joyiga qaytariladi
    note = C.ROOT / "HOLAT.md"
    real_note = note.read_bytes() if note.is_file() else None
    try:
        p2 = script("handoff.py", "set", "sinov eslatmasi", "--agent", "selftest")
        p3 = script("handoff.py", "show")
        ok = (blocked and C.busy_state() is None and p2.returncode == 0 and p3.returncode == 0
              and "sinov eslatmasi" in p3.stdout and "Band emas" in p3.stdout)
    finally:
        C.BUSY_FILE.unlink(missing_ok=True)
        if real_note is not None:
            note.write_bytes(real_note)
        elif note.is_file():
            note.unlink()
    ok = ok and (note.read_bytes() == real_note if real_note is not None else not note.exists())
    check("navbat: band paytida ikkinchi ish to'xtaydi, eskirgan belgi to'siq bo'lmaydi, holat eslatmasi ishlaydi", ok,
          (p.stderr.strip().splitlines() or [""])[-1][:120] if not blocked else "")
    check("asl (test) video o'zgarmadi", before == (video.stat().st_size, video.stat().st_mtime_ns))
    p = script("render.py", video, "-o", C.INPUT_DIR / "bad.mp4", expect=1)
    check("input/ ga yozish rad etiladi", p.returncode == 1 and not (C.INPUT_DIR / "bad.mp4").exists())

    failed = [r for r in results if not r[1]]
    C.info(f"\nNATIJA: {len(results) - len(failed)}/{len(results)} tekshiruv o'tdi.")
    if failed:
        C.info("O'tmaganlar: " + "; ".join(r[0] for r in failed))
        return 1
    C.info("Hammasi ishlayapti. Sinov natijalari: output/selftest_*.mp4 va output/test_video_final.mp4")
    return 0


if __name__ == "__main__":
    C.run_main(main)
