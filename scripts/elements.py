"""Grafik qatlamlar: subtitr (kinetik matn), sarlavha, rasm, b-roll, ro'yxat, tanlov, raqam,
ovozli xabar, logotip, oxirgi kadr.

Har bir qatlam `draw(frame, t)` bilan kadr ustiga o'zini chizadi. Qatlamlarni compose.py yig'adi.
Elementlar ro'yxati elements.json da beriladi (AGENTS.md dagi jadvalga qarang).
"""
from __future__ import annotations

import math
import random
import re
import subprocess
from pathlib import Path

import numpy as np

import common as C
import motion as M
from motion import cv2, Image, ImageDraw

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

CAPTION_PRESETS = {
    # toza, zamonaviy: kichik harf, zich harflar, yumshoq soya, so'zlar xiralikdan ochiladi
    "clean": {
        "font": "Inter", "italic": False, "weight_sub": 500, "weight_plain": 600, "weight_main": 700,
        "size_sub": 56, "size_plain": 76, "size_main": 106, "size_huge": 196,
        "tracking": -0.045, "leading": 1.02, "case": "lower", "strip_punct": True,
        "color": "#FFFFFF", "accent": "#FFE600", "big_accent": False, "sub_opacity": 0.92,
        "position_y": 0.64, "max_width": 0.84, "align": "center",
        "reveal": "word", "animation": "blur", "anim_ms": 220, "blur_px": 14, "rise_px": 10, "dim": 0.35,
        "shadow": {"blur": 16, "dy": 4, "opacity": 0.5, "color": "#000000"},
        "glow": None, "stroke": None, "box": None, "auto_numbers": False,
    },
    # baland, tor shrift, KATTA harf, sariq porlash
    "glow": {
        "font": "Oswald", "weight_sub": 500, "weight_plain": 600, "weight_main": 700,
        "size_sub": 62, "size_plain": 88, "size_main": 132, "size_huge": 240,
        "tracking": 0.0, "leading": 1.08, "case": "upper", "big_accent": True,
        "animation": "pop", "anim_ms": 200, "reveal": "cue",
        "glow": {"blur": 20, "opacity": 0.5},
        "shadow": {"blur": 10, "dy": 3, "opacity": 0.6, "color": "#000000"},
    },
    # asosiy so'z rangli quti ichida
    "box": {
        "weight_main": 700, "size_main": 92, "reveal": "cue", "animation": "pop",
        "box": {"text": "#111111", "radius": 0.26, "pad_x": 0.34, "pad_y": 0.16},
    },
    # nafis kursiv
    "serif": {
        "font": "Playfair Display", "italic": True, "weight_sub": 400, "weight_plain": 500, "weight_main": 600,
        "tracking": -0.01, "case": "asis", "size_plain": 80, "size_main": 110,
        "animation": "blur", "reveal": "cue", "anim_ms": 380,
    },
}


class Ctx:
    """Qatlamlar uchun umumiy ma'lumot: kadr o'lchami, shriftlar, uslub, fayl qidirish."""

    def __init__(self, style: dict, brand_dir: Path | None = None):
        self.style = style
        self.W, self.H = int(style["video"]["width"]), int(style["video"]["height"])
        self.fps = float(style["video"]["fps"])
        self.k = self.H / 1920.0                     # o'lchamlar 1920 balandlik uchun berilgan
        self.brand_dir = Path(brand_dir) if brand_dir else None
        font_dirs = []
        if self.brand_dir:
            font_dirs.append(self.brand_dir / "fonts")
        font_dirs.append(C.ROOT / style.get("subtitles", {}).get("fonts_dir", "style/fonts"))
        self.fonts = M.Fonts(font_dirs)
        self.anchor = (0.5, 0.38)                    # yuz markazi (zoom va bo'lingan ekran uchun)

    def asset(self, value: str, what: str = "Fayl") -> Path:
        """Fayl yo'lini topadi: to'liq yo'l, brend papkasi yoki loyiha papkasiga nisbatan."""
        p = Path(str(value))
        candidates = [p] if p.is_absolute() else (
            ([self.brand_dir / p] if self.brand_dir else []) + [C.ROOT / p])
        for c in candidates:
            if c.is_file():
                return c.resolve()
        raise C.MontajError(f"{what} topilmadi: {value} (qidirilgan joylar: "
                            + ", ".join(str(c) for c in candidates) + ")")

    def caption_cfg(self, override: dict | None = None) -> dict:
        user = dict(self.style.get("captions", {}))
        if override:
            user.update(override)
        preset = str(user.get("preset", "clean"))
        if preset not in CAPTION_PRESETS:
            raise C.MontajError(f"captions.preset noto'g'ri: {preset!r}. Mumkin: {', '.join(CAPTION_PRESETS)}")
        cfg = dict(CAPTION_PRESETS["clean"])
        cfg.update(CAPTION_PRESETS[preset])
        cfg.update({k: v for k, v in user.items() if not k.startswith("_") and v is not None})
        return cfg


# ---------------------------------------------------------------- matnni tayyorlash

def fix_apostrophes(text: str) -> str:
    """o' va g' uchun to'g'ri belgi (‘), qolgan joylarda tutuq belgisi (’)."""
    text = re.sub(r"(?<=[oOgGОо])[ʻʼ`´'‘’]", "‘", text)
    return re.sub(r"[ʻʼ`´']", "’", text)


