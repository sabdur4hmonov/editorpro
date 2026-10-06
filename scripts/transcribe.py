"""Videodan so'z-so'z vaqtli matn chiqaradi (JSON va SRT).

Misol:
    python scripts/transcribe.py input/video.mp4
    python scripts/transcribe.py input/video.mp4 --language ru --model base

Natija (standart): temp/<video nomi>/orig.words.json va orig.srt
Asl video o'zgarmaydi.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import common as C


def extract_audio(video: Path, wav: Path, max_seconds: float | None = None) -> None:
    """Videodan 16 kHz mono WAV ajratadi (whisper shuni kutadi)."""
    cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", video]
    if max_seconds:
        cmd += ["-t", f"{max_seconds:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", C.guard_output(wav, video)]
    C.run(cmd)


def load_model(wcfg: dict):
    """faster-whisper modelini yuklaydi. Birinchi marta internetdan yuklab oladi."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise C.MontajError(
            "faster-whisper o'rnatilmagan. Avval .venv ni yoqing va o'rnating:\n"
            "  .venv\\Scripts\\Activate.ps1\n  pip install -r requirements.txt"
        ) from None

    device = str(wcfg.get("device", "cpu")).lower()
    compute = str(wcfg.get("compute_type", "int8"))
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    kwargs = {"device": device, "compute_type": compute}
    if device == "cpu":
        kwargs["cpu_threads"] = int(wcfg.get("cpu_threads", 4))
    C.info(f"  Whisper modeli yuklanmoqda: {wcfg['model']} ({device}, {compute})...")
    try:
        return WhisperModel(str(wcfg["model"]), **kwargs)
    except Exception as exc:  # model yuklab bo'lmadi, internet yo'q, GPU kutubxonasi yo'q va h.k.
        raise C.MontajError(
            f"Whisper modelini yuklab bo'lmadi ({wcfg['model']}, {device}, {compute}): {exc}\n"
            "Tekshiring: internet bormi (model birinchi marta yuklanadi), "
            "style.json da whisper.model nomi to'g'rimi, device 'cpu' turibdimi."
        ) from exc


def transcribe_audio(wav: Path, wcfg: dict, model=None) -> dict:
    """WAV faylni matnga aylantiradi va so'zlar ro'yxatini qaytaradi."""
    model = model or load_model(wcfg)
    language = str(wcfg.get("language", "auto")).lower()
    started = time.time()
    try:
        segments, tinfo = model.transcribe(
            str(wav),
            language=None if language in ("", "auto") else language,
            beam_size=int(wcfg.get("beam_size", 5)),
            word_timestamps=True,
            vad_filter=bool(wcfg.get("vad_filter", True)),
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
            initial_prompt=wcfg.get("initial_prompt") or None,
        )
        words, segs = [], []
        for seg in segments:  # generator: aynan shu yerda haqiqiy ish bajariladi
            seg_words = []
            for w in (seg.words or []):
                token = w.word.strip()
                if token:
                    seg_words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                                      "word": token, "prob": round(float(w.probability), 3)})
            segs.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()})
            words += seg_words
    except Exception as exc:
        raise C.MontajError(f"Whisper transkripsiya paytida xato berdi: {exc}") from exc
    return {
        "language": tinfo.language,
        "language_probability": round(float(tinfo.language_probability), 3),
        "duration": round(float(tinfo.duration), 3),
        "model": str(wcfg["model"]),
        "elapsed_sec": round(time.time() - started, 2),
        "segments": segs,
        "words": words,
    }


def transcribe_video(video: Path, style: dict, out_dir: Path | None = None,
                     base_name: str = "orig", model=None) -> dict:
    """To'liq bosqich: ovozni ajratish -> whisper -> JSON va SRT yozish."""
    video = C.need_file(video, "Video")
    out_dir = Path(out_dir) if out_dir else C.job_dir(video)
    json_path = C.guard_output(out_dir / f"{base_name}.words.json", video)
    srt_path = C.guard_output(out_dir / f"{base_name}.srt", video)

    meta = C.ffprobe_info(video)
    if not meta["has_audio"]:
        C.warn("Videoda ovoz yo'q, transkripsiya bo'sh bo'ladi.")
        result = {"language": None, "language_probability": 0, "duration": meta["duration"],
                  "model": None, "elapsed_sec": 0, "segments": [], "words": []}
    else:
        wav = out_dir / "audio16k.wav"
        extract_audio(video, wav)
        result = transcribe_audio(wav, style["whisper"], model=model)
    result["source"] = str(video)
    cues = C.words_to_cues(result["words"], style["subtitles"])
    C.write_json(result, json_path)
    C.write_srt(cues, srt_path)
    result["json_path"], result["srt_path"], result["cues"] = str(json_path), str(srt_path), cues
    return result


def low_confidence_words(words: list, threshold: float) -> list:
    return [w for w in words if w.get("prob", 1.0) < threshold]


def main() -> int:
    ap = argparse.ArgumentParser(description="Videodan so'z-so'z vaqtli matn chiqaradi (JSON + SRT).")
    ap.add_argument("video", help="Video fayl (masalan input/video.mp4)")
    ap.add_argument("--out-dir", help="Natija papkasi (standart: temp/<video nomi>/)")
    ap.add_argument("--name", default="orig", help="Natija fayl nomi boshi (standart: orig)")
    ap.add_argument("--model", help="Whisper modeli (style.json dagini almashtiradi): base, small, medium ...")
    ap.add_argument("--language", help="Til: uz, ru, en yoki auto")
    ap.add_argument("--compute-type", help="int8 (CPU uchun), float16 (GPU uchun) ...")
    ap.add_argument("--device", help="cpu, cuda yoki auto")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    for key, val in (("model", args.model), ("language", args.language),
                     ("compute_type", args.compute_type), ("device", args.device)):
        if val:
            style["whisper"][key] = val

    C.info(f"Transkripsiya: {args.video}")
    res = transcribe_video(Path(args.video), style, args.out_dir, args.name)
    dur = res["duration"] or 0.0
    speed = (dur / res["elapsed_sec"]) if res["elapsed_sec"] else 0
    C.info(f"  Til: {res['language']} (ishonch {res['language_probability']}), "
           f"so'zlar: {len(res['words'])}, subtitr bo'laklari: {len(res['cues'])}")
    if speed:
        C.info(f"  Vaqt: {res['elapsed_sec']}s, tezlik: {speed:.1f}x (1x = video uzunligi bilan teng)")
    low = low_confidence_words(res["words"], float(style["whisper"].get("low_confidence", 0.5)))
    if low:
        C.info("  Shubhali so'zlar (tekshirib chiqing): "
               + ", ".join(f"{w['word']}@{C.fmt_time(w['start'])}" for w in low[:30]))
    C.info(f"  JSON: {res['json_path']}\n  SRT:  {res['srt_path']}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
