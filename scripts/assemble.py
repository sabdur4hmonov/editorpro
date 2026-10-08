"""Ko'p klipli montaj: tartiblangan klip ro'yxatidan bitta asosiy video yig'adi (restoran promo kabi).

    python scripts/assemble.py input/promo                 # papka: klip ro'yxati shablonini yaratadi va yig'adi
    python scripts/assemble.py input/promo/clips.json      # tayyor ro'yxat (yoki temp/<nom>/clips.json)
    python scripts/pipeline.py input/promo --style ...     # pipeline ham papka/ro'yxat qabul qiladi

Ro'yxat (clips.json), kliplar shu tartibda ketma-ket qo'yiladi:
    {"name": "restoran_promo", "product_audio": "keep",
     "clips": [
       {"file": "input/promo/01_oshpaz.mp4", "role": "speech"},
       {"file": "input/promo/02_qovurga.mp4", "role": "product", "in": 0.5, "out": 2.0},
       {"file": "input/promo/ovoz.m4a", "role": "voiceover",
        "cover": [{"file": "input/promo/05_salat.mp4", "in": 0, "out": 2.5}, {"file": "input/promo/06_xil.mp4"}]}
     ]}

role:
  speech     - gapiruvchi kadr: tasvir va ovoz; keyin odatdagidek transkripsiya va jimlik kesiladi.
  product    - nutqsiz kadr (taom, qadoqlash, joy): to'liq ekran, klipning o'z ovozi qoladi (standart
               product_audio "keep"; foydalanuvchi musiqa bersa "mute" yoki klipda "keep_audio": false).
               Bu oraliq jimlik deb KESILMAYDI (segments.json: protect).
  voiceover  - alohida yozilgan ovoz (audio fayl yoki video ovozi). Tasviri "cover" dagi mahsulot kliplari,
               ketma-ket; ovozdan qisqa bo'lsa oxirgi kadr ushlab turiladi, uzun bo'lsa kesiladi.
in/out (soniya) - klipning qaysi qismi olinadi; focus_x/focus_y (0..1) - 9:16 ga kesishda qaysi qism qoladi.

Har klip style.json dagi video.width x video.height, video.fps ga keltiriladi (60 fps HEVC 1440x2560 ham),
natija temp/<nom>/<nom>.mp4 va temp/<nom>/segments.json. Asl fayllar faqat o'qiladi.
Ro'yxat va fayllar o'zgarmasa qayta yig'ilmaydi.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import common as C

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".opus"}
ROLES = ("speech", "product", "voiceover")


def _resolve(value: str, base: Path) -> Path:
    p = Path(str(value))
    for cand in ([p] if p.is_absolute() else [base / p, C.ROOT / p]):
        if cand.is_file():
            return cand.resolve()
    raise C.MontajError(f"Klip topilmadi: {value}")


def template_for_folder(folder: Path) -> dict:
    """Papkadagi kliplardan ro'yxat shabloni: nom bo'yicha tartib, ovozi borlari speech, qolganlari product."""
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in C.VIDEO_EXTS | AUDIO_EXTS)
    if not files:
        raise C.MontajError(f"Papkada video yoki audio klip yo'q: {folder}")
    clips = []
    for p in files:
        if p.suffix.lower() in AUDIO_EXTS:
            clips.append({"file": str(p), "role": "voiceover", "cover": []})
            continue
        meta = C.ffprobe_info(p)
        clips.append({"file": str(p), "role": "speech" if meta["has_audio"] else "product"})
    return {"name": C.slugify(folder.name), "product_audio": "keep", "clips": clips}


def load_manifest(source: Path) -> tuple:
    """(ro'yxat, asos papka, ro'yxat fayli). Papka berilsa temp/<nom>/clips.json yaratiladi yoki o'qiladi."""
    if source.is_dir():
        inside = source / "clips.json"
        if inside.is_file():
            return C.read_json(inside, "Klip ro'yxati"), source, inside
        mpath = C.TEMP_DIR / C.slugify(source.name) / "clips.json"
        if not mpath.is_file():
            C.write_json(template_for_folder(source), mpath)
            C.info(f"Klip ro'yxati shabloni yaratildi: {mpath}\n  Tartib va rollarni tekshiring (speech/product/voiceover).")
        return C.read_json(mpath, "Klip ro'yxati"), source, mpath
    data = C.read_json(source, "Klip ro'yxati")
    return data, source.parent, source


