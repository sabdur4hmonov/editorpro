"""Rasmdan fonni olib tashlaydi: faqat narsaning o'zi shaffof fonda (stiker kabi) PNG bo'lib qoladi.

    python scripts/cutout.py temp/video/images/oksimetr.jpg
    python scripts/cutout.py temp/video/images/*.jpg --sheet temp/video/cutouts.jpg

Natija: <nom>.cut.png (asl fayl yonida). Asl rasmning <fayl>.credit.json manbasi natija yoniga
ko'chiriladi (render oxirida "Rasm manbalari" to'g'ri chiqishi uchun).
--sheet: har kesilgan rasm katak (shaffof) va to'q ko'k fonda ko'rsatiladi: fon qoldig'i va chetdagi
"halo" shu varaqda ko'rib tekshiriladi.

Modellar (rembg, birinchi ishlatishda ~/.rembg/models ga yuklanadi):
  isnet-general-use (standart, Apache-2.0, ~170 MB) - och fondagi och narsa (qo'l, teri) ham butun qoladi;
  birefnet-general (MIT, ~1 GB) - ba'zi rasmlarda chetlari aniqroq, lekin och terini fon deb o'chirishi mumkin.
Har rasmni ikkala model bilan kesib (--suffix), varaqda solishtirib tanlang.
BRIA modellari (bria-rmbg) tijoratda ishlatib bo'lmaydi (CC BY-NC), shuning uchun rad etiladi.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import common as C

DEFAULT_MODEL = "isnet-general-use"
NON_COMMERCIAL = ("bria",)


def session(model: str, device: str = 'auto'):
    if any(model.startswith(bad) for bad in NON_COMMERCIAL):
        raise C.MontajError(f"{model}: litsenziyasi tijoratga ruxsat bermaydi (BRIA, CC BY-NC). "
                            f"{DEFAULT_MODEL} ishlating.")
    try:
        from rembg import new_session
    except ImportError as exc:
        raise C.MontajError("rembg o'rnatilmagan: .venv\\Scripts\\python.exe -m pip install \"rembg[cpu]\"") from exc
    import hardware
    providers=hardware.onnx_providers(device)
    try:
        return new_session(model,providers=providers)
    except Exception as error:
        if providers[0]=='CPUExecutionProvider': raise
        C.warn(f'rembg CUDA init failed; CPU fallback: {error}')
        return new_session(model,providers=['CPUExecutionProvider'])


def clean_alpha(img: Image.Image, floor: int = 12, erode: int = 1) -> Image.Image:
    """Chetdagi xira qoldiqni tozalaydi: juda past alfa 0 bo'ladi, chet 1 px ichkariga suriladi."""
    import cv2

    rgba = np.array(img.convert("RGBA"))
    a = rgba[..., 3]
    a[a < floor] = 0
    if erode > 0:
        hard = (a > 127).astype(np.uint8)
        inner = cv2.erode(hard, np.ones((3, 3), np.uint8), iterations=erode)
        # faqat qattiq chetni yeyamiz, yumshoq (soch, shisha) o'tishlar qoladi
        a = np.where((hard == 1) & (inner == 0), (a.astype(np.float32) * 0.55).astype(np.uint8), a)
    rgba[..., 3] = a
    return Image.fromarray(rgba, "RGBA")


def trim(img: Image.Image, pad: int = 6) -> Image.Image:
    box = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        raise C.MontajError("Kesilgan rasm bo'm-bo'sh chiqdi: model narsani topmadi (boshqa rasm tanlang).")
    x0, y0, x1, y1 = box
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))


def cut(src: Path, sess, out: Path | None = None, max_side: int = 1600, suffix: str = "cut") -> Path:
    from rembg import remove

    img = Image.open(src).convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    try:
        res = remove(img, session=sess, post_process_mask=True)
    except Exception as error:
        if 'CUDAExecutionProvider' not in sess.inner_session.get_providers(): raise
        C.warn(f'rembg CUDA inference failed; CPU fallback: {error}')
        sess.inner_session.set_providers(['CPUExecutionProvider'])
        res = remove(img, session=sess, post_process_mask=True)
    res = trim(clean_alpha(res))
    out = out or src.with_name(f"{src.stem}.{suffix}.png")
    res.save(out)
    credit = src.with_name(src.name + ".credit.json")
    if credit.is_file():
        data = json.loads(credit.read_text(encoding="utf-8"))
        data["edit"] = "fon olib tashlangan (rembg/BiRefNet)"
        out.with_name(out.name + ".credit.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def sheet(paths: list, dest: Path, cell: int = 360) -> Path:
    """Har rasm ikki marta: katak fonda (shaffoflik) va to'q ko'k fonda (video ustidagi ko'rinish)."""
    cols = 2
    canvas = Image.new("RGB", (cell * cols * 2, cell * ((len(paths) + cols - 1) // cols)), (20, 20, 24))
    for i, p in enumerate(paths):
        img = Image.open(p).convert("RGBA")
        img.thumbnail((cell - 20, cell - 40), Image.LANCZOS)
        for k, bg in enumerate(("check", (25, 32, 70))):
            tile = Image.new("RGB", (cell, cell), (255, 255, 255) if bg == "check" else bg)
            if bg == "check":
                d = ImageDraw.Draw(tile)
                for yy in range(0, cell, 20):
                    for xx in range(0, cell, 20):
                        if (xx // 20 + yy // 20) % 2:
                            d.rectangle([xx, yy, xx + 19, yy + 19], fill=(200, 200, 200))
            tile.paste(img, ((cell - img.width) // 2, (cell - img.height) // 2 + 10), img)
            ImageDraw.Draw(tile).text((8, 6), Path(p).stem, fill=(255, 80, 80))
            canvas.paste(tile, ((i % cols) * cell * 2 + k * cell, (i // cols) * cell))
    canvas.save(dest, quality=90)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Rasmdan fonni olib tashlaydi (shaffof PNG).")
    ap.add_argument("images", nargs="+", help="Rasm fayllari (jpg/png)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"rembg modeli (standart {DEFAULT_MODEL})")
    ap.add_argument('--device',choices=('auto','cpu','cuda'),default='auto',help='ONNX provider; unavailable CUDA falls back to CPU')
    ap.add_argument("--sheet", help="Tekshirish varag'i (jpg)")
    ap.add_argument("--suffix", default="cut", help="Natija nomi: <nom>.<suffix>.png (ikki modelni solishtirish uchun)")
    args = ap.parse_args()
    sess = session(args.model,args.device)
    outs = []
    for name in args.images:
        src = C.need_file(name, "Rasm")
        out = cut(src, sess, suffix=args.suffix)
        C.info(f"  {src} -> {out}")
        outs.append(out)
    if args.sheet:
        C.info(f"TEKSHIRISH VARAG'I: {sheet(outs, Path(args.sheet))}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
