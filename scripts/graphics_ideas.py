"""Graphics ideation: for each emphasis moment decide which visual best SHOWS the idea, and reject labels that only
repeat the subtitle.

    python scripts/graphics_ideas.py ideas  temp/<nom>/cut.mp4 [--subs temp/<nom>/subs.srt] [--words temp/<nom>/cut.words.json]
    python scripts/graphics_ideas.py apply  temp/<nom>/cut.mp4 --ids 1,4,6
    python scripts/graphics_ideas.py record temp/<nom>/cut.mp4 --id 4 --verdict approved|rejected [--note "..."]
    python scripts/graphics_ideas.py check  temp/<nom>/cut.mp4 [--elements temp/<nom>/elements.json]

Moment types (Uzbek / Russian / English cue words, from the transcript only — nothing is invented):
  object      concrete noun with a drawable object (icon lexicon or an image you supply) -> hero object flies in
              (s33: big prop, rotation, motion trail, ~9 frames)
  count/list  "3 ta / uch xil ..." + ordinals "birinchi, ikkinchi ..." -> group fan/stack/spread with one labelled
              item per spoken ordinal (s26 pill fan); the group replaces the subtitle for its span (hide_captions)
  comparison  "X yoki Y", "X emas, Y", "lekin", "o'rniga" -> two cards side by side, the chosen one highlighted (s42)
  process     "avval / keyin / so'ng / oxirida / qadam / bosqich" -> numbered spread
  stat        number + unit (% , so'm, dollar, million, ming, kun, yil, marta ...) -> count-up stat
Ranking: format plan (temp/<nom>/edit_plan.json `graphics` order), quality targets (density, min gap) and the user's
past verdicts per idea type in style/graphics_history.json. Placement avoids the face box from face.py.
The no-repeat rule (`repeat_violations`) is also enforced by studio.preflight: an on-screen label whose words are
the subtitle words shown at the same time is an error, unless the element hides the captions for its span
(`hide_captions: true`) or carries `allow_repeat` with a written `repeat_reason`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import common as C

HISTORY = C.ROOT / "style" / "graphics_history.json"
APOS = str.maketrans({c: "'" for c in "ʻʼ’‘`´"})
MARKUP = re.compile(r"\{[^}]*\}|[*_!=~]+")
TEXT_KINDS = {"card": ["text"], "title": ["text"], "text": ["text"], "callout": ["text"], "handnote": ["text"],
              "group": ["items.text"], "label": ["items.name", "items.kicker"], "aside": ["items.text"],
              "list": ["items.text"], "choice": ["items.text"], "icon": ["text"], "canvas": ["items.text"]}

# Uzbek (+ru/en) noun stems -> Phosphor icon (MIT, own asset). Brand logos are never used (*-logo excluded).
OBJECTS = {
    "telefon": "device-mobile", "smartfon": "device-mobile", "noutbuk": "laptop", "kompyuter": "laptop",
    "pul": "money", "dollar": "currency-dollar", "so'm": "money", "kitob": "book-open", "daftar": "notebook",
    "dori": "pill", "tabletka": "pill", "antibiotik": "pill", "vitamin": "pill", "shifokor": "stethoscope",
    "doktor": "stethoscope", "vrach": "stethoscope", "yurak": "heart", "qon": "drop", "suv": "drop", "soat": "clock",
    "kalendar": "calendar", "mashina": "car", "uy": "house", "maktab": "graduation-cap", "universitet": "graduation-cap",
    "kamera": "camera", "video": "video-camera", "ovqat": "fork-knife", "sport": "barbell", "bola": "baby",
    "chaqaloq": "baby", "kasalxona": "hospital", "klinika": "hospital", "shifoxona": "hospital", "termometr": "thermometer",
    "harorat": "thermometer", "isitma": "thermometer-hot", "virus": "virus", "bakteriya": "virus", "ukol": "syringe",
    "shprits": "syringe", "emlash": "syringe", "vaksina": "syringe", "tish": "tooth", "miya": "brain", "suyak": "bone",
    "ko'z": "eye", "quloq": "ear", "uyqu": "bed", "karavot": "bed", "dna": "dna", "tahlil": "flask", "analiz": "flask",
    "mikroskop": "microscope", "retsept": "prescription", "niqob": "face-mask", "quyosh": "sun", "kofe": "coffee",
    "choy": "coffee", "kiyim": "t-shirt", "poyabzal": "sneaker", "yo'tal": "virus", "lampa": "lightbulb",
    "g'oya": "lightbulb", "maqsad": "target", "xavf": "warning", "himoya": "shield-check", "natija": "chart-line-up",
    "o'sish": "trend-up", "grafik": "chart-bar", "odam": "users", "mijoz": "users", "obunachi": "users",
}
NUM_WORDS = {"bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "besh": 5, "olti": 6, "yetti": 7, "sakkiz": 8, "to'qqiz": 9, "o'n": 10,
             "ikkita": 2, "uchta": 3, "to'rtta": 4, "beshta": 5, "oltita": 6, "yettita": 7}
ORDINALS = {"birinchi": 1, "ikkinchi": 2, "uchinchi": 3, "to'rtinchi": 4, "beshinchi": 5, "oltinchi": 6, "yettinchi": 7,
            "первое": 1, "второе": 2, "третье": 3, "first": 1, "second": 2, "third": 3}
COUNT_NOUNS = {"ta", "xil", "usul", "qadam", "sabab", "narsa", "funksiya", "qoida", "belgi", "turi", "maslahat", "xato",
               "bosqich", "yo'l", "omil", "alomat", "simptom"}
UNITS = {"%", "foiz", "so'm", "dollar", "million", "mln", "ming", "kun", "yil", "oy", "marta", "soat", "daqiqa", "kg",
         "gramm", "litr", "barobar"}
COMPARE = {"yoki", "emas", "lekin", "ammo", "o'rniga", "farqi", "aksincha", "vs", "или", "но", "or", "but"}
PROCESS = {"avval", "keyin", "so'ng", "oxirida", "qadam", "bosqich", "boshida", "keyingi"}
STOP = {"va", "bu", "u", "shu", "bilan", "uchun", "ham", "esa", "deb", "edi", "bo'ladi", "kerak", "mumkin", "juda", "eng",
        "bir", "bor", "yo'q", "men", "siz", "biz", "ular", "agar", "chunki", "lekin", "yoki", "ta", "xil", "ni", "da"}


def norm(text: str) -> str:
    return MARKUP.sub("", str(text)).translate(APOS).lower()


def tokens(text: str) -> list:
    return [t.strip("'") for t in re.findall(r"[\w']+", norm(text)) if len(t.strip("'")) > 1]


def _same(a: str, b: str) -> bool:
    """Equal, or the same Uzbek stem with a suffix (o'pka / o'pkasi, dori / dorilar)."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 4 and long_.startswith(short) and len(long_) - len(short) <= 4