def validate(data: dict, base: Path) -> list:
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        raise C.MontajError("clips.json: \"clips\" ro'yxati bo'sh yoki yo'q.")
    out = []
    for n, c in enumerate(clips, 1):
        role = c.get("role")
        if role not in ROLES:
            raise C.MontajError(f"clips.json: {n}-klip role noto'g'ri: {role!r}. Mumkin: {', '.join(ROLES)}")
        item = dict(c, path=_resolve(c.get("file", ""), base))
        item["cover_paths"] = [dict(cv, path=_resolve(cv.get("file", ""), base)) for cv in c.get("cover", []) or []]
        for key in ("in", "out"):
            if key in c and float(c[key]) < 0:
                raise C.MontajError(f"clips.json: {n}-klip {key} manfiy bo'lishi mumkin emas.")
        out.append(item)
    return out


def _fingerprint(data: dict, clips: list, style: dict) -> str:
    h = hashlib.sha1(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for c in clips:
        for p in [c["path"]] + [cv["path"] for cv in c["cover_paths"]]:
            st = p.stat()
            h.update(f"{p}|{st.st_size}|{int(st.st_mtime)}".encode("utf-8"))
    v = style["video"]
    h.update(f"{v['width']}x{v['height']}@{v['fps']}|{style['cut'].get('intermediate_crf', 16)}".encode("utf-8"))
    return h.hexdigest()


def _span(item: dict, meta: dict) -> tuple:
    start = float(item.get("in", 0.0))
    end = float(item.get("out", meta["duration"]))
    end = min(end, meta["duration"])
    if end - start < 0.1:
        raise C.MontajError(f"Klip juda qisqa yoki in/out noto'g'ri: {item['path'].name} ({start}-{end})")
    return start, end


def _vf(style: dict, item: dict) -> str:
    v = style["video"]
    W, H, fps = int(v["width"]), int(v["height"]), float(v["fps"])
    fx, fy = float(item.get("focus_x", 0.5)), float(item.get("focus_y", 0.5))
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={W}:{H}:(iw-{W})*{fx:.3f}:(ih-{H})*{fy:.3f},fps={fps:g},setsar=1,format=yuv420p")


def _encode_args(style: dict) -> list:
    crf = int(style["cut"].get("intermediate_crf", 16))
    return ["-c:v", "libx264", "-crf", str(crf), "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def _segment(item: dict, style: dict, out: Path, mute: bool) -> float:
    """Bitta speech/product klipini bir xil formatdagi bo'lakka aylantiradi. Davomiylikni qaytaradi."""
    meta = C.ffprobe_info(item["path"])
    if not meta["has_video"]:
        raise C.MontajError(f"{item['path'].name}: video oqimi yo'q (audio uchun role: voiceover).")
    s, e = _span(item, meta)
    dur = e - s
    cmd = [C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}",
           "-i", str(item["path"])]
    if mute or not meta["has_audio"]:
        if item["role"] == "speech" and not meta["has_audio"]:
            C.warn(f"{item['path'].name}: speech klipida ovoz yo'q, jim ovoz qo'yildi.")
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0", "-af", "apad"]
    cmd += ["-vf", _vf(style, item), *_encode_args(style), "-t", f"{dur:.3f}", str(out)]
    C.run(cmd)
    return C.ffprobe_info(out)["duration"]


def _voiceover(item: dict, style: dict, work: Path, idx: int) -> float:
    v = style["video"]
    W, H, fps = int(v["width"]), int(v["height"]), float(v["fps"])
    meta = C.ffprobe_info(item["path"])
    if not meta["has_audio"]:
        raise C.MontajError(f"{item['path'].name}: voiceover faylida ovoz yo'q.")
    s, e = _span(item, meta)
    dur = e - s
    ff = C.need_tool("ffmpeg")
    cover = work / f"vo_{idx:02d}_cover.mp4"
    if item["cover_paths"]:
        parts = []
        for j, cv in enumerate(item["cover_paths"]):
            part = work / f"vo_{idx:02d}_c{j:02d}.mp4"
            _segment(dict(cv, role="product"), style, part, True)
            parts.append(part)
        listing = work / f"vo_{idx:02d}_cover.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        C.run([ff, "-hide_banner", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(cover)])
        src = ["-i", str(cover)]
    else:
        C.warn(f"{item['path'].name}: cover kliplari berilmagan, tasvir qora (ustiga broll qo'ying).")
        src = ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps:g}"]
    out = work / f"seg_{idx:02d}.mp4"
    C.run([ff, "-hide_banner", "-nostdin", "-y", *src, "-ss", f"{s:.3f}", "-t", f"{dur:.3f}", "-i", str(item["path"]),
           "-map", "0:v:0", "-map", "1:a:0", "-vf", f"tpad=stop_mode=clone:stop_duration={dur:.3f},format=yuv420p",
           "-af", "apad", *_encode_args(style), "-t", f"{dur:.3f}", str(out)])
    return C.ffprobe_info(out)["duration"]


