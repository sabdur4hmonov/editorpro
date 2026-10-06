"""Videodan so'z-so'z vaqtli matn chiqaradi (JSON va SRT).

Misol:
    python scripts/transcribe.py input/video.mp4
    python scripts/transcribe.py input/video.mp4 --language ru --model base
    python scripts/transcribe.py input/video.mp4 --model yuldashev222/whisper-small-uz-v1-ct2
    python scripts/transcribe.py --model-info small          # model bormi, hajmi qancha (hech narsa yuklamaydi)

Natija (standart): temp/<video nomi>/orig.words.json va orig.srt
Asl video o'zgarmaydi.

Model sozlamasi style/style.json ning "whisper" bo'limida turadi:
    model         - nom (tiny, base, small, medium ...), Hugging Face manzili (muallif/model, faster-whisper
                    formatida) yoki kompyuterdagi model papkasi
    language      - uz, ru, en yoki auto
    compute_type  - int8 (CPU uchun)
    beam_size     - 5 (kattaroq = sekinroq, ba'zan aniqroq)
Buyruq qatoridagi --model, --language, --compute-type, --beam-size shu sozlamani bir martalik almashtiradi.

Yangi model internetdan o'zi yuklanMAYDI: avval hajmi ko'rsatiladi va ruxsat so'raladi.
Ruxsat berilgach: --allow-download. Ruxsatsiz chiqish kodi 4 ("yuklashga ruxsat kerak", bu xato emas).

Har transkripsiyadan keyin so'z vaqtlari tekshiriladi (tartib, end >= start, davomiylikdan oshmasligi).
Muammo bo'lsa ro'yxati chiqadi va <nom>.timing_issues.json ga yoziladi; JSON va SRT formati o'zgarmaydi.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import time
from pathlib import Path

import common as C

EXIT_NEED_DOWNLOAD = 4
# faster-whisper modeli uchun kerakli fayllar (kutubxonaning o'zi ham aynan shularni yuklaydi)
MODEL_FILES = ("config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*")
# Kam xotirada tavsiya qilinadigan kichik modellar va taxminiy hajmi (GB)
SMALL_MODELS = (("small", 0.5), ("base", 0.15), ("tiny", 0.08))


class DownloadNeeded(C.MontajError):
    """Model keshda yo'q va yuklashga ruxsat berilmagan (chiqish kodi 4)."""

# Windows'da keraksiz "symlink" ogohlantirishini o'chiradi (model baribir to'g'ri saqlanadi)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def extract_audio(video: Path, wav: Path, max_seconds: float | None = None) -> None:
    """Videodan 16 kHz mono WAV ajratadi (whisper shuni kutadi)."""
    cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", video]
    if max_seconds:
        cmd += ["-t", f"{max_seconds:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", C.guard_output(wav, video)]
    C.run(cmd)


def _fw_import():
    try:
        import faster_whisper  # noqa: F401
        from faster_whisper import WhisperModel
        return WhisperModel
    except ImportError:
        raise C.MontajError(
            "faster-whisper o'rnatilmagan. Avval .venv ni yoqing va o'rnating:\n"
            "  .venv\\Scripts\\Activate.ps1\n  pip install -r requirements.txt"
        ) from None


def gb(n: float) -> str:
    """Fayl hajmi o'qiladigan ko'rinishda (1 GB = 1000 MB, Hugging Face saytidagi kabi)."""
    return f"{n / 1e9:.2f} GB" if n >= 1e8 else f"{n / 1e6:.1f} MB"