# ---------------------------------------------------------------- no-repeat rule
def element_texts(el: dict) -> list:
    """(text, start, end) shown by an element, item by item."""
    out = []
    kind = el.get("type")
    s, e = float(el.get("start", el.get("at", 0))), float(el.get("end", el.get("start", 0) or 0))
    if kind == 'canvas':
        return [row for item in el.get('items', []) for row in
                element_texts(dict(item, start=item.get('at', s), end=item.get('end', e)))]
    for path in TEXT_KINDS.get(kind, []):
        if path.startswith("items."):
            key = path.split(".", 1)[1]
            items = el.get("items", [])
            for i, it in enumerate(items):
                if isinstance(it, dict) and str(it.get(key, "")).strip():
                    a = float(it.get("at", s))
                    out.append((str(it[key]), a, float(it.get("end", e))))
        elif str(el.get(path, "")).strip():
            out.append((str(el[path]), s, e))
    return out


def hidden_spans(elements: list) -> list:
    return [(float(el.get("start", 0)), float(el.get("end", 0))) for el in elements if el.get("hide_captions")]


def visible_cues(cues: list, elements: list) -> list:
    spans = hidden_spans(elements)
    out = []
    for cue in cues:
        pieces = [(cue['start'], cue['end'])]
        for a, b in spans:
            pieces = [(x, y) for s, e in pieces for x, y in
                      ((s, min(e, a)), (max(s, b), e)) if y > x]
        out.extend(dict(cue, start=s, end=e) for s, e in pieces)
    return out


def repeat_violations(elements: list, cues: list, min_overlap: float = 0.15, ratio: float = 0.8) -> list:
    """Labels whose words are (>= 80 %) the subtitle words visible at the same time."""
    shown = visible_cues(cues, elements)
    out = []
    for n, el in enumerate(elements, 1):
        if el.get("type") in ("stat", "follow", "lower_third", "sfx", "zoom") or el.get("hide_captions"):
            continue
        for text, a, b in element_texts(el):
            et = [t for t in tokens(text) if t not in STOP] or tokens(text)
            if not et:
                continue
            ct = []
            for c in shown:
                if min(b, c["end"]) - max(a, c["start"]) >= min_overlap:
                    ct += tokens(c["text"])
            hit = [t for t in et if any(_same(t, c) for c in ct)]
            if ct and len(hit) / len(et) >= ratio:
                out.append({"element": n, "type": el.get("type"), "text": text, "at": round(a, 2),
                            "allowed": bool(el.get("allow_repeat") and str(el.get("repeat_reason", "")).strip()),
                            "fix": "show the thing (hero object / icon / image) instead of its name, or make this element "
                                   "the text: hide_captions: true for its span"})
    return out


