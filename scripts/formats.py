"""Video format: measure raw footage, rank the 8 reference formats, combine with a style group into one edit plan.

    python scripts/formats.py features input/video.mp4 [--words temp/<nom>/orig.words.json]
    python scripts/formats.py detect   input/video.mp4 [--words ...] [--features-extra '{"props":true}']
    python scripts/formats.py plan     input/video.mp4 [--format talking_head] [--group A_studio_explainer] [--reason "..."]
    python scripts/formats.py record   input/video.mp4 --format X --group Y --verdict approved|rejected [--note "..."]
    python scripts/formats.py list

Formats and their rules live in docs/formats/formats.json (guide: docs/FORMATS.md). Measured features (2 fps samples):
face presence, two-or-more faces, face size (close selfie vs wide), number of distinct backgrounds ("setups"),
content cuts (PySceneDetect, already in .venv), handheld shake, speech-without-face share (voice-over), split-screen line,
a persistent bright card at the top (question sticker), orientation, darkness. These are proxies: costume, props or
"story" cannot be measured, so the ranking says `needs_editor_judgement` when it is not clear and the agent decides
from frames. The user's later corrections (`record`) are stored in style/choice_history.json and shift the next ranking
for footage with similar features (`history_bonus`).
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np

import common as C

FORMATS_FILE = C.ROOT / "docs" / "formats" / "formats.json"
HISTORY_FILE = C.ROOT / "style" / "choice_history.json"
MODEL = C.ROOT / "assets" / "models" / "face_yunet.onnx"
FPS = 2.0
FEATURE_KEYS = ("face_ratio", "two_face_ratio", "face_height_median", "gaze_off", "setups", "cuts_per_min", "shake",
                "vo_ratio", "split_line", "top_card", "horizontal", "dark")


def formats() -> dict:
    return C.read_json(FORMATS_FILE, "Formatlar fayli")["formats"]


# ---------------------------------------------------------------- measurement
def _frames(video: Path, height: int = 320):
    meta = C.ffprobe_info(video)
    if not meta["has_video"] or not meta["height"]:
        raise C.MontajError(f"{video.name}: video oqimi yo'q.")
    w = max(2, int(round(height * meta["width"] / meta["height"] / 2)) * 2)
    p = subprocess.run([C.need_tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(video), "-an", "-vf",
                        f"fps={FPS},scale={w}:{height}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    n = len(p.stdout) // (w * height * 3)
    if not n:
        raise C.MontajError(f"{video.name}: kadr o'qilmadi.")
    return meta, np.frombuffer(p.stdout[:n * w * height * 3], np.uint8).reshape(n, height, w, 3)


def _cuts(video: Path) -> list:
    try:
        from scenedetect import ContentDetector, detect
        scenes = detect(str(video), ContentDetector(threshold=27.0))
        return [round(s[0].get_seconds(), 3) for s in scenes[1:]]
    except ImportError:
        C.warn("scenedetect yo'q: kesishlar sanalmadi (cuts_per_min = null).")
        return None


def _faces(frames: np.ndarray):
    import cv2
    h, w = frames.shape[1:3]
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), 0.7, 0.3, 50)
    out = []
    for f in frames:
        _, faces = det.detect(f)
        rows = []
        for x in ([] if faces is None else faces):
            if x[3] < h * 0.03:
                continue
            ex1, ey1, ex2, ey2, nx = x[4], x[5], x[6], x[7], x[8]
            eye = max(1.0, abs(ex2 - ex1))
            yaw = (nx - (ex1 + ex2) / 2) / eye      # 0 = looking at the camera; |0.3+| = turned away
            rows.append(tuple(float(v) for v in x[:4]) + (float(yaw),))
        out.append(rows)
    return out


def _setups(frames: np.ndarray, faces: list, thr: float = 0.35) -> int:
    """Distinct backgrounds: HSV histogram of the frame with face/body column masked, greedy clustering."""
    import cv2
    h, w = frames.shape[1:3]
    hists = []
    for f, fs in zip(frames, faces):
        mask = np.full((h, w), 255, np.uint8)
        for (x, y, fw, fh) in fs:
            cv2.rectangle(mask, (int(x - fw), int(y - fh * .5)), (int(x + 2 * fw), h), 0, -1)
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], mask, [8, 4, 4], [0, 180, 0, 256, 0, 256])
        hists.append(cv2.normalize(hist, hist).flatten())
    centres, counts = [], []
    for hst in hists:
        d = [cv2.compareHist(c, hst, cv2.HISTCMP_BHATTACHARYYA) for c in centres]
        if d and min(d) < thr:
            counts[int(np.argmin(d))] += 1
        else:
            centres.append(hst)
            counts.append(1)
    need = max(2, int(len(hists) * 0.04))
    return max(1, sum(c >= need for c in counts))


def _shake(frames: np.ndarray) -> float:
    """Median frame-to-frame global shift (phase correlation, % of width) on the outer border region."""
    import cv2
    if len(frames) < 3:
        return 0.0
    h, w = frames.shape[1:3]
    win = cv2.createHanningWindow((w, h), cv2.CV_32F)
    vals = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    for f in frames[1:]:
        cur = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        (dx, dy), resp = cv2.phaseCorrelate(prev, cur, win)
        if resp > 0.05:
            vals.append(math.hypot(dx, dy) / w * 100)
        prev = cur
    return round(float(np.median(vals)), 3) if vals else 0.0


def _split_line(frames: np.ndarray) -> float:
    """Persistent straight horizontal edge across the frame in the middle band (0.3-0.7 H).

    Per frame and row: share of columns with a strong vertical step (>25 grey levels). A split-screen seam is one row
    where that share is high (>0.6) in most frames. Returns the share of frames that have such a row in the band
    (0..1; >0.6 = split screen). Text lines and furniture edges are short or move, so they rarely pass."""
    g = frames.mean(axis=3)
    h = g.shape[1]
    lo, hi = int(h * .3), int(h * .7)
    step = np.abs(np.diff(g[:, lo - 1:hi + 1], axis=1)) > 25          # (n, rows, w)
    share = step.mean(axis=2)                                         # (n, rows)
    # the seam row must stand out from the frame's other rows (noise/texture is strong everywhere)
    rows = (share > 0.6) & (share > 3 * np.median(share, axis=1, keepdims=True) + 0.05)
    # the same row (±2 px) in many frames
    counts = np.zeros(rows.shape[1])
    for r in range(rows.shape[1]):
        counts[r] = rows[:, max(0, r - 2):r + 3].any(axis=1).mean()
    return round(float(counts.max()), 3)


def _top_card(frames: np.ndarray) -> bool:
    """A bright, nearly static, card-shaped region in the top 35 % (question sticker / title card), not touching the top
    edge (lamps and windows usually do), 30-95 % of the width, filled >75 %, present in >80 % of frames."""
    import cv2
    if len(frames) < 4:
        return False
    h, w = frames.shape[1:3]
    top = frames[:, :int(h * .35)].mean(axis=3)
    region = (((top > 215).mean(axis=0) > .8) & (top.std(axis=0) < 12)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(region, 8)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if y > 1 and 0.3 * w <= bw <= 0.95 * w and 0.02 * h <= bh <= 0.2 * h and area / (bw * bh) > 0.75:
            return True
    return False


def features(video: Path, words: list | None = None) -> dict:
    meta, frames = _frames(video)
    faces = _faces(frames)
    n = len(frames)
    face_ratio = sum(bool(f) for f in faces) / n
    two = sum(len(f) >= 2 for f in faces) / n
    heights = [max(x[3] for x in f) / frames.shape[1] for f in faces if f]
    yaws = [abs(max(f, key=lambda x: x[3])[4]) for f in faces if f]
    cuts = _cuts(video)
    dur = meta["duration"]
    vo = None
    if words:
        times = [i / FPS for i in range(n)]
        speaking = [any(w[1] <= t <= w[2] + 0.3 for w in words) for t in times]
        sp = sum(speaking)
        vo = round(sum(s and not f for s, f in zip(speaking, faces)) / sp, 3) if sp else 0.0
    return {"video": str(video), "duration": round(dur, 2), "width": meta["width"], "height": meta["height"],
            "samples": n, "face_ratio": round(face_ratio, 3), "two_face_ratio": round(two, 3),
            "face_height_median": round(float(np.median(heights)), 3) if heights else 0.0,
            "gaze_off": round(sum(y > 0.3 for y in yaws) / len(yaws), 3) if yaws else 0.0,
            "setups": _setups(frames, faces), "cuts": len(cuts) if cuts is not None else None,
            "cuts_per_min": round(len(cuts) / dur * 60, 2) if cuts is not None and dur else None,
            "shake": _shake(frames), "vo_ratio": vo, "split_line": _split_line(frames), "top_card": _top_card(frames),
            "horizontal": meta["width"] > meta["height"], "dark": round(float(frames.mean()) / 255, 3) < 0.22,
            "brightness": round(float(frames.mean()) / 255, 3),
            "method": "2 fps samples, YuNet faces, HSV-hist background clusters, PySceneDetect content(27), "
                      "phase-correlation shake; proxies, not scene understanding"}


# ---------------------------------------------------------------- ranking
def _cond(value, rule) -> bool:
    if value is None:
        return False
    if isinstance(rule, bool):
        return bool(value) == rule
    lo, hi = rule
    return (lo is None or value >= lo) and (hi is None or value <= hi)


def _vector(f: dict) -> np.ndarray:
    return np.array([f.get("face_ratio") or 0, f.get("two_face_ratio") or 0, min(1, (f.get("face_height_median") or 0) * 3),
                     f.get("gaze_off") or 0,
                     min(1, (f.get("setups") or 1) / 6), min(1, (f.get("cuts_per_min") or 0) / 30), min(1, (f.get("shake") or 0) / 2),
                     f.get("vo_ratio") or 0, (f.get("split_line") or 0), float(bool(f.get("top_card"))),
                     float(bool(f.get("horizontal"))), float(bool(f.get("dark")))])


def history_bonus(f: dict, kind: str = "format") -> dict:
    """Past user decisions for similar footage: +2 per approved / -2 per rejected, weighted by similarity (>0.85)."""
    if not HISTORY_FILE.is_file():
        return {}
    rows = C.read_json(HISTORY_FILE).get("decisions", [])
    v = _vector(f)
    out = {}
    for r in rows:
        if not r.get("features") or not r.get(kind):
            continue
        u = _vector(r["features"])
        sim = 1 - float(np.linalg.norm(u - v)) / math.sqrt(len(v))
        if sim < 0.85:
            continue
        sign = 2.0 if r.get("verdict") == "approved" else -2.0
        out[r[kind]] = round(out.get(r[kind], 0) + sign * sim, 2)
    return out


def detect(f: dict, extra: dict | None = None) -> dict:
    """Rank formats by docs/formats/formats.json `detect` rules (+ agent-observed extras, + history)."""
    extra = extra or {}
    hist = history_bonus(f)
    rows = []
    for key, fmt in formats().items():
        score, reasons = 0.0, []
        for rule in fmt["detect"]["rules"]:
            val = extra.get(rule["feature"]) if rule["feature"] in extra else f.get(rule["feature"])
            if _cond(val, rule["when"] if not isinstance(rule["when"], list) else tuple(rule["when"])):
                score += rule["points"]
                reasons.append(f"{rule['feature']}={val} ({rule['points']:+})")
        if hist.get(key):
            score += hist[key]
            reasons.append(f"history {hist[key]:+}")
        rows.append({"format": key, "score": round(score, 2), "reasons": reasons})
    rows.sort(key=lambda r: (-r["score"], r["format"]))
    gap = rows[0]["score"] - rows[1]["score"]
    clear = rows[0]["score"] >= 3 and gap >= 2
    return {"selected": rows[0]["format"] if clear else None, "ranked": rows[:4], "needs_editor_judgement": not clear,
            "confidence": "medium" if clear else "low", "features": f, "agent_extras": extra}


def reason_line(fmt_key: str, det: dict) -> str:
    row = next((r for r in det["ranked"] if r["format"] == fmt_key), None)
    name = formats()[fmt_key]["name"]
    why = "; ".join((row or {}).get("reasons", [])[:3]) or "agent judgement"
    return f"{name}: {why}"


# ---------------------------------------------------------------- plan
def plan(video: Path, fmt_key: str, group: str | None, det: dict, reason: str | None, subtype: str | None = None) -> dict:
    fm = formats()
    if fmt_key not in fm:
        raise C.MontajError("Noma'lum format: " + fmt_key + ". Mavjud: " + ", ".join(fm))
    f = fm[fmt_key]
    import sample_groups as SG
    group_bonus = history_bonus(det['features'], 'group')
    group = group or max(f['style_groups'], key=lambda g: group_bonus.get(g, 0))
    if group not in SG.FAMILIES:
        raise C.MontajError("Noma'lum uslub guruhi: " + group)
    if group == "D_cinematic_commercial" and subtype not in ("promo", "showcase", "vlog"):
        subtype = "promo"
    out = {"video": str(video), "format": fmt_key, "format_name": f["name"],
           "format_reason": reason or reason_line(fmt_key, det),
           "style_group": group, "style_reason": f"{group}: {f['group_reason']}" if group == f["style_groups"][0]
           else f"{group}: similar-footage user history or agent choice", "subtype": subtype,
           "edit": f["edit"], "quality_targets": f["quality_targets"], "graphics": f["graphics"],
           "detection": {k: det[k] for k in ("selected", "ranked", "needs_editor_judgement", "confidence")},
           "features": det["features"]}
    return out


def approval_lines(p: dict) -> list:
    """Two lines for the approval message (pipeline prints them; skills copy them)."""
    flag = " (taxmin, kadrdan tekshiring)" if p["detection"]["needs_editor_judgement"] else ""
    return [f"FORMAT: {p['format_name']} — {p['format_reason']}{flag}",
            f"USLUB: {p['style_reason']}"]


def record(video: Path, fmt_key: str | None, group: str | None, verdict: str, note: str, feats: dict | None) -> dict:
    data = C.read_json(HISTORY_FILE) if HISTORY_FILE.is_file() else {"decisions": []}
    row = {"video": Path(video).name, "format": fmt_key, "group": group, "verdict": verdict, "note": note,
           "features": {k: feats.get(k) for k in FEATURE_KEYS} if feats else None,
           "time": __import__("datetime").datetime.now().isoformat(timespec="seconds")}
    data["decisions"].append(row)
    C.write_json(data, HISTORY_FILE)
    return row


def _words(path: str | None) -> list | None:
    if not path:
        return None
    data = C.read_json(path)
    rows = data.get("words", data) if isinstance(data, dict) else data
    out = []
    for w in rows:
        if isinstance(w, dict):
            out.append((w.get("word"), float(w["start"]), float(w["end"])))
        else:
            out.append((w[3] if len(w) > 3 else w[0], float(w[1]), float(w[2])))
    return out


def guide() -> str:
    """docs/FORMATS.md generated from docs/formats/formats.json (one source of truth)."""
    data = C.read_json(FORMATS_FILE)
    out = ["# Video formatlari (8 namuna) — qo'llanma",
           "",
           r"Bu fayl `docs/formats/formats.json` dan yasaladi: `.venv\Scripts\python.exe scripts\formats.py guide`.",
           "Qo'lda tahrir qilmang — JSON ni tahrir qilib, qayta yarating.",
           "",
           "**Qanday ishlatiladi.** Montaj boshida: `formats.py plan VIDEO [--words temp/<nom>/orig.words.json]` xom videoni",
           "o'lchaydi (yuz, ikki kishi, qarash yo'nalishi, yuz kattaligi, fonlar soni, kesishlar, silkinish, ovoz kadr ortidanmi,",
           "bo'lingan ekran, tepadagi savol kartochkasi), formatni va uslub guruhini tanlaydi, sababini bir qatorda yozadi.",
           "Tasdiq xabarida ikkala tanlov sababi bilan ko'rsatiladi. Aniq bo'lmasa (`needs_editor_judgement`) agent kadrlarga",
           "qarab hal qiladi va kuzatganini `--features-extra '{\"costume\": true}'` bilan beradi. Foydalanuvchi tuzatsa:",
           "`formats.py record VIDEO --format X --group Y --verdict approved|rejected` — keyingi o'xshash videoda hisobga olinadi.",
           "",
           "**Dalil qoidasi.** Har xulosa: video, vaqt, kadr; ishonch; muqobil izoh. 3 tadan kam videoda ko'ringan = *kuzatuv*",
           "(observation). Namunalar boshqalarning ishi: faqat uslub olinadi, logotip/musiqa/footage/shrift ko'chirilmaydi.",
           "Belgilar xom videoga emas, tayyor videoga qarab o'lchangan: xom videoda kesish va grafika hali yo'q, shuning uchun",
           "kesish/fon qoidalari klip papkasi yoki ko'p kadrli xom materialda ishlaydi.",
           "",
           "| Format | Qisqacha | Dalil sinfi | Mos namunalar |",
           "|---|---|---|---|"]
    for k, f in data["formats"].items():
        ms = ", ".join(f"{m['video']} ({m['confidence']})" for m in f["matching_samples"]) or "—"
        out.append(f"| **{f['name']}** (`{k}`) | {f['summary']} | {f['evidence_class']} | {ms} |")
    for k, f in data["formats"].items():
        e = f["edit"]
        cap = e["captions"]
        q = f["quality_targets"]
        out += ["", f"## {f['name']} (`{k}`) — {f['evidence_class']}", "", f["summary"], "",
                f"**Belgilangan namuna:** `{f['labelled_example']['file']}`"]
        out += [f"- {x}" for x in f["labelled_example"]["evidence"]]
        out += ["", "**Mos namunalar (1-42):**" if f["matching_samples"] else "**Mos namunalar (1-42):** topilmadi — qoidalar *kuzatuv*."]
        out += [f"- {m['video']} ({m['confidence']}): {m['evidence']}" for m in f["matching_samples"]]
        rules = "; ".join(f"{r['feature']} {r['when']} → {r['points']:+}" for r in f["detect"]["rules"])
        out += ["", f"**Xom videodan tanib olish:** {f['recognise']}", f"<br>Qoidalar (ball): {rules}",
                "", f"**Tuzilma:** {f['structure']}",
                f"**Kesish:** {e['cut_pattern']}",
                f"**Subtitr:** {cap['mode']}; preset `{cap.get('preset')}`, balandligi {cap['size_pct_h']} % H, joyi y {cap['position_y']}"
                + (f" — {cap['note']}" if cap.get('note') else ""),
                f"**Grafika:** {', '.join(e['graphic_types'])}; daqiqasiga {e['graphics_per_min']}",
                f"**B-roll:** {e['broll']}",
                f"**Ovoz:** {e['sound']}",
                "**Xatolar:** " + "; ".join(e["mistakes"]),
                f"**Sifat nishonlari (quality gate):** kesish/min {q['cuts_per_min']}, grafika/min {q['graphics_per_min']}, "
                f"orasida kamida {q['min_gap_s']} s, sokin bo'lak {q['calm_stretch_s']} s, subtitr {q['caption_size_pct_h']} % H, "
                f"birinchi yozuv ≤ {q['hook_text_s']} s, yuzni yopish ≤ {q['max_face_cover']:.0%}",
                f"**Uslub guruhlari:** {', '.join(f['style_groups'])} — {f['group_reason']}"]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("features", "detect", "plan", "record"):
        s = sub.add_parser(name)
        s.add_argument("video")
        s.add_argument("--words")
        s.add_argument("--features-extra", help="JSON: agent-observed booleans, e.g. {\"props\": true, \"costume\": true}")
        if name in ("plan", "record"):
            s.add_argument("--format")
            s.add_argument("--group")
        if name == "plan":
            s.add_argument("--reason")
            s.add_argument("--subtype", choices=("promo", "showcase", "vlog"))
        if name == "record":
            s.add_argument("--verdict", choices=("approved", "rejected"), required=True)
            s.add_argument("--note", default="")
    sub.add_parser("list")
    sub.add_parser("guide")
    a = ap.parse_args()
    if a.cmd == "guide":
        (C.ROOT / "docs" / "FORMATS.md").write_text(guide(), encoding="utf-8")
        C.info("docs/FORMATS.md yangilandi.")
        return 0
    if a.cmd == "list":
        for k, f in formats().items():
            C.info(f"{k}: {f['name']} — {f['summary']} [{f['evidence_class']}]")
        return 0
    video = C.need_file(a.video, "Video")
    work = C.job_dir(video)
    cache = work / "format_features.json"
    if cache.is_file() and C.read_json(cache).get("video") == str(video) and not a.words:
        feats = C.read_json(cache)
    else:
        feats = features(video, _words(a.words))
        work.mkdir(parents=True, exist_ok=True)
        C.write_json(feats, cache)
    extra = json.loads(a.features_extra) if a.features_extra else {}
    if a.cmd == "features":
        C.info(json.dumps(feats, ensure_ascii=False, indent=1))
    elif a.cmd == "detect":
        C.info(json.dumps(detect(feats, extra), ensure_ascii=False, indent=1))
    elif a.cmd == "plan":
        det = detect(feats, extra)
        key = a.format or det["selected"] or det["ranked"][0]["format"]
        p = plan(video, key, a.group, det, a.reason, a.subtype)
        C.write_json(p, work / "edit_plan.json")
        for line in approval_lines(p):
            C.info(line)
        C.info(f"Reja: {work / 'edit_plan.json'}")
    else:
        row = record(video, a.format, a.group, a.verdict, a.note, feats)
        C.info("YOZILDI: " + json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    C.run_main(main)
