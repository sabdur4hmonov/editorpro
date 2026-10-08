"""Motion-grafika yadrosi: shriftlar, matn chizish, sprite, kadrga joylash, animatsiya.

Bu faylni elements.py va compose.py ishlatadi. O'zi alohida ishga tushirilmaydi.
Hamma narsa Pillow (matn va shakllar) + OpenCV/NumPy (kadr bilan ishlash) ustiga qurilgan.
"""
from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path

import numpy as np

import common as C

try:
    import cv2
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError as exc:  # aniq xabar: nima yetishmayotgani
    raise C.MontajError(
        f"Motion-grafika uchun kutubxona yetishmaydi: {exc.name}. O'rnatish:\n"
        "  .venv\\Scripts\\python.exe -m pip install pillow opencv-python numpy"
    ) from None

FONT_EXTS = {".ttf", ".otf", ".ttc"}
WEIGHT_WORDS = {"thin": 100, "extralight": 200, "ultralight": 200, "light": 300, "regular": 400, "book": 400,
                "medium": 500, "semibold": 600, "demibold": 600, "bold": 700, "extrabold": 800,
                "ultrabold": 800, "black": 900, "heavy": 900}


# ---------------------------------------------------------------- animatsiya egri chiziqlari

def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(p: float) -> float:
    """Tez boshlanib, sekin to'xtaydi."""
    p = clamp01(p)
    return 1 - (1 - p) ** 3


def ease_in_out(p: float) -> float:
    p = clamp01(p)
    return p * p * (3 - 2 * p)


def ease_back(p: float, overshoot: float = 1.4) -> float:
    """Biroz oshib ketib qaytadi ("pop" effekti)."""
    p = clamp01(p) - 1
    return 1 + p * p * ((overshoot + 1) * p + overshoot)


def spring(p: float, omega: float = 12.0, zeta: float = 0.5) -> float:
    """Prujina kabi: tez chiqadi, biroz oshib ketadi va o'rniga tushadi (0 -> 1)."""
    p = clamp01(p)
    if p >= 1:
        return 1.0
    wd = omega * math.sqrt(max(1e-6, 1 - zeta * zeta))
    return 1 - math.exp(-zeta * omega * p) * (math.cos(wd * p) + (zeta * omega / wd) * math.sin(wd * p))


def breathe(t: float, amount: float = 0.006, period: float = 3.2) -> float:
    """Ekranda uzoq turgan element uchun juda sekin "nafas olish" masshtabi (1 atrofida)."""
    return 1.0 + amount * math.sin(t * 2 * math.pi / period)


def rgb(color: str) -> tuple:
    m = re.fullmatch(r"#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})", str(color).strip())
    if not m:
        raise C.MontajError(f"Rang noto'g'ri: {color!r}. To'g'ri ko'rinish: #RRGGBB (masalan #FFE600).")
    return tuple(int(g, 16) for g in m.groups())


# ---------------------------------------------------------------- shriftlar