def parse_markup(text: str) -> list:
    """Belgilangan matnni so'zlarga ajratadi: [(so'z, daraja, yangi_qator)].

    *so'z* katta, **so'z** katta + rangli, !!so'z!! juda katta + rangli, _so'z_ faqat rangli.
    Belgilar butun so'z(lar) atrofiga qo'yiladi. "\n" majburiy yangi qator.
    """
    # "_" faqat so'z chegarasida belgi hisoblanadi (masalan @ilm_markazi ichidagisi oddiy harf)
    text = re.sub(r"(?<!\S)_(?=\S)", "\x01", text)
    text = re.sub(r"(?<=\S)_(?=$|[\s.,!?;:])", "\x01", text)
    marks = {"!!": "huge", "**": "big_accent", "*": "big", "\x01": "accent"}
    out, level, newline = [], "normal", False
    for tok in re.split(r"(!!|\*\*|\*|\x01|\n|[ \t\r\f\v]+)", text):
        if not tok:
            continue
        if tok == "\n":
            newline = True
        elif tok.isspace():
            continue
        elif tok in marks:
            level = "normal" if level == marks[tok] else marks[tok]
        else:
            out.append((tok, level, newline))
            newline = False
    return out


strip_markup = C.strip_markup


def apply_case(word: str, mode: str) -> str:
    if mode == "upper":
        return word.upper()
    if mode == "lower":
        letters = [c for c in word if c.isalpha()]
        if len(letters) >= 2 and all(c.isupper() for c in letters):
            return word  # qisqartma (SMM, IELTS) o'zgarmaydi
        return word.lower()
    return word


class RichBlock:
    """Bir necha qatorli, har xil o'lchamli matn bloki. So'zlar alohida sprite bo'lib saqlanadi."""

    def __init__(self, ctx: Ctx, text: str, cfg: dict, size_scale: float = 1.0):
        self.ctx, self.cfg = ctx, cfg
        k = ctx.k * size_scale
        tokens = []
        for word, level, newline in parse_markup(fix_apostrophes(text)):
            if cfg.get("strip_punct"):
                word = word.rstrip(".,;:").lstrip(",.")
            word = apply_case(word, str(cfg.get("case", "asis")))
            if word:
                tokens.append({"text": word, "level": level, "newline": newline})
        emph = any(t["level"] in ("big", "big_accent", "huge") for t in tokens)
        if not emph and cfg.get("auto_numbers") and all(t["level"] == "normal" for t in tokens):
            # belgi qo'yilmagan bo'lakda raqamlar o'zi ajratiladi (masalan "3 oyda", "100%")
            for i, t in enumerate(tokens):
                if any(ch.isdigit() for ch in t["text"]):
                    t["level"] = "big_accent"
                    if len(t["text"].strip("%+-")) <= 3 and i + 1 < len(tokens) and len(tokens[i + 1]["text"]) <= 6:
                        tokens[i + 1]["level"] = "big_accent"   # "3 oyda", "10 yil" birga
                    emph = True
                    break
        accent = cfg.get("accent", "#FFE600")
        box = cfg.get("box")
        for t in tokens:
            lvl = t["level"]
            if lvl == "huge":
                size, weight = cfg["size_huge"], cfg["weight_main"]
            elif lvl in ("big", "big_accent"):
                size, weight = cfg["size_main"], cfg["weight_main"]
            elif emph:
                size, weight = cfg["size_sub"], cfg["weight_sub"]
            else:
                size, weight = cfg["size_plain"], cfg["weight_plain"]
            t["size"] = size * k
            t["font"] = ctx.fonts.get(cfg["font"], t["size"], weight, bool(cfg.get("italic")))
            colored = lvl in ("big_accent", "huge", "accent") or (lvl == "big" and cfg.get("big_accent"))
            t["boxed"] = bool(box) and lvl in ("big", "big_accent", "huge")
            t["color"] = box.get("text", "#111111") if t["boxed"] else (accent if colored else cfg["color"])
            t["opacity"] = 1.0 if lvl != "normal" or not emph else float(cfg.get("sub_opacity", 1.0))
            t["track"] = float(cfg.get("tracking", 0)) * t["size"]
            t["emph"] = lvl in ("big", "big_accent", "huge")

        # qatorlarga bo'lish: o'lcham o'zgarsa yoki kenglikka sig'masa yangi qator
        max_w = float(cfg.get("max_width", 0.84)) * ctx.W
        lines, cur, cur_w = [], [], 0.0
        for t in tokens:
            t["w"] = M.text_advance(t["font"], t["text"], t["track"])
            space = t["font"].getlength(" ") * 0.9 + t["track"]
            add = t["w"] + (space if cur else 0)
            if cur and (t["newline"] or abs(cur[0]["size"] - t["size"]) > 0.5 or cur_w + add > max_w):
                lines.append(cur)
                cur, cur_w, add = [], 0.0, t["w"]
            t["gap"] = space if cur else 0.0
            cur.append(t)
            cur_w += add
        if cur:
            lines.append(cur)

        self.words, self.boxes = [], []
        leading = float(cfg.get("leading", 1.02))
        widths = [sum(t["w"] + t["gap"] for t in line) for line in lines]
        self.width = max(widths) if widths else 0.0
        y = 0.0
        align = str(cfg.get("align", "center"))
        for line, lw in zip(lines, widths):
            size = line[0]["size"]
            pad_y = (box.get("pad_y", 0.16) * size) if (box and line[0]["boxed"]) else 0.0
            y += pad_y
            baseline = y + size * 0.80
            x = 0.0 if align == "left" else (self.width - lw) / 2
            if box and line[0]["boxed"]:
                px = box.get("pad_x", 0.34) * size
                bw, bh = int(lw + px * 2), int(size * 1.02 + pad_y * 2)
                spr = M.rounded_rect_sprite(bw, bh, box.get("radius", 0.26) * size,
                                            M.rgb(box.get("color", accent)) + (255,),
                                            shadow={"blur": 14 * ctx.k, "dy": 6 * ctx.k, "opacity": 0.35})
                self.boxes.append({"spr": spr, "x": x - px, "y": y - pad_y, "first": len(self.words)})
            for t in line:
                x += t["gap"]
                glow = None
                if cfg.get("glow") and t["color"] == accent:
                    glow = dict(cfg["glow"], blur=cfg["glow"].get("blur", 18) * ctx.k, color=accent)
                shadow = None
                if cfg.get("shadow") and not t["boxed"]:
                    sh = cfg["shadow"]
                    shadow = dict(sh, blur=sh.get("blur", 16) * ctx.k, dy=sh.get("dy", 4) * ctx.k)
                stroke = None
                if cfg.get("stroke"):
                    stroke = dict(cfg["stroke"], width=cfg["stroke"].get("width", 4) * ctx.k)
                spr, _ = M.text_sprite(t["text"], t["font"], t["color"], t["track"], shadow, glow, stroke)
                self.words.append({"spr": spr, "x": x, "y": baseline, "w": t["w"], "size": size,
                                   "opacity": t["opacity"], "emph": t["emph"], "text": t["text"]})
                x += t["w"]
            y += size * leading + pad_y
        self.height = y

    @property
    def plain_words(self) -> list:
        return [w["text"] for w in self.words]

    def draw(self, frame, cx: float, cy: float, t: float, times: list | None, cfg: dict,
             start: float, end: float) -> None:
        """Blokni (cx, cy) markazga chizadi. times: har bir so'zning paydo bo'lish vaqti (yoki None)."""
        ox, oy = cx - self.width / 2, cy - self.height / 2
        anim = max(0.001, float(cfg.get("anim_ms", 220)) / 1000.0)
        out = clamp_exit(t, end, 0.07)
        mode = str(cfg.get("animation", "blur"))
        reveal = str(cfg.get("reveal", "word"))
        for b in self.boxes:
            t0 = times[b["first"]] if (times and reveal != "cue") else start
            p = M.ease_back((t - t0) / anim)
            if t >= t0:
                M.blit(frame, b["spr"], ox + b["x"], oy + b["y"], opacity=out * M.clamp01((t - t0) / (anim * 0.6)),
                       scale=0.85 + 0.15 * p, anchor=(b["spr"].w / 2, b["spr"].h / 2))
        for i, w in enumerate(self.words):
            t0 = times[i] if (times and reveal in ("word", "dim")) else start
            p = (t - t0) / anim
            base_op = w["opacity"] * out
            if p < 0:
                if reveal == "dim":
                    M.blit(frame, w["spr"], ox + w["x"], oy + w["y"], opacity=base_op * float(cfg.get("dim", 0.35)))
                continue
            e = M.ease_out(p)
            if mode == "none" or p >= 1:
                M.blit(frame, w["spr"], ox + w["x"], oy + w["y"], opacity=base_op)
            elif mode == "pop":
                M.blit(frame, w["spr"], ox + w["x"], oy + w["y"], opacity=base_op * M.clamp01(p * 2.5),
                       scale=0.72 + 0.28 * M.ease_back(p), anchor=(w["w"] / 2, -w["size"] * 0.35))
            elif mode == "fade":
                M.blit(frame, w["spr"], ox + w["x"], oy + w["y"], opacity=base_op * e)
            else:  # blur: xiralikdan ochiladi va biroz pastdan ko'tariladi
                M.blit(frame, w["spr"], ox + w["x"], oy + w["y"] + (1 - e) * float(cfg.get("rise_px", 10)) * self.ctx.k,
                       opacity=base_op * e, blur=(1 - e) * float(cfg.get("blur_px", 14)) * self.ctx.k)


