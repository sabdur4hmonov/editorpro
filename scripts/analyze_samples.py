"""samples/ dagi namuna videolarni tahlil qiladi va JSON hisobot yozadi.

Har bir video uchun:
  - ffprobe: davomiylik, o'lcham, fps, ovoz
  - sahna kesishlari: o'rtacha va median kesish uzunligi (PySceneDetect, bo'lmasa ffmpeg)
  - whisper: nutq tezligi (so'z/daqiqa)
  - har N soniyadan kadr rasmlari va umumiy "contact sheet" (temp/analysis/<nom>/)
  - ovoz balandligi (loudnorm o'lchovi: LUFS, true peak, LRA)
  - rang: o'rtacha yorqinlik, to'yinganlik, kontrast

Misol:
    python scripts/analyze_samples.py
    python scripts/analyze_samples.py --no-whisper
    python scripts/analyze_samples.py samples/bitta.mp4

Hisobot: temp/analysis/report.json. Kadr rasmlarini agent ko'rib chiqib, rang, subtitr joyi,
shrift va effektlar haqida xulosani style/style.json ga yozadi (AGENTS.md ga qarang).
Namuna videolar o'zgarmaydi.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

import common as C

ANALYSIS_DIR = C.TEMP_DIR / "analysis"


def scene_lengths(video: Path, threshold: float, duration: float) -> tuple[list, str]:
    """Sahna (kesish) uzunliklari ro'yxati va qaysi usul ishlatilgani."""
    try:
        from scenedetect import ContentDetector, detect
        scenes = detect(str(video), ContentDetector(threshold=threshold))
        lengths = []
        for start, end in scenes:
            s = getattr(start, "seconds", None)
            e = getattr(end, "seconds", None)
            if s is None or callable(s):
                s, e = start.get_seconds(), end.get_seconds()
            lengths.append(float(e) - float(s))
        return (lengths or [duration]), "scenedetect"
    except ImportError:
        C.warn("scenedetect o'rnatilmagan, ffmpeg sahna filtri ishlatiladi (aniqligi pastroq).")
    except Exception as exc:
        C.warn(f"scenedetect xato berdi ({exc}), ffmpeg sahna filtri ishlatiladi.")
    proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-i", video, "-an",
                  "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"])
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
    points = [0.0] + [t for t in times if 0 < t < duration] + [duration]
    return [b - a for a, b in zip(points, points[1:]) if b - a > 0] or [duration], "ffmpeg-scene"


def loudness(video: Path) -> dict | None:
    proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-i", video, "-vn",
                  "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not blocks:
        return None
    data = json.loads(blocks[-1])

    def num(key):
        try:
            return float(data[key])
        except (KeyError, ValueError):
            return None

    return {"integrated_lufs": num("input_i"), "true_peak_db": num("input_tp"), "lra": num("input_lra")}


def extract_frames(video: Path, out_dir: Path, every: float) -> list:
    """Har 'every' soniyadan bitta kadr va umumiy jadval rasmlari (contact sheet)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("frame_*.jpg")) + list(out_dir.glob("sheet_*.jpg")):
        old.unlink()  # faqat temp/analysis ichidagi eski kadrlar
    ffmpeg = C.need_tool("ffmpeg")
    C.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", video, "-an",
           "-vf", f"fps=1/{every:g},scale=-2:640", "-q:v", "4", out_dir / "frame_%04d.jpg"])
    C.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", video, "-an",
           "-vf", f"fps=1/{every:g},scale=-2:360,tile=6x3:padding=4:margin=4", "-q:v", "5",
           out_dir / "sheet_%02d.jpg"])
    return sorted(str(p) for p in out_dir.glob("frame_*.jpg"))


def color_stats(frames: list) -> dict | None:
    """Kadrlardan o'rtacha yorqinlik, to'yinganlik va kontrast (0-255 shkala)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        C.warn("opencv o'rnatilmagan, rang statistikasi o'tkazib yuborildi.")
        return None
    bright, sat, contrast = [], [], []
    for path in frames[:60]:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)  # yo'lda kirill harf bo'lsa ham ishlaydi
        if img is None:
            continue
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        bright.append(float(hsv[..., 2].mean()))
        sat.append(float(hsv[..., 1].mean()))
        contrast.append(float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).std()))
    if not bright:
        return None
    return {"brightness": round(statistics.mean(bright), 1), "saturation": round(statistics.mean(sat), 1),
            "contrast": round(statistics.mean(contrast), 1)}


