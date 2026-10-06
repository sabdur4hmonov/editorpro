"""SRT dan chiroyli subtitr (ASS) yasaydi va videoga yozadi.

Shrift, o'lcham, rang, kontur va joy style/style.json dan olinadi.

Misol:
    python scripts/subtitles.py temp/video/cut.mp4 temp/video/subs.srt --ass-only
    python scripts/subtitles.py temp/video/cut.mp4 temp/video/subs.srt --approved -o output/video_sub.mp4

MUHIM: matn videoga yozilishidan oldin foydalanuvchi uni ko'rib tasdiqlashi shart
(o'zbek tilida whisper xato qiladi). --approved faqat tasdiqdan keyin beriladi.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import common as C

ALIGN = {"bottom": 2, "center": 5, "middle": 5, "top": 8}
EXIT_NEED_APPROVAL = 3


def ass_color(hex_color: str, alpha: int = 0) -> str:
    """#RRGGBB -> ASS formati &HAABBGGRR."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})", str(hex_color).strip())
    if not m:
        raise C.MontajError(f"Rang noto'g'ri: {hex_color!r}. To'g'ri ko'rinish: #RRGGBB (masalan #FFE600).")
    r, g, b = m.groups()
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(sec: float) -> str:
    cs = int(round(max(0.0, sec) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def clean_text(text: str, uppercase: bool) -> str:
    text = re.sub(r"<[^>]+>", "", text)                 # SRT ichidagi <i>, <b> teglari
    text = C.strip_markup(text)                         # motion dvigateli belgilari (*, **, !!, _)
    text = text.replace("{", "(").replace("}", ")").replace("\\", "/")
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper() if uppercase else text


def word_times(cue: dict, tokens: list, words: list | None) -> list:
    """Bo'lak ichidagi har bir so'zning boshlanish vaqti.

    Haqiqiy so'z vaqtlari mos kelsa shular olinadi, aks holda so'z uzunligiga qarab taqsimlanadi.
    """
    if words:
        inside = [w for w in words if cue["start"] - 0.02 <= (w["start"] + w["end"]) / 2 <= cue["end"] + 0.02]
        if len(inside) == len(tokens):
            starts = [max(cue["start"], min(w["start"], cue["end"])) for w in inside]
            starts[0] = cue["start"]
            if all(b > a for a, b in zip(starts, starts[1:])):
                return starts
    total = sum(len(t) for t in tokens) or 1
    starts, pos = [], cue["start"]
    for t in tokens:
        starts.append(pos)
        pos += (cue["end"] - cue["start"]) * len(t) / total
    return starts


def build_ass(cues: list, style: dict, play_w: int, play_h: int, words: list | None = None) -> str:
    """Subtitr bo'laklaridan ASS matnini yasaydi. O'lchamlar video balandligiga moslab masshtablanadi."""
    sub = style["subtitles"]
    ref_h = float(C.style_get(style, "video", "height"))
    k = play_h / ref_h if ref_h else 1.0
    position = str(sub.get("position", "bottom")).lower()
    if position not in ALIGN:
        raise C.MontajError(f"subtitles.position noto'g'ri: {position!r}. Mumkin: bottom, center, top.")
    font = str(C.style_get(style, "subtitles", "font")).replace(",", " ")
    primary = ass_color(sub.get("primary_color", "#FFFFFF"))
    outline = ass_color(sub.get("outline_color", "#000000"))
    back = ass_color("#000000", alpha=0x80)
    hl_on = bool(sub.get("highlight_enabled", False))
    hl = ass_color(sub.get("highlight_color", "#FFE600")) if hl_on else primary
    hl_tag, base_tag = "{\\c" + hl[:2] + hl[4:] + "&}", "{\\c" + primary[:2] + primary[4:] + "&}"
    pop = "{\\fscx88\\fscy88\\t(0,90,\\fscx100\\fscy100)}" if sub.get("pop_animation", False) else ""
    uppercase = bool(sub.get("uppercase", False))

    head = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {play_w}", f"PlayResY: {play_h}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: None", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Main,{font},{size},{pc},{pc},{oc},{bc},{bold},0,0,0,100,100,0,0,1,{ow},{sh},{al},{mh},{mh},{mv},1".format(
            font=font, size=max(8, round(float(sub.get("font_size", 84)) * k)), pc=primary, oc=outline, bc=back,
            bold=-1 if sub.get("bold", True) else 0,
            ow=round(float(sub.get("outline_width", 6)) * k, 1), sh=round(float(sub.get("shadow", 2)) * k, 1),
            al=ALIGN[position], mh=round(float(sub.get("margin_h", 90)) * k),
            mv=0 if ALIGN[position] == 5 else round(float(sub.get("margin_v", 460)) * k)),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = []
    for cue in cues:
        text = clean_text(cue["text"], uppercase)
        if not text:
            continue
        tokens = text.split(" ")
        if not hl_on or len(tokens) < 2:
            body = pop + (hl_tag + text if hl_on else text)
            events.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Main,,0,0,0,,{body}")
            continue
        starts = word_times(cue, tokens, words) + [cue["end"]]
        for i in range(len(tokens)):
            if starts[i + 1] - starts[i] < 0.01:
                continue
            body = " ".join((hl_tag + t + base_tag) if j == i else t for j, t in enumerate(tokens))
            events.append(f"Dialogue: 0,{ass_time(starts[i])},{ass_time(starts[i + 1])},Main,,0,0,0,,"
                          f"{pop if i == 0 else ''}{body}")
    return "\n".join(head + events) + "\n"


def make_ass(video: Path, srt: Path, ass_path: Path, style: dict, words: list | None = None,
             target_size: tuple | None = None) -> Path:
    """SRT dan ASS fayl yasaydi. target_size berilmasa videoning o'z o'lchami olinadi."""
    cues = C.parse_srt(srt)
    if not cues:
        raise C.MontajError(f"SRT faylda subtitr yo'q: {srt}")
    if target_size:
        w, h = target_size
    else:
        meta = C.ffprobe_info(video)
        w, h = meta["width"], meta["height"]
    ass_path = C.guard_output(ass_path, video)
    ass_path.write_text(build_ass(cues, style, int(w), int(h), words), encoding="utf-8")
    return ass_path


def subs_filter(ass_path: Path, style: dict) -> str:
    """FFmpeg 'subtitles' filtri matni. Windows yo'l muammosi common.filter_path da hal qilingan.

    FFmpeg loyiha papkasidan (cwd=ROOT) ishga tushiriladi, shuning uchun yo'l nisbiy bo'lib,
    ichida disk harfi (D:) va teskari slesh qolmaydi.
    """
    if not C.has_filter("subtitles"):
        raise C.MontajError("Bu FFmpeg da 'subtitles' filtri yo'q (libass siz yig'ilgan). "
                            "To'liq versiyani o'rnating: winget install Gyan.FFmpeg")
    text = "subtitles=filename=" + C.filter_path(ass_path, cwd=C.ROOT)
    fonts_dir = style["subtitles"].get("fonts_dir")
    if fonts_dir:
        fd = (C.ROOT / fonts_dir) if not Path(fonts_dir).is_absolute() else Path(fonts_dir)
        if fd.is_dir() and any(f.suffix.lower() in (".ttf", ".otf", ".ttc") for f in fd.iterdir()):
            text += ":fontsdir=" + C.filter_path(fd, cwd=C.ROOT)
    return text


def burn(video: Path, ass_path: Path, out_path: Path, style: dict) -> Path:
    """Subtitrni videoga yozadi (ovoz o'zgarmaydi)."""
    out_path = C.guard_output(out_path, video)
    v = style["video"]
    cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
           "-i", Path(video).resolve(), "-vf", subs_filter(ass_path, style),
           "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", str(v.get("preset", "medium")),
           "-crf", str(v.get("crf", 20)), "-pix_fmt", "yuv420p", "-c:a", "copy",
           "-movflags", "+faststart", out_path]
    C.run(cmd, cwd=C.ROOT)
    return out_path


def print_cues(cues: list) -> None:
    C.info("\nSubtitr matni (tekshiring):")
    for i, cue in enumerate(cues, 1):
        C.info(f"  {i:>3}  {C.fmt_time(cue['start'])} - {C.fmt_time(cue['end'])}  {cue['text']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="SRT dan uslubli subtitr yasab videoga yozadi.")
    ap.add_argument("video", help="Video fayl")
    ap.add_argument("srt", help="SRT fayl (tekshirilgan matn)")
    ap.add_argument("-o", "--output", help="Natija video (standart: output/<nom>_sub.mp4)")
    ap.add_argument("--ass", help="ASS fayl yo'li (standart: temp/<video nomi>/subs.ass)")
    ap.add_argument("--ass-only", action="store_true", help="Faqat ASS fayl yasa, videoga yozma")
    ap.add_argument("--words", help="words.json (so'zni ajratib ko'rsatish vaqtlari aniqroq bo'ladi)")
    ap.add_argument("--approved", action="store_true",
                    help="Foydalanuvchi matnni ko'rib tasdiqlagan. Busiz videoga yozilmaydi")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    video = C.need_file(args.video, "Video")
    srt = C.need_file(args.srt, "SRT fayl")
    words = C.read_json(args.words, "So'zlar fayli").get("words") if args.words else None
    ass_path = Path(args.ass) if args.ass else C.job_dir(video) / "subs.ass"

    cues = C.parse_srt(srt)
    print_cues(cues)
    make_ass(video, srt, ass_path, style, words)
    C.info(f"\nASS fayl: {ass_path}")
    if args.ass_only:
        return 0

    if not args.approved:
        answer = C.confirm("\nMatn to'g'rimi? Videoga yozaymi? [y/N]: ")
        if answer is None:
            C.info("\nTASDIQ KERAK: yuqoridagi matnni foydalanuvchiga ko'rsating. "
                   "U tasdiqlagach, shu buyruqni --approved bilan qayta ishga tushiring.")
            return EXIT_NEED_APPROVAL
        if not answer:
            C.info(f"To'xtatildi. Matnni {srt} faylida tuzating va qayta ishga tushiring.")
            return EXIT_NEED_APPROVAL

    out = Path(args.output) if args.output else C.OUTPUT_DIR / f"{C.output_stem(video.stem)}_sub.mp4"
    burn(video, ass_path, out, style)
    src = C.ffprobe_info(video)
    meta, problems = C.verify_video(out, src["width"], src["height"], src["duration"], need_audio=src["has_audio"])
    C.info(f"Tayyor: {out} ({meta['width']}x{meta['height']}, {meta['duration']:.2f}s)")
    if problems:
        raise C.MontajError("Natija tekshiruvdan o'tmadi: " + "; ".join(problems))
    return 0


if __name__ == "__main__":
    C.run_main(main)