def model_status(name: str) -> dict:
    """Model qayerda ekanini aniqlaydi. Internetga chiqmaydi, hech narsa yuklamaydi.

    Qaytaradi: {"name", "kind": "local" | "hub", "repo", "path", "cached", "bytes"}
      local - kompyuterdagi papka; hub - Hugging Face modeli (cached: keshda bor-yo'qligi).
    """
    name = str(name or "").strip()
    if not name:
        raise C.MontajError("Model nomi bo'sh. style.json da whisper.model ni to'ldiring (masalan: small).")
    for cand in (Path(name), C.ROOT / name):
        if cand.is_dir():
            if not (cand / "model.bin").is_file():
                raise C.MontajError(f"Model papkasida model.bin yo'q: {cand}\n"
                                    "Bu faster-whisper (CTranslate2) formatidagi model papkasi bo'lishi kerak.")
            return {"name": name, "kind": "local", "repo": None, "path": str(cand.resolve()), "cached": True,
                    "bytes": (cand / "model.bin").stat().st_size}
    _fw_import()
    from faster_whisper import utils as fw_utils
    known = dict(getattr(fw_utils, "_MODELS", {}))
    if "/" in name:
        repo = name
    elif name in known:
        repo = known[name]
    else:
        raise C.MontajError(f"Noma'lum model: {name!r}.\n  Tayyor nomlar: {', '.join(sorted(known))}\n"
                            "  Yoki Hugging Face manzili (muallif/model) yoki model papkasining yo'li.")
    path, cached, size = None, False, None
    try:
        path = fw_utils.download_model(name, local_files_only=True)
    except Exception:
        path = None      # keshda yo'q
    if path and (Path(path) / "model.bin").is_file():
        cached, size = True, (Path(path) / "model.bin").stat().st_size
    return {"name": name, "kind": "hub", "repo": repo, "path": str(path) if cached else None,
            "cached": cached, "bytes": size}


def remote_size(repo: str) -> dict:
    """Hugging Face'dan model fayllari hajmini so'raydi (faqat ma'lumot, hech narsa yuklamaydi)."""
    try:
        import huggingface_hub
        info = huggingface_hub.HfApi().model_info(repo, files_metadata=True)
    except ImportError:
        raise C.MontajError("huggingface_hub o'rnatilmagan (faster-whisper bilan birga keladi).") from None
    except Exception as exc:
        kind = type(exc).__name__
        if "NotFound" in kind:
            raise C.MontajError(f"Hugging Face'da bunday model yo'q (yoki yopiq): {repo}\n"
                                "Nomini tekshiring: https://huggingface.co/" + repo) from None
        raise C.MontajError(f"Hugging Face'dan model hajmini bilib bo'lmadi ({repo}): {kind}: {exc}\n"
                            "Internet borligini tekshiring.") from None
    files = [(s.rfilename, int(s.size or 0)) for s in (info.siblings or [])
             if any(fnmatch.fnmatch(s.rfilename, pat) for pat in MODEL_FILES)]
    if not any(name == "model.bin" for name, _ in files):
        raise C.MontajError(f"{repo} ichida model.bin yo'q: bu faster-whisper (CTranslate2) formatidagi model emas.\n"
                            "Oddiy (transformers) whisper modeli bo'lsa, uni avval CTranslate2 formatiga o'tkazish kerak.")
    return {"repo": repo, "total": sum(size for _, size in files), "files": files}


def _cache_free_bytes() -> int | None:
    try:
        from huggingface_hub import constants
        folder = Path(constants.HF_HUB_CACHE)
        while not folder.exists() and folder.parent != folder:
            folder = folder.parent
        return shutil.disk_usage(folder).free
    except Exception:
        return None


def ensure_model(name: str, allow_download: bool | None = None) -> dict:
    """Model tayyorligini ta'minlaydi. Keshda bo'lmasa: hajmini aytadi va ruxsat bo'lsagina yuklaydi.

    allow_download: True - ruxsat berilgan; False - yuklama; None - terminalda so'ra (so'rab bo'lmasa yuklama).
    """
    st = model_status(name)
    if st["cached"]:
        return st
    remote = remote_size(st["repo"])
    free = _cache_free_bytes()
    lines = [f"Model kompyuterda yo'q: {name}" + (f" ({st['repo']})" if st["repo"] != name else ""),
             f"  Yuklash hajmi: {gb(remote['total'])} (internetdan, Hugging Face)"]
    if free is not None:
        lines.append(f"  Diskda bo'sh joy: {gb(free)}")
        if free < remote["total"] * 1.1:
            raise C.MontajError("\n".join(lines) + "\nDiskda joy yetmaydi: avval joy bo'shating.")
    C.info("\n".join(lines))
    if allow_download is None:
        answer = C.confirm(f"Shu modelni yuklaymi ({gb(remote['total'])})? [y/N]: ")
        allow_download = answer if answer is not None else False
        if answer is False:
            raise DownloadNeeded("Yuklash rad etildi. Model yuklanmadi.")
    if not allow_download:
        raise DownloadNeeded(
            f"YUKLASHGA RUXSAT KERAK: {name} ({gb(remote['total'])}). Hech narsa yuklanmadi.\n"
            "  1) Foydalanuvchidan so'rang: shu hajmdagi modelni yuklashga rozimi.\n"
            "  2) Rozi bo'lsa shu buyruqni --allow-download bilan qayta ishga tushiring\n"
            f"     (yoki bir marta: python scripts/transcribe.py --model-info {name} --allow-download).")
    import huggingface_hub
    C.info(f"  Yuklanmoqda: {st['repo']} ({gb(remote['total'])}). Internet tezligiga qarab bir necha daqiqa...")
    try:
        huggingface_hub.snapshot_download(st["repo"], allow_patterns=list(MODEL_FILES))
    except Exception as exc:
        raise C.MontajError(f"Modelni yuklab bo'lmadi ({st['repo']}): {type(exc).__name__}: {exc}\n"
                            "Internetni tekshirib, shu buyruqni qayta ishga tushiring (yuklash davom etadi).") from exc
    st = model_status(name)
    if not st["cached"]:
        raise C.MontajError(f"Model yuklandi, lekin keshda topilmadi: {name}. Qayta urinib ko'ring.")
    C.info(f"  Yuklandi: {st['path']}")
    return st