# ---------------------------------------------------------------- ideation
def _clean_words(words: list) -> list:
    out = []
    for w in words:
        if isinstance(w, dict):
            out.append({"w": norm(w.get("word", "")).strip(" ,.?!:;\"«»"), "start": float(w["start"]), "end": float(w["end"])})
    return [w for w in out if w["w"]]


def _phrase(words: list, i: int, n: int = 3) -> str:
    keep = []
    for w in words[i:i + 6]:
        if w["w"] in STOP or w["w"] in ORDINALS:
            continue
        keep.append(w["w"])
        if len(keep) >= n:
            break
    return " ".join(keep)


def _object_icon(word: str) -> str | None:
    for stem, icon in OBJECTS.items():
        if _same(word, stem) or (len(stem) >= 4 and word.startswith(stem)):
            return icon
    return None


def moments(words: list) -> list:
    W = _clean_words(words)
    ideas = []
    # count / list with ordinals
    ords = [(i, ORDINALS[w["w"].rstrip("si")] if w["w"].rstrip("si") in ORDINALS else ORDINALS.get(w["w"]))
            for i, w in enumerate(W) if w["w"] in ORDINALS or w["w"].rstrip("si") in ORDINALS]
    if len(ords) >= 2:
        items = [{"at": round(W[i]["start"], 2), "text": _phrase(W, i + 1)} for i, _ in ords]
        items = [it for it in items if it["text"]]
        if len(items) >= 2:
            ideas.append({"type": "list", "at": items[0]["at"], "end": round(W[ords[-1][0]]["end"] + 2.5, 2),
                          "items": items[:6], "trigger": " / ".join(W[i]["w"] for i, _ in ords[:6]),
                          "reason": "spoken ordinals: each item appears when it is said (s26 fan, s42 bracket)"})
    for i, w in enumerate(W):
        nxt = W[i + 1]["w"] if i + 1 < len(W) else ""
        num = int(w["w"]) if w["w"].isdigit() else NUM_WORDS.get(w["w"])
        if num and 2 <= num <= 8 and (nxt in COUNT_NOUNS or nxt.endswith("ta")):
            ideas.append({"type": "count", "at": round(w["start"], 2), "end": round(w["end"] + 3.0, 2), "count": num,
                          "trigger": f"{w['w']} {nxt}", "reason": f"'{w['w']} {nxt}': show {num} objects, not the number"})
        if w["w"].rstrip('%').replace(",", "").replace(".", "").isdigit() and (nxt in UNITS or w["w"].endswith("%")):
            ideas.append({"type": "stat", "at": round(w["start"], 2), "end": round(w["end"] + 2.2, 2),
                          "value": w["w"], "suffix": nxt, "trigger": f"{w['w']} {nxt}",
                          "reason": "number with a unit: count-up ring makes the size felt"})
        if w["w"] in COMPARE and 0 < i < len(W) - 1:
            a, b = _phrase(W[max(0, i - 3):i][::-1], 0, 1), _phrase(W, i + 1, 1)
            if a and b and a != b:
                ideas.append({"type": "comparison", "at": round(W[max(0, i - 1)]["start"], 2), "end": round(w["end"] + 2.6, 2),
                              "items": [a, b], "trigger": f"{a} {w['w']} {b}",
                              "reason": "two options named: two objects side by side, the chosen one marked (s42, s06)"})
        if w["w"] in PROCESS:
            ideas.append({"type": "process", "at": round(w["start"], 2), "end": round(w["end"] + 2.5, 2),
                          "trigger": w["w"], "reason": "step word: numbered path of steps"})
        icon = _object_icon(w["w"])
        if icon:
            ideas.append({"type": "object", "at": round(w["start"], 2), "end": round(w["start"] + 2.2, 2), "icon": icon,
                          "trigger": w["w"], "reason": f"concrete thing '{w['w']}': show it (hero object, s33 prop entrance)"})
    return ideas