def clamp_exit(t: float, end: float, dur: float) -> float:
    return M.clamp01((end - t) / dur) if dur > 0 else 1.0


def appear(t: float, start: float, end: float, tin: float = 0.28, tout: float = 0.16) -> tuple:
    """Element paydo bo'lishi/yo'qolishi: (shaffoflik, masshtab)."""
    p_in = (t - start) / tin if tin > 0 else 1.0
    op = M.clamp01(p_in * 1.8) * clamp_exit(t, end, tout)
    return op, 0.82 + 0.18 * M.ease_back(p_in)


# ---------------------------------------------------------------- qatlamlar

class Layer:
    z = 30

    def __init__(self, start: float, end: float):
        self.start, self.end = float(start), float(end)

    def active(self, t: float) -> bool:
        return self.start <= t < self.end

    def draw(self, frame, t: float) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class CaptionLayer(Layer):
    """Subtitr: SRT bo'laklari, so'zlar nutq bilan birga ochiladi."""
    z = 50

    def __init__(self, ctx: Ctx, cues: list, words: list | None, total: float):
        super().__init__(0, total)
        import subtitles as S
        self.ctx, self.cfg = ctx, ctx.caption_cfg()
        self.items = []
        cues = sorted(cues, key=lambda c: c["start"])
        for i, cue in enumerate(cues):
            end = cue["end"]
            nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
            if nxt is not None and 0 <= nxt - end < float(self.cfg.get("hold_gap", 0.35)):
                end = nxt  # qisqa pauzada matn miltillamasligi uchun keyingisigacha ushlab turiladi
            self.items.append({"start": cue["start"], "end": end, "text": cue["text"], "cue": cue,
                               "block": None, "times": None})
        self.words, self._word_times = words, S.word_times

    def _prepare(self, item: dict) -> None:
        block = RichBlock(self.ctx, item["text"], self.cfg)
        tokens = block.plain_words
        item["block"] = block
        item["times"] = self._word_times(item["cue"], tokens, self.words) if tokens else []

    def draw(self, frame, t: float) -> None:
        for item in self.items:
            if item["start"] <= t < item["end"]:
                if item["block"] is None:
                    self._prepare(item)
                item["block"].draw(frame, self.ctx.W / 2, float(self.cfg["position_y"]) * self.ctx.H, t,
                                   item["times"], self.cfg, item["start"], item["end"])
            elif item["block"] is not None and t >= item["end"]:
                item["block"] = None  # xotirani bo'shatish


