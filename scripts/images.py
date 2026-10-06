"""Videoga qo'yish uchun rasm va qo'shimcha kadr (b-roll) topadi yoki yaratadi.

    # 1) Qidirish: nomzodlar raqamlangan bitta rasmga teriladi (agent ko'rib tanlaydi)
    python scripts/images.py search "mountain sunrise" --video input/video.mp4
    python scripts/images.py search "student studying" --kind video --video input/video.mp4

    # 2) Tanlash: to'liq o'lchamdagi fayl yuklanadi, yoniga muallif va litsenziya yoziladi
    python scripts/images.py pick 3 --name tog --video input/video.mp4

    # 3) AI bilan yaratish (GEMINI_API_KEY kerak)
    python scripts/images.py ai "minimal 3D illustration of a rocket, yellow and black" --name raketa --video input/video.mp4

    # 4) Ishlatilgan rasmlar uchun mualliflik ro'yxati
    python scripts/images.py credits --video input/video.mp4

Manbalar:
  openverse, wikimedia  - kalitsiz ishlaydi. Faqat tijoratda ishlatsa bo'ladigan litsenziyalar olinadi
                          (CC0, jamoat mulki, CC BY). CC BY da muallifni ko'rsatish SHART.
  pexels, pixabay       - bepul kalit kerak (.env fayliga PEXELS_API_KEY=..., PIXABAY_API_KEY=...).
                          Sifatli fotosuratlar va b-roll videolar; muallifni ko'rsatish shart emas.
  ai (gemini)           - pullik bo'lishi mumkin; .env ga GEMINI_API_KEY=... yoziladi.

Fayllar temp/<video nomi>/images/ ga tushadi (yoki --out papkaga). Kalitlar hech qayerga chiqarilmaydi.
Odamlar yuzi, brend logotiplari va mashhur asarlar tushgan rasmlarni reklama uchun ishlatishda ehtiyot bo'ling.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import common as C

UA = "editor-pro/1.0 (local video editing tool)"
TIMEOUT = 30
MAX_IMAGE = 30 * 1024 * 1024
MAX_VIDEO = 150 * 1024 * 1024
MAX_SIDE = 2400                       # yuklangan rasm shu o'lchamgacha kichraytiriladi
SOURCES = ("openverse", "wikimedia", "pexels", "pixabay")
FREE_LICENSES = {"cc0", "pdm", "by", "pexels", "pixabay"}       # tijoratda ishlatsa va o'zgartirsa bo'ladi
LICENSE_NAMES = {"cc0": "CC0 (jamoat mulki)", "pdm": "Jamoat mulki", "by": "CC BY (muallif ko'rsatiladi)",
                 "by-sa": "CC BY-SA (muallif + shu litsenziya)", "pexels": "Pexels litsenziyasi",
                 "pixabay": "Pixabay litsenziyasi", "ai": "AI yaratgan"}
ORIENT = {"portrait": "tall", "landscape": "wide", "square": "square"}


# ---------------------------------------------------------------- tarmoq

def _mask(url: str) -> str:
    """Xato matnida kalit ko'rinmasligi uchun manzildagi so'rov qismini olib tashlaydi."""
    return url.split("?", 1)[0]


def _request(url: str, headers: dict | None = None, data: bytes | None = None):
    if not url.lower().startswith("https://"):
        raise C.MontajError(f"Faqat https manzillar ochiladi: {_mask(url)}")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        hint = {401: "kalit noto'g'ri", 403: "ruxsat yo'q yoki kalit noto'g'ri",
                429: "so'rovlar chegarasi tugadi, keyinroq urinib ko'ring"}.get(exc.code, "")
        raise C.MontajError(f"{_mask(url)} javobi: HTTP {exc.code}" + (f" ({hint})" if hint else "")) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise C.MontajError(f"{_mask(url)} ga ulanib bo'lmadi (internet yoki manba ishlamayapti): {reason}") from None


def http_json(url: str, headers: dict | None = None, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        headers = {"Content-Type": "application/json", **(headers or {})}
    with _request(url, headers, data) as resp:
        raw = resp.read(40 * 1024 * 1024)
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise C.MontajError(f"{_mask(url)} tushunarsiz javob qaytardi (JSON emas).") from None


def download(url: str, dest: Path, limit: int, kind: str) -> Path:
    """Faylni yuklaydi. Turi (rasm/video) va hajmi tekshiriladi."""
    with _request(url) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype and not (ctype.startswith(kind + "/") or ctype == "application/octet-stream"):
            raise C.MontajError(f"Kutilgan {kind}, kelgan fayl turi: {ctype} ({_mask(url)})")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        size = 0
        with open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    fh.close()
                    tmp.unlink(missing_ok=True)
                    raise C.MontajError(f"Fayl juda katta (> {limit // (1024 * 1024)} MB): {_mask(url)}")
                fh.write(chunk)
    tmp.replace(dest)
    return dest


# ---------------------------------------------------------------- manbalar

def _clean(text) -> str:
    """HTML teglarini olib tashlaydi (Wikimedia muallif maydoni HTML bo'lib keladi)."""
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:160]


