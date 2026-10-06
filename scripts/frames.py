"""Videodan kadrlarni bitta rasmga terib beradi (natijani ko'z bilan tekshirish uchun).

    python scripts/frames.py output/video_final.mp4                 # 8 ta kadr, teng oraliqda
    python scripts/frames.py output/video_final.mp4 --n 12
    python scripts/frames.py output/video_final.mp4 --at 2.0,2.1,2.25   # aniq vaqtlar (animatsiyani tekshirish)

Natija (standart): temp/frames/<video nomi>.jpg. Video o'zgarmaydi.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import common as C


def grab(video: Path, t: float, out: Path, height: int) -> bool:
    proc = C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
                  "-ss", f"{max(0.0, t):.3f}", "-i", video, "-an", "-frames:v", "1",
                  "-vf", f"scale=-2:{height}", "-q:v", "3", out], check=False)
    return proc.returncode == 0 and out.is_file() and out.stat().st_size > 0


def sheet(video: str | Path, out: str | Path | None = None, n: int = 8, times: list | None = None,
          height: int = 640) -> dict:
    video = C.need_file(video, "Video")
    meta = C.ffprobe_info(video)
    if not meta["has_video"]:
        raise C.MontajError(f"Faylda video oqimi yo'q: {video}")
    dur = max(0.1, meta["duration"])
    if times:
        times = [min(max(0.0, float(t)), max(0.0, dur - 0.05)) for t in times]
    else:
        times = [dur * (i + 0.5) / n for i in range(n)]
    out = Path(out) if out else C.TEMP_DIR / "frames" / f"{C.slugify(video.stem)}.jpg"
    C.guard_output(out, video)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".{out.stem}_frames"
    work.mkdir(parents=True, exist_ok=True)
    shots = []
    for i, t in enumerate(times):
        f = work / f"{i:02d}.jpg"
        if grab(video, t, f, height):
            shots.append((t, f))
    if not shots:
        raise C.MontajError("Videodan kadr olib bo'lmadi.")
    try:
        font = ImageFont.truetype(str(C.ROOT / "style" / "fonts" / "Inter.ttf"), 22)
    except OSError:
        font = ImageFont.load_default()
    imgs = [(t, Image.open(f).convert("RGB")) for t, f in shots]
    cols = min(len(imgs), 6 if len(imgs) > 8 else 4)
    rows = (len(imgs) + cols - 1) // cols
    cw, ch, pad = imgs[0][1].width, imgs[0][1].height, 8
    canvas = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad) + pad), (16, 16, 18))
    draw = ImageDraw.Draw(canvas)
    for i, (t, im) in enumerate(imgs):
        x, y = pad + (i % cols) * (cw + pad), pad + (i // cols) * (ch + pad)
        canvas.paste(im.resize((cw, ch)), (x, y))
        label = f"{t:.2f}s"
        draw.rectangle([x, y, x + draw.textlength(label, font=font) + 14, y + 32], fill=(0, 0, 0))
        draw.text((x + 7, y + 3), label, font=font, fill=(255, 255, 255))
    canvas.save(out, quality=88)
    for _, f in shots:
        f.unlink(missing_ok=True)
    try:
        work.rmdir()
    except OSError:
        pass
    return {"output": str(out), "count": len(imgs), "duration": dur}


def main() -> int:
    ap = argparse.ArgumentParser(description="Videodan kadrlar varag'i (tekshirish uchun).")
    ap.add_argument("video")
    ap.add_argument("-o", "--output", help="Natija rasm (standart: temp/frames/<nom>.jpg)")
    ap.add_argument("--n", type=int, default=8, help="Nechta kadr (standart 8)")
    ap.add_argument("--at", help="Aniq vaqtlar, vergul bilan: 2.0,2.1,2.25")
    ap.add_argument("--height", type=int, default=640, help="Har kadr balandligi, piksel")
    args = ap.parse_args()
    if not 1 <= args.n <= 24:
        raise C.MontajError("--n 1 dan 24 gacha bo'lishi kerak.")
    times = None
    if args.at:
        try:
            times = [float(x) for x in args.at.split(",") if x.strip()]
        except ValueError:
            raise C.MontajError("--at uchun sonlar kerak, masalan: 2.0,2.1,2.25") from None
        if not 1 <= len(times) <= 24:
            raise C.MontajError("--at da 1 dan 24 tagacha vaqt bo'lishi kerak.")
    res = sheet(args.video, args.output, args.n, times, args.height)
    C.info(f"RASM TAYYOR ({res['count']} kadr, video {res['duration']:.1f}s): {res['output']}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
