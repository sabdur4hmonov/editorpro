"""Butun montajni bitta buyruq bilan bajaradi.

    python scripts/pipeline.py input/video.mp4

Tartib: transcribe -> auto_cut -> (subtitr matnini tasdiqlash) -> subtitles -> render -> tekshiruv

Subtitr matni tasdiqlanmaguncha videoga yozilmaydi:
  1) Birinchi ishga tushirishda matn ko'rsatiladi va skript to'xtaydi (chiqish kodi 3).
  2) Matn temp/<nom>/subs.srt faylida tuzatiladi.
  3) Tasdiqdan keyin:  python scripts/pipeline.py input/video.mp4 --approve-subs
     (oldingi ish qayta bajarilmaydi, tuzatilgan matn ishlatiladi)

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
    ap.add_argument("video", help="Asl video (masalan input/video.mp4)")
    ap.add_argument("-o", "--output", help="Natija (standart: output/<nom>_final.mp4)")
    ap.add_argument("--approve-subs", action="store_true",
                    help="Foydalanuvchi subtitr matnini ko'rib tasdiqladi, davom et")
    ap.add_argument("--no-subs", action="store_true", help="Subtitrsiz (transkripsiya ham qilinmaydi)")
    ap.add_argument("--no-cut", action="store_true", help="Jim joylarni kesma")
    ap.add_argument("--no-repeats", action="store_true", help="Takrorlarni kesma")
    ap.add_argument("--no-silence", action="store_true", help="Jim joylarni kesma (faqat --remove/--trim ishlaydi)")
    ap.add_argument("--remove", help="Qo'lda olib tashlanadigan oraliqlar, asl video bo'yicha: 10-15,22.5-24")
    ap.add_argument("--trim", help="Faqat shu oraliq qolsin, asl video bo'yicha: 5-42")
    ap.add_argument("--music", help="Fon musiqa fayli")
    ap.add_argument("--brand", help="Brend nomi (brands/<nom>/brand.json): shrift, rang, logotip, oxirgi kadr")
    ap.add_argument("--elements", help="Grafik elementlar fayli (standart: temp/<nom>/elements.json, bo'lsa)")
    ap.add_argument("--engine", choices=["motion", "ass", "off"],
                    help="Subtitr dvigateli (style.json: captions.engine ni almashtiradi)")
    ap.add_argument("--stills", help="Render qilmasdan, shu vaqtlardagi kadrlarni rasm qilib ko'rsat: 1.5,4,9")
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
    if args.language:
        style["whisper"]["language"] = args.language
    if args.model:
        style["whisper"]["model"] = args.model
    video = C.need_file(args.video, "Video")
    if video.suffix.lower() not in C.VIDEO_EXTS:
        C.warn(f"{video.suffix} kengaytmasi odatiy video emas, baribir sinab ko'raman.")
    C.need_tool("ffmpeg"), C.need_tool("ffprobe")
    src = C.ffprobe_info(video)
    if not src["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    work = C.job_dir(video)
    out = Path(args.output) if args.output else C.OUTPUT_DIR / f"{C.output_stem(video.stem)}_final.mp4"
    C.guard_output(out, video)
    C.info(f"Video: {video}\n  {src['width']}x{src['height']}, {src['fps']:g} fps, {src['duration']:.2f}s, "
           f"ovoz: {'bor' if src['has_audio'] else 'yoq'}\nIsh papkasi: {work}")

    want_subs = bool(style["subtitles"].get("enabled", True)) and not args.no_subs and engine != "off"
    if style.get("_brand"):
        C.info(f"Brend: {style['_brand']}")
    want_cut = bool(style["cut"].get("enabled", True)) and not args.no_cut
    state_path, subs_srt = work / "job.json", work / "subs.srt"
    state = C.read_json(state_path) if state_path.is_file() else {}
    remove = auto_cut.parse_ranges(args.remove)
    trim = auto_cut.parse_ranges(args.trim)
    if len(trim) > 1:
        raise C.MontajError("--trim uchun bitta oraliq kerak, masalan: 5-42")
    opts = {"subs": want_subs, "cut": want_cut, "no_repeats": args.no_repeats, "no_silence": args.no_silence,
            "silence_db": args.silence_db, "language": style["whisper"]["language"],
            "model": style["whisper"]["model"], "remove": args.remove or "", "trim": args.trim or ""}
    whisper_opts = {"language": style["whisper"]["language"], "model": style["whisper"]["model"]}
    resume = (not args.force and state.get("fingerprint") == fingerprint(video)
              and state.get("opts") == opts and Path(state.get("cut_video", "")).is_file())

    if resume:
        C.info("\nOldingi natija topildi: transkripsiya va kesish qayta bajarilmaydi (--force bilan boshidan).")
        cut_video = Path(state["cut_video"])
    else:
        # ---- 1. transkripsiya
        words = None
        if want_subs or (want_cut and style["cut"].get("remove_repeats", True) and not args.no_repeats):
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

        # ---- 2. kesish
        if want_cut:
            t = step("2/4 Jim joylar va takrorlarni kesish")
            res = auto_cut.cut_video(video, style, words, work, apply=True,
                                     silence_db=args.silence_db, no_repeats=args.no_repeats,
                                     remove=remove, trim=trim[0] if trim else None, no_silence=args.no_silence)
            cut_video, cut_words = Path(res["video"]), res["words"]
            done(t)
        else:
            C.info("\n=== 2/4 Kesish o'tkazib yuborildi ===")
            cut_video, cut_words = video, words
            if words is not None:
                C.write_json({"source": str(video), "words": words}, work / "cut.words.json")

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
        if low:
            C.info("\n  Whisper ishonchi past so'zlar (ayniqsa shularni tekshiring): "
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
                          cuts, elements_file, music, True if args.nvenc else None)
    else:
        t = step("4/4 Render")
        meta = R.render(cut_video, out, style, subs_ass, music, True if args.nvenc else None)
    done(t)

    C.info("\n=== Tekshiruv (ffprobe) ===")
    C.info(f"  Fayl:        {out}")
    C.info(f"  O'lcham:     {meta['width']}x{meta['height']} (kutilgan {style['video']['width']}x{style['video']['height']})")
    C.info(f"  Davomiylik:  {meta['duration']:.2f}s (asl video {src['duration']:.2f}s"
           + (", oxirgi kadr qo'shilgan" if style.get("endcard", {}).get("enabled") and engine == "motion" else "") + ")")
    C.info(f"  FPS:         {meta['fps']:g}")
    C.info(f"  Ovoz:        {'bor' if meta['has_audio'] else 'YOQ'} ({meta['acodec']}, {meta['sample_rate']} Hz)")
    C.info(f"  Hajm:        {meta['size_bytes'] / 1e6:.1f} MB")
    C.info(f"\nTAYYOR ({time.time() - total:.1f}s): {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
