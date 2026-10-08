"""Yakuniy ovozni yig'adi: nutq (alohida me'yorlanadi) + musiqa va ovoz effektlari (nutqqa halaqit bermaydi).

Odatda compose.py chaqiradi. Alohida ham ishlatsa bo'ladi:
    python scripts/audio_mix.py temp/video/cut.mp4 -o temp/video/final_audio.wav --music musiqa.mp3

Ovoz effektlari (SFX): assets/sfx/<nom>.wav yoki brend papkasidagi sfx/<nom>.wav|mp3.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import common as C
import render as R

SFX_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac")

# Nutqni tozalash zanjirlari (audio.voice). Claude ovozni eshita olmaydi: qaysi biri yaxshi
# eshitilishini foydalanuvchi tinglab hal qiladi.
VOICE_PRESETS = {
    "off": "",
    # past shovqinni kesadi, yengil siqadi: ko'p hollarda xavfsiz
    "clean": "highpass=f=75,acompressor=threshold=-21dB:ratio=2.5:attack=12:release=180:makeup=1.5,deesser=i=0.3",
    # + shovqinni pasaytirish: shovqinli xona yoki ko'cha uchun
    "denoise": "highpass=f=80,afftdn=nr=10:nf=-45,acompressor=threshold=-21dB:ratio=2.5:attack=12:release=180:makeup=1.5,deesser=i=0.3",
    # kuchliroq siqish va tiniqlik: "radio" ovozi
    "strong": ("highpass=f=90,afftdn=nr=12:nf=-42,acompressor=threshold=-24dB:ratio=3.5:attack=8:release=160:makeup=3,"
               "deesser=i=0.5,equalizer=f=3500:t=q:w=1.2:g=2"),
}


def find_sfx(name: str, brand_dir: Path | None = None) -> Path:
    """SFX faylini nomi bo'yicha topadi (avval brend papkasi, keyin assets/sfx)."""
    name = str(name)
    direct = Path(name)
    if direct.suffix.lower() in SFX_EXTS:
        for base in ([brand_dir] if brand_dir else []) + [C.ROOT]:
            if (base / direct).is_file():
                return (base / direct).resolve()
        if direct.is_file():
            return direct.resolve()
    folders = ([brand_dir / "sfx"] if brand_dir else []) + [C.ROOT / "assets" / "sfx"]
    for folder in folders:
        for ext in SFX_EXTS:
            if (folder / f"{name}{ext}").is_file():
                return (folder / f"{name}{ext}").resolve()
    have = sorted({p.stem for f in folders if f.is_dir() for p in f.iterdir() if p.suffix.lower() in SFX_EXTS})
    raise C.MontajError(f"Ovoz effekti topilmadi: {name!r}. Mavjudlari: {', '.join(have) or 'yoq'}")


LAST_REPORT: dict = {}     # oxirgi build_audio natijasi (compose.py tekshiruv ro'yxatiga qo'shadi)


