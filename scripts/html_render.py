"""HTML/CSS/SVG sahifani shaffof fonli PNG rasmga aylantiradi (brauzer yordamida).

Bu orqali agent istalgan grafikani o'zi "chizadi": kartochka, diagramma, telefon ekrani maketi,
sxema, illyustratsiya. HTML yoziladi, shu skript uni rasm qiladi, rasm videoga `image` yoki
`broll` elementi bilan qo'yiladi.

    python scripts/html_render.py temp/video/gfx/karta.html -o temp/video/images/karta.png
    python scripts/html_render.py sahifa.html -o rasm.png --trim           # bo'sh chetlarni kesib tashlaydi
    python scripts/html_render.py sahifa.html -o fon.jpg --size 1080x1920 --brand NOM

Sahifa ichida tayyor narsalar:
  - Loyiha va brend shriftlari (Inter, Montserrat, Onest, Oswald, Unbounded, Playfair Display, Caveat ...):
    font-family: "Inter" deb yozish kifoya.
  - CSS o'zgaruvchilari: var(--accent) brend rangi, var(--W), var(--H) kadr o'lchami (px).
  - Fon standart holatda shaffof. Internetdan hech narsa yuklanmaydi (rasm, shrift lokal bo'lsin).

Brauzer: kompyuterdagi Edge yoki Chrome ishlatiladi (alohida o'rnatish kerak emas).
Animatsiya (harakatli HTML) bu yerda yo'q: bitta kadr olinadi. Harakatni videoda `anim` beradi.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageFont

import common as C

FONT_EXTS = {".ttf", ".otf"}


def find_browser() -> str:
    """Edge yoki Chrome yo'lini topadi. MONTAJ_BROWSER muhit o'zgaruvchisi bilan almashtirsa bo'ladi."""
    env = os.environ.get("MONTAJ_BROWSER", "").strip().strip('"')
    if env:
        if Path(env).is_file():
            return env
        raise C.MontajError(f"MONTAJ_BROWSER da ko'rsatilgan brauzer topilmadi: {env}")
    candidates = []
    if os.name == "nt":
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        for root in filter(None, roots):
            candidates += [Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                           Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"]
    elif sys.platform == "darwin":
        candidates += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                       Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    else:
        candidates += [Path("/opt/pw-browsers/chromium")]
    for c in candidates:
        if c.is_file():
            return str(c)
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    raise C.MontajError("Brauzer topilmadi: Microsoft Edge yoki Google Chrome kerak "
                        "(yoki MONTAJ_BROWSER muhit o'zgaruvchisida to'liq yo'lini ko'rsating).")


def font_faces(style: dict) -> str:
    """Loyiha va brend shriftlari uchun @font-face qoidalari."""
    dirs = []
    bdir = C.brand_dir(style)
    if bdir:
        dirs.append(bdir / "fonts")
    dirs.append(C.ROOT / style.get("subtitles", {}).get("fonts_dir", "style/fonts"))
    rules, seen = [], set()
    for folder in dirs:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in FONT_EXTS:
                continue
            try:
                family, sub = ImageFont.truetype(str(path), 20).getname()
            except Exception:
                continue
            italic = "italic" in (sub or "").lower() or "italic" in path.stem.lower()
            key = (family, italic)
            if key in seen:
                continue
            seen.add(key)
            rules.append(f'@font-face{{font-family:"{family}";src:url("{path.resolve().as_uri()}");'
                         f'font-weight:100 900;font-style:{"italic" if italic else "normal"};}}')
    return "\n".join(rules)


def prepare(html_path: Path, style: dict, width: int, height: int, transparent: bool) -> Path:
    """Sahifaga shrift va o'zgaruvchilarni qo'shib, temp/ ichiga vaqtinchalik nusxa yozadi."""
    raw = html_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise C.MontajError(f"HTML fayl UTF-8 emas: {html_path}") from None
    accent = str(style.get("captions", {}).get("accent", "#FFE600"))
    inject = (f'<base href="{html_path.parent.resolve().as_uri()}/">\n<style>\n{font_faces(style)}\n'
              f':root{{--accent:{accent};--W:{width}px;--H:{height}px;}}\n'
              f'html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;'
              f'background:{"transparent" if transparent else "#000"};}}\n</style>\n')
    low = text.lower()
    pos = low.find("<head")
    if pos >= 0:
        pos = low.find(">", pos) + 1
        text = text[:pos] + "\n" + inject + text[pos:]
    else:
        text = "<!doctype html><html><head><meta charset=\"utf-8\">\n" + inject + "</head><body>" + text + "</body></html>"
    work = C.TEMP_DIR / ".html_render"
    work.mkdir(parents=True, exist_ok=True)
    out = work / (hashlib.md5(str(html_path.resolve()).encode("utf-8")).hexdigest()[:12] + ".html")
    out.write_text(text, encoding="utf-8")
    return out


def render(html_path: str | Path, out_path: str | Path, style: dict | None = None, size: tuple | None = None,
           transparent: bool = True, trim: bool = False, wait_ms: int = 1200, network: bool = False) -> dict:
    """Sahifani rasmga aylantiradi. Qaytaradi: {"output", "width", "height", "browser"}."""
    html_path = C.need_file(html_path, "HTML fayl")
    style = style or C.load_style()
    width, height = size or (int(style["video"]["width"]), int(style["video"]["height"]))
    out_path = Path(out_path)
    C.guard_output(out_path)
    if out_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise C.MontajError("Natija .png yoki .jpg bo'lishi kerak.")
    browser = find_browser()
    page = prepare(html_path, style, width, height, transparent)
    shot = page.with_suffix(".png")
    shot.unlink(missing_ok=True)
    profile = C.TEMP_DIR / ".html_render" / "profile"      # foydalanuvchining ochiq brauzeriga tegmaslik uchun alohida
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
           "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
           "--disable-background-networking", "--force-device-scale-factor=1",
           f"--window-size={width},{height}", f"--user-data-dir={profile}",
           f"--virtual-time-budget={int(wait_ms)}", f"--screenshot={shot}"]
    if transparent:
        cmd.append("--default-background-color=00000000")
    if not network:
        cmd.append("--host-resolver-rules=MAP * ~NOTFOUND")   # tashqi manzillarga chiqmaydi
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.append("--no-sandbox")
    cmd.append(page.as_uri())
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        raise C.MontajError("Brauzer 120 soniyada javob bermadi (sahifa juda og'ir yoki brauzer osilib qoldi).") from None
    # Edge qaytganidan keyin PNG yana ~1.5 s yozilishi mumkin. Hajmi
    # 0.5 s o'zgarmaguncha kutamiz; 10 s sekin kompyuter uchun zaxira.
    deadline = time.monotonic() + 10.0
    last_size = -1
    stable_since = time.monotonic()
    shot_ready = False
    while time.monotonic() < deadline:
        now = time.monotonic()
        try:
            size = shot.stat().st_size if shot.is_file() else 0
        except OSError:
            size = 0
        if size != last_size:
            last_size = size
            stable_since = now
        elif size >= 100 and now - stable_since >= 0.5:
            shot_ready = True
            break
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    if not shot_ready:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-6:])
        raise C.MontajError(f"Brauzer rasm chiqarmadi (kod {proc.returncode}). Brauzer: {browser}\n{tail}")
    try:
        img = Image.open(shot).convert("RGBA")
    except Exception as exc:
        raise C.MontajError(f"Brauzer chiqargan rasmni ochib bo'lmadi: {exc}") from exc
    if img.size != (width, height):
        C.warn(f"Brauzer {img.size[0]}x{img.size[1]} rasm berdi (so'ralgan {width}x{height}): o'lcham to'g'rilandi.")
        fixed = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        fixed.alpha_composite(img.crop((0, 0, min(width, img.width), min(height, img.height))))
        img = fixed
    if trim:
        box = img.getchannel("A").getbbox()
        if box is None:
            raise C.MontajError("Sahifa bo'sh chiqdi (hech narsa chizilmagan): HTML ni tekshiring.")
        pad = 4
        img = img.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(width, box[2] + pad), min(height, box[3] + pad)))
    elif transparent and img.getchannel("A").getbbox() is None:
        raise C.MontajError("Sahifa bo'sh chiqdi (hech narsa chizilmagan): HTML ni tekshiring.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        img.save(out_path)
    else:
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.getchannel("A"))
        bg.save(out_path, quality=93)
    shot.unlink(missing_ok=True)
    page.unlink(missing_ok=True)
    return {"output": str(out_path), "width": img.width, "height": img.height, "browser": browser}


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML/CSS/SVG sahifani PNG rasmga aylantiradi.")
    ap.add_argument("html", help="HTML fayl (masalan temp/video/gfx/karta.html)")
    ap.add_argument("-o", "--output", required=True, help="Natija rasm (.png shaffof, .jpg fonli)")
    ap.add_argument("--size", help="Sahifa o'lchami, masalan 1080x1920 (standart: style.json dagi video o'lchami)")
    ap.add_argument("--brand", help="Brend nomi (shrift va rang shundan olinadi)")
    ap.add_argument("--trim", action="store_true", help="Bo'sh (shaffof) chetlarni kesib tashla")
    ap.add_argument("--opaque", action="store_true", help="Shaffof emas, qora fon bilan")
    ap.add_argument("--wait", type=int, default=1200, help="Sahifa tayyor bo'lishini kutish, ms (standart 1200)")
    ap.add_argument("--allow-network", action="store_true", help="Sahifaga internetdan fayl yuklashga ruxsat")
    args = ap.parse_args()
    size = None
    if args.size:
        try:
            w, h = (int(x) for x in args.size.lower().split("x"))
            if not (16 <= w <= 8000 and 16 <= h <= 8000):
                raise ValueError
            size = (w, h)
        except ValueError:
            raise C.MontajError("--size 1080x1920 ko'rinishida bo'lishi kerak.") from None
    res = render(args.html, args.output, C.load_style(brand=args.brand), size, not args.opaque, args.trim,
                 args.wait, args.allow_network)
    C.info(f"TAYYOR: {res['output']} ({res['width']}x{res['height']})")
    return 0


if __name__ == "__main__":
    C.run_main(main)
