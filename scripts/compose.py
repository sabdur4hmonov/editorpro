"""Yakuniy videoni motion-grafika bilan yig'adi: zoom, subtitr animatsiyasi, grafik elementlar,
logotip, oxirgi kadr, musiqa va ovoz effektlari.

Misol:
    python scripts/compose.py temp/video/cut.mp4 --subs temp/video/subs.srt --approved
    python scripts/compose.py temp/video/cut.mp4 --subs temp/video/subs.srt --elements temp/video/elements.json \\
        --brand ilm-markazi --approved -o output/video_final.mp4
    python scripts/compose.py temp/video/cut.mp4 --subs temp/video/subs.srt --stills 1.5,4,9   # tez ko'rish

Qanday ishlaydi: ffmpeg videoni kadrlarga ochib beradi -> Python har kadrga zoom va qatlamlarni
chizadi -> ffmpeg kadrlarni ovoz bilan birga kodlaydi. Asl video o'zgarmaydi.

MUHIM: subtitr matni foydalanuvchi tasdiqlamaguncha videoga yozilmaydi (--approved).
--stills faqat ko'rish uchun rasm chiqaradi, unga tasdiq kerak emas.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import common as C
import audio_mix
import elements as E
import face as F
import motion as M
import render as R
from motion import cv2

EXIT_NEED_APPROVAL = 3
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}


# ---------------------------------------------------------------- kadrni formatga keltirish

def crop_window(meta: dict, W: int, H: int, face: dict | None) -> tuple | None:
    """Manbadan maqsad nisbatidagi oyna (cw, ch, x, y). Yuz topilgan bo'lsa shu atrofida."""
    sw, sh = meta["width"], meta["height"]
    target = W / H
    if sw / sh > target:
        ch, cw = sh, int(round(sh * target / 2)) * 2
    else:
        cw, ch = sw, int(round(sw / target / 2)) * 2
    cx = (face["cx"] if face else 0.5) * sw
    cy = (face["cy"] if face else 0.5) * sh
    x = int(min(max(0, cx - cw / 2), sw - cw))
    y = int(min(max(0, cy - ch * (0.40 if face else 0.5)), sh - ch))
    return cw, ch, x, y


