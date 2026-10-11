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
import copy
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


def draft_style(style: dict) -> dict:
    """Qoralama uchun nusxa: nisbat saqlanadi, final sozlamalariga tegilmaydi."""
    out = copy.deepcopy(style)
    cfg = out.get("preview", {})
    fps_cfg = cfg.get("fps", 15)
    # "source": the draft keeps the output (source) rate; only size and encode get cheaper
    height, fps = int(cfg.get("height", 640)), float(C.fps_of(out) if str(fps_cfg).lower() == "source" else fps_cfg)
    if not 240 <= height <= 1080 or height % 2 or not 1 <= fps <= 60:
        raise C.MontajError("preview.height: 240..1080 juft son, preview.fps: 1..60 bo'lishi kerak.")
    v = out["video"]
    height = min(height, int(v["height"]))
    width = max(2, round(int(v["width"]) * height / int(v["height"]) / 2) * 2)
    v.update(width=width, height=height, fps=min(fps, C.fps_of(out)),
             crf=int(cfg.get("crf", 28)), preset=str(cfg.get("preset", "ultrafast")))
    out["_draft"] = True
    return out


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


LOOK_PRESETS = {
    "off": {},
    "natural": {"contrast": 1.04, "saturation": 1.06, "sharpen": 0.35},
    "warm": {"contrast": 1.05, "saturation": 1.08, "warmth": 0.25, "sharpen": 0.35},
    "cool": {"contrast": 1.05, "saturation": 1.04, "warmth": -0.2, "sharpen": 0.35},
    "punchy": {"contrast": 1.10, "saturation": 1.18, "sharpen": 0.5, "vignette": 0.2},
    "film": {"contrast": 1.06, "saturation": 0.96, "warmth": 0.12, "vignette": 0.3, "grain": 4},
}


def look_filters(style: dict, brand_dir: Path | None) -> tuple[str, str]:
    """Rang ishlovi (color grade): (YUV bosqichidagi filtrlar, RGB bosqichidagi LUT filtri)."""
    cfg = dict(style.get("look", {}))
    if not cfg.get("enabled", True):
        return "", ""
    preset = str(cfg.get("preset", "natural"))
    if preset not in LOOK_PRESETS:
        raise C.MontajError(f"look.preset noto'g'ri: {preset!r}. Mumkin: {', '.join(LOOK_PRESETS)}")
    look = dict(LOOK_PRESETS[preset])
    look.update({k: v for k, v in cfg.items() if k not in ("preset", "enabled") and not k.startswith("_") and v is not None})
    parts = []
    eq = []
    for key, default in (("contrast", 1.0), ("saturation", 1.0), ("brightness", 0.0), ("gamma", 1.0)):
        value = float(look.get(key, default))
        if abs(value - default) > 0.001:
            eq.append(f"{key}={value:.3f}")
    if eq:
        parts.append("eq=" + ":".join(eq))
    warmth = max(-1.0, min(1.0, float(look.get("warmth", 0))))
    if abs(warmth) > 0.01 and C.has_filter("colortemperature"):
        parts.append(f"colortemperature=temperature={int(6500 - warmth * 2200)}:mix=1")
    if float(look.get("sharpen", 0)) > 0.01:
        parts.append(f"unsharp=5:5:{min(1.5, float(look['sharpen'])):.2f}:5:5:0.0")
    if float(look.get("vignette", 0)) > 0.01:
        parts.append(f"vignette=angle={min(1.0, float(look['vignette'])) * 0.8:.3f}")
    if float(look.get("grain", 0)) > 0.1:
        parts.append(f"noise=alls={min(12, int(round(float(look['grain']))))}:allf=t+u")
    lut = ""
    if look.get("lut"):
        lp = Path(str(look["lut"]))
        candidates = [lp] if lp.is_absolute() else ([brand_dir / lp] if brand_dir else []) + [C.ROOT / lp]
        found = next((c for c in candidates if c.is_file()), None)
        if found is None:
            raise C.MontajError(f"LUT fayli topilmadi: {look['lut']} (.cube fayl brend papkasida yoki loyihada bo'lsin)")
        if not C.has_filter("lut3d"):
            C.warn("Bu FFmpeg da lut3d filtri yo'q, LUT qo'llanmaydi.")
        else:
            lut = "lut3d=file=" + C.filter_path(found, cwd=C.ROOT) + ":interp=tetrahedral"
    return ",".join(parts), lut