def history_weights(plan=None, local=None) -> dict:
    out = {}
    rows = [r for p in (HISTORY, local) if p and Path(p).is_file() for r in C.read_json(p).get('decisions', [])]
    for r in rows:
        if (plan or {}).get('format') and r.get('format') and r['format'] != plan['format']:
            continue
        k = r.get("type")
        if k:
            out[k] = out.get(k, 0.0) + (1.0 if r.get("verdict") == "approved" else -1.0)
    return out


def rank(ideas: list, plan: dict | None, duration: float, face: dict | None, local_history=None) -> list:
    order = (plan or {}).get("graphics") or ["object", "count", "list", "comparison", "stat", "process"]
    q = (plan or {}).get("quality_targets") or {"graphics_per_min": [4, 16], "min_gap_s": 0.8}
    hist = history_weights(plan, local_history)
    for d in ideas:
        base = (len(order) - order.index(d["type"])) if d["type"] in order else 0.5
        d["score"] = round(base + 0.6 * hist.get(d["type"], 0.0), 2)
        if d["type"] == "list":
            d["score"] += 2          # a spoken enumeration is the strongest structure signal
    ideas.sort(key=lambda d: (-d["score"], d["at"]))
    budget = max(1, int(q["graphics_per_min"][1] * max(duration, 1) / 60))
    chosen = []
    for d in ideas:
        if len(chosen) >= budget:
            break
        if any(not (d["end"] + q["min_gap_s"] <= c["at"] or c["end"] + q["min_gap_s"] <= d["at"]) for c in chosen):
            continue
        chosen.append(d)
    chosen.sort(key=lambda d: d["at"])
    for k, d in enumerate(chosen, 1):
        d["id"] = k
        d["recipe"] = recipe(d, face)
    return chosen


def _free_side(face: dict | None) -> tuple:
    """(x for objects, y top band) away from the face; face from face.py (cx, cy, w, h fractions)."""
    if not face:
        return 0.78, 0.18
    x = 0.22 if face["cx"] > 0.55 else 0.78
    top = max(0.12, face["cy"] - face.get("h", .15) * 0.9 - 0.1)
    return x, top


def recipe(d: dict, face: dict | None) -> list:
    x, top = _free_side(face)
    chest = min(0.8, (face["cy"] + face.get("h", .15) * 1.2) if face else 0.62)
    if d["type"] == "object":
        return [{"type": "hero", "icon": d["icon"], "start": d["at"], "end": d["end"], "x": x, "y": max(0.14, top),
                 "size": 0.26, "from": [1.25 if x > 0.5 else -0.25, max(0.05, top - 0.08)], "rotate_from": 38 if x > 0.5 else -38,
                 "trail": 0.6, "depth": 0.4, "_why": d["reason"]}]
    if d["type"] in ("list", "process"):
        items = d.get("items") or [{"at": d["at"], "text": d["trigger"]}]
        return [{"type": "group", "layout": "fan" if len(items) <= 5 else "stack", "start": items[0]["at"],
                 "end": d["end"], "pivot": [0.1 if x < 0.5 else 0.9, chest], "angle_from": -75 if x < 0.5 else -105,
                 "spread": 60 if x < 0.5 else -60, "length": 0.4, "thickness": 0.05, "active": True,
                 "hide_captions": True, "items": items, "_why": d["reason"]}]
    if d["type"] == "count":
        # The count is in the speech; which counted object it denotes still needs a human/agent sentence check.
        return [{"type": "icon", "name": d.get('icon', 'circle'), "start": round(d['at']+.12*i, 2),
                 "end": d['end'], "x": .5+(i-(d['count']-1)/2)*min(.11,.72/d['count']), "y": chest,
                 "size": .08, "bg": "none", "_why": d['reason']} for i in range(d['count'])]
    if d["type"] == "comparison":
        a, b = d["items"]
        return [{"type": "group", "layout": "spread", "start": d["at"], "end": d["end"], "x": 0.5, "y": max(0.14, top),
                 "width": 0.3, "height": 0.12, "columns": 2, "active": True, "hide_captions": True,
                 "items": [{"at": d["at"], "text": a}, {"at": round(d["at"] + 0.07, 2), "text": b}], "_why": d["reason"]}]
    if d["type"] == "stat":
        try:
            value = float(d["value"].replace(",", ".").rstrip("%"))
        except ValueError:
            value = 0
        return [{"type": "stat", "start": d["at"], "end": d["end"], "value": value, "suffix": d.get("suffix", ""),
                 "x": x, "y": max(0.16, top), "_why": d["reason"]}]
    return []


