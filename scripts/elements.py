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
CAPTION_ANIMS = ("blur", "fade", "pop", "rise", "flicker", "bar", "letters", "ltrack", "none")
FLICKER = (1.0, 0.28, 0.28, 1.0, 0.28, 0.28)      # "miltillab yonish": kadrma-kadr shaffoflik

CAPTION_PRESETS = {
    # Namuna videolarning asosiy uslubi (samples/ 2, 7, 8, 10): kichik harf, juda zich harflar, asosiy ibora
    # katta, qolgani ostida kichik; so'zlar xiralikdan ochiladi, so'zlar orasi keng boshlanib zichlashadi,
    # blok sekin kattalashadi, tugagach xiralashib yo'qoladi. Sariq so'z porlaydi.
    "clean": {
        "font": "Inter", "italic": False, "weight_sub": 500, "weight_plain": 500, "weight_main": 600,
        "size_sub": 78, "size_plain": 80, "size_main": 124, "size_huge": 300,
        "tracking": -0.06, "leading": 1.0, "word_space": 0.78, "case": "smart", "strip_punct": True,
        "fit_sub": True, "fit_min": 0.62, "fit_max": 1.1,
        "color": "#FFFFFF", "accent": "#FFE600", "big_accent": False, "sub_opacity": 1.0,
        "position_y": 0.56, "max_width": 0.84, "align": "center",
        "reveal": "word", "animation": "blur", "anim_ms": 300, "blur_px": 14, "rise_px": 0, "dim": 0.35,
        "slide_in": 0.8, "slide_ms": 900, "track_in": 0.0, "track_ms": 1100, "intro_scale": 0.94, "intro_ms": 500, "drift": 0.035,
        "exit": "blur", "exit_ms": 170, "letter_ms": 45, "letter_track": 0.22, "letter_from": "below", "bar_ms": 120,
        "shadow": {"blur": 18, "dy": 4, "opacity": 0.45, "color": "#000000"},
        "glow": {"blur": 16, "opacity": 0.5}, "stroke": None, "box": None, "auto_numbers": False,
        "highlight": {"color": None, "text": "#111111"},
        "highlight2": {"color": "#D7263D", "text": "#FFFFFF", "pre": "#FFFFFF"},
    },
    # baland, tor shrift, KATTA harf, sariq porlash (namuna 5, 10: "KELINGLAR", "TASAVVUR QILING")
    "glow": {
        "font": "Oswald", "weight_sub": 500, "weight_plain": 600, "weight_main": 700,
        "size_sub": 62, "size_plain": 88, "size_main": 132, "size_huge": 240,
        "tracking": 0.0, "leading": 1.08, "word_space": 0.9, "case": "upper", "big_accent": True,
        "animation": "pop", "anim_ms": 200, "reveal": "cue", "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.0,
        "exit": "fade", "exit_ms": 100,
        "glow": {"blur": 20, "opacity": 0.5},
        "shadow": {"blur": 10, "dy": 3, "opacity": 0.6, "color": "#000000"},
    },
    # sarlavha: tor KATTA harflar tepadan birin-ketin tushadi, sariq porlaydi (namuna 5)
    "caps": {
        "font": "Inter", "font_main": "Oswald", "weight_sub": 500, "weight_plain": 600, "weight_main": 700,
        "size_sub": 62, "size_plain": 80, "size_main": 250, "size_huge": 330,
        "tracking": -0.02, "leading": 0.98, "word_space": 0.9, "case": "smart", "case_main": "upper",
        "big_accent": True, "fit_sub": False, "position_y": 0.2, "reveal": "cue", "animation": "letters", "anim_sub": "blur",
        "letter_from": "above", "letter_ms": 38, "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.05,
        "glow": {"blur": 26, "opacity": 0.6}, "exit": "blur", "exit_ms": 220,
        "shadow": {"blur": 12, "dy": 4, "opacity": 0.35, "color": "#000000"},
    },
    # asosiy so'z rangli quti ichida
    "box": {
        "weight_main": 700, "size_main": 92, "reveal": "cue", "animation": "pop", "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0,
        "drift": 0.0, "exit": "fade", "exit_ms": 100, "glow": None,
        "box": {"text": "#111111", "radius": 0.26, "pad_x": 0.34, "pad_y": 0.16},
    },
    # nafis kursiv (namuna 3): asosiy ibora Playfair kursivda, kichik so'zlar oddiy shriftda
    "serif": {
        "font": "Inter", "font_main": "Playfair Display", "italic_main": True,
        "weight_sub": 400, "weight_plain": 400, "weight_main": 500,
        "tracking": -0.02, "case": "asis", "size_sub": 58, "size_plain": 76, "size_main": 112, "size_huge": 180,
        "animation": "blur", "reveal": "word", "anim_ms": 380, "slide_in": 0.5, "track_in": 0.0, "drift": 0.02, "glow": None,
    },
    # bir-ikki so'zdan, tez almashadi (namuna 12)
    "single": {
        "weight_plain": 600, "weight_sub": 500, "size_plain": 72, "size_sub": 54, "size_main": 150,
        "position_y": 0.6, "reveal": "cue", "animation": "fade", "anim_ms": 110, "slide_in": 0.0, "track_in": 0.0,
        "intro_scale": 0.97, "intro_ms": 160, "drift": 0.0, "exit": "none",
    },
    # marker: kichik, chapga tekislangan, bir necha qator; ==so'z== ustidan rangli quti surtiladi (namuna 13)
    "marker": {
        "weight_plain": 500, "weight_sub": 500, "weight_main": 600, "size_plain": 52, "size_sub": 52, "size_main": 78,
        "tracking": -0.055, "leading": 1.12, "align": "left", "position_y": 0.42, "max_width": 0.66,
        "animation": "blur", "anim_ms": 240, "slide_in": 0.6, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.02,
        "glow": None, "exit": "blur",
    },
    # juda qalin katta so'z harfma-harf sakrab chiqadi, ostida mayda izoh (namuna 14)
    "heavy": {
        "weight_main": 800, "weight_sub": 500, "weight_plain": 700, "size_main": 270, "size_huge": 360,
        "size_sub": 52, "size_plain": 120, "tracking": -0.065, "leading": 0.96, "case": "asis", "align": "left",
        "fit_sub": True, "fit_min": 0.5, "fit_max": 2.2,
        "anim_main": "letters", "anim_sub": "blur", "animation": "blur", "letter_ms": 60, "letter_from": "below",
        "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.02, "exit": "drop", "exit_ms": 230, "glow": None,
        "shadow": {"blur": 22, "dy": 6, "opacity": 0.3, "color": "#000000"},
    },
    # qiya sariq sarlavha: harflar keng chiqib zichlashadi, ostidagi so'zlar pastdan o'tiradi (namuna 6)
    "italic": {
        "italic": True, "weight_main": 700, "weight_sub": 400, "weight_plain": 600, "big_accent": True,
        "size_main": 104, "size_sub": 52, "size_plain": 80, "case": "asis", "align": "left",
        "anim_main": "ltrack", "anim_sub": "rise", "animation": "blur", "letter_ms": 50, "letter_track": 0.3,
        "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.03, "glow": {"blur": 18, "opacity": 0.6}, "exit": "blur",
    },
    # ovozli xabar sahnasi ostidagi matn: Har So'z Bosh Harfda, bir-ikki so'zdan (namuna 4, 10)
    "karaoke": {
        "weight_plain": 600, "weight_sub": 600, "size_plain": 58, "size_sub": 58, "size_main": 70,
        "tracking": -0.05, "case": "title", "strip_punct": False, "position_y": 0.745,
        "reveal": "cue", "animation": "fade", "anim_ms": 90, "slide_in": 0.0, "track_in": 0.0, "intro_scale": 1.0, "drift": 0.0,
        "exit": "none", "glow": None, "shadow": {"blur": 10, "dy": 2, "opacity": 0.3, "color": "#000000"},
    },
}


# Instagram Reels interfeysi yopadigan chetlar (kadrga nisbatan). Manba: ffmpeg-skill loyihasidagi
# platforma jadvali (MIT), style.json: platform.safe orqali o'zgartiriladi.
DEFAULT_SAFE = {"top": 0.08, "bottom": 0.20, "left": 0.05, "right": 0.12}


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
        safe = dict(DEFAULT_SAFE)
        safe.update(style.get("platform", {}).get("safe", {}) or {})
        self.safe = safe                             # ilova tugmalari yopadigan chetlar (kadrga nisbatan)
        self.notes: list = []

    def note(self, text: str) -> None:
        """Render to'xtamaydigan ogohlantirish (oxirida ko'rsatiladi), takrorlanmaydi."""
        if text not in self.notes:
            self.notes.append(text)

    def check_safe(self, what: str, left: float, top: float, right: float, bottom: float) -> None:
        s = self.safe
        out = []
        if top < s["top"] * self.H - 2:
            out.append("tepadan")
        if bottom > (1 - s["bottom"]) * self.H + 2:
            out.append("pastdan")
        if left < s["left"] * self.W - 2:
            out.append("chapdan")
        # o'ng tomondagi tugmalar (yoqtirish, izoh, ulashish) kadrning pastki yarmida turadi:
        # tepada turgan narsaga o'ng chegara qo'llanmaydi
        if right > (1 - s["right"]) * self.W + 2 and bottom > 0.45 * self.H:
            out.append("o'ngdan")
        if out:
            self.note(f"{what} xavfsiz zonadan chiqyapti ({', '.join(out)}): Instagram tugmalari yopishi mumkin.")

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


MARKS = {"!!": "huge", "**": "big_accent", "*": "big", "\x01": "accent", "==": "mark", "~~": "mark2"}
CUE_TAG = re.compile(r"^\s*\{([A-Za-z][\w-]*)((?:,[A-Za-z_]+=[^,{}\s]+)*)\}\s*")


def split_cue_tag(text: str) -> tuple:
    """Bo'lak boshidagi uslub belgisini ajratadi: "{caps,y=0.2} MATN" -> ("caps", {"y": "0.2"}, "MATN")."""
    m = CUE_TAG.match(text)
    if not m:
        return None, {}, text
    opts = dict(part.split("=", 1) for part in m.group(2).split(",") if part)
    return m.group(1), opts, text[m.end():]


def parse_markup(text: str) -> list:
    """Belgilangan matnni so'zlarga ajratadi: [(so'z, daraja, yangi_qator)].

    *so'z* katta, **so'z** katta + rangli, !!so'z!! juda katta + rangli, _so'z_ faqat rangli,
    ==so'z== marker bilan bo'yalgan (urg'u rangi), ~~so'z~~ ikkinchi rangli marker.
    Belgilar butun so'z(lar) atrofiga qo'yiladi. "\\n" majburiy yangi qator. "\\*" oddiy yulduzcha (*3 oyda).
    """
    text = text.replace("\\*", "\x02")
    # "_" faqat so'z chegarasida belgi hisoblanadi (masalan @ilm_markazi ichidagisi oddiy harf)
    text = re.sub(r"(?<!\S)_(?=\S)", "\x01", text)
    text = re.sub(r"(?<=\S)_(?=$|[\s.,!?;:])", "\x01", text)
    out, level, newline = [], "normal", False
    for tok in re.split(r"(!!|\*\*|\*|==|~~|\x01|\n|[ \t\r\f\v]+)", text):
        if not tok:
            continue
        if tok == "\n":
            newline = True
        elif tok.isspace():
            continue
        elif tok in MARKS:
            level = "normal" if level == MARKS[tok] else MARKS[tok]
        else:
            out.append((tok.replace("\x02", "*"), level, newline))
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
    if mode == "smart":
        return word          # yozilganidek; gap boshidagi bosh harfni CaptionLayer kichraytiradi
    if mode == "title":
        for i, c in enumerate(word):
            if c.isalpha():
                return word[:i] + c.upper() + word[i + 1:]
    return word


