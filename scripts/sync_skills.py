"""Bitta manbadan Claude va Codex skill nusxalarini tekshiradi/yangilaydi."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("montaj", "namuna", "brend", "transcribe-uz", "promo")


def expected(source: str, agent: str) -> str:
    if agent == "codex":
        source = re.sub(r"(?m)^argument-hint:[^\r\n]*\r?\n", "", source)
        source = source.replace("$ARGUMENTS", "<arguments supplied in the user prompt>")
    return source


def sync(root: Path = ROOT, apply: bool = False) -> list[str]:
    # Read every source before writing anything: missing sources cannot partly update skills.
    sources = {name: (root / "docs/claude_skills" / name / "SKILL.md").read_text(encoding="utf-8")
               for name in NAMES}
    changed = []
    for agent, directory in (("claude", ".claude"), ("codex", ".agents")):
        for name, source in sources.items():
            path = root / directory / "skills" / name / "SKILL.md"
            text = expected(source, agent)
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                changed.append(path.relative_to(root).as_posix())
                if apply:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Nusxalar eskirgan bo'lsa 1-kod")
    mode.add_argument("--apply", action="store_true", help="Faqat NAMES dagi SKILL.md nusxalarini yangilash")
    args = parser.parse_args()
    try:
        changed = sync(apply=args.apply)
    except OSError as error:
        parser.exit(2, f"Skill manbasi/nusxasi xatosi: {error}\n")
    for path in changed:
        print(("Yangilandi: " if args.apply else "Eskirgan: ") + path)
    print("SKILLS: " + ("sinxron" if not changed or args.apply else "yangilash kerak"))
    return int(bool(changed) and not args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