class TextLayer(Layer):
    """Erkin matn yoki sarlavha. Belgilar subtitrdagi kabi (*katta*, **rangli**, !!juda katta!!)."""
    z = 45

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        override = {"reveal": "cue", "animation": el.get("anim", "blur"), "case": el.get("case", "asis"),
                    "strip_punct": False, "auto_numbers": False}
        for key in ("preset", "font", "color", "accent", "align", "max_width", "italic", "box", "glow"):
            if key in el:
                override[key] = el[key]
        if "weight" in el:
            override.update(weight_sub=el["weight"], weight_plain=el["weight"], weight_main=el["weight"])
        self.ctx, self.cfg = ctx, ctx.caption_cfg(override)
        self.block = RichBlock(ctx, str(el.get("text", "")), self.cfg, float(el.get("size", 1.0)))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H

    def draw(self, frame, t: float) -> None:
        self.block.draw(frame, self.cx, self.cy, t, None, self.cfg, self.start, self.end)


class VideoReader:
    """Qo'shimcha videodan kadrlarni ketma-ket o'qiydi (ffmpeg orqali, kerakli o'lchamda)."""

    def __init__(self, path: Path, w: int, h: int, fps: float):
        self.path, self.w, self.h, self.fps = Path(path), int(w), int(h), fps
        self.proc, self.pos, self.last = None, -1, None
        self.duration = C.ffprobe_info(path)["duration"]

    def _open(self, offset: float) -> None:
        self.close()
        cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error"]
        if offset > 0.01:
            cmd += ["-ss", f"{offset:.3f}"]
        cmd += ["-i", str(self.path), "-an", "-vf",
                f"fps={self.fps:g},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
                f"crop={self.w}:{self.h},format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.pos = int(round(offset * self.fps)) - 1

    def frame_at(self, t_rel: float):
        idx = max(0, int(round(t_rel * self.fps)))
        if self.proc is None or idx < self.pos or idx > self.pos + 3:
            self._open(min(idx / self.fps, max(0.0, self.duration - 0.05)))
        size = self.w * self.h * 3
        while self.pos < idx:
            buf = self.proc.stdout.read(size)
            if len(buf) < size:
                break  # video tugadi: oxirgi kadr ushlab turiladi
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
            self.pos += 1
        return self.last

    def close(self) -> None:
        if self.proc is not None:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None


class BrollLayer(Layer):
    """Qo'shimcha kadr: to'liq ekran ("full") yoki ekran ikkiga bo'linadi ("split": tepada gapiruvchi)."""
    z = 10

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        self.mode = str(el.get("mode", "full"))
        if self.mode not in ("full", "split"):
            raise C.MontajError(f"broll.mode noto'g'ri: {self.mode!r}. Mumkin: full, split")
        self.fade = float(el.get("fade", 0.0))
        self.offset = float(el.get("offset", 0.0))
        self.path = ctx.asset(el.get("file", ""), "B-roll fayli")
        self.rw, self.rh = ctx.W, ctx.H if self.mode == "full" else ctx.H // 2
        self.is_image = self.path.suffix.lower() in IMAGE_EXTS
        if self.is_image:
            img = Image.open(self.path).convert("RGB")
            scale = max(self.rw / img.width, self.rh / img.height) * 1.08  # sekin kattalashish uchun zaxira
            img = img.resize((max(self.rw, int(img.width * scale) + 1), max(self.rh, int(img.height * scale) + 1)),
                             Image.LANCZOS)
            self.still = np.asarray(img)
            self.reader = None
        elif self.path.suffix.lower() in C.VIDEO_EXTS:
            self.reader = VideoReader(self.path, self.rw, self.rh, ctx.fps)
        else:
            raise C.MontajError(f"B-roll uchun rasm yoki video kerak: {self.path.name}")

    def _content(self, t: float):
        if self.is_image:
            p = M.clamp01((t - self.start) / max(0.1, self.end - self.start))
            z = 1.0 + 0.08 * p                       # sekin yaqinlashish (Ken Burns)
            sh, sw = self.still.shape[:2]
            cw, ch = self.rw * 1.08 / z, self.rh * 1.08 / z
            x0, y0 = (sw - cw) / 2, (sh - ch) / 2
            crop = self.still[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
            return cv2.resize(crop, (self.rw, self.rh), interpolation=cv2.INTER_LINEAR)
        return self.reader.frame_at(self.offset + t - self.start)

    def draw(self, frame, t: float) -> None:
        content = self._content(t)
        if content is None:
            return
        W, H = self.ctx.W, self.ctx.H
        op = 1.0
        if self.fade > 0:
            op = M.clamp01((t - self.start) / self.fade) * clamp_exit(t, self.end, self.fade)
        if self.mode == "split":
            # gapiruvchi tepaga: yuz atrofidan W x H/2 bo'lak kesib olinadi
            half = H // 2
            ax, ay = self.ctx.anchor
            ch = H * 0.62
            cw = ch * W / half
            if cw > W:
                cw, ch = W, W * half / W
            x0 = int(min(max(0, ax * W - cw / 2), W - cw))
            y0 = int(min(max(0, ay * H - ch * 0.42), H - ch))
            top = cv2.resize(frame[y0:int(y0 + ch), x0:int(x0 + cw)], (W, half), interpolation=cv2.INTER_LINEAR)
            canvas = np.concatenate([top, content[:H - half]], axis=0)
            canvas[half - 2:half + 2] = 255
            content = canvas
        if op >= 0.997:
            frame[:] = content
        else:
            frame[:] = (frame.astype(np.float32) * (1 - op) + content.astype(np.float32) * op).astype(np.uint8)

    def close(self) -> None:
        if self.reader:
            self.reader.close()


class ImageLayer(Layer):
    """Rasm (yoki kichik video) ustma-qatlam: joyi, kengligi, yumaloq burchak, soya."""
    z = 30

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        self.path = ctx.asset(el.get("file", ""), "Rasm")
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.4)) * ctx.H
        self.width = int(float(el.get("width", 0.5)) * ctx.W)
        self.radius = float(el.get("radius", 0)) * ctx.k
        self.anim = str(el.get("anim", "pop"))
        self.opacity = float(el.get("opacity", 1.0))
        self.shadow = {"blur": 18 * ctx.k, "dy": 8 * ctx.k, "opacity": 0.35} if el.get("shadow", True) else None
        self.reader = None
        if self.path.suffix.lower() in C.VIDEO_EXTS:
            meta = C.ffprobe_info(self.path)
            self.vh = max(2, int(self.width * meta["height"] / max(1, meta["width"])) // 2 * 2)
            self.width = self.width // 2 * 2
            self.reader = VideoReader(self.path, self.width, self.vh, ctx.fps)
            self.spr = None
        else:
            self.spr = M.image_sprite(self.path, width=self.width, radius=self.radius, shadow=self.shadow)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        if self.anim == "fade":
            scale = 1.0
        elif self.anim == "none":
            op, scale = 1.0, 1.0
        spr = self.spr
        if self.reader is not None:
            content = self.reader.frame_at(t - self.start)
            if content is None:
                return
            rgba = np.dstack([content, np.full(content.shape[:2], 255, np.uint8)])
            spr = M.Sprite(rgba, -self.width / 2, -self.vh / 2)
        M.blit(frame, spr, self.cx, self.cy, opacity=op * self.opacity, scale=scale, anchor=(0, 0))

    def close(self) -> None:
        if self.reader:
            self.reader.close()


def icon_sprite(kind: str, size: int, color: tuple = (255, 255, 255, 255), thickness: float = 0.16) -> M.Sprite:
    """Oddiy vektor belgi: check, cross, play, pause, plus. Sprite nuqtasi: markaz."""
    s = 4
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    n, w = size * s, max(2, int(size * s * thickness))

    def line(points):
        d.line([(x * n, y * n) for x, y in points], fill=color, width=w, joint="curve")
        for x, y in (points[0], points[-1]):
            d.ellipse([x * n - w / 2, y * n - w / 2, x * n + w / 2, y * n + w / 2], fill=color)

    if kind == "check":
        line([(0.2, 0.54), (0.42, 0.76), (0.82, 0.26)])
    elif kind == "cross":
        line([(0.24, 0.24), (0.76, 0.76)])
        line([(0.76, 0.24), (0.24, 0.76)])
    elif kind == "plus":
        line([(0.5, 0.18), (0.5, 0.82)])
        line([(0.18, 0.5), (0.82, 0.5)])
    elif kind == "play":
        d.polygon([(0.3 * n, 0.2 * n), (0.82 * n, 0.5 * n), (0.3 * n, 0.8 * n)], fill=color)
    elif kind == "pause":
        d.rounded_rectangle([0.27 * n, 0.2 * n, 0.43 * n, 0.8 * n], radius=0.05 * n, fill=color)
        d.rounded_rectangle([0.57 * n, 0.2 * n, 0.73 * n, 0.8 * n], radius=0.05 * n, fill=color)
    else:
        raise C.MontajError(f"Noma'lum belgi: {kind}")
    return M.from_pil(big.resize((size, size), Image.LANCZOS), -size / 2, -size / 2)


class ListLayer(Layer):
    """Raqamli ro'yxat: qatorlar aytilgan vaqtda birma-bir chiqadi. Qatorda matn va/yoki rasm bo'ladi."""
    z = 35

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        cfg = ctx.caption_cfg({"preset": el.get("preset", "clean")})
        k = ctx.k * float(el.get("size", 1.0))
        accent = el.get("accent", cfg["accent"])
        size = 62 * k
        self.row_h = size * float(el.get("spacing", 1.55))
        self.x, self.y = float(el.get("x", 0.09)) * ctx.W, float(el.get("y", 0.34)) * ctx.H
        style = str(el.get("style", "badge"))
        font = ctx.fonts.get(cfg["font"], size, 600)
        shadow = {"blur": 12 * k, "dy": 3 * k, "opacity": 0.55}
        self.rows = []
        items = el.get("items") or []
        if not items:
            raise C.MontajError("list elementida 'items' bo'sh.")
        for i, item in enumerate(items, 1):
            row = {"at": float(item.get("at", el["start"])), "parts": []}
            x = 0.0
            if el.get("numbered", True):
                if style == "badge":
                    d = int(size * 1.0)
                    row["parts"].append((M.rounded_rect_sprite(d, d, d / 2, M.rgb(accent) + (255,),
                                                               shadow={"blur": 8 * k, "dy": 3 * k, "opacity": 0.3}),
                                         x, -d / 2))
                    nf = ctx.fonts.get(cfg["font"], size * 0.62, 700)
                    spr, adv = M.text_sprite(str(i), nf, el.get("number_color", "#111111"))
                    row["parts"].append((spr, x + (d - adv) / 2, size * 0.22))
                    x += d + size * 0.34
                else:  # plain: katta oq raqam
                    nf = ctx.fonts.get(cfg["font"], size * 1.25, 500)
                    spr, adv = M.text_sprite(str(i), nf, cfg["color"], shadow=shadow)
                    row["parts"].append((spr, x, size * 0.44))
                    x += max(adv, size * 0.8) + size * 0.4
            if item.get("image"):
                ih = int(self.row_h * 0.82)
                img = M.image_sprite(ctx.asset(item["image"], "Ro'yxat rasmi"), height=ih, radius=10 * k,
                                     shadow={"blur": 8 * k, "dy": 3 * k, "opacity": 0.3})
                row["parts"].append((img, x - img.ox, 0))
                x += -img.ox * 2 + size * 0.3
            if item.get("text"):
                text = fix_apostrophes(str(item["text"]))
                spr, adv = M.text_sprite(text, font, cfg["color"], float(cfg["tracking"]) * size, shadow)
                row["parts"].append((spr, x, size * 0.34))
            self.rows.append(row)

    def draw(self, frame, t: float) -> None:
        out = clamp_exit(t, self.end, 0.18)
        for i, row in enumerate(self.rows):
            p = (t - row["at"]) / 0.3
            if p < 0:
                continue
            e = M.ease_out(p)
            cy = self.y + i * self.row_h
            for spr, dx, dy in row["parts"]:
                M.blit(frame, spr, self.x + dx - (1 - e) * 40 * self.ctx.k, cy + dy, opacity=out * M.clamp01(p * 2))


class ChoiceLayer(Layer):
    """To'g'ri/noto'g'ri kartochkasi: ikkita belgi (x va check) va ostida matn. Har band o'z vaqtida almashadi."""
    z = 35

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        cfg = ctx.caption_cfg({"preset": "clean"})
        k = self.k = ctx.k * float(el.get("size", 1.0))
        self.color = M.rgb(el.get("color", "#5BB8F5"))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.58)) * ctx.H
        self.tile = int(190 * k)
        self.gap = int(36 * k)
        self.decide = float(el.get("decide", 0.8))
        self.icons = {"cross": icon_sprite("cross", int(self.tile * 0.74)),
                      "check": icon_sprite("check", int(self.tile * 0.74))}
        self.tile_spr = M.rounded_rect_sprite(self.tile, self.tile, 30 * k, self.color + (215,),
                                              border=(255, 255, 255, 150), border_width=max(1, int(3 * k)),
                                              shadow={"blur": 16 * k, "dy": 6 * k, "opacity": 0.28})
        font = ctx.fonts.get(cfg["font"], 58 * k, 600)
        self.items = []
        items = el.get("items") or []
        if not items:
            raise C.MontajError("choice elementida 'items' bo'sh.")
        for n, item in enumerate(items):
            end = float(items[n + 1].get("at", self.end)) if n + 1 < len(items) else self.end
            lines = self._wrap(fix_apostrophes(str(item.get("text", ""))), font, 520 * k)
            sprs = [M.text_sprite(line, font, "#FFFFFF", float(cfg["tracking"]) * 58 * k,
                                  {"blur": 6 * k, "dy": 2 * k, "opacity": 0.35}) for line in lines]
            w = int(max([adv for _, adv in sprs] + [200 * k]) + 70 * k)
            h = int(len(sprs) * 68 * k + 44 * k)
            card = M.rounded_rect_sprite(w, h, 26 * k, self.color + (215,), border=(255, 255, 255, 150),
                                         border_width=max(1, int(3 * k)),
                                         shadow={"blur": 16 * k, "dy": 6 * k, "opacity": 0.28})
            self.items.append({"at": float(item.get("at", self.start)), "end": end, "ok": bool(item.get("ok")),
                               "card": card, "w": w, "h": h, "lines": sprs})

    @staticmethod
    def _wrap(text: str, font, max_w: float) -> list:
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if cur and font.getlength(trial) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + ([cur] if cur else [])

    def draw(self, frame, t: float) -> None:
        out = clamp_exit(t, self.end, 0.18)
        item = next((i for i in self.items if i["at"] <= t < i["end"]), None)
        if item is None:
            return
        k, tile = self.k, self.tile
        p = (t - item["at"]) / 0.28
        op, scale = out * M.clamp01(p * 2), 0.86 + 0.14 * M.ease_back(p)
        decided = M.clamp01((t - item["at"] - self.decide) / 0.25)
        top = self.cy - tile - 22 * k
        for kind, x in (("cross", self.cx - self.gap / 2 - tile), ("check", self.cx + self.gap / 2)):
            chosen = (kind == "check") == item["ok"]
            dim = 1.0 if chosen else 1.0 - 0.68 * decided
            M.blit(frame, self.tile_spr, x, top, opacity=op * dim, scale=scale, anchor=(tile / 2, tile / 2))
            M.blit(frame, self.icons[kind], x + tile / 2, top + tile / 2, opacity=op * dim,
                   scale=scale * (1.0 + (0.08 * math.sin(min(1.0, decided) * math.pi) if chosen else 0)), anchor=(0, 0))
        M.blit(frame, item["card"], self.cx - item["w"] / 2, self.cy + 8 * k, opacity=op, scale=scale,
               anchor=(item["w"] / 2, item["h"] / 2))
        for n, (spr, adv) in enumerate(item["lines"]):
            M.blit(frame, spr, self.cx - adv / 2, self.cy + 8 * k + 22 * k + 50 * k + n * 68 * k, opacity=op)