def memory_advice(model_bytes: int | None) -> str:
    """Xotira yetmaganda: kichikroq model tavsiyasi."""
    size = (model_bytes or 0) / 2**30
    smaller = [f"{n} (~{g} GB)" for n, g in SMALL_MODELS if g < size * 0.8] or ["base (~0.15 GB)", "tiny (~0.08 GB)"]
    return ("Nima qilish kerak:\n"
            "  1) Og'ir dasturlarni yoping (Docker Desktop, Chrome, boshqa agentlar) va qayta urining.\n"
            f"  2) Yordam bermasa kichikroq model: {', '.join(smaller[:2])}. "
            "Bir martalik: --model NOM; doimiy: style.json dagi whisper.model.")


def load_model(wcfg: dict, allow_download: bool | None = None):
    """faster-whisper modelini yuklaydi. Model keshda bo'lmasa ruxsatsiz internetdan yuklamaydi."""
    WhisperModel = _fw_import()
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
    st = ensure_model(str(wcfg.get("model", "")), allow_download)
    size = st.get("bytes") or 0
    C.info(f"  Whisper modeli yuklanmoqda: {wcfg['model']} ({device}, {compute}"
           + (f", fayl {gb(size)}" if size else "") + ")...")
    mem = C.memory_status()
    if mem:
        free = min(mem["ram"], mem["commit"])
        need = max(0.6, size / 2**30 * 1.2 + 0.4)          # taxminiy: model fayli + ishlash uchun zaxira
        C.info(f"  Bo'sh xotira: RAM {mem['ram']} GB (jami {mem['total']} GB), dasturlar uchun zaxira {mem['commit']} GB"
               + (f"; bu model uchun taxminan {need:.1f} GB kerak" if size else ""))
        if size and free < size / 2**30 * 0.6:
            raise C.MontajError(
                f"Xotira yetmaydi: model fayli {gb(size)}, bo'sh xotira esa {free} GB "
                f"(RAM {mem['ram']} GB, zaxira {mem['commit']} GB). Model yuklanmadi.\n" + memory_advice(size))
        if free < need:
            C.warn(f"Bo'sh xotira kam ({free} GB, kerak ~{need:.1f} GB). Model yuklanmasligi yoki juda sekin "
                   "ishlashi mumkin: og'ir dasturlarni yoping (Docker Desktop, Chrome, boshqa agentlar).")
    try:
        # keshdagi papka yo'li beriladi: internetga umuman chiqilmaydi
        return WhisperModel(st["path"], **kwargs)
    except Exception as exc:  # xotira yetmadi, GPU kutubxonasi yo'q, model buzuq va h.k.
        text = str(exc).lower()
        if isinstance(exc, MemoryError) or "alloc" in text or "memory" in text:
            now = C.memory_status()
            raise C.MontajError(
                f"Whisper modeliga xotira yetmadi ({wcfg['model']}" + (f", fayl {gb(size)}" if size else "") + f"): {exc}\n"
                + (f"Hozir bo'sh: RAM {now['ram']} GB, zaxira {now['commit']} GB.\n" if now else "")
                + memory_advice(size)
            ) from exc
        raise C.MontajError(
            f"Whisper modelini yuklab bo'lmadi ({wcfg['model']}, {device}, {compute}): {exc}\n"
            "Tekshiring: style.json da whisper.model nomi to'g'rimi, device 'cpu' turibdimi, "
            "model faster-whisper (CTranslate2) formatidami."
        ) from exc


