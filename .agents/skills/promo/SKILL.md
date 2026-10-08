---
name: promo
description: Edit a restaurant or product promo from a folder of separate clips (chef or staff talking, food close-ups, packing, voice-over) fully on its own - item names, sets, price, offer and call to action come only from the speech and clearly visible text in frames, clip roles are decided by the agent, and every promo gets its own look from docs/PROMO.md. Use when the user gives promo footage, a clip folder, or asks for a promo / reklama video.
---

# /promo — autonomous multi-clip promo

Arguments: `<arguments supplied in the user prompt>` (clip folder or `clips.json`, optional existing brand).
Talk to the user in **Uzbek**, short numbered steps. Read first, fully: `docs/PROMO.md`, then `AGENTS.md`,
`docs/PLAYBOOK.md`, `docs/AGENT_MEMORY.md`. Never guess a field or flag: check `--help`, `scripts/assemble.py`,
`scripts/promo_looks.py`, `scripts/elements.py`. Python is `.venv/Scripts/python.exe` from the project root.
Never read `.env`. Never write into `input/` or `samples/`.

## Autonomy (the user gives only the clips)

1. Everything comes from the footage: transcribe all speech and voice-over clips; read clearly visible text in
   frames (box, uniform, signboard, menu, price tag) with `frames.py` - as text only, never cut out a logo.
2. Item names, set numbers, price, offer and call to action only if said or clearly visible. Never invent.
   Uncertain -> `[?word]` with its source (clip + time) in the approval message.
3. Decide the clip roles yourself from the sound, the "Kliplar bo'yicha nutq" table and the frames; fix
   `temp/<job>/clips.json` and re-run. Show the role list in the approval message.
4. Ask only once, only for the Instagram handle of the follow card (none given -> no handle). Music and logo
   only from files the user gives; otherwise the clips' own sound, no logo.

## Workflow

1. `handoff.py show`; claim `handoff.py set "..." --video <folder> --agent <claude|codex>`.
2. Per-video style: copy `style/style.json` to `temp/<job>/style.json`, Uzbek speech model
   `yuldashev222/whisper-small-uz-v1-ct2`. `pipeline.py <folder> --style temp/<job>/style.json --prepare-only`.
3. Look: `promo_looks.py list` (never repeat the previous promo's look), `promo_looks.py palette
   temp/<job>/<job>.mp4 --out temp/<job>/palette.json`, choose the direction from content + footage + samples,
   `promo_looks.py apply <look> --style temp/<job>/style.json --accent "#RRGGBB"`.
4. Text and `elements.json` per `docs/PROMO.md` §3-5 (`{vo}` for voice-over, look tags for hook/hero/price,
   `label` per item with a cut-out from the client's own frame, `aside` beside the speaker, follow at the end).
5. Stills at every text event; check face, safe zone, timing.
6. ONE approval message: role table, marked text with `[?]` + sources, what was found where (names, price,
   offer), plan table, look + one-line reason, stills, the one Instagram question.
7. "ha" -> write it word for word into the video note -> draft -> "ha" -> final -> `ffprobe` + frame sheet ->
   `promo_looks.py record <look> --job <job> --accent "#RRGGBB"` -> review.md, AGENT_MEMORY (or
   deferred_learning.md in parallel work).

## Handoff

Write `handoff.py set "..." --video <folder> --agent <claude|codex>` after every milestone (text sent, the
user's answer word for word, elements written, before/after render). Parallel rules: `docs/PARALLEL.md`.
