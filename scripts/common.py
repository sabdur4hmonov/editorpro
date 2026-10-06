"""Umumiy yordamchi funksiyalar: yo'llar, style.json, ffmpeg/ffprobe, SRT.

Bu faylni boshqa skriptlar import qiladi. O'zi alohida ishga tushirilmaydi.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_PATH = ROOT / "style" / "style.json"
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TEMP_DIR = ROOT / "temp"
SAMPLES_DIR = ROOT / "samples"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
# Windows buyruq qatori chegarasi ~32 ming belgi. Undan uzun filtr grafigi faylga yoziladi.
MAX_INLINE_GRAPH = 20000


class MontajError(Exception):
    """Foydalanuvchiga tushunarli xato."""


# ---------------------------------------------------------------- konsol

def setup_console() -> None:
    """Windows konsolida o'zbek/rus harflari xato bermasligi uchun UTF-8 yoqiladi."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def info(msg: str) -> None:
    print(msg, flush=True)


def warn(msg: str) -> None:
    print(f"[OGOHLANTIRISH] {msg}", flush=True)


def run_main(main_func) -> None:
    """Skriptning main() funksiyasini ishga tushiradi va xatoni chiroyli ko'rsatadi."""
    setup_console()
    try:
        code = main_func()
    except MontajError as exc:
        print(f"\n[XATO] {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[TO'XTATILDI] Foydalanuvchi to'xtatdi.", file=sys.stderr)
        sys.exit(130)
    sys.exit(code or 0)


# ---------------------------------------------------------------- style.json

def load_style(path: str | Path | None = None) -> dict:
    """style/style.json ni o'qiydi. Fayl yo'q yoki buzuq bo'lsa aniq xato beradi."""
    p = Path(path) if path else STYLE_PATH
    if not p.is_file():
        raise MontajError(f"Uslub fayli topilmadi: {p}\nstyle/style.json bo'lishi shart.")
    try:
        style = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise MontajError(
            f"{p} fayli JSON sifatida buzuq: {exc.lineno}-qator, {exc.colno}-ustun: {exc.msg}"
        ) from exc
    for section in ("video", "audio", "cut", "subtitles", "whisper"):
        if not isinstance(style.get(section), dict):
            raise MontajError(f"{p} ichida \"{section}\" bo'limi yo'q yoki noto'g'ri.")
    return style


def style_get(style: dict, section: str, key: str):
    """style.json dan qiymat oladi, yo'q bo'lsa qaysi kalit yo'qligini aytadi."""
    try:
        return style[section][key]
    except KeyError:
        raise MontajError(
            f"style/style.json da \"{section}.{key}\" qiymati yo'q. Uni qo'shing."
        ) from None


# ---------------------------------------------------------------- yo'llar

