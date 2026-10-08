"""Butun montajni bitta buyruq bilan bajaradi.

    python scripts/pipeline.py input/video.mp4

Tartib: transcribe -> auto_cut -> (subtitr matnini tasdiqlash) -> subtitles -> render -> tekshiruv

Subtitr matni tasdiqlanmaguncha videoga yozilmaydi:
  1) Birinchi ishga tushirishda matn ko'rsatiladi va skript to'xtaydi (chiqish kodi 3).
  2) Matn temp/<nom>/subs.srt faylida tuzatiladi.
  3) Tasdiqdan keyin:  python scripts/pipeline.py input/video.mp4 --approve-subs
     (oldingi ish qayta bajarilmaydi, tuzatilgan matn ishlatiladi)

Tayyor skript matni bo'lsa (nima deyilgani yozilgan .txt):
     python scripts/pipeline.py input/video.mp4 --script input/video.txt
   Matn skriptdan, vaqt whisperdan olinadi (video yonida shu nomli .txt bo'lsa o'zi topiladi).

Tasdiqlangan (tuzatilgan) so'zlar fayli bo'lsa (scripts/apply_corrections.py natijasi):
     python scripts/pipeline.py input/video.mp4 --words temp/video/orig.words.fixed.json
   Whisper qayta ishlamaydi: matn ham, vaqt ham shu fayldan olinadi.

Lug'at (style/glossary.json va brands/<nom>/glossary.json) har safar o'zi qo'llanadi (--no-glossary o'chiradi).
Foydalanuvchi eslatmalari (style/notes.md, brands/<nom>/notes.md) boshida ko'rsatiladi.

Asl video hech qachon o'zgarmaydi. Natija: output/<nom>_final.mp4
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import common as C
import auto_cut
import render as R
import subtitles as S
import transcribe as T

EXIT_NEED_APPROVAL = 3


def fingerprint(video: Path) -> dict:
    st = video.stat()
    return {"input": str(video), "size": st.st_size, "mtime": int(st.st_mtime)}


def step(title: str) -> float:
    C.info(f"\n=== {title} ===")
    return time.time()


def done(started: float) -> None:
    C.info(f"  ({time.time() - started:.1f}s)")


def main() -> int:
    ap = argparse.ArgumentParser(description="To'liq montaj: transcribe -> auto_cut -> subtitles -> render.")
    ap.add_argument("video", help="Asl video (masalan input/video.mp4), yoki ko'p klipli montaj uchun klip papkasi / clips.json")
    ap.add_argument("-o", "--output", help="Natija (standart: output/<nom>_final.mp4)")
    ap.add_argument("--approve-subs", action="store_true",
                    help="Foydalanuvchi subtitr matnini ko'rib tasdiqladi, davom et")
    ap.add_argument("--no-subs", action="store_true", help="Subtitrsiz (transkripsiya ham qilinmaydi)")
    ap.add_argument("--no-cut", action="store_true", help="Jim joylarni kesma")
    ap.add_argument("--no-repeats", action="store_true", help="Takrorlarni kesma")
    ap.add_argument("--no-silence", action="store_true", help="Jim joylarni kesma (faqat --remove/--trim ishlaydi)")
    ap.add_argument("--remove", help="Qo'lda olib tashlanadigan oraliqlar, asl video bo'yicha: 10-15,22.5-24")
    ap.add_argument("--trim", help="Faqat shu oraliq qolsin, asl video bo'yicha: 5-42")
    ap.add_argument("--script", help="Tayyor skript matni (.txt): subtitr matni shundan, vaqti whisperdan olinadi")
    ap.add_argument("--no-script", action="store_true", help="Video yonidagi shu nomli .txt ni ishlatma")
    ap.add_argument("--words", help="Tasdiqlangan so'zlar fayli (words.fixed.json): whisper o'rniga shu ishlatiladi")
    ap.add_argument("--no-glossary", action="store_true", help="Lug'atni qo'llama")
    ap.add_argument("--music", help="Fon musiqa fayli")
    ap.add_argument("--brand", help="Brend nomi (brands/<nom>/brand.json): shrift, rang, logotip, oxirgi kadr")
    ap.add_argument("--elements", help="Grafik elementlar fayli (standart: temp/<nom>/elements.json, bo'lsa)")
    ap.add_argument("--engine", choices=["motion", "ass", "off"],
                    help="Subtitr dvigateli (style.json: captions.engine ni almashtiradi)")
    ap.add_argument("--stills", help="Render qilmasdan, shu vaqtlardagi kadrlarni rasm qilib ko'rsat: 1.5,4,9")
    ap.add_argument("--draft", action="store_true", help="Kichik qoralama; subtitr tasdiqi baribir talab qilinadi")
    ap.add_argument("--prepare-only", action="store_true", help="Faqat transkripsiya/kesish/matn; hech qanday video render qilinmaydi")
    ap.add_argument("--language", help="Til: uz, ru, en, auto (style.json dagini almashtiradi)")
    ap.add_argument("--model", help="Whisper modeli: base, small, medium ...")
    ap.add_argument("--silence-db", type=float, help="Jimlik chegarasi dB (masalan -40)")
    ap.add_argument("--nvenc", action="store_true", help="NVIDIA karta bilan kodlash")
    ap.add_argument("--force", action="store_true", help="Oldingi oraliq natijalarni tashlab, boshidan boshla")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    total = time.time()
    style = C.load_style(args.style, args.brand)
    if args.engine:
        style["captions"]["engine"] = args.engine
    engine = str(style["captions"].get("engine", "motion")).lower()
    if engine not in ("motion", "ass", "off"):
        raise C.MontajError(f"captions.engine noto'g'ri: {engine!r}. Mumkin: motion, ass, off.")
    if args.draft and engine != "motion":
        raise C.MontajError("--draft hozir motion dvigateli bilan ishlaydi.")
    if args.language:
        style["whisper"]["language"] = args.language
    if args.model:
        style["whisper"]["model"] = args.model
    protect = None
    source = Path(args.video)
    if source.is_dir() or source.suffix.lower() == ".json":
        # ko'p klipli montaj: kliplar avval bitta asosiy videoga yig'iladi (scripts/assemble.py)
        import assemble as A
        C.busy_acquire(f"montaj: {source.name}")
        built = A.build(source, style)
        video, protect = built["video"], built["protect"]
    else:
        video = C.need_file(args.video, "Video")
    if video.suffix.lower() not in C.VIDEO_EXTS:
        C.warn(f"{video.suffix} kengaytmasi odatiy video emas, baribir sinab ko'raman.")
    C.need_tool("ffmpeg"), C.need_tool("ffprobe")
    src = C.ffprobe_info(video)
    if not src["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    work = C.job_dir(video)
    C.busy_acquire(f"montaj: {video.name}")
    out_dir = C.OUTPUT_DIR / style["_brand"] if style.get("_brand") else C.OUTPUT_DIR   # har brend o'z papkasida
    out = Path(args.output) if args.output else out_dir / f"{C.output_stem(video.stem)}_{'draft' if args.draft else 'final'}.mp4"
    C.guard_output(out, video)
    C.info(f"Video: {video}\n  {src['width']}x{src['height']}, {src['fps']:g} fps, {src['duration']:.2f}s, "
           f"ovoz: {'bor' if src['has_audio'] else 'yoq'}\nIsh papkasi: {work}")

    want_subs = bool(style["subtitles"].get("enabled", True)) and not args.no_subs and engine != "off"
    if style.get("_brand"):
        C.info(f"Brend: {style['_brand']}")
    elif C.list_brands():
        C.info("Brend tanlanmadi (umumiy uslub ishlatiladi). Mavjud brendlar: " + ", ".join(C.list_brands())
               + ". Tanlash: --brand NOM")

    def save_result(status: str, **extra) -> None:
        """Holatni temp/<nom>/result.json ga yozadi (watcher va agentlar shuni o'qiydi)."""
        C.write_json({"status": status, "video": str(video), "brand": style.get("_brand", ""), **extra},
                     work / "result.json")
    want_cut = bool(style["cut"].get("enabled", True)) and not args.no_cut
    # tayyor skript: --script yoki video yonidagi shu nomli .txt
    script_file = None
    if args.script:
        script_file = C.need_file(args.script, "Skript fayli")
    elif not args.no_script and video.with_suffix(".txt").is_file():
        script_file = video.with_suffix(".txt")
        C.info(f"Skript topildi (video yonida): {script_file.name}. Ishlatmaslik uchun: --no-script")
    script_fp = ""
    if script_file:
        st = script_file.stat()
        script_fp = f"{script_file}|{st.st_size}|{int(st.st_mtime)}"
    # tasdiqlangan so'zlar fayli (matn tuzatilgan, vaqtlar asl video bo'yicha)
    words_file, words_fp = None, ""
    if args.words:
        if args.script:
            raise C.MontajError("--words va --script birga ishlatilmaydi: bittasini tanlang.")
        words_file = C.need_file(args.words, "So'zlar fayli")
        script_file, script_fp = None, ""          # video yonidagi .txt ham ishlatilmaydi
        st = words_file.stat()
        words_fp = f"{words_file}|{st.st_size}|{int(st.st_mtime)}"
    # lug'at: doim xato yoziladigan so'zlar (umumiy + brend)
    import glossary as G
    gloss = [] if args.no_glossary else G.load(style)
    gloss_fp = "|".join(f"{e['from']}>{e['to']}" for e in gloss)
    import feedback as FB
    FB.print_notes(style.get("_brand") or None)
    state_path, subs_srt = work / "job.json", work / "subs.srt"
    state = C.read_json(state_path) if state_path.is_file() else {}
    remove = auto_cut.parse_ranges(args.remove)
    trim = auto_cut.parse_ranges(args.trim)
    if len(trim) > 1:
        raise C.MontajError("--trim uchun bitta oraliq kerak, masalan: 5-42")
    opts = {"subs": want_subs, "cut": want_cut, "no_repeats": args.no_repeats, "no_silence": args.no_silence,
            "silence_db": args.silence_db, "language": style["whisper"]["language"],
            "model": style["whisper"]["model"], "remove": args.remove or "", "trim": args.trim or "",
            "script": script_fp, "words": words_fp, "glossary": gloss_fp}
    whisper_opts = {"language": style["whisper"]["language"], "model": style["whisper"]["model"]}
    resume = (not args.force and state.get("fingerprint") == fingerprint(video)
              and state.get("opts") == opts and Path(state.get("cut_video", "")).is_file())

    if resume:
        C.info("\nOldingi natija topildi: transkripsiya va kesish qayta bajarilmaydi (--force bilan boshidan).")
        cut_video = Path(state["cut_video"])
    else:
        # ---- 1. transkripsiya
        words = None
        if words_file is not None:
            # whisper ishlamaydi: tasdiqlangan so'zlar ishlatiladi
            data = C.read_json(words_file, "So'zlar fayli")
            words = data.get("words") if isinstance(data, dict) else None
            if not isinstance(words, list) or not all(isinstance(w, dict) and {"start", "end", "word"} <= set(w) for w in words):
                raise C.MontajError(f"{words_file} so'zlar fayli emas (ichida start/end/word li \"words\" ro'yxati kerak).")
            issues = T.check_words(words, src["duration"])
            if issues:
                T.print_issues(issues)
                raise C.MontajError("So'zlar fayli bu videoga mos emas yoki vaqtlari buzilgan (yuqoridagi ro'yxat). "
                                    "To'g'ri faylni bering yoki --words siz ishga tushiring.")
            review = sum(1 for w in words if w.get("needs_review"))
            C.info(f"\n=== 1/4 Transkripsiya o'rniga tayyor so'zlar: {words_file.name} ({len(words)} so'z"
                   + (f", {review} tasi 'tekshirilsin' belgili" if review else "") + ") ===")
        elif want_subs or (want_cut and style["cut"].get("remove_repeats", True) and not args.no_repeats):
            cached = work / "orig.words.json"
            if (not args.force and cached.is_file() and state.get("fingerprint") == fingerprint(video)
                    and state.get("whisper") == whisper_opts):
                # faqat kesish sozlamasi o'zgargan: transkripsiya qayta qilinmaydi
                words = C.read_json(cached).get("words", [])
                C.info(f"\n=== 1/4 Transkripsiya: oldingi natija ishlatiladi ({len(words)} so'z) ===")
            elif src["has_audio"]:
                t = step("1/4 Transkripsiya (whisper)")
                tr = T.transcribe_video(video, style, work)
                words = tr["words"]
                C.info(f"  Til: {tr['language']}, so'zlar: {len(words)}")
                done(t)
            else:
                C.warn("Videoda ovoz yo'q: transkripsiya va subtitr o'tkazib yuboriladi.")
                words = []
        else:
            C.info("\n=== 1/4 Transkripsiya o'tkazib yuborildi ===")

        if words:
            T.print_squeezed(T.squeezed_runs(words))

        # ---- lug'at: doim xato yoziladigan so'zlar to'g'rilanadi (vaqtlar o'zgarmaydi)
        if gloss and words:
            words, changed = G.apply_to_words(words, gloss)
            if changed:
                C.info(f"\n  Lug'at bo'yicha {len(changed)} ta joy to'g'rilandi: "
                       + ", ".join(f"{old} -> {new}" for _, old, new in changed[:12])
                       + (" ..." if len(changed) > 12 else ""))

        # ---- 2. kesish
        if want_cut:
            t = step("2/4 Jim joylar va takrorlarni kesish")
            res = auto_cut.cut_video(video, style, words, work, apply=True,
                                     silence_db=args.silence_db, no_repeats=args.no_repeats,
                                     remove=remove, trim=trim[0] if trim else None, no_silence=args.no_silence,
                                     protect=protect)
            cut_video, cut_words = Path(res["video"]), res["words"]
            done(t)
        else:
            C.info("\n=== 2/4 Kesish o'tkazib yuborildi ===")
            cut_video, cut_words = video, words
            if words is not None:
                C.write_json({"source": str(video), "words": words}, work / "cut.words.json")

        # ---- skript bo'yicha matn: so'zlar skriptdan, vaqtlar whisperdan
        (work / "script.notes.json").unlink(missing_ok=True)
        if script_file and want_subs and cut_words:
            t = step("Skript matnini nutq vaqtlariga tekislash")
            import script_align as SA
            aligned = SA.align(cut_words, SA.read_script_file(script_file))
            SA.print_report(aligned)
            C.write_json({"source": str(video), "words": cut_words}, work / "cut.whisper.words.json")
            cut_words = aligned["words"]
            C.write_json({"source": str(video), "script": str(script_file), "words": cut_words},
                         work / "cut.words.json")
            C.write_json({"script": str(script_file), "notes": aligned["notes"], "report": aligned["report"]},
                         work / "script.notes.json")
            done(t)
        elif script_file and want_subs:
            C.warn("Skript berilgan, lekin videoda nutq topilmadi: skript ishlatilmadi.")

        # tekshiriladigan subtitr fayli (foydalanuvchi shuni tahrir qiladi)
        if subs_srt.exists():  # oldingi (ehtimol qo'lda tuzatilgan) matn yo'qolmasin
            subs_srt.replace(work / "subs.prev.srt")
        if want_subs and cut_words:
            C.write_srt(C.words_to_cues(cut_words, C.cue_style(style)), subs_srt)
        C.write_json({"fingerprint": fingerprint(video), "opts": opts, "cut_video": str(cut_video),
                      "whisper": whisper_opts}, state_path)

    elements_file = Path(args.elements) if args.elements else (work / "elements.json")
    if args.elements:
        C.need_file(elements_file, "elements.json")
    elif not elements_file.is_file():
        elements_file = None
    cuts_file = work / "cuts.json"
    cuts = C.read_json(cuts_file) if (cuts_file.is_file() and cut_video != video) else None

    # ---- tez ko'rish: faqat rasmlar (tasdiq kerak emas, video yozilmaydi)
    if args.prepare_only:
        if want_subs and subs_srt.is_file():
            S.print_cues(C.parse_srt(subs_srt))
            save_result("need_approval", subs=str(subs_srt))
            C.info(f"MATN TAYYOR, TASDIQ KUTILMOQDA: {subs_srt}")
            return EXIT_NEED_APPROVAL
        save_result("prepared", subs=None)
        C.info("TAYYORLANDI: nutq/subtitr yo'q, render bajarilmadi.")
        return 0
    if args.stills:
        if engine != "motion":
            raise C.MontajError("--stills faqat motion dvigateli bilan ishlaydi (captions.engine: motion).")
        import compose as CP
        try:
            times = [float(x) for x in args.stills.split(",") if x.strip()]
        except ValueError:
            raise C.MontajError("--stills uchun vergul bilan ajratilgan sonlar kerak, masalan: 1.5,4,9.2") from None
        words_file = work / "cut.words.json"
        res = CP.compose(cut_video, None, style, subs_srt if (want_subs and subs_srt.is_file()) else None,
                         C.read_json(words_file).get("words", []) if words_file.is_file() else None,
                         cuts, elements_file, stills=times, stills_out=work / "stills.jpg")
        C.info(f"\nRASM TAYYOR ({res['count']} kadr): {res['stills']}")
        for note in res.get("notes") or []:
            C.warn(note)
        save_result("stills", stills=res["stills"], notes=res.get("notes") or [])
        return 0

    # ---- 3. subtitr: tasdiq va ASS
    subs_ass = None
    subs_ok = False
    if want_subs and subs_srt.is_file():
        t = step("3/4 Subtitr")
        cues = C.parse_srt(subs_srt)
        S.print_cues(cues)
        words_file = work / "cut.words.json"
        cut_words = C.read_json(words_file).get("words", []) if words_file.is_file() else []
        low = T.low_confidence_words(cut_words, float(style["whisper"].get("low_confidence", 0.5)))
        notes_file = work / "script.notes.json"
        if notes_file.is_file():
            rep_ = C.read_json(notes_file).get("report", {})
            C.info(f"\n  Matn skriptdan olingan ({rep_.get('coverage', 0):.0%} so'z nutqda aniq topildi)."
                   + (" Quyidagi so'zlar boshqacha eshitilgan: matni skriptdagidek, vaqti taxminiy." if low else ""))
        review = [w for w in cut_words if w.get("needs_review")]
        if review:
            C.info("\n  'Tekshirilsin' deb belgilangan joylar (foydalanuvchidan so'rang): "
                   + ", ".join(f"{w['word']}@{C.fmt_time(w['start'])}" for w in review[:40]))
        if low:
            C.info("\n  Ishonchi past so'zlar (ayniqsa shularni tekshiring): "
                   + ", ".join(f"{w['word']}@{C.fmt_time(w['start'])}" for w in low[:40]))
        approved = args.approve_subs
        if approved and not resume:
            # matn hozirgina yaratildi, uni hali hech kim ko'rmagan: tasdiq hisobga olinmaydi
            C.warn("--approve-subs faqat matn ko'rsatilgandan KEYINGI ishga tushirishda ishlaydi.")
            approved = False
        if not approved:
            approved = bool(C.confirm(f"\nMatnni tuzatish kerak bo'lsa hozir shu faylni tahrir qilib saqlang: "
                                      f"{subs_srt}\nMatn to'g'rimi? Videoga yozaymi? [y/N]: "))
        if not approved:
            C.info(f"\nTASDIQ KERAK. Subtitr matni: {subs_srt}\n"
                   "  1) Yuqoridagi matnni foydalanuvchiga ko'rsating, xatolarni shu faylda tuzating.\n"
                   "  2) Tasdiqdan keyin shu buyruqni --approve-subs bilan qayta ishga tushiring.")
            save_result("need_approval", subs=str(subs_srt))
            return EXIT_NEED_APPROVAL
        subs_ok = True
        if engine == "ass":
            subs_ass = S.make_ass(cut_video, subs_srt, work / "subs.ass", style, cut_words,
                                  target_size=(style["video"]["width"], style["video"]["height"]))
            C.info(f"  ASS: {subs_ass}")
        done(t)
    elif want_subs:
        C.info("\n=== 3/4 Subtitr: videoda nutq topilmadi, subtitr qo'yilmaydi ===")
    else:
        C.info("\n=== 3/4 Subtitr o'tkazib yuborildi ===")

    # ---- 4. render
    music = Path(args.music) if args.music else None
    if engine == "motion":
        t = step("4/4 Render (motion: zoom, subtitr animatsiyasi, elementlar)")
        import compose as CP
        words_file = work / "cut.words.json"
        meta = CP.compose(cut_video, out, style, subs_srt if subs_ok else None,
                          C.read_json(words_file).get("words", []) if words_file.is_file() else None,
                          cuts, elements_file, music, True if args.nvenc else None, draft=args.draft)
    else:
        t = step("4/4 Render")
        meta = R.render(cut_video, out, style, subs_ass, music, True if args.nvenc else None)
    done(t)

    C.info("\n=== Tekshiruv (ffprobe) ===")
    C.info(f"  Fayl:        {out}")
    render_style = CP.draft_style(style) if args.draft else style
    C.info(f"  O'lcham:     {meta['width']}x{meta['height']} (kutilgan {render_style['video']['width']}x{render_style['video']['height']})")
    C.info(f"  Davomiylik:  {meta['duration']:.2f}s (asl video {src['duration']:.2f}s"
           + (", oxirgi kadr qo'shilgan" if style.get("endcard", {}).get("enabled") and engine == "motion" else "") + ")")
    C.info(f"  FPS:         {meta['fps']:g}")
    C.info(f"  Ovoz:        {'bor' if meta['has_audio'] else 'YOQ'} ({meta['acodec']}, {meta['sample_rate']} Hz)")
    C.info(f"  Hajm:        {meta['size_bytes'] / 1e6:.1f} MB")
    if engine == "motion":
        CP.print_report(meta, style)
    # ishlatilgan stok/AI rasmlar uchun mualliflik ro'yxati
    credits = []
    if elements_file and engine == "motion":
        import images as IM
        credits = IM.collect_credits(elements_file, C.brand_dir(style))
        if credits:
            text = IM.credits_text(credits)
            (work / "credits.txt").write_text(text + "\n", encoding="utf-8")
            C.info("\n=== Rasm manbalari ===\n" + text)
    save_result("draft" if args.draft else "done", output=str(out), notes=meta.get("notes") or [], checks=meta.get("checks") or [],
                credits=[{"file": c.get("file"), "credit": c.get("credit"),
                          "attribution_required": bool(c.get("attribution_required")),
                          "ai_generated": bool(c.get("ai_generated"))} for c in credits])
    C.info(f"\nTAYYOR ({time.time() - total:.1f}s): {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