def fit_graph(meta: dict, style: dict, face: dict | None, brand_dir: Path | None = None) -> tuple[str, str]:
    """ffmpeg filtr grafigi: manba -> W x H, rgb24. (grafik, tanlangan usul) qaytaradi."""
    style = C.resolve_fps(style, meta=meta)
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
    pre += f"fps={C.fps_expr(fps)}"
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
    grade, lut = look_filters(style, brand_dir)
    if grade:
        body += "," + grade
    body += f",setsar=1,scale=in_color_matrix={matrix}:in_range={rng}"
    if lut:
        body += ",format=gbrp," + lut
    return body + ",format=rgb24[fit]", fit


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
    import motion_language as ML
    strength = ML.config(style)["zoom_strength"]
    if strength is not None:                       # brand motion preset: zoom strength multiplier
        punch, push = 1 + (punch - 1) * float(strength), push * float(strength)
    min_seg = float(z.get("min_segment", 0.8))
    bounds, pos = [], 0.0
    speed = float((cuts or {}).get("speed", 1.0)) or 1.0
    for seg in (cuts or {}).get("keep", []) or [{"start": 0.0, "end": base_dur}]:
        length = (float(seg["end"]) - float(seg["start"])) / speed
        bounds.append((pos, pos + length))
        pos += length
    if len(bounds) < 2:
        bounds = [(0.0, base_dur)]
    if style.get("_variety") and ML.variety_cfg(style)["enabled"]:
        return ML.zoom_variety(style, bounds, punch, push, min_seg)[0]
    plan, level, flip = [], 1.0, False
    for i, (t0, t1) in enumerate(bounds):
        if i > 0 and (t1 - t0) >= min_seg:
            flip = not flip
            level = punch if flip else 1.0
        z1 = level + push * min(1.0, (t1 - t0) / 4.0)
        plan.append((t0, t1, level, z1))
    return plan


def zoom_at(plan: list, manual: list, t: float, anchor: tuple, ease: bool = False) -> tuple:
    """ease: the push inside a cut segment eases in and out instead of a constant-speed crawl."""
    z, cx, cy = 1.0, anchor[0], anchor[1]
    for t0, t1, z0, z1 in plan:
        if t0 <= t < t1:
            p = (t - t0) / max(0.001, t1 - t0)
            z = z0 + (z1 - z0) * (M.ease_in_out(p) if ease else p)
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
    if 'event_map' in style.get('sfx',{}):
        import sound_design
        return sound_design.gather(style,elements,cues,words,C.brand_dir(style))
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
            tokens = E.parse_markup(E.fix_apostrophes(E.split_cue_tag(cue["text"])[2]))
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
    gap = max(0.3, float(cfg.get("min_gap_sec", 1.5)))     # effektlar juda zich bo'lmasin
    for ev in auto:
        if ev["at"] - last >= gap and not any(abs(ev["at"] - x["at"]) < gap / 2 for x in events):
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
        import graphics_ideas
        layers[-1].hidden_spans = graphics_ideas.hidden_spans(elements)
        layers[-1].el_ref, layers[-1].el_type = "captions", "captions"
    logo = style.get("logo", {})
    if logo.get("file"):
        layers.append(E.LogoLayer(ctx, logo, base_dur))
    if style.get("progress_bar", {}).get("enabled"):
        layers.append(E.ProgressLayer(ctx, style["progress_bar"], total))
    if total > base_dur:
        layers.append(E.EndcardLayer(ctx, style.get("endcard", {}), base_dur, total))
    layers.sort(key=lambda layer: layer.z)
    return layers


