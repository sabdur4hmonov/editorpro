"""Navbat almashish: bir agent to'xtaganda (limit, tanaffus) ikkinchisi qayerdan davom etishini biladi.

    python scripts/handoff.py show                       loyiha va barcha tugallanmagan video egalari
    python scripts/handoff.py show --video input/a.mp4    shu videoning to'liq eslatmasi
    python scripts/handoff.py set "matn" --video input/a.mp4 --agent codex
    python scripts/handoff.py clear --video input/a.mp4 --agent codex  videoni tugagan deb belgilash

Loyiha HOLAT.md umumiy holat uchun; har video temp/<video>/HOLAT.md da egasi bilan saqlanadi.
Limit to'satdan tugaydi: eslatma oxirida emas, ish davomida yoziladi.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

import common as C

FILE = C.ROOT / "HOLAT.md"
PREFIX = "<!-- handoff: "


def video_note(video: str | Path) -> tuple[Path, str]:
    source = Path(video).resolve()
    folder = source.parent if C.is_inside(source, C.TEMP_DIR) and source.stem == "cut" else C.TEMP_DIR / C.slugify(source.stem)
    if folder.resolve().parent != C.TEMP_DIR.resolve():
        raise C.MontajError("Video eslatmasi faqat temp/<video>/ ichida bo'lishi kerak.")
    return folder / "HOLAT.md", str(source)


def read_note(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    line = text.splitlines()[0] if text else ""
    try:
        if not line.startswith(PREFIX) or not line.endswith(" -->"):
            raise ValueError
        data = json.loads(line[len(PREFIX):-4])
        if not isinstance(data, dict) or not data.get("agent") or data.get("status") not in ("unfinished", "done"):
            raise ValueError
    except (ValueError, TypeError):
        raise C.MontajError(f"Video eslatmasi metama'lumoti buzuq; ustidan yozilmadi: {path}") from None
    return data, text


def unfinished_notes() -> list[dict]:
    rows = []
    for path in sorted(C.TEMP_DIR.glob("*/HOLAT.md")):
        try:
            data, _ = read_note(path)
            if data["status"] == "unfinished":
                rows.append(dict(data, note=str(path)))
        except (OSError, C.MontajError) as error:
            rows.append({"agent": "noma'lum", "video": path.parent.name, "note": str(path), "error": str(error)})
    return rows


def write_video_note(video, text: str | None, agent: str, done=False) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", agent):
        raise C.MontajError("Video eslatmasi uchun --agent claude yoki codex kabi aniq nom kerak.")
    path, source = video_note(video)
    with C.file_mutex(path.parent / ".handoff.guard"):
        old, old_text = read_note(path) if path.exists() else ({}, "")
        if old and old["agent"] != agent:
            raise C.MontajError(f"Bu video {old['agent']} ga tegishli; {agent} uning eslatmasini o'zgartira olmaydi: {path}")
        # cut.mp4 is a derived alias for the same video folder, not a new input claim.
        alias = Path(source).name == "cut.mp4" and Path(source).parent == path.parent.resolve()
        if old and old.get("video") != source and not alias:
            raise C.MontajError(f"Bir xil temp nomi boshqa videoga tegishli: {old.get('video')}. Boshqa video nomi kerak.")
        if done and not old:
            raise C.MontajError("Tugatish uchun avval shu videoning eslatmasini yozing.")
        body = old_text.split("\n", 1)[1] if done else f"# Holat ({time.strftime('%Y-%m-%d %H:%M')}, {agent})\n\n{text.strip()}\n"
        data = {"agent": agent, "video": old.get("video", source), "status": "done" if done else "unfinished"}
        C.atomic_text(path, PREFIX + json.dumps(data, ensure_ascii=False) + " -->\n" + body)
    return path


def ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds} soniya oldin"
    if seconds < 5400:
        return f"{seconds // 60} daqiqa oldin"
    if seconds < 172800:
        return f"{seconds // 3600} soat oldin"
    return f"{seconds // 86400} kun oldin"


def recent_jobs(limit: int = 5) -> list:
    """temp/<nom>/result.json lar: pipeline har ishdan keyin holatini shu yerga yozadi."""
    rows = []
    for path in C.TEMP_DIR.glob("*/result.json"):
        try:
            data = C.read_json(path)
            rows.append((path.stat().st_mtime, path.parent.name, str(data.get("status", "?")),
                         str(data.get("brand", "") or "brendsiz"), str(data.get("video", ""))))
        except (OSError, C.MontajError, ValueError):
            continue
    return sorted(rows, reverse=True)[:limit]


def git_lines() -> list:
    out = []
    for args in (["rev-parse", "--abbrev-ref", "HEAD"], ["status", "--short"], ["log", "--oneline", "-n", "3"]):
        try:
            p = subprocess.run(["git", *args], cwd=str(C.ROOT), capture_output=True, text=True, timeout=20,
                               encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return ["  git topilmadi"]
        if p.returncode != 0:
            return ["  bu papka git ombori emas (yoki git xato berdi)"]
        out.append(p.stdout.rstrip())
    changed = [ln for ln in out[1].splitlines() if ln.strip()]
    lines = [f"  branch: {out[0].strip()}",
             f"  commit qilinmagan o'zgarishlar: {len(changed)} ta" + (" (" + ", ".join(ln[3:] for ln in changed[:6])
                                                                      + (" ..." if len(changed) > 6 else "") + ")" if changed else "")]
    lines += ["  " + ln for ln in out[2].splitlines()]
    return lines


STATUS = {"need_approval": "subtitr matni tasdiqlanishi kutilmoqda", "stills": "ko'rik kadrlari olingan (render qilinmagan)",
          "done": "render tugagan", "ok": "tugagan", "error": "xato bilan to'xtagan"}


def show(video=None) -> int:
    C.info("=== Navbat almashish holati ===")
    if FILE.is_file():
        C.info(f"\nEslatma (HOLAT.md, {ago(time.time() - FILE.stat().st_mtime)} yozilgan):")
        C.info(FILE.read_text(encoding="utf-8").rstrip())
    else:
        C.info("\nEslatma yo'q (HOLAT.md yozilmagan): oldingi agent ishni tugatgan yoki hali boshlamagan.")
    notes = unfinished_notes()
    C.info("\nTugallanmagan video eslatmalari:" if notes else "\nTugallanmagan video eslatmasi yo'q.")
    for row in notes:
        C.info(f"  Egasi: {row['agent']}; video: {row['video']}\n    Eslatma: {row['note']}")
        if row.get("error"):
            C.warn(row["error"])
    if video:
        path, _ = video_note(video)
        C.info(f"\nShu video eslatmasi ({path}):")
        C.info(read_note(path)[1] if path.is_file() else "Hali yozilmagan.")
    busy = C.busy_state()
    if busy:
        C.info(f"\nBAND: {busy.get('what')} ({busy.get('agent')}), {ago(time.time() - float(busy.get('started', 0)))} "
               "boshlangan. Yangi og'ir ish navbatda kutadi.")
    else:
        C.info("\nBand emas: hozir hech qanday og'ir ish ketmayapti.")
    jobs = recent_jobs()
    C.info("\nOxirgi ishlar (temp/):" if jobs else "\ntemp/ da ish yo'q.")
    for mtime, name, status, brand, video in jobs:
        C.info(f"  {name}: {STATUS.get(status, status)} [{brand}], {ago(time.time() - mtime)}\n      video: {video}")
    C.info("\nGit:")
    for line in git_lines():
        C.info(line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Agentlar orasida navbat almashish eslatmasi (HOLAT.md).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sh = sub.add_parser("show", help="Loyiha, barcha tugallanmagan videolar va CPU holati")
    sh.add_argument("--video", help="Shu videoning to'liq temp/<video>/HOLAT.md eslatmasi")
    s = sub.add_parser("set", help="Holatni yozib qo'y")
    s.add_argument("text", help="Nima qilindi, nima kutilmoqda, keyingi qadam (buyrug'i bilan)")
    s.add_argument("--agent", help="Kim yozdi: claude, codex, chat (standart: MONTAJ_AGENT yoki 'agent')")
    s.add_argument("--video", help="Faqat shu video eslatmasi; yozilmasa loyiha HOLAT.md")
    cl = sub.add_parser("clear", help="Video tugagan deb belgilanadi; loyihada eski clear xatti-harakati")
    cl.add_argument("--video")
    cl.add_argument("--agent")
    args = ap.parse_args()
    if args.cmd == "show":
        return show(args.video)
    if args.cmd == "clear":
        if args.video:
            path = write_video_note(args.video, None, args.agent or os.environ.get("MONTAJ_AGENT", ""), done=True)
            C.info(f"Video tugagan deb belgilandi, matn/tasdiqlar saqlandi: {path}")
            return 0
        FILE.unlink(missing_ok=True)
        C.info("Eslatma tozalandi.")
        return 0
    text = args.text.strip()
    if not text:
        raise C.MontajError("Bo'sh eslatma yozilmaydi.")
    agent = (args.agent or os.environ.get("MONTAJ_AGENT", "") or "agent").strip()
    if args.video:
        path = write_video_note(args.video, text, agent)
    else:
        path = FILE
        with C.file_mutex(C.TEMP_DIR / ".project_handoff.guard"):
            C.atomic_text(path, f"# Holat ({time.strftime('%Y-%m-%d %H:%M')}, {agent})\n\n{text}\n")
    C.info(f"Yozildi: {path}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
