"""Yakuniy videoni style.json dagi formatga keltirib chiqaradi.

Bajaradi: o'lcham (masalan 9:16, 1080x1920), fps, subtitr (ixtiyoriy), ovoz me'yori (loudnorm,
ikki bosqichli), musiqa (ixtiyoriy). Natija faqat output/ ga yoziladi.

Misol:
    python scripts/render.py temp/video/cut.mp4 -o output/video_final.mp4
    python scripts/render.py temp/video/cut.mp4 --subs temp/video/subs.ass --music musiqa.mp3
    python scripts/render.py temp/video/cut.mp4 --nvenc        # faqat NVIDIA karta bo'lsa
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import common as C
import subtitles as S


def video_chain(meta: dict, style: dict, subs_ass: Path | None) -> str:
    """Video filtr zanjiri: fps -> o'lchamga moslash -> subtitr -> format."""
    v = style["video"]
    W, H = int(C.style_get(style, "video", "width")), int(C.style_get(style, "video", "height"))
    if W % 2 or H % 2:
        raise C.MontajError(f"video.width va video.height juft son bo'lishi kerak (hozir {W}x{H}).")
    fps = float(C.style_get(style, "video", "fps"))
    fit = str(v.get("fit", "auto")).lower()
    if fit == "auto":
        src_ar = meta["width"] / meta["height"] if meta["height"] else W / H
        fit = "crop" if abs(src_ar / (W / H) - 1) <= 0.25 else "blur"
    if fit == "crop":
        body = f"[0:v]fps={fps:g},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    elif fit == "pad":
        body = (f"[0:v]fps={fps:g},scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
    elif fit == "blur":
        bw, bh = W // 4 // 2 * 2, H // 4 // 2 * 2
        body = (f"[0:v]fps={fps:g},split=2[bgsrc][fgsrc];"
                f"[bgsrc]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
                f"boxblur=8:2,scale={W}:{H}[bg];"
                f"[fgsrc]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        raise C.MontajError(f"video.fit noto'g'ri: {fit!r}. Mumkin: auto, crop, pad, blur.")
    body += ",setsar=1"
    if subs_ass:
        body += "," + S.subs_filter(subs_ass, style)
    return body + ",format=yuv420p[vout]"


def audio_chain(has_voice: bool, music_idx: int | None, style: dict, duration: float,
                loudnorm: str | None) -> str:
    """Ovoz zanjiri: nutq (+ musiqa, nutq paytida pasayadi) -> loudnorm."""
    a = style["audio"]
    sr = int(a.get("sample_rate", 48000))
    voice_src = "[0:a]" if has_voice else f"[{1 if music_idx != 1 else 2}:a]"
    parts = []
    if music_idx is None:
        parts.append(f"{voice_src}aresample={sr},aformat=channel_layouts=stereo[mix]")
    else:
        vol = float(a.get("music_volume_db", -20))
        fade = max(0.0, min(float(a.get("music_fade_sec", 1.5)), duration / 3))
        m = f"[{music_idx}:a]aresample={sr},aformat=channel_layouts=stereo,volume={vol}dB"
        if fade > 0:
            m += f",afade=t=in:st=0:d={min(0.5, fade):.3f},afade=t=out:st={max(0.0, duration - fade):.3f}:d={fade:.3f}"
        if a.get("music_ducking", True) and has_voice:
            parts.append(f"{voice_src}aresample={sr},aformat=channel_layouts=stereo,asplit=2[voice][sc]")
            parts.append(m + "[mraw]")
            parts.append("[mraw][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[music]")
        else:
            parts.append(f"{voice_src}aresample={sr},aformat=channel_layouts=stereo[voice]")
            parts.append(m + "[music]")
        parts.append("[voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")
    tail = "[mix]"
    tail += (loudnorm + f",aresample={sr}") if loudnorm else "anull"
    parts.append(tail + "[aout]")
    return ";".join(parts)


def measure_loudness(inputs: list, graph_audio: str, workdir: Path) -> dict | None:
    """1-bosqich: ovoz balandligini o'lchaydi. Jim (ovozsiz) bo'lsa None qaytaradi."""
    proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y"] + inputs +
                 ["-filter_complex", graph_audio, "-map", "[aout]", "-f", "null", "-"])
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not blocks:
        raise C.MontajError("loudnorm o'lchov natijasi topilmadi (ffmpeg chiqishi kutilgandek emas).")
    data = json.loads(blocks[-1])
    try:
        values = {k: float(data[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except (KeyError, ValueError):
        return None
    if not all(math.isfinite(x) for x in values.values()) or values["input_i"] < -69:
        return None
    return values


def encoder_args(style: dict, use_nvenc: bool) -> list:
    v = style["video"]
    if use_nvenc:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(v.get("nvenc_cq", 21)), "-b:v", "0"]
    return ["-c:v", str(v.get("codec", "libx264")), "-preset", str(v.get("preset", "medium")),
            "-crf", str(v.get("crf", 20))]


def render(video: Path, out_path: Path, style: dict, subs_ass: Path | None = None,
           music: Path | None = None, nvenc: bool | None = None) -> dict:
    """Yakuniy render. Natija haqida ma'lumot (ffprobe) qaytaradi."""
    video = C.need_file(video, "Video")
    out_path = C.guard_output(out_path, video)
    meta = C.ffprobe_info(video)
    if not meta["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    duration = meta["duration"]
    a = style["audio"]
    if music is None and a.get("music_file"):
        music = C.ROOT / a["music_file"] if not Path(a["music_file"]).is_absolute() else Path(a["music_file"])
    if music is not None:
        music = C.need_file(music, "Musiqa fayli")
        if not C.ffprobe_info(music)["has_audio"]:
            raise C.MontajError(f"Musiqa faylida ovoz yo'q: {music}")

    inputs = ["-i", str(video)]
    music_idx = None
    if music is not None:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        music_idx = 1
    if not meta["has_audio"]:  # ovozsiz video: natijada baribir (jim) ovoz yo'lakchasi bo'ladi
        C.warn("Videoda ovoz yo'q. Natijaga jim ovoz yo'lakchasi qo'shiladi.")
        inputs += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]

    target = f"loudnorm=I={a.get('loudnorm_i', -14)}:TP={a.get('loudnorm_tp', -1.5)}:LRA={a.get('loudnorm_lra', 11)}"
    C.info("  1/2: ovoz balandligi o'lchanmoqda...")
    measured = measure_loudness(inputs, audio_chain(meta["has_audio"], music_idx, style, duration,
                                                    target + ":print_format=json"), out_path.parent)
    loudnorm = None
    if measured:
        loudnorm = (f"{target}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
                    f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
                    f":offset={measured['target_offset']}:linear=true")
        C.info(f"       hozirgi balandlik {measured['input_i']} LUFS -> maqsad {a.get('loudnorm_i', -14)} LUFS")
    else:
        C.warn("Ovoz to'liq jim, loudnorm qo'llanmaydi.")

    graph = video_chain(meta, style, subs_ass) + ";" + audio_chain(
        meta["has_audio"], music_idx, style, duration, loudnorm)
    import hardware
    want_nvenc = hardware.encoder(style,nvenc)
    if want_nvenc and not C.has_encoder("h264_nvenc"):
        C.warn("Bu FFmpeg da h264_nvenc yo'q. CPU (libx264) ishlatiladi.")
        want_nvenc = False

    def attempt(use_nvenc: bool) -> None:
        post = ["-map", "[vout]", "-map", "[aout]"] + encoder_args(style, use_nvenc) + [
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", str(a.get("bitrate", "192k")),
            "-ar", str(a.get("sample_rate", 48000)), "-t", f"{duration:.3f}",
            "-movflags", "+faststart", str(out_path)]
        C.run_ffmpeg_graph(inputs, graph, post, out_path.parent, cwd=C.ROOT)

    C.info(f"  2/2: render ({'NVENC' if want_nvenc else 'CPU libx264'})...")
    if want_nvenc:
        try:
            attempt(True)
        except C.MontajError as exc:
            C.warn(f"NVENC ishlamadi (NVIDIA karta yoki drayver yo'q bo'lishi mumkin). CPU bilan qayta urinaman.\n{exc}")
            attempt(False)
    else:
        attempt(False)

    W, H = int(style["video"]["width"]), int(style["video"]["height"])
    out_meta, problems = C.verify_video(out_path, W, H, duration, need_audio=True)
    if problems:
        raise C.MontajError(f"Natija tekshiruvdan o'tmadi ({out_path.name}): " + "; ".join(problems))
    return out_meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Yakuniy videoni style.json formatida chiqaradi.")
    ap.add_argument("video", help="Kirish video (odatda temp/<nom>/cut.mp4)")
    ap.add_argument("-o", "--output", help="Natija (standart: output/<nom>_final.mp4)")
    ap.add_argument("--subs", help="Videoga yoziladigan ASS subtitr fayli (subtitles.py --ass-only chiqargan)")
    ap.add_argument("--music", help="Fon musiqa fayli (balandligi style.json: audio.music_volume_db)")
    ap.add_argument("--nvenc", action="store_true", help="NVIDIA karta bilan kodlash (bo'lmasa CPU ga qaytadi)")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style)
    video = C.need_file(args.video, "Video")
    out = Path(args.output) if args.output else C.OUTPUT_DIR / f"{C.output_stem(video.stem)}_final.mp4"
    subs = C.need_file(args.subs, "Subtitr fayli") if args.subs else None
    if subs and subs.suffix.lower() != ".ass":
        raise C.MontajError("--subs uchun .ass fayl kerak. Avval: python scripts/subtitles.py VIDEO SRT --ass-only")
    C.info(f"Render: {video.name} -> {out}")
    meta = render(video, out, style, subs, Path(args.music) if args.music else None,
                  True if args.nvenc else None)
    C.info(f"Tayyor: {out}\n  {meta['width']}x{meta['height']}, {meta['fps']:g} fps, "
           f"{meta['duration']:.2f}s, ovoz: {'bor' if meta['has_audio'] else 'yoq'} ({meta['acodec']})")
    return 0


if __name__ == "__main__":
    C.run_main(main)
