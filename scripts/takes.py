"""Klip papkasi uchun dubl (take) tanlash: yomon va takroriy urinishlarni topadi, har gapning eng yaxshi dublini
so'z chegarasida kesadi, to'g'ri tartibda assemble.py ro'yxatiga (clips.json) yozadi.

    python scripts/takes.py input/papka [--style temp/<nom>/style.json] [--script skript.txt]
    python scripts/takes.py input/papka --verify     # yig'ilgan video transkripsiyasi bilan tekshirish

Odatda pipeline.py papka berilganda buni o'zi birinchi bosqich qilib chaqiradi (/montaj, /namuna, /promo).

Ikki rejim:
  A) skript bor (papkada script.txt yoki --script): har klip skript gaplariga moslanadi (bir klipda bir nechta
     gap, bir gap bir nechta klipda - dubllar). Tartib skriptdan. Klipi yo'q gap "dubl yo'q" deb ko'rsatiladi.
  B) skript yo'q: kliplar matni solishtirilib bir xil gaplar dubl sifatida guruhlanadi. Tartib: fayl nomidagi
     raqam, bo'lmasa yozilgan vaqt (metadata), bo'lmasa mazmundan taklif (taxminiy, tasdiq kerak).

Har dubl baholanadi (mos so'zlar, "ee/mm", to'xtatilgan urinish va "qaytadan", ishonchi past so'zlar, uzun pauza,
ovoz cho'qqisi/juda past ovoz, xiralik, qorong'i/kuygan kadr, silkinish, yuz) va sababi yoziladi. Ballari yaqin
dubllar "close call" bo'ladi - jim hal qilinmaydi. Nutqsiz kliplar (taom, b-roll) uchun joy taklif qilinadi
va tasdiqqa chiqariladi.

Natija (temp/<nom>/): takes.json, clips.json, report.html, A rejimda script.lines.txt (subtitr matni skriptdan).
Qo'lda tanlash (keyingi ishga tushirishda ustun): temp/<nom>/takes.override.json yoki input/<papka>/takes.override.json
    {"pin": [{"clip": "c3.mp4", "line": 4}], "force": [{"line": 4, "clip": "c3.mp4", "take": 2}],
     "exclude": ["c7.mp4"], "place": [{"clip": "taom.mp4", "after_line": 3}], "order": [2, 1, 3],
     "clip_order": ["b.mp4", "a.mp4"], "clips": {"ovoz.m4a": {"role": "voiceover", "cover": [{"file": "..."}]}}}
Asl fayllar faqat o'qiladi. Sozlamalar: style.json "takes" bo'limi. Retsept: docs/TAKES.md.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import html
import json
import math
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

import common as C
import script_align as SA

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".opus"}
SR = 24000                      # tahlil uchun ovoz chastotasi (mono)
OVERRIDE = "takes.override.json"
STATUS = {"good": "yaxshi", "close": "close call", "decide": "qaror kerak", "missing": "dubl yo'q", "forced": "qo'lda"}


def config(style: dict) -> dict:
    """style/style.json "takes" bo'limi + per-video uslubdagi o'zgarishlar (eski nusxalarda bo'lim yo'q bo'lishi mumkin)."""
    base = C.read_json(C.STYLE_PATH, "style.json").get("takes")
    if not isinstance(base, dict):
        raise C.MontajError("style/style.json ichida \"takes\" bo'limi yo'q.")
    over = style.get("takes") if isinstance(style.get("takes"), dict) else {}
    return C.deep_merge(base, over)


# ---------------------------------------------------------------- matn

class Matcher:
    """So'zlarni solishtirish: script_align.norm (kichik harf, lotin, tinish va apostrofsiz) ustida."""

    def __init__(self, cfg: dict):
        self.cache: dict = {}
        self.fillers = {SA.norm(x) for x in cfg["fillers"]} - {""}
        self.numbers = {SA.norm(x) for x in cfg["number_words"]} - {""}
        latin = {SA.norm(x) for x in cfg["number_words"] if str(x).isascii()} - {""}
        self.ordinals = {n + ("nchi" if n.endswith(("i", "a")) else "inchi") for n in latin}
        self.cache_num: dict = {}
        phrases = {tuple(t for t in map(SA.norm, str(p).split()) if t) for p in cfg["retake_words"]}
        self.retake = sorted(phrases - {()}, key=len, reverse=True)

    def is_filler(self, t: str) -> bool:
        return t in self.fillers

    def is_numeric(self, t: str) -> bool:
        """Raqam, son so'zi yoki tartib so'zi ("birinchi"; whisper "ikkinchii", "ikinci" deb yozsa ham)."""
        if any(ch.isdigit() for ch in t) or t in self.numbers or t.endswith(("inchi", "nchi")):
            return True
        if t not in self.cache_num:
            self.cache_num[t] = len(t) >= 5 and any(SA.similarity(t, o, self.cache) >= 0.8 for o in self.ordinals)
        return self.cache_num[t]

    def number_pair(self, a: str, b: str) -> bool:
        return a != b and ((a.isdigit() and b in self.numbers) or (b.isdigit() and a in self.numbers))

    def sim(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        if self.number_pair(a, b):
            return 0.75                       # "20" va "yigirma": mos, lekin hisobotda belgilanadi
        return SA.similarity(a, b, self.cache)

    def retake_positions(self, toks: list) -> set:
        hits: set = set()
        i = 0
        while i < len(toks):
            for ph in self.retake:
                if all(i + x < len(toks) and self.sim(toks[i + x], ph[x]) >= 0.85 for x in range(len(ph))):
                    hits.update(range(i, i + len(ph)))
                    i += len(ph) - 1
                    break
            i += 1
        return hits


def tokenize(words: list) -> list:
    """[(so'z indeksi, norm)] - bo'sh (faqat tinish belgisi) so'zlarsiz."""
    out = []
    for k, w in enumerate(words):
        n = SA.norm(str(w.get("word", "")))
        if n:
            out.append((k, n))
    return out


def split_sentences(line: str) -> list:
    masked = re.sub(r"\[[^\]]*\]", lambda m: m.group(0).replace(".", "\x00").replace("!", "\x01").replace("?", "\x02"), line)
    parts = re.split(r"(?<=[.!?…])\s+", masked)
    return [p.replace("\x00", ".").replace("\x01", "!").replace("\x02", "?").strip() for p in parts if p.strip()]


def script_segments(text: str, cfg: dict) -> list:
    """Skript gaplari. Har qator bitta gap; max_line_words dan uzun qator (paragraf) gaplarga bo'linadi."""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln and not ln.startswith(("#", "//"))]
    segs, carry = [], ""
    for line in lines:
        parts = split_sentences(line) if len(line.split()) > int(cfg["max_line_words"]) else [line]
        for part in parts:
            part = f"{carry} {part}".strip() if carry else part
            toks, _ = SA.read_script(part)
            if not toks:                       # faqat [eslatma]: keyingi gapga qo'shiladi
                carry = part
                continue
            carry = ""
            segs.append({"n": len(segs) + 1, "raw": part, "norm": [t["norm"] for t in toks],
                         "text": C.strip_markup(" ".join(t["raw"] for t in toks))})
    if carry and segs:
        segs[-1]["raw"] += " " + carry
    if not segs:
        raise C.MontajError("Skript fayli bo'sh (yoki ichida faqat izoh va eslatmalar bor).")
    return segs


def hotwords(segs: list, cfg: dict) -> str:
    """Whisperga ishora: skriptdagi uzun va kam uchraydigan so'zlar (atoqli otlar, taom nomlari)."""
    seen, out = set(), []
    words = [w for s in segs for w in re.findall(r"[^\W\d_][\w'ʻʼ‘’`-]*", C.strip_markup(re.sub(r"\[[^\]]*\]", " ", s["raw"])))]
    for w in sorted(words, key=lambda x: -len(x)):
        key = SA.norm(w)
        if len(key) >= 5 and key not in seen:
            seen.add(key)
            out.append(w)
        if len(out) >= int(cfg["hotwords_max"]):
            break
    return " ".join(out)


# ---------------------------------------------------------------- moslash

def local_align(a: list, b: list, M: Matcher, blocked: set | frozenset = frozenset()) -> dict | None:
    """Gap (a) eshitilgan so'zlar (b) ichida qayerda aytilganini topadi (Smith-Waterman, xatoli so'zlarga chidamli).

    blocked: b dagi band so'zlar (boshqa dublga tegishli yoki "qaytadan"). Topilmasa None.
    """
    n, m = len(a), len(b)
    if not n or not m:
        return None
    H = [[0.0] * (m + 1) for _ in range(n + 1)]
    T = [[0] * (m + 1) for _ in range(n + 1)]
    best, bi, bj = 0.0, 0, 0
    for i in range(1, n + 1):
        ai = a[i - 1]
        Hi, Hp, Ti = H[i], H[i - 1], T[i]
        for j in range(1, m + 1):
            if j - 1 in blocked:
                continue
            s = M.sim(ai, b[j - 1])
            h, t = 0.0, 0
            diag = Hp[j - 1] + (2.0 * s - 0.6 if s >= 0.5 else -0.8)
            if diag > h:
                h, t = diag, 1
            up = Hp[j] - 0.5                                     # gapdagi so'z aytilmagan
            if up > h:
                h, t = up, 2
            left = Hi[j - 1] - (0.1 if M.is_filler(b[j - 1]) else 0.4)   # ortiqcha so'z ("ee" arzon)
            if left > h:
                h, t = left, 3
            Hi[j], Ti[j] = h, t
            if h > best:
                best, bi, bj = h, i, j
    if best <= 0:
        return None
    pairs, i, j = [], bi, bj
    while i > 0 and j > 0 and T[i][j]:
        t = T[i][j]
        if t == 1:
            pairs.append((i - 1, j - 1, M.sim(a[i - 1], b[j - 1])))
            i, j = i - 1, j - 1
        elif t == 2:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    good = [p for p in pairs if p[2] >= 0.5]
    if not good:
        return None
    i0, i1, j0, j1 = good[0][0], good[-1][0], good[0][1], good[-1][1]
    cover = sum(1.0 if s >= SA.MATCH else 0.5 for _, _, s in good) / n
    paired = {j for _, j, _ in good}
    return {"score": best, "value": best - 0.5 * (i0 + (n - 1 - i1)), "i0": i0, "i1": i1, "j0": j0, "j1": j1,
            "cover": round(min(1.0, cover), 3), "matched": sum(1 for p in good if p[2] >= SA.MATCH), "n": n,
            "extras": [x for x in range(j0, j1 + 1) if x not in paired],
            "numflags": [(a[p[0]], b[p[1]]) for p in good if M.number_pair(a[p[0]], b[p[1]])]}


def fit(a: list, sub: list, M: Matcher) -> float:
    """Gap shu so'zlarni qanchalik tushuntiradi (F1: gap so'zlari topildi + eshitilgan so'zlar gapda bor)."""
    r = local_align(a, sub, M)
    if not r:
        return 0.0
    content = sum(1 for t in sub if not M.is_filler(t)) or 1
    precision = min(1.0, r["cover"] * r["n"] / content)
    return round(2 * precision * r["cover"] / (precision + r["cover"]), 3) if precision + r["cover"] else 0.0


def _take(clip: dict, ci: int, line: int, toks: list, j0: int, j1: int, r: dict | None, **extra) -> dict:
    words = clip["words"]
    k0, k1 = toks[j0][0], toks[j1][0]
    t = {"clip": clip["name"], "ci": ci, "line": line, "w0": k0, "w1": k1, "j0": j0, "j1": j1,
         "start": round(float(words[k0]["start"]), 3), "end": round(float(words[k1]["end"]), 3),
         "text": " ".join(str(words[k]["word"]).strip() for k in range(k0, k1 + 1)),
         "cover": r["cover"] if r else 0.0, "matched": r["matched"] if r else 0, "n_line": r["n"] if r else 0,
         "extras": [toks[x][0] for x in (r["extras"] if r else [])], "numflags": r["numflags"] if r else [],
         "retake_after": False, "restart": False}
    t.update(extra)
    return t


def match_script(clips: list, segs: list, M: Matcher, cfg: dict, pins: dict) -> list:
    """A rejim: har klipdagi skript gaplari dubllarini topadi (bir klipda bir nechta gap va takrorlar bo'lishi mumkin)."""
    takes = []
    min_cover = float(cfg["match_min_cover"])
    for ci, clip in enumerate(clips):
        toks = clip["_toks"]
        if not toks:
            continue
        b = [t for _, t in toks]
        blocked = set(clip["_retake"])
        pinned = pins.get(clip["name"])
        allowed = [pinned - 1] if pinned and 1 <= pinned <= len(segs) else list(range(len(segs)))
        found, cache = [], {}
        while len(found) < 40:
            best = None
            for s in allowed:
                if s not in cache:
                    cache[s] = local_align(segs[s]["norm"], b, M, blocked)
                r = cache[s]
                if r and r["cover"] >= min_cover and r["matched"] >= min(2, len(segs[s]["norm"])):
                    if best is None or r["value"] > best[1]["value"]:
                        best = (s, r)
            if best is None:
                break
            s, r = best
            sub = b[r["j0"]:r["j1"] + 1]
            own = fit(segs[s]["norm"], sub, M)
            runner = (None, 0.0)
            for s2 in range(len(segs)):
                if s2 != s:
                    f2 = fit(segs[s2]["norm"], sub, M)
                    if f2 > runner[1]:
                        runner = (s2, f2)
            found.append(_take(clip, ci, s, toks, r["j0"], r["j1"], r, fit=own,
                               runner_line=None if runner[0] is None else runner[0] + 1,
                               runner_fit=runner[1], margin=round(own - runner[1], 3)))
            blocked |= set(range(r["j0"], r["j1"] + 1))
            # band qilingan so'zlarga tegmagan eng yaxshi moslik baribir eng yaxshi bo'lib qoladi
            cache = {k: v for k, v in cache.items() if not v or v["j1"] < r["j0"] or v["j0"] > r["j1"]}
        if pinned and not found:
            content = [j for j, (_, t) in enumerate(toks) if not M.is_filler(t) and j not in clip["_retake"]]
            if content:
                found.append(_take(clip, ci, pinned - 1, toks, content[0], content[-1], None, fit=0.0,
                                   runner_line=None, runner_fit=0.0, margin=0.0, pinned=True))
        takes += found
    return takes


def fill_missing(takes: list, n_lines: int, cfg: dict) -> None:
    """Dubli yo'q gap: boshqa gapga berilgan, lekin unga ham deyarli teng mos dubl (masalan "ikkinchi" so'zi
    eshitilmagan) - o'sha gapda boshqa to'liq dubl bo'lsa shu yerga o'tkaziladi. Farq kichik: "qaror kerak" bo'ladi."""
    low, margin = float(cfg["match_low_cover"]), float(cfg["match_margin"])
    for li in range(n_lines):
        if any(t["line"] == li for t in takes):
            continue
        cands = sorted((t for t in takes if t.get("runner_line") == li + 1 and t["margin"] < 2 * margin
                        and t["cover"] >= low and not t.get("pinned")), key=lambda t: t["margin"])
        for t in cands:
            if any(x is not t and x["line"] == t["line"] and x["cover"] >= low for x in takes):
                t.update(line=li, runner_line=t["line"] + 1, fit=t["runner_fit"], runner_fit=t["fit"],
                         margin=round(t["runner_fit"] - t["fit"], 3), moved=True)
                break


# ---------------------------------------------------------------- skriptsiz rejim

def utterances(clip: dict, M: Matcher, cfg: dict) -> list:
    """Klip nutqini gaplarga bo'ladi: uzun pauza, gap oxiri belgisi, "qaytadan" va boshidan qayta boshlash."""
    toks, words, retake = clip["_toks"], clip["words"], clip["_retake"]
    out, cur = [], []

    def close(after_retake: bool = False) -> None:
        if cur:
            out.append({"j": list(cur), "retake_after": after_retake})
            cur.clear()
        elif after_retake and out:
            out[-1]["retake_after"] = True

    for j, (k, _) in enumerate(toks):
        if j in retake:
            close(True)
            continue
        if cur:
            pk = toks[cur[-1]][0]
            gap = float(words[k]["start"]) - float(words[pk]["end"])
            if gap >= float(cfg["line_gap"]) or re.search(r"[.!?…]$", str(words[pk]["word"]).strip()):
                close()
        cur.append(j)
    close()
    res = []
    for u in out:
        res += _split_restart(u, toks, M)
    return res


def _split_restart(u: dict, toks: list, M: Matcher) -> list:
    """"bugun sizga ... bugun sizga uchta sir" -> birinchi qism to'xtatilgan urinish."""
    js = u["j"]
    t = [toks[j][1] for j in js]
    for k in (4, 3, 2):
        for p in range(k, len(t) - k + 1):
            if all(M.sim(t[x], t[p + x]) >= 0.8 for x in range(k)):
                head = {"j": js[:p], "retake_after": False, "restart": True}
                return [head] + _split_restart({"j": js[p:], "retake_after": u["retake_after"]}, toks, M)
    return [u]


def numbers_differ(a: list, b: list, M: Matcher) -> bool:
    """"birinchi set" va "ikkinchi set": raqam/tartib so'zi boshqa - bu dubl emas, boshqa gap."""
    for op, a0, a1, b0, b1 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "replace" and any(M.is_numeric(x) for x in a[a0:a1]) and any(M.is_numeric(x) for x in b[b0:b1]):
            return True
    return False


def clean(tokens: list, M: Matcher) -> list:
    """Solishtirish uchun: "ee/mm" va ketma-ket takrorlangan so'zlarsiz."""
    out = []
    for t in tokens:
        if not M.is_filler(t) and (not out or out[-1] != t):
            out.append(t)
    return out


def line_rel(a: list, b: list, M: Matcher, cfg: dict, loose: bool = False) -> tuple:
    """(nisbiy o'xshashlik, xom o'xshashlik). Nisbiy >= 1: bitta gapning dubllari.

    To'liq: ikki gap matni (harflar bo'yicha) same_line dan o'xshash. Boshlanishi: qisqasining so'zlari uzunining
    boshida same_line_prefix ulushda topiladi (to'xtatilgan urinish). loose: urinish to'xtatilgani aniq ("qaytadan"
    yoki gap qayta boshlangan) - boshlanish chegarasi 0.7 barobar yumshoqroq.
    """
    a, b = clean(a, M), clean(b, M)
    if not a or not b or numbers_differ(a, b, M):
        return 0.0, 0.0
    full = SequenceMatcher(None, " ".join(a), " ".join(b), autojunk=False).ratio()
    short, longer = (a, b) if len(a) <= len(b) else (b, a)
    pref = 0.0
    if 2 <= len(short) < len(longer):
        r = local_align(short, longer[:len(short) + 2], M)
        if r and r["i0"] <= 1 and r["j0"] <= 1:
            pref = r["cover"]
    need = float(cfg["same_line_prefix"]) * (0.7 if loose else 1.0)
    return max(full / float(cfg["same_line"]), pref / need), round(max(full, pref), 3)


def group_lines(clips: list, M: Matcher, cfg: dict) -> tuple:
    """B rejim: hamma kliplardagi gaplarni dubl guruhlariga yig'adi. Qaytaradi: (takes, lines, fragments)."""
    utts = []
    for ci, clip in enumerate(clips):
        for u in utterances(clip, M, cfg):
            toks = clip["_toks"]
            content = [toks[j][1] for j in u["j"] if not M.is_filler(toks[j][1])]
            probs = [float(clip["words"][toks[j][0]].get("prob", 1.0)) for j in u["j"]]
            utts.append(dict(u, ci=ci, content=content, prob=sum(probs) / len(probs) if probs else 0.0,
                             start=float(clip["words"][toks[u["j"][0]][0]]["start"])))
    utts.sort(key=lambda u: (clips[u["ci"]]["order"], u["start"]))
    min_words = int(cfg["speech_min_words"])
    clusters: list = []
    later, fragments = [], []
    # 1) oddiy (to'xtatilmagan) gaplar o'zaro guruhlanadi
    for ui, u in enumerate(utts):
        if not u["content"]:
            continue                                   # faqat "ee", "mm"
        if len(u["content"]) < min_words or u["retake_after"] or u.get("restart"):
            later.append(ui)
            continue
        best, bv = None, 0.0
        for c, members in enumerate(clusters):
            v = max(line_rel(u["content"], utts[m]["content"], M, cfg)[0] for m in members)
            if v > bv:
                best, bv = c, v
        if best is not None and bv >= 1.0:
            clusters[best].append(ui)
        else:
            clusters.append([ui])
    core = [list(c) for c in clusters]                 # to'xtatilgan urinishlar boshqa gaplarni o'ziga tortmaydi
    # 2) to'xtatilgan, qisqa urinishlar eng mos gapga qo'shiladi (boshlanishi yumshoqroq chegarada)
    for ui in later:
        u = utts[ui]
        best, bv = None, 0.0
        for c, members in enumerate(core):
            if len(u["content"]) < min_words:
                v = 1.0 if any(M.sim(u["content"][0], utts[m]["content"][0]) >= 0.8 for m in members) else 0.0
            else:
                v = max(line_rel(u["content"], utts[m]["content"], M, cfg, True)[0] for m in members)
            if v > bv:
                best, bv = c, v
        if best is not None and bv >= 1.0:
            clusters[best].append(ui)
            u["restart"] = u.get("restart") or len(u["content"]) < min_words
        elif len(u["content"]) >= 4:                   # to'liq gapga o'xshaydi: alohida gap, lekin tasdiqqa chiqadi
            clusters.append([ui])
            core.append([ui])
            u["only_flagged"] = True
        else:
            fragments.append({"clip": clips[u["ci"]]["name"], "start": round(u["start"], 2),
                              "text": " ".join(clip_text(clips[u["ci"]], u["j"])),
                              "why": "to'xtatilgan urinish yoki bitta so'z, boshqa dubli topilmadi"})
    takes, lines = [], []
    for c, members in enumerate(clusters):
        # namuna: boshqa dubllarga eng o'xshash (medoid), keyin uzunrog'i va keyingisi
        def central(u: dict) -> tuple:
            near = sum(line_rel(u["content"], utts[o]["content"], M, cfg)[1] for o in members if utts[o] is not u)
            return (round(near, 3), len(clean(u["content"], M)), clips[u["ci"]]["order"], u["start"])
        ref = clean(max((utts[m] for m in members), key=central)["content"], M)
        lines.append({"ref": ref, "members": members})
    for li, line in enumerate(lines):
        for m in line["members"]:
            u = utts[m]
            clip = clips[u["ci"]]
            toks = clip["_toks"]
            b = [toks[j][1] for j in u["j"]]
            r = local_align(line["ref"], b, M)
            own = line_rel(u["content"], line["ref"], M, cfg)[1]
            runner = (None, 0.0)
            for l2, other in enumerate(lines):
                if l2 != li:
                    v = line_rel(u["content"], other["ref"], M, cfg)[1]
                    if v > runner[1]:
                        runner = (l2, v)
            j0, j1 = u["j"][0], u["j"][-1]
            if r:
                rr = dict(r, extras=[u["j"][x] for x in r["extras"]])
            else:
                rr = {"cover": 0.0, "matched": 0, "n": len(line["ref"]), "extras": [], "numflags": []}
            takes.append(_take(clip, u["ci"], li, toks, j0, j1, rr, fit=own, runner_line=runner[0], runner_fit=runner[1],
                               margin=round(own - runner[1], 3), retake_after=u["retake_after"],
                               restart=bool(u.get("restart")), only_flagged=bool(u.get("only_flagged"))))
    return takes, lines, fragments


def clip_text(clip: dict, js: list) -> list:
    toks = clip["_toks"]
    return [str(clip["words"][toks[j][0]]["word"]).strip() for j in js]


# ---------------------------------------------------------------- tartib

def natural_key(name: str) -> list:
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", name)]


def order_clips(names: list, created: dict | None = None, override: dict | None = None) -> dict:
    """Kliplar tartibi va uning manbasi: qo'lda > fayl nomidagi raqam > yozilgan vaqt > aniq emas."""
    names = list(names)
    natural = sorted(names, key=natural_key)
    wanted = [n for n in (override or {}).get("clip_order", []) if n in names]
    if wanted:
        return {"names": wanted + [n for n in natural if n not in wanted], "source": "qo'lda (takes.override.json)",
                "confidence": "high"}
    stems = [Path(n).stem for n in names]
    groups = [re.findall(r"\d+", s) for s in stems]
    if names and all(groups):
        keys = [tuple(int(g) for g in gs) for gs in groups]
        same_pattern = len({re.sub(r"\d+", "#", s) for s in stems}) == 1
        leading = all(re.match(r"\s*\d", s) for s in stems)
        if (same_pattern or leading) and len(set(keys)) == len(keys):
            return {"names": [n for _, n in sorted(zip(keys, names))], "source": "fayl nomidagi raqam",
                    "confidence": "high"}
    if names and created and all(created.get(n) for n in names) and len({created[n] for n in names}) == len(names):
        return {"names": sorted(names, key=lambda n: created[n]), "source": "yozilgan vaqt (metadata creation_time)",
                "confidence": "high"}
    return {"names": natural, "source": "aniq emas: nomlarda tartib raqami va metadata vaqti yo'q (mazmundan taklif)",
            "confidence": "low"}


def content_group(text: str, cfg: dict) -> int:
    """Mazmundan tartib: 0 - ilmoq (savol, "bilasizmi"), 2 - chaqiriq (obuna, murojaat), 1 - qolgani."""
    toks = [SA.norm(w) for w in text.split()]
    joined = " " + " ".join(toks) + " "
    hook = sum(1 for w in cfg["hook_words"] if f" {' '.join(map(SA.norm, w.split()))} " in joined) + ("?" in text)
    cta = sum(1 for w in cfg["cta_words"] if f" {' '.join(map(SA.norm, w.split()))} " in joined)
    if cta and cta >= hook:
        return 2
    return 0 if hook else 1


# ---------------------------------------------------------------- baholash

def media_issues(t: dict, m: dict | None, cfg: dict) -> tuple:
    """(jarima, sabablar, yuz ulushi yoki None) - ovoz va kadrlar bo'yicha."""
    if not m:
        return 0.0, [], None
    W, L = cfg["weights"], cfg["limits"]
    pen, why = 0.0, []
    audio = m.get("audio")
    if audio is not None and len(audio):
        a = audio[int(t["start"] * SR):int(t["end"] * SR)]
        if a.size:
            rms = 20 * math.log10(float(np.sqrt(np.mean(a.astype(np.float64) ** 2))) + 1e-9)
            clipped = float(np.mean(np.abs(a) >= float(L["clip_level"])))
            if clipped > float(L["clip_fraction"]):
                pen += W["clipping"]
                why.append(f"ovoz cho'qqisi kesilgan (clipping {clipped:.2%})")
            if rms < float(L["quiet_db"]):
                pen += W["too_quiet"]
                why.append(f"ovoz juda past ({rms:.0f} dB)")
    frames = [f for f in m.get("frames") or [] if t["start"] - 0.5 <= f["t"] <= t["end"] + 0.5]
    if not frames and m.get("frames"):
        mid = (t["start"] + t["end"]) / 2
        frames = [min(m["frames"], key=lambda f: abs(f["t"] - mid))]
    face_frac = None
    if frames:
        med = lambda key: float(np.median([f[key] for f in frames]))
        if med("sharp") < float(L["blur_var"]):
            pen += W["blur"]
            why.append(f"xira (keskinlik {med('sharp'):.0f})")
        if med("luma") < float(L["dark_luma"]):
            pen += W["dark"]
            why.append(f"qorong'i (yorqinlik {med('luma'):.0f})")
        if med("blown") > float(L["blown_frac"]):
            pen += W["blown"]
            why.append(f"yorug'lik kuygan ({med('blown'):.0%} oq)")
        moving = [f["shift"] for f in frames[1:]] or [0.0]
        if float(np.median(moving)) > float(L["shake_px"]):
            pen += W["shake"]
            why.append(f"kamera silkinadi ({float(np.median(moving)):.0f} px)")
        x0, x1 = m.get("crop", (0.0, 1.0))
        inside = [bool(f.get("face")) and f["face"][0] >= x0 - 0.02 and f["face"][2] <= x1 + 0.02 for f in frames]
        face_frac = sum(inside) / len(inside)
    return pen, why, face_frac


def score_takes(takes: list, clips: list, M: Matcher, cfg: dict, low_conf: float, media: dict | None) -> None:
    W, L = cfg["weights"], cfg["limits"]
    for t in takes:
        clip = clips[t["ci"]]
        ws = clip["words"][t["w0"]:t["w1"] + 1]
        norms = [SA.norm(str(w["word"])) for w in ws]
        why = [f"mos so'zlar {t['matched']}/{t['n_line']}" if t["n_line"] else "mos so'z topilmadi"]
        score = 100.0 - float(W["coverage"]) * (1.0 - min(1.0, float(t["cover"])))
        fill = [str(w["word"]).strip() for w, n in zip(ws, norms) if n and M.is_filler(n)]
        if fill:
            score -= W["filler"] * len(fill)
            why.append(f"to'ldiruvchi: {', '.join(fill[:4])}" + (f" (+{len(fill) - 4})" if len(fill) > 4 else ""))
        stut = sum(1 for a, b in zip(norms, norms[1:]) if a and a == b and not M.is_filler(a))
        if stut:
            score -= W["stutter"] * stut
            why.append(f"so'z takrorlandi ({stut})")
        extra = [str(clip["words"][k]["word"]).strip() for k in t["extras"]
                 if not M.is_filler(SA.norm(str(clip["words"][k]["word"])))]
        if extra:
            score -= W["extra_word"] * min(5, len(extra))
            why.append(f"ortiqcha so'z: {' '.join(extra[:5])}")
        if t.get("restart"):
            score -= W["retake_after"]
            why.append("to'xtatilgan urinish (gap qaytadan boshlangan)")
        if t.get("retake_after"):
            score -= W["retake_after"]
            why.append("keyin 'qaytadan' aytilgan")
        low = [w for w in ws if float(w.get("prob", 1.0)) < low_conf]
        if low:
            score -= W["low_conf"] * len(low) / len(ws)
            why.append(f"ishonchi past: {len(low)} so'z")
        gaps = [float(b["start"]) - float(a["end"]) for a, b in zip(ws, ws[1:])]
        long_gaps = [g for g in gaps if g > float(L["long_gap"])]
        if long_gaps:
            score -= W["long_gap"] * len(long_gaps)
            why.append(f"uzun pauza {max(long_gaps):.1f}s")
        t["prob"] = round(sum(float(w.get("prob", 1.0)) for w in ws) / len(ws), 3) if ws else 0.0
        if t.get("numflags"):
            why.append("raqam/so'z: " + ", ".join(f"{a}~{b}" for a, b in t["numflags"][:3]))
        pen, mwhy, face = media_issues(t, (media or {}).get(clip["name"]), cfg)
        score -= pen
        why += mwhy
        t["face_frac"] = face
        t["score"] = round(score, 1)
        t["reasons"] = why


def retake_flags(takes: list, clips: list, M: Matcher) -> None:
    """Dubldan keyin darhol (orada ko'pi bilan bitta so'z, 3 s ichida) "qaytadan" aytilsa - u tashlab ketilgan urinish.

    Orada bir nechta so'z bo'lsa "qaytadan" o'sha so'zlarga (keyingi gapning to'xtatilgan boshlanishiga) tegishli.
    """
    by_clip: dict = {}
    for t in takes:
        by_clip.setdefault(t["ci"], []).append(t)
    for ci, items in by_clip.items():
        items.sort(key=lambda t: t["j0"])
        clip = clips[ci]
        toks, retake = clip["_toks"], sorted(clip["_retake"])
        for n, t in enumerate(items):
            limit = items[n + 1]["j0"] if n + 1 < len(items) else len(toks)
            for p in retake:
                if not t["j1"] < p < limit:
                    continue
                between = [j for j in range(t["j1"] + 1, p) if j not in clip["_retake"] and not M.is_filler(toks[j][1])]
                gap = float(clip["words"][toks[p][0]]["start"]) - float(clip["words"][toks[t["j1"]][0]]["end"])
                if len(between) <= 1 and gap <= 3.0:
                    t["retake_after"] = True
                break


def choose(lines: list, takes: list, clips: list, cfg: dict, forced: dict) -> None:
    W = cfg["weights"]
    for li, line in enumerate(lines):
        cand = [t for t in takes if t["line"] == li]
        line["takes"] = [t["id"] for t in sorted(cand, key=lambda t: (-t["score"], t["id"]))]
        if not cand:
            line.update(chosen=None, runner=None, status="missing", why="hech bir klipda topilmadi")
            continue
        if any((t.get("face_frac") or 0) >= 0.5 for t in cand):
            for t in cand:
                if t.get("face_frac") is not None and t["face_frac"] < 0.5:
                    t["score"] = round(t["score"] - W["face_missing"], 1)
                    t["reasons"].append("yuz kadrda emas yoki 9:16 dan chiqib qoladi")
        if len(cand) > 1:
            last = max(cand, key=lambda t: (clips[t["ci"]]["order"], t["start"]))
            last["score"] = round(last["score"] + W["later_bonus"], 1)
            last["reasons"].append("oxirgi urinish")
        ranked = sorted(cand, key=lambda t: (-t["score"], -clips[t["ci"]]["order"], -t["start"]))
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        if li in forced:
            best = forced[li]
            second = next((t for t in ranked if t is not best), None)
            line.update(status="forced", why="qo'lda tanlangan (takes.override.json)")
        elif best["cover"] < float(cfg["match_low_cover"]):
            line.update(status="decide", why=f"to'liq dubl yo'q (eng yaxshisi {best['cover']:.0%})")
        elif best.get("margin") is not None and best["runner_line"] is not None and best["margin"] < float(cfg["match_margin"]):
            line.update(status="decide", why=f"{best['runner_line']}-gapga ham o'xshaydi (farq {best['margin']:.2f})")
        elif second and best["score"] - second["score"] < float(cfg["close_margin"]):
            line.update(status="close", why=f"ikki dubl deyarli teng: {best['score']:g} va {second['score']:g}")
        else:
            line.update(status="good", why="" if best["cover"] >= float(cfg["match_good_cover"])
                        else f"{best['n_line'] - best['matched']} so'z aniq eshitilmadi")
        if line["status"] in ("good", "close") and best.get("only_flagged"):
            line.update(status="decide", why="yagona dubl to'xtatilgan urinish ('qaytadan' aytilgan): ishlatilsinmi?")
        if line["status"] in ("good", "close") and best.get("prob", 1.0) < float(cfg["speech_min_prob"]):
            line.update(status="decide", why=f"nutq ishonchi past ({best['prob']:.2f}): shovqin bo'lishi mumkin")
        line["takes"] = [best["id"]] + [t["id"] for t in ranked if t is not best]
        line["chosen"], line["runner"] = best["id"], second["id"] if second else None
        line["takes_n"] = len(cand)


# ---------------------------------------------------------------- kesish

def _rms(audio: np.ndarray, t: float, half: float = 0.01) -> float:
    a = audio[max(0, int((t - half) * SR)):max(0, int((t + half) * SR))]
    return float(np.sqrt(np.mean(a.astype(np.float64) ** 2))) if a.size else 0.0


def quietest(audio: np.ndarray | None, lo: float, hi: float, pref: float, nudge: float) -> float:
    """[lo, hi] oralig'ida eng jim nuqta (pref ga yaqini afzal)."""
    pref = min(max(pref, lo), hi)
    if audio is None or not len(audio) or hi - lo < 0.01:
        return pref
    best, cost = pref, None
    for t in np.arange(lo, hi + 1e-9, 0.005):
        c = _rms(audio, float(t)) * (1.0 + 0.5 * abs(float(t) - pref) / max(nudge, 1e-3))
        if cost is None or c < cost:
            best, cost = float(t), c
    return best


def cut_points(t: dict, clip: dict, audio: np.ndarray | None, cfg: dict) -> dict:
    """So'z chegarasi + zaxira, eng jim nuqtaga surilgan. Oldingi/keyingi so'zga (dubldan tashqari) o'tmaydi."""
    words, dur = clip["words"], float(clip["duration"])
    s, e = float(words[t["w0"]]["start"]), float(words[t["w1"]]["end"])
    prev_end = float(words[t["w0"] - 1]["end"]) if t["w0"] > 0 else 0.0
    next_start = float(words[t["w1"] + 1]["start"]) if t["w1"] + 1 < len(words) else dur
    pad_in, pad_out, nudge = float(cfg["pad_in"]), float(cfg["pad_out"]), float(cfg["nudge"])
    lo, hi = max(0.0, prev_end + 0.02, s - pad_in - nudge), s - 0.01
    cin = quietest(audio, lo, hi, s - pad_in, nudge) if hi > lo else max(0.0, min(s, (prev_end + s) / 2))
    lo2, hi2 = e + 0.02, min(dur, next_start - 0.02, e + pad_out + nudge)
    cout = quietest(audio, lo2, hi2, e + pad_out, nudge) if hi2 > lo2 else min(dur, max(e, (e + next_start) / 2))
    warn = []
    if audio is not None and len(audio):
        speech = float(np.median([_rms(audio, x) for x in np.arange(s, e, 0.02)] or [0.0]))
        if speech > 0:
            for name, at in (("boshi", cin), ("oxiri", cout)):
                rel = 20 * math.log10(_rms(audio, at) / speech + 1e-9)
                if rel > float(cfg["limits"]["cut_loud_db"]):
                    warn.append(f"kesish {name} ({at:.2f}s) da ovoz bor ({rel:.0f} dB): so'z kesilishi mumkin")
    return {"cut_in": round(cin, 3), "cut_out": round(max(cout, cin + 0.1), 3), "cut_warn": warn}


# ---------------------------------------------------------------- tahlil (sof funksiya: testlar shuni chaqiradi)

def analyze(clips: list, cfg: dict, segs: list | None = None, override: dict | None = None,
            order: dict | None = None, media: dict | None = None, low_conf: float = 0.5) -> dict:
    """clips: [{"name", "kind" (video/audio), "duration", "words"}], tartib bo'yicha (order["names"]).

    Qaytaradi: lines, takes, entries (montaj ro'yxati), placements, unmatched, fragments, decisions.
    """
    override = override or {}
    M = Matcher(cfg)
    order = order or {"names": [c["name"] for c in clips], "source": "berilgan", "confidence": "high"}
    pos = {n: i for i, n in enumerate(order["names"])}
    clips = sorted(clips, key=lambda c: pos.get(c["name"], 10 ** 6))
    for i, c in enumerate(clips):
        c["order"] = i
        c["_toks"] = tokenize(c.get("words") or [])
        c["_retake"] = M.retake_positions([t for _, t in c["_toks"]])
        content = [(k, t) for k, t in c["_toks"] if not M.is_filler(t)]
        strong = [k for k, _ in content if float(c["words"][k].get("prob", 1.0)) >= float(cfg["speech_min_prob"])]
        c["speech"] = len(content) >= int(cfg["speech_min_words"]) or len(strong) >= 1
        if ((override.get("clips") or {}).get(c["name"]) or {}).get("role") == "product":
            c["_toks"], c["_retake"], c["speech"] = [], set(), False      # qo'lda: nutqsiz klip (butunligicha)
    pins = {p["clip"]: int(p["line"]) for p in override.get("pin", []) if "clip" in p and "line" in p}
    fragments: list = []
    if segs:
        mode = "script"
        takes = match_script(clips, segs, M, cfg, pins)
        lines = [{"n": s["n"], "text": s["text"], "raw": s["raw"], "ref": s["norm"]} for s in segs]
        fill_missing(takes, len(segs), cfg)
    else:
        mode = "transcript"
        takes, groups, fragments = group_lines([c for c in clips], M, cfg)
        lines = [{"ref": g["ref"]} for g in groups]
    # dubl raqamlari: klip ichida vaqt bo'yicha 1, 2, 3 ...
    for c in clips:
        own = sorted((t for t in takes if t["ci"] == c["order"]), key=lambda t: t["start"])
        for k, t in enumerate(own, 1):
            t["k"], t["id"] = k, f"{c['name']} #{k}"
    retake_flags(takes, clips, M)
    if mode == "transcript":
        # tartib: kliplar tartibida birinchi aytilgan joy; manba noaniq bo'lsa mazmundan (ilmoq oldin, chaqiriq oxirida)
        def key(li: int) -> tuple:
            own = [t for t in takes if t["line"] == li]
            first = min((clips[t["ci"]]["order"], t["start"]) for t in own)
            best = max(own, key=lambda t: len(t["text"]))
            group = content_group(best["text"], cfg) if order["confidence"] == "low" else 1
            return (group,) + first
        auto = sorted(range(len(lines)), key=key)
        renum = {li: n for n, li in enumerate(auto)}
        lines = [lines[li] for li in auto]
        for t in takes:
            t["line"] = renum[t["line"]]
            if t.get("runner_line") is not None:
                t["runner_line"] = renum[t["runner_line"]] + 1
        for n, line in enumerate(lines, 1):
            line["n"] = n
            texts = sorted((t for t in takes if t["line"] == n - 1), key=lambda t: -len(t["text"]))
            line["text"] = texts[0]["text"] if texts else ""
        # pin: klipning hamma dubllari shu gapga
        for t in takes:
            want = pins.get(t["clip"])
            if want and 1 <= want <= len(lines):
                t["line"], t["pinned"] = want - 1, True
    score_takes(takes, clips, M, cfg, low_conf, media)
    by_id = {t["id"]: t for t in takes}
    forced, notes = {}, []
    for f in override.get("force", []):
        n, clip = int(f.get("line", 0)), f.get("clip")
        if not 1 <= n <= len(lines):
            notes.append(f"override force: {n}-gap yo'q")
            continue
        if "in" in f and "out" in f:
            c = next((c for c in clips if c["name"] == clip), None)
            js = [j for j, (k, _) in enumerate(c["_toks"]) if float(f["in"]) <= float(c["words"][k]["start"]) and float(c["words"][k]["end"]) <= float(f["out"])] if c else []
            if not js:
                notes.append(f"override force: {clip} {f['in']}-{f['out']} oralig'ida so'z yo'q")
                continue
            t = _take(c, c["order"], n - 1, c["_toks"], js[0], js[-1], None, fit=0.0, runner_line=None,
                      runner_fit=0.0, margin=0.0, k=len([x for x in takes if x["ci"] == c["order"]]) + 1)
            t["id"] = f"{clip} #{t['k']} (qo'lda)"
            score_takes([t], clips, M, cfg, low_conf, media)
            takes.append(t)
        else:
            t = by_id.get(f"{clip} #{int(f.get('take', 1))}")
            if not t:
                notes.append(f"override force: {clip} #{f.get('take', 1)} dubli topilmadi")
                continue
            t["line"] = n - 1
        forced[n - 1] = t
    choose(lines, takes, clips, cfg, forced)
    by_id = {t["id"]: t for t in takes}

    # tartib (B rejimda override "order" - gap raqamlari)
    seq = list(range(len(lines)))
    if mode == "transcript" and override.get("order"):
        want = [int(n) - 1 for n in override["order"] if 1 <= int(n) <= len(lines)]
        seq = want + [i for i in seq if i not in want]

    # kesish nuqtalari (faqat tanlangan dubllar)
    for line in lines:
        if line.get("chosen"):
            t = by_id[line["chosen"]]
            t.update(cut_points(t, clips[t["ci"]], ((media or {}).get(t["clip"]) or {}).get("audio"), cfg))

    entries = []
    for li in seq:
        line = lines[li]
        if not line.get("chosen"):
            continue
        t = by_id[line["chosen"]]
        entries.append({"kind": "take", "clip": t["clip"], "ci": t["ci"], "take": t["id"], "lines": [line["n"]],
                        "in": t["cut_in"], "out": t["cut_out"], "w0": t["w0"], "w1": t["w1"]})
    # bir klipdagi ketma-ket gaplar (orasida boshqa so'z yo'q) bitta bo'lak bo'lib qoladi
    merged: list = []
    for e in entries:
        p = merged[-1] if merged else None
        if p and p["kind"] == "take" and p["clip"] == e["clip"] and e["w0"] == p["w1"] + 1 \
                and e["in"] - p["out"] <= float(cfg["merge_gap"]):
            p.update(out=e["out"], w1=e["w1"], lines=p["lines"] + e["lines"], take=p["take"] + " + " + e["take"])
        else:
            merged.append(dict(e))
    entries = merged

    # nutqsiz kliplar: kliplar tartibidagi qo'shnisidan keyin taklif qilinadi (hamisha tasdiqqa chiqadi)
    excluded = set(override.get("exclude", []))
    chosen_ci = {by_id[l["chosen"]]["ci"] for l in lines if l.get("chosen")}
    place_over = {p["clip"]: p for p in override.get("place", []) if "clip" in p}
    line_pos = {lines[li]["n"]: k for k, li in enumerate(seq)}
    placements, unmatched = [], []
    for c in clips:
        if c["name"] in excluded:
            continue
        has_take = any(t["ci"] == c["order"] for t in takes)
        if c["speech"] and not has_take and mode == "script":
            unmatched.append({"clip": c["name"], "text": " ".join(str(w["word"]).strip() for w in c["words"])[:200],
                              "why": "nutq bor, lekin skriptdagi hech bir gapga mos kelmadi (montajga qo'shilmadi)"})
            continue
        if c["speech"] or has_take:
            continue
        ov = place_over.get(c["name"])
        if ov and ov.get("skip"):
            placements.append({"clip": c["name"], "after_line": None, "skip": True, "source": "qo'lda: tashlab ketildi",
                               "confidence": "high"})
            continue
        if ov:
            placements.append({"clip": c["name"], "after_line": int(ov.get("after_line", 0)), "source": "qo'lda",
                               "confidence": "high"})
            continue
        prev = [x for x in clips if x["order"] < c["order"] and x["order"] in chosen_ci]
        after, src = 0, "boshida (oldida nutqli klip yo'q)"
        if prev:
            pc = prev[-1]
            ns = [n for l in lines if l.get("chosen") and by_id[l["chosen"]]["ci"] == pc["order"] for n in [l["n"]]]
            after = max(ns, key=lambda n: line_pos.get(n, -1))
            src = f"kliplar tartibida {pc['name']} dan keyin ({after}-gapdan keyin)"
        placements.append({"clip": c["name"], "after_line": after, "source": src, "confidence": "low",
                           "why": "nutqsiz klip: joyi taxminiy" + ("" if order["confidence"] == "high" else
                                                                  ", kliplar tartibi ham noaniq")})
    for p in placements:
        if p.get("skip"):
            continue
        c = next(c for c in clips if c["name"] == p["clip"])
        item = {"kind": "clip", "clip": c["name"], "ci": c["order"], "take": None, "lines": [], "after_line": p["after_line"]}
        idx = 0
        if p["after_line"]:
            target = line_pos.get(p["after_line"], len(seq))
            for k, e in enumerate(entries):
                if e["kind"] == "take" and min(line_pos.get(n, 10 ** 6) for n in e["lines"]) <= target:
                    idx = k + 1
        while idx < len(entries) and entries[idx]["kind"] == "clip":
            idx += 1                                   # oldin shu joyga qo'yilganlardan keyin (kliplar tartibi)
        entries.insert(idx, item)

    decisions = []
    if mode == "transcript" and order["confidence"] == "low" and not override.get("order"):
        decisions.append(f"Tartib taxminiy ({order['source']}): ilmoq boshida, chaqiriq oxirida - tasdiqlang yoki "
                         "takes.override.json \"order\"")
    for line in lines:
        if line["status"] in ("decide", "close", "missing"):
            decisions.append(f"{line['n']}-gap [{STATUS[line['status']]}]: {line['why']} - \"{line['text'][:70]}\"")
    for u in unmatched:
        decisions.append(f"{u['clip']}: {u['why']}")
    for p in placements:
        if p["confidence"] == "low":
            decisions.append(f"{p['clip']} (nutqsiz): taklif - {p['after_line']}-gapdan keyin; {p['why']}")
    for f in fragments:
        decisions.append(f"{f['clip']} {f['start']}s \"{f['text']}\": {f['why']} - qo'shilmadi")
    for line in lines:
        t = by_id.get(line.get("chosen") or "")
        for w in (t or {}).get("cut_warn", []):
            decisions.append(f"{line['n']}-gap ({t['id']}): {w}")
    decisions += notes
    for c in clips:
        c.pop("_toks", None)
        c.pop("_retake", None)
    return {"mode": mode, "lines": lines, "takes": takes, "entries": entries, "placements": placements,
            "unmatched": unmatched, "fragments": fragments, "decisions": decisions, "order": order,
            "excluded": sorted(excluded), "clips": [{k: v for k, v in c.items() if k != "words"} for c in clips]}


# ---------------------------------------------------------------- media

def load_audio(path: Path) -> np.ndarray | None:
    proc = subprocess.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-i", str(path), "-vn",
                           "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0 or not proc.stdout:
        return None
    return np.frombuffer(proc.stdout, np.float32)


def creation_time(path: Path) -> float | None:
    proc = subprocess.run([C.need_tool("ffprobe"), "-v", "error", "-show_entries", "format_tags:stream_tags",
                           "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    tags = [data.get("format", {}).get("tags", {})] + [s.get("tags", {}) for s in data.get("streams", [])]
    for tg in tags:
        for key in ("com.apple.quicktime.creationdate", "creation_time", "date"):
            value = next((v for k, v in (tg or {}).items() if k.lower() == key), None)
            if not value:
                continue
            try:
                stamp = datetime.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            except ValueError:
                continue
            if stamp.year >= 2001:
                return stamp.timestamp()
    return None


def frame_metrics(path: Path, meta: dict, cfg: dict, tdir: Path) -> list:
    """~1 fps, kichik o'lchamdagi kadrlar: yorqinlik, oq kuygan ulush, keskinlik, siljish, yuz (kesh bilan)."""
    if not meta["has_video"] or not meta["height"] or not meta["width"]:
        return []
    fps, h = float(cfg["frames_fps"]), int(cfg["frames_height"])
    w = max(2, int(round(h * meta["width"] / meta["height"] / 2)) * 2)
    cache = tdir / f"{C.slugify(path.name)}.frames.json"
    st = path.stat()
    key = f"{st.st_size}|{int(st.st_mtime)}|{fps:g}|{h}"
    if cache.is_file():
        old = C.read_json(cache)
        if old.get("key") == key:
            return old.get("frames", [])
    proc = subprocess.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path),
                           "-an", "-vf", f"fps={fps:g},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                          capture_output=True, stdin=subprocess.DEVNULL)
    import cv2
    import face as F
    det = None
    if hasattr(cv2, "FaceDetectorYN") and F.MODEL.is_file():
        try:
            cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
        except Exception:
            pass
        try:
            det = cv2.FaceDetectorYN.create(str(F.MODEL), "", (w, h), 0.6, 0.3, 50)
        except Exception:
            det = None
    frames, prev = [], None
    for i in range(len(proc.stdout) // (w * h * 3)):
        img = np.frombuffer(proc.stdout, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        g32 = gray.astype(np.float32)
        shift = 0.0
        if prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g32)
            shift = float(math.hypot(dx, dy))
        prev = g32
        box = None
        if det is not None:
            try:
                _, faces = det.detect(img)
            except Exception:
                faces = None
            if faces is not None and len(faces):
                x, y, fw, fh = [float(v) for v in max(faces, key=lambda f: f[2] * f[3])[:4]]
                box = [round(x / w, 3), round(y / h, 3), round((x + fw) / w, 3), round((y + fh) / h, 3)]
        frames.append({"t": round(i / fps, 3), "luma": round(float(gray.mean()), 1),
                       "blown": round(float((gray >= 250).mean()), 3),
                       "sharp": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
                       "shift": round(shift, 1), "face": box})
    C.write_json({"key": key, "frames": frames}, cache)
    return frames


def crop_window(meta: dict, style: dict, focus_x: float = 0.5) -> tuple:
    """assemble.py 9:16 ga kesganda gorizontal bo'yicha qoladigan qism (0..1)."""
    if not meta.get("width") or not meta.get("height"):
        return 0.0, 1.0
    target = float(style["video"]["width"]) / float(style["video"]["height"])
    cw = min(1.0, target / (meta["width"] / meta["height"]))
    x0 = (1.0 - cw) * float(focus_x)
    return round(x0, 3), round(x0 + cw, 3)


def whisper_cfg(style: dict, cfg: dict, segs: list | None) -> dict:
    wcfg = dict(style["whisper"])
    if segs and str(cfg.get("script_hint", "off")) == "hotwords":
        hw = hotwords(segs, cfg)
        if hw:
            wcfg["hotwords"] = hw
    return wcfg


def cache_key(path: Path, wcfg: dict) -> str:
    st = path.stat()
    keys = {k: wcfg.get(k) for k in ("model", "language", "beam_size", "vad_filter", "initial_prompt", "hotwords",
                                     "compute_type")}
    raw = json.dumps([path.name, st.st_size, int(st.st_mtime), keys], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def words_path(tdir: Path, path: Path) -> Path:
    return tdir / f"{C.slugify(path.name)}.words.json"


def transcribe_clips(paths: list, style: dict, wcfg: dict, tdir: Path) -> dict:
    """Har klip transkripsiyasi (kesh: fayl, model, til, hotwords o'zgarmasa qayta qilinmaydi)."""
    import transcribe as T
    out, model = {}, None
    for p in paths:
        wp, key = words_path(tdir, p), cache_key(p, wcfg)
        if wp.is_file():
            data = C.read_json(wp)
            if data.get("takes_key") == key:
                out[p.name] = data.get("words", [])
                continue
        if not C.ffprobe_info(p)["has_audio"]:
            C.write_json({"source": str(p), "words": [], "takes_key": key}, wp)
            out[p.name] = []
            continue
        if model is None:
            model = T.load_model(wcfg)
        C.info(f"  transkripsiya: {p.name}")
        res = T.transcribe_video(p, dict(style, whisper=wcfg), tdir, base_name=wp.name[:-len(".words.json")], model=model)
        data = C.read_json(wp)
        data["takes_key"] = key
        C.write_json(data, wp)
        out[p.name] = res["words"]
    return out


def load_override(folder: Path, work: Path) -> dict:
    """input/<papka>/takes.override.json (foydalanuvchi) + temp/<nom>/takes.override.json (ustun)."""
    out: dict = {}
    for p in (folder / OVERRIDE, work / OVERRIDE):
        if not p.is_file():
            continue
        data = C.read_json(p, "takes.override.json")
        if not isinstance(data, dict):
            raise C.MontajError(f"{p}: JSON obyekt bo'lishi kerak.")
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if isinstance(value, list):
                out[key] = out.get(key, []) + value if key not in ("order", "clip_order") else value
            elif isinstance(value, dict):
                out[key] = C.deep_merge(out.get(key, {}), value)
            else:
                out[key] = value
    return out


def thumb(video: Path, t: float, out: Path) -> str | None:
    if not out.is_file():
        C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}",
               "-i", str(video), "-frames:v", "1", "-vf", "scale=180:-2", "-q:v", "5", str(out)], check=False)
    return out.name if out.is_file() else None


def _write_if_changed(path: Path, text: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def _manifest_hash(data: dict) -> str:
    body = {k: v for k, v in data.items() if k != "_takes"}
    return hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def find_script(folder: Path, cfg: dict, script: str | Path | None) -> Path | None:
    if script:
        return C.need_file(script, "Skript fayli")
    for name in cfg["script_files"]:
        if (folder / name).is_file():
            return (folder / name).resolve()
    return None


def prepare(source: str | Path, style: dict, script: str | Path | None = None) -> dict | None:
    """Papka uchun dubl tanlash. Qaytaradi: {"manifest", "script_lines", "mode", "report", "decisions"} yoki None."""
    import assemble as A
    cfg = config(style)
    folder = Path(source)
    if not cfg.get("enabled", True):
        return None
    if (folder / "clips.json").is_file():
        C.info("Papkada clips.json bor: dubl tanlash o'tkazib yuboriladi (qo'lda ro'yxat ishlatiladi).")
        return None
    job = C.slugify(folder.name)
    work = C.TEMP_DIR / job
    tdir = work / "takes"
    (tdir / "thumbs").mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in C.VIDEO_EXTS | AUDIO_EXTS)
    if not files:
        raise C.MontajError(f"Papkada video yoki audio klip yo'q: {folder}")
    override = load_override(folder, work)
    excluded = set(override.get("exclude", []))
    spath = find_script(folder, cfg, script)
    segs = script_segments(SA.read_script_file(spath), cfg) if spath else None
    use = [p for p in files if p.name not in excluded]
    created = {p.name: creation_time(p) for p in use}
    order = order_clips([p.name for p in use], created, override)
    C.info(f"\n=== Dubl tanlash: {len(use)} klip, {'skript bilan (' + spath.name + ', ' + str(len(segs)) + ' gap)' if segs else 'skriptsiz'} ===")
    C.info(f"  Kliplar tartibi: {order['source']}")
    wcfg = whisper_cfg(style, cfg, segs)
    by = {p.name: p for p in use}
    words = transcribe_clips([by[n] for n in order["names"]], style, wcfg, tdir)
    import glossary as G
    gloss = G.load(style)
    if gloss:                                  # doim xato yoziladigan so'zlar (vaqtlar o'zgarmaydi)
        words = {n: G.apply_to_words(ws, gloss)[0] for n, ws in words.items()}
    clips, media, metas = [], {}, {}
    clip_over = override.get("clips", {}) if isinstance(override.get("clips"), dict) else {}
    for n in order["names"]:
        p = by[n]
        meta = metas[n] = C.ffprobe_info(p)
        clips.append({"name": n, "path": str(p), "kind": "video" if meta["has_video"] else "audio",
                      "duration": meta["duration"], "words": words.get(n, [])})
        focus = float((clip_over.get(n) or {}).get("focus_x", 0.5))
        media[n] = {"audio": load_audio(p) if meta["has_audio"] else None,
                    "frames": frame_metrics(p, meta, cfg, tdir), "crop": crop_window(meta, style, focus)}
    res = analyze(clips, cfg, segs, override, order, media, float(style["whisper"].get("low_confidence", 0.5)))
    by_id = {t["id"]: t for t in res["takes"]}

    # ko'rinish kadrlari (kesish boshi va oxiri)
    for line in res["lines"]:
        t = by_id.get(line.get("chosen") or "")
        if t and metas[t["clip"]]["has_video"]:
            stem = C.slugify(f"{t['clip']}_{t['k']}")
            t["thumb_in"] = thumb(by[t["clip"]], t["cut_in"] + 0.03, tdir / "thumbs" / f"{stem}_in.jpg")
            t["thumb_out"] = thumb(by[t["clip"]], t["cut_out"] - 0.06, tdir / "thumbs" / f"{stem}_out.jpg")
    for e in res["entries"]:
        if e["kind"] == "clip" and metas[e["clip"]]["has_video"]:
            e["thumb"] = thumb(by[e["clip"]], metas[e["clip"]]["duration"] / 2,
                               tdir / "thumbs" / f"{C.slugify(e['clip'])}_mid.jpg")

    # montaj ro'yxati (assemble.py)
    fade = float(cfg["fade_ms"]) / 1000.0
    items = []
    for e in res["entries"]:
        p, meta = by[e["clip"]], metas[e["clip"]]
        if e["kind"] == "take":
            item = {"file": str(p), "role": "speech" if meta["has_video"] else "voiceover",
                    "in": e["in"], "out": e["out"], "fade": fade, "lines": e["lines"], "take": e["take"]}
            if not meta["has_video"]:
                item["cover"] = []
        else:
            item = {"file": str(p), "role": "product", "take": None, "lines": []}
        extra = {k: v for k, v in (clip_over.get(e["clip"]) or {}).items() if k not in ("file", "in", "out")}
        item.update(extra)
        e["expect"], e["expect_text"] = [], []
        if e["kind"] == "take":
            if res["mode"] == "script":
                for n in e["lines"]:
                    toks, _ = SA.read_script(segs[n - 1]["raw"])
                    e["expect"] += [t["norm"] for t in toks]
                    e["expect_text"] += [C.strip_markup(t["raw"]) for t in toks]
            else:
                ws = next(c for c in clips if c["name"] == e["clip"])["words"][e["w0"]:e["w1"] + 1]
                for w in ws:
                    nrm = SA.norm(str(w["word"]))
                    if nrm:
                        e["expect"].append(nrm)
                        e["expect_text"].append(str(w["word"]).strip())
        items.append(item)
    if not items:
        raise C.MontajError("Montajga hech narsa tushmadi: kliplarda mos nutq ham, nutqsiz klip ham topilmadi. "
                            "report.html ni ko'ring yoki takes.override.json bilan tanlang.")
    manifest = {"name": job, "product_audio": "keep", "clips": items}
    manifest["_takes"] = _manifest_hash(manifest)
    mpath = work / "clips.json"
    use_path, hand = mpath, False
    if mpath.is_file():
        old = C.read_json(mpath, "clips.json")
        generated = old.get("_takes") == _manifest_hash(old)
        template = {k: v for k, v in old.items() if k != "_takes"} == A.template_for_folder(folder)
        if not (generated or template):
            hand = True
            use_path = work / "takes.clips.json"
            C.warn(f"{mpath} qo'lda o'zgartirilgan: shu ishlatiladi. Dubl tanlash taklifi: {use_path} "
                   "(ishlatish uchun clips.json ni o'chiring yoki qarorlarni takes.override.json ga yozing).")
    C.write_json(manifest, use_path)
    lines_path = None
    if res["mode"] == "script":
        lines_path = work / "script.lines.txt"
        placed = [segs[n - 1]["raw"] for e in res["entries"] if e["kind"] == "take" for n in e["lines"]]
        _write_if_changed(lines_path, "\n".join(placed) + "\n")
    data = dict(res, folder=str(folder), job=job, script=str(spath) if spath else None,
                script_lines=str(lines_path) if lines_path else None, manifest=str(mpath if hand else use_path),
                proposal=str(use_path), hand_edited=hand, total_lines=len(res["lines"]),
                created=datetime.datetime.now().isoformat(timespec="seconds"), verify=None)
    C.write_json(data, work / "takes.json")
    report = write_report(data, work)
    print_summary(data, report)
    return {"manifest": mpath if hand else use_path, "script_lines": lines_path, "mode": res["mode"],
            "report": report, "decisions": res["decisions"]}


# ---------------------------------------------------------------- tekshiruv

def frame_luma(video: Path, t: float) -> float | None:
    proc = subprocess.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{max(0.0, t):.3f}",
                           "-i", str(video), "-frames:v", "1", "-vf", "scale=64:-2,format=gray", "-f", "rawvideo", "-"],
                          capture_output=True, stdin=subprocess.DEVNULL)
    return float(np.frombuffer(proc.stdout, np.uint8).mean()) if proc.stdout else None