class RichBlock:
    """Bir necha qatorli, har xil o'lchamli matn bloki. So'zlar alohida sprite bo'lib saqlanadi.

    Animatsiya turlari (cfg["animation"], asosiy so'zlar uchun "anim_main", kichik so'zlar uchun "anim_sub"):
      blur    - xiralikdan ochiladi va biroz ko'tariladi
      fade    - shunchaki ochiladi
      pop     - prujina bilan kattalashib chiqadi
      rise    - pastroqdan chiqib joyiga o'tiradi
      flicker - bir-ikki marta miltillab yonadi
      bar     - avval so'z o'rnida to'ldirilgan to'rtburchak, keyin so'zning o'zi
      letters - harflar birin-ketin sakrab chiqadi (letter_from: below | above)
      ltrack  - harflar keng oraliq bilan chiqib, zichlashadi
      none    - animatsiyasiz
    Butun blok: track_in (so'zlar orasi boshida keng, keyin zichlashadi), intro_scale, drift, exit.
    """

    def __init__(self, ctx: Ctx, text: str, cfg: dict, size_scale: float = 1.0):
        self.ctx, self.cfg = ctx, cfg
        k = ctx.k * size_scale
        tokens = []
        for word, level, newline in parse_markup(fix_apostrophes(text)):
            if cfg.get("strip_punct"):
                word = word.rstrip(".,;:").lstrip(",.")
            mode = cfg.get("case_main") if (level in ("big", "big_accent", "huge") and cfg.get("case_main")) else cfg.get("case", "asis")
            word = apply_case(word, str(mode))
            if word:
                if tokens and not newline and not any(ch.isalnum() for ch in word):
                    level = tokens[-1]["level"]      # emoji oldingi so'z bilan bir qatorda va bir o'lchamda turadi
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
        hl = dict(cfg.get("highlight") or {})
        hl2 = dict(cfg.get("highlight2") or {})
        anim_all = str(cfg.get("animation", "blur"))
        anim_main, anim_sub = str(cfg.get("anim_main") or anim_all), str(cfg.get("anim_sub") or anim_all)
        for name in (anim_all, anim_main, anim_sub):
            if name not in CAPTION_ANIMS:
                raise C.MontajError(f"Subtitr animatsiyasi noto'g'ri: {name!r}. Mumkin: {', '.join(CAPTION_ANIMS)}")
        font_main = cfg.get("font_main") or cfg["font"]
        italic_main = cfg.get("italic") if cfg.get("italic_main") is None else cfg.get("italic_main")
        for t in tokens:
            lvl = t["level"]
            big = lvl in ("big", "big_accent", "huge")
            if lvl == "huge":
                size, weight = cfg["size_huge"], cfg["weight_main"]
            elif big:
                size, weight = cfg["size_main"], cfg["weight_main"]
            elif emph:
                size, weight = cfg["size_sub"], cfg["weight_sub"]
            else:
                size, weight = cfg["size_plain"], cfg["weight_plain"]
            t["size"] = size * k
            t["font"] = ctx.fonts.get(font_main if big else cfg["font"], t["size"], weight,
                                      bool(italic_main if big else cfg.get("italic")))
            colored = lvl in ("big_accent", "huge", "accent") or (lvl == "big" and cfg.get("big_accent"))
            t["boxed"] = bool(box) and big
            t["mark"] = {"mark": hl, "mark2": hl2}.get(lvl)
            t["color"] = box.get("text", "#111111") if t["boxed"] else (accent if colored else cfg["color"])
            t["opacity"] = 1.0 if lvl != "normal" or not emph else float(cfg.get("sub_opacity", 1.0))
            t["track"] = float(cfg.get("tracking", 0)) * t["size"]
            t["emph"] = big
            t["anim"] = anim_main if big else (anim_sub if emph else anim_all)

        # qatorlarga bo'lish: o'lcham o'zgarsa yoki kenglikka sig'masa yangi qator
        max_w = float(cfg.get("max_width", 0.84)) * ctx.W
        word_space = float(cfg.get("word_space", 0.9))
        star_kern = float(cfg.get("star_kern", 0.07))

        def measure(t: dict) -> float:
            if t["text"][:1] == "*" and len(t["text"]) > 1 and t["text"][1].isalnum():
                return (M.measure(t["font"], "*", 0) - star_kern * t["size"]
                        + M.measure(t["font"], t["text"][1:], t["track"]))
            return M.measure(t["font"], t["text"], t["track"])

        if emph and cfg.get("fit_sub"):
            self._fit_sub(tokens, cfg, k, max_w, word_space, measure)
        lines, cur, cur_w = [], [], 0.0
        for t in tokens:
            t["w"] = measure(t)
            space = t["font"].getlength(" ") * word_space + t["track"]
            add = t["w"] + (space if cur else 0)
            if cur and (t["newline"] or abs(cur[0]["size"] - t["size"]) > 0.5 or cur_w + add > max_w):
                lines.append(cur)
                cur, cur_w, add = [], 0.0, t["w"]
            t["gap"] = space if cur else 0.0
            cur.append(t)
            cur_w += add
        if cur:
            lines.append(cur)

        self.words, self.boxes, self.marks = [], [], []
        leading = float(cfg.get("leading", 1.02))
        widths = [sum(t["w"] + t["gap"] for t in line) for line in lines]
        self.width = max(widths) if widths else 0.0
        y = 0.0
        align = str(cfg.get("align", "center"))
        shadow_cfg = cfg.get("shadow")
        for li, (line, lw) in enumerate(zip(lines, widths)):
            size = line[0]["size"]
            pad_y = (box.get("pad_y", 0.16) * size) if (box and line[0]["boxed"]) else 0.0
            y += pad_y
            baseline = y + size * 0.80
            x = 0.0 if align == "left" else ((self.width - lw) if align == "right" else (self.width - lw) / 2)
            if box and line[0]["boxed"]:
                px = box.get("pad_x", 0.34) * size
                bw, bh = int(lw + px * 2), int(size * 1.02 + pad_y * 2)
                spr = M.rounded_rect_sprite(bw, bh, box.get("radius", 0.26) * size,
                                            M.rgb(box.get("color", accent)) + (255,),
                                            shadow={"blur": 14 * ctx.k, "dy": 6 * ctx.k, "opacity": 0.35})
                self.boxes.append({"spr": spr, "x": x - px, "y": y - pad_y, "first": len(self.words)})
            group = None
            for wi, t in enumerate(line):
                x += t["gap"]
                glow = None
                if cfg.get("glow") and t["color"] == accent:
                    glow = dict(cfg["glow"], blur=cfg["glow"].get("blur", 18) * ctx.k, color=accent)
                shadow = None
                if shadow_cfg and not t["boxed"]:
                    shadow = dict(shadow_cfg, blur=shadow_cfg.get("blur", 16) * ctx.k, dy=shadow_cfg.get("dy", 4) * ctx.k)
                stroke = None
                if cfg.get("stroke"):
                    stroke = dict(cfg["stroke"], width=cfg["stroke"].get("width", 4) * ctx.k)
                word = {"x": x, "y": baseline, "w": t["w"], "size": size, "opacity": t["opacity"], "emph": t["emph"],
                        "text": t["text"], "line": li, "li": wi, "ln": len(line), "anim": t["anim"],
                        "color": t["color"], "letters": None, "pre": None, "group": None}
                if t["mark"] is not None:
                    # marker: so'z avval urg'u rangida chiqadi, keyin ustidan rangli quti "surtiladi"
                    mk = t["mark"]
                    fill = mk.get("color") or accent
                    word["pre"], _ = M.word_sprite(t["text"], t["font"], mk.get("pre") or fill, t["track"], shadow)
                    word["spr"], _ = M.word_sprite(t["text"], t["font"], mk.get("text", "#111111"), t["track"])
                    if group is None or group["fill"] != fill:
                        group = {"fill": fill, "x0": x, "x1": x + t["w"], "y": baseline, "size": size,
                                 "words": [], "cfg": mk}
                        self.marks.append(group)
                    group["x1"] = x + t["w"]
                    group["words"].append(len(self.words))
                    word["group"] = len(self.marks) - 1
                    word["anim"] = anim_all if anim_all in ("blur", "fade", "none", "rise") else "blur"
                else:
                    group = None
                    if t["text"][:1] == "*" and len(t["text"]) > 1 and t["text"][1].isalnum():
                        # "*3 oyda": yulduzcha so'zga yopishib turadi (namunalardagi belgi)
                        star, adv = M.word_sprite("*", t["font"], cfg.get("star_color") or t["color"], 0, shadow, glow, stroke)
                        rest, _ = M.word_sprite(t["text"][1:], t["font"], t["color"], t["track"], shadow, glow, stroke)
                        word["spr"] = M.merge_sprites([(star, 0.0, 0.0), (rest, adv - star_kern * size, 0.0)])
                    else:
                        word["spr"], _ = M.word_sprite(t["text"], t["font"], t["color"], t["track"], shadow, glow, stroke)
                    if word["anim"] in ("letters", "ltrack") and all(kind == "text" for kind, _ in M.Emoji.split(t["text"])):
                        word["letters"] = self._letters(t, shadow, glow, stroke)
                self.words.append(word)
                x += t["w"]
            y += size * leading + pad_y
        self.height = y
        for g in self.marks:
            mk, size = g["cfg"], g["size"]
            px, top, bottom = float(mk.get("pad_x", 0.14)) * size, float(mk.get("top", 0.86)) * size, float(mk.get("bottom", 0.24)) * size
            w, h = int(g["x1"] - g["x0"] + px * 2), int(top + bottom)
            g["spr"] = M.rounded_rect_sprite(max(2, w), max(2, h), float(mk.get("radius", 0.10)) * size,
                                             M.rgb(g["fill"]) + (255,))
            g["bx"], g["by"], g["bw"] = g["x0"] - px, g["y"] - top, w
        self.line_sizes = [line[0]["size"] for line in lines]
        self._bars: dict = {}

    def _fit_sub(self, tokens: list, cfg: dict, k: float, max_w: float, word_space: float, measure) -> None:
        """Kichik qator(lar)ni asosiy ibora kengligiga moslaydi (namunalardagi "blok" ko'rinishi).

        Kichik so'zlar bitta qatorga sig'sa o'lchami asosiy qator kengligiga tenglashadi; juda maydalashib
        ketadigan bo'lsa ikki qatorga bo'linadi. O'lcham size_sub ning fit_min..fit_max ulushida qoladi.
        """
        def width(run: list) -> float:
            return sum(measure(t) for t in run) + sum(t["font"].getlength(" ") * word_space + t["track"] for t in run[1:])

        def resize(run: list, factor: float) -> None:
            for t in run:
                t["size"] = t["size"] * factor
                t["font"] = self.ctx.fonts.get(cfg["font"], t["size"], cfg["weight_sub"], bool(cfg.get("italic")))
                t["track"] = float(cfg.get("tracking", 0)) * t["size"]

        # asosiy iboradan OLDINGI kichik so'zlar (tepadagi yorliq: "Men", "bugun", ==Kamerani==) o'z o'lchamida qoladi
        runs, cur, seen_big = [], [], False
        for t in tokens:
            if t["emph"] or t["newline"]:
                if cur and seen_big:
                    runs.append(cur)
                cur = [] if t["emph"] else [t]
                seen_big = seen_big or t["emph"]
            else:
                cur.append(t)
        if cur and seen_big:
            runs.append(cur)
        big = [t for t in tokens if t["emph"]]
        if not big or not runs:
            return
        # asosiy iboraning eng keng qatori (o'zi ham kenglikka sig'masa bo'linadi)
        main_w, line_w = 0.0, 0.0
        for i, t in enumerate(big):
            add = measure(t) + (t["font"].getlength(" ") * word_space + t["track"] if line_w else 0)
            if line_w and (t["newline"] or abs(big[i - 1]["size"] - t["size"]) > 0.5 or line_w + add > max_w):
                main_w, line_w, add = max(main_w, line_w), 0.0, measure(t)
            line_w += add
        main_w = max(main_w, line_w)
        lo, hi = float(cfg.get("fit_min", 0.62)), float(cfg.get("fit_max", 1.1))
        for run in runs:
            w = width(run)
            if w <= 0:
                continue
            factor = main_w / w
            if factor < lo and len(run) >= 3:
                # ikki qator: uzunliklari eng yaqin bo'ladigan joydan bo'linadi, kengrog'i asosiy qatorga tenglashadi
                best, cut = None, 1
                for i in range(1, len(run)):
                    wide = max(width(run[:i]), width(run[i:]))
                    if best is None or wide < best:
                        best, cut = wide, i
                run[cut]["newline"] = True
                factor = main_w / best
            resize(run, min(hi, max(lo, factor)))

    @staticmethod
    def _letters(t: dict, shadow, glow, stroke) -> list:
        """So'zni harflarga bo'ladi: [(sprite, x siljish, kenglik)]. Harflar orasidagi masofa asl so'zdagidek."""
        out, x, text, font = [], 0.0, t["text"], t["font"]
        for i, ch in enumerate(text):
            nxt = text[i + 1:i + 2]
            adv = (font.getlength(ch + nxt) - font.getlength(nxt) if nxt else font.getlength(ch)) + (t["track"] if nxt else 0)
            if not ch.isspace():
                spr, _ = M.text_sprite(ch, font, t["color"], 0.0, shadow, glow, stroke)
                out.append((spr, x, font.getlength(ch)))
            x += adv
        return out

    @property
    def plain_words(self) -> list:
        return [w["text"] for w in self.words]

    def draw(self, frame, cx: float, cy: float, t: float, times: list | None, cfg: dict,
             start: float, end: float) -> None:
        """Blokni (cx, cy) markazga chizadi. times: har bir so'zning paydo bo'lish vaqti (yoki None)."""
        k = self.ctx.k
        anim = max(0.001, float(cfg.get("anim_ms", 220)) / 1000.0)
        reveal = str(cfg.get("reveal", "word"))
        blur_px = float(cfg.get("blur_px", 14)) * k
        # ---- butun blok: kirish masshtabi, sekin o'sish, chiqish
        life = max(0.2, end - start)
        intro_from = float(cfg.get("intro_scale", 1.0))
        scale = intro_from + (1 - intro_from) * M.ease_out((t - start) / max(0.001, float(cfg.get("intro_ms", 450)) / 1000.0))
        scale *= 1.0 + float(cfg.get("drift", 0.0)) * M.clamp01((t - start) / life)
        exit_mode, exit_dur = str(cfg.get("exit", "fade")), max(0.001, float(cfg.get("exit_ms", 100)) / 1000.0)
        out_blur, sink = 0.0, 0.0
        if exit_mode == "blur":                       # tugagach xiralashib yo'qoladi (keyingi bo'lak ustidan chiqadi)
            q = M.clamp01((t - end) / exit_dur)
            out, out_blur = 1.0 - q, q * blur_px * 1.5
            scale *= 1.0 + 0.05 * q
        elif exit_mode == "drop":                     # pastga tushib ketadi
            q = M.clamp01((t - end) / exit_dur)
            out, sink = 1.0 - q * q, M.ease_in_out(q) * self.height * 0.9
        elif exit_mode == "none":
            out = 1.0 if t < end else 0.0
        else:                                         # fade: tugashidan oldin tez so'nadi va biroz cho'kadi
            out = clamp_exit(t, end, exit_dur)
            sink = (1 - out) * 8 * k
        if out <= 0.003:
            return
        # ---- so'zlar orasi boshida keng, keyin zichlashadi (qator markaziga nisbatan)
        track_in = float(cfg.get("track_in", 0.0))
        spread = track_in * (1 - M.ease_out((t - start) / max(0.001, float(cfg.get("track_ms", 1100)) / 1000.0))) if track_in else 0.0
        slide_in = float(cfg.get("slide_in", 0.0))
        slide_dur = max(0.001, float(cfg.get("slide_ms", 900)) / 1000.0)
        half_w, half_h = self.width / 2, self.height / 2

        def put(spr, xr: float, yr: float, ax: float = 0.0, ay: float = 0.0, extra: float = 1.0,
                opacity: float = 1.0, blur: float = 0.0, dx: float = 0.0, dy: float = 0.0) -> None:
            # (xr, yr) - blok ichidagi nuqta; (ax, ay) - sprite ichida joyida qoladigan nuqta
            fx = cx + (xr + ax - half_w) * scale + dx
            fy = cy + (yr + ay - half_h) * scale + dy + sink
            M.blit(frame, spr, fx - ax, fy - ay, opacity=opacity * out, scale=scale * extra,
                   blur=blur + out_blur, anchor=(ax, ay))

        def shift(w: dict) -> float:
            return (w["li"] - (w["ln"] - 1) / 2) * spread * w["size"] if spread else 0.0

        def t_of(i: int) -> float:
            return times[i] if (times and reveal in ("word", "dim")) else start

        for b in self.boxes:
            t0 = times[b["first"]] if (times and reveal != "cue") else start
            if t >= t0:
                spr = b["spr"]
                put(spr, b["x"], b["y"], spr.w / 2, spr.h / 2, 0.7 + 0.3 * M.spring((t - t0) / (anim * 1.6)),
                    M.clamp01((t - t0) / (anim * 0.6)))
        # ---- marker qutilari: guruhdagi oxirgi so'z chiqqach chapdan o'ngga surtiladi
        wiped = {}
        for gi, g in enumerate(self.marks):
            t0 = t_of(g["words"][-1]) + float(g["cfg"].get("delay_ms", 160)) / 1000.0
            p = M.ease_in_out((t - t0) / max(0.001, float(g["cfg"].get("wipe_ms", 320)) / 1000.0))
            wiped[gi] = p
            if p > 0.004:
                spr = g["spr"]
                part = M.Sprite(np.ascontiguousarray(spr.pix[:, :max(1, int(round(spr.w * p)))]), spr.ox, spr.oy)
                put(part, g["bx"] + shift(self.words[g["words"][0]]), g["by"])
        fps = 25.0
        for i, w in enumerate(self.words):
            t0 = t_of(i)
            p = (t - t0) / anim
            base_op = w["opacity"]
            sx = shift(w)
            if p < 0:
                if reveal == "dim":
                    put(w["spr"], w["x"] + sx, w["y"], opacity=base_op * float(cfg.get("dim", 0.35)))
                continue
            spr = w["spr"]
            if w["group"] is not None:
                g = self.marks[w["group"]]
                covered = wiped[w["group"]] * g["bw"] >= (w["x"] + w["w"] * 0.5 - g["bx"])
                spr = w["spr"] if covered else w["pre"]
            mode = w["anim"]
            e = M.ease_out(p)
            # har bir so'z o'ngroqdan sirg'alib kelib joyiga o'tiradi (namunalardagi asosiy harakat)
            dx = slide_in * w["size"] * scale * (1 - M.ease_out((t - t0) / slide_dur)) if slide_in else 0.0
            if mode in ("letters", "ltrack") and w["letters"]:
                step = float(cfg.get("letter_ms", 45)) / 1000.0
                ldur = max(anim, 0.26)
                last = t0 + step * (len(w["letters"]) - 1) + ldur
                if t >= last and mode == "letters":
                    put(spr, w["x"] + sx, w["y"], opacity=base_op, dx=dx)
                    continue
                from_above = str(cfg.get("letter_from", "below")) == "above"
                wide = float(cfg.get("letter_track", 0.22)) * w["size"]
                tighten = 1 - M.ease_out((t - t0) / max(0.001, float(cfg.get("track_ms", 1100)) / 1000.0))
                n = len(w["letters"])
                for j, (lspr, lx, lw) in enumerate(w["letters"]):
                    lp = (t - (t0 + j * step)) / ldur
                    if lp < 0:
                        continue
                    le = M.ease_out(lp)
                    if mode == "ltrack":
                        put(lspr, w["x"] + sx + lx + (j - (n - 1) / 2) * wide * tighten, w["y"],
                            opacity=base_op * le, blur=(1 - le) * blur_px * 0.6)
                    else:
                        dy = (1 - le) * w["size"] * 0.28 * (-1 if from_above else 1)
                        put(lspr, w["x"] + sx + lx, w["y"], lw / 2, -w["size"] * 0.30, 0.35 + 0.65 * M.spring(lp),
                            base_op * M.clamp01(lp * 3.0), dy=dy * scale)
                continue
            if mode == "none" or p >= 1:
                put(spr, w["x"] + sx, w["y"], opacity=base_op, dx=dx)
            elif mode == "pop":
                put(spr, w["x"] + sx, w["y"], w["w"] / 2, -w["size"] * 0.35, 0.6 + 0.4 * M.spring(p),
                    base_op * M.clamp01(p * 2.5))
            elif mode == "fade":
                put(spr, w["x"] + sx, w["y"], opacity=base_op * e, dx=dx)
            elif mode == "rise":
                put(spr, w["x"] + sx, w["y"], opacity=base_op * M.clamp01(p * 2.2),
                    dx=dx, dy=(1 - M.spring(p, 9.0, 0.62)) * w["size"] * 0.42 * scale)
            elif mode == "flicker":
                # 25 kadr/s ritmida: yonadi, ikki kadr xira, yana yonadi ... keyin barqaror
                n = int((t - t0) * fps + 1e-6)
                put(spr, w["x"] + sx, w["y"], opacity=base_op * (FLICKER[n] if n < len(FLICKER) else 1.0))
            elif mode == "bar":
                if (t - t0) < float(cfg.get("bar_ms", 120)) / 1000.0:
                    key = (i, w["color"])
                    if key not in self._bars:
                        self._bars[key] = M.rounded_rect_sprite(max(2, int(w["w"])), max(2, int(w["size"] * 0.74)),
                                                                0, M.rgb(w["color"]) + (255,))
                    put(self._bars[key], w["x"] + sx, w["y"] - w["size"] * 0.70, opacity=base_op)
                else:
                    put(spr, w["x"] + sx, w["y"], opacity=base_op)
            else:  # blur: xiralikdan ochiladi va biroz pastdan ko'tariladi
                put(spr, w["x"] + sx, w["y"], opacity=base_op * e, blur=(1 - e) * blur_px,
                    dx=dx, dy=(1 - e) * float(cfg.get("rise_px", 10)) * k)

    @staticmethod
    def tail(cfg: dict) -> float:
        """Bo'lak tugaganidan keyin ham chizilishi kerak bo'lgan vaqt (chiqish animatsiyasi)."""
        if str(cfg.get("exit", "fade")) in ("blur", "drop"):
            return float(cfg.get("exit_ms", 100)) / 1000.0
        return 0.0