def check_words(words: list, duration: float | None = None, tolerance: float = 0.1) -> list:
    """So'z vaqtlarini tekshiradi. Muammolar ro'yxatini qaytaradi (bo'sh ro'yxat = hammasi joyida).

    Tekshiriladi: boshlanish vaqtlari o'sish tartibida, end >= start, vaqtlar manfiy emas va
    davomiylikdan oshmaydi. Hech narsa tuzatilmaydi, faqat ko'rsatiladi.
    """
    issues, prev = [], None
    for i, w in enumerate(words, 1):
        try:
            start, end = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            issues.append({"index": i, "word": str(w.get("word", "")) if isinstance(w, dict) else "",
                           "problem": "start yoki end yo'q (yoki son emas)"})
            continue
        def add(problem):
            issues.append({"index": i, "word": str(w.get("word", "")), "start": start, "end": end, "problem": problem})
        if end < start:
            add(f"end < start ({end} < {start})")
        if start < 0:
            add("boshlanish vaqti manfiy")
        if prev is not None and start < prev:
            add(f"tartib buzilgan: oldingi so'z {prev} da boshlangan, bu esa {start} da")
        if duration and end > float(duration) + tolerance:
            add(f"davomiylikdan oshgan (end {end} > {float(duration):.3f})")
        prev = start
    return issues


def print_issues(issues: list, limit: int = 30) -> None:
    if not issues:
        return
    C.warn(f"So'z vaqtlarida {len(issues)} ta muammo topildi (tuzatilmadi, faqat ko'rsatilmoqda):")
    for it in issues[:limit]:
        C.info(f"    #{it['index']} \"{it.get('word', '')}\": {it['problem']}")
    if len(issues) > limit:
        C.info(f"    ... yana {len(issues) - limit} ta")


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
                     base_name: str = "orig", model=None, allow_download: bool | None = None) -> dict:
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
        if model is None:      # avval model: yuklashga ruxsat kerak bo'lsa ortiqcha ish qilinmaydi
            model = load_model(style["whisper"], allow_download)
        wav = out_dir / "audio16k.wav"
        extract_audio(video, wav)
        result = transcribe_audio(wav, style["whisper"], model=model)
    result["source"] = str(video)
    cues = C.words_to_cues(result["words"], C.cue_style(style))
    C.write_json(result, json_path)
    C.write_srt(cues, srt_path)
    # vaqt tekshiruvi: natija fayllari formati o'zgarmaydi, muammolar alohida faylga yoziladi
    issues = check_words(result["words"], max(float(result["duration"] or 0), float(meta["duration"] or 0)))
    issues_path = out_dir / f"{base_name}.timing_issues.json"
    if issues:
        print_issues(issues)
        C.write_json({"source": str(json_path), "issues": issues}, issues_path)
    else:
        issues_path.unlink(missing_ok=True)
    result["json_path"], result["srt_path"], result["cues"] = str(json_path), str(srt_path), cues
    result["timing_issues"] = issues
    return result


def low_confidence_words(words: list, threshold: float) -> list:
    return [w for w in words if w.get("prob", 1.0) < threshold]