class Fonts:
    """Shrift oilasi nomi bo'yicha fayl topadi. Avval loyiha papkalari, keyin tizim shriftlari."""

    def __init__(self, dirs: list):
        self.entries: list = []
        self.cache: dict = {}
        self.system_scanned = False
        self.warned: set = set()
        for d in dirs:
            self._scan(Path(d), recursive=False)

    def _scan(self, folder: Path, recursive: bool) -> None:
        if not folder.is_dir():
            return
        files = folder.rglob("*") if recursive else folder.iterdir()
        for path in sorted(files):
            if path.suffix.lower() not in FONT_EXTS or not path.is_file():
                continue
            try:
                font = ImageFont.truetype(str(path), 20)
                family, style_name = font.getname()
            except Exception:
                continue  # buzuq yoki tushunarsiz shrift fayli
            try:
                axes = font.get_variation_axes()
            except Exception:
                axes = None
            low = (style_name or "").lower().replace(" ", "").replace("-", "")
            weight = next((w for name, w in sorted(WEIGHT_WORDS.items(), key=lambda kv: -len(kv[0]))
                           if name in low), 400)
            self.entries.append({"path": str(path), "family": (family or path.stem).lower(),
                                 "italic": "italic" in low or "oblique" in low,
                                 "weight": weight, "axes": axes})

    def _scan_system(self) -> None:
        if self.system_scanned:
            return
        self.system_scanned = True
        if sys.platform == "win32":
            roots = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
                     Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"]
        elif sys.platform == "darwin":
            roots = [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
        else:
            roots = [Path("/usr/share/fonts"), Path.home() / ".fonts"]
        for root in roots:
            self._scan(root, recursive=True)

    def _pick(self, family: str, weight: int, italic: bool):
        found = [e for e in self.entries if e["family"] == family.lower()]
        if not found:
            return None
        found.sort(key=lambda e: (e["italic"] != italic, e["axes"] is None, abs(e["weight"] - weight)))
        return found[0]

    def get(self, family: str, size: float, weight: int = 400, italic: bool = False):
        size = max(4, int(round(size)))
        key = (family.lower(), size, int(weight), bool(italic))
        if key in self.cache:
            return self.cache[key]
        entry = self._pick(family, weight, italic)
        if entry is None:
            self._scan_system()
            entry = self._pick(family, weight, italic)
        if entry is None:
            if family.lower() not in self.warned:
                self.warned.add(family.lower())
                C.warn(f"\"{family}\" shrifti topilmadi (style/fonts/ yoki brend papkasiga .ttf qilib tashlang). "
                       "O'rniga Inter ishlatiladi.")
            entry = self._pick("inter", weight, italic) or (self.entries[0] if self.entries else None)
            if entry is None:
                raise C.MontajError("Hech qanday shrift topilmadi. style/fonts/ papkasida .ttf fayllar bo'lishi kerak.")
        font = ImageFont.truetype(entry["path"], size)
        glyph_key = ('uzbek',entry['path'])
        if glyph_key not in self.warned:
            self.warned.add(glyph_key)
            from glyph_audit import missing
            try:
                absent=missing(entry['path'])
                if absent: C.warn(f"Uzbek glyph missing: {family}: {absent}")
            except (OSError,ValueError,IndexError) as error:
                C.warn(f"Font cmap could not be verified: {family}: {error}")
        if entry["axes"]:
            values = []
            for axis in entry["axes"]:
                name = axis["name"].decode() if isinstance(axis["name"], bytes) else str(axis["name"])
                if name.lower().startswith("weight"):
                    values.append(min(max(weight, axis["minimum"]), axis["maximum"]))
                elif name.lower().startswith("optical"):
                    values.append(axis["maximum"])  # katta o'lchamdagi matn uchun
                else:
                    values.append(axis["default"])
            try:
                font.set_variation_by_axes(values)
            except Exception:
                pass
        self.cache[key] = font
        return font


# ---------------------------------------------------------------- sprite (shaffof rasm bo'lagi)

class Sprite:
    """Kadrga qo'yiladigan shaffof rasm. Ranglar alfa bilan oldindan ko'paytirilgan (premultiplied)."""

    __slots__ = ("pix", "ox", "oy", "_blur")

    def __init__(self, pix: np.ndarray, ox: float = 0, oy: float = 0):
        self.pix = pix          # (h, w, 4) uint8, premultiplied RGBA
        self.ox = ox            # nuqtaga nisbatan chap-yuqori burchak siljishi
        self.oy = oy
        self._blur: dict = {}

    @property
    def w(self) -> int:
        return self.pix.shape[1]

    @property
    def h(self) -> int:
        return self.pix.shape[0]

    def blurred(self, radius: float) -> "Sprite":
        """Xiralashtirilgan nusxa (keshlanadi). Matn "xiralikdan ochilishi" uchun."""
        level = int(round(radius))
        if level <= 0:
            return self
        if level not in self._blur:
            pad = level * 2
            pix = cv2.copyMakeBorder(self.pix, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
            pix = cv2.GaussianBlur(pix, (0, 0), level)
            self._blur[level] = Sprite(pix, self.ox - pad, self.oy - pad)
        return self._blur[level]


def from_pil(img, ox: float = 0, oy: float = 0) -> Sprite:
    """Pillow RGBA rasmidan sprite yasaydi."""
    arr = np.asarray(img.convert("RGBA")).astype(np.uint16)
    alpha = arr[..., 3:4]
    arr[..., :3] = (arr[..., :3] * alpha + 127) // 255
    return Sprite(arr.astype(np.uint8), ox, oy)


def blit(frame: np.ndarray, spr: Sprite, x: float, y: float, opacity: float = 1.0,
         scale: float = 1.0, blur: float = 0.0, anchor: tuple | None = None) -> None:
    """Spriteni kadrga joylaydi. (x, y) - sprite boshlang'ich nuqtasi (ox/oy shunga nisbatan).

    scale != 1 bo'lsa (x + anchor[0], y + anchor[1]) nuqta joyida qoladi, qolgani kattalashadi/kichrayadi.
    """
    if opacity <= 0.003:
        return
    if blur >= 0.5:
        spr = spr.blurred(blur)
    pix, left, top = spr.pix, x + spr.ox, y + spr.oy
    if abs(scale - 1.0) > 0.004:
        nw, nh = max(1, int(round(spr.w * scale))), max(1, int(round(spr.h * scale)))
        pix = cv2.resize(pix, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        ax, ay = anchor if anchor is not None else (0.0, 0.0)
        cx, cy = x + ax, y + ay                       # kadrda qimirlamaydigan nuqta
        left = cx + (spr.ox - ax) * scale
        top = cy + (spr.oy - ay) * scale
    left, top = int(round(left)), int(round(top))
    fh, fw = frame.shape[:2]
    h, w = pix.shape[:2]
    x0, y0, x1, y1 = max(0, left), max(0, top), min(fw, left + w), min(fh, top + h)
    if x0 >= x1 or y0 >= y1:
        return
    src = pix[y0 - top:y1 - top, x0 - left:x1 - left]
    dst = frame[y0:y1, x0:x1]
    alpha = src[..., 3:4].astype(np.uint16)
    color = src[..., :3].astype(np.uint16)
    if opacity < 0.997:
        k = int(opacity * 256)
        alpha = (alpha * k) >> 8
        color = (color * k) >> 8
    dst[:] = (color + (dst.astype(np.uint16) * (255 - alpha) + 127) // 255).astype(np.uint8)


# ---------------------------------------------------------------- matn

def text_advance(font, text: str, tracking: float) -> float:
    from motion_language import clusters
    return font.getlength(text) + tracking * max(0, len(clusters(text)) - 1)


def _draw_tracked(draw, x: float, y: float, text: str, font, fill, tracking: float, stroke: int = 0, stroke_fill=None):
    """Matnni harflar orasidagi masofa (tracking) bilan chizadi. y - asos chizig'i (baseline)."""
    if abs(tracking) < 0.01:
        draw.text((x, y), text, font=font, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=stroke_fill)
        return
    from motion_language import clusters
    units = clusters(text)
    for i, ch in enumerate(units):
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=stroke_fill)
        nxt = units[i + 1] if i + 1 < len(units) else ""
        x += (font.getlength(ch + nxt) - font.getlength(nxt) if nxt else font.getlength(ch)) + tracking


def text_sprite(text: str, font, color: str, tracking: float = 0.0, shadow: dict | None = None,
                glow: dict | None = None, stroke: dict | None = None) -> tuple:
    """Bitta so'z yoki ibora uchun sprite. (sprite, kenglik) qaytaradi. Sprite nuqtasi: chap + asos chizig'i."""
    ascent, descent = font.getmetrics()
    adv = text_advance(font, text, tracking)
    sh_blur = float((shadow or {}).get("blur", 0))
    sh_dx, sh_dy = float((shadow or {}).get("dx", 0)), float((shadow or {}).get("dy", 0))
    gl_blur = float((glow or {}).get("blur", 0))
    st_w = int(round(float((stroke or {}).get("width", 0))))
    pad = int(math.ceil(max(sh_blur * 3 + max(abs(sh_dx), abs(sh_dy)), gl_blur * 3, st_w) + 6))
    w, h = int(math.ceil(adv)) + pad * 2, ascent + descent + pad * 2
    base_y = pad + ascent
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def mask_of(width: int = 0):
        m = Image.new("L", (w, h), 0)
        _draw_tracked(ImageDraw.Draw(m), pad, base_y, text, font, 255, tracking, width, 255)
        return m

    mask = mask_of(st_w)
    if shadow and float(shadow.get("opacity", 0)) > 0:
        sm = mask.filter(ImageFilter.GaussianBlur(sh_blur)) if sh_blur > 0 else mask
        sm = sm.point(lambda v, k=float(shadow["opacity"]): int(v * k))
        layer = Image.new("RGBA", (w, h), rgb(shadow.get("color", "#000000")) + (0,))
        layer.putalpha(sm)
        img.alpha_composite(layer, (int(round(sh_dx)), int(round(sh_dy))) if sh_dx >= 0 and sh_dy >= 0 else (0, 0))
    if glow and float(glow.get("opacity", 0)) > 0 and gl_blur > 0:
        gm = mask.filter(ImageFilter.GaussianBlur(gl_blur)).point(
            lambda v, k=float(glow["opacity"]): min(255, int(v * k * 1.6)))
        layer = Image.new("RGBA", (w, h), rgb(glow.get("color", color)) + (0,))
        layer.putalpha(gm)
        img.alpha_composite(layer)
    draw = ImageDraw.Draw(img)
    if st_w > 0:
        _draw_tracked(draw, pad, base_y, text, font, rgb(stroke.get("color", "#000000")) + (255,), tracking,
                      st_w, rgb(stroke.get("color", "#000000")) + (255,))
    _draw_tracked(draw, pad, base_y, text, font, rgb(color) + (255,), tracking)
    return from_pil(img, -pad, -base_y), adv


# ---------------------------------------------------------------- emoji

class Emoji:
    """Emoji rasmlari (assets/emoji/noto-emoji-128.zip). Matn ichidagi emoji rasm qilib chiziladi."""

    ZIP = C.ROOT / "assets" / "emoji" / "noto-emoji-128.zip"
    _zip = None
    _names: set = set()
    _cache: dict = {}
    _missing_warned = False

    @classmethod
    def _open(cls) -> bool:
        if cls._zip is None:
            if not cls.ZIP.is_file():
                if not cls._missing_warned:
                    cls._missing_warned = True
                    C.warn(f"Emoji to'plami topilmadi ({cls.ZIP}). Emoji o'rniga bo'sh joy qoladi.")
                return False
            import zipfile
            cls._zip = zipfile.ZipFile(cls.ZIP)
            cls._names = {n[:-4] for n in cls._zip.namelist() if n.endswith(".png")}
        return True

    @staticmethod
    def _is_start(ch: str) -> bool:
        o = ord(ch)
        return (0x1F000 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF
                or 0x2190 <= o <= 0x21FF or 0x2300 <= o <= 0x23FF or o in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D))

    @classmethod
    def split(cls, text: str) -> list:
        """Matnni bo'laklarga ajratadi: [("text", "salom "), ("emoji", "1f525")]."""
        if not any(cls._is_start(ch) for ch in text) or not cls._open():
            return [("text", text)]
        out, buf, i = [], "", 0
        while i < len(text):
            if cls._is_start(text[i]):
                j, best = i + 1, None
                seq = [ord(text[i])]
                if "%x" % seq[0] in cls._names:
                    best = (i + 1, "%x" % seq[0])
                while j < len(text) and j - i < 12:  # ZWJ ketma-ketliklari, teri rangi, variatsiya belgisi
                    o = ord(text[j])
                    if not (o in (0x200D, 0xFE0F, 0x20E3) or 0x1F3FB <= o <= 0x1F3FF or cls._is_start(text[j])):
                        break
                    if o != 0xFE0F:
                        seq.append(o)
                    j += 1
                    name = "_".join("%x" % c for c in seq)
                    if name in cls._names:
                        best = (j, name)
                if best:
                    if buf:
                        out.append(("text", buf))
                        buf = ""
                    out.append(("emoji", best[1]))
                    i = best[0]
                    if i < len(text) and ord(text[i]) == 0xFE0F:
                        i += 1
                    continue
            buf += text[i]
            i += 1
        if buf:
            out.append(("text", buf))
        return out

    @classmethod
    def image(cls, name: str, size: int):
        key = (name, size)
        if key not in cls._cache:
            import io
            img = Image.open(io.BytesIO(cls._zip.read(name + ".png"))).convert("RGBA")
            cls._cache[key] = img.resize((size, size), Image.LANCZOS)
        return cls._cache[key]


def measure(font, text: str, tracking: float = 0.0) -> float:
    """Matn kengligi (emoji bilan birga)."""
    runs = Emoji.split(text)
    if len(runs) == 1 and runs[0][0] == "text":
        return text_advance(font, text, tracking)
    em = font.size * 1.06
    return sum(text_advance(font, r, tracking) if kind == "text" else em for kind, r in runs)


def word_sprite(text: str, font, color: str, tracking: float = 0.0, shadow: dict | None = None,
                glow: dict | None = None, stroke: dict | None = None) -> tuple:
    """text_sprite ning emoji tushunadigan varianti. (sprite, kenglik) qaytaradi."""
    runs = Emoji.split(text)
    if len(runs) == 1 and runs[0][0] == "text":
        return text_sprite(text, font, color, tracking, shadow, glow, stroke)
    em = int(round(font.size * 1.06))
    parts, x = [], 0.0
    for kind, value in runs:
        if kind == "text":
            if value.strip() == "":
                x += text_advance(font, value, tracking)
                continue
            spr, adv = text_sprite(value, font, color, tracking, shadow, glow, stroke)
            parts.append((spr, x, 0.0))
            x += adv
        else:
            img = Emoji.image(value, em)
            sh = None
            if shadow and float(shadow.get("opacity", 0)) > 0:
                sh = {"blur": shadow.get("blur", 10), "dy": shadow.get("dy", 3), "opacity": float(shadow["opacity"]) * 0.8}
            spr = pil_sprite(img, shadow=sh)             # nuqtasi markazda
            parts.append((spr, x + em / 2, -font.size * 0.36))
            x += em
    return merge_sprites(parts), x


def merge_sprites(parts: list) -> Sprite:
    """Bir necha spriteni bitta qiladi. parts: [(sprite, x, y)] - har birining nuqtasi umumiy nuqtaga nisbatan."""
    left = min(px + spr.ox for spr, px, _ in parts)
    top = min(py + spr.oy for spr, _, py in parts)
    right = max(px + spr.ox + spr.w for spr, px, _ in parts)
    bottom = max(py + spr.oy + spr.h for spr, _, py in parts)
    canvas = np.zeros((int(math.ceil(bottom - top)), int(math.ceil(right - left)), 4), np.uint8)
    for spr, px, py in parts:
        x0, y0 = int(round(px + spr.ox - left)), int(round(py + spr.oy - top))
        h, w = min(spr.h, canvas.shape[0] - y0), min(spr.w, canvas.shape[1] - x0)
        dst = canvas[y0:y0 + h, x0:x0 + w].astype(np.uint16)
        src = spr.pix[:h, :w].astype(np.uint16)
        canvas[y0:y0 + h, x0:x0 + w] = (src + (dst * (255 - src[..., 3:4]) + 127) // 255).astype(np.uint8)
    return Sprite(canvas, left, top)


# ---------------------------------------------------------------- shakllar

def rounded_rect_sprite(w: int, h: int, radius: float, fill: tuple, border: tuple | None = None,
                        border_width: int = 0, shadow: dict | None = None) -> Sprite:
    """Burchaklari yumaloq to'rtburchak. fill/border: (r, g, b, a). Sprite nuqtasi: chap-yuqori burchak."""
    s = 3  # silliq chetlar uchun kattaroq chizib, keyin kichraytiramiz
    sh_blur = float((shadow or {}).get("blur", 0))
    sh_dy = float((shadow or {}).get("dy", 0))
    pad = int(math.ceil(sh_blur * 3 + abs(sh_dy) + 2)) if shadow else 2
    big = Image.new("RGBA", ((w + pad * 2) * s, (h + pad * 2) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    box = [pad * s, pad * s, (pad + w) * s - 1, (pad + h) * s - 1]
    d.rounded_rectangle(box, radius=radius * s, fill=fill, outline=border, width=border_width * s if border else 0)
    img = big.resize((w + pad * 2, h + pad * 2), Image.LANCZOS)
    if shadow and float(shadow.get("opacity", 0)) > 0:
        alpha = img.getchannel("A").filter(ImageFilter.GaussianBlur(sh_blur)).point(
            lambda v, k=float(shadow["opacity"]): int(v * k))
        base = Image.new("RGBA", img.size, rgb(shadow.get("color", "#000000")) + (0,))
        base.putalpha(alpha)
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(base, (0, int(round(max(0, sh_dy)))))
        out.alpha_composite(img)
        img = out
    return from_pil(img, -pad, -pad)


def glass(frame: np.ndarray, x: int, y: int, w: int, h: int, radius: int, opacity: float = 1.0,
          blur: float = 18, tint: tuple = (255, 255, 255), tint_alpha: float = 0.22) -> None:
    """"Shisha" panel: orqadagi tasvir xiralashadi va ustiga och rang beriladi."""
    fh, fw = frame.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(fw, x + w), min(fh, y + h)
    if x0 >= x1 or y0 >= y1 or opacity <= 0.01:
        return
    roi = frame[y0:y1, x0:x1]
    soft = cv2.GaussianBlur(roi, (0, 0), blur)
    soft = (soft.astype(np.float32) * (1 - tint_alpha) + np.array(tint, np.float32) * tint_alpha)
    mask = np.zeros((h, w), np.uint8)
    cv2.rectangle(mask, (radius, 0), (w - radius - 1, h - 1), 255, -1)
    cv2.rectangle(mask, (0, radius), (w - 1, h - radius - 1), 255, -1)
    for cx, cy in ((radius, radius), (w - radius - 1, radius), (radius, h - radius - 1), (w - radius - 1, h - radius - 1)):
        cv2.circle(mask, (cx, cy), radius, 255, -1, lineType=cv2.LINE_AA)
    m = (mask[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255.0 * opacity)[..., None]
    roi[:] = (roi.astype(np.float32) * (1 - m) + soft * m).astype(np.uint8)


def pil_sprite(img, radius: float = 0, shadow: dict | None = None) -> Sprite:
    """Pillow rasmidan sprite: yumaloq burchak va soya bilan. Sprite nuqtasi: markaz."""
    img = img.convert("RGBA")
    if radius > 0:
        s = 3
        m = Image.new("L", (img.width * s, img.height * s), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width * s - 1, img.height * s - 1], radius=radius * s, fill=255)
        m = m.resize(img.size, Image.LANCZOS)
        img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", img.size, 0), m))
    if shadow and float(shadow.get("opacity", 0)) > 0:
        sh_blur, sh_dy = float(shadow.get("blur", 12)), float(shadow.get("dy", 6))
        pad = int(math.ceil(sh_blur * 3 + abs(sh_dy)))
        canvas = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
        alpha = Image.new("L", canvas.size, 0)
        alpha.paste(img.getchannel("A"), (pad, pad + int(round(sh_dy))))
        alpha = alpha.filter(ImageFilter.GaussianBlur(sh_blur)).point(lambda v, k=float(shadow["opacity"]): int(v * k))
        base = Image.new("RGBA", canvas.size, rgb(shadow.get("color", "#000000")) + (0,))
        base.putalpha(alpha)
        canvas.alpha_composite(base)
        canvas.alpha_composite(img, (pad, pad))
        img = canvas
    return from_pil(img, -img.width / 2, -img.height / 2)


def image_sprite(path: str | Path, width: int | None = None, height: int | None = None,
                 radius: float = 0, shadow: dict | None = None) -> Sprite:
    """Rasm faylidan sprite (PNG shaffofligi saqlanadi). Sprite nuqtasi: markaz."""
    p = C.need_file(path, "Rasm")
    try:
        img = Image.open(p).convert("RGBA")
    except Exception as exc:
        raise C.MontajError(f"Rasmni ochib bo'lmadi ({p.name}): {exc}") from exc
    if width or height:
        ratio = img.width / img.height
        if width and height:
            w, h = int(width), int(height)
        elif width:
            w, h = int(width), max(1, int(round(width / ratio)))
        else:
            w, h = max(1, int(round(height * ratio))), int(height)
        img = img.resize((w, h), Image.LANCZOS)
    return pil_sprite(img, radius, shadow)