def clamp_exit(t: float, end: float, dur: float) -> float:
    return M.clamp01((end - t) / dur) if dur > 0 else 1.0


def appear(t: float, start: float, end: float, tin: float = 0.42, tout: float = 0.14) -> tuple:
    """Element paydo bo'lishi/yo'qolishi: (shaffoflik, masshtab).

    Kirish: prujina bilan kattalashib chiqadi. Chiqish: tezroq, biroz kichrayib so'nadi.
    """
    p_in = (t - start) / tin if tin > 0 else 1.0
    out = clamp_exit(t, end, tout)
    return M.clamp01(p_in * 4.0) * out, (0.6 + 0.4 * M.spring(p_in)) * (0.92 + 0.08 * out)


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
    """Subtitr: SRT bo'laklari, so'zlar nutq bilan birga ochiladi.

    Bo'lak boshida uslub belgisi bo'lishi mumkin: "{caps,y=0.2} MATN" - shu bo'lak boshqa presetda,
    boshqa joyda chiziladi (namuna videolardagi kabi: sarlavha bir uslubda, oddiy gap boshqasida).
    Belgi sozlamalari: y, x (0..1), size (ko'paytma), align, anim, anim_main, anim_sub, exit, case.
    """
    z = 50
    TAG_NUM = {"y": "position_y", "x": "position_x", "size": "_size", "track": "track_in", "drift": "drift"}
    TAG_STR = {"align": "align", "anim": "animation", "anim_main": "anim_main", "anim_sub": "anim_sub",
               "exit": "exit", "case": "case", "reveal": "reveal", "color": "color", "accent": "accent"}

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
            name, opts, text = split_cue_tag(cue["text"])
            prev = strip_markup(cues[i - 1]["text"]).rstrip() if i else ""
            sentence_start = not prev or prev[-1:] in ".!?\u2026"
            self.items.append({"start": cue["start"], "end": end, "text": text, "cue": dict(cue, text=text),
                               "block": None, "times": None, "cfg": self._cue_cfg(name, opts, cue), "tail": 0.0,
                               "sentence_start": sentence_start})
            self.items[-1]["tail"] = RichBlock.tail(self.items[-1]["cfg"])
        self.words, self._word_times = words, S.word_times

    def _cue_cfg(self, name, opts: dict, cue: dict) -> dict:
        if name is None and not opts:
            return self.cfg
        over = {}
        if name and name not in ("default", str(self.cfg.get("preset", "clean"))):
            if name not in CAPTION_PRESETS:
                raise C.MontajError(f"Subtitr bo'lagidagi uslub noma'lum: {{{name}}} ({C.fmt_time(cue['start'])}). "
                                    f"Mumkin: {', '.join(CAPTION_PRESETS)}")
            # bo'lakda boshqa preset aytilgan bo'lsa, o'sha presetning o'z qiymatlari umumiy sozlamadan ustun turadi
            over.update({key: val for key, val in CAPTION_PRESETS[name].items()})
            over["preset"] = name
        for key, val in opts.items():
            if key in self.TAG_NUM:
                try:
                    over[self.TAG_NUM[key]] = float(val)
                except ValueError:
                    raise C.MontajError(f"Subtitr belgisida {key}={val!r} son emas ({C.fmt_time(cue['start'])}).")
            elif key in self.TAG_STR:
                over[self.TAG_STR[key]] = val
            else:
                raise C.MontajError(f"Subtitr belgisida noma'lum sozlama: {key} ({C.fmt_time(cue['start'])}). "
                                    f"Mumkin: {', '.join(sorted(set(self.TAG_NUM) | set(self.TAG_STR)))}")
        cfg = self.ctx.caption_cfg({"preset": over.get("preset", self.cfg.get("preset", "clean"))})
        for key in ("font", "accent"):          # brend shrifti va rangi har qanday presetda saqlanadi
            keep = self.ctx.style.get("captions", {}).get(key)
            if keep and key in over and key not in opts:
                over[key] = keep
        cfg.update(over)
        return cfg

    def _prepare(self, item: dict) -> None:
        cfg = item["cfg"]
        size = float(cfg.get("_size", 1.0))
        if str(cfg.get("case")) == "smart" and item["sentence_start"]:
            # gap boshidagi bosh harf kichraytiriladi; gap ichidagi atoqli otlar (Rus, Instagram) yozilganidek qoladi
            item["text"] = re.sub(r"^((?:\{[^{}]*\}|[^\w]|_)*)([^\W\d_])(?=[^\W\d_]*[a-z\u0430-\u044f\u2018\u2019'])",
                                  lambda m: m.group(1) + m.group(2).lower(), item["text"], count=1)
        block = RichBlock(self.ctx, item["text"], cfg, size)
        # juda keng chiqsa xavfsiz zonaga sig'adigan qilib kichraytiriladi (o'ngda Instagram tugmalari bor)
        safe = self.ctx.safe
        room = (1 - 2 * max(safe["left"], safe["right"])) * self.ctx.W
        if block.width > room:
            block = RichBlock(self.ctx, item["text"], cfg, size * max(0.6, room / block.width * 0.99))
        tokens = block.plain_words
        cx, cy = self._center(block, cfg)
        self.ctx.check_safe(f"Subtitr ({C.fmt_time(item['start'])})", cx - block.width / 2, cy - block.height / 2,
                            cx + block.width / 2, cy + block.height / 2)
        item["block"] = block
        # emoji va tinish belgilari aytilmaydi: ular oldingi so'z bilan birga chiqadi
        spoken = [i for i, tok in enumerate(tokens) if any(ch.isalnum() for ch in tok)]
        times = [item["start"]] * len(tokens)
        if spoken:
            got = self._word_times(item["cue"], [tokens[i] for i in spoken], self.words)
            last = item["start"]
            pos = dict(zip(spoken, got))
            for i in range(len(tokens)):
                if i in pos:
                    last = pos[i]
                    times[i] = last
                else:
                    times[i] = min(last + 0.06, item["end"])
        item["times"] = times

    def _center(self, block, cfg: dict) -> tuple:
        """Blok markazi. align left/right bo'lsa position_x blokning shu chetini bildiradi."""
        W, H = self.ctx.W, self.ctx.H
        align = str(cfg.get("align", "center"))
        px = cfg.get("position_x")
        if px is None:
            px = {"left": self.ctx.safe["left"] + 0.03, "right": 1 - self.ctx.safe["right"] - 0.03}.get(align, 0.5)
        cx = float(px) * W + {"left": block.width / 2, "right": -block.width / 2}.get(align, 0.0)
        return cx, float(cfg["position_y"]) * H

    def draw(self, frame, t: float) -> None:
        for item in self.items:
            if item["start"] <= t < item["end"] + item["tail"]:
                if item["block"] is None:
                    self._prepare(item)
                    if t >= item["end"] + item["tail"]:
                        continue
                cx, cy = self._center(item["block"], item["cfg"])
                item["block"].draw(frame, cx, cy, t, item["times"], item["cfg"], item["start"], item["end"])
            elif item["block"] is not None and t >= item["end"] + item["tail"]:
                item["block"] = None  # xotirani bo'shatish