def _frame_db(path: Path, hop_sec: float = 0.05):
    """WAV faylning qisqa bo'laklardagi balandligi (dBFS). numpy massiv qaytaradi."""
    import wave

    import numpy as np
    with wave.open(str(path), "rb") as wf:
        sr, ch, n = wf.getframerate(), wf.getnchannels(), wf.getnframes()
        if wf.getsampwidth() != 2:
            raise C.MontajError(f"Kutilgan 16-bit WAV emas: {path.name}")
        data = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data[: len(data) // ch * ch].reshape(-1, ch).mean(axis=1)
    hop = max(1, int(sr * hop_sec))
    frames = len(data) // hop
    if frames == 0:
        return np.zeros(0, np.float32)
    rms = np.sqrt((data[: frames * hop].reshape(frames, hop) ** 2).mean(axis=1) + 1e-12)
    return 20.0 * np.log10(rms)


def voice_margin(voice_wav: Path, add_wav: Path) -> float | None:
    """Nutq bor paytlarda qo'shimchalar (musiqa, effektlar) nutqdan necha dB past ekanini o'lchaydi.

    Qaytaradi: vaqtning 95 foizida qo'shimchalar nutqdan kamida shuncha dB past (None - ustma-ust tushmagan).
    """
    import numpy as np
    v, a = _frame_db(voice_wav), _frame_db(add_wav)
    n = min(len(v), len(a))
    if n == 0:
        return None
    v, a = v[:n], a[:n]
    both = (v > -45.0) & (a > -70.0)          # nutq ham bor, qo'shimcha ham eshitiladi
    if int(both.sum()) < 3:
        return None
    return float(np.percentile(v[both] - a[both], 5))


def build_audio(video: Path, out_wav: Path, style: dict, total: float, music: Path | None = None,
                sfx: list | None = None, brand_dir: Path | None = None) -> Path:
    """Ovozni yig'ib WAV ga yozadi. sfx: [{"at": soniya, "name": nom, "volume_db": son}].

    Tartib ("nutq birinchi"):
      1) Nutq (asl ovoz) ALOHIDA me'yorlanadi: musiqa yoki effekt qo'shilsa ham nutq balandligi o'zgarmaydi.
      2) Musiqa va effektlar alohida yig'iladi; nutq paytida o'zi pasayadi (sidechain).
      3) Nutq bor joylarda qo'shimchalar nutqdan kamida audio.voice_margin_db past ekanligi o'lchanadi;
         yetmasa qo'shimchalar yana pasaytiriladi.
      4) Ikkalasi qo'shiladi, cho'qqilar cheklanadi (limiter).
    """
    global LAST_REPORT
    LAST_REPORT = {}
    video = C.need_file(video, "Video")
    out_wav = C.guard_output(out_wav, video)
    work = out_wav.parent
    meta = C.ffprobe_info(video)
    a = style["audio"]
    scfg = style.get("sfx", {})
    sr = int(a.get("sample_rate", 48000))
    stereo = f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo"
    voice = str(a.get("voice", "off")).lower()
    if voice not in VOICE_PRESETS:
        raise C.MontajError(f"audio.voice noto'g'ri: {voice!r}. Mumkin: {', '.join(VOICE_PRESETS)}")

    # ---- 1) nutq zanjiri va uni alohida me'yorlash
    v_inputs = ["-i", str(video)]
    if meta["has_audio"]:
        chain = VOICE_PRESETS[voice]
        v_graph = f"[0:a]{stereo}" + (f",{chain}" if chain else "") + f",apad=whole_dur={total:.3f}[voice0]"
    else:
        v_inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", f"anullsrc=r={sr}:cl=stereo"]
        v_graph = f"[1:a]{stereo}[voice0]"
    target = f"loudnorm=I={a.get('loudnorm_i', -14)}:TP={a.get('loudnorm_tp', -1.5)}:LRA={a.get('loudnorm_lra', 11)}"
    measured = None
    if meta["has_audio"]:
        measured = R.measure_loudness(v_inputs, v_graph + f";[voice0]{target}:print_format=json,aresample={sr}[aout]", work)
    if measured:
        v_norm = (f"[voice0]{target}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
                  f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
                  f":offset={measured['target_offset']}:linear=true,aresample={sr}[vn]")
    else:
        v_norm = f"[voice0]aresample={sr}[vn]"
        if meta["has_audio"]:
            C.warn("Asl ovoz to'liq jim, loudnorm qo'llanmaydi.")

    events = []
    for ev in sorted(sfx or [], key=lambda e: float(e.get("at", 0))):
        at = float(ev.get("at", 0))
        if 0 <= at < total:
            events.append((at, find_sfx(ev.get("name", ""), brand_dir),
                           float(ev.get("volume_db", scfg.get("volume_db", -14)))))
    if music is not None:
        music = C.need_file(music, "Musiqa fayli")
        if not C.ffprobe_info(music)["has_audio"]:
            raise C.MontajError(f"Musiqa faylida ovoz yo'q: {music}")
    pcm = ["-c:a", "pcm_s16le", "-ar", str(sr)]

    if music is None and not events:
        # qo'shimcha yo'q: faqat me'yorlangan nutq
        C.run_ffmpeg_graph(v_inputs, v_graph + ";" + v_norm, ["-map", "[vn]", "-t", f"{total:.3f}"] + pcm + [str(out_wav)], work)
        if measured:
            C.info(f"       ovoz: {measured['input_i']} LUFS -> {a.get('loudnorm_i', -14)} LUFS")
        LAST_REPORT = {"additions": False}
        if scfg.get('cue_sheet',False):
            import review_tools
            report={'events':[],'mix':review_tools.metrics(out_wav,work),'note':'Speech only, no SFX/music events.'}
            C.write_json(report,work/'audio_cues.json')
            (work/'audio_cues.md').write_text('# Audio cue sheet\n\nSpeech only; no SFX/music events.\n',encoding='utf-8')
            review_tools.waveform(out_wav,[],work/'audio_waveform.png')
        return out_wav

    # ---- 2) nutq va qo'shimchalar alohida fayllarga
    inputs, parts, idx = list(v_inputs), [v_graph, v_norm], len(v_inputs) // 2
    if not meta["has_audio"]:
        idx = 2
    can_duck = bool(measured)
    duck_music = bool(a.get("music_ducking", True)) and can_duck and music is not None
    duck_sfx = bool(scfg.get("duck", True)) and can_duck and bool(events)
    taps = ["[vout]"] + (["[scm]"] if duck_music else []) + (["[scs]"] if duck_sfx else [])
    parts.append(f"[vn]asplit={len(taps)}" + "".join(taps) if len(taps) > 1 else "[vn]anull[vout]")
    buses = []
    if music is not None:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        vol = float(a.get("music_volume_db", -20))
        fade = max(0.0, min(float(a.get("music_fade_sec", 1.5)), total / 3))
        chain = f"[{idx}:a]{stereo},atrim=0:{total:.3f},volume={vol}dB"
        if fade > 0:
            chain += f",afade=t=in:st=0:d={min(0.5, fade):.3f},afade=t=out:st={max(0.0, total - fade):.3f}:d={fade:.3f}"
        if duck_music:
            parts.append(chain + "[mraw]")
            parts.append("[mraw][scm]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[music]")
        else:
            parts.append(chain + "[music]")
        buses.append("[music]")
        idx += 1
    if events:
        labels = []
        for n, (at, path, vol) in enumerate(events):
            inputs += ["-i", str(path)]
            parts.append(f"[{idx}:a]{stereo},volume={vol}dB,adelay={int(round(at * 1000))}:all=1[s{n}]")
            labels.append(f"[s{n}]")
            idx += 1
        mixed = "[sfxraw]" if duck_sfx else "[sfxbus]"
        if len(labels) > 1:
            parts.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0{mixed}")
        else:
            parts.append(f"{labels[0]}anull{mixed}")
        if duck_sfx:
            # nutq bor paytda effekt tez pasayadi, nutq tugashi bilan qaytadi
            parts.append("[sfxraw][scs]sidechaincompress=threshold=0.05:ratio=4:attack=5:release=160[sfxbus]")
        buses.append("[sfxbus]")
    if len(buses) > 1:
        parts.append("".join(buses) + f"amix=inputs={len(buses)}:duration=longest:dropout_transition=0:normalize=0[addraw]")
    else:
        parts.append(f"{buses[0]}anull[addraw]")
    parts.append(f"[addraw]apad=whole_dur={total:.3f},atrim=0:{total:.3f}[add]")
    v_wav, a_wav = work / "audio_voice.wav", work / "audio_additions.wav"
    C.run_ffmpeg_graph(inputs, ";".join(parts),
                       ["-map", "[vout]", "-t", f"{total:.3f}"] + pcm + [str(v_wav),
                        "-map", "[add]", "-t", f"{total:.3f}"] + pcm + [str(a_wav)], work)

    # ---- 3) nutq ustunligini o'lchash va kafolatlash
    required = float(a.get("voice_margin_db", 10))
    margin = voice_margin(v_wav, a_wav)
    reduce_db = 0.0
    if margin is not None and margin < required:
        reduce_db = min(24.0, required - margin)

    # ---- 4) yakuniy aralashma (nutq balandligi o'zgarmaydi), cho'qqilar cheklanadi
    limit = min(1.0, max(0.0625, 10 ** (float(a.get("loudnorm_tp", -1.5)) / 20)))
    C.run_ffmpeg_graph(["-i", str(v_wav), "-i", str(a_wav)],
                       f"[1:a]volume={-reduce_db:.2f}dB[a];[0:a][a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                       f"alimiter=limit={limit:.4f}:level=0:attack=5:release=60:latency=1[aout]",
                       ["-map", "[aout]", "-t", f"{total:.3f}"] + pcm + [str(out_wav)], work)
    final_margin = None if margin is None else round(margin + reduce_db, 1)
    LAST_REPORT = {"additions": True, "music": music is not None, "sfx": len(events), "required_db": required,
                   "margin_db": final_margin, "reduced_db": round(reduce_db, 1)}
    if scfg.get('cue_sheet',False):
        import review_tools
        report=review_tools.audio_report(v_wav,a_wav,out_wav,style,events,music,reduce_db,duck_sfx,duck_music,sfx)
        report['design_events']=sfx or []
        report['final_bus_margin_percentile_db']=final_margin
        C.write_json(report,work/'audio_cues.json')
        LAST_REPORT['cue_sheet']=str(work/'audio_cues.json')
    line = (f"       ovoz: nutq {measured['input_i']} LUFS -> {a.get('loudnorm_i', -14)} LUFS (alohida me'yorlandi)"
            if measured else "       ovoz: asl ovoz yo'q yoki jim")
    line += (f", musiqa: {music.name}" if music else "") + (f", effektlar: {len(events)}" if events else "")
    C.info(line)
    if final_margin is None:
        C.info("       qo'shimchalar nutq bilan ustma-ust tushmadi")
    else:
        C.info(f"       nutq paytida qo'shimchalar nutqdan {final_margin:g} dB past (talab: kamida {required:g} dB)"
               + (f"; buning uchun {reduce_db:.1f} dB pasaytirildi" if reduce_db > 0 else ""))
    for tmp in (v_wav, a_wav):
        tmp.unlink(missing_ok=True)
    return out_wav


def main() -> int:
    ap = argparse.ArgumentParser(description="Nutq + musiqa + effektlardan yakuniy ovoz yasaydi (WAV).")
    ap.add_argument("video")
    ap.add_argument("-o", "--output", help="Natija WAV (standart: temp/<nom>/final_audio.wav)")
    ap.add_argument("--music", help="Fon musiqa fayli")
    ap.add_argument("--brand", help="Brend nomi (brands/<nom>/)")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()
    style = C.load_style(args.style, args.brand)
    video = C.need_file(args.video, "Video")
    out = Path(args.output) if args.output else C.job_dir(video) / "final_audio.wav"
    build_audio(video, out, style, C.ffprobe_info(video)["duration"],
                Path(args.music) if args.music else None, None, C.brand_dir(style))
    C.info(f"Tayyor: {out}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
