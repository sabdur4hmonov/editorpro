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
Show stills, draft and final in the chat; defer shared learning during parallel editing as below.

## Before anything

1. Read `AGENTS.md` and `docs/PLAYBOOK.md` fully. They are the source of truth for commands, element
   fields and editing rules. Do not guess a flag or field: check `--help` or the code.
2. `git status` and `git log --oneline -5`. If a watcher window is running (`jobs/watcher.json` has a
   recent `alive_at`), ask the user to close it before direct Claude Code/Codex work.
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
10. **Learn from the answer.** During parallel editing, save proposals only in your own
    `temp/<job>/deferred_learning.md`. At the end, when the other agent is idle, one agent records them with
    `scripts/feedback.py add "..." [--brand NAME] [--video PATH]`, turn it into a setting in
    `brand.json` / `style.json` when it maps to one, and add repeated whisper mistakes to the
    glossary (`scripts/glossary.py add`). The same remark must not be needed twice.
11. Shared changes are prohibited while another agent has an unfinished video. In an idle maintenance session,
    if you changed scripts, `style/style.json`, a brand or docs: run
    `scripts/selftest.py --no-whisper --offline`, then `git commit`.

## Autonomy (derive, flag, never invent)

- Derive names, numbers, places, offers and the call to action from the speech (transcript) and from text
  clearly visible in frames (`frames.py ... -o temp/<job>/...`): signboard, uniform, screen, document. Use it as
  text only; never cut a logo out of a frame.
- Never invent a name, number, price, handle or claim. Anything uncertain goes into the ONE approval message
  as `[?word]` with its source (time in the video, speech or frame).
- Ask the user only for what cannot be derived (for example an Instagram handle, a brand to use, music or a logo
  file) and ask it once, inside the approval message. Without a music or logo file: the video's own sound, no logo.

## Fast order: ONE approval message (user rule, 2026-10-07)

The user does not want question lists. Each round trip costs them time.

1. **Apply your best guess yourself** for every doubtful word and flag it inline as `[?word]`. Do not
   send a numbered list of questions. Proper nouns, Russian words: keep exactly as said, fix only
   misheard letters.
2. **Prepare everything before asking**: corrected and marked text, plan table, pictures already found
   and cut out, stills at every key moment (with alternatives when a choice matters, e.g. two accent
   colours side by side), the follow card on a still, credits.
3. **Send one message**: full marked text with `[?]` flags, plan table, stills, credits, and the few
   answers you need. The user answers once.
4. After "ha" on the text: write the approval word for word into your video's `temp/<job>/HOLAT.md`, then go straight to the
   draft. After "ha" on the draft: the final. Do not stop in between when your own checks pass.
5. **Uzbek transcription**: use `--model yuldashev222/whisper-small-uz-v1-ct2` (in the HF cache). The
   default `small` produced unusable Uzbek on "doktor 1"; the fine-tuned model got whole sentences right.
6. **Pictures** are cut-out stickers (`scripts/cutout.py`, no frame or border), real CC0/public-domain
   photos, each exactly matching its word (the user rejects loosely related pictures). Place them under
   the caption block; above it only when hands, the safe zone or the follow card are in the way; never
   over the face, the text or the hands. Check every cut-out on the `--sheet` and on stills.
7. **Full-frame stock b-roll** only when the user asks for it; on "doktor 1" it was rejected.

## Hard rules

- Subtitles are never burned in without the user's explicit approval in this conversation.
- Every number shown on screen was said in the video or given by the user.
- Music, film clips and logos only from files the user provided.
- If a script fails, find the cause. If shared code needs changing while another agent owns an
  unfinished video, stop and tell the user; never skip a stage silently.

## Parallel work and handoff

Run `scripts/handoff.py show` first: it lists every unfinished video and its owner. Work only on
your assigned video; never touch another agent's video folder or note. Claim yours with
`scripts/handoff.py set "Started ..." --video <video> --agent <claude|codex>` and use
`show --video <video>` to read its full note. Repeat set after each milestone, including the user's
exact approval, brand, files and next command. Finish with `clear --video <video> --agent <owner>`;
this marks done and retains approvals. Project HOLAT.md is for project-wide state only.

Use only your own `temp/<job>/` and a full per-video `temp/<job>/style.json` copy. Pass `--style`
to pipeline/compose/transcribe/compare_models. Put frame sheets in that folder with `frames.py -o`;
pass `--out-dir temp/<job>/compare` to compare_models. Output video names must be distinct.
Set MONTAJ_AGENT in your own terminal. Heavy jobs wait FIFO, report the holder, and stop clearly
after MONTAJ_BUSY_TIMEOUT seconds (default 7200). Do not delete locks manually.

While another agent has an unfinished video, do not edit scripts/, style/style.json, brands/,
docs/ or skills, and do not run selftest. If code changes are needed, stop and tell the user.
No git commits during parallel editing. Feedback, glossary and AGENT_MEMORY are written at the
end by one agent when the other is idle; until then use only your deferred_learning.md.
Never change the branch or merge. See docs/PARALLEL.md for verified command examples.