class TextLayer(Layer):
    """Erkin matn yoki sarlavha. Belgilar subtitrdagi kabi (*katta*, **rangli**, !!juda katta!!)."""
    z = 45

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        override = {"reveal": "cue", "animation": el.get("anim", "blur"), "case": el.get("case", "asis"),
                    "strip_punct": False, "auto_numbers": False}
        for key in ("preset", "font", "color", "accent", "align", "max_width", "italic", "box", "glow", "tracking"):
            if key in el:
                override[key] = el[key]
        if "weight" in el:
            override.update(weight_sub=el["weight"], weight_plain=el["weight"], weight_main=el["weight"])
        self.ctx, self.cfg = ctx, ctx.caption_cfg(override)
        self.behind_person = bool(el.get("behind_person", False))
        self.block = RichBlock(ctx, str(el.get("text", "")), self.cfg, float(el.get("size", 1.0)))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H
        # stagger: so'zlar birin-ketin chiqadi (soniya); loop: "bob" - sekin tebranib turadi
        self.times = None
        stagger = float(el.get("stagger", 0))
        if stagger > 0:
            self.cfg = dict(self.cfg, reveal="word")
            self.times = [self.start + i * stagger for i in range(len(self.block.words))]
        self.loop = str(el.get("loop", "none"))
        if self.loop not in ("none", "bob"):
            raise C.MontajError(f"loop noto'g'ri: {self.loop!r}. Mumkin: none, bob")
        self.k = ctx.k
        half_w, half_h = self.block.width / 2, self.block.height / 2
        ctx.check_safe(f"Matn ({strip_markup(str(el.get('text', '')))[:24]})", self.cx - half_w, self.cy - half_h,
                       self.cx + half_w, self.cy + half_h)

    def draw(self, frame, t: float) -> None:
        cy = self.cy
        if self.loop == "bob":
            cy += math.sin((t - self.start) * 2 * math.pi / 2.6) * 7 * self.k
        self.block.draw(frame, self.cx, cy, t, self.times, self.cfg, self.start, self.end)


class VideoReader:
    """Qo'shimcha videodan kadrlarni ketma-ket o'qiydi (ffmpeg orqali, kerakli o'lchamda)."""

    def __init__(self, path: Path, w: int, h: int, fps: float, cover: bool = True):
        self.path, self.w, self.h, self.fps = Path(path), int(w), int(h), fps
        self.proc, self.pos, self.last = None, -1, None
        meta = C.ffprobe_info(path)
        self.duration = meta["duration"]
        self.alpha = bool(meta.get("alpha"))        # shaffof fonli video (ProRes 4444, WebM alfa)
        self.codec = meta.get("vcodec")
        self.cover = cover
        self.channels = 4 if self.alpha else 3

    def _open(self, offset: float) -> None:
        self.close()
        cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error"]
        if offset > 0.01:
            cmd += ["-ss", f"{offset:.3f}"]
        if self.alpha and self.codec in ("vp9", "vp8"):   # WebM alfa kanali faqat libvpx dekoderi bilan o'qiladi
            cmd += ["-c:v", "libvpx-vp9" if self.codec == "vp9" else "libvpx"]
        fmt = "rgba" if self.alpha else "rgb24"
        fit = (f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}"
               if self.cover else f"scale={self.w}:{self.h}")
        cmd += ["-i", str(self.path), "-an", "-vf", f"fps={self.fps:g},{fit},format={fmt}",
                "-f", "rawvideo", "-pix_fmt", fmt, "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.pos = int(round(offset * self.fps)) - 1

    def frame_at(self, t_rel: float):
        idx = max(0, int(round(t_rel * self.fps)))
        if self.proc is None or idx < self.pos or idx > self.pos + 3:
            self._open(min(idx / self.fps, max(0.0, self.duration - 0.05)))
        size = self.w * self.h * self.channels
        while self.pos < idx:
            buf = self.proc.stdout.read(size)
            if len(buf) < size:
                break  # video tugadi: oxirgi kadr ushlab turiladi
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, self.channels)
            self.pos += 1
        return self.last

    def sprite_at(self, t_rel: float):
        """Shaffof video kadri sprite sifatida (alfa oldindan ko'paytirilgan). Nuqtasi: markaz."""
        frame = self.frame_at(t_rel)
        if frame is None:
            return None
        if self.alpha:
            pix = frame.astype(np.uint16)
            pix[..., :3] = (pix[..., :3] * pix[..., 3:4] + 127) // 255
            pix = pix.astype(np.uint8)
        else:
            pix = np.dstack([frame, np.full(frame.shape[:2], 255, np.uint8)])
        return M.Sprite(pix, -self.w / 2, -self.h / 2)

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
        W, H = self.ctx.W, self.ctx.H
        op = 1.0
        if self.fade > 0:
            op = M.clamp01((t - self.start) / self.fade) * clamp_exit(t, self.end, self.fade)
        if self.reader is not None and self.reader.alpha and self.mode == "full":
            # shaffof fonli video (masalan Remotion yoki After Effects'dan): asosiy video ustiga qo'yiladi
            spr = self.reader.sprite_at(self.offset + t - self.start)
            if spr is not None:
                M.blit(frame, spr, W / 2, H / 2, opacity=op)
            return
        content = self._content(t)
        if content is None:
            return
        content = content[..., :3]
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
            self.reader = VideoReader(self.path, self.width, self.vh, ctx.fps, cover=False)
            self.spr = None
        else:
            border = float(el.get("border", 0)) * ctx.W          # oq hoshiya (kartochka ko'rinishi)
            rotate = float(el.get("rotate", 0))                  # biroz qiyshaytirish (gradus)
            if border > 0 or abs(rotate) > 0.05:
                self.spr = self._framed(border, str(el.get("border_color", "#FFFFFF")), rotate)
            else:
                self.spr = M.image_sprite(self.path, width=self.width, radius=self.radius, shadow=self.shadow)
        pad = math.ceil(18 * ctx.k * 3 + 8 * ctx.k) if (self.shadow and self.spr) else 0   # soya chetini hisobga olmaymiz
        half_w = (self.spr.w / 2 - pad) if self.spr else self.width / 2
        half_h = (self.spr.h / 2 - pad) if self.spr else self.vh / 2
        ctx.check_safe(f"Rasm ({self.path.name})", self.cx - half_w, self.cy - half_h, self.cx + half_w, self.cy + half_h)

    def _framed(self, border: float, color: str, rotate: float) -> M.Sprite:
        """Rasm atrofiga hoshiya chizadi va (kerak bo'lsa) qiyshaytiradi."""
        try:
            img = Image.open(self.path).convert("RGBA")
        except Exception as exc:
            raise C.MontajError(f"Rasmni ochib bo'lmadi ({self.path.name}): {exc}") from exc
        b = int(round(border))
        inner_w = max(8, self.width - 2 * b)
        img = img.resize((inner_w, max(8, int(round(inner_w * img.height / img.width)))), Image.LANCZOS)
        if b > 0:
            if self.radius > 0:
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1],
                                                       radius=max(1, self.radius - b), fill=255)
                img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", img.size, 0), mask))
            card = Image.new("RGBA", (img.width + 2 * b, img.height + 2 * b), M.rgb(color) + (255,))
            card.alpha_composite(img, (b, b))
            img = card
        if self.radius > 0:
            mask = Image.new("L", (img.width * 3, img.height * 3), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, mask.width - 1, mask.height - 1], radius=self.radius * 3, fill=255)
            mask = mask.resize(img.size, Image.LANCZOS)
            img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", img.size, 0), mask))
        if abs(rotate) > 0.05:
            img = img.rotate(-rotate, resample=Image.BICUBIC, expand=True)
        return M.pil_sprite(img, 0, self.shadow)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        if self.anim == "fade":
            scale = 1.0
        elif self.anim == "none":
            op, scale = 1.0, 1.0
        spr = self.spr
        if self.reader is not None:
            spr = self.reader.sprite_at(t - self.start)
            if spr is None:
                return
        elif t - self.start > 1.0:
            scale *= M.breathe(t - self.start)       # uzoq turgan rasm sekin "nafas oladi"
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
        self.glass = str(el.get("style", "solid")) == "glass"
        self.tile_spr = M.rounded_rect_sprite(self.tile, self.tile, 30 * k, self.color + ((0,) if self.glass else (215,)),
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
            card = M.rounded_rect_sprite(w, h, 26 * k, self.color + ((0,) if self.glass else (215,)), border=(255, 255, 255, 150),
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
            if self.glass:
                M.glass(frame, int(x), int(top), tile, tile, int(30 * k), opacity=op * dim, tint=self.color, tint_alpha=0.5)
            M.blit(frame, self.tile_spr, x, top, opacity=op * dim, scale=1.0 if self.glass else scale,
                   anchor=(tile / 2, tile / 2))
            M.blit(frame, self.icons[kind], x + tile / 2, top + tile / 2, opacity=op * dim,
                   scale=scale * (1.0 + (0.08 * math.sin(min(1.0, decided) * math.pi) if chosen else 0)), anchor=(0, 0))
        if self.glass:
            M.glass(frame, int(self.cx - item["w"] / 2), int(self.cy + 8 * k), item["w"], item["h"], int(26 * k),
                    opacity=op, tint=self.color, tint_alpha=0.5)
        M.blit(frame, item["card"], self.cx - item["w"] / 2, self.cy + 8 * k, opacity=op,
               scale=1.0 if self.glass else scale, anchor=(item["w"] / 2, item["h"] / 2))
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
        mx, my = float(cfg.get("margin_x", 0.07)) * ctx.W, float(cfg.get("margin_y", 0.09)) * ctx.H
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


class CalloutLayer(Layer):
    """Panel ichidagi matn: shisha (orqasi xira), qora yoki brend rangidagi kartochka."""
    z = 36

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        k = self.k = ctx.k * float(el.get("size", 1.0))
        self.kind = str(el.get("style", "glass"))
        if self.kind not in ("glass", "dark", "accent"):
            raise C.MontajError(f"callout.style noto'g'ri: {self.kind!r}. Mumkin: glass, dark, accent")
        width = float(el.get("width", 0.72)) * ctx.W
        self.pad_x, self.pad_y = 44 * k, 30 * k
        cap = ctx.caption_cfg({"preset": el.get("preset", "clean")})
        self.cfg = dict(cap, reveal="cue", animation="fade", case="asis", strip_punct=False, auto_numbers=False,
                        align=el.get("align", "center"), shadow=None if self.kind == "accent" else cap.get("shadow"),
                        max_width=(width - 2 * self.pad_x) / ctx.W, size_plain=58, size_sub=50, size_main=72,
                        color=el.get("color", "#111111" if self.kind == "accent" else "#FFFFFF"))
        if self.kind == "accent":
            self.cfg["accent"] = self.cfg["color"]   # rangli panel ustida urg'u so'zi ham matn rangida (faqat kattaroq)
        self.block = RichBlock(ctx, str(el.get("text", "")), self.cfg, float(el.get("size", 1.0)))
        self.w = int(self.block.width + 2 * self.pad_x)
        self.h = int(self.block.height + 2 * self.pad_y)
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H
        accent = M.rgb(el.get("accent", cap["accent"]))
        fill = {"glass": (255, 255, 255, 0), "dark": (18, 18, 22, 225), "accent": accent + (255,)}[self.kind]
        self.radius = int(30 * k)
        self.panel = M.rounded_rect_sprite(self.w, self.h, self.radius, fill, border=(255, 255, 255, 130),
                                           border_width=max(1, int(3 * k)) if self.kind != "accent" else 0,
                                           shadow={"blur": 20 * k, "dy": 8 * k, "opacity": 0.3})
        ctx.check_safe("Kartochka (callout)", self.cx - self.w / 2, self.cy - self.h / 2,
                       self.cx + self.w / 2, self.cy + self.h / 2)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        x0, y0 = self.cx - self.w / 2, self.cy - self.h / 2
        if self.kind == "glass":
            M.glass(frame, int(x0), int(y0), self.w, self.h, self.radius, opacity=op, blur=22 * self.k, tint_alpha=0.16)
            M.blit(frame, self.panel, x0, y0, opacity=op)
        else:
            M.blit(frame, self.panel, x0, y0, opacity=op, scale=scale, anchor=(self.w / 2, self.h / 2))
        self.block.draw(frame, self.cx, self.cy, t, None, self.cfg, self.start + 0.08, self.end)


class LowerThirdLayer(Layer):
    """Ism va lavozim plashkasi (chap pastda): rangli chiziq, ism qalin, lavozim ingichka."""
    z = 36

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        k = self.k = ctx.k * float(el.get("size", 1.0))
        cap = ctx.caption_cfg({"preset": el.get("preset", "clean")})
        shadow = {"blur": 12 * k, "dy": 3 * k, "opacity": 0.55}
        self.x, self.y = float(el.get("x", 0.07)) * ctx.W, float(el.get("y", 0.72)) * ctx.H
        name = fix_apostrophes(str(el.get("name", "")))
        if not name:
            raise C.MontajError("lower_third uchun 'name' kerak.")
        f1 = ctx.fonts.get(cap["font"], 60 * k, 700)
        self.name = M.word_sprite(name, f1, cap["color"], cap["tracking"] * 60 * k, shadow)
        self.role = None
        if el.get("role"):
            f2 = ctx.fonts.get(cap["font"], 40 * k, 500)
            self.role = M.word_sprite(fix_apostrophes(str(el["role"])), f2, cap["color"], cap["tracking"] * 40 * k, shadow)
        bar_h = int((118 if self.role else 66) * k)
        self.bar = M.rounded_rect_sprite(max(4, int(9 * k)), bar_h, 4 * k, M.rgb(el.get("accent", cap["accent"])) + (255,),
                                         shadow={"blur": 8 * k, "dy": 2 * k, "opacity": 0.3})
        self.bar_h = bar_h
        width = max(self.name[1], self.role[1] if self.role else 0) + 34 * k
        ctx.check_safe("Ism plashkasi (lower_third)", self.x, self.y, self.x + width, self.y + bar_h)

    def draw(self, frame, t: float) -> None:
        k = self.k
        out = clamp_exit(t, self.end, 0.14)
        p = (t - self.start) / 0.35
        e = M.ease_out(p)
        grow = M.ease_out((t - self.start) / 0.22)
        M.blit(frame, self.bar, self.x, self.y + self.bar_h * (1 - grow) / 2, opacity=out * M.clamp01(p * 4),
               scale=1.0)
        tx = self.x + 34 * k - (1 - e) * 36 * k
        M.blit(frame, self.name[0], tx, self.y + 50 * k, opacity=out * M.clamp01((p - 0.15) * 2.5))
        if self.role:
            e2 = M.ease_out((t - self.start - 0.1) / 0.35)
            M.blit(frame, self.role[0], self.x + 34 * k - (1 - e2) * 36 * k, self.y + 104 * k,
                   opacity=0.88 * out * M.clamp01(((t - self.start - 0.1) / 0.35 - 0.15) * 2.5))


class EmojiLayer(Layer):
    """Katta emoji: sakrab chiqadi va sekin "nafas oladi".

    sticker: true - oq hoshiyali stiker ko'rinishi; rotate: qiyalik (gradus); wiggle: tebranish (gradus).
    """
    z = 37

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        runs = [v for kind, v in M.Emoji.split(str(el.get("emoji", ""))) if kind == "emoji"]
        if not runs:
            raise C.MontajError(f"emoji elementida tanilmagan emoji: {el.get('emoji')!r} "
                                "(bayroqlar va juda yangi emojilar to'plamda yo'q).")
        size = max(16, int(float(el.get("size", 0.2)) * ctx.W))
        img = M.Emoji.image(runs[0], size)
        if el.get("sticker"):
            pad = max(2, int(size * 0.075))
            canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
            canvas.alpha_composite(img, (pad, pad))
            alpha = np.asarray(canvas)[..., 3]
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pad * 2 + 1, pad * 2 + 1))
            edge = cv2.GaussianBlur(cv2.dilate(alpha, kernel), (0, 0), max(0.6, pad * 0.12))
            white = Image.fromarray(np.dstack([np.full_like(edge, 255)] * 3 + [edge]), "RGBA")
            white.alpha_composite(canvas)
            img = white
        self.rotate, self.wiggle = float(el.get("rotate", 0)), abs(float(el.get("wiggle", 0)))
        shadow = {"blur": 14 * ctx.k, "dy": 6 * ctx.k, "opacity": 0.38}
        steps = 9 if self.wiggle else 1
        self.sprites = []
        for i in range(steps):
            ang = self.rotate + (self.wiggle * (2 * i / (steps - 1) - 1) if steps > 1 else 0)
            turned = img.rotate(ang, resample=Image.BICUBIC, expand=True) if abs(ang) > 0.05 else img
            self.sprites.append(M.pil_sprite(turned, shadow=shadow))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H
        half = self.sprites[0].w / 2
        ctx.check_safe(f"Emoji ({el.get('emoji')})", self.cx - half * 0.8, self.cy - half * 0.8,
                       self.cx + half * 0.8, self.cy + half * 0.8)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        spr = self.sprites[0]
        if len(self.sprites) > 1:
            pos = (math.sin((t - self.start) * 2 * math.pi / 1.5) + 1) / 2
            spr = self.sprites[min(len(self.sprites) - 1, int(round(pos * (len(self.sprites) - 1))))]
        M.blit(frame, spr, self.cx, self.cy, opacity=op, scale=scale * M.breathe(t - self.start, 0.02, 1.8),
               anchor=(0, 0))