def build(source: str | Path, style: dict) -> dict:
    """Asosiy video yig'adi. Qaytaradi: {"video": Path, "protect": [(s, e)], "segments": [...]}."""
    source = Path(source)
    if not source.exists():
        raise C.MontajError(f"Klip papkasi yoki ro'yxati topilmadi: {source}")
    data, base, mpath = load_manifest(source)
    name = C.slugify(str(data.get("name") or (source.name if source.is_dir() else source.parent.name)))
    clips = validate(data, base)
    work = C.TEMP_DIR / name
    parts_dir = work / "assemble"
    parts_dir.mkdir(parents=True, exist_ok=True)
    out = C.guard_output(work / f"{name}.mp4")
    seg_file = work / "segments.json"
    fp = _fingerprint(data, clips, style)
    if out.is_file() and seg_file.is_file():
        old = C.read_json(seg_file)
        if old.get("fingerprint") == fp:
            C.info(f"Klip ro'yxati o'zgarmagan: {out.name} qayta yig'ilmaydi.")
            return {"video": out, "protect": [tuple(p) for p in old.get("protect", [])], "segments": old["segments"]}
    keep_audio = str(data.get("product_audio", "keep")) == "keep"
    files, segments, protect, pos = [], [], [], 0.0
    C.info(f"Kliplar yig'ilmoqda ({len(clips)} ta) -> {out}")
    for i, item in enumerate(clips):
        if item["role"] == "voiceover":
            dur = _voiceover(item, style, parts_dir, i)
            seg = parts_dir / f"seg_{i:02d}.mp4"
        else:
            seg = parts_dir / f"seg_{i:02d}.mp4"
            mute = item["role"] == "product" and not item.get("keep_audio", keep_audio)
            dur = _segment(item, style, seg, mute)
        files.append(seg)
        segments.append({"start": round(pos, 3), "end": round(pos + dur, 3), "role": item["role"], "file": str(item["path"])})
        if item["role"] == "product":
            protect.append((round(pos, 3), round(pos + dur, 3)))
        C.info(f"  {i + 1:>2}. {item['role']:<9} {pos:7.2f}-{pos + dur:7.2f}s  {item['path'].name}")
        pos += dur
    listing = parts_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in files), encoding="utf-8")
    C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
           "-c", "copy", "-movflags", "+faststart", str(out)])
    C.write_json({"fingerprint": fp, "manifest": str(mpath), "video": str(out), "segments": segments,
                  "protect": [list(p) for p in protect]}, seg_file)
    C.info(f"Yig'ildi: {out} ({pos:.2f}s), bo'laklar: {seg_file}")
    return {"video": out, "protect": protect, "segments": segments}


def report(segments: list, words: list) -> list:
    """Har bo'lakdagi so'zlar soni va rol bo'yicha maslahat (agent rollarni shunga qarab tekshiradi)."""
    rows = []
    for seg in segments:
        n = sum(1 for w in words if seg["start"] <= (float(w["start"]) + float(w["end"])) / 2 < seg["end"])
        hint = ""
        if seg["role"] in ("speech", "voiceover") and n == 0:
            hint = "nutq topilmadi: product bo'lishi mumkin"
        elif seg["role"] == "product" and n > 0:
            hint = "so'z eshitildi: speech/voiceover bo'lishi mumkin"
        rows.append(dict(seg, words=n, hint=hint))
    return rows


def print_report(segments: list, words: list) -> list:
    rows = report(segments, words)
    C.info("\nKliplar bo'yicha nutq (rollarni tekshiring):")
    for i, r in enumerate(rows, 1):
        C.info(f"  {i:>2}. {r['role']:<9} {r['start']:7.2f}-{r['end']:7.2f}s  {r['words']:>3} so'z  {Path(r['file']).name}"
               + (f"  <- {r['hint']}" if r["hint"] else ""))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Tartiblangan kliplardan bitta asosiy video yig'adi (ko'p klipli montaj).")
    ap.add_argument("source", help="Klip papkasi yoki clips.json")
    ap.add_argument("--style", help="Boshqa style.json fayli (o'lcham va fps shundan)")
    ap.add_argument("--brand", help="Brend nomi")
    args = ap.parse_args()
    style = C.load_style(args.style, args.brand)
    C.busy_acquire(f"assemble: {Path(args.source).name}")
    build(args.source, style)
    return 0


if __name__ == "__main__":
    C.run_main(main)