def speech_rate(video: Path, style: dict, work: Path, max_sec: float, model) -> dict | None:
    """Whisper bilan nutq tezligi (so'z/daqiqa). Faqat birinchi max_sec soniya tahlil qilinadi."""
    import transcribe as T
    wav = work / "speech16k.wav"
    T.extract_audio(video, wav, max_sec)
    res = T.transcribe_audio(wav, style["whisper"], model=model)
    wav.unlink(missing_ok=True)
    words = res["words"]
    if not words:
        return {"words": 0, "words_per_minute": 0, "language": res["language"]}
    speech_span = max(1.0, words[-1]["end"] - words[0]["start"])
    cues = C.words_to_cues(words, C.cue_style(style))
    return {"words": len(words), "language": res["language"],
            "analyzed_sec": round(min(max_sec, res["duration"]), 1),
            "words_per_minute": round(len(words) / speech_span * 60, 1),
            "sample_text": " ".join(w["word"] for w in words[:40]),
            "avg_words_per_cue": round(len(words) / max(1, len(cues)), 2)}


def analyze_one(video: Path, style: dict, use_whisper: bool, model) -> dict:
    acfg = style.get("analysis", {})
    meta = C.ffprobe_info(video)
    work = ANALYSIS_DIR / C.slugify(video.stem)
    work.mkdir(parents=True, exist_ok=True)
    item = {"file": video.name, "probe": {k: meta[k] for k in (
        "duration", "width", "height", "fps", "has_audio", "vcodec", "acodec", "sample_rate", "channels")}}
    if not meta["has_video"]:
        item["error"] = "video oqimi yo'q"
        return item
    lengths, method = scene_lengths(video, float(acfg.get("scene_threshold", 27)), meta["duration"])
    item["cuts"] = {"method": method, "scene_count": len(lengths),
                    "avg_cut_sec": round(statistics.mean(lengths), 2),
                    "median_cut_sec": round(statistics.median(lengths), 2),
                    "min_cut_sec": round(min(lengths), 2), "max_cut_sec": round(max(lengths), 2)}
    frames = extract_frames(video, work, float(acfg.get("frame_every_sec", 2)))
    item["frames"] = {"dir": str(work), "count": len(frames),
                      "sheets": sorted(str(p) for p in work.glob("sheet_*.jpg"))}
    item["color"] = color_stats(frames)
    if meta["has_audio"]:
        item["loudness"] = loudness(video)
        if use_whisper:
            item["speech"] = speech_rate(video, style, work, float(acfg.get("whisper_max_sec", 120)), model)
    return item


