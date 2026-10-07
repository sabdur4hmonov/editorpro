"""Navbat almashish: bir agent to'xtaganda (limit, tanaffus) ikkinchisi qayerdan davom etishini biladi.

    python scripts/handoff.py show                       hozirgi holat: eslatma, band belgisi, oxirgi ishlar, git
    python scripts/handoff.py set "matn" [--agent NOM]   holatni yozib qo'yish (har muhim qadamdan keyin)
    python scripts/handoff.py clear                      ish tugagach eslatmani tozalash

Eslatma loyiha papkasidagi HOLAT.md da turadi (gitga kirmaydi). Claude Code, Codex va chat (watcher)
bir xil faylni o'qiydi. Limit to'satdan tugashi mumkin: shuning uchun eslatma oxirida emas, ish davomida yoziladi.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

import common as C

FILE = C.ROOT / "HOLAT.md"


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


def show() -> int:
    C.info("=== Navbat almashish holati ===")
    if FILE.is_file():
        C.info(f"\nEslatma (HOLAT.md, {ago(time.time() - FILE.stat().st_mtime)} yozilgan):")
        C.info(FILE.read_text(encoding="utf-8").rstrip())
    else:
        C.info("\nEslatma yo'q (HOLAT.md yozilmagan): oldingi agent ishni tugatgan yoki hali boshlamagan.")
    busy = C.busy_state()
    if busy:
        C.info(f"\nBAND: {busy.get('what')} ({busy.get('agent')}), {ago(time.time() - float(busy.get('started', 0)))} "
               "boshlangan. U tugamaguncha og'ir ish boshlamang.")
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
    sub.add_parser("show", help="Hozirgi holatni ko'rsat")
    s = sub.add_parser("set", help="Holatni yozib qo'y")
    s.add_argument("text", help="Nima qilindi, nima kutilmoqda, keyingi qadam (buyrug'i bilan)")
    s.add_argument("--agent", help="Kim yozdi: claude, codex, chat (standart: MONTAJ_AGENT yoki 'agent')")
    sub.add_parser("clear", help="Eslatmani o'chir (ish to'liq tugaganda)")
    args = ap.parse_args()
    if args.cmd == "show":
        return show()
    if args.cmd == "clear":
        FILE.unlink(missing_ok=True)
        C.info("Eslatma tozalandi.")
        return 0
    text = args.text.strip()
    if not text:
        raise C.MontajError("Bo'sh eslatma yozilmaydi.")
    agent = (args.agent or os.environ.get("MONTAJ_AGENT", "") or "agent").strip()
    FILE.write_text(f"# Holat ({time.strftime('%Y-%m-%d %H:%M')}, {agent})\n\n{text}\n", encoding="utf-8")
    C.info(f"Yozildi: {FILE}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