# ---------------------------------------------------------------- CLI
def _load(video: Path, subs: str | None, words: str | None):
    work = C.job_dir(video) if not C.is_inside(video, C.TEMP_DIR) else video.parent
    wp = Path(words) if words else work / "cut.words.json"
    w = C.read_json(wp)["words"] if wp.is_file() else []
    sp = Path(subs) if subs else work / "subs.srt"
    cues = C.parse_srt(sp) if sp.is_file() else []
    plan = C.read_json(work / "edit_plan.json") if (work / "edit_plan.json").is_file() else None
    return work, w, cues, plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("ideas", "apply", "record", "check"):
        s = sub.add_parser(name)
        s.add_argument("video")
        s.add_argument("--subs")
        s.add_argument("--words")
        s.add_argument("--elements")
        if name == "apply":
            s.add_argument("--ids", required=True)
        if name == "record":
            s.add_argument("--id", type=int, required=True)
            s.add_argument("--verdict", choices=("approved", "rejected"), required=True)
            s.add_argument("--note", default="")
    a = ap.parse_args()
    video = C.need_file(a.video, "Video")
    work, words, cues, plan = _load(video, a.subs, a.words)
    ideas_file = work / "graphics_ideas.json"
    if a.cmd == "ideas":
        import face as FACE
        face = FACE.detect(video, quiet=True)
        dur = C.ffprobe_info(video)["duration"]
        ideas = rank(moments(words), plan, dur, face, work/'graphics_history.json')
        C.write_json({"video": str(video), "format": (plan or {}).get("format"), "needs_agent_review": True,
                      "semantic_limit": "lexical proposals; comparison/list/process must be checked against the complete sentence",
                      "ideas": ideas}, ideas_file)
        for d in ideas:
            C.info(f"  [{d['id']}] {d['at']:6.2f}s {d['type']:10} '{d['trigger']}' — {d['reason']} (score {d['score']})")
        C.info(f"G'OYALAR: {len(ideas)} ta -> {ideas_file}. Tanlash: graphics_ideas.py apply VIDEO --ids 1,3")
    elif a.cmd == "apply":
        data = C.read_json(ideas_file, "graphics_ideas.json (avval: ideas)")
        ids = {int(x) for x in a.ids.split(",") if x.strip()}
        missing = ids - {d['id'] for d in data['ideas']}
        if missing:
            raise C.MontajError('Noma’lum g‘oya ids: '+', '.join(map(str, sorted(missing))))
        path = Path(a.elements) if a.elements else work / "elements.json"
        cur = C.read_json(path) if path.is_file() else {"elements": []}
        if path.is_file():
            C.write_json(cur, path.with_name(path.stem + ".prev.json"))
        added = []
        for d in data["ideas"]:
            if d["id"] in ids:
                for el in d["recipe"]:
                    el = {k: v for k, v in el.items() if not k.startswith("_")}
                    cur["elements"].append(el)
                    added.append(d["type"])
        C.write_json(cur, path)
        C.info(f"QO'SHILDI: {', '.join(added) or 'hech narsa'} -> {path}. Tasdiq/rad: graphics_ideas.py record VIDEO --id N --verdict ...")
    elif a.cmd == "record":
        data = C.read_json(ideas_file, "graphics_ideas.json")
        d = next((x for x in data["ideas"] if x["id"] == a.id), None)
        if not d:
            raise C.MontajError(f"G'oya {a.id} topilmadi.")
        import handoff
        other = [r for r in handoff.unfinished_notes() if Path(r['note']).parent.resolve()!=work.resolve()]
        dest = work/'graphics_history.json' if other else HISTORY
        hist = C.read_json(dest) if dest.is_file() else {"decisions": []}
        hist["decisions"].append({"video": video.name, "type": d["type"], "trigger": d["trigger"], "verdict": a.verdict,
                                  "note": a.note, "format": data.get("format"), "time": dt.datetime.now().isoformat(timespec="seconds")})
        C.write_json(hist, dest)
        C.info(f"YOZILDI: {d['type']} {a.verdict} -> {dest}" + (' (umumiy tarix idle agentga qoldirildi)' if other else ''))
    else:
        path = Path(a.elements) if a.elements else work / "elements.json"
        els = C.read_json(path)["elements"] if path.is_file() else []
        bad = repeat_violations(els, cues)
        for b in bad:
            C.warn(f"{b['element']}-element ({b['type']}) '{b['text']}' {b['at']}s subtitrni takrorlaydi"
                   + (" (ruxsat: repeat_reason)" if b["allowed"] else "") + f". {b['fix']}")
        C.info(f"TAKROR TEKSHIRUVI: {len([b for b in bad if not b['allowed']])} xato")
        return 1 if any(not b["allowed"] for b in bad) else 0
    return 0


if __name__ == "__main__":
    C.run_main(main)