class IconLayer(Layer):
    """Vektor belgi (Phosphor): fonsiz, doira, kvadrat yoki shisha fon ustida. Ostiga qisqa yozuv qo'ysa bo'ladi."""
    z = 37

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        import icons as IC
        self.ctx = ctx
        k = ctx.k
        name = str(el.get("name", "")).strip()
        if not name:
            raise C.MontajError("icon uchun 'name' kerak (qidirish: python scripts/icons.py find SO'Z).")
        self.size = size = max(24, int(float(el.get("size", 0.16)) * ctx.W))
        self.bg = str(el.get("bg", "none"))
        if self.bg not in ("none", "circle", "square", "glass"):
            raise C.MontajError(f"icon.bg noto'g'ri: {self.bg!r}. Mumkin: none, circle, square, glass")
        cap = ctx.caption_cfg()
        accent = M.rgb(el.get("accent", cap["accent"]))

        def colour(value, default):
            v = str(value) if value else default
            return accent if v == "accent" else M.rgb(v)

        plate = colour(el.get("bg_color"), "accent")
        bright = (0.299 * plate[0] + 0.587 * plate[1] + 0.114 * plate[2]) / 255
        default = "#FFFFFF" if self.bg in ("none", "glass") else ("#111111" if bright > 0.55 else "#FFFFFF")
        col = colour(el.get("color"), default)
        inner = size if self.bg == "none" else int(size * 0.56)
        icon = IC.render(name, inner, col + (255,), str(el.get("style", "fill")))
        self.radius = int(size * 0.28)
        if self.bg in ("circle", "square"):
            s = 3
            big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
            d = ImageDraw.Draw(big)
            if self.bg == "circle":
                d.ellipse([0, 0, size * s - 1, size * s - 1], fill=plate + (255,))
            else:
                d.rounded_rectangle([0, 0, size * s - 1, size * s - 1], radius=self.radius * s, fill=plate + (255,))
            img = big.resize((size, size), Image.LANCZOS)
            img.alpha_composite(icon, ((size - inner) // 2, (size - inner) // 2))
        elif self.bg == "glass":
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            img.alpha_composite(icon, ((size - inner) // 2, (size - inner) // 2))
        else:
            img = icon
        shadow = {"blur": 14 * k, "dy": 6 * k, "opacity": 0.32 if self.bg != "glass" else 0.2}
        self.spr = M.pil_sprite(img, shadow=shadow)
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.3)) * ctx.H
        self.label = None
        bottom = self.cy + size / 2
        if el.get("text"):
            fsize = float(el.get("text_size", 44)) * k
            font = ctx.fonts.get(cap["font"], fsize, 600)
            self.label = M.word_sprite(fix_apostrophes(str(el["text"])), font, "#FFFFFF", cap["tracking"] * fsize,
                                       {"blur": 10 * k, "dy": 3 * k, "opacity": 0.55})
            self.label_y = self.cy + size / 2 + fsize * 1.25
            bottom = self.label_y + fsize * 0.3
        half = max(size / 2, (self.label[1] / 2) if self.label else 0)
        ctx.check_safe(f"Belgi ({name})", self.cx - half, self.cy - size / 2, self.cx + half, bottom)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end)
        size = self.size
        if self.bg == "glass":
            M.glass(frame, int(self.cx - size / 2), int(self.cy - size / 2), size, size, self.radius, opacity=op,
                    blur=20 * self.ctx.k, tint_alpha=0.18)
        M.blit(frame, self.spr, self.cx, self.cy, opacity=op,
               scale=scale * M.breathe(t - self.start, 0.012, 2.4), anchor=(0, 0))
        if self.label:
            p = M.clamp01((t - self.start - 0.12) / 0.25)
            M.blit(frame, self.label[0], self.cx - self.label[1] / 2, self.label_y + (1 - M.ease_out(p)) * 12 * self.ctx.k,
                   opacity=p * clamp_exit(t, self.end, 0.14))


class Backdrop:
    """Chizilgan harakatli fon: qorong'i gradient, sekin suzuvchi yorug'lik dog'lari va uchqunlar.

    Tez ishlashi uchun yorug'lik kichik o'lchamda hisoblanib, keyin kattalashtiriladi.
    """

    def __init__(self, ctx: Ctx, cfg: dict):
        W, H = ctx.W, ctx.H
        self.W, self.H, self.k = W, H, ctx.k
        accent = M.rgb(cfg.get("accent", ctx.caption_cfg()["accent"]))
        c1, c2 = M.rgb(cfg.get("color1", "#05050A")), M.rgb(cfg.get("color2", "#120C22"))
        self.lw, self.lh = max(8, W // 6), max(8, H // 6)
        yy = np.linspace(0.0, 1.0, self.lh, dtype=np.float32)[:, None]
        xx = np.linspace(-1.0, 1.0, self.lw, dtype=np.float32)[None, :]
        mix = np.clip(yy * 0.85 + 0.15 * (1 - np.abs(xx)), 0, 1)[..., None]
        base = np.array(c1, np.float32) * (1 - mix) + np.array(c2, np.float32) * mix
        vign = 1.0 - 0.45 * np.clip((xx ** 2 + (2 * yy - 1) ** 2) / 2.0, 0, 1)
        self.base = base * vign[..., None]
        self.X = np.linspace(0.0, 1.0, self.lw, dtype=np.float32)[None, :]
        self.Y = np.linspace(0.0, 1.0, self.lh, dtype=np.float32)[:, None]
        strength = float(cfg.get("glow", 1.0))
        cool = M.rgb(cfg.get("color3", "#3B2A8C"))
        deep = M.rgb(cfg.get("color4", "#16307A"))
        # (rang, markaz x/y, tebranish amplitudasi x/y, davr, faza, kenglik, kuch)
        self.glows = [(accent, 0.50, 0.05, 0.22, 0.02, 11.0, 0.0, 0.24, 0.30 * strength),
                      (cool, 0.88, 0.46, 0.10, 0.12, 15.0, 1.7, 0.40, 0.60 * strength),
                      (deep, 0.10, 0.88, 0.14, 0.06, 13.0, 3.1, 0.42, 0.55 * strength),
                      (accent, 0.80, 1.02, 0.12, 0.02, 17.0, 4.4, 0.22, 0.14 * strength)]
        # sahna projektorlari: tepadagi ikki nuqtadan sekin siljiydigan nur dastalari
        self.rays = []
        if cfg.get("rays", True):
            asp = H / W
            for sx, a0, swing, period, ph in ((-0.08, 1.02, 0.16, 9.0, 0.0), (1.08, 2.12, 0.16, 11.5, 2.0)):
                dx, dy = self.X - sx, (self.Y + 0.04) * asp
                ang = np.arctan2(dy, dx).astype(np.float32)
                fall = np.clip(1.15 - np.sqrt(dx * dx + dy * dy) / (1.25 * asp), 0, 1).astype(np.float32)
                self.rays.append((ang, fall, a0, swing, period, ph))
        self.ray_col = np.array([min(255, c + 60) for c in accent], np.float32) * (0.20 * strength)
        # mayda don: tekis qorong'i fonda "zinapoya" (banding) chiqmasligi uchun
        rng = np.random.default_rng(11)
        self.grain = rng.integers(0, 5, size=(H, W, 3), dtype=np.uint8)
        pattern = str(cfg.get("pattern", "dots"))
        if pattern == "dots":
            step = max(12, int(34 * ctx.k))
            dots = np.zeros((H, W), np.uint8)
            for row, y in enumerate(range(step // 2, H, step)):
                for x in range((step // 2) if row % 2 else step, W, step):
                    cv2.circle(dots, (x, y), max(1, int(2.2 * ctx.k)), 9, -1, lineType=cv2.LINE_AA)
            self.grain = cv2.add(self.grain, cv2.merge([dots, dots, dots]))
        elif pattern == "grid":
            step = max(24, int(float(cfg.get("grid", 108)) * ctx.k))
            lines = np.zeros((H, W), np.uint8)
            lines[::step, :] = 16
            lines[:, ::step] = 16
            self.grain = cv2.add(self.grain, cv2.merge([lines, lines, lines]))
        elif pattern != "none":
            raise C.MontajError(f"background.pattern noto'g'ri: {pattern!r}. Mumkin: dots, grid, none")
        # uchqunlar (bokeh)
        r = random.Random(7)
        self.sparks = []
        sizes = [int(v * ctx.k) for v in (10, 16, 26)]
        self.spark_sprites = {}
        for size in sizes:
            for name, col in (("a", accent), ("w", (255, 255, 255))):
                d = size * 4
                g = np.zeros((d, d), np.float32)
                cv2.circle(g, (d // 2, d // 2), size, 1.0, -1, lineType=cv2.LINE_AA)
                g = cv2.GaussianBlur(g, (0, 0), size * 0.55)
                pix = np.dstack([g * col[0], g * col[1], g * col[2], g * 255]).astype(np.uint8)
                self.spark_sprites[(size, name)] = M.Sprite(pix, -d / 2, -d / 2)
        for _ in range(int(cfg.get("sparks", 26))):
            self.sparks.append({"x": r.uniform(0.02, 0.98) * W, "y": r.uniform(0, 1) * H, "v": r.uniform(18, 60) * ctx.k,
                                "key": (r.choice(sizes), r.choice("aaw")), "ph": r.uniform(0, 6.28),
                                "f": r.uniform(0.5, 1.4), "sway": r.uniform(6, 26) * ctx.k, "op": r.uniform(0.25, 0.7)})

    def draw(self, frame, t: float, boost: float = 0.0) -> None:
        """boost 0..1: chaqnash (zarba paytida projektorlar va yorug'lik bir zum kuchayadi)."""
        low = self.base.copy()
        gain = 1.0 + 0.9 * boost
        for col, cx, cy, ax, ay, period, ph, width, amp in self.glows:
            x = cx + ax * math.sin(2 * math.pi * t / period + ph)
            y = cy + ay * math.cos(2 * math.pi * t / (period * 1.3) + ph)
            g = np.exp(-(((self.X - x) ** 2) + ((self.Y - y) * self.H / self.W) ** 2) / (2 * width * width)) * (amp * gain)
            low += g[..., None] * np.array(col, np.float32)
        for ang, fall, a0, swing, period, ph in self.rays:
            a = a0 + swing * math.sin(2 * math.pi * t / period + ph)
            beam = np.exp(-((ang - a) ** 2) / (2 * (0.075 * (1 + 0.5 * boost)) ** 2)) * fall
            low += beam[..., None] * (self.ray_col * (1.0 + 2.2 * boost))
        np.clip(low, 0, 255, out=low)
        up = cv2.resize(low.astype(np.uint8), (self.W, self.H), interpolation=cv2.INTER_CUBIC)
        frame[:] = cv2.add(up, self.grain)
        span = self.H + 80 * self.k
        for sp in self.sparks:
            y = (sp["y"] - sp["v"] * t) % span - 40 * self.k
            x = sp["x"] + math.sin(t * sp["f"] + sp["ph"]) * sp["sway"]
            op = sp["op"] * (0.55 + 0.45 * math.sin(t * sp["f"] * 2.1 + sp["ph"]))
            M.blit(frame, self.spark_sprites[sp["key"]], x, y, opacity=max(0.0, op))


class StageLayer(Layer):
    """Videoning bir qismini (crop) yumaloq burchakli kartochkaga olib, orqasiga yangi harakatli fon chizadi.

    Tayyor Reels ichidagi xira fonni almashtirish yoki gorizontal videoni chiroyli ramkaga olish uchun.
    punch: zarba paytida kartochka ichidagi tasvir biroz yaqinlashadi; shake: kartochka silkinadi.
    """
    z = 1

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        W, H, k = ctx.W, ctx.H, ctx.k
        crop = el.get("crop", [0, 0, 1, 1])
        if (not isinstance(crop, list) or len(crop) != 4 or not all(isinstance(v, (int, float)) for v in crop)
                or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1)):
            raise C.MontajError("stage.crop: [x0, y0, x1, y1] bo'lishi kerak, 0..1 oralig'ida (x0 < x1, y0 < y1).")
        self.sx0, self.sy0 = int(round(crop[0] * W)), int(round(crop[1] * H))
        self.sx1, self.sy1 = int(round(crop[2] * W)), int(round(crop[3] * H))
        sw, sh = self.sx1 - self.sx0, self.sy1 - self.sy0
        if sw < 16 or sh < 16:
            raise C.MontajError("stage.crop juda kichik.")
        self.cw = max(16, int(float(el.get("width", 0.92)) * W) // 2 * 2)
        self.ch = max(16, int(round(self.cw * sh / sw)) // 2 * 2)
        self.cx, self.cy = float(el.get("x", 0.5)) * W, float(el.get("y", 0.47)) * H
        if self.ch > H or self.cw > W:
            raise C.MontajError("stage: kartochka kadrga sig'maydi (width ni kichraytiring).")
        self.radius = max(0, min(int(float(el.get("radius", 40)) * k), self.cw // 2, self.ch // 2))
        border = el.get("border", {}) or {}
        accent = M.rgb(el.get("accent", ctx.caption_cfg()["accent"]))
        bw = max(0, int(float(border.get("width", 5)) * k))
        bcol = accent if str(border.get("color", "accent")) == "accent" else M.rgb(border["color"])
        self.shadow = M.rounded_rect_sprite(self.cw, self.ch, self.radius, (0, 0, 0, 255),
                                            shadow={"blur": 30 * k, "dy": 14 * k, "opacity": 0.6})
        self.ring = M.rounded_rect_sprite(self.cw, self.ch, self.radius, (0, 0, 0, 0), border=bcol + (255,),
                                          border_width=bw) if bw else None
        if self.radius:
            r = self.radius
            m = np.zeros((r * 4, r * 4), np.float32)
            cv2.circle(m, (r * 4, r * 4), r * 4, 1.0, -1, lineType=cv2.LINE_AA)       # chap-yuqori burchak
            self.corner = cv2.resize(m, (r, r), interpolation=cv2.INTER_AREA)[..., None]
        self.backdrop = Backdrop(ctx, dict(el.get("background", {}) or {}, accent=el.get("accent", ctx.caption_cfg()["accent"])))
        self.float_px = float(el.get("float", 6)) * k
        self.punch = self._events(el.get("punch"), "punch", {"scale": 0.045, "dur": 0.55})
        self.shake = self._events(el.get("shake"), "shake", {"amp": 9.0, "dur": 0.5})
        self.flash = self._events(el.get("flash"), "flash", {"amount": 1.0, "dur": 0.9})
        prog = el.get("progress")
        self.progress = None
        if prog:
            prog = prog if isinstance(prog, dict) else {}
            self.progress = {"h": max(2, int(float(prog.get("height", 7)) * k)),
                             "color": np.array(M.rgb(prog["color"]) if prog.get("color") else accent, np.float32)}
        self.footer = None
        ft = el.get("footer")
        if ft:
            fh = max(8, int(float(ft.get("height", 0.066)) * self.ch))
            font = ctx.fonts.get(ctx.caption_cfg()["font"], fh * 0.5, 700)
            text = M.word_sprite(fix_apostrophes(str(ft.get("text", ""))), font, str(ft.get("color", "#%02X%02X%02X" % accent)),
                                 0.0, None)
            self.footer = {"h": fh, "from": float(ft.get("from", self.start)), "text": text,
                           "fill": np.array(M.rgb(ft.get("fill", "#0C0C12")), np.float32), "line": np.array(bcol, np.float32)}
        half_w, half_h = self.cw / 2, self.ch / 2
        ctx.check_safe("Kartochka (stage)", max(ctx.safe["left"] * W, self.cx - half_w), self.cy - half_h,
                       min((1 - ctx.safe["right"]) * W, self.cx + half_w), self.cy + half_h)

    @staticmethod
    def _events(items, name: str, defaults: dict) -> list:
        out = []
        for it in items or []:
            if not isinstance(it, dict) or "at" not in it:
                raise C.MontajError(f"stage.{name}: har biri {{\"at\": soniya}} ko'rinishida bo'lishi kerak.")
            ev = dict(defaults)
            ev.update({key: float(val) for key, val in it.items()})
            out.append(ev)
        return out

    def draw(self, frame, t: float) -> None:
        k = self.ctx.k
        # zarba: tez yaqinlashib, sekin qaytadi
        zoom = 1.0
        for ev in self.punch:
            p = (t - ev["at"]) / ev["dur"]
            if 0 <= p < 1:
                zoom += ev["scale"] * (M.ease_out(p / 0.18) if p < 0.18 else 1 - M.ease_in_out((p - 0.18) / 0.82))
        sx0, sy0, sx1, sy1 = self.sx0, self.sy0, self.sx1, self.sy1
        if zoom > 1.001:
            sw, sh = (sx1 - sx0) / zoom, (sy1 - sy0) / zoom
            mx, my = (sx0 + sx1) / 2, (sy0 + sy1) / 2
            sx0, sx1, sy0, sy1 = int(mx - sw / 2), int(mx + sw / 2), int(my - sh / 2), int(my + sh / 2)
        card = cv2.resize(frame[sy0:sy1, sx0:sx1], (self.cw, self.ch), interpolation=cv2.INTER_LINEAR)
        boost = 0.0
        for ev in self.flash:
            p = (t - ev["at"]) / ev["dur"]
            if 0 <= p < 1:
                boost = max(boost, ev["amount"] * (M.ease_out(p / 0.12) if p < 0.12 else (1 - (p - 0.12) / 0.88) ** 2))
        self.backdrop.draw(frame, t, min(1.5, boost))
        ox = 0.0
        oy = math.sin((t - self.start) * 2 * math.pi / 6.5) * self.float_px
        for ev in self.shake:
            p = (t - ev["at"]) / ev["dur"]
            if 0 <= p < 1:
                amp = ev["amp"] * k * (1 - p) ** 2
                ox += amp * math.sin(p * ev["dur"] * 2 * math.pi * 13)
                oy += amp * math.cos(p * ev["dur"] * 2 * math.pi * 17)
        intro = M.clamp01((t - self.start) / 0.45)
        oy += (1 - M.ease_out(intro)) * 60 * k
        H, W = frame.shape[:2]
        x0 = int(round(min(max(0, self.cx - self.cw / 2 + ox), W - self.cw)))
        y0 = int(round(min(max(0, self.cy - self.ch / 2 + oy), H - self.ch)))
        if self.footer and t >= self.footer["from"]:
            f = self.footer
            op = M.ease_out((t - f["from"]) / 0.4)
            band = card[self.ch - f["h"]:]
            band[:] = (band.astype(np.float32) * (1 - 0.94 * op) + f["fill"] * (0.94 * op)).astype(np.uint8)
            line = max(1, int(2 * k))
            band[:line] = (band[:line].astype(np.float32) * (1 - op) + f["line"] * op).astype(np.uint8)
            spr, tw = f["text"]
            M.blit(card, spr, (self.cw - tw) / 2, self.ch - f["h"] * 0.30, opacity=op)
        if self.progress:
            # video qayergacha kelgani: kartochkaning eng pastki chetida ingichka chiziq
            ph = self.progress["h"]
            done_w = int(self.cw * M.clamp01((t - self.start) / max(0.01, self.end - self.start)))
            strip = card[self.ch - ph:]
            strip[:] = (strip.astype(np.float32) * 0.35).astype(np.uint8)
            strip[:, :done_w] = self.progress["color"].astype(np.uint8)
        M.blit(frame, self.shadow, x0, y0, opacity=intro)
        region = frame[y0:y0 + self.ch, x0:x0 + self.cw]
        r = self.radius
        saved = None
        if r:
            saved = [region[:r, :r].copy(), region[:r, -r:].copy(), region[-r:, :r].copy(), region[-r:, -r:].copy()]
        if intro < 0.999:
            region[:] = (region.astype(np.float32) * (1 - intro) + card.astype(np.float32) * intro).astype(np.uint8)
        else:
            region[:] = card
        if r:
            a = self.corner
            for patch, sl, mask in ((saved[0], (slice(0, r), slice(0, r)), a),
                                    (saved[1], (slice(0, r), slice(-r, None)), a[:, ::-1]),
                                    (saved[2], (slice(-r, None), slice(0, r)), a[::-1]),
                                    (saved[3], (slice(-r, None), slice(-r, None)), a[::-1, ::-1])):
                cur = region[sl].astype(np.float32)
                region[sl] = (cur * mask + patch.astype(np.float32) * (1 - mask)).astype(np.uint8)
        if self.ring is not None:
            M.blit(frame, self.ring, x0, y0, opacity=intro)


class BurstLayer(Layer):
    """Emoji otilishi: bir nechta emoji pastdan ko'tarilib, so'nib ketadi (kulgu, olqish paytida)."""
    z = 38

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        W, H, k = ctx.W, ctx.H, ctx.k
        raw = el.get("emoji", "\U0001F602")
        names = []
        for item in (raw if isinstance(raw, list) else [raw]):
            names += [v for kind, v in M.Emoji.split(str(item)) if kind == "emoji"]
        if not names:
            raise C.MontajError(f"burst elementida tanilmagan emoji: {raw!r}")
        count = int(el.get("count", 9))
        if not 1 <= count <= 60:
            raise C.MontajError("burst.count 1 dan 60 gacha bo'lishi kerak.")
        base = float(el.get("size", 0.085)) * W
        xr = el.get("x", [0.12, 0.88])
        x_lo, x_hi = (xr if isinstance(xr, list) else [float(xr) - 0.2, float(xr) + 0.2])
        self.y0 = float(el.get("y_from", 0.74)) * H
        self.rise = float(el.get("rise", 0.38)) * H
        self.dur = max(0.3, self.end - self.start - 0.35)
        r = random.Random(int(self.start * 1000) + count)
        self.parts = []
        for i in range(count):
            size = max(16, int(base * r.uniform(0.7, 1.25)))
            spr = M.pil_sprite(M.Emoji.image(r.choice(names), size), shadow={"blur": 8 * k, "dy": 4 * k, "opacity": 0.3})
            self.parts.append({"spr": spr, "x": r.uniform(float(x_lo), float(x_hi)) * W, "delay": r.uniform(0, 0.35),
                               "sway": r.uniform(8, 38) * k, "ph": r.uniform(0, 6.28), "rise": r.uniform(0.6, 1.0)})

    def draw(self, frame, t: float) -> None:
        for p in self.parts:
            q = (t - self.start - p["delay"]) / self.dur
            if not 0 <= q <= 1:
                continue
            y = self.y0 - self.rise * p["rise"] * M.ease_out(q)
            x = p["x"] + math.sin(q * 5 + p["ph"]) * p["sway"]
            M.blit(frame, p["spr"], x, y, opacity=M.clamp01(q * 7) * M.clamp01((1 - q) / 0.3),
                   scale=0.5 + 0.5 * M.spring(q * 3.2), anchor=(0, 0))


class ConfettiLayer(Layer):
    """Konfetti: ikki pastki burchakdan (yoki tepadan) rangli qog'ozlar otiladi."""
    z = 39

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        W, H, k = ctx.W, ctx.H, ctx.k
        self.W, self.H, self.k = W, H, k
        origin = str(el.get("origin", "sides"))
        if origin not in ("sides", "top"):
            raise C.MontajError(f"confetti.origin noto'g'ri: {origin!r}. Mumkin: sides, top")
        count = int(el.get("count", 70))
        if not 1 <= count <= 300:
            raise C.MontajError("confetti.count 1 dan 300 gacha bo'lishi kerak.")
        accent = ctx.caption_cfg()["accent"]
        colors = [M.rgb(c) for c in (el.get("colors") or [accent, "#FFFFFF", "#FF5A5F", "#3DDC97", "#5B8CFF"])]
        y_from = float(el.get("y_from", 0.72)) * H
        r = random.Random(int(self.start * 1000) + count * 7)
        self.g = 1500.0 * k
        self.parts = []
        for i in range(count):
            if origin == "sides":
                left = i % 2 == 0
                ang = math.radians(r.uniform(52, 82))
                speed = r.uniform(900, 1700) * k
                vx = math.cos(ang) * speed * (1 if left else -1)
                vy = -math.sin(ang) * speed
                x, y = (0.03 * W if left else 0.97 * W), y_from
            else:
                x, y = r.uniform(0, 1) * W, -20 * k
                vx, vy = r.uniform(-120, 120) * k, r.uniform(150, 520) * k
            self.parts.append({"x": x, "y": y, "vx": vx, "vy": vy, "col": r.choice(colors), "w": r.uniform(9, 18) * k,
                               "h": r.uniform(14, 28) * k, "rot": r.uniform(0, 6.28), "spin": r.uniform(-9, 9),
                               "flip": r.uniform(3, 9), "ph": r.uniform(0, 6.28), "delay": r.uniform(0, 0.12)})

    def draw(self, frame, t: float) -> None:
        life = self.end - self.start
        for p in self.parts:
            tau = t - self.start - p["delay"]
            if tau < 0:
                continue
            drag = 1.0 / (1.0 + 0.9 * tau)                     # havo qarshiligi: tezlik sekin so'nadi
            x = p["x"] + p["vx"] * tau * drag
            y = p["y"] + p["vy"] * tau * drag + 0.5 * self.g * tau * tau * 0.55
            if y > self.H + 40 or x < -40 or x > self.W + 40:
                continue
            fade = M.clamp01((life - tau) / 0.35)
            w = p["w"] * abs(math.cos(tau * p["flip"] + p["ph"])) * fade + 1.0
            h = p["h"] * fade
            a = p["rot"] + p["spin"] * tau
            ca, sa = math.cos(a), math.sin(a)
            pts = np.array([[x + (dx * ca - dy * sa), y + (dx * sa + dy * ca)]
                            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))], np.int32)
            cv2.fillConvexPoly(frame, pts, p["col"], lineType=cv2.LINE_AA)


class FollowLayer(Layer):
    """Obuna kartochkasi (namuna 9, 12, 14): doira ichida logotip, ostida @manzil va "Obuna" tugmasi.

    Kursor uchib kelib tugmani bosadi, tugma "bosildi" holatiga o'tadi (kulrang, boshqa yozuv).
    logo: fayl (bo'lmasa doira brend rangida, ichida name yozuvi). Vaqt: start..end, bosish: tap (soniya, startdan).
    """
    z = 60

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.ctx = ctx
        cap = ctx.caption_cfg({"preset": "clean"})
        k = self.k = ctx.k * float(el.get("scale", 1.0))
        color = M.rgb(el.get("color") or cap["accent"])
        d = self.d = max(40, int(float(el.get("size", 0.30)) * ctx.W))
        self.cx, self.cy = float(el.get("x", 0.5)) * ctx.W, float(el.get("y", 0.66)) * ctx.H
        ring = max(3, int(d * 0.035))
        shadow = {"blur": 22 * k, "dy": 8 * k, "opacity": 0.35}
        s = 3
        big = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(big)
        draw.ellipse([0, 0, d * s - 1, d * s - 1], fill=(255, 255, 255, 255))
        draw.ellipse([ring * s, ring * s, (d - ring) * s - 1, (d - ring) * s - 1], fill=color + (255,))
        disc = big.resize((d, d), Image.LANCZOS)
        inner = d - ring * 2
        if el.get("logo"):
            try:
                logo = Image.open(ctx.asset(el["logo"], "Logotip")).convert("RGBA")
            except C.MontajError:
                raise
            except Exception as exc:
                raise C.MontajError(f"follow.logo ochilmadi: {exc}") from exc
            side = min(logo.size)
            logo = logo.crop(((logo.width - side) // 2, (logo.height - side) // 2,
                              (logo.width + side) // 2, (logo.height + side) // 2)).resize((inner, inner), Image.LANCZOS)
            mask = Image.new("L", (inner * s, inner * s), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, inner * s - 1, inner * s - 1], fill=255)
            mask = mask.resize((inner, inner), Image.LANCZOS)
            # logotip shaffof bo'lsa doira rangi ko'rinadi, to'liq rasm bo'lsa doirani to'ldiradi
            patch = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
            patch.paste(logo, (0, 0), Image.composite(logo.getchannel("A"), Image.new("L", (inner, inner), 0), mask))
            disc.alpha_composite(patch, (ring, ring))
        elif el.get("name"):
            bright = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255
            size = d * 0.15
            font = ctx.fonts.get(cap["font"], size, 600)
            text = fix_apostrophes(str(el["name"]))
            while M.measure(font, text, 0) > inner * 0.8 and size > 10:
                size *= 0.92
                font = ctx.fonts.get(cap["font"], size, 600)
            spr, tw = M.word_sprite(text, font, "#111111" if bright > 0.6 else "#FFFFFF", cap["tracking"] * size * 0.5)
            name_img = Image.fromarray(self._unpremultiply(spr.pix), "RGBA")
            disc.alpha_composite(name_img, (int((d - tw) / 2 + spr.ox), int(d * 0.56 + spr.oy)))
        self.disc = M.pil_sprite(disc, shadow=shadow)                       # nuqtasi markazda
        handle = fix_apostrophes(str(el.get("handle", "")))
        if not handle:
            raise C.MontajError("follow uchun 'handle' kerak (masalan \"@sahifa_nomi\").")
        fsize = d * 0.145
        font = ctx.fonts.get(cap["font"], fsize, 600)
        txt, tw = M.word_sprite(handle, font, "#111111", -0.03 * fsize)
        ph, pw = int(fsize * 1.55), int(tw + fsize * 1.3)
        self.pill = M.rounded_rect_sprite(pw, ph, ph / 2, (255, 255, 255, 255), shadow={"blur": 12 * k, "dy": 4 * k, "opacity": 0.3})
        self.pill_text, self.pill_size = (txt, tw), (pw, ph, fsize)
        bsize = d * 0.10
        bfont = ctx.fonts.get(cap["font"], bsize, 600)
        self.buttons = []
        for label, fill, ink in ((str(el.get("button", "Obuna")), color, None), (str(el.get("done", "Obuna bo'ldingiz")), (232, 232, 236), "#222222")):
            bright = (0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]) / 255
            spr, bw = M.word_sprite(fix_apostrophes(label), bfont, ink or ("#111111" if bright > 0.6 else "#FFFFFF"), -0.02 * bsize)
            w, h = int(bw + bsize * 2.0), int(bsize * 1.7)
            self.buttons.append((M.rounded_rect_sprite(w, h, h / 2, fill + (255,), shadow={"blur": 8 * k, "dy": 3 * k, "opacity": 0.25}),
                                 spr, bw, w, h, bsize))
        self.tap = self.start + float(el.get("tap", 1.3))
        r = max(6, int(d * 0.06))
        cur = Image.new("RGBA", (r * 2 * s, r * 2 * s), (0, 0, 0, 0))
        ImageDraw.Draw(cur).ellipse([0, 0, r * 2 * s - 1, r * 2 * s - 1], fill=(255, 255, 255, 170), outline=(255, 255, 255, 255), width=s * 2)
        self.cursor = M.pil_sprite(cur.resize((r * 2, r * 2), Image.LANCZOS), shadow={"blur": 6 * k, "dy": 2 * k, "opacity": 0.3})
        self.pill_y = d * 0.47
        self.btn_y = self.pill_y + ph * 0.5 + self.buttons[0][4] * 0.62
        ctx.check_safe("Obuna kartochkasi (follow)", self.cx - d / 2, self.cy - d / 2, self.cx + d / 2,
                       self.cy + self.btn_y + self.buttons[0][4] / 2)

    @staticmethod
    def _unpremultiply(pix: np.ndarray) -> np.ndarray:
        out = pix.astype(np.float32)
        a = np.maximum(out[..., 3:4], 1.0)
        out[..., :3] = np.clip(out[..., :3] * 255.0 / a, 0, 255)
        return out.astype(np.uint8)

    def draw(self, frame, t: float) -> None:
        op, scale = appear(t, self.start, self.end, 0.5, 0.18)
        if op <= 0.003:
            return
        cx, cy = self.cx, self.cy

        def at(spr, dx: float, dy: float, extra: float = 1.0, opacity: float = 1.0) -> None:
            # (dx, dy) - kartochka markaziga nisbatan; hammasi shu markaz atrofida kattalashadi
            M.blit(frame, spr, cx + dx * scale, cy + dy * scale, opacity=op * opacity, scale=scale * extra, anchor=(0, 0))

        at(self.disc, 0, 0)
        pw, ph, fsize = self.pill_size
        pp = M.clamp01((t - self.start - 0.12) / 0.3)
        if pp > 0:
            grow = 0.6 + 0.4 * M.spring(pp)
            M.blit(frame, self.pill, cx - pw / 2 * scale, cy + (self.pill_y - ph / 2) * scale, opacity=op * M.clamp01(pp * 3),
                   scale=scale * grow, anchor=(pw / 2, ph / 2))
            txt, tw = self.pill_text
            M.blit(frame, txt, cx - tw / 2 * scale, cy + (self.pill_y + fsize * 0.36) * scale,
                   opacity=op * M.clamp01((pp - 0.3) * 3), scale=scale, anchor=(0, 0))
        bp = M.clamp01((t - self.start - 0.3) / 0.3)
        if bp > 0:
            pressed = t >= self.tap
            box, spr, bw, w, h, bsize = self.buttons[1 if pressed else 0]
            dip = 1.0
            q = (t - self.tap) / 0.22
            if -0.25 <= q < 1:                      # bosilganda tugma bir zum kichrayadi
                dip = 1.0 - 0.10 * math.sin(M.clamp01(q + 0.25) / 1.25 * math.pi)
            grow = (0.6 + 0.4 * M.spring(bp)) * dip
            M.blit(frame, box, cx - w / 2 * scale, cy + (self.btn_y - h / 2) * scale, opacity=op * M.clamp01(bp * 3),
                   scale=scale * grow, anchor=(w / 2, h / 2))
            M.blit(frame, spr, cx - bw / 2 * scale, cy + (self.btn_y + bsize * 0.36) * scale,
                   opacity=op * M.clamp01((bp - 0.3) * 3), scale=scale * dip, anchor=(bw / 2, -bsize * 0.36))
        # kursor: o'ng-pastdan uchib kelib tugmani bosadi va so'nadi
        c0, c1 = self.tap - 0.55, self.tap + 0.35
        if c0 <= t < c1:
            e = M.ease_in_out((t - c0) / 0.5)
            x = cx + (self.d * 0.75 * (1 - e) + self.buttons[0][3] * 0.18) * scale
            y = cy + (self.btn_y + self.d * 0.55 * (1 - e) + self.buttons[0][4] * 0.1) * scale
            M.blit(frame, self.cursor, x, y, opacity=op * M.clamp01((t - c0) / 0.12) * M.clamp01((c1 - t) / 0.2),
                   scale=1.0 - 0.2 * M.clamp01(1 - abs(t - self.tap) / 0.12), anchor=(0, 0))


class SceneLayer(Layer):
    """To'liq ekranli chizilgan fon (namuna 4, 8, 9, 11): ustiga matn, rasm, ovozli xabar qo'yiladi.

    background: Backdrop sozlamalari (color1..color4, rays, sparks, pattern: dots | grid | none, glow).
    Video shu vaqtda ko'rinmaydi (ovoz davom etadi). fade: kirish/chiqish (soniya).
    """
    z = 2

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        bg = dict(el.get("background", {}) or {})
        bg.setdefault("accent", el.get("accent", ctx.caption_cfg()["accent"]))
        self.backdrop = Backdrop(ctx, bg)
        self.fade = max(0.0, float(el.get("fade", 0.22)))
        self.buf = None

    def draw(self, frame, t: float) -> None:
        op = 1.0
        if self.fade > 0:
            op = M.clamp01((t - self.start) / self.fade) * M.clamp01((self.end - t) / self.fade)
        if op >= 0.997:
            self.backdrop.draw(frame, t - self.start)
            return
        if op <= 0.003:
            return
        if self.buf is None:
            self.buf = np.empty_like(frame)
        self.backdrop.draw(self.buf, t - self.start)
        cv2.addWeighted(self.buf, op, frame, 1 - op, 0, dst=frame)


class GradeLayer(Layer):
    """Vaqtincha rang ishlovi: mode "bw" - oq-qora (namuna 13 boshi, 14 dagi "to'xtab qolgan" kadr)."""
    z = 0

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.mode = str(el.get("mode", "bw"))
        if self.mode not in ("bw", "dim"):
            raise C.MontajError(f"grade.mode noto'g'ri: {self.mode!r}. Mumkin: bw, dim")
        self.amount = M.clamp01(float(el.get("amount", 1.0 if self.mode == "bw" else 0.45)))
        self.fade = max(0.0, float(el.get("fade", 0.25)))

    def draw(self, frame, t: float) -> None:
        op = self.amount
        if self.fade > 0:
            op *= M.clamp01((t - self.start) / self.fade) * M.clamp01((self.end - t) / self.fade)
        if op <= 0.003:
            return
        if self.mode == "bw":
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            cv2.addWeighted(cv2.merge([gray, gray, gray]), op, frame, 1 - op, 0, dst=frame)
        else:
            frame[:] = (frame.astype(np.float32) * (1 - op)).astype(np.uint8)


class FlashLayer(Layer):
    """Qisqa chaqnash (sahna almashganda): kadr bir zum oqarib, qaytadi."""
    z = 90

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.color = np.array(M.rgb(el.get("color", "#FFFFFF")), np.float32)
        self.amount = M.clamp01(float(el.get("amount", 0.9)))

    def draw(self, frame, t: float) -> None:
        p = (t - self.start) / max(0.001, self.end - self.start)
        if not 0 <= p < 1:
            return
        op = self.amount * (M.ease_out(p / 0.3) if p < 0.3 else (1 - (p - 0.3) / 0.7) ** 2)
        if op > 0.003:
            frame[:] = (frame.astype(np.float32) * (1 - op) + self.color * op).astype(np.uint8)


class ProgressLayer(Layer):
    """Video qayergacha kelganini ko'rsatadigan ingichka chiziq (tepada yoki pastda)."""
    z = 80

    def __init__(self, ctx: Ctx, cfg: dict, total: float):
        super().__init__(0, total)
        self.ctx = ctx
        self.h = max(2, int(float(cfg.get("height", 8)) * ctx.k))
        self.color = np.array(M.rgb(cfg.get("color") or ctx.caption_cfg()["accent"]), np.uint8)
        self.top = str(cfg.get("position", "top")) != "bottom"

    def draw(self, frame, t: float) -> None:
        w = int(self.ctx.W * M.clamp01(t / max(0.01, self.end)))
        y = 0 if self.top else self.ctx.H - self.h
        frame[y:y + self.h, :w] = self.color


class HandnoteLayer(TextLayer):
    """Caveat qo'lyozma izoh; animatsiya va joylashuv TextLayer bilan bir xil."""

    def __init__(self, ctx: Ctx, el: dict):
        if not str(el.get("text", "")).strip():
            raise C.MontajError("handnote.text kerak.")
        config = dict(el)
        config.setdefault("font", "Caveat")
        config.setdefault("preset", "clean")
        config.setdefault("tracking", 0.01)
        config.setdefault("size", 1.15)
        config.setdefault("stagger", 0.08)
        super().__init__(ctx, config)


class ArrowLayer(Layer):
    """Chizilib chiqadigan egri strelka: points [start, control, end] yoki siniq yo'l."""
    z = 44

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        values = el.get("points")
        if not isinstance(values, list) or not 2 <= len(values) <= 32:
            raise C.MontajError("arrow.points: 2..32 ta [x,y], 0..1.")
        points = np.asarray(values, dtype=np.float64)
        if points.shape != (len(values), 2) or not np.isfinite(points).all() or (points < 0).any() or (points > 1).any():
            raise C.MontajError("arrow.points koordinatalari 0..1 bo'lishi kerak.")
        points *= [ctx.W, ctx.H]
        if len(points) == 3:
            t = np.linspace(0, 1, 65)[:, None]
            points = (1-t)**2 * points[0] + 2*(1-t)*t*points[1] + t**2 * points[2]
        lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
        if lengths.sum() < 2:
            raise C.MontajError("arrow yo'li juda qisqa.")
        bounds = np.r_[0, np.cumsum(lengths)]
        samples = np.linspace(0, bounds[-1], 65)
        self.points = np.stack([np.interp(samples, bounds, points[:, i]) for i in range(2)], axis=1)
        self.stroke = max(1, int(float(el.get("stroke", 6)) * ctx.k))
        self.head = max(4, float(el.get("head", 28)) * ctx.k)
        self.seconds = float(el.get("draw_sec", 0.6))
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise C.MontajError("arrow.draw_sec musbat son bo'lishi kerak.")
        self.color = M.rgb(el.get("color", ctx.caption_cfg()["color"])) + (255,)
        pad = self.head + self.stroke + 3
        self.left, self.top = np.floor(self.points.min(axis=0)-pad).astype(int)
        right, bottom = np.ceil(self.points.max(axis=0)+pad).astype(int)
        self.width, self.height = int(right-self.left), int(bottom-self.top)
        self.local = self.points - [self.left, self.top]
        self.cache = {}
        ctx.check_safe("Strelka", self.left, self.top, right, bottom)

    def draw(self, frame, t: float) -> None:
        index = min(64, max(1, int(M.ease_out((t-self.start)/self.seconds)*64)))
        if index not in self.cache:
            image = Image.new("RGBA", (self.width, self.height))
            draw = ImageDraw.Draw(image)
            coords = [tuple(point) for point in self.local[:index+1]]
            draw.line(coords, fill=self.color, width=self.stroke, joint="curve")
            if index == 64:
                tip = self.local[-1]
                direction = self.local[-2] - tip
                direction /= max(0.01, np.linalg.norm(direction))
                normal = np.array([-direction[1], direction[0]])
                for side in (-1, 1):
                    wing = tip + direction*self.head + normal*self.head*.48*side
                    draw.line([tuple(wing), tuple(tip)], fill=self.color, width=self.stroke)
            self.cache[index] = M.from_pil(image, 0, 0)
        M.blit(frame, self.cache[index], self.left, self.top, opacity=clamp_exit(t, self.end, 0.15))


class PhoneLayer(Layer):
    """Telefon yoki profil kartochkasi: faqat berilgan rasm/ism/manzil, soxta statistika yo'q."""
    z = 38

    def __init__(self, ctx: Ctx, el: dict):
        super().__init__(el["start"], el["end"])
        self.cx, self.cy = float(el.get("x", 0.5))*ctx.W, float(el.get("y", 0.32))*ctx.H
        width = max(40, int(float(el.get("width", 0.42))*ctx.W))
        phone = el.get("type") == "phone"
        height = int(width*(1.92 if phone else 0.85))
        radius = max(4, int(width*.09))
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, width-1, height-1), radius=radius, fill="#111116" if phone else "#202028", outline="#ECECF0", width=max(1, int(3*ctx.k)))
        pad = max(4, int(width*.06))
        top = int(width*.12) if phone else pad
        if el.get("image"):
            with Image.open(ctx.asset(el["image"], "Telefon rasmi")) as source:
                picture = source.convert("RGBA")
            picture.thumbnail((width-pad*2, height-top-pad))
            image.alpha_composite(picture, ((width-picture.width)//2, top+(height-top-pad-picture.height)//2))
        else:
            name = fix_apostrophes(str(el.get("name", "")).strip())
            handle = fix_apostrophes(str(el.get("handle", "")).strip())
            if not name or not handle:
                raise C.MontajError("phone/profile uchun image yoki name+handle kerak.")
            cfg = ctx.caption_cfg()
            avatar_size = int(width*.24)
            avatar_y = top+pad
            draw.ellipse((pad, avatar_y, pad+avatar_size, avatar_y+avatar_size), fill=cfg["accent"])
            if el.get("avatar"):
                with Image.open(ctx.asset(el["avatar"], "Profil rasmi")) as source:
                    avatar = source.convert("RGBA")
                side = min(avatar.size)
                avatar = avatar.crop(((avatar.width-side)//2, (avatar.height-side)//2,
                                      (avatar.width+side)//2, (avatar.height+side)//2)).resize((avatar_size, avatar_size), Image.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size))
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size-1, avatar_size-1), fill=255)
                # Keep source transparency inside the circular mask.
                avatar.putalpha(Image.fromarray(np.minimum(np.asarray(mask), np.asarray(avatar.getchannel("A")))))
                image.alpha_composite(avatar, (pad, avatar_y))
            y = avatar_y+avatar_size+pad
            for label, weight, color in ((name, 700, "#FFFFFF"), (handle, 500, "#C8C8D0")):
                size = width*.075
                font = ctx.fonts.get(cfg["font"], size, weight)
                while font.getlength(label) > width-pad*2 and size > 4:
                    size *= .9
                    font = ctx.fonts.get(cfg["font"], size, weight)
                draw.text((pad, y), label, font=font, fill=color)
                y += size*1.45
            bio = fix_apostrophes(str(el.get("bio", "")))
            if bio:
                font = ctx.fonts.get(cfg["font"], width*.06, 400)
                lines = []
                for word in bio.split():
                    if lines and font.getlength(lines[-1]+" "+word) <= width-pad*2:
                        lines[-1] += " "+word
                    else:
                        lines.append(word)
                if y+len(lines)*width*.08 > height-pad or any(font.getlength(line) > width-pad*2 for line in lines):
                    raise C.MontajError("Profil bio juda uzun; qisqartiring yoki phone ishlating.")
                for line in lines:
                    draw.text((pad, y), line, font=font, fill="#E0E0E8")
                    y += width*.08
        if phone:
            draw.rounded_rectangle((width*.38, width*.035, width*.62, width*.07), radius=max(1, int(width*.02)), fill="#606068")
        self.sprite = M.pil_sprite(image, shadow={"blur": 16*ctx.k, "dy": 5*ctx.k, "opacity": .35})
        ctx.check_safe("Telefon/profil", self.cx-width/2, self.cy-height/2, self.cx+width/2, self.cy+height/2)

    def draw(self, frame, t: float) -> None:
        opacity, scale = appear(t, self.start, self.end)
        M.blit(frame, self.sprite, self.cx, self.cy, opacity=opacity, scale=scale, anchor=(0, 0))


ELEMENT_TYPES = {"text": TextLayer, "title": TextLayer, "image": ImageLayer, "broll": BrollLayer,
                 "list": ListLayer, "choice": ChoiceLayer, "stat": StatLayer, "voice": VoiceLayer,
                 "callout": CalloutLayer, "lower_third": LowerThirdLayer, "emoji": EmojiLayer,
                 "icon": IconLayer, "stage": StageLayer, "burst": BurstLayer, "confetti": ConfettiLayer,
                 "follow": FollowLayer, "scene": SceneLayer, "grade": GradeLayer, "flash": FlashLayer,
                 "handnote": HandnoteLayer, "arrow": ArrowLayer, "phone": PhoneLayer, "profile": PhoneLayer}
# "at" bilan beriladigan qisqa hodisalar: boshlanishi "at", uzunligi "duration"
TIMED_TYPES = {"burst": 2.0, "confetti": 2.6, "flash": 0.3}
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
            if kind in TIMED_TYPES and "at" in el:
                el["start"] = float(el["at"])
                el["end"] = el["start"] + float(el.get("duration", TIMED_TYPES[kind])) + (0.35 if kind == "burst" else 0)
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