def search_openverse(query: str, n: int, orient: str, kind: str) -> list:
    if kind != "photo":
        return []
    params = {"q": query, "license_type": "commercial,modification", "page_size": min(20, max(n * 2, 8)),
              "extension": "jpg,jpeg,png,webp", "mature": "false"}
    if orient in ORIENT:
        params["aspect_ratio"] = ORIENT[orient]
    data = http_json("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params))
    out = []
    for r in data.get("results", []):
        lic = str(r.get("license", "")).lower()
        out.append({"source": "openverse", "id": str(r.get("id", "")), "kind": "photo",
                    "title": _clean(r.get("title")), "thumb": r.get("thumbnail") or r.get("url"),
                    "full": r.get("url"), "page": r.get("foreign_landing_url"),
                    "author": _clean(r.get("creator")), "author_url": r.get("creator_url") or "",
                    "license": lic, "license_version": str(r.get("license_version") or ""),
                    "license_url": r.get("license_url") or "", "width": r.get("width") or 0,
                    "height": r.get("height") or 0})
    return out


def _wm_license(name: str) -> str:
    n = name.lower().replace("creative commons", "cc").strip()
    if "cc0" in n or "zero" in n:
        return "cc0"
    if "public domain" in n or n.startswith("pd") or "no restrictions" in n:
        return "pdm"
    m = re.match(r"cc[ -]by(-sa|-nc|-nd|-nc-sa|-nc-nd)?\b", n)
    if m:
        return "by" + (m.group(1) or "")
    return n or "unknown"


def search_wikimedia(query: str, n: int, orient: str, kind: str) -> list:
    if kind != "photo":
        return []
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
              "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": min(40, max(n * 3, 12)),
              "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "480",
              "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|ObjectName"}
    data = http_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    pages = sorted((data.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        w, h = int(info.get("width") or 0), int(info.get("height") or 0)
        if min(w, h) < 600:
            continue
        if orient == "portrait" and w > h or orient == "landscape" and h > w:
            continue
        meta = info.get("extmetadata") or {}
        lic_name = (meta.get("LicenseShortName") or {}).get("value", "")
        out.append({"source": "wikimedia", "id": str(page.get("pageid", "")), "kind": "photo",
                    "title": _clean((meta.get("ObjectName") or {}).get("value") or page.get("title", "")[5:]),
                    "thumb": info.get("thumburl") or info.get("url"), "full": info.get("url"),
                    "page": info.get("descriptionurl"), "author": _clean((meta.get("Artist") or {}).get("value")),
                    "author_url": "", "license": _wm_license(lic_name), "license_version": lic_name,
                    "license_url": (meta.get("LicenseUrl") or {}).get("value", ""), "width": w, "height": h})
    return out


def search_pexels(query: str, n: int, orient: str, kind: str) -> list:
    key = C.secret("PEXELS_API_KEY")
    if not key:
        return []
    params = {"query": query, "per_page": min(40, max(n * 2, 8))}
    if orient in ("portrait", "landscape", "square"):
        params["orientation"] = orient
    out = []
    if kind == "photo":
        data = http_json("https://api.pexels.com/v1/search?" + urllib.parse.urlencode(params), {"Authorization": key})
        for r in data.get("photos", []):
            src = r.get("src") or {}
            out.append({"source": "pexels", "id": str(r.get("id", "")), "kind": "photo", "title": _clean(r.get("alt")),
                        "thumb": src.get("medium") or src.get("small"), "full": src.get("large2x") or src.get("original"),
                        "page": r.get("url"), "author": _clean(r.get("photographer")),
                        "author_url": r.get("photographer_url") or "", "license": "pexels", "license_version": "",
                        "license_url": "https://www.pexels.com/license/", "width": r.get("width") or 0,
                        "height": r.get("height") or 0})
    else:
        data = http_json("https://api.pexels.com/v1/videos/search?" + urllib.parse.urlencode(params), {"Authorization": key})
        for r in data.get("videos", []):
            files = [f for f in (r.get("video_files") or []) if f.get("link") and "mp4" in str(f.get("file_type", ""))]
            if not files:
                continue
            # 1080 ga eng yaqin (undan kichik bo'lmagan) variant; bo'lmasa eng kattasi
            files.sort(key=lambda f: (min(f.get("width") or 0, f.get("height") or 0) < 1000,
                                      abs(min(f.get("width") or 0, f.get("height") or 0) - 1080)))
            best = files[0]
            pics = r.get("video_pictures") or []
            user = r.get("user") or {}
            out.append({"source": "pexels", "id": str(r.get("id", "")), "kind": "video", "title": "",
                        "thumb": r.get("image") or (pics[0].get("picture") if pics else None), "full": best["link"],
                        "page": r.get("url"), "author": _clean(user.get("name")), "author_url": user.get("url") or "",
                        "license": "pexels", "license_version": "", "license_url": "https://www.pexels.com/license/",
                        "width": best.get("width") or 0, "height": best.get("height") or 0,
                        "duration": r.get("duration") or 0})
    return out


def search_pixabay(query: str, n: int, orient: str, kind: str) -> list:
    key = C.secret("PIXABAY_API_KEY")
    if not key:
        return []
    params = {"key": key, "q": query[:100], "per_page": min(40, max(n * 2, 8)), "safesearch": "true"}
    out = []
    if kind == "photo":
        params["image_type"] = "photo"
        if orient in ("portrait", "landscape"):
            params["orientation"] = "vertical" if orient == "portrait" else "horizontal"
        data = http_json("https://pixabay.com/api/?" + urllib.parse.urlencode(params))
        for r in data.get("hits", []):
            out.append({"source": "pixabay", "id": str(r.get("id", "")), "kind": "photo", "title": _clean(r.get("tags")),
                        "thumb": r.get("webformatURL") or r.get("previewURL"), "full": r.get("largeImageURL"),
                        "page": r.get("pageURL"), "author": _clean(r.get("user")), "author_url": "",
                        "license": "pixabay", "license_version": "",
                        "license_url": "https://pixabay.com/service/license-summary/",
                        "width": r.get("imageWidth") or 0, "height": r.get("imageHeight") or 0})
    else:
        data = http_json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode(params))
        for r in data.get("hits", []):
            vids = r.get("videos") or {}
            best = None
            for name in ("medium", "large", "small"):
                v = vids.get(name) or {}
                if v.get("url") and min(v.get("width") or 0, v.get("height") or 0) >= 700:
                    best = v
                    break
            best = best or vids.get("small") or vids.get("tiny") or {}
            if not best.get("url"):
                continue
            w, h = best.get("width") or 0, best.get("height") or 0
            if orient == "portrait" and w > h or orient == "landscape" and h > w:
                continue
            out.append({"source": "pixabay", "id": str(r.get("id", "")), "kind": "video", "title": _clean(r.get("tags")),
                        "thumb": best.get("thumbnail"), "full": best["url"], "page": r.get("pageURL"),
                        "author": _clean(r.get("user")), "author_url": "", "license": "pixabay", "license_version": "",
                        "license_url": "https://pixabay.com/service/license-summary/", "width": w, "height": h,
                        "duration": r.get("duration") or 0})
    return out


SEARCHERS = {"openverse": search_openverse, "wikimedia": search_wikimedia,
             "pexels": search_pexels, "pixabay": search_pixabay}


# ---------------------------------------------------------------- qidirish

def images_dir(video: str | None, out: str | None) -> Path:
    if out:
        folder = Path(out)
        if not folder.is_absolute():
            folder = C.ROOT / folder
    elif video:
        folder = C.job_dir(C.need_file(video, "Video")) / "images"
    else:
        folder = C.TEMP_DIR / "images"
    C.guard_output(folder / "x.jpg")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def search(query: str, folder: Path, n: int = 8, kind: str = "photo", orient: str = "any",
           sources: list | None = None, allow_sa: bool = False) -> dict:
    """Manbalardan nomzodlarni yig'adi, kichik rasmlarini yuklaydi va ko'rib tanlash uchun varaq yasaydi."""
    cfg = C.load_style().get("images", {})
    sources = sources or list(cfg.get("sources") or SOURCES)
    allowed = set(cfg.get("licenses") or FREE_LICENSES) | {"pexels", "pixabay"}
    if allow_sa:
        allowed.add("by-sa")
    pools, problems = [], []
    for name in sources:
        if name not in SEARCHERS:
            raise C.MontajError(f"Noma'lum manba: {name!r}. Mumkin: {', '.join(SOURCES)}")
        if name in ("pexels", "pixabay") and not C.secret(name.upper() + "_API_KEY"):
            problems.append(f"{name}: kalit yo'q (.env ga {name.upper()}_API_KEY qo'shilsa ishlaydi)")
            continue
        try:
            found = [c for c in SEARCHERS[name](query, n, orient, kind)
                     if c.get("full") and c.get("thumb") and c["license"] in allowed]
        except C.MontajError as exc:
            problems.append(f"{name}: {exc}")
            continue
        if found:
            pools.append(found)
        else:
            problems.append(f"{name}: mos natija yo'q")
    # manbalar navbat bilan aralashtiriladi (bitta manba hammasini egallamasin)
    picked, i = [], 0
    while len(picked) < n and any(pools):
        pool = pools[i % len(pools)]
        if pool:
            picked.append(pool.pop(0))
        i += 1
        if i > 10 * n + 40:
            break
    thumbs = folder / "thumbs"
    for old in thumbs.glob("*") if thumbs.is_dir() else []:
        old.unlink()
    good = []
    for cand in picked:
        num = len(good) + 1
        dest = thumbs / f"{num:02d}.jpg"
        try:
            raw = download(cand["thumb"], dest.with_suffix(".bin"), 8 * 1024 * 1024, "image")
            with Image.open(raw) as im:
                im = im.convert("RGB")
                im.thumbnail((480, 480))
                im.save(dest, quality=88)
            raw.unlink(missing_ok=True)
        except Exception as exc:                      # bitta buzuq rasm butun qidiruvni to'xtatmasin
            dest.with_suffix(".bin").unlink(missing_ok=True)
            problems.append(f"{cand['source']} #{cand['id']}: kichik rasm ochilmadi ({str(exc)[:80]})")
            continue
        cand["n"] = num
        cand["thumb_file"] = str(dest)
        good.append(cand)
    data = {"query": query, "kind": kind, "candidates": good, "problems": problems}
    C.write_json(data, folder / "candidates.json")
    if good:
        data["sheet"] = str(contact_sheet(good, folder / "candidates.jpg", query))
    return data


def contact_sheet(cands: list, out: Path, title: str) -> Path:
    cols = 4 if len(cands) > 4 else max(1, len(cands))
    cell, label = 300, 58
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label) + 46), (22, 22, 26))
    draw = ImageDraw.Draw(sheet)
    try:
        f_big = ImageFont.truetype(str(C.ROOT / "style" / "fonts" / "Inter.ttf"), 30)
        f_small = ImageFont.truetype(str(C.ROOT / "style" / "fonts" / "Inter.ttf"), 17)
    except OSError:
        f_big = f_small = ImageFont.load_default()
    draw.text((12, 10), f"\"{title}\"  -  tanlash: images.py pick RAQAM", font=f_small, fill=(200, 200, 205))
    for i, c in enumerate(cands):
        x, y = (i % cols) * cell, 46 + (i // cols) * (cell + label)
        with Image.open(c["thumb_file"]) as im:
            im = im.convert("RGB")
            im.thumbnail((cell - 12, cell - 12))
            sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        draw.rounded_rectangle([x + 8, y + 8, x + 62, y + 50], radius=10, fill=(255, 230, 0))
        draw.text((x + 18, y + 9), str(c["n"]), font=f_big, fill=(17, 17, 17))
        info = f"{c['source']} · {c['license']} · {c['width']}x{c['height']}"
        if c.get("duration"):
            info += f" · {c['duration']}s"
        draw.text((x + 10, y + cell + 4), info, font=f_small, fill=(215, 215, 220))
        who = (c.get("author") or "")[:30]
        draw.text((x + 10, y + cell + 28), who, font=f_small, fill=(150, 150, 158))
    sheet.save(out, quality=88)
    return out


# ---------------------------------------------------------------- tanlash

def credit_line(c: dict) -> str:
    """Mualliflik qatori (CC BY uchun shu ko'rinish talab qilinadi)."""
    if c.get("license") == "ai":
        return f"AI yaratgan rasm ({c.get('provider', '')} {c.get('model', '')})".strip()
    title = f"\"{c['title']}\"" if c.get("title") else ("Video" if c.get("kind") == "video" else "Rasm")
    who = f" - {c['author']}" if c.get("author") else ""
    lic = LICENSE_NAMES.get(c.get("license", ""), c.get("license", ""))
    if c.get("license") in ("by", "by-sa"):
        lic = f"CC {c['license'].upper()} {c.get('license_version', '')}".strip()
        if c.get("license_version", "").upper().startswith("CC"):
            lic = c["license_version"]
    return f"{title}{who}, {lic}, {c.get('page') or c.get('full') or ''}".strip(", ")


def save_image(src: Path, dest_base: Path) -> Path:
    """Rasmni qayta saqlaydi (o'lchamini cheklab): shaffof bo'lsa PNG, bo'lmasa JPG."""
    try:
        with Image.open(src) as im:
            im.load()
            alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
            im = im.convert("RGBA" if alpha else "RGB")
            if alpha and im.getchannel("A").getextrema()[0] == 255:
                im, alpha = im.convert("RGB"), False
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            out = dest_base.with_suffix(".png" if alpha else ".jpg")
            im.save(out, **({} if alpha else {"quality": 93}))
    except C.MontajError:
        raise
    except Exception as exc:
        raise C.MontajError(f"Yuklangan fayl rasm emas yoki buzuq: {exc}") from exc
    return out


def pick(numbers: list, folder: Path, name: str | None = None) -> list:
    cfile = folder / "candidates.json"
    if not cfile.is_file():
        raise C.MontajError(f"Avval qidiring: images.py search ... ({cfile} topilmadi)")
    cands = {c["n"]: c for c in C.read_json(cfile).get("candidates", [])}
    results = []
    for idx, num in enumerate(numbers):
        if num not in cands:
            raise C.MontajError(f"{num}-raqamli nomzod yo'q. Mavjudlari: {', '.join(map(str, sorted(cands)))}")
        c = cands[num]
        base = C.slugify(name) if name else f"{c['source']}_{c['id']}"
        if name and len(numbers) > 1:
            base += f"_{idx + 1}"
        raw = folder / f".{base}.download"
        if c["kind"] == "video":
            download(c["full"], raw, MAX_VIDEO, "video")
            out = folder / f"{base}.mp4"
            raw.replace(out)
            meta = C.ffprobe_info(out)
            if not meta.get("has_video"):
                out.unlink(missing_ok=True)
                raise C.MontajError("Yuklangan fayl video emas.")
        else:
            download(c["full"], raw, MAX_IMAGE, "image")
            try:
                out = save_image(raw, folder / base)
            finally:
                raw.unlink(missing_ok=True)
        credit = {k: c.get(k) for k in ("source", "id", "title", "author", "author_url", "license",
                                        "license_version", "license_url", "page", "kind")}
        credit["attribution_required"] = c["license"] in ("by", "by-sa")
        credit["credit"] = credit_line(c)
        C.write_json(credit, out.with_name(out.name + ".credit.json"))
        results.append({"file": out, "credit": credit})
    return results


# ---------------------------------------------------------------- AI rasm

def _find_image_data(node):
    """Javob ichidan base64 rasmni qidiradi (javob tuzilishi o'zgarsa ham topadi)."""
    if isinstance(node, dict):
        data = node.get("data")
        mime = str(node.get("mime_type") or node.get("mimeType") or "")
        if isinstance(data, str) and len(data) > 1000 and (mime.startswith("image/") or not mime):
            return data
        for value in node.values():
            found = _find_image_data(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_image_data(value)
            if found:
                return found
    return None


def ai_image(prompt: str, folder: Path, name: str, aspect: str = "9:16", size: str | None = None) -> dict:
    """Gemini API orqali rasm yaratadi. Manba: ai.google.dev/gemini-api/docs/image-generation (2026-10)."""
    cfg = C.load_style().get("images", {}).get("ai", {})
    provider = str(cfg.get("provider", "gemini"))
    if provider != "gemini":
        raise C.MontajError(f"images.ai.provider: hozircha faqat 'gemini' bor (berilgan: {provider!r}).")
    key = C.secret("GEMINI_API_KEY")
    if not key:
        raise C.MontajError("AI rasm uchun kalit yo'q. Loyiha papkasidagi .env fayliga qo'shing:\n"
                            "  GEMINI_API_KEY=...   (kalit: https://aistudio.google.com/apikey)\n"
                            "Kalitsiz yo'llar: images.py search (stok rasm), html_render.py (o'zi chizadi), icons.py.")
    model = str(cfg.get("model", "gemini-3.1-flash-image"))
    body = {"model": model, "input": [{"type": "text", "text": prompt}],
            "response_format": {"type": "image", "aspect_ratio": aspect, "image_size": size or str(cfg.get("size", "1K"))}}
    endpoint = str(cfg.get("endpoint", "https://generativelanguage.googleapis.com/v1beta/interactions"))
    resp = http_json(endpoint, {"x-goog-api-key": key}, body)
    data = _find_image_data(resp)
    if not data:
        keys = ", ".join(sorted(resp.keys())) if isinstance(resp, dict) else type(resp).__name__
        raise C.MontajError(f"AI javobida rasm topilmadi (javob kalitlari: {keys}). "
                            "Model nomi yoki API o'zgargan bo'lishi mumkin: style.json dagi images.ai ni tekshiring.")
    raw = folder / f".{C.slugify(name)}.download"
    try:
        raw.write_bytes(base64.b64decode(data))
        out = save_image(raw, folder / C.slugify(name))
    finally:
        raw.unlink(missing_ok=True)
    credit = {"source": "ai", "provider": provider, "model": model, "prompt": prompt, "license": "ai",
              "ai_generated": True, "attribution_required": False, "kind": "photo",
              "credit": f"AI yaratgan rasm ({provider} {model})"}
    C.write_json(credit, out.with_name(out.name + ".credit.json"))
    return {"file": out, "credit": credit}


# ---------------------------------------------------------------- mualliflik ro'yxati

def collect_credits(elements_file: str | Path | None, brand_dir: Path | None = None) -> list:
    """elements.json da ishlatilgan fayllarning mualliflik ma'lumoti (yonidagi .credit.json dan)."""
    if not elements_file or not Path(elements_file).is_file():
        return []
    data = C.read_json(elements_file)
    items = data.get("elements", data) if isinstance(data, dict) else data
    out, seen = [], set()

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("file", "image") and isinstance(value, str):
                    for base in ([brand_dir] if brand_dir else []) + [C.ROOT]:
                        p = Path(value) if Path(value).is_absolute() else base / value
                        side = p.with_name(p.name + ".credit.json")
                        if side.is_file() and str(side) not in seen:
                            seen.add(str(side))
                            out.append(dict(C.read_json(side), file=value))
                            break
                else:
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(items)
    return out


def credits_text(credits: list) -> str:
    lines = []
    need = [c for c in credits if c.get("attribution_required")]
    if need:
        lines.append("MUALLIF KO'RSATILISHI SHART (post tavsifiga yozing):")
        lines += [f"  - {c['credit']}" for c in need]
    ai = [c for c in credits if c.get("ai_generated")]
    if ai:
        lines.append("AI YARATGAN RASM BOR: Instagramda \"AI info\" belgisini yoqish kerak bo'lishi mumkin.")
        lines += [f"  - {c['file']}" for c in ai]
    rest = [c for c in credits if not c.get("attribution_required") and not c.get("ai_generated")]
    if rest:
        lines.append("Muallif ko'rsatish shart emas (ma'lumot uchun):")
        lines += [f"  - {c['credit']}" for c in rest]
    return "\n".join(lines)


# ---------------------------------------------------------------- buyruq qatori

def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(C.ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Videoga rasm va b-roll topish yoki yaratish.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def where(p):
        p.add_argument("--video", help="Qaysi video uchun (fayllar temp/<nom>/images/ ga tushadi)")
        p.add_argument("--out", help="Boshqa papka (masalan brands/NOM/assets)")

    s = sub.add_parser("search", help="Stok rasm yoki video qidirish")
    s.add_argument("query", help="Qidiruv so'zi (inglizcha yozilsa natija ko'proq)")
    s.add_argument("--kind", choices=["photo", "video"], default="photo")
    s.add_argument("--n", type=int, default=8, help="Nechta nomzod (standart 8)")
    s.add_argument("--orient", choices=["any", "portrait", "landscape", "square"], default="any")
    s.add_argument("--source", help="Manbalar, vergul bilan: " + ",".join(SOURCES))
    s.add_argument("--allow-sa", action="store_true", help="CC BY-SA litsenziyasini ham qo'sh")
    where(s)
    p = sub.add_parser("pick", help="Tanlangan nomzod(lar)ni to'liq o'lchamda yuklash")
    p.add_argument("numbers", help="Raqam(lar): 3 yoki 1,4")
    p.add_argument("--name", help="Fayl nomi (kengaytmasiz), masalan: tog")
    where(p)
    a = sub.add_parser("ai", help="AI bilan rasm yaratish (GEMINI_API_KEY kerak)")
    a.add_argument("prompt", help="Rasm tavsifi (inglizcha)")
    a.add_argument("--name", required=True, help="Fayl nomi (kengaytmasiz)")
    a.add_argument("--ar", default="9:16", help="Tomonlar nisbati: 9:16, 1:1, 16:9, 4:5 ...")
    a.add_argument("--size", help="O'lcham: 1K, 2K (standart: style.json images.ai.size)")
    where(a)
    c = sub.add_parser("credits", help="Videoda ishlatilgan rasmlar uchun mualliflik ro'yxati")
    c.add_argument("--video", required=True)
    c.add_argument("--brand")
    args = ap.parse_args()

    if args.cmd == "credits":
        work = C.job_dir(C.need_file(args.video, "Video"))
        credits = collect_credits(work / "elements.json", C.brand_dir(C.load_style(brand=args.brand)))
        if not credits:
            C.info("Mualliflik ma'lumoti bor rasm ishlatilmagan.")
            return 0
        text = credits_text(credits)
        (work / "credits.txt").write_text(text + "\n", encoding="utf-8")
        C.info(text + f"\n\nSaqlandi: {work / 'credits.txt'}")
        return 0

    folder = images_dir(args.video, args.out)
    if args.cmd == "search":
        if not 1 <= args.n <= 24:
            raise C.MontajError("--n 1 dan 24 gacha bo'lishi kerak.")
        res = search(args.query, folder, args.n, args.kind, args.orient,
                     [x.strip() for x in args.source.split(",") if x.strip()] if args.source else None, args.allow_sa)
        for c_ in res["candidates"]:
            C.info(f"  {c_['n']:>2}. [{c_['source']}, {LICENSE_NAMES.get(c_['license'], c_['license'])}] "
                   f"{c_['width']}x{c_['height']}  {c_.get('title') or ''}"[:150])
        for problem in res["problems"]:
            C.info(f"  ({problem})")
        if not res["candidates"]:
            raise C.MontajError("Hech narsa topilmadi. Boshqa (inglizcha) so'z bilan sinab ko'ring "
                                "yoki --source bilan manbani almashtiring.")
        C.info(f"\nNOMZODLAR ({len(res['candidates'])} ta): {res['sheet']}\n"
               f"Rasmni ko'rib tanlang:  images.py pick RAQAM --name NOM"
               + (f" --video \"{args.video}\"" if args.video else (f" --out \"{args.out}\"" if args.out else "")))
        return 0
    if args.cmd == "pick":
        try:
            nums = [int(x) for x in args.numbers.split(",") if x.strip()]
        except ValueError:
            raise C.MontajError("Raqamlar kerak, masalan: 3 yoki 1,4") from None
        for item in pick(nums, folder, args.name):
            C.info(f"YUKLANDI: {rel(item['file'])}\n  {item['credit']['credit']}"
                   + ("\n  DIQQAT: muallifni ko'rsatish SHART (post tavsifida)." if item["credit"]["attribution_required"] else ""))
        C.info("\nelements.json da ishlatish:  {\"type\": \"image\" yoki \"broll\", \"file\": \"<yuqoridagi yo'l>\", ...}")
        return 0
    item = ai_image(args.prompt, folder, args.name, args.ar, args.size)
    C.info(f"YARATILDI: {rel(item['file'])}\n  AI yaratgan rasm: postda \"AI info\" belgisi kerak bo'lishi mumkin.")
    return 0


if __name__ == "__main__":
    C.run_main(main)
