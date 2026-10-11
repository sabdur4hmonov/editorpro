"""Jim joylarni va takrorlangan gaplarni topib kesadi.

Avval kesish ro'yxatini ko'rsatadi. --apply berilsagina videoni kesadi.

Misol:
    python scripts/auto_cut.py input/video.mp4                 # faqat ro'yxat
    python scripts/auto_cut.py input/video.mp4 --apply         # ro'yxat + kesish
    python scripts/auto_cut.py input/video.mp4 --words temp/video/orig.words.json --apply

Natija (standart): temp/<video nomi>/cut.mp4, cuts.json, (so'zlar berilsa) cut.words.json va cut.srt
Asl video o'zgarmaydi.
"""
from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path

import common as C


# ---------------------------------------------------------------- jim joylar

def detect_silences(video: Path, noise_db: float, min_silence: float, duration: float) -> list:
    """ffmpeg silencedetect yordamida jim oraliqlarni topadi: [(boshi, oxiri)]."""
    proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-i", video, "-vn",
                  "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"])
    silences, start = [], None
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
            continue
        m = re.search(r"silence_end:\s*(-?[\d.]+)", line)
        if m and start is not None:
            silences.append((start, min(duration, float(m.group(1)))))
            start = None
    if start is not None:  # video oxirigacha jim
        silences.append((start, duration))
    return [(s, e) for s, e in silences if e > s]


def silence_removals(silences: list, duration: float, padding: float) -> list:
    """Jim oraliqlardan olib tashlanadigan qismlarni hisoblaydi (nutq atrofida zaxira qoldirib)."""
    removals = []
    for s, e in silences:
        rs = 0.0 if s <= 0.05 else s + padding
        re_ = duration if e >= duration - 0.05 else e - padding
        if re_ - rs >= 0.1:
            removals.append({"start": rs, "end": re_, "reason": "jim"})
    return removals


def complement(removals: list, duration: float) -> list:
    """Olib tashlanadigan oraliqlardan qoladigan (saqlanadigan) oraliqlarni chiqaradi."""
    keep, pos = [], 0.0
    for r in sorted(removals, key=lambda x: x["start"]):
        if r["start"] > pos:
            keep.append([pos, min(r["start"], duration)])
        pos = max(pos, r["end"])
    if pos < duration:
        keep.append([pos, duration])
    return [k for k in keep if k[1] - k[0] > 0]


# ---------------------------------------------------------------- takrorlar

def _norm(word: str) -> str:
    return re.sub(r"[^\w]+", "", word.lower().replace("'", "").replace("ʻ", "").replace("’", ""))


def find_repeats(keep: list, words: list, similarity: float) -> list:
    """Qayta aytilgan gaplarni topadi: oldingi (xato) urinish olib tashlanadi, oxirgisi qoladi.

    Har bir saqlanadigan bo'lak (ikki jimlik orasidagi nutq) keyingi 1-2 bo'lak bilan
    solishtiriladi. Agar ikkalasi bir xil so'zlar bilan boshlansa, birinchisi takror hisoblanadi.
    """
    chunks = []
    for ks, ke in keep:
        toks = [w for w in words if ks <= (w["start"] + w["end"]) / 2 < ke]
        chunks.append({"start": ks, "end": ke,
                       "norm": [n for n in (_norm(w["word"]) for w in toks) if n],
                       "text": " ".join(w["word"] for w in toks)})
    removed = []
    for i, a in enumerate(chunks):
        for b in chunks[i + 1:i + 3]:
            n = min(len(a["norm"]), len(b["norm"]))
            if n < 2:
                continue
            ratio = difflib.SequenceMatcher(None, " ".join(a["norm"][:n]), " ".join(b["norm"][:n])).ratio()
            need = 0.95 if n == 2 else similarity
            if ratio >= need:
                removed.append({"start": a["start"], "end": a["end"], "reason": "takror",
                                "text": a["text"], "kept_text": b["text"], "similarity": round(ratio, 2)})
                break
    return removed


# ---------------------------------------------------------------- reja