def print_model_info(name: str, allow_download: bool) -> int:
    """--model-info: model holatini ko'rsatadi. --allow-download bilan birga kelsa yuklab ham qo'yadi."""
    st = model_status(name)
    if st["cached"]:
        where = "kompyuterdagi papka" if st["kind"] == "local" else f"keshda bor ({st['repo']})"
        C.info(f"Model: {name}\n  Holati: {where}\n  Joyi: {st['path']}\n  model.bin: {gb(st['bytes'] or 0)}")
        mem = C.memory_status()
        if mem:
            need = max(0.6, (st["bytes"] or 0) / 2**30 * 1.2 + 0.4)
            C.info(f"  Xotira: taxminan {need:.1f} GB kerak; hozir bo'sh RAM {mem['ram']} GB, zaxira {mem['commit']} GB")
        return 0
    if allow_download:
        st = ensure_model(name, True)
        C.info(f"Model tayyor: {name} (model.bin {gb(st['bytes'] or 0)})")
        return 0
    remote = remote_size(st["repo"])
    C.info(f"Model: {name}\n  Holati: kompyuterda YO'Q (Hugging Face: {st['repo']})\n"
           f"  Yuklash hajmi: {gb(remote['total'])} ({len(remote['files'])} ta fayl, asosiysi model.bin)")
    free = _cache_free_bytes()
    if free is not None:
        C.info(f"  Diskda bo'sh joy: {gb(free)}")
    C.info("  Yuklash uchun (foydalanuvchi rozi bo'lgach): shu buyruqqa --allow-download qo'shing.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Videodan so'z-so'z vaqtli matn chiqaradi (JSON + SRT).")
    ap.add_argument("video", nargs="?", help="Video fayl (masalan input/video.mp4)")
    ap.add_argument("--out-dir", help="Natija papkasi (standart: temp/<video nomi>/)")
    ap.add_argument("--name", default="orig", help="Natija fayl nomi boshi (standart: orig)")
    ap.add_argument("--model", help="Whisper modeli (style.json dagini bir martalik almashtiradi): base, small, "
                                    "medium, Hugging Face manzili (muallif/model) yoki model papkasi")
    ap.add_argument("--language", help="Til: uz, ru, en yoki auto")
    ap.add_argument("--compute-type", help="int8 (CPU uchun), float16 (GPU uchun) ...")
    ap.add_argument("--beam-size", type=int, help="Qidiruv kengligi (standart: style.json dagi, odatda 5)")
    ap.add_argument("--device", help="cpu, cuda yoki auto")
    ap.add_argument("--allow-download", action="store_true",
                    help="Model kompyuterda bo'lmasa internetdan yuklashga ruxsat (foydalanuvchi rozi bo'lgach)")
    ap.add_argument("--model-info", nargs="?", const="", metavar="MODEL",
                    help="Model holatini ko'rsat (bormi, hajmi) va chiq. Nom berilmasa sozlamadagi model")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    for key, val in (("model", args.model), ("language", args.language),
                     ("compute_type", args.compute_type), ("device", args.device)):
        if val:
            style["whisper"][key] = val
    if args.beam_size is not None:
        if not 1 <= args.beam_size <= 20:
            raise C.MontajError("--beam-size 1 dan 20 gacha bo'lishi kerak.")
        style["whisper"]["beam_size"] = args.beam_size

    try:
        if args.model_info is not None:
            return print_model_info(args.model_info or str(style["whisper"].get("model", "")), args.allow_download)
        if not args.video:
            ap.error("video fayl kerak (yoki --model-info)")
        C.info(f"Transkripsiya: {args.video}")
        res = transcribe_video(Path(args.video), style, args.out_dir, args.name,
                               allow_download=True if args.allow_download else None)
    except DownloadNeeded as exc:
        C.info(f"\n{exc}")
        return EXIT_NEED_DOWNLOAD
    dur = res["duration"] or 0.0
    speed = (dur / res["elapsed_sec"]) if res["elapsed_sec"] else 0
    C.info(f"  Model: {res['model']}, til: {res['language']} (ishonch {res['language_probability']}), "
           f"so'zlar: {len(res['words'])}, subtitr bo'laklari: {len(res['cues'])}")
    if speed:
        C.info(f"  Vaqt: {res['elapsed_sec']}s, tezlik: {speed:.1f}x (1x = video uzunligi bilan teng)")
    low = low_confidence_words(res["words"], float(style["whisper"].get("low_confidence", 0.5)))
    if low:
        C.info("  Shubhali so'zlar (tekshirib chiqing): "
               + ", ".join(f"{w['word']}@{C.fmt_time(w['start'])}" for w in low[:30]))
    if res["words"]:
        C.info("  So'z vaqtlari tekshiruvi: " + ("muammo yo'q" if not res["timing_issues"]
                                                 else f"{len(res['timing_issues'])} ta muammo (yuqorida)"))
    C.info(f"  JSON: {res['json_path']}\n  SRT:  {res['srt_path']}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