def fit_graph(meta: dict, style: dict, face: dict | None) -> tuple[str, str]:
    """ffmpeg filtr grafigi: manba -> W x H, rgb24. (grafik, tanlangan usul) qaytaradi."""
    v = style["video"]
    W, H = int(C.style_get(style, "video", "width")), int(C.style_get(style, "video", "height"))
    if W % 2 or H % 2:
        raise C.MontajError(f"video.width va video.height juft son bo'lishi kerak (hozir {W}x{H}).")
    fps = float(C.style_get(style, "video", "fps"))
    fit = str(v.get("fit", "auto")).lower()
    src_ar = meta["width"] / meta["height"] if meta["height"] else W / H
    if fit == "auto":
        if abs(src_ar / (W / H) - 1) <= 0.25:
            fit = "crop"
        else:
            fit = "face" if face else "blur"
    pre = "[0:v]"
    if (meta.get("color_transfer") or "") in HDR_TRANSFERS:
        if C.has_filter("zscale") and C.has_filter("tonemap"):
            C.info("  HDR video aniqlandi: oddiy rang (SDR) ga o'tkaziladi.")
            pre += ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                    "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
            matrix, rng = "bt709", "tv"
        else:
            C.warn("HDR video, lekin bu FFmpeg da zscale/tonemap yo'q: ranglar xira chiqishi mumkin.")
            matrix, rng = "bt2020", "tv"
    else:
        cs = (meta.get("color_space") or "").lower()
        if cs in ("smpte170m", "bt470bg", "bt601"):
            matrix = "bt601"
        elif cs.startswith("bt2020"):
            matrix = "bt2020"
        elif cs == "bt709" or max(meta["width"], meta["height"]) >= 1280 or min(meta["width"], meta["height"]) >= 720:
            matrix = "bt709"
        else:
            matrix = "bt601"
        rng = "pc" if (meta.get("color_range") or "").lower() in ("pc", "jpeg", "full") else "tv"
    pre += f"fps={fps:g}"
    if fit in ("crop", "face"):
        cw, ch, x, y = crop_window(meta, W, H, face if fit == "face" or face else None)
        body = f"{pre},crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos"
    elif fit == "pad":
        body = (f"{pre},scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black")
    elif fit == "blur":
        bw, bh = W // 4 // 2 * 2, H // 4 // 2 * 2
        body = (f"{pre},split=2[bgsrc][fgsrc];"
                f"[bgsrc]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},boxblur=8:2,scale={W}:{H}[bg];"
                f"[fgsrc]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        raise C.MontajError(f"video.fit noto'g'ri: {fit!r}. Mumkin: auto, crop, face, pad, blur.")
    return body + f",setsar=1,scale=in_color_matrix={matrix}:in_range={rng},format=rgb24[fit]", fit


def face_in_output(meta: dict, W: int, H: int, face: dict | None, fit: str) -> tuple:
    """Yuz markazining chiqish kadridagi o'rni (0..1). Zoom shu nuqta atrofida bo'ladi."""
    if not face:
        return 0.5, 0.38
    sw, sh = meta["width"], meta["height"]
    fx, fy = face["cx"] * sw, face["cy"] * sh
    if fit in ("crop", "face"):
        cw, ch, x, y = crop_window(meta, W, H, face)
        return float(np.clip((fx - x) / cw, 0.2, 0.8)), float(np.clip((fy - y) / ch, 0.15, 0.7))
    scale = min(W / sw, H / sh)
    return (float(np.clip(((W - sw * scale) / 2 + fx * scale) / W, 0.2, 0.8)),
            float(np.clip(((H - sh * scale) / 2 + fy * scale) / H, 0.15, 0.7)))


# ---------------------------------------------------------------- zoom

def zoom_plan(style: dict, cuts: dict | None, base_dur: float) -> list:
    """Kesish joylarida navbatma-navbat yaqinlashtirish: [(boshi, oxiri, z0, z1)]."""
    z = style.get("zoom", {})
    if not z.get("enabled", True):
        return []
    punch = float(z.get("punch_in", 1.12))
    push = float(z.get("slow_push", 0.03))
    min_seg = float(z.get("min_segment", 0.8))
    bounds, pos = [], 0.0
    for seg in (cuts or {}).get("keep", []) or [{"start": 0.0, "end": base_dur}]:
        length = float(seg["end"]) - float(seg["start"])
        bounds.append((pos, pos + length))
        pos += length
    if len(bounds) < 2:
        bounds = [(0.0, base_dur)]
    plan, level, flip = [], 1.0, False
    for i, (t0, t1) in enumerate(bounds):
        if i > 0 and (t1 - t0) >= min_seg:
            flip = not flip
            level = punch if flip else 1.0
        z1 = level + push * min(1.0, (t1 - t0) / 4.0)
        plan.append((t0, t1, level, z1))
    return plan


def zoom_at(plan: list, manual: list, t: float, anchor: tuple) -> tuple:
    z, cx, cy = 1.0, anchor[0], anchor[1]
    for t0, t1, z0, z1 in plan:
        if t0 <= t < t1:
            z = z0 + (z1 - z0) * (t - t0) / max(0.001, t1 - t0)
            break
    for el in manual:
        s, e = float(el.get("start", 0)), float(el.get("end", 0))
        if s <= t < e:
            ease = max(0.001, float(el.get("ease", 0.25)))
            w = min(M.ease_in_out((t - s) / ease), M.ease_in_out((e - t) / ease))
            z = z + (float(el.get("scale", 1.2)) - z) * w
            cx = cx + (float(el.get("x", cx)) - cx) * w
            cy = cy + (float(el.get("y", cy)) - cy) * w
    return z, cx, cy


def zoom_frame(frame: np.ndarray, z: float, cx: float, cy: float) -> np.ndarray:
    if z <= 1.002:
        return frame
    H, W = frame.shape[:2]
    tx = float(np.clip((1 - z) * cx * W, W * (1 - z), 0))
    ty = float(np.clip((1 - z) * cy * H, H * (1 - z), 0))
    return cv2.warpAffine(frame, np.float32([[z, 0, tx], [0, z, ty]]), (W, H),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


# ---------------------------------------------------------------- yig'ish

def gather_sfx(style: dict, elements: list, cues: list, words: list | None) -> list:
    """Ovoz effektlari ro'yxati: elements.json dagi "sfx" lar + (yoqilgan bo'lsa) avtomatik."""
    events = [{"at": float(el.get("at", el.get("start", 0))), "name": el.get("name", "pop"),
               **({"volume_db": float(el["volume_db"])} if "volume_db" in el else {})}
              for el in elements if el.get("type") == "sfx"]
    cfg = style.get("sfx", {})
    if not cfg.get("enabled", False):
        return events
    auto = []
    if cfg.get("on_big_word"):
        import subtitles as S
        for cue in cues:
            tokens = E.parse_markup(E.fix_apostrophes(cue["text"]))
            times = S.word_times(cue, [w for w, _, _ in tokens], words) if tokens else []
            for (word, level, _), at in zip(tokens, times):
                if level in ("big", "big_accent", "huge"):
                    auto.append({"at": at, "name": cfg["on_big_word"]})
                    break  # bir bo'lakda bitta effekt
    if cfg.get("on_element"):
        for el in elements:
            if el.get("type") in ("image", "list", "choice", "stat", "voice", "title", "text"):
                auto.append({"at": max(0.0, float(el.get("start", 0)) - 0.05), "name": cfg["on_element"]})
    auto.sort(key=lambda e: e["at"])
    last = -9.0
    for ev in auto:
        if ev["at"] - last >= 0.3 and not any(abs(ev["at"] - x["at"]) < 0.15 for x in events):
            events.append(ev)
            last = ev["at"]
    return events


def read_elements(path: str | Path | None) -> list:
    if not path:
        return []
    data = C.read_json(path, "elements.json")
    items = data.get("elements") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise C.MontajError(f"{path}: 'elements' ro'yxat bo'lishi kerak.")
    return items


def build_layers(ctx: E.Ctx, style: dict, cues: list, words: list | None, elements: list,
                 base_dur: float, total: float) -> list:
    layers = E.build_elements(ctx, elements, base_dur)
    if cues and str(style.get("captions", {}).get("engine", "motion")) != "off":
        layers.append(E.CaptionLayer(ctx, cues, words, base_dur))
    logo = style.get("logo", {})
    if logo.get("file"):
        layers.append(E.LogoLayer(ctx, logo, base_dur))
    if total > base_dur:
        layers.append(E.EndcardLayer(ctx, style.get("endcard", {}), base_dur, total))
    layers.sort(key=lambda layer: layer.z)
    return layers


def _read_exact(stream, view: memoryview) -> int:
    got = 0
    while got < len(view):
        n = stream.readinto(view[got:])
        if not n:
            break
        got += n
    return got


def _tail(path: Path, lines: int = 12) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-lines:])
    except OSError:
        return ""


