---
name: promo
description: Edit a restaurant or product promo from many separate clips (chef talking, food close-ups, packing, voice-over) in the style of samples/sample 20 - words beside the speaker, big italic glowing hero and price, product label chips, small voice-over captions. Use when the user gives promo footage or asks for a video "like sample 20".
---

# /promo — multi-clip restaurant / product promo

Arguments: `<arguments supplied in the user prompt>` (clip folder in `input/` or a `clips.json`, optional brand).
Talk to the user in **Uzbek**, short numbered steps. Read first, fully: `docs/PROMO.md` (the recipe, measured
from sample 20), then `AGENTS.md`, `docs/PLAYBOOK.md`, `docs/AGENT_MEMORY.md`. Do not guess a field: check
`scripts/assemble.py` (manifest format) and `scripts/elements.py` (`label`, `aside`, presets `promo`, `vo`).
Python is `.venv/Scripts/python.exe` from the project root. Never read `.env`. Never write into `input/` or `samples/`.

## What you need from the user (ask once, in one message)

Clips in `input/<promo>/` (order by file name), brand or brandless, item names and their order ("1-set Mol
qovurg'asi" ...), the price exactly as written, logo and music files if wanted. Never invent a price, item
name, logo or music.

## Workflow

1. `handoff.py show`; claim the job with `handoff.py set ... --video <folder>` style note.
   Look at every clip (`frames.py <clip> --n 6 -o temp/<job>/...`).
2. `pipeline.py input/<promo> --style temp/<job>/style.json --prepare-only` creates `temp/<job>/clips.json`
   (template) and assembles. Fix roles (speech / product / voiceover), order, `in`/`out`, voiceover `cover`,
   then run again. Product ranges are protected from silence cutting (`segments.json`).
3. Text: one approval message (marked text with `[?word]`, plan table, stills). Voice-over cues start with
   `{vo}`, hero phrases `{promo}**...**`, price `{promo}<small line> !!<price>!! <unit>`. Words shown beside
   the speaker go to `aside` and are removed from the captions.
4. `elements.json` per `docs/PROMO.md` §4: `aside`, behind-person `title` (preset promo), `label` per item
   (cut-out food image from the client's own frame: `frames.py --at`, `cutout.py`), handwritten `aside`
   (font Caveat) at the end. No broll/stage/scene/grade in a video that uses behind_person.
5. Stills at every text event; compare with sample 20 (`studio.py compare "samples/sample 20.MP4" ... --out
   temp/<job>/compare.json`). Approval -> draft -> final, exactly as in `/namuna`.
6. Music/SFX: you cannot hear; render two variants if the user asks, let them choose.

## Handoff

Write `handoff.py set "..." --video <folder> --agent <claude|codex>` after every milestone (text sent, answer
word for word, elements written, before/after render). Parallel rules: `docs/PARALLEL.md`.
