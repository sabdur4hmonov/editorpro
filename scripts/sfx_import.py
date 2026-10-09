"""Import a purchased SFX pack: unpack, convert, trim silence, normalise loudness, sort into categories, licence note, re-index.

    1) Put the pack (zip or folder) into assets\\sfx\\_inbox\\
    2) .venv\\Scripts\\python.exe scripts\\sfx_import.py --shop "Shop name" --license "licence name / URL" [--pack NAME]

Per audio file: ffmpeg decode -> 48 kHz stereo; leading/trailing silence below --silence-db trimmed (with a few ms
kept); loudest 100 ms window set to the same RMS target as the synthesized library and the sample peak kept at or
below -1 dBFS (sfx_synth.normalise); category from file and folder names (CATEGORY_WORDS). No match or a tie ->
`_unsorted/` for the user to sort by hand (move the file into a category folder and re-run `sfx_library.py`).
Output: assets/sfx/<category>/real__<pack>__<name>.wav + credit.json + LICENSE.txt; pack note
assets/sfx/_licenses/<pack>.md (tracked in git). Purchased audio itself is git-ignored (real__*, _inbox, _unsorted):
shop licences usually forbid redistribution. Originals are moved to _inbox/_done/<pack>/ (never deleted).
Imported real files win over synthesized ones automatically (sound_design.variants).
Zips are extracted with a path check (no absolute paths or `..`); only audio files are read.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import numpy as np

import common as C
import sfx_synth as S

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aif", ".aiff", ".aac", ".opus"}
# English + Russian + Uzbek words commonly used in pack file names. Order does not matter; scores are counted.
CATEGORY_WORDS = {
    "whoosh": ["whoosh", "woosh", "swoosh", "swish", "whoose", "passby", "pass-by", "pass_by", "fly by", "flyby", "air", "wind", "свист", "вжух"],
    "swipe": ["swipe", "slide", "transition", "trans", "scroll", "page", "свайп", "переход"],
    "pop": ["pop", "bubble", "blip", "boop", "pluck", "поп", "пузыр"],
    "click": ["click", "button", "tap", "mouse", "ui", "interface", "toggle", "switch", "клик", "кнопк"],
    "tick": ["tick", "tock", "clock", "timer", "metronome", "тик", "час"],
    "hit": ["hit", "punch", "smack", "kick", "slap", "snap", "knock", "удар"],
    "impact": ["impact", "boom", "slam", "thud", "drop", "bass", "cinematic hit", "braam", "explosion", "удар баса"],
    "riser": ["riser", "rise", "rising", "uplifter", "build", "buildup", "tension", "sweep up", "reverse", "райзер", "нараст"],
    "ding": ["ding", "bell", "chime", "notification", "success", "alert", "coin", "sparkle", "звон", "колокол", "уведом"],
    "typing": ["typing", "typewriter", "keyboard", "keys", "type", "печат", "клавиат"],
}
INBOX = C.ROOT / "assets" / "sfx" / "_inbox"
LIBRARY = C.ROOT / "assets" / "sfx"


def words_of(text: str) -> str:
    return " " + re.sub(r"[\W_]+", " ", text.lower()) + " "


def categorise(rel_path: str) -> tuple:
    """(category or None, scores). File name counts double; folders count once. Ties/zero -> None."""
    parts = Path(rel_path).parts
    name, folders = words_of(Path(parts[-1]).stem), words_of(" ".join(parts[:-1]))
    scores = {}
    for cat, keys in CATEGORY_WORDS.items():
        s = 0
        for k in keys:
            kk = " " + re.sub(r"[\W_]+", " ", k.lower()).strip()
            # word start match: "whooshes", "clicks", "risers" count; "ui" must be a whole word
            if len(kk.strip()) <= 2:
                hit_name, hit_dir = f"{kk} " in name, f"{kk} " in folders
            else:
                hit_name, hit_dir = kk in name, kk in folders
            s += 2 * hit_name + hit_dir
        if s:
            scores[cat] = s
    if not scores:
        return None, scores
    best = max(scores.values())
    top = [c for c, v in scores.items() if v == best]
    return (top[0] if len(top) == 1 else None), scores


def safe_extract(zip_path: Path, dest: Path) -> list:
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or Path(name).suffix.lower() not in AUDIO_EXTS:
                continue
            if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or ".." in Path(name).parts:
                C.warn(f"Zip ichida xavfli yo'l o'tkazib yuborildi: {name}")
                continue
            if Path(name).parts[0] == "__MACOSX" or Path(name).name.startswith("._"):
                continue
            target = (dest / name).resolve()
            if not C.is_inside(target, dest.resolve()):
                C.warn(f"Zip ichida xavfli yo'l o'tkazib yuborildi: {name}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out.append(target)
    return out


def decode(path: Path) -> np.ndarray:
    p = subprocess.run([C.need_tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(path), "-f", "f32le", "-acodec",
                        "pcm_f32le", "-ac", "2", "-ar", str(S.SR), "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise C.MontajError(f"{path.name}: ffmpeg o'qiy olmadi ({p.stderr.decode(errors='replace')[:200]})")
    return np.frombuffer(p.stdout, "<f4").astype(np.float64).reshape(-1, 2)


def trim_silence(x: np.ndarray, threshold_db: float = -50.0, keep_ms: float = 8.0) -> np.ndarray:
    level = np.max(np.abs(x), axis=1)
    loud = np.nonzero(level > 10 ** (threshold_db / 20))[0]
    if not len(loud):
        return x[:0]
    keep = int(S.SR * keep_ms / 1000)
    a, b = max(0, loud[0] - keep), min(len(x), loud[-1] + keep + 1)
    y = x[a:b].copy()
    fade = min(len(y), int(S.SR * 0.005))
    if fade:
        y[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return y


def import_pack(source: Path, shop: str, licence: str, pack: str, library: Path, silence_db: float = -50.0) -> dict:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    work = C.TEMP_DIR / "sfx_import" / pack
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if source.is_file() and source.suffix.lower() == ".zip":
        files, base = safe_extract(source, work), work
    elif source.is_dir():
        files, base = sorted(p for p in source.rglob("*") if p.suffix.lower() in AUDIO_EXTS and p.is_file()), source
    elif source.is_file() and source.suffix.lower() in AUDIO_EXTS:
        files, base = [source], source.parent
    else:
        raise C.MontajError(f"{source.name}: zip, papka yoki audio fayl kutilgan.")
    rows = []
    for f in files:
        rel = f.relative_to(base).as_posix()
        cat, scores = categorise(rel)
        x = trim_silence(decode(f), silence_db)
        if len(x) < int(S.SR * 0.01):
            rows.append({"source": rel, "status": "skipped: silent or < 10 ms"})
            continue
        x = S.normalise(x)
        stem = C.slugify(Path(rel).stem)[:60] or "sfx"
        folder = library / (cat or "_unsorted")
        dest = folder / f"real__{pack}__{stem}.wav"
        n = 2
        while dest.exists():
            dest = folder / f"real__{pack}__{stem}_{n}.wav"
            n += 1
        S.write_wav(dest, x)
        C.write_json({"source": f"{shop} — pack '{pack}', original file '{rel}'", "license": licence, "shop": shop,
                      "pack": pack, "original_file": rel, "imported": stamp, "category": cat or "_unsorted",
                      "category_scores": scores, "kind": "real", "processing": "48 kHz stereo, silence trimmed, "
                      f"loudest-100ms RMS {S.TARGET_RMS_DB} dBFS, peak <= {S.PEAK_DB} dBFS"},
                     dest.with_suffix(".wav.credit.json"))
        dest.with_suffix(".wav.LICENSE.txt").write_text(f"{licence}\nShop: {shop}. Pack: {pack}. Imported {stamp}.\n",
                                                         encoding="utf-8")
        rows.append({"source": rel, "file": str(dest.relative_to(C.ROOT)), "category": cat or "_unsorted",
                     "duration": round(len(x) / S.SR, 3), "rms_db": round(S.loudest_rms_db(x), 2), "scores": scores})
    note = library / "_licenses" / f"{pack}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    for r in rows:
        if "category" in r:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
    note.write_text(f"# SFX pack: {pack}\n\n- Shop: {shop}\n- Licence: {licence}\n- Imported: {stamp}\n"
                    f"- Files: {sum(counts.values())} ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})\n"
                    f"- Audio files are git-ignored (real__*); this note and assets/sfx/index.json are tracked.\n",
                    encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return {"pack": pack, "rows": rows, "counts": counts, "licence_note": str(note.relative_to(C.ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shop", required=True, help="Do'kon nomi (masalan sayt nomi)")
    ap.add_argument("--license", required=True, help="Litsenziya nomi yoki havolasi (foydalanuvchi beradi)")
    ap.add_argument("--pack", help="Paket nomi (bitta zip/papka bo'lsa; bo'lmasa fayl nomidan)")
    ap.add_argument("--inbox", default=str(INBOX), help="Kiruvchi papka (standart assets/sfx/_inbox)")
    ap.add_argument("--library", default=str(LIBRARY), help="Kutubxona (standart assets/sfx)")
    ap.add_argument("--silence-db", type=float, default=-50.0, help="Bosh/oxiridagi jimlik chegarasi, dBFS")
    a = ap.parse_args()
    inbox, library = Path(a.inbox).resolve(), Path(a.library).resolve()
    for p in (inbox, library):
        if not C.is_inside(p, C.ROOT):
            raise C.MontajError("--inbox/--library loyiha ichida bo'lsin.")
    if not a.shop.strip() or not a.license.strip():
        raise C.MontajError("--shop va --license bo'sh bo'lmasin: litsenziya taxmin qilinmaydi.")
    inbox.mkdir(parents=True, exist_ok=True)
    items = [p for p in sorted(inbox.iterdir()) if not p.name.startswith("_") and
             (p.is_dir() or p.suffix.lower() == ".zip" or p.suffix.lower() in AUDIO_EXTS)]
    if not items:
        raise C.MontajError(f"{inbox} bo'sh: zip yoki papkani shu yerga tashlang.")
    if a.pack and len(items) > 1:
        raise C.MontajError("--pack faqat bitta zip/papka bo'lganda beriladi.")
    import sfx_library
    total = 0
    for item in items:
        pack = C.slugify(a.pack or item.stem)[:40] or "pack"
        res = import_pack(item, a.shop.strip(), a.license.strip(), pack, library, a.silence_db)
        done = inbox / "_done" / pack
        done.mkdir(parents=True, exist_ok=True)
        shutil.move(str(item), str(done / item.name))
        unsorted = res["counts"].get("_unsorted", 0)
        C.info(f"PACK {pack}: {sum(res['counts'].values())} fayl -> " + ", ".join(f"{k} {v}" for k, v in sorted(res["counts"].items())))
        if unsorted:
            C.warn(f"{unsorted} ta fayl _unsorted/ da: nomidan kategoriya aniqlanmadi, qo'lda joylang va "
                   "`scripts\\sfx_library.py` ni qayta ishga tushiring.")
        total += len(res["rows"])
    rows = sfx_library.index(library)
    C.info(f"SFX IMPORT [OK]: {total} fayl; kutubxona {len(rows)} fayl; real usable "
           f"{sum(r['kind'] == 'real' and r['usable'] for r in rows)}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