def _runs(idx: list) -> list:
    out: list = []
    for i in idx:
        if out and i == out[-1][-1] + 1:
            out[-1].append(i)
        else:
            out.append([i])
    return out


def check_text(expected: list, expected_text: list, words: list, M: Matcher) -> dict:
    """Kutilgan matn va yig'ilgan video transkripsiyasi: qamrov, tushib qolgan, ortiqcha, tartibi buzilgan so'zlar."""
    heard_i = [(k, SA.norm(str(w.get("word", "")))) for k, w in enumerate(words)]
    heard_i = [(k, n) for k, n in heard_i if n]
    heard = [n for _, n in heard_i]
    pairs = SA.align_pairs(expected, heard)
    ok = [(i, j) for i, j in pairs if i is not None and j is not None and M.sim(expected[i], heard[j]) >= SA.MATCH]
    got_i, got_j = {i for i, _ in ok}, {j for _, j in ok}
    at_of = {}
    for i, j in ok:
        at_of[i] = float(words[heard_i[j][0]]["start"])
    def near(i: int) -> float:
        before = [at_of[x] for x in at_of if x < i]
        return round(max(before), 2) if before else 0.0
    missing = [{"text": " ".join(expected_text[i] for i in run), "at": near(run[0]), "norm": [expected[i] for i in run]}
               for run in _runs([i for i in range(len(expected)) if i not in got_i])]
    extra = [{"text": " ".join(str(words[heard_i[j][0]]["word"]).strip() for j in run),
              "at": round(float(words[heard_i[run[0]][0]]["start"]), 2), "norm": [heard[j] for j in run]}
             for run in _runs([j for j in range(len(heard)) if j not in got_j and not M.is_filler(heard[j])])]
    moved = []
    for m in list(missing):
        for x in list(extra):
            if len(m["norm"]) >= 2 and SequenceMatcher(None, " ".join(m["norm"]), " ".join(x["norm"])).ratio() >= 0.8:
                moved.append({"text": m["text"], "expected_at": m["at"], "heard_at": x["at"]})
                missing.remove(m)
                extra.remove(x)
                break
    for item in missing + extra:
        item.pop("norm", None)
    return {"coverage": round(len(got_i) / len(expected), 3) if expected else 0.0, "expected_words": len(expected),
            "heard_words": len(heard), "missing": missing, "extra": extra, "out_of_order": moved}