def parse_ranges(text: str | None) -> list:
    """"10-15,22.5-24" ko'rinishidagi matndan [(10.0, 15.0), (22.5, 24.0)] yasaydi (soniyalarda)."""
    out = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", part)
        if not m or float(m.group(2)) <= float(m.group(1)):
            raise C.MontajError(f"Oraliq noto'g'ri: {part!r}. To'g'ri ko'rinish: 10-15,22.5-24 (soniyalarda, asl video bo'yicha).")
        out.append((float(m.group(1)), float(m.group(2))))
    return out


def subtract_ranges(removals: list, protect: list | None) -> list:
    """Kesiladigan oraliqlardan himoyalangan qismlarni olib tashlaydi (qolgan bo'laklar saqlanadi)."""
    if not protect:
        return removals
    out = []
    for r in removals:
        parts = [(r["start"], r["end"])]
        for ps, pe in protect:
            nxt = []
            for s, e in parts:
                if pe <= s or ps >= e:
                    nxt.append((s, e))
                    continue
                if s < ps:
                    nxt.append((s, ps))
                if pe < e:
                    nxt.append((pe, e))
            parts = nxt
        out += [dict(r, start=s, end=e) for s, e in parts if e - s > 1e-3]
    return out


def build_plan(video: Path, style: dict, words: list | None = None,
               silence_db: float | None = None, min_silence: float | None = None,
               no_repeats: bool = False, remove: list | None = None, trim: tuple | None = None,
               no_silence: bool = False, protect: list | None = None) -> dict:
    """Kesish rejasini tuzadi (hali hech narsa kesilmaydi).

    protect: [(boshi, oxiri)] - jimlik deb kesilmaydigan oraliqlar (masalan nutqsiz mahsulot kadrlari, assemble.py).
    """
    cut = style["cut"]
    meta = C.ffprobe_info(video)
    if not meta["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    duration = meta["duration"]
    fps = float(C.style_get(C.resolve_fps(style, meta=meta), "video", "fps"))
    noise = float(silence_db if silence_db is not None else cut.get("silence_db", -35))
    min_sil = float(min_silence if min_silence is not None else cut.get("min_silence", 0.45))
    padding = float(cut.get("padding", 0.1))
    min_keep = float(cut.get("min_keep", 0.2))

    removals = []
    manual = []
    if trim:  # faqat shu oraliq qoladi
        if trim[0] > 0:
            manual.append({"start": 0.0, "end": min(trim[0], duration), "reason": "qo'lda (trim)"})
        if trim[1] < duration:
            manual.append({"start": trim[1], "end": duration, "reason": "qo'lda (trim)"})
    for s0, e0 in remove or []:
        if s0 < duration:
            manual.append({"start": s0, "end": min(e0, duration), "reason": "qo'lda"})
    if no_silence:
        pass
    elif meta["has_audio"]:
        silences = detect_silences(video, noise, min_sil, duration)
        removals = silence_removals(silences, duration, padding)
    else:
        C.warn("Videoda ovoz yo'q, jim joylarni aniqlab bo'lmaydi. Hech narsa kesilmaydi.")
    removals = subtract_ranges(removals, protect)

    keep = complement(removals, duration)
    # juda qisqa bo'laklar (shovqin, chertish) olib tashlanadi, agar ichida so'z bo'lmasa
    for ks, ke in list(keep):
        has_word = any(ks <= (w["start"] + w["end"]) / 2 < ke for w in (words or []))
        protected = any(ps < ke and ks < pe for ps, pe in (protect or []))
        if ke - ks < min_keep and not has_word and not protected:
            removals.append({"start": ks, "end": ke, "reason": "juda qisqa bo'lak"})
    keep = complement(removals, duration)

    if words and cut.get("remove_repeats", True) and not no_repeats:
        removals += find_repeats(keep, words, float(cut.get("repeat_similarity", 0.85)))
        keep = complement(removals, duration)
    if manual:
        removals += manual
        keep = complement(removals, duration)

    # kadr to'riga moslash: video va ovoz bir xil joydan kesilsin (sinxron buzilmasin)
    snapped = []
    for ks, ke in keep:
        s, e = round(ks * fps) / fps, round(ke * fps) / fps
        if snapped and s <= snapped[-1][1]:
            snapped[-1][1] = max(snapped[-1][1], e)
        elif e - s >= 1.0 / fps:
            snapped.append([s, e])
    removals.sort(key=lambda r: r["start"])
    speed = float(cut.get("speed", 1.0) or 1.0)
    if not 0.5 <= speed <= 2.0:
        raise C.MontajError(f"cut.speed 0.5 va 2.0 orasida bo'lishi kerak (hozir {speed}).")
    return {
        "source": str(video),
        "duration": duration,
        "fps": fps,
        "speed": speed,
        "settings": {"silence_db": noise, "min_silence": min_sil, "padding": padding,
                     "fade_ms": float(cut.get("fade_ms", 15))},
        "keep": [{"start": round(s, 4), "end": round(e, 4)} for s, e in snapped],
        "removed": [{**r, "start": round(r["start"], 3), "end": round(r["end"], 3)} for r in removals],
        "new_duration": round(sum(e - s for s, e in snapped) / speed, 3),
    }


def print_plan(plan: dict) -> None:
    removed = plan["removed"]
    C.info(f"\nKesish ro'yxati: {Path(plan['source']).name}")
    C.info(f"  Sozlama: {plan['settings']['silence_db']} dB dan past, "
           f"{plan['settings']['min_silence']} s dan uzun joylar jim hisoblanadi")
    if not removed:
        C.info("  Kesiladigan joy topilmadi.")
    else:
        C.info(f"  {'#':>3}  {'boshi':>9}  {'oxiri':>9}  {'uzunlik':>7}  sabab")
        for i, r in enumerate(removed, 1):
            line = (f"  {i:>3}  {C.fmt_time(r['start']):>9}  {C.fmt_time(r['end']):>9}  "
                    f"{r['end'] - r['start']:>6.2f}s  {r['reason']}")
            if r["reason"] == "takror":
                line += f"\n         olib tashlanadi: \"{r['text']}\"\n         qoladi:          \"{r['kept_text']}\""
            C.info(line)
    if abs(float(plan.get("speed", 1.0)) - 1.0) > 0.001:
        C.info(f"  Tezlik: {plan['speed']:g}x")
    saved = plan["duration"] - plan["new_duration"]
    pct = (saved / plan["duration"] * 100) if plan["duration"] else 0
    C.info(f"  Jami: {plan['duration']:.2f}s -> {plan['new_duration']:.2f}s "
           f"({saved:.2f}s yoki {pct:.0f}% qisqaradi, {len(plan['keep'])} ta bo'lak qoladi)")


# ---------------------------------------------------------------- qo'llash

def segment_frames(keep: list, out_fps: float) -> list:
    """[(first source frame, frame count)] per kept segment by cumulative rounding (no A/V drift)."""
    acc, frames = 0.0, []
    for seg in keep:
        a = round(acc * out_fps)
        acc += seg["end"] - seg["start"]
        frames.append((round(seg["start"] * out_fps), round(acc * out_fps) - a))
    return frames


def apply_plan(video: Path, plan: dict, out_path: Path, style: dict,
               force_file_graph: bool = False) -> Path:
    """Rejani qo'llaydi: bo'laklarni kesib, yumshoq o'tish bilan ulab, bitta fayl qiladi."""
    keep = plan["keep"]
    if not keep:
        raise C.MontajError("Kesishdan keyin hech narsa qolmadi. silence_db ni pasaytiring (masalan -45).")
    out_path = C.guard_output(out_path, video)
    meta = C.ffprobe_info(video)
    fps = plan["fps"]                                   # boundary grid of the plan (seconds stay as planned)
    out_fps = float(C.resolve_fps(style, meta=meta)["video"]["fps"])
    if str(style.get("video", {}).get("fps", "")).lower() != "source":
        out_fps = float(style["video"]["fps"]) if "fps" in style.get("video", {}) else fps
    fade = max(0.0, float(plan["settings"].get("fade_ms", 15)) / 1000.0)
    # chegaralar kadr to'riga yaxlitlanadi (qo'lda tahrirlangan reja uchun ham)
    keep = [{"start": round(k["start"] * fps) / fps, "end": round(k["end"] * fps) / fps} for k in keep]
    keep = [k for k in keep if k["end"] - k["start"] >= 1.0 / fps - 1e-9]
    if not keep:
        raise C.MontajError("Rejadagi bo'laklar bir kadrdan ham qisqa.")
    n = len(keep)
    parts = [f"[0:v]fps={C.fps_expr(out_fps)},split={n}" + "".join(f"[vs{i}]" for i in range(n))]
    # video frames per segment by cumulative rounding: audio keeps the planned seconds, the picture never
    # drifts more than half an output frame and nothing accumulates (plan grid == output rate: exact frames)
    frames = segment_frames(keep, out_fps)
    if meta["has_audio"]:
        parts.append(f"[0:a]aresample=48000,asplit={n}" + "".join(f"[as{i}]" for i in range(n)))
    for i, seg in enumerate(keep):
        s, e = seg["start"], seg["end"]
        d = e - s
        # fps filtridan keyin vaqt birligi 1 kadr, shuning uchun chegaralar aniq kadrga tushadi
        f0, nf = frames[i]
        parts.append(f"[vs{i}]trim=start_frame={f0}:end_frame={f0 + nf},setpts=PTS-STARTPTS[v{i}]")
        if meta["has_audio"]:
            f = min(fade, d / 4)
            chain = f"[as{i}]atrim=start={s:.6f}:end={e:.6f},asetpts=PTS-STARTPTS"
            if f > 0:
                chain += f",afade=t=in:st=0:d={f:.4f},afade=t=out:st={d - f:.4f}:d={f:.4f}"
            parts.append(chain + f"[a{i}]")
    speed = float(plan.get("speed", 1.0) or 1.0)
    fast = abs(speed - 1.0) > 0.001
    vlab, alab = ("[vc]", "[ac]") if fast else ("[vout]", "[aout]")
    if meta["has_audio"]:
        parts.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1{vlab}{alab}")
    else:
        parts.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0{vlab}")
    if fast:  # butun videoni tezlashtirish/sekinlashtirish (ovoz balandligi o'zgarmaydi)
        parts.append(f"[vc]setpts=PTS/{speed:.4f},fps={C.fps_expr(out_fps)}[vout]")
        if meta["has_audio"]:
            parts.append(f"[ac]atempo={speed:.4f}[aout]")
    graph = ";\n".join(parts)

    crf = int(style["cut"].get("intermediate_crf", 16))
    post = ["-map", "[vout]"]
    if meta["has_audio"]:
        post += ["-map", "[aout]", "-c:a", "aac", "-b:a", "256k"]
    post += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(out_path)]
    C.run_ffmpeg_graph(["-i", str(video)], graph, post, out_path.parent, force_file=force_file_graph)
    return out_path