def is_inside(path: Path, parent: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def guard_output(path: str | Path, source: str | Path | None = None) -> Path:
    """Natija fayli input/ yoki samples/ ichiga yozilmasligini kafolatlaydi."""
    p = Path(path).resolve()
    for protected in (INPUT_DIR, SAMPLES_DIR):
        if is_inside(p, protected):
            raise MontajError(
                f"Natijani {protected.name}/ ichiga yozish taqiqlangan: {p}\n"
                "Natija faqat output/ (yoki oraliq fayllar uchun temp/) ga yoziladi."
            )
    if source is not None and p == Path(source).resolve():
        raise MontajError(f"Natija fayli asl fayl bilan bir xil bo'lishi mumkin emas: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def need_file(path: str | Path, what: str = "Fayl") -> Path:
    p = Path(path)
    if not p.is_file():
        raise MontajError(f"{what} topilmadi: {p}")
    return p.resolve()


def slugify(name: str) -> str:
    """Fayl nomidan xavfsiz papka nomi yasaydi (faqat lotin harf, raqam, - va _).

    Nomda lotin bo'lmagan harflar (masalan kirill) bo'lsa, ikki xil fayl bir xil nomga
    tushib qolmasligi uchun oxiriga qisqa xesh qo'shiladi.
    """
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:60] or "video"
    if any(ord(ch) > 127 for ch in name):
        slug += "_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:6]
    return slug


def output_stem(name: str) -> str:
    """Natija fayli uchun nom: asl nom saqlanadi, faqat Windows'da taqiqlangan belgilar almashtiriladi."""
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip(" .")
    return stem or "video"


def job_dir(video: str | Path) -> Path:
    """Har bir video uchun temp/ ichida alohida ish papkasi."""
    d = TEMP_DIR / slugify(Path(video).stem)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- jarayonlar

def need_tool(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise MontajError(
            f"\"{name}\" topilmadi. FFmpeg o'rnatilmagan yoki PATH da yo'q.\n"
            "O'rnatish: winget install Gyan.FFmpeg  (keyin terminalni yopib qayta oching)"
        )
    return exe


def run(cmd: list, cwd: str | Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Buyruqni ishga tushiradi. Xato bo'lsa oxirgi qatorlarini ko'rsatadi."""
    cmd = [str(c) for c in cmd]
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        raise MontajError(f"Dastur topilmadi: {cmd[0]}") from None
    if check and proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-15:])
        raise MontajError(
            f"Buyruq xato bilan tugadi (kod {proc.returncode}): {Path(cmd[0]).name}\n"
            f"--- oxirgi qatorlar ---\n{tail}"
        )
    return proc


_FFMPEG_MAJOR: list = []


def ffmpeg_major() -> int | None:
    """FFmpeg asosiy versiyasi (masalan 7). Aniqlab bo'lmasa None."""
    if not _FFMPEG_MAJOR:
        out = run([need_tool("ffmpeg"), "-hide_banner", "-version"]).stdout
        m = re.search(r"ffmpeg version\s+n?(\d+)\.\d+", out)
        _FFMPEG_MAJOR.append(int(m.group(1)) if m else None)
    return _FFMPEG_MAJOR[0]


def has_filter(name: str) -> bool:
    out = run([need_tool("ffmpeg"), "-hide_banner", "-filters"]).stdout
    return re.search(rf"^\s*\S+\s+{re.escape(name)}\s", out, re.M) is not None


def has_encoder(name: str) -> bool:
    out = run([need_tool("ffmpeg"), "-hide_banner", "-encoders"]).stdout
    return re.search(rf"^\s*\S+\s+{re.escape(name)}\s", out, re.M) is not None


def run_ffmpeg_graph(pre: list, graph: str, post: list, workdir: Path,
                     cwd: Path | None = None, force_file: bool = False) -> subprocess.CompletedProcess:
    """filter_complex grafigi bilan ffmpeg ni ishga tushiradi.

    Qisqa grafik buyruq qatorida beriladi. Uzun grafik faylga yoziladi:
    FFmpeg 7+ da "-/filter_complex fayl", eskisida "-filter_complex_script fayl"
    (bu eski variant FFmpeg 9 da olib tashlangan).
    """
    ffmpeg = need_tool("ffmpeg")
    base = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    if len(graph) <= MAX_INLINE_GRAPH and not force_file:
        return run(base + pre + ["-filter_complex", graph] + post, cwd=cwd)

    workdir.mkdir(parents=True, exist_ok=True)
    script = workdir / "filter_graph.txt"
    script.write_text(graph, encoding="utf-8")
    major = ffmpeg_major()
    new_style = ["-/filter_complex", str(script)]
    old_style = ["-filter_complex_script", str(script)]
    order = [old_style, new_style] if (major is not None and major < 7) else [new_style, old_style]
    last_err: MontajError | None = None
    for variant in order:
        try:
            return run(base + pre + variant + post, cwd=cwd)
        except MontajError as exc:
            last_err = exc
            text = str(exc)
            if "Unrecognized option" in text or "Option not found" in text or "Error splitting" in text:
                continue  # bu ffmpeg versiyasi shu variantni tanimaydi, ikkinchisini sinaymiz
            raise
    raise last_err  # type: ignore[misc]


# ---------------------------------------------------------------- ffprobe

def ffprobe_info(path: str | Path) -> dict:
    """Video haqida asosiy ma'lumot: davomiylik, o'lcham, fps, ovoz."""
    p = need_file(path, "Video")
    proc = run([need_tool("ffprobe"), "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", str(p)])
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise MontajError(f"ffprobe natijasini o'qib bo'lmadi: {p}") from None
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"
              and s.get("disposition", {}).get("attached_pic", 0) != 1), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    def _f(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _rate(text) -> float:
        try:
            num, den = str(text).split("/")
            return float(num) / float(den) if float(den) else 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0

    duration = _f(fmt.get("duration")) or _f((v or {}).get("duration")) or _f((a or {}).get("duration"))
    out = {
        "path": str(p),
        "duration": round(duration, 3),
        "size_bytes": int(_f(fmt.get("size"))),
        "has_video": v is not None,
        "has_audio": a is not None,
        "width": 0, "height": 0, "fps": 0.0, "rotation": 0,
        "vcodec": None, "acodec": None, "sample_rate": 0, "channels": 0,
    }
    if v:
        rotation = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rotation = int(_f(sd.get("rotation")))
        if not rotation:
            rotation = int(_f((v.get("tags") or {}).get("rotate")))
        w, h = int(v.get("width", 0)), int(v.get("height", 0))
        if abs(rotation) % 180 == 90:  # telefon videosi yonboshlab saqlangan
            w, h = h, w
        out.update(width=w, height=h, rotation=rotation, vcodec=v.get("codec_name"),
                   fps=round(_rate(v.get("avg_frame_rate")) or _rate(v.get("r_frame_rate")), 3))
    if a:
        out.update(acodec=a.get("codec_name"), sample_rate=int(_f(a.get("sample_rate"))),
                   channels=int(a.get("channels", 0)))
    return out


def verify_video(path: str | Path, width: int | None = None, height: int | None = None,
                 duration: float | None = None, tolerance: float = 0.5,
                 need_audio: bool = True) -> tuple[dict, list]:
    """Natijani ffprobe bilan tekshiradi. (ma'lumot, muammolar ro'yxati) qaytaradi."""
    meta = ffprobe_info(path)
    problems = []
    if not meta["has_video"]:
        problems.append("video oqimi yo'q")
    if width and height and (meta["width"], meta["height"]) != (width, height):
        problems.append(f"o'lcham {meta['width']}x{meta['height']}, kutilgan {width}x{height}")
    if duration is not None and abs(meta["duration"] - duration) > tolerance:
        problems.append(f"davomiylik {meta['duration']:.2f}s, kutilgan {duration:.2f}s (+-{tolerance}s)")
    if need_audio and not meta["has_audio"]:
        problems.append("ovoz oqimi yo'q")
    if meta["duration"] <= 0:
        problems.append("davomiylik 0")
    return meta, problems


# ---------------------------------------------------------------- filtr yo'llari

def escape_filter_value(value: str) -> str:
    """FFmpeg filtr qiymatini ikki bosqichda ekranlaydi (filtr + filtergraph darajasi).

    Masalan ikki nuqta ':' -> '\\\\:' bo'ladi. Qo'shtirnoq ishlatilmaydi.
    """
    s = str(value)
    s = s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")   # 1-daraja
    s = s.replace("\\", "\\\\").replace("'", "\\'")                        # 2-daraja
    for ch in "[],;":
        s = s.replace(ch, "\\" + ch)
    return s


def filter_path(path: str | Path, cwd: Path | None = None) -> str:
    """Fayl yo'lini FFmpeg filtri ichida xavfsiz ishlatish uchun tayyorlaydi.

    Windows muammosi: 'D:\\papka\\sub.ass' dagi ikki nuqta filtr parametrlarini
    ajratuvchi, teskari slesh esa ekranlash belgisi deb o'qiladi. Yechim:
      1) iloji bo'lsa yo'lni cwd ga nisbatan nisbiy qilamiz (disk harfi yo'qoladi),
      2) teskari sleshlarni to'g'ri sleshga almashtiramiz,
      3) qolgan maxsus belgilarni ekranlaymiz.
    """
    p = Path(path).resolve()
    if cwd is not None:
        try:
            p = p.relative_to(Path(cwd).resolve())
        except ValueError:
            pass
    return escape_filter_value(p.as_posix())


# ---------------------------------------------------------------- vaqt va SRT

def fmt_time(sec: float) -> str:
    sec = max(0.0, float(sec))
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:06.3f}"


def srt_time(sec: float) -> str:
    ms = int(round(max(0.0, float(sec)) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: list, path: str | Path) -> None:
    lines = []
    for i, cue in enumerate(cues, 1):
        lines += [str(i), f"{srt_time(cue['start'])} --> {srt_time(cue['end'])}", cue["text"].strip(), ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


_SRT_TIME = re.compile(
    r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{1,3})")


def parse_srt(path: str | Path) -> list:
    """SRT faylni o'qiydi: [{'start', 'end', 'text'}]. Buzuq bloklar haqida xato beradi."""
    p = need_file(path, "SRT fayl")
    text = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        rows = [r for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        idx = next((i for i, r in enumerate(rows) if _SRT_TIME.search(r)), None)
        if idx is None:
            raise MontajError(f"SRT blokida vaqt qatori topilmadi ({p.name}): {rows[0][:60]!r}")
        g = _SRT_TIME.search(rows[idx]).groups()
        start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3].ljust(3, "0")) / 1000
        end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7].ljust(3, "0")) / 1000
        body = " ".join(r.strip() for r in rows[idx + 1:]).strip()
        if body and end > start:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def words_to_cues(words: list, sub_style: dict) -> list:
    """So'zlar ro'yxatidan qisqa subtitr bo'laklari yasaydi (Reels uslubi)."""
    max_words = int(sub_style.get("max_words_per_line", 3))
    max_chars = int(sub_style.get("max_chars_per_line", 18))
    max_dur = float(sub_style.get("max_cue_duration", 2.5))
    gap_break = float(sub_style.get("gap_break", 0.6))
    cues, cur = [], []

    def flush():
        if cur:
            cues.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                         "text": " ".join(w["word"] for w in cur)})
            cur.clear()

    for w in words:
        token = str(w.get("word", "")).strip()
        if not token:
            continue
        item = {"start": float(w["start"]), "end": float(w["end"]), "word": token}
        if cur:
            text_len = len(" ".join(x["word"] for x in cur)) + 1 + len(token)
            if (len(cur) >= max_words or text_len > max_chars
                    or item["end"] - cur[0]["start"] > max_dur
                    or item["start"] - cur[-1]["end"] > gap_break):
                flush()
        cur.append(item)
        if token[-1] in ".!?":
            flush()
    flush()
    # bo'laklar ustma-ust tushmasin va juda qisqa bo'lmasin
    min_dur = float(sub_style.get("min_cue_duration", 0.3))
    for i, cue in enumerate(cues):
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else math.inf
        cue["end"] = min(max(cue["end"], cue["start"] + min_dur), nxt)
        cue["start"], cue["end"] = round(cue["start"], 3), round(cue["end"], 3)
    return [c for c in cues if c["end"] > c["start"]]


def write_json(data, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: str | Path, what: str = "JSON fayl"):
    p = need_file(path, what)
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise MontajError(f"{p} buzuq JSON: {exc}") from exc
