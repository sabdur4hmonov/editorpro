---
name: montaj
description: Edit a raw talking-head video into a finished vertical Reel for a brand using this project's scripts (cut, captions, graphics, images, brand, audio). Use when the user gives a raw video and asks to edit / montaj it.
---

# /montaj — full edit of one video

Arguments: `<arguments supplied in the user prompt>` (video path, optional brand name, optional script file).

You are the editor. The user (a beginner programmer, professional video editor) gives a raw video and a
brand; you make every other decision. Talk to the user in **Uzbek**, short numbered steps.

**Default look:** unless the brand's `brand.json` or the user says otherwise, the target style is the
reference reels in `samples/`. Read `docs/NAMUNA_USLUBI.md` and follow the `/namuna` skill's
checklist ("What 'like the samples' means") for captions, hook, elements and ending.
Read `docs/STUDIO.md` for sample comparisons, automatic preflight, approved draft renders,
emphasis proposals, behind-person titles, new graphics, covers and preparation-only batches.
Show stills, draft and final in the chat; record tested lessons in `docs/AGENT_MEMORY.md`.

## Before anything

1. Read `AGENTS.md` and `docs/PLAYBOOK.md` fully. They are the source of truth for commands, element
   fields and editing rules. Do not guess a flag or field: check `--help` or the code.
2. `git status` and `git log --oneline -5`. If a watcher window is running (`jobs/watcher.json` has a
   recent `alive_at`), ask the user to close it: only one agent works at a time.
3. Python is always `.venv/Scripts/python.exe`, run from the project root.
4. Never read, print or commit `.env`. Never write into `input/` or `samples/`.

## Workflow

1. **Resolve inputs.** Video exists? If the user named a brand, it must exist in `brands/` (if
   missing, run the `/brend` flow or ask). If the user named no brand, this is a **brandless**
   video: omit `--brand`, use the general style, add no logo or end card, invent nothing.
   Look for a script: `<video>.txt` next to the video or the third argument. Read
   `scripts/feedback.py show [--brand NAME]` (the pipeline also prints these notes) and follow them.
   Look at the footage first (`scripts/frames.py <video> --n 12`) and decide the video type
   (PLAYBOOK §0): talking head, stage/interview, or an already-finished reel.
2. **First pass.** `scripts/pipeline.py <video> --brand <brand> [--script <txt>]`. Exit code 3 means
   "approval needed", not an error. Read the printed cut list and subtitle text.
3. **Understand the content.** Read `temp/<job>/subs.srt`, `cut.words.json`, and
   `script.notes.json` if present. Write the plan table to `temp/<job>/plan.md` (PLAYBOOK §1).
4. **Mark up captions.** Edit `temp/<job>/subs.srt` text lines only (never the timing lines):
   one emphasis per cue, per AGENTS.md "Subtitr matni va belgilar". Do not change wording the user
   wrote in a script; flag doubtful words instead.
5. **Design graphics.** Write `temp/<job>/elements.json` following PLAYBOOK §2–3. For every image
   you need, walk the ladder in PLAYBOOK §4: brand assets → `icon` → HTML you draw
   (`scripts/html_render.py`) → stock (`scripts/images.py search`, then LOOK at `candidates.jpg`
   with the Read tool, then `pick`) → AI image (only if `GEMINI_API_KEY` is set; ask before first use).
6. **Look before rendering.** `pipeline.py ... --stills t1,t2,...` (up to 12 times, one inside each
   element). Open `temp/<job>/stills.jpg` and judge it honestly as a designer: legibility, face not
   covered, inside the safe-zone frame, one focal point, brand colour used once. Fix and repeat.
7. **Get approval.** Show the user: the full subtitle text (with low-confidence / changed words
   called out), the removed repeats, the plan in 3–6 lines, and the stills image path. Wait for a
   clear yes. Only then run with `--approve-subs`.
8. **Verify the render.** Check the printed `Tekshiruv` and `Platforma` lines. Run
   `scripts/frames.py <output video>` and open the sheet it prints; for a doubtful animation use
   `--at 2.0,2.1,2.25` (three close frames).
9. **Report** in Uzbek: output file, what you did (short), image sources / credits that must be
   mentioned, AI-image note if any, and ask the user to listen for audio (you cannot hear).
10. **Learn from the answer.** Record every piece of feedback the user gives with
    `scripts/feedback.py add "..." [--brand NAME] [--video PATH]`, turn it into a setting in
    `brand.json` / `style.json` when it maps to one, and add repeated whisper mistakes to the
    glossary (`scripts/glossary.py add`). The same remark must not be needed twice.
11. If you changed scripts, `style/style.json`, a brand or docs: run
    `scripts/selftest.py --no-whisper --offline`, then `git commit`.

## Hard rules

- Subtitles are never burned in without the user's explicit approval in this conversation.
- Every number shown on screen was said in the video or given by the user.
- Music, film clips and logos only from files the user provided.
- If a script fails, find the cause and fix it; never skip a stage silently.

## Handoff (another agent may continue this work)

Run `scripts/handoff.py show` before starting and continue unfinished work found there. Write
`scripts/handoff.py set "..." --agent <claude|codex>` after every milestone (text sent for approval,
user's answer, elements written, before and after a render): video, brand, what is done, what the
user still has to answer, the exact next command. Usage limits end a session without warning.