def remap_words(words: list, keep: list, speed: float = 1.0) -> list:
    """So'z vaqtlarini kesilgan (va tezlashtirilgan) videoning yangi vaqt chizig'iga o'tkazadi."""
    out, offset = [], 0.0
    speed = float(speed or 1.0)
    for seg in keep:
        s, e = seg["start"], seg["end"]
        for w in words:
            mid = (w["start"] + w["end"]) / 2
            if s <= mid < e:
                item = dict(w)
                item["start"] = round((max(s, w["start"]) - s + offset) / speed, 3)
                item["end"] = round((min(e, w["end"]) - s + offset) / speed, 3)
                if item["end"] > item["start"]:
                    out.append(item)
        offset += e - s
    return out


def cut_video(video: Path, style: dict, words: list | None = None, out_dir: Path | None = None,
              apply: bool = True, **plan_kwargs) -> dict:
    """To'liq bosqich: reja -> ko'rsatish -> (apply bo'lsa) kesish va so'zlarni qayta hisoblash."""
    video = C.need_file(video, "Video")
    out_dir = Path(out_dir) if out_dir else C.job_dir(video)
    plan = build_plan(video, style, words, **plan_kwargs)
    print_plan(plan)
    C.write_json(plan, C.guard_output(out_dir / "cuts.json", video))
    result = {"plan": plan, "plan_path": str(out_dir / "cuts.json"), "video": None,
              "words": None, "srt_path": None, "applied": False}
    if not apply:
        return result

    nothing_to_cut = not plan["removed"] and abs(float(plan.get("speed", 1.0)) - 1.0) <= 0.001
    if nothing_to_cut:
        result["video"] = str(video)  # kesadigan joy yo'q: asl fayl keyingi bosqichga o'tadi (nusxa olinmaydi)
        new_words = list(words or [])
    else:
        result["video"] = str(apply_plan(video, plan, out_dir / "cut.mp4", style))
        new_words = remap_words(words or [], plan["keep"], plan.get("speed", 1.0))
    result["applied"] = True
    if words is not None:
        C.write_json({"source": result["video"], "words": new_words}, out_dir / "cut.words.json")
        C.write_srt(C.words_to_cues(new_words, C.cue_style(style)), out_dir / "cut.srt")
        result["words"], result["srt_path"] = new_words, str(out_dir / "cut.srt")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Jim joylar va takrorlarni topib kesadi.")
    ap.add_argument("video", help="Video fayl (masalan input/video.mp4)")
    ap.add_argument("--words", help="transcribe.py chiqargan words.json (takrorlarni topish uchun)")
    ap.add_argument("--apply", action="store_true", help="Ro'yxatni ko'rsatgach, kesishni ham bajar")
    ap.add_argument("--plan", help="Tayyor (tahrirlangan) cuts.json ni qo'llash")
    ap.add_argument("--out-dir", help="Natija papkasi (standart: temp/<video nomi>/)")
    ap.add_argument("--silence-db", type=float, help="Jimlik chegarasi dB (masalan -40). style.json dagini almashtiradi")
    ap.add_argument("--min-silence", type=float, help="Eng qisqa jimlik uzunligi, soniya")
    ap.add_argument("--no-repeats", action="store_true", help="Takrorlarni qidirma")
    ap.add_argument("--no-silence", action="store_true", help="Jim joylarni kesma (faqat qo'lda berilganlar)")
    ap.add_argument("--remove", help="Qo'lda olib tashlanadigan oraliqlar, asl video bo'yicha: 10-15,22.5-24")
    ap.add_argument("--trim", help="Faqat shu oraliq qolsin, asl video bo'yicha: 5-42")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    video = C.need_file(args.video, "Video")
    words = None
    if args.words:
        words = C.read_json(args.words, "So'zlar fayli").get("words", [])

    if args.plan:
        plan = C.read_json(args.plan, "Kesish rejasi")
        if not isinstance(plan.get("keep"), list) or "settings" not in plan:
            raise C.MontajError(f"{args.plan} kesish rejasiga o'xshamaydi (ichida 'keep' va 'settings' yo'q).")
        print_plan(plan)
        out_dir = Path(args.out_dir) if args.out_dir else C.job_dir(video)
        out = apply_plan(video, plan, out_dir / "cut.mp4", style)
        if words is not None:
            new_words = remap_words(words, plan["keep"], plan.get("speed", 1.0))
            C.write_json({"source": str(out), "words": new_words}, out_dir / "cut.words.json")
            C.write_srt(C.words_to_cues(new_words, C.cue_style(style)), out_dir / "cut.srt")
        C.info(f"\nKesilgan video: {out}")
        return 0

    trim = parse_ranges(args.trim)
    if len(trim) > 1:
        raise C.MontajError("--trim uchun bitta oraliq kerak, masalan: 5-42")
    res = cut_video(video, style, words, args.out_dir, apply=args.apply,
                    silence_db=args.silence_db, min_silence=args.min_silence, no_repeats=args.no_repeats,
                    remove=parse_ranges(args.remove), trim=trim[0] if trim else None, no_silence=args.no_silence)
    C.info(f"\nReja saqlandi: {res['plan_path']}")
    if not args.apply:
        C.info("Bu faqat ro'yxat. Kesish uchun shu buyruqqa --apply qo'shing.")
        return 0
    meta, problems = C.verify_video(res["video"], duration=res["plan"]["new_duration"],
                                    need_audio=C.ffprobe_info(video)["has_audio"])
    C.info(f"Kesilgan video: {res['video']} ({meta['duration']:.2f}s)")
    if problems:
        raise C.MontajError("Kesilgan video tekshiruvdan o'tmadi: " + "; ".join(problems))
    return 0


if __name__ == "__main__":
    C.run_main(main)