def summarize(items: list) -> dict:
    """Barcha namunalar bo'yicha umumiy xulosa va style.json uchun raqamli tavsiya."""
    ok = [i for i in items if "error" not in i]
    if not ok:
        return {}

    def med(values):
        values = [v for v in values if v is not None]
        return round(statistics.median(values), 2) if values else None

    sizes = Counter((i["probe"]["width"], i["probe"]["height"]) for i in ok).most_common(1)[0][0]
    summary = {
        "videos": len(ok),
        "most_common_size": f"{sizes[0]}x{sizes[1]}",
        "median_fps": med([i["probe"]["fps"] for i in ok]),
        "median_duration_sec": med([i["probe"]["duration"] for i in ok]),
        "median_cut_sec": med([i["cuts"]["median_cut_sec"] for i in ok]),
        "avg_cut_sec": med([i["cuts"]["avg_cut_sec"] for i in ok]),
        "median_loudness_lufs": med([(i.get("loudness") or {}).get("integrated_lufs") for i in ok]),
        "median_words_per_minute": med([(i.get("speech") or {}).get("words_per_minute") or None for i in ok]),
        "median_brightness": med([(i.get("color") or {}).get("brightness") for i in ok]),
        "median_saturation": med([(i.get("color") or {}).get("saturation") for i in ok]),
    }
    suggest = {"video.width": sizes[0], "video.height": sizes[1]}
    if summary["median_fps"]:
        suggest["video.fps"] = round(summary["median_fps"])
    if summary["median_loudness_lufs"] is not None:
        suggest["audio.loudnorm_i"] = max(-20, min(-10, round(summary["median_loudness_lufs"])))
    wpm = summary["median_words_per_minute"]
    if wpm:  # tez gapiriladigan uslubda jimliklar qisqaroq qoldiriladi
        suggest["cut.min_silence"] = 0.3 if wpm >= 170 else 0.45 if wpm >= 130 else 0.6
    summary["suggested_style"] = suggest
    summary["agent_todo"] = ("Kadr rasmlarini (frames.sheets) ko'rib chiqing: subtitr joyi, shrift, rang, kontur, "
                             "effektlar. Xulosani foydalanuvchiga ayting va tasdiqlagach style/style.json ga yozing.")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Namuna videolarni tahlil qilib JSON hisobot yozadi.")
    ap.add_argument("videos", nargs="*", help="Aniq fayllar (berilmasa samples/ dagi hammasi)")
    ap.add_argument("--no-whisper", action="store_true", help="Nutq tezligini o'lchama (ancha tez ishlaydi)")
    ap.add_argument("--report", help="Hisobot fayli (standart: temp/analysis/report.json)")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    if args.videos:
        videos = [C.need_file(v, "Video") for v in args.videos]
    else:
        if not C.SAMPLES_DIR.is_dir():
            raise C.MontajError(f"samples/ papkasi topilmadi: {C.SAMPLES_DIR}")
        videos = sorted(p for p in C.SAMPLES_DIR.iterdir() if p.suffix.lower() in C.VIDEO_EXTS)
    if not videos:
        raise C.MontajError("samples/ ichida video yo'q. Avval yoqqan uslubdagi 3-5 ta namuna videoni "
                            "samples/ ga tashlang (mp4, mov, mkv).")

    model = None
    if not args.no_whisper:
        import transcribe as T
        model = T.load_model(style["whisper"])

    items = []
    for n, video in enumerate(videos, 1):
        C.info(f"\n[{n}/{len(videos)}] {video.name}")
        try:
            item = analyze_one(video, style, not args.no_whisper, model)
        except C.MontajError as exc:
            C.warn(f"{video.name} tahlil qilinmadi: {exc}")
            item = {"file": video.name, "error": str(exc)}
        items.append(item)
        if "error" not in item:
            p, c = item["probe"], item["cuts"]
            C.info(f"  {p['width']}x{p['height']}, {p['fps']:g} fps, {p['duration']:.1f}s, "
                   f"kesishlar: {c['scene_count']} ta, o'rtacha {c['avg_cut_sec']}s, median {c['median_cut_sec']}s")
            if item.get("loudness"):
                C.info(f"  balandlik: {item['loudness']['integrated_lufs']} LUFS")
            if item.get("speech"):
                C.info(f"  nutq: {item['speech']['words_per_minute']} so'z/daqiqa ({item['speech']['language']})")
            C.info(f"  kadrlar: {item['frames']['count']} ta -> {item['frames']['dir']}")

    report = {"videos": items, "summary": summarize(items)}
    report_path = C.guard_output(Path(args.report) if args.report else ANALYSIS_DIR / "report.json")
    C.write_json(report, report_path)
    C.info(f"\nHisobot: {report_path}")
    if report["summary"]:
        C.info("style.json uchun raqamli tavsiya: " + json.dumps(report["summary"]["suggested_style"], ensure_ascii=False))
        C.info("Keyingi qadam: kadr rasmlarini (sheet_*.jpg) ko'rib, uslub xulosasini style/style.json ga yozish.")
    failed = [i for i in items if "error" in i]
    return 1 if failed and len(failed) == len(items) else 0


if __name__ == "__main__":
    C.run_main(main)
