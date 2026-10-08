"""Ikkala agent uchun: namuna taqqoslash, preflight, urg'u, muqova va matn navbati."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
import common as C
import elements as E
import motion as M
from motion import cv2


def destination(path, source=None, final=False) -> Path:
    path = Path(path).resolve()
    folders = (C.OUTPUT_DIR,) if final else (C.TEMP_DIR, C.OUTPUT_DIR)
    if not any(C.is_inside(path, folder) for folder in folders):
        raise C.MontajError("Yangi natija faqat temp/ yoki output/ ichiga yoziladi.")
    sources = (source,) if isinstance(source, (str, Path)) else (source or ())
    for original in sources:
        if path == Path(original).resolve():
            raise C.MontajError(f"Natija manba faylini almashtira olmaydi: {path}")
    return C.guard_output(path)


def load_elements(path) -> list:
    if path is None:
        return []
    data = C.read_json(path)
    data = data.get("elements") if isinstance(data, dict) else data
    if not isinstance(data, list):
        raise C.MontajError("elements ro'yxat bo'lishi kerak.")
    return data


def preflight(style: dict, cues: list, elements: list, duration: float, validate_layers=True) -> dict:
    cfg = style.get("quality", {})
    errors, warnings, events, accents = [], [], [0.0, duration], []
    def warning(code, text):
        warnings.append({"code": code, "text": text})
    colored = {"accent", "big_accent", "huge", "mark", "mark2"}
    ctx = E.Ctx(style, C.brand_dir(style))
    def color_groups(tokens, preset=None, cue=False):
        cfg = ctx.caption_cfg({"preset": preset} if preset else None)
        # Cue-specific presets override global layout settings in CaptionLayer.
        if cue and preset and preset != style.get("captions", {}).get("preset", "clean"):
            cfg.update(E.CAPTION_PRESETS[preset])
        levels = [level for _, level, _ in tokens]
        if cfg.get("auto_numbers") and levels and all(level == "normal" for level in levels):
            for i, (word, _, _) in enumerate(tokens):
                if any(char.isdigit() for char in word):
                    levels[i] = "big_accent"
                    if len(word.strip("%+-")) <= 3 and i+1 < len(tokens) and len(tokens[i+1][0]) <= 6:
                        levels[i+1] = "big_accent"
                    break
        flags = [level in colored or (level == "big" and cfg.get("big_accent")) for level in levels]
        return sum(flag and (i == 0 or not flags[i-1]) for i, flag in enumerate(flags))
    hook = follow = False
    accent_cues = 0
    for n, cue in enumerate(cues, 1):
        try:
            start, end = float(cue["start"]), float(cue["end"])
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration + 0.05):
                raise ValueError("vaqt video chegarasidan tashqarida")
            preset, _, text = E.split_cue_tag(str(cue["text"]))
            if preset and preset not in E.CAPTION_PRESETS:
                raise ValueError(f"noma'lum preset: {preset}")
            tokens = E.parse_markup(text)
            hero = any(level in ("big", "big_accent", "huge") for _, level, _ in tokens)
            if start <= float(cfg.get("hook_sec", 1.5)) and (preset in ("caps", "heavy") or hero):
                hook = True
            if hero or preset in ("caps", "heavy", "marker"):
                events.append(start)
            groups = color_groups(tokens, preset, cue=True)
            if groups:
                accent_cues += 1
                accents.append((start, end, f"subtitr {n}"))
            if groups > 1:
                warning("multiple_accents", f"{n}-subtitrda bir nechta rangli urg'u bor.")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{n}-subtitr: {error}")
    for n, el in enumerate(elements, 1):
        try:
            kind = el["type"]
            if kind not in set(E.ELEMENT_TYPES) | E.NON_LAYER_TYPES:
                raise ValueError(f"noma'lum type: {kind}")
            start = float(el.get("at", el.get("start", 0)))
            raw_end = float(el.get("end", duration))
            if kind in E.TIMED_TYPES and "at" in el:
                raw_end = start + float(el.get("duration", E.TIMED_TYPES[kind])) + (0.35 if kind == "burst" else 0)
            if kind == "sfx":
                raw_end = start + 0.001
            if not math.isfinite(raw_end):
                raise ValueError("end cheksiz/NaN")
            # The existing compositor explicitly clips element ends to the source duration.
            end = min(raw_end, duration)
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration + 0.05):
                raise ValueError("vaqt video chegarasidan tashqarida")
            if kind != "sfx":
                events.append(start)
            if kind == "follow" and end >= duration - float(cfg.get("ending_sec", 3.5)):
                follow = True
            for item in el.get("items", []):
                at = float(item.get("at", start))
                if not start <= at < end:
                    raise ValueError("items.at element oralig'ida emas")
                events.append(at)
            if kind in ("title", "text") and str(el.get("text", "")).strip() and start <= float(cfg.get("hook_sec", 1.5)):
                hook = True
            visual_accent = kind in ("stat", "follow", "phone", "profile") or (
                kind == "list" and el.get("numbered", True) and el.get("style", "badge") == "badge")
            if kind in ("title", "text", "callout", "handnote"):
                visual_accent = bool(color_groups(E.parse_markup(str(el.get("text", ""))), el.get("preset")))
            if visual_accent:
                accents.append((start, end, f"element {n}"))
            if "behind_person" in el and (not isinstance(el["behind_person"], bool) or kind not in ("text", "title")):
                raise ValueError("behind_person faqat text/title va true/false")
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{n}-element: {error}")
    if not hook:
        warning("hook_missing", "Birinchi 1.5 soniyada sarlavha/urg'uli ilmoq aniqlanmadi; mazmunini agent tekshiradi.")
    gap = float(cfg.get("max_event_gap", 4))
    times = sorted(set(t for t in events if 0 <= t <= duration))
    for a, b in zip(times, times[1:]):
        if b - a > gap + 0.05:
            warning("rhythm_gap", f"{a:.2f}-{b:.2f}s: {b-a:.1f}s yangi vizual hodisa yo'q; sokin sahna bo'lsa rejada izohlang.")
    ratio = accent_cues / len(cues) if cues else 0
    if ratio > float(cfg.get("max_accent_cue_ratio", 0.5)):
        warning("accent_density", f"Subtitrlarning {ratio:.0%} ida rangli urg'u bor; kamroq rangli urg'u ko'rib chiqing.")
    for i, (a, b, label) in enumerate(accents):
        for c, d, other in accents[i + 1:]:
            if min(b, d) - max(a, c) > 0.1:
                warning("accent_overlap", f"{max(a,c):.2f}s: {label} va {other} rangli urg'usi bir vaqtda.")
    endcard = style.get("endcard", {})
    if not follow and not (endcard.get("enabled") and (endcard.get("handle") or endcard.get("text"))):
        warning("ending_missing", "Oxirida follow yoki mazmunli endcard aniqlanmadi; brendsiz videoda CTAni foydalanuvchi belgilaydi.")
    if validate_layers and not errors:
        layers = []
        try:
            layers = E.build_elements(ctx, elements, duration)
            if cues:
                layers.append(E.CaptionLayer(ctx, cues, None, duration))
            for text in ctx.notes:
                warning("safe_zone", text)
        except C.MontajError as error:
            errors.append(str(error))
        finally:
            for layer in layers:
                layer.close()
    if any(isinstance(el, dict) and el.get("behind_person") for el in elements):
        import person_mask
        if not person_mask.verify():
            errors.append("behind_person uchun tasdiqlangan PPHumanSeg modeli kerak; o'zi yuklanmaydi.")
        if any(isinstance(el, dict) and el.get("type") in ("stage", "scene", "broll", "grade") for el in elements):
            errors.append("behind_person stage/scene/broll/grade bilan birga qo'llanmaydi.")
    return {"errors": errors, "warnings": warnings, "accent_cue_ratio": round(ratio, 3),
            "human_review_required": ["subtitr tasdiqi HOLAT.md da", "yuz va grafika", "mazmun", "harakat", "ovoz"],
            "structural_ok": not errors}


def suggestions(words: list, keywords: list) -> dict:
    # Proposals only: transcript and timings are never overwritten.
    corrections, skipped = [], []
    groups, current = [], []
    for i, word in enumerate(words):
        if current and (float(word["start"]) - float(words[current[-1]]["end"]) > 0.6 or len(current) >= 9):
            groups.append(current)
            current = []
        current.append(i)
        if re.search(r"[.!?]$", str(word["word"])):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    normalized = {keyword.casefold() for keyword in keywords}
    for group in groups:
        rows = [words[i] for i in group]
        if any(row.get("needs_review") or (isinstance(row.get("prob"), (int, float)) and row["prob"] < 0.5) for row in rows):
            skipped.append({"index": group[0] + 1, "reason": "ishonchi past; avval matnni tekshir"})
            continue
        if any(re.search(r"\*|!!|==|~~|^\{", str(row["word"])) for row in rows):
            continue
        chosen = next((i for i in group if re.search(r"\d", str(words[i]["word"]))), None)
        reason = "raqam"
        if chosen is None:
            chosen = next((i for i in group if str(words[i]["word"]).strip(".,!?;:").casefold() in normalized), None)
            reason = "agent bergan kalit so'z"
        if chosen is None:
            skipped.append({"index": group[0] + 1, "reason": "asosiy ma'noni agent tanlasin"})
            continue
        phrase = [chosen]
        if reason == "raqam" and chosen + 1 in group and re.match(r"(?i)^(oy|yil|kun|hafta|soat|foiz|million|ming|so.m|dollar)", str(words[chosen + 1]["word"])):
            phrase.append(chosen + 1)
        original = " ".join(str(words[i]["word"]) for i in phrase)
        corrections.append({"index": chosen + 1, "count": len(phrase), "was": original,
                            "text": f"*{original}*", "note": f"TAKLIF: {reason}; agent tekshirsin"})
    return {"corrections": corrections, "skipped": skipped, "automatic_approval": False}


def grab_rgb(video: Path, at: float, height=640) -> Image.Image:
    if video.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        with Image.open(video) as image:
            result = image.convert("RGB")
            result.thumbnail((height * 2, height))
            return result
    meta = C.ffprobe_info(video)
    if not 0 <= at < meta["duration"]:
        raise C.MontajError(f"Kadr vaqti chegaradan tashqarida: {at}, video {meta['duration']}s")
    proc = binary_run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{at:.5f}",
                  "-i", video, "-an", "-frames:v", "1", "-vf", f"scale=-2:{height}", "-f", "image2pipe", "-vcodec", "png", "-"])
    import io
    with Image.open(io.BytesIO(proc.stdout)) as image:
        return image.convert("RGB")


def binary_run(command):
    process = subprocess.run([str(part) for part in command], capture_output=True)
    if process.returncode:
        raise C.MontajError(process.stderr.decode("utf-8", "replace")[-1200:])
    return process


def metrics(image: Image.Image, box=None) -> dict:
    if box:
        image = image.crop(tuple(round(v * (image.width if i % 2 == 0 else image.height)) for i, v in enumerate(box)))
        if image.width < 1 or image.height < 1:
            raise C.MontajError("box kadrda bir pikseldan kichik; kattaroq hudud tanlang.")
    rgb = np.asarray(image)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    yellow = (hsv[..., 0] >= 18) & (hsv[..., 0] <= 38) & (hsv[..., 1] > 100) & (hsv[..., 2] > 120)
    return {"brightness": round(float(hsv[..., 2].mean()), 2),
            "saturation": round(float(hsv[..., 1].mean()), 2),
            "contrast": round(float(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).std()), 2),
            "yellow_pixel_ratio": round(float(yellow.mean()), 4),
            "box": box, "box_width": round(box[2]-box[0], 4) if box else None,
            "box_height": round(box[3]-box[1], 4) if box else None}


def compare(args) -> int:
    reference, ours = C.need_file(args.reference), C.need_file(args.ours)
    def duration(path):
        return 1.0 if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") else C.ffprobe_info(path)["duration"]
    times = parse_numbers(args.at) if args.at else [duration(ours) * (i + 0.5) / args.n for i in range(args.n)]
    refs = parse_numbers(args.reference_at) if args.reference_at else [t / duration(ours) * duration(reference) for t in times]
    if len(times) != len(refs) or not 1 <= len(times) <= 120:
        raise C.MontajError("Vaqtlar soni teng va 1..120 bo'lishi kerak.")
    box, ref_box = parse_box(args.box), parse_box(args.reference_box)
    sources = (reference, ours)
    out = destination(args.out or C.TEMP_DIR / "compare_samples" / (C.slugify(ours.stem) + "_" + C.slugify(reference.stem)) / "report.json", sources)
    if out.suffix.lower() != ".json":
        raise C.MontajError("Taqqoslash hisoboti .json bo'lishi kerak.")
    records = []
    pages, pairs = [], []
    viewer_path = destination(out.parent / "compare.html", sources)
    # Check every generated path before writing the first comparison frame.
    for i in range(len(times)):
        destination(out.parent / f"pair_{i+1:04d}.png", sources)
    for i in range((len(times)+3)//4):
        destination(out.parent / f"sheet_{i+1:03d}.jpg", sources)
    for i, (at, ref_at) in enumerate(zip(times, refs)):
        images = [grab_rgb(reference, ref_at), grab_rgb(ours, at)]
        canvas = Image.new("RGB", (744, 710), (20, 20, 24))
        draw = ImageDraw.Draw(canvas)
        for column, (image, label, roi) in enumerate(zip(images, (f"NAMUNA {ref_at:.3f}s", f"BIZNIKI {at:.3f}s"), (ref_box, box))):
            if roi:
                image = image.copy()
                ImageDraw.Draw(image).rectangle(tuple(v * (image.width if j % 2 == 0 else image.height) for j, v in enumerate(roi)), outline="#00FFFF", width=2)
            image.thumbnail((360, 640))
            x = 8 + column * 372 + (360-image.width)//2
            canvas.paste(image, (x, 40))
            draw.text((8 + column * 372, 10), label, fill="white")
        pair = out.parent / f"pair_{i+1:04d}.png"
        canvas.save(destination(pair, sources))
        pairs.append(canvas)
        records.append({"ours_at": at, "reference_at": ref_at, "image": pair.name,
                        "reference": metrics(images[0], ref_box), "ours": metrics(images[1], box)})
        if len(pairs) == 4 or i == len(times)-1:
            page = Image.new("RGB", (744 * 2, 710 * 2), (20, 20, 24))
            for j, pair_image in enumerate(pairs):
                page.paste(pair_image, ((j % 2) * 744, (j // 2) * 710))
            sheet = out.parent / f"sheet_{len(pages)+1:03d}.jpg"
            page.save(destination(sheet, sources), quality=90)
            pages.append(str(sheet))
            pairs = []
    report = {"reference": str(reference), "ours": str(ours), "frames": records, "sheets": pages,
              "note": "Rang piksellari matnni avtomatik tanimaydi; box agent o'lchagan hudud. Avto uslub/did balli yo'q."}
    C.write_json(report, out)
    payload = json.dumps(records, ensure_ascii=False).replace("<", "\\u003c")
    viewer = '<!doctype html><meta charset="utf-8"><title>Namuna taqqoslash</title><style>body{background:#15151a;color:white;font:16px system-ui;margin:20px}img{max-height:80vh;max-width:100%}input{width:90%}</style>'
    viewer += f'<h1>{html.escape(reference.name)} / {html.escape(ours.name)}</h1><input id="seek" type="range" min="0" max="{len(records)-1}" value="0"><p id="label"></p><img id="pair"><pre id="stats"></pre>'
    viewer += f'<script>const rows={payload};function show(){{const r=rows[seek.value];pair.src=r.image;label.textContent=`Namuna ${{r.reference_at.toFixed(3)}}s / Bizniki ${{r.ours_at.toFixed(3)}}s`;stats.textContent=JSON.stringify({{namuna:r.reference,bizniki:r.ours}},null,2)}}seek.oninput=show;show();</script>'
    viewer_path.write_text(viewer, encoding="utf-8")
    C.info(f"TAQQOSLASH: {out}; {out.parent / 'compare.html'}; {len(records)} kadr")
    return 0


def parse_numbers(text):
    try:
        values = [float(value) for value in text.split(",")]
    except ValueError:
        raise C.MontajError("Vergul bilan ajratilgan sonlar kerak.") from None
    if not all(math.isfinite(value) for value in values):
        raise C.MontajError("NaN/Infinity qabul qilinmaydi.")
    return values


def parse_box(text):
    if text is None:
        return None
    box = parse_numbers(text)
    if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
        raise C.MontajError("box: x0,y0,x1,y1, 0..1 va ijobiy o'lcham.")
    return box


def cover(args) -> int:
    import compose
    import face
    video = C.need_file(args.video)
    style = C.load_style(args.style, args.brand)
    meta = C.ffprobe_info(video)
    if not 0 <= args.at < meta["duration"]:
        raise C.MontajError("--at video oralig'ida bo'lishi kerak.")
    graph, _ = compose.fit_graph(meta, style, face.detect(video, quiet=True), C.brand_dir(style))
    W, H = int(style["video"]["width"]), int(style["video"]["height"])
    proc = binary_run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", str(args.at),
                  "-i", video, "-filter_complex", graph, "-map", "[fit]", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    if len(proc.stdout) != W * H * 3:
        raise C.MontajError("Muqova kadri to'liq olinmadi.")
    pixels = np.frombuffer(proc.stdout, np.uint8).reshape(H, W, 3).copy()
    fade = np.linspace(0.05, 0.8, H, dtype=np.float32)[:, None, None]
    image = Image.fromarray((pixels * (1-fade)).astype(np.uint8))
    ctx = E.Ctx(style, C.brand_dir(style))
    cfg = ctx.caption_cfg()
    title = E.fix_apostrophes(args.title.strip())
    if not title:
        raise C.MontajError("Muqova sarlavhasi bo'sh bo'lmasin.")
    available = W * (1 - ctx.safe["left"] - ctx.safe["right"] - 0.04)
    size, lines = H * 0.065, []
    while size >= H * 0.018:
        font = ctx.fonts.get(cfg["font"], size, 800)
        lines = []
        for word in title.split():
            if lines and font.getlength(lines[-1] + " " + word) <= available:
                lines[-1] += " " + word
            else:
                lines.append(word)
        if len(lines) <= 4 and max(font.getlength(line) for line in lines) <= available:
            break
        size *= 0.92
    else:
        raise C.MontajError("Muqova sarlavhasi juda uzun; qisqartiring.")
    draw = ImageDraw.Draw(image)
    cx = W * (ctx.safe["left"] + (1 - ctx.safe["left"] - ctx.safe["right"]) / 2)
    bottom = H * (1 - ctx.safe["bottom"] - 0.035)
    line_h = size * 1.2
    top = bottom - len(lines) * line_h
    for i, line in enumerate(lines):
        M.draw_text(draw,(cx, top + i * line_h), line, anchor="mt", font=font, fill=cfg["color"],
                  stroke_width=max(1, int(H/640)), stroke_fill="#101014")
    draw.rounded_rectangle((cx-available/2, top-size*.45, cx-available/2+available*.3, top-size*.38),
                           radius=max(1, size*.03), fill=cfg["accent"])
    logo = style.get("logo", {}).get("file")
    if logo:
        with Image.open(ctx.asset(logo)) as source:
            badge = source.convert("RGBA")
        badge.thumbnail((int(W*.25), int(H*.09)))
        image.paste(badge, (int(W*ctx.safe["left"]), int(H*ctx.safe["top"])), badge)
    folder = C.OUTPUT_DIR / style["_brand"] if style.get("_brand") else C.OUTPUT_DIR
    out = destination(args.out or folder / (C.output_stem(video.stem)+"_cover.png"), video)
    if out.suffix.lower() != ".png":
        raise C.MontajError("Muqova natijasi .png bo'lishi kerak.")
    image.save(out)
    C.info(f"MUQOVA: {out}")
    return 0


def batch(args) -> int:
    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        raise C.MontajError(f"Papka topilmadi: {folder}")
    videos = sorted(path.resolve() for path in folder.iterdir() if path.is_file() and path.suffix.lower() in C.VIDEO_EXTS)
    if not videos:
        raise C.MontajError("Papkada video yo'q.")
    names = [C.slugify(video.stem) for video in videos]
    if len(names) != len(set(names)):
        raise C.MontajError("Bir xil ish nomiga tushadigan videolar bor; alohida papka/nom tanlang.")
    report_path = destination(args.out or C.TEMP_DIR / "batch" / (C.slugify(folder.name)+".json"), videos)
    if report_path.suffix.lower() != ".json":
        raise C.MontajError("Navbat hisoboti .json bo'lishi kerak.")
    style = C.load_style(args.style, args.brand)
    config_hash = hashlib.sha256(json.dumps(style, sort_keys=True).encode()).hexdigest()
    previous = C.read_json(report_path).get("jobs", []) if args.resume and report_path.exists() else []
    prior = {item["video"]: item for item in previous}
    rows = []
    for video in videos:
        st = video.stat()
        fingerprint = [st.st_size, st.st_mtime_ns, config_hash, args.no_cut]
        old = prior.get(str(video), {})
        work = C.TEMP_DIR / C.slugify(video.stem)
        if (work / "job.json").is_file():
            recorded = C.read_json(work / "job.json").get("fingerprint", {}).get("input")
            if recorded and Path(recorded).resolve() != video:
                raise C.MontajError(f"{video.name}: temp ish papkasi boshqa manbaga tegishli; alohida nom kerak.")
        if old.get("fingerprint") == fingerprint and old.get("status") == "need_approval" and (work / "subs.srt").is_file():
            rows.append(old)
            C.info(f"NAVBAT: tayyor matn saqlandi: {video.name}")
            continue
        command = [sys.executable, str(C.ROOT / "scripts/pipeline.py"), str(video), "--prepare-only"]
        if args.brand:
            command += ["--brand", args.brand]
        if args.style:
            command += ["--style", args.style]
        if args.no_cut:
            command += ["--no-cut"]
        C.info(f"NAVBAT: {video.name}")
        log = destination(report_path.parent / (C.slugify(video.stem)+".log"))
        with log.open("w", encoding="utf-8") as output:
            run = subprocess.run(command, cwd=C.ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        code = run.returncode
        status = "need_approval" if code == 3 else "prepared_no_speech" if code == 0 else "need_download" if code == 4 else "error"
        rows.append({"video": str(video), "fingerprint": fingerprint, "status": status, "code": code,
                     "subs": str(work / "subs.srt") if (work / "subs.srt").exists() else None, "log": str(log)})
        C.write_json({"jobs": rows, "rendered": False, "remaining": len(videos)-len(rows)}, report_path)
        if code not in (0, 3):
            C.info(f"NAVBAT TO'XTADI: {status}; log: {log}")
            return code
    C.write_json({"jobs": rows, "rendered": False, "remaining": 0}, report_path)
    C.info(f"NAVBAT TAYYOR: {len(rows)} video, subtitr tasdiqi alohida; {report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("compare", help="Video/rasmlarni yonma-yon, aniq kadr vaqtlarida taqqoslash")
    p.add_argument("reference"); p.add_argument("ours")
    p.add_argument("--at"); p.add_argument("--reference-at")
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--box", help="Bizniki matn hududi: x0,y0,x1,y1, 0..1")
    p.add_argument("--reference-box", help="Namuna matn hududi: x0,y0,x1,y1, 0..1")
    p.add_argument("--out", help="JSON hisobot; yonida HTML, juft kadrlar va sheets")
    p = sub.add_parser("preflight", help="Renderdan oldin tuzilish va namuna qoidalarini tekshirish")
    p.add_argument("video"); p.add_argument("--subs"); p.add_argument("--elements")
    p.add_argument("--brand"); p.add_argument("--style"); p.add_argument("--out")
    p = sub.add_parser("suggest", help="Urg'u takliflarini alohida JSONga chiqarish (avtomatik qo'llamaydi)")
    p.add_argument("words"); p.add_argument("--keyword", action="append", default=[])
    p.add_argument("--out")
    p = sub.add_parser("cover", help="Video kadridan brend uslubida PNG muqova")
    p.add_argument("video"); p.add_argument("--title", required=True); p.add_argument("--at", type=float, default=0)
    p.add_argument("--brand"); p.add_argument("--style"); p.add_argument("--out")
    p = sub.add_parser("batch", help="Papkadagi videolarni ketma-ket faqat matn bosqichigacha tayyorlash")
    p.add_argument("folder"); p.add_argument("--brand"); p.add_argument("--style"); p.add_argument("--out")
    p.add_argument("--no-cut", action="store_true"); p.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.action == "compare":
        if not 1 <= args.n <= 120:
            raise C.MontajError("--n: 1..120")
        return compare(args)
    if args.action == "cover":
        C.busy_acquire("muqova")
        return cover(args)
    if args.action == "batch":
        return batch(args)
    if args.action == "suggest":
        import apply_corrections
        source = C.need_file(args.words)
        data = apply_corrections.load_words(source)
        proposal = suggestions(data["words"], args.keyword)
        # Metadata lives beside a strict corrections file, so apply_corrections can read the proposal.
        out = destination(args.out or source.with_name("emphasis.suggested.json"), source)
        C.write_json({"corrections": proposal["corrections"]}, out)
        C.write_json({"skipped": proposal["skipped"], "automatic_approval": False}, destination(out.with_suffix(".review.json"), source))
        C.info(f"URG'U TAKLIFI: {out}; {len(proposal['corrections'])} ibora; agent tekshirgach qo'llaydi.")
        return 0
    video = C.need_file(args.video)
    report = preflight(C.load_style(args.style, args.brand), C.parse_srt(args.subs) if args.subs else [],
                       load_elements(args.elements), C.ffprobe_info(video)["duration"])
    sources = [video, *(Path(path) for path in (args.subs, args.elements) if path)]
    out = destination(args.out or C.job_dir(video) / "preflight.json", sources)
    if out.suffix.lower() != ".json":
        raise C.MontajError("Preflight hisoboti .json bo'lishi kerak.")
    C.write_json(report, out)
    for error in report["errors"]:
        C.info(f"[XATO] {error}")
    for warning in report["warnings"]:
        C.warn(warning["text"])
    C.info(f"PREFLIGHT: {len(report['errors'])} xato, {len(report['warnings'])} ogohlantirish; {out}")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    C.run_main(main)