def check_export(path: Path, style: dict, meta: dict | None = None) -> list:
    """Platforma talablari bo'yicha tekshiruv: [(nom, holat, tafsilot)]. holat: ok | ogoh | xato."""
    import json as _json
    import re as _re
    plat = style.get("platform", {})
    meta = meta or C.ffprobe_info(path)
    rows = []

    def row(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        rows.append((name, "ok" if ok else ("ogoh" if warn_only else "xato"), detail))

    W, H = int(style["video"]["width"]), int(style["video"]["height"])
    row("O'lcham", (meta["width"], meta["height"]) == (W, H), f"{meta['width']}x{meta['height']}")
    row("Video kodek", meta["vcodec"] in ("h264", "hevc") and meta.get("pix_fmt") == "yuv420p",
        f"{meta['vcodec']}, {meta.get('pix_fmt')}")
    row("Kadr tezligi", (1 if style.get("_draft") else 23) <= meta["fps"] <= float(plat.get("fps_max", 60)), f"{meta['fps']:g} fps")
    max_dur = float(plat.get("max_duration", 90))
    row("Davomiylik", meta["duration"] <= max_dur, f"{meta['duration']:.1f}s (chegara {max_dur:g}s)", warn_only=True)
    row("Ovoz", meta["has_audio"] and meta["acodec"] == "aac", f"{meta['acodec']}, {meta['sample_rate']} Hz")
    if meta["has_audio"]:
        proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-i", str(path), "-vn",
                      "-af", "loudnorm=print_format=json", "-f", "null", "-"])
        blocks = _re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, _re.S)
        try:
            data = _json.loads(blocks[-1])
            lufs, tp = float(data["input_i"]), float(data["input_tp"])
            target, tol = float(plat.get("lufs", -14)), float(plat.get("lufs_tolerance", 2.0))
            row("Balandlik", abs(lufs - target) <= tol, f"{lufs:.1f} LUFS (maqsad {target:g} +-{tol:g})", warn_only=True)
            row("Eng baland nuqta", tp <= float(plat.get("true_peak", -1.0)) + 0.3, f"{tp:.1f} dBTP", warn_only=True)
        except (IndexError, KeyError, ValueError):
            pass  # jim ovoz: o'lchab bo'lmaydi
    return rows


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


def visual_cut_times(cuts: dict | None, elements: list) -> list:
    """Output-time cuts captions must respect: applied edit boundaries plus full/split b-roll in/out."""
    import quality_gate
    times = list(quality_gate.editorial_cut_times(cuts) or [])
    for el in elements:
        if el.get("type") == "broll" and str(el.get("mode", "full")) in ("full", "split") and "end" in el:
            times += [float(el.get("start", 0)), float(el["end"])]
    return sorted({round(t, 3) for t in times if t > 0})


class CutMatch:
    """look.match_cuts (off by default): at an editorial jump cut the new shot starts at the previous shot's
    brightness (gain 0.9-1.1) and eases back to its own level over look.match_seconds (0.6 s)."""

    def __init__(self, style: dict, cuts: dict | None, fps: float):
        look = style.get("look", {}) or {}
        self.on = bool(look.get("match_cuts")) and bool(cuts)
        self.span = max(1, int(round(float(look.get("match_seconds", .6)) * fps)))
        import quality_gate
        self.cuts = {int(round(t * fps)) for t in (quality_gate.editorial_cut_times(cuts) or [])} if self.on else set()
        self.prev, self.active = None, None

    def apply(self, frame: np.ndarray, index: int) -> np.ndarray:
        level = float(frame[::8, ::8].mean())
        if index in self.cuts and self.prev:
            self.active = (index, min(1.1, max(.9, self.prev / max(level, 1.0))))
        out = frame
        if self.active:
            c, g = self.active
            p = M.ease_in_out((index - c) / self.span)
            gain = g ** (1 - p)
            if p >= 1:
                self.active = None
            elif abs(gain - 1) > .002:
                out = cv2.convertScaleAbs(frame, alpha=gain)
        self.prev = float(out[::8, ::8].mean())
        return out


def grain_filter(style: dict) -> str:
    """Light temporal luma grain against banding in flat gradients (video.grain 0..6; absent/0: none)."""
    g = float(style.get("video", {}).get("grain", 0) or 0)
    if not 0 <= g <= 6:
        raise C.MontajError("video.grain: 0..6 (1-2 yengil).")
    return f",noise=c0s={g:g}:c0f=t+u" if g > 0 and not style.get("_draft") else ""


def variety_summary(style: dict, cap, element_moves: list, cuts, base_dur: float, work: Path) -> dict:
    """Per video: count of each animation and the longest run of identical consecutive ones."""
    import motion_language as ML
    cues = [p["enter"] for p in (getattr(cap, "variety", None) or []) if p["enter"] != "explicit"]
    z = style.get("zoom", {})
    zoom_moves = []
    if z.get("enabled", True) and cuts and len(cuts.get("keep", [])) > 1:
        speed, pos, bounds = float(cuts.get("speed", 1) or 1), 0.0, []
        for seg in cuts["keep"]:
            length = (float(seg["end"]) - float(seg["start"])) / speed
            bounds.append((pos, pos + length)); pos += length
        zoom_moves = ML.zoom_variety(style, bounds, float(z.get("punch_in", 1.12)), float(z.get("slow_push", .03)),
                                     float(z.get("min_segment", .8)))[1]
    other = sorted(element_moves + zoom_moves)
    rep = {"plan": style["_variety"], "captions": ML.variety_report(cues), "motion": ML.variety_report([m for _, _, m in other]),
           "caption_rows": getattr(cap, "variety", None), "motion_rows": other}
    C.write_json(rep, work / "motion_variety_report.json")
    return {"captions": rep["captions"], "motion": rep["motion"]}


