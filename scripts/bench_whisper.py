"""Whisper tezligini shu kompyuterda o'lchaydi va qaysi modelni ishlatishni tavsiya qiladi.

    python scripts/bench_whisper.py                          # small modelini sinaydi
    python scripts/bench_whisper.py --models small base      # ikkalasini solishtiradi
    python scripts/bench_whisper.py input/video.mp4 --language uz

Tezlik "x" da ko'rsatiladi: 2x degani 60 soniyalik ovoz 30 soniyada matnga aylanadi.
Natija: temp/whisper_bench.json
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import common as C
import transcribe as T

DEFAULT_SPEECH = C.TEMP_DIR / "selftest" / "speech.wav"
DEFAULT_VIDEO = C.TEMP_DIR / "selftest" / "test_video.mp4"


def main() -> int:
    ap = argparse.ArgumentParser(description="Whisper modellari tezligini o'lchaydi.")
    ap.add_argument("media", nargs="?", help="Nutqli audio yoki video (standart: temp/selftest/speech.wav)")
    ap.add_argument("--models", nargs="+", default=["small"], help="Sinaladigan modellar (standart: small)")
    ap.add_argument("--language", help="Til (standart: namuna uchun en, o'z faylingiz uchun style.json dagi)")
    ap.add_argument("--seconds", type=float, default=60, help="Eng ko'pi bilan necha soniya sinalsin")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    wcfg = dict(style["whisper"])
    real_speech = True
    if args.media:
        media = C.need_file(args.media, "Fayl")
        wcfg["language"] = args.language or wcfg.get("language", "auto")
    elif DEFAULT_SPEECH.is_file():
        media = DEFAULT_SPEECH
        wcfg["language"] = args.language or "en"
    elif DEFAULT_VIDEO.is_file():
        media, real_speech = DEFAULT_VIDEO, False
        wcfg["language"] = args.language or "en"
        wcfg["vad_filter"] = False  # nutq yo'q: model baribir butun ovozni qayta ishlashi uchun
        C.warn("Nutqli namuna yo'q, test video (faqat ton) ishlatiladi. Natija taxminiy, "
               "haqiqiy nutqda sekinroq bo'ladi. Aniqroq o'lchash uchun o'z videongizni bering.")
    else:
        raise C.MontajError("Sinov uchun fayl yo'q. Fayl bering: python scripts/bench_whisper.py input/video.mp4\n"
                            "yoki avval: python scripts/selftest.py --no-whisper")

    wav = C.TEMP_DIR / "whisper_bench.wav"
    T.extract_audio(media, wav, args.seconds)
    audio_sec = C.ffprobe_info(wav)["duration"]
    C.info(f"Namuna: {media.name}, {audio_sec:.1f} soniya, til: {wcfg['language']}, "
           f"{wcfg.get('device', 'cpu')}/{wcfg.get('compute_type', 'int8')}, {wcfg.get('cpu_threads', 4)} oqim")

    rows = []
    for name in args.models:
        cfg = dict(wcfg, model=name)
        C.info(f"\nModel: {name}")
        t0 = time.time()
        model = T.load_model(cfg)
        load_sec = time.time() - t0
        res = T.transcribe_audio(wav, cfg, model=model)
        speed = audio_sec / max(res["elapsed_sec"], 0.01)
        text = " ".join(w["word"] for w in res["words"])
        rows.append({"model": name, "load_sec": round(load_sec, 1), "transcribe_sec": res["elapsed_sec"],
                     "speed_x": round(speed, 2), "words": len(res["words"]), "language": res["language"],
                     "real_speech": real_speech, "text": text[:300]})
        C.info(f"  yuklash: {load_sec:.1f}s (birinchi marta internetdan yuklab olish ham shu ichida)")
        C.info(f"  transkripsiya: {res['elapsed_sec']}s -> tezlik {speed:.1f}x, so'zlar: {len(res['words'])}")
        if text:
            C.info(f"  matn: {text[:160]}")
        del model
    wav.unlink(missing_ok=True)

    first = rows[0]
    if first["speed_x"] >= 2:
        advice = f"'{first['model']}' bu kompyuterda yetarlicha tez ({first['speed_x']}x). Shuni qoldiring."
    elif first["speed_x"] >= 1:
        advice = (f"'{first['model']}' ishlaydi, lekin sekinroq ({first['speed_x']}x). Qisqa Reels uchun yetadi; "
                  "uzun videolarda style.json da whisper.model ni 'base' qiling.")
    else:
        advice = (f"'{first['model']}' juda sekin ({first['speed_x']}x, video uzunligidan ham sekin). "
                  "TAVSIYA: style.json da whisper.model ni 'base' qiling (tezroq, lekin xatosi ko'proq).")
    C.info(f"\nXULOSA: {advice}")
    C.write_json({"audio_sec": audio_sec, "results": rows, "advice": advice}, C.TEMP_DIR / "whisper_bench.json")
    return 0


if __name__ == "__main__":
    C.run_main(main)
