"""Yakuniy ovozni yig'adi: nutq + musiqa (nutq paytida pasayadi) + ovoz effektlari, keyin loudnorm.

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


def build_audio(video: Path, out_wav: Path, style: dict, total: float, music: Path | None = None,
                sfx: list | None = None, brand_dir: Path | None = None) -> Path:
    """Ovozni yig'ib WAV ga yozadi. sfx: [{"at": soniya, "name": nom, "volume_db": son}]."""
    video = C.need_file(video, "Video")
    out_wav = C.guard_output(out_wav, video)
    meta = C.ffprobe_info(video)
    a = style["audio"]
    sr = int(a.get("sample_rate", 48000))
    inputs = ["-i", str(video)]
    idx = 1
    parts = []
    stereo = f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo"
    if meta["has_audio"]:
        parts.append(f"[0:a]{stereo},apad=whole_dur={total:.3f}[voice0]")
    else:
        inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", f"anullsrc=r={sr}:cl=stereo"]
        parts.append(f"[{idx}:a]{stereo}[voice0]")
        idx += 1
    mix = ["[voice]"]
    if music is not None:
        music = C.need_file(music, "Musiqa fayli")
        if not C.ffprobe_info(music)["has_audio"]:
            raise C.MontajError(f"Musiqa faylida ovoz yo'q: {music}")
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        vol = float(a.get("music_volume_db", -20))
        fade = max(0.0, min(float(a.get("music_fade_sec", 1.5)), total / 3))
        chain = f"[{idx}:a]{stereo},atrim=0:{total:.3f},volume={vol}dB"
        if fade > 0:
            chain += f",afade=t=in:st=0:d={min(0.5, fade):.3f},afade=t=out:st={max(0.0, total - fade):.3f}:d={fade:.3f}"
        if a.get("music_ducking", True) and meta["has_audio"]:
            parts.append("[voice0]asplit=2[voice][sc]")
            parts.append(chain + "[mraw]")
            parts.append("[mraw][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[music]")
        else:
            parts.append("[voice0]anull[voice]")
            parts.append(chain + "[music]")
        mix.append("[music]")
        idx += 1
    else:
        parts.append("[voice0]anull[voice]")
    default_db = float(style.get("sfx", {}).get("volume_db", -12))
    for n, ev in enumerate(sorted(sfx or [], key=lambda e: float(e.get("at", 0)))):
        at = float(ev.get("at", 0))
        if at < 0 or at >= total:
            continue
        path = find_sfx(ev.get("name", ""), brand_dir)
        inputs += ["-i", str(path)]
        ms = int(round(at * 1000))
        parts.append(f"[{idx}:a]{stereo},volume={float(ev.get('volume_db', default_db))}dB,"
                     f"adelay={ms}:all=1[s{n}]")
        mix.append(f"[s{n}]")
        idx += 1
    if len(mix) > 1:
        parts.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[mix]")
    else:
        parts.append("[voice]anull[mix]")

    target = f"loudnorm=I={a.get('loudnorm_i', -14)}:TP={a.get('loudnorm_tp', -1.5)}:LRA={a.get('loudnorm_lra', 11)}"
    graph = ";".join(parts)
    measured = R.measure_loudness(inputs, graph + f";[mix]{target}:print_format=json,aresample={sr}[aout]", out_wav.parent)
    if measured:
        tail = (f"[mix]{target}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
                f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
                f":offset={measured['target_offset']}:linear=true,aresample={sr}[aout]")
        C.info(f"       ovoz: {measured['input_i']} LUFS -> {a.get('loudnorm_i', -14)} LUFS"
               + (f", musiqa: {music.name}" if music else "") + (f", effektlar: {len(mix) - 1 - (1 if music else 0)}" if sfx else ""))
    else:
        tail = "[mix]anull[aout]"
        C.warn("Ovoz to'liq jim, loudnorm qo'llanmaydi.")
    C.run_ffmpeg_graph(inputs, graph + ";" + tail,
                       ["-map", "[aout]", "-t", f"{total:.3f}", "-c:a", "pcm_s16le", "-ar", str(sr), str(out_wav)],
                       out_wav.parent)
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