class StatLayer(Layer):
    """Katta raqam (masalan 90%) sanab chiqadi, atrofida halqa to'ladi."""
    z = 35

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        self.cfg = ctx.caption_cfg({"preset": el.get("preset", "clean")})
        self.k = ctx.k * float(el.get("size", 1.0))
        try:
            self.value = float(el.get("value", 0))
        except (TypeError, ValueError):
            raise C.MontajError("stat.value son bo'lishi kerak (masalan 90).") from None
        self.suffix = str(el.get("suffix", "%"))
        self.max = float(el.get("max", 100))
        self.ring = bool(el.get("ring", True))
        self.accent = M.rgb(el.get("accent", self.cfg["accent"]))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.4)) * ctx.H
        self.count = float(el.get("count_sec", 0.9))
        self.radius = int(210 * self.k)
        self.label = None
        if el.get("label"):
            font = ctx.fonts.get(self.cfg["font"], 60 * self.k, 600)
            self.label = M.text_sprite(fix_apostrophes(str(el["label"])), font, self.cfg["color"],
                                       float(self.cfg["tracking"]) * 60 * self.k,
                                       {"blur": 12 * self.k, "dy": 3 * self.k, "opacity": 0.5})
        self._cache: dict = {}

    def _ring(self, frac: float) -> M.Sprite:
        key = int(round(frac * 120))
        if key not in self._cache:
            r, s = self.radius, 3
            th = int(r * 0.17)
            size = (r * 2 + 8) * s
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            box = [4 * s, 4 * s, size - 4 * s, size - 4 * s]
            d.ellipse(box, outline=(255, 255, 255, 70), width=th * s)
            if key > 0:
                d.arc(box, -90, -90 + 360 * key / 120, fill=self.accent + (255,), width=th * s)
            self._cache[key] = M.from_pil(img.resize((size // s, size // s), Image.LANCZOS), -size / s / 2, -size / s / 2)
        return self._cache[key]

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        p = M.ease_out((t - self.start) / self.count)
        value = self.value * p
        if self.ring:
            M.blit(frame, self._ring(M.clamp01(value / self.max)), self.cx, self.cy, opacity=op, scale=scale, anchor=(0, 0))
        text = (f"{value:.0f}" if float(self.value).is_integer() else f"{value:.1f}") + self.suffix
        size = (150 if self.ring else 230) * self.k
        if ("n", text) not in self._cache:
            font = self.ctx.fonts.get(self.cfg["font"], size, 700)
            self._cache[("n", text)] = M.text_sprite(
                text, font, self.cfg["color"] if self.ring else self.cfg["accent"],
                float(self.cfg["tracking"]) * size, {"blur": 14 * self.k, "dy": 4 * self.k, "opacity": 0.5})
        spr, adv = self._cache[("n", text)]
        M.blit(frame, spr, self.cx - adv / 2, self.cy + size * 0.36, opacity=op)
        if self.label:
            spr, adv = self.label
            M.blit(frame, spr, self.cx - adv / 2, self.cy + (self.radius if self.ring else size * 0.5) + 95 * self.k,
                   opacity=op * M.clamp01((t - self.start - 0.25) / 0.25))


class VoiceLayer(Layer):
    """Ovozli xabar ko'rinishidagi pleyer: tugma, to'lqin chiziqlari, vaqt."""
    z = 35

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        k = self.k = ctx.k * float(el.get("size", 1.0))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H
        self.w, self.h = int(float(el.get("width", 0.62)) * ctx.W), int(132 * k)
        self.accent = M.rgb(el.get("accent", "#3B82F6"))
        self.panel = M.rounded_rect_sprite(self.w, self.h, 30 * k, (24, 24, 28, 235), border=(255, 255, 255, 110),
                                           border_width=max(1, int(3 * k)),
                                           shadow={"blur": 18 * k, "dy": 8 * k, "opacity": 0.4})
        d = int(self.h * 0.6)
        self.button = M.rounded_rect_sprite(d, d, d / 2, self.accent + (255,))
        self.bd = d
        self.pause = icon_sprite("pause", int(d * 0.62))
        rnd = random.Random(str(el.get("seed", el.get("start", 0))))
        self.bars = [0.25 + 0.75 * abs(math.sin(i * 0.7) * rnd.uniform(0.35, 1.0)) for i in range(int(el.get("bars", 38)))]
        self.font = ctx.fonts.get("Inter", 26 * k, 500)
        self.total = float(el.get("length", self.end - self.start))

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        k, x0, y0 = self.k, self.cx - self.w / 2, self.cy - self.h / 2
        M.blit(frame, self.panel, x0, y0, opacity=op, scale=scale, anchor=(self.w / 2, self.h / 2))
        if (t - self.start) < 0.2:
            return
        bx = x0 + self.h * 0.2
        M.blit(frame, self.button, bx, self.cy - self.bd / 2, opacity=op)
        M.blit(frame, self.pause, bx + self.bd / 2, self.cy, opacity=op)
        progress = M.clamp01((t - self.start) / max(0.1, self.end - self.start))
        left, right = bx + self.bd + 26 * k, x0 + self.w - 34 * k
        step = (right - left) / len(self.bars)
        bw = max(2, int(step * 0.5))
        for i, hgt in enumerate(self.bars):
            done = (i + 0.5) / len(self.bars) <= progress
            bh = int(self.h * 0.42 * hgt)
            xx = int(left + i * step)
            yy = int(self.cy - 8 * k - bh / 2)
            color = np.array((255, 255, 255) if done else (120, 124, 135), np.float32)
            roi = frame[max(0, yy):yy + bh, max(0, xx):xx + bw]
            if roi.size:
                roi[:] = (roi.astype(np.float32) * (1 - op) + color * op).astype(np.uint8)
        sec = int(progress * self.total)
        spr, _ = M.text_sprite(f"{sec // 60}:{sec % 60:02d}", self.font, "#B8BCC8")
        M.blit(frame, spr, left, y0 + self.h - 20 * k, opacity=op)


class LogoLayer(Layer):
    """Brend logotipi: butun video davomida burchakda yoki tepada turadi."""
    z = 70

    def __init__(self, ctx: Ctx, cfg: dict, total: float):
        super().__init__(float(cfg.get("start", 0.0)), total)
        self.ctx = ctx
        width = int(float(cfg.get("width", 0.26)) * ctx.W)
        self.spr = M.image_sprite(ctx.asset(cfg["file"], "Logotip"), width=width)
        self.opacity = float(cfg.get("opacity", 0.95))
        pos = str(cfg.get("position", "top"))
        mx, my = float(cfg.get("margin_x", 0.06)) * ctx.W, float(cfg.get("margin_y", 0.07)) * ctx.H
        hw, hh = self.spr.w / 2, self.spr.h / 2
        table = {"top": (ctx.W / 2, my + hh), "top_left": (mx + hw, my + hh), "top_right": (ctx.W - mx - hw, my + hh),
                 "bottom": (ctx.W / 2, ctx.H - my - hh), "bottom_left": (mx + hw, ctx.H - my - hh),
                 "bottom_right": (ctx.W - mx - hw, ctx.H - my - hh)}
        if pos not in table:
            raise C.MontajError(f"logo.position noto'g'ri: {pos!r}. Mumkin: {', '.join(table)}")
        self.cx, self.cy = table[pos]

    def draw(self, frame, t: float) -> None:
        M.blit(frame, self.spr, self.cx, self.cy,
               opacity=self.opacity * M.clamp01((t - self.start) / 0.35) * clamp_exit(t, self.end, 0.2))


class EndcardLayer(Layer):
    """Oxirgi kadr: xira fon, logotip, nom, @manzil va "obuna bo'ling" tugmasi."""
    z = 90

    def __init__(self, ctx: Ctx, cfg: dict, start: float, end: float):
        super().__init__(start, end)
        self.ctx = ctx
        k = ctx.k
        cap = ctx.caption_cfg({"preset": cfg.get("preset", "clean")})
        self.bg = M.rgb(cfg["background"]) if cfg.get("background") else None
        self.logo = None
        if cfg.get("logo") or ctx.style.get("logo", {}).get("file"):
            self.logo = M.image_sprite(ctx.asset(cfg.get("logo") or ctx.style["logo"]["file"], "Logotip"),
                                       width=int(float(cfg.get("logo_width", 0.42)) * ctx.W))
        shadow = {"blur": 14 * k, "dy": 4 * k, "opacity": 0.45}
        self.title = self.handle = self.button = None
        if cfg.get("text"):
            f = ctx.fonts.get(cap["font"], 92 * k, 700)
            self.title = M.text_sprite(fix_apostrophes(str(cfg["text"])), f, cap["color"], cap["tracking"] * 92 * k, shadow)
        if cfg.get("handle"):
            f = ctx.fonts.get(cap["font"], 54 * k, 500)
            self.handle = M.text_sprite(str(cfg["handle"]), f, cap["color"], cap["tracking"] * 54 * k, shadow)
        if cfg.get("button", "Obuna bo‘ling"):
            label = fix_apostrophes(str(cfg.get("button", "Obuna bo'ling")))
            f = ctx.fonts.get(cap["font"], 52 * k, 700)
            spr, adv = M.text_sprite(label, f, cfg.get("button_text", "#111111"), cap["tracking"] * 52 * k)
            bw, bh = int(adv + 110 * k), int(112 * k)
            pill = M.rounded_rect_sprite(bw, bh, bh / 2, M.rgb(cfg.get("button_color", cap["accent"])) + (255,),
                                         shadow={"blur": 16 * k, "dy": 8 * k, "opacity": 0.35})
            self.button = (pill, bw, bh, spr, adv)
        self._blurred = None

    def draw(self, frame, t: float) -> None:
        W, H, k = self.ctx.W, self.ctx.H, self.ctx.k
        p = M.clamp01((t - self.start) / 0.35)
        if self.bg is not None:
            frame[:] = (frame.astype(np.float32) * (1 - p) + np.array(self.bg, np.float32) * p).astype(np.uint8)
        else:
            if self._blurred is None:  # oxirgi kadr bir marta xiralashtiriladi
                small = cv2.resize(frame, (W // 6, H // 6), interpolation=cv2.INTER_AREA)
                small = cv2.GaussianBlur(small, (0, 0), 9)
                self._blurred = (cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * 0.45)
            frame[:] = (frame.astype(np.float32) * (1 - p) + self._blurred * p).astype(np.uint8)
        y = H * 0.40
        if self.logo:
            op, scale = appear(t, self.start + 0.1, self.end + 9)
            M.blit(frame, self.logo, W / 2, y, opacity=op, scale=scale, anchor=(0, 0))
            y += self.logo.h / 2 + 110 * k
        if self.title:
            spr, adv = self.title
            M.blit(frame, spr, W / 2 - adv / 2, y, opacity=M.clamp01((t - self.start - 0.25) / 0.25),
                   blur=(1 - M.ease_out((t - self.start - 0.25) / 0.3)) * 12 * k)
            y += 84 * k
        if self.handle:
            spr, adv = self.handle
            M.blit(frame, spr, W / 2 - adv / 2, y, opacity=0.85 * M.clamp01((t - self.start - 0.4) / 0.25))
            y += 70 * k
        if self.button:
            pill, bw, bh, spr, adv = self.button
            op, scale = appear(t, self.start + 0.6, self.end + 9)
            by = y + 40 * k
            M.blit(frame, pill, W / 2 - bw / 2, by, opacity=op, scale=scale, anchor=(bw / 2, bh / 2))
            M.blit(frame, spr, W / 2 - adv / 2, by + bh * 0.66, opacity=op)


ELEMENT_TYPES = {"text": TextLayer, "title": TextLayer, "image": ImageLayer, "broll": BrollLayer,
                 "list": ListLayer, "choice": ChoiceLayer, "stat": StatLayer, "voice": VoiceLayer}
NON_LAYER_TYPES = {"sfx", "zoom"}


def build_elements(ctx: Ctx, elements: list, total: float) -> list:
    """elements.json dagi ro'yxatdan qatlamlar yasaydi. Xato bo'lsa qaysi elementdaligini aytadi."""
    layers = []
    for n, el in enumerate(elements, 1):
        if not isinstance(el, dict):
            raise C.MontajError(f"elements.json: {n}-element obyekt emas.")
        kind = el.get("type")
        if kind in NON_LAYER_TYPES:
            continue
        if kind not in ELEMENT_TYPES:
            raise C.MontajError(f"elements.json: {n}-elementda noma'lum type: {kind!r}. Mumkin: "
                                + ", ".join(sorted(set(ELEMENT_TYPES) | NON_LAYER_TYPES)))
        try:
            el = dict(el)
            el["start"] = float(el.get("start", 0))
            el["end"] = min(float(el.get("end", total)), total)
            if el["end"] <= el["start"]:
                raise C.MontajError("'end' 'start' dan katta bo'lishi kerak (yoki video uzunligidan oshib ketgan).")
            if kind == "title":
                el.setdefault("size", 1.25)
                el.setdefault("y", 0.24)
            layers.append(ELEMENT_TYPES[kind](ctx, el))
        except C.MontajError as exc:
            raise C.MontajError(f"elements.json: {n}-element ({kind}): {exc}") from None
        except (KeyError, TypeError, ValueError) as exc:
            raise C.MontajError(f"elements.json: {n}-element ({kind}) noto'g'ri to'ldirilgan: {exc}") from None
    return layers