def check_junctions(video: Path, times: list, words: list, cfg: dict) -> list:
    """Har ulanish: so'z o'rtasidan kesilmaganmi (transkripsiya), qora kadr yo'qmi, chertish (click) yo'qmi."""
    L = cfg["limits"]
    audio = load_audio(video)
    ov = float(L["word_cut_overlap"])
    out = []
    for t in times:
        problems = []
        for w in words:
            if float(w["start"]) < t - ov and float(w["end"]) > t + ov:
                problems.append(f"so'z ulanish ustida: \"{str(w['word']).strip()}\" ({w['start']:.2f}-{w['end']:.2f}s)")
        for at in (t - 0.04, t + 0.02):
            luma = frame_luma(video, at)
            if luma is not None and luma < float(L["black_luma"]):
                problems.append(f"qora kadr {at:.2f}s (yorqinlik {luma:.0f})")
                break
        if audio is not None and len(audio):
            k = int(t * SR)
            win = audio[max(0, k - SR // 200):k + SR // 200].astype(np.float64)
            ctx = audio[max(0, k - SR // 10):k + SR // 10].astype(np.float64)
            if win.size > 2 and ctx.size > 2:
                jump = float(np.max(np.abs(np.diff(win))))
                base = float(np.median(np.abs(np.diff(ctx))))
                if jump > float(L["click_jump"]) and jump > 8 * base + 1e-4:
                    problems.append(f"chertish (click) ehtimoli: sakrash {jump:.2f}")
        out.append({"at": round(t, 3), "ok": not problems, "problems": problems})
    return out


def verify(work: Path, words: list, style: dict) -> dict | None:
    """Yig'ilgan videoning transkripsiyasini kutilgan matn bilan solishtiradi va ulanishlarni tekshiradi."""
    tpath, spath = work / "takes.json", work / "segments.json"
    if not tpath.is_file() or not spath.is_file():
        return None
    data, seg = C.read_json(tpath), C.read_json(spath)
    cfg = config(style)
    M = Matcher(cfg)
    entries = data.get("entries", [])
    if Path(seg.get("manifest", "")).resolve() != Path(data.get("proposal", "")).resolve() \
            or len(seg.get("segments", [])) != len(entries):
        res = {"skipped": "yig'ilgan video dubl tanlash ro'yxatidan emas (qo'lda clips.json): matn tekshirilmadi"}
        times = [s["start"] for s in seg.get("segments", [])[1:]]
        res["junctions"] = check_junctions(Path(seg["video"]), times, words, cfg)
    else:
        expected = [t for e in entries for t in e.get("expect", [])]
        expected_text = [t for e in entries for t in e.get("expect_text", [])]
        res = check_text(expected, expected_text, words, M)
        res["junctions"] = check_junctions(Path(seg["video"]), [s["start"] for s in seg["segments"][1:]], words, cfg)
        if data.get("mode") == "script":
            placed = {n for e in entries for n in e.get("lines", [])}
            res["script_lines"] = f"{len(placed)}/{data.get('total_lines', len(data.get('lines', [])))}"
    res["at"] = datetime.datetime.now().isoformat(timespec="seconds")
    data["verify"] = res
    C.write_json(data, tpath)
    write_report(data, work)
    C.info("\n=== Dubl tanlash tekshiruvi (yig'ilgan video qayta transkripsiya qilindi) ===")
    if "coverage" in res:
        C.info(f"  Qamrov: {res['coverage']:.0%} ({res['expected_words']} kutilgan so'z, {res['heard_words']} eshitildi)"
               + (f", skript gaplari: {res['script_lines']}" if res.get("script_lines") else ""))
        for m in res["missing"][:10]:
            C.warn(f"tushib qolgan (~{m['at']}s): \"{m['text']}\"")
        for x in res["extra"][:10]:
            C.info(f"  ortiqcha ({x['at']}s): \"{x['text']}\"")
        for o in res["out_of_order"]:
            C.warn(f"tartibi boshqa: \"{o['text']}\" ({o['heard_at']}s da eshitildi)")
    else:
        C.warn(res["skipped"])
    bad = [j for j in res["junctions"] if not j["ok"]]
    C.info(f"  Ulanishlar: {len(res['junctions']) - len(bad)}/{len(res['junctions'])} toza")
    for j in bad:
        C.warn(f"ulanish {j['at']}s: " + "; ".join(j["problems"]))
    C.info(f"  Hisobot: {work / 'report.html'}")
    return res


# ---------------------------------------------------------------- hisobot

def print_summary(data: dict, report: Path) -> None:
    by_id = {t["id"]: t for t in data["takes"]}
    C.info(f"  Rejim: {'skript bo' + chr(39) + 'yicha' if data['mode'] == 'script' else 'skriptsiz (transkripsiya)'}; "
           f"tartib: {data['order']['source']}")
    for line in data["lines"]:
        t = by_id.get(line.get("chosen") or "")
        r = by_id.get(line.get("runner") or "")
        head = f"  {line['n']:>2}. [{STATUS[line['status']]:<11}]"
        if not t:
            C.info(f"{head} \"{line['text'][:60]}\" - {line['why']}")
            continue
        C.info(f"{head} {t['id']} {t['cut_in']:.2f}-{t['cut_out']:.2f}s ball {t['score']:g}"
               + (f" | 2-nomzod {r['id']} {r['score']:g}" if r else "") + f"  \"{line['text'][:50]}\"")
    for p in data["placements"]:
        C.info(f"   +  {p['clip']} (nutqsiz): " + ("tashlab ketildi" if p.get("skip") else f"{p['after_line']}-gapdan keyin")
               + f" [{p['source']}]")
    if data["decisions"]:
        C.info("  Tasdiqqa chiqadigan qarorlar:")
        for d in data["decisions"]:
            C.info(f"    - {d}")
    C.info(f"  Montaj ro'yxati: {data['proposal']}\n  Hisobot: {report}")


def write_report(data: dict, work: Path) -> Path:
    esc = lambda x: html.escape(str(x))
    by_id = {t["id"]: t for t in data["takes"]}
    colors = {"good": "#1f9d55", "close": "#d68910", "decide": "#c0392b", "missing": "#7f8c8d", "forced": "#2471a3"}

    def img(name: str | None, label: str) -> str:
        """Kadr rasm faylning ichiga joylanadi: hisobot bitta fayl bo'lib istalgan joyda ochiladi."""
        path = work / "takes" / "thumbs" / str(name or "")
        if not name or not path.is_file():
            return ""
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return (f'<figure><img src="data:image/jpeg;base64,{data}" alt="{esc(label)}"><figcaption>{esc(label)}</figcaption>'
                "</figure>")

    rows = []
    for line in data["lines"]:
        t, r = by_id.get(line.get("chosen") or ""), by_id.get(line.get("runner") or "")
        chosen = "—"
        if t:
            chosen = (f"<b>{esc(t['id'])}</b><br>{t['cut_in']:.2f}–{t['cut_out']:.2f} s, ball <b>{t['score']:g}</b>"
                      f"<br><small>{esc('; '.join(t['reasons']))}</small>"
                      + (f"<br><small class=warn>{esc('; '.join(t['cut_warn']))}</small>" if t.get("cut_warn") else "")
                      + (f"<br><small>gap mosligi {t['fit']:.2f}, boshqa gap ({esc(t['runner_line'])}) {t['runner_fit']:.2f}</small>"
                         if t.get("runner_line") else ""))
        runner = (f"{esc(r['id'])}<br>ball {r['score']:g} (farq {t['score'] - r['score']:+.1f})<br><small>{esc('; '.join(r['reasons']))}</small>"
                  if r and t else "—")
        thumbs = img(t.get("thumb_in"), "kirish") + img(t.get("thumb_out"), "chiqish") if t else ""
        rows.append(f"<tr><td class=n>{line['n']}</td><td><span class=chip style='background:{colors[line['status']]}'>"
                    f"{esc(STATUS[line['status']])}</span><div>{esc(line['text'])}</div><small>{esc(line.get('why', ''))}</small>"
                    f"<br><small>dubllar: {len(line.get('takes', []))}</small></td><td>{chosen}</td><td>{runner}</td>"
                    f"<td class=thumbs>{thumbs}</td></tr>")
    seq = []
    for e in data["entries"]:
        if e["kind"] == "take":
            seq.append(f"<li>{esc(e['take'])} — gap {', '.join(map(str, e['lines']))} ({e['in']:.2f}–{e['out']:.2f} s)</li>")
        else:
            seq.append(f"<li>{esc(e['clip'])} — nutqsiz klip{img(e.get('thumb'), 'kadr')}</li>")
    v = data.get("verify")
    if v:
        vhtml = ""
        if "coverage" in v:
            vhtml += (f"<p>Qamrov: <b>{v['coverage']:.0%}</b> ({v['expected_words']} kutilgan so'z, {v['heard_words']} eshitildi)"
                      + (f", skript gaplari {esc(v['script_lines'])}" if v.get("script_lines") else "") + "</p>")
            for key, title in (("missing", "Tushib qolgan"), ("extra", "Ortiqcha"), ("out_of_order", "Tartibi boshqa")):
                if v.get(key):
                    vhtml += f"<h3>{title}</h3><ul>" + "".join(
                        f"<li>{esc(x['text'])} <small>({esc(x.get('at', x.get('heard_at', '')))} s)</small></li>" for x in v[key]) + "</ul>"
        else:
            vhtml += f"<p class=warn>{esc(v.get('skipped', ''))}</p>"
        js = v.get("junctions", [])
        vhtml += f"<p>Ulanishlar: {sum(1 for j in js if j['ok'])}/{len(js)} toza</p><ul>" + "".join(
            f"<li class=warn>{j['at']:.2f} s: {esc('; '.join(j['problems']))}</li>" for j in js if not j["ok"]) + "</ul>"
    else:
        vhtml = "<p>Hali tekshirilmagan: pipeline yig'ilgan videoni transkripsiya qilgach shu yer to'ladi.</p>"
    extras = ""
    if data["unmatched"]:
        extras += "<h2>Skriptga mos kelmagan nutqli kliplar</h2><ul>" + "".join(
            f"<li><b>{esc(u['clip'])}</b>: {esc(u['text'])}</li>" for u in data["unmatched"]) + "</ul>"
    if data["fragments"]:
        extras += "<h2>Qo'shilmagan bo'laklar</h2><ul>" + "".join(
            f"<li>{esc(f['clip'])} {f['start']} s: \"{esc(f['text'])}\" — {esc(f['why'])}</li>" for f in data["fragments"]) + "</ul>"
    if data["placements"]:
        extras += "<h2>Nutqsiz kliplar</h2><ul>" + "".join(
            f"<li><b>{esc(p['clip'])}</b>: " + ("tashlab ketildi" if p.get("skip") else f"{p['after_line']}-gapdan keyin")
            + f" <small>({esc(p['source'])}{'; ' + esc(p['why']) if p.get('why') else ''})</small></li>" for p in data["placements"]) + "</ul>"
    decisions = "".join(f"<li>{esc(d)}</li>" for d in data["decisions"]) or "<li>Yo'q</li>"
    order_cls = "" if data["order"]["confidence"] == "high" else " class=warn"
    page = f"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dubl tanlash</title><style>
:root{{--bg:#fafafa;--fg:#1d1d1f;--muted:#666;--line:#ddd;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141414;--fg:#eee;--muted:#aaa;--line:#333;--card:#1e1e1e}}}}
body{{font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:16px;max-width:1280px}}
table{{border-collapse:collapse;width:100%;background:var(--card)}}td,th{{border-bottom:1px solid var(--line);padding:8px;vertical-align:top;text-align:left}}
.chip{{color:#fff;border-radius:10px;padding:1px 8px;font-size:12px;display:inline-block;margin-bottom:4px}}
small{{color:var(--muted)}}.warn{{color:#c0392b}}.n{{font-weight:700;width:28px}}
figure{{display:inline-block;margin:0 6px 0 0}}figure img{{width:90px;border-radius:4px;display:block}}figcaption{{font-size:11px;color:var(--muted)}}
.thumbs{{white-space:nowrap}}@media (max-width:700px){{td{{display:block}}tr{{display:block;border-bottom:2px solid var(--line)}}}}
</style></head><body>
<h1>Dubl tanlash: {esc(data['job'])}</h1>
<p>Rejim: <b>{'skript bo‘yicha' if data['mode'] == 'script' else 'skriptsiz (transkripsiya)'}</b>{(' — ' + esc(Path(data['script']).name)) if data.get('script') else ''}.
Kliplar tartibi: <span{order_cls}>{esc(data['order']['source'])}</span>. Yaratildi: {esc(data['created'])}.</p>
<h2>Tasdiq kerak bo'lgan qarorlar</h2><ul>{decisions}</ul>
<h2>Gaplar</h2><table><tr><th>#</th><th>Gap</th><th>Tanlangan dubl</th><th>2-nomzod</th><th>Kesish kadrlari</th></tr>{''.join(rows)}</table>
{extras}<h2>Montaj tartibi</h2><ol>{''.join(seq)}</ol>
<h2>Tekshiruv</h2>{vhtml}
<p><small>Qo'lda tanlash: {esc(work / OVERRIDE)} (pin, force, exclude, place, order, clip_order, clips). docs/TAKES.md</small></p>
</body></html>"""
    out = work / "report.html"
    out.write_text(page, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Klip papkasi: dubllarni topish, eng yaxshisini tanlash, so'z chegarasida kesish, tartib.")
    ap.add_argument("source", help="Klip papkasi (masalan input/promo)")
    ap.add_argument("--style", help="Per-video style.json (temp/<nom>/style.json)")
    ap.add_argument("--brand", help="Brend nomi")
    ap.add_argument("--script", help="Skript matni (standart: papkadagi script.txt)")
    ap.add_argument("--verify", action="store_true", help="Yig'ilgan videoni tekshirish (temp/<nom>/orig.words.json bilan)")
    args = ap.parse_args()
    style = C.load_style(args.style, args.brand)
    folder = Path(args.source)
    if not folder.is_dir():
        raise C.MontajError(f"Papka topilmadi: {folder}")
    if args.verify:
        work = C.TEMP_DIR / C.slugify(folder.name)
        words = C.read_json(work / "orig.words.json", "Yig'ilgan video so'zlari").get("words", [])
        return 0 if verify(work, words, style) is not None else 1
    C.busy_acquire(f"takes: {folder.name}")
    res = prepare(folder, style, args.script)
    return 0 if res else 1


if __name__ == "__main__":
    C.run_main(main)