def compose(video: Path, out_path: Path | None, style: dict, srt: Path | None = None,
            words: list | None = None, cuts: dict | None = None, elements_file: Path | None = None,
            music: Path | None = None, nvenc: bool | None = None, stills: list | None = None,
            stills_out: Path | None = None, draft: bool = False, trace: tuple | None = None) -> dict:
    """Asosiy funksiya. stills berilsa faqat shu vaqtlardagi kadrlarni rasm qilib chiqaradi.

    trace=(t0, t1): faqat o'lchov - shu oraliq kadrlari chiziladi (kodlanmaydi), har blit geometriyasi
    qaytariladi (review_tools lint). Render natijasiga ta'sir qilmaydi.
    """
    video = C.need_file(video, "Video")
    meta = C.ffprobe_info(video)
    style = C.resolve_fps(style, meta=meta)
    if draft:
        style = draft_style(style)
    if not meta["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    W, H = int(style["video"]["width"]), int(style["video"]["height"])
    fps = float(style["video"]["fps"])
    work = C.job_dir(video) if not C.is_inside(video, C.TEMP_DIR) else video.parent
    brand_dir = C.brand_dir(style)
    import motion_language as ML
    style = ML.choose(style,work)
    style = ML.setup_variety(style, work)
    ctx = E.Ctx(style, brand_dir)
    mc = ML.config(style)
    M.SUBPIXEL = bool(mc["subpixel"])
    blur_cfg = mc["motion_blur"] if mc["motion_blur"]["enabled"] else None
    # a record-only trace never changes pixels; it feeds motion lint and the smoothness check of every render
    M.TRACE = M.Trace(blur_cfg) if (trace or M.SUBPIXEL or blur_cfg or not stills) else None

    base_dur = meta["duration"]
    end_cfg = style.get("endcard", {})
    total = base_dur + (float(end_cfg.get("duration", 2.2)) if end_cfg.get("enabled") else 0.0)
    cues = C.parse_srt(srt) if srt else []
    elements = read_elements(elements_file)

    import energy_curve
    style, elements = energy_curve.prepare(video, words, cues, elements, style, work)
    ctx.style = style
    elements, element_moves = ML.element_plan(style, elements)

    import studio
    precheck = studio.preflight(style, cues, elements, base_dur, validate_layers=False)
    C.write_json(precheck, work / "preflight.json")
    if precheck["errors"]:
        raise C.MontajError("PREFLIGHT: " + "; ".join(precheck["errors"]))
    for warning in precheck["warnings"]:
        ctx.note("Preflight: " + warning["text"])
    segmenter = None
    if any(el.get("behind_person") for el in elements):
        from person_mask import PersonMask
        segmenter = PersonMask(style.get('hardware',{}).get('onnx','auto'))

    face = F.detect(video, quiet=True, style=style) if style.get("zoom", {}).get("face_aware", True) else None
    graph, fit = fit_graph(meta, style, face, brand_dir)
    ctx.anchor = face_in_output(meta, W, H, face, fit)
    plan = zoom_plan(style, cuts, base_dur)
    ctx.cut_times = visual_cut_times(cuts, elements)
    zoom_ease = bool(mc["cuts"]["enabled"] and mc["cuts"]["zoom_ease"]) or bool(style.get("_variety"))
    manual_zoom = [el for el in elements if el.get("type") == "zoom"]
    layers = build_layers(ctx, style, cues, words, elements, base_dur, total)
    behind = [layer for layer in layers if getattr(layer, "behind_person", False)]
    ffmpeg = C.need_tool("ffmpeg")
    size = W * H * 3

    monitor = None
    if style.get("quality", {}).get("face_safety", True) and not stills:
        import face_safety
        monitor = face_safety.FaceMonitor(ctx, layers, style)

    match = CutMatch(style, cuts, fps)

    def render_frame(frame: np.ndarray, t: float, index: int | None = None) -> np.ndarray:
        if match.on and index is not None and t < base_dur:
            frame = match.apply(frame, index)
        tracer = M.TRACE
        if tracer is not None:
            tracer.begin_frame(index if index is not None else int(round(t * fps)))
        if t < base_dur and (plan or manual_zoom):
            z, cx, cy = zoom_at(plan, manual_zoom, t, ctx.anchor, zoom_ease)
            frame = zoom_frame(frame, z, cx, cy)
        measuring = False
        if behind:
            original = frame.copy()
            active_behind = [layer for layer in behind if layer.active(t)]
            if active_behind:
                alpha = segmenter.infer(original)
                for layer in active_behind:
                    layer.draw(frame, t)
                from person_mask import restore_person
                restore_person(frame, original, alpha)
        for layer in layers:
            if layer in behind:
                continue
            if layer.active(t):
                if tracer is not None:
                    tracer.begin_layer(getattr(layer, "el_ref", type(layer).__name__))
                if monitor is not None and index is not None:
                    kind = getattr(layer, 'el_type', '')
                    if kind == 'flash' and measuring:
                        monitor.after(frame, t, index)
                        measuring = False
                    elif kind not in ('stage', 'scene', 'broll', 'grade', 'flash') and not measuring:
                        monitor.before(frame, t)
                        measuring = True
                layer.draw(frame, t)
        if monitor is not None and index is not None and measuring:
            monitor.after(frame, t, index)
        if style.get("_draft"):
            cv2.putText(frame, "QORALAMA", (10, max(18, int(H * 0.04))), cv2.FONT_HERSHEY_SIMPLEX,
                        max(0.4, H / 1920), (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    try:
        # ---------------- faqat o'lchov (motion lint): kadrlar chiziladi, kodlanmaydi
        if trace:
            t0, t1 = max(0.0, float(trace[0])), min(total, float(trace[1]))
            first, stop = int(round(t0 * fps)), int(round(t1 * fps))
            dec = subprocess.Popen([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{first / fps:.4f}",
                                    "-i", str(video), "-filter_complex", graph, "-map", "[fit]", "-f", "rawvideo",
                                    "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   stdin=subprocess.DEVNULL, bufsize=size, cwd=str(C.ROOT))
            buf = bytearray(size)
            view = memoryview(buf)
            held = np.zeros((H, W, 3), np.uint8)
            try:
                for i in range(first, stop):
                    if i / fps < base_dur and _read_exact(dec.stdout, view) == size:
                        held[:] = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
                    render_frame(held.copy(), i / fps, i)
            finally:
                dec.stdout.close()
                dec.kill() if dec.poll() is None else None
                dec.wait()
            return {"rows": M.TRACE.rows, "fps": fps, "W": W, "H": H, "k": ctx.k, "cuts": ctx.cut_times,
                    "range": [first / fps, stop / fps], "notes": list(ctx.notes)}
        # ---------------- faqat rasmlar (tez ko'rish)
        if stills:
            shots = []
            for t in stills:
                t = max(0.0, min(float(t), total - 0.02))
                src_t = min(t, max(0.0, base_dur - 0.08))
                proc = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{src_t:.3f}",
                                       "-i", str(video), "-filter_complex", graph, "-map", "[fit]", "-frames:v", "1",
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, cwd=str(C.ROOT))
                if len(proc.stdout) < size:
                    raise C.MontajError(f"{t:.2f}s dagi kadrni olib bo'lmadi: "
                                        + proc.stderr.decode("utf-8", "replace")[-300:])
                frame = np.frombuffer(proc.stdout[:size], np.uint8).reshape(H, W, 3).copy()
                frame = render_frame(frame, t)
                sf = ctx.safe   # xavfsiz zona chegarasi (faqat ko'rish rasmida chiziladi, videoga tushmaydi)
                cv2.rectangle(frame, (int(sf["left"] * W), int(sf["top"] * H)),
                              (int((1 - sf["right"]) * W), int((1 - sf["bottom"]) * H)), (0, 255, 255), 2)
                shots.append((t, frame))
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
            return {"stills": str(stills_out), "count": len(shots), "notes": list(ctx.notes)}

        # ---------------- to'liq render
        out_path = C.guard_output(out_path, video)
        C.info("  1/3: ovoz yig'ilmoqda...")
        if music is None and style["audio"].get("music_file"):
            music = ctx.asset(style["audio"]["music_file"], "Musiqa fayli")
        paired=bool(style.get('sfx',{}).get('mixes')) and style.get('sfx',{}).get('enabled')
        audio_dir=work/'audio_mixes'/out_path.stem/style['sfx'].get('profile','subtle') if paired else work
        wav = audio_mix.build_audio(video, audio_dir / "final_audio.wav", style, total, music,
                                    gather_sfx(style, elements, cues, words), brand_dir)

        import hardware
        want_nvenc = hardware.encoder(style,nvenc)
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
                                   stdout=subprocess.PIPE, stderr=dlog, stdin=subprocess.DEVNULL, bufsize=size,
                                   cwd=str(C.ROOT))
            enc_cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", C.fps_expr(fps), "-i", "-",
                       "-i", str(wav), "-map", "0:v", "-map", "1:a",
                       "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" + grain_filter(style)]
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
            import zlib
            hashes = []
            try:
                for i in range(total_frames):
                    t = i / fps
                    if dec.stdout is not None and _read_exact(dec.stdout, view) == size:
                        got_any = True
                        last[:] = frame
                        cur = frame
                        hashes.append(zlib.crc32(frame[::24, ::24].tobytes()))
                    else:
                        hashes.append(None)
                        if not got_any:
                            raise C.MontajError("Videodan kadr o'qib bo'lmadi:\n" + _tail(dec_log))
                        cur = last.copy()   # video tugadi (oxirgi kadr): shu kadr ushlab turiladi
                    cur = render_frame(cur, t, i)
                    try:
                        enc.stdin.write(cur.tobytes() if cur is not frame else buf)
                    except (BrokenPipeError, OSError):
                        if want_nvenc:
                            break  # enc.wait below reports failure and retries the whole job on CPU.
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
        out_meta["draft"] = bool(style.get("_draft"))
        out_meta["notes"] = list(ctx.notes)
        out_meta["checks"] = check_export(out_path, style, out_meta)
        if monitor is not None:
            import face_safety
            safety = monitor.report()
            C.write_json(dict(safety, video=str(out_path)), work / "face_safety.json")
            out_meta["face_safety"] = {k: safety[k] for k in ("ok", "max_cover", "frames_checked", "frames_with_face", "limit", "verification")}
            safety_state = 'ogoh' if safety['verification']=='unverified_no_face' and safety['detector_available'] else ('ok' if safety['ok'] else 'xato')
            out_meta["checks"].append(("Yuz xavfsizligi", safety_state,
                                       face_safety.summary(safety).split(": ", 1)[1]))
        rep = audio_mix.LAST_REPORT
        if rep.get("additions") and rep.get("margin_db") is not None:
            # musiqa/effektlar nutqni bosib ketmaganini ko'rsatadigan o'lchov
            out_meta["checks"].append(("Nutq ustunligi", "ok" if rep["margin_db"] >= rep["required_db"] - 0.5 else "ogoh",
                                       f"qo'shimchalar nutqdan {rep['margin_db']:g} dB past (talab {rep['required_db']:g} dB)"
                                       + (f", {rep['reduced_db']:g} dB pasaytirildi" if rep.get("reduced_db") else "")))
        if paired:
            import sound_design
            out_meta['mixes']=sound_design.alternate_mixes(video,out_path,work,style,total,elements,cues,words,music,
                                                          brand_dir,dict(rep))
        out_meta['audio']=dict(rep)
        if M.TRACE is not None and M.TRACE.rows:
            import review_tools
            lint = review_tools.lint_rows(M.TRACE.rows, fps, ctx.k, ctx.cut_times)
            C.write_json(lint, work / "motion_lint.json")
            out_meta['motion_lint'] = lint['summary']
        cap = next((layer for layer in layers if getattr(layer, 'el_type', '') == 'captions'), None)
        if cap is not None and cap.contrast:
            out_meta['caption_contrast'] = cap.contrast
        if style.get('_variety'):
            out_meta['variety'] = variety_summary(style, cap, element_moves, cuts, base_dur, work)
        import quality_gate
        lint_full = C.read_json(work / "motion_lint.json") if (work / "motion_lint.json").is_file() and M.TRACE is not None else {}
        smooth = quality_gate.smoothness(
            fps, C.source_fps(meta)[0], hashes, wav, quality_gate.editorial_cut_times(cuts) or [], cues, words,
            dict(lint_full.get('summary', {}), flag_rows=lint_full.get('flags', [])) if lint_full else None,
            out_meta.get('variety'), [it['cfg'].get('anim_main', it['cfg'].get('animation')) for it in cap.items] if cap else None,
            out_path)
        C.write_json(dict(smooth, video=str(out_path)), work / "smoothness.json")
        out_meta['smoothness'] = {k: smooth[k] for k in ('held_frames', 'output_holds', 'drift_jitter_px', 'warnings')}
        out_meta['smoothness'].update(cuts=smooth['cuts'], caption_lag=smooth['caption_lag'], fps=fps, source_fps=smooth['source_fps'])
        for w in smooth['warnings']:
            C.warn("SMOOTH: " + w)
        out_meta["checks"].append(("Silliqlik", "ok" if not smooth['warnings'] else "ogoh",
                                   f"{len(smooth['warnings'])} ogohlantirish, takror kadr {smooth['held_frames']} (temp/.../smoothness.json)"))
        if (work/'edit_plan.json').is_file():
            import quality_gate
            rendered_cuts = quality_gate.editorial_cut_times(cuts)
            loudness_row = next((r for r in out_meta['checks'] if r[0]=='Balandlik'), None)
            if loudness_row:
                out_meta['integrated_lufs'] = float(loudness_row[2].split()[0])
            quality = quality_gate.evaluate(style, cues, elements, base_dur, C.read_json(work/'edit_plan.json'), out_meta, rendered_cuts)
            C.write_json(quality, work/'quality_gate.json')
            (work/'quality_gate.md').write_text(quality_gate.markdown(quality), encoding='utf-8')
            out_meta['quality_gate'] = dict(status=quality['status'], score=quality['score'], measured=quality['known'], total=quality['total'])
            C.info(f"QUALITY: {quality['status']}; {quality['score']}; {quality['known']}/{quality['total']} measured")
            if style.get('quality', {}).get('enforce_final') and not style.get('_draft') and quality['fix_list']:
                raise C.MontajError('QUALITY: final tasdiqlanmaydi; tuzatish/o‘lchash: '+', '.join(r['key'] for r in quality['fix_list']))
        return out_meta
    finally:
        M.SUBPIXEL, M.TRACE = False, None
        for layer in layers:
            layer.close()


def print_report(meta: dict, style: dict) -> None:
    """Platforma tekshiruvi va joylashuv ogohlantirishlarini chiqaradi."""
    checks = meta.get("checks") or []
    if checks:
        C.info(f"\nPlatforma tekshiruvi ({style.get('platform', {}).get('name', 'Instagram Reels')}):")
        for name, state, detail in checks:
            C.info(f"  [{'OK' if state == 'ok' else 'OGOH' if state == 'ogoh' else 'XATO'}] {name}: {detail}")
    for note in meta.get("notes") or []:
        C.warn(note)
    for name,mix in (meta.get('mixes') or {}).items():
        C.info(f"  Mix {name}: {mix['file']} | cue sheet: {mix['audio'].get('cue_sheet','no events')}")


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
    ap.add_argument("--draft", action="store_true", help="Kichik qoralama (preview sozlamalari); subtitr tasdiqi baribir kerak")
    ap.add_argument("--nvenc", action="store_true", help="NVIDIA karta bilan kodlash")
    ap.add_argument("--style", help="Boshqa style.json fayli")
    args = ap.parse_args()

    style = C.load_style(args.style, args.brand)
    video = C.need_file(args.video, "Video")
    C.busy_acquire(f"render: {video.name}")
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
        for note in res.get("notes") or []:
            C.warn(note)
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
    out = Path(args.output) if args.output else C.OUTPUT_DIR / f"{C.output_stem(name)}_{'draft' if args.draft else 'final'}.mp4"
    C.info(f"Compose: {video.name} -> {out}")
    meta = compose(video, out, style, srt, words, cuts, elements_file,
                   Path(args.music) if args.music else None, True if args.nvenc else None, draft=args.draft)
    C.info(f"Tayyor ({meta['seconds']}s): {out}\n  {meta['width']}x{meta['height']}, {meta['fps']:g} fps, "
           f"{meta['duration']:.2f}s, ovoz: {'bor' if meta['has_audio'] else 'yoq'} ({meta['acodec']})")
    print_report(meta, style)
    return 0


if __name__ == "__main__":
    C.run_main(main)