def compose(video: Path, out_path: Path | None, style: dict, srt: Path | None = None,
            words: list | None = None, cuts: dict | None = None, elements_file: Path | None = None,
            music: Path | None = None, nvenc: bool | None = None, stills: list | None = None,
            stills_out: Path | None = None) -> dict:
    """Asosiy funksiya. stills berilsa faqat shu vaqtlardagi kadrlarni rasm qilib chiqaradi."""
    video = C.need_file(video, "Video")
    meta = C.ffprobe_info(video)
    if not meta["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    W, H = int(style["video"]["width"]), int(style["video"]["height"])
    fps = float(style["video"]["fps"])
    work = C.job_dir(video) if not C.is_inside(video, C.TEMP_DIR) else video.parent
    brand_dir = C.brand_dir(style)
    ctx = E.Ctx(style, brand_dir)

    base_dur = meta["duration"]
    end_cfg = style.get("endcard", {})
    total = base_dur + (float(end_cfg.get("duration", 2.2)) if end_cfg.get("enabled") else 0.0)
    cues = C.parse_srt(srt) if srt else []
    elements = read_elements(elements_file)

    face = F.detect(video, quiet=True) if style.get("zoom", {}).get("face_aware", True) else None
    graph, fit = fit_graph(meta, style, face)
    ctx.anchor = face_in_output(meta, W, H, face, fit)
    plan = zoom_plan(style, cuts, base_dur)
    manual_zoom = [el for el in elements if el.get("type") == "zoom"]
    layers = build_layers(ctx, style, cues, words, elements, base_dur, total)
    ffmpeg = C.need_tool("ffmpeg")
    size = W * H * 3

    def render_frame(frame: np.ndarray, t: float) -> np.ndarray:
        if t < base_dur and (plan or manual_zoom):
            z, cx, cy = zoom_at(plan, manual_zoom, t, ctx.anchor)
            frame = zoom_frame(frame, z, cx, cy)
        for layer in layers:
            if layer.active(t):
                layer.draw(frame, t)
        return frame

    try:
        # ---------------- faqat rasmlar (tez ko'rish)
        if stills:
            shots = []
            for t in stills:
                t = max(0.0, min(float(t), total - 0.02))
                src_t = min(t, max(0.0, base_dur - 0.08))
                proc = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{src_t:.3f}",
                                       "-i", str(video), "-filter_complex", graph, "-map", "[fit]", "-frames:v", "1",
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
                if len(proc.stdout) < size:
                    raise C.MontajError(f"{t:.2f}s dagi kadrni olib bo'lmadi: "
                                        + proc.stderr.decode("utf-8", "replace")[-300:])
                frame = np.frombuffer(proc.stdout[:size], np.uint8).reshape(H, W, 3).copy()
                shots.append((t, render_frame(frame, t)))
            stills_out = C.guard_output(stills_out or (work / "stills.jpg"), video)
            th = 720
            tw = int(W * th / H)
            cols = min(4, len(shots))
            rows = (len(shots) + cols - 1) // cols
            sheet = np.zeros((rows * (th + 8) + 8, cols * (tw + 8) + 8, 3), np.uint8)
            for i, (t, frame) in enumerate(shots):
                small = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
                cv2.putText(small, f"{t:.2f}s", (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5, cv2.LINE_AA)
                cv2.putText(small, f"{t:.2f}s", (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
                r, c = divmod(i, cols)
                sheet[8 + r * (th + 8):8 + r * (th + 8) + th, 8 + c * (tw + 8):8 + c * (tw + 8) + tw] = small
            ok, buf = cv2.imencode(".jpg", sheet[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88])
            if not ok:
                raise C.MontajError("Rasmni saqlab bo'lmadi.")
            stills_out.write_bytes(buf.tobytes())
            return {"stills": str(stills_out), "count": len(shots)}

        # ---------------- to'liq render
        out_path = C.guard_output(out_path, video)
        C.info("  1/3: ovoz yig'ilmoqda...")
        if music is None and style["audio"].get("music_file"):
            music = ctx.asset(style["audio"]["music_file"], "Musiqa fayli")
        wav = audio_mix.build_audio(video, work / "final_audio.wav", style, total, music,
                                    gather_sfx(style, elements, cues, words), brand_dir)

        want_nvenc = bool(style["video"].get("use_nvenc", False)) if nvenc is None else nvenc
        if want_nvenc and not C.has_encoder("h264_nvenc"):
            C.warn("Bu FFmpeg da h264_nvenc yo'q. CPU (libx264) ishlatiladi.")
            want_nvenc = False
        dec_log, enc_log = work / "compose_decode.log", work / "compose_encode.log"
        total_frames = int(round(total * fps))
        C.info(f"  2/3: kadrlar yig'ilmoqda ({total_frames} ta kadr, {fit}"
               + (", yuz topildi" if face else "") + (f", {len(layers)} qatlam" if layers else "") + ")...")
        with open(dec_log, "wb") as dlog, open(enc_log, "wb") as elog:
            dec = subprocess.Popen([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(video),
                                    "-filter_complex", graph, "-map", "[fit]", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                   stdout=subprocess.PIPE, stderr=dlog, stdin=subprocess.DEVNULL, bufsize=size)
            enc_cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{fps:g}", "-i", "-",
                       "-i", str(wav), "-map", "0:v", "-map", "1:a",
                       "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"]
            enc_cmd += R.encoder_args(style, want_nvenc) + [
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                "-c:a", "aac", "-b:a", str(style["audio"].get("bitrate", "192k")),
                "-ar", str(style["audio"].get("sample_rate", 48000)), "-t", f"{total:.3f}",
                "-movflags", "+faststart", str(out_path)]
            enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=elog)
            buf = bytearray(size)
            view = memoryview(buf)
            frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            last = np.zeros((H, W, 3), np.uint8)
            began = shown = time.time()
            got_any = False
            try:
                for i in range(total_frames):
                    t = i / fps
                    if dec.stdout is not None and _read_exact(dec.stdout, view) == size:
                        got_any = True
                        last[:] = frame
                        cur = frame
                    else:
                        if not got_any:
                            raise C.MontajError("Videodan kadr o'qib bo'lmadi:\n" + _tail(dec_log))
                        cur = last.copy()   # video tugadi (oxirgi kadr): shu kadr ushlab turiladi
                    cur = render_frame(cur, t)
                    try:
                        enc.stdin.write(cur.tobytes() if cur is not frame else buf)
                    except (BrokenPipeError, OSError):
                        raise C.MontajError("Kodlovchi (ffmpeg) to'xtab qoldi:\n" + _tail(enc_log)) from None
                    if time.time() - shown > 5:
                        shown = time.time()
                        C.info(f"       {i + 1}/{total_frames} kadr ({(i + 1) * 100 // total_frames}%), "
                               f"{(i + 1) / (shown - began):.0f} kadr/s")
            finally:
                for stream in (enc.stdin, dec.stdout):
                    try:
                        stream.close()
                    except Exception:
                        pass
                dec.kill() if dec.poll() is None else None
                dec.wait()
            C.info("  3/3: fayl yozilmoqda...")
            code = enc.wait()
        if code != 0:
            if want_nvenc:
                C.warn("NVENC ishlamadi, CPU bilan qayta urinaman.")
                return compose(video, out_path, style, srt, words, cuts, elements_file, music, False)
            raise C.MontajError(f"Kodlash xato bilan tugadi (kod {code}):\n" + _tail(enc_log))
        out_meta, problems = C.verify_video(out_path, W, H, total, need_audio=True)
        if problems:
            raise C.MontajError(f"Natija tekshiruvdan o'tmadi ({out_path.name}): " + "; ".join(problems))
        out_meta["seconds"] = round(time.time() - began, 1)
        return out_meta
    finally:
        for layer in layers:
            layer.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Motion-grafikali yakuniy render (zoom, subtitr, elementlar, brend).")
    ap.add_argument("video", help="Kirish video (odatda temp/<nom>/cut.mp4)")
    ap.add_argument("-o", "--output", help="Natija (standart: output/<nom>_final.mp4)")
    ap.add_argument("--subs", help="Tekshirilgan SRT (matnda *katta*, **rangli**, !!juda katta!! belgilari bo'lishi mumkin)")
    ap.add_argument("--words", help="words.json (so'zlar nutq bilan birga ochilishi uchun)")
    ap.add_argument("--cuts", help="cuts.json (kesish joylarida zoom uchun)")
    ap.add_argument("--elements", help="elements.json (grafik elementlar ro'yxati)")
    ap.add_argument("--music", help="Fon musiqa fayli")
    ap.add_argument("--brand", help="Brend nomi (brands/<nom>/brand.json)")
    ap.add_argument("--stills", help="Faqat shu vaqtlardagi kadrlarni rasm qil, masalan: 1.5,4,9.2")
    ap.add_argument("--stills-out", help="Rasm fayli (standart: temp/<nom>/stills.jpg)")
    ap.add_argument("--approved", action="store_true", help="Foydalanuvchi subtitr matnini tasdiqlagan")
    ap.add_argument("--nvenc", action="store_true", help="NVIDIA karta bilan kodlash")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style, args.brand)
    video = C.need_file(args.video, "Video")
    srt = C.need_file(args.subs, "SRT fayl") if args.subs else None
    words = C.read_json(args.words, "So'zlar fayli").get("words") if args.words else None
    cuts = C.read_json(args.cuts, "Kesish rejasi") if args.cuts else None
    elements_file = C.need_file(args.elements, "elements.json") if args.elements else None

    if args.stills:
        try:
            times = [float(x) for x in args.stills.split(",") if x.strip()]
        except ValueError:
            raise C.MontajError("--stills uchun vergul bilan ajratilgan sonlar kerak, masalan: 1.5,4,9.2") from None
        res = compose(video, None, style, srt, words, cuts, elements_file, stills=times,
                      stills_out=Path(args.stills_out) if args.stills_out else None)
        C.info(f"Rasm tayyor ({res['count']} kadr): {res['stills']}")
        return 0

    if srt and not args.approved:
        import subtitles as S
        S.print_cues(C.parse_srt(srt))
        answer = C.confirm("\nMatn to'g'rimi? Videoga yozaymi? [y/N]: ")
        if answer is None:
            C.info("\nTASDIQ KERAK: yuqoridagi matnni foydalanuvchiga ko'rsating. "
                   "U tasdiqlagach, shu buyruqni --approved bilan qayta ishga tushiring.")
            return EXIT_NEED_APPROVAL
        if not answer:
            C.info(f"To'xtatildi. Matnni {srt} faylida tuzating va qayta ishga tushiring.")
            return EXIT_NEED_APPROVAL

    name = video.parent.name if C.is_inside(video, C.TEMP_DIR) and video.stem == "cut" else video.stem
    out = Path(args.output) if args.output else C.OUTPUT_DIR / f"{C.output_stem(name)}_final.mp4"
    C.info(f"Compose: {video.name} -> {out}")
    meta = compose(video, out, style, srt, words, cuts, elements_file,
                   Path(args.music) if args.music else None, True if args.nvenc else None)
    C.info(f"Tayyor ({meta['seconds']}s): {out}\n  {meta['width']}x{meta['height']}, {meta['fps']:g} fps, "
           f"{meta['duration']:.2f}s, ovoz: {'bor' if meta['has_audio'] else 'yoq'} ({meta['acodec']})")
    return 0


if __name__ == "__main__":
    C.run_main(main)
