---
name: namuna
description: Edit a video so it looks like the reference reels in samples/ (the user's target style) - lockup captions with word slide-in, yellow glow accents, caps/heavy hook titles, marker highlights, voice-message scenes, follow card. Use when the user asks for a video "like the samples" / "namunadagidek", or for any talking-head edit without other style instructions.
---

# /namuna — edit in the sample style

Arguments: `<arguments supplied in the user prompt>` (video path, optional brand, optional script file).
Talk to the user in **Uzbek**, short numbered steps. The user is a beginner programmer and a
professional video editor; the reference for "good" is the 14 reels in `samples/`.

Read first, fully: `docs/NAMUNA_USLUBI.md` (what the samples do and how each thing is reproduced),
then `AGENTS.md` and `docs/PLAYBOOK.md`. Do not guess a flag, preset or element field: check
`--help`, `docs/NAMUNA_USLUBI.md` or `scripts/elements.py` (`CAPTION_PRESETS`, `ELEMENT_TYPES`).

Python is always `.venv/Scripts/python.exe` from the project root. Never read or print `.env`.
Never write into `input/` or `samples/`.

## What "like the samples" means (check every item before rendering)

1. **Captions are lockups, not karaoke lines.** In each sentence mark ONE hero phrase
   (`*white big*`, `**yellow big**`, `!!huge!!`); the rest of the sentence becomes the small line
   under it, automatically fitted to the hero line's width. A short sentence with a mark stays one
   cue. Unmarked sentences fall back to 3-4 word cues: use that only for filler speech.
2. **Lowercase, tight, centered at chest height.** Do not change `tracking`, `case` or
   `position_y` unless a brand's `brand.json` says so. Proper nouns keep their capital: write
   `Rus`, `Instagram`, `SMM` that way in the text.
3. **Yellow is rare.** At most one yellow phrase per cue, and not in every cue. The star (`\*`) goes
   only on the hook and on 1-2 key numbers: `**\*3 oyda**`.
4. **The hook (first 2 s) uses a different preset**: `{caps,y=0.2}` or `{heavy,x=0.07,y=0.3}`.
5. **Markers** (`==word==`, `~~word~~`) are for interview-style long sentences (`{marker}`) and for
   the small label above a `{heavy}` word. Not for decoration.
6. **Elements every 3-4 seconds**, chosen from the table in `docs/NAMUNA_USLUBI.md` §5.
   Enumeration → `list`; right/wrong → `choice` (glass); a number → `!!n!!` or `stat`;
   testimonial audio → `scene` + `voice` + `{karaoke}` cues; ending → `follow`.
7. **Ending**: a `follow` card for 2.5-3.5 s with the brand's handle. Logo only from a file the
   user provided (`brands/<name>/`); without a logo use `name`.

## Workflow

1. **Inputs.** Video, brand (or brandless), script. Read notes: `scripts/feedback.py show [--brand X]`.
   Look at the footage: `scripts/frames.py <video> --n 12`.
2. **Transcript.** Follow the `transcribe-uz` skill: transcribe, correct text only, show the user,
   wait for approval. Whisper invents text over laughter/music: remove squeezed runs.
3. **Mark up the approved text.** Put the marks and cue tags into `corrections.json` (`text`
   fields) so they survive re-runs: e.g. `{"index": 12, "count": 3, "was": "3 oyda rus",
   "text": "**\\*3 oyda Rus**"}`. A word that starts with `{preset}` starts a new cue.
   Re-apply corrections; never edit `orig.words.json` or timings.
4. **First pass.** `scripts/pipeline.py <video> [--brand X] --words temp/<job>/orig.words.fixed.json`
   (exit code 3 = waiting for approval, not an error). Read `temp/<job>/subs.srt`: every cue should
   read as "hero line + small line" or a plain short cue.
5. **Plan and elements.** Write `temp/<job>/plan.md` (PLAYBOOK §1) and `temp/<job>/elements.json`.
   Times are in the cut video's seconds (`cut.words.json`).
6. **Look before rendering.** `--stills t1,t2,...` (up to 12) at the middle of every hook, every
   element and 3-4 ordinary cues. Open the image. Compare with the sample sheets
   (`scripts/frames.py "samples/sample 7.mp4" --n 8` etc.): size, weight, position, yellow amount.
   Fix and repeat until it matches. Nothing may leave the safe frame.
7. **Approval, then render.** Show the user the caption text and the stills. Only after a clear
   yes: `--approve-subs`. For sound choices render two variants (`--elements` with and without
   `sfx`, `-o` different names) and let the user listen: you cannot hear.
8. **After the render.** `scripts/frames.py output/<file>.mp4 --n 8`, check the report lines
   (`Tekshiruv`, `Platforma`, `Nutq ustunligi`). Report in Uzbek: file, what was done, what is
   still different from the samples, questions.
9. **Learn.** During parallel editing, save remarks and proposals in your own deferred_learning.md.
   At the end, when the other agent is idle, one agent updates feedback, glossary and AGENT_MEMORY,
   and any approved shared settings, then commits.

## Clip folder (takes: best take per line, right order)

When the input is a folder of clips (with or without `script.txt`), `pipeline.py` first runs `scripts/takes.py`
(read `docs/TAKES.md`): it transcribes every clip, finds bad and repeated takes, keeps the best take of each line,
cuts at word boundaries (padding, quietest point, short fade), orders the lines (script order; without a script:
numbered names -> recording time -> content, the last one low confidence) and assembles. Originals are never changed;
"removing" only means leaving a take out of the edit list.

1. `pipeline.py input/<folder> --style temp/<job>/style.json --prepare-only`. Read the printed "Tasdiqqa chiqadigan
   qarorlar" list and `temp/<job>/report.html` (status colours, score and reason, runner-up, cut thumbnails).
2. For clips without speech and for every close call / needs-decision / missing line, look at the frames
   (`frames.py <clip> --n 6 -o temp/<job>/...`), write your proposal into `temp/<job>/takes.override.json`
   (`pin`, `force`, `exclude`, `place`, `order`, `clip_order`, `clips`) and re-run. Never accept a low-confidence item silently.
3. The ONE approval message carries: `report.html`, the order and its source, each close call / needs decision /
   missing line with your choice and reason, the places of clips without speech, the marked subtitle text, stills.
   The subtitle text approval is never skipped.
4. Write the user's answer into the override file and the video note, re-run. After transcription of the assembled
   video the pipeline prints the verification (coverage %, missing / extra / out-of-order words, every junction):
   report any problem.

## Autonomy (derive, flag, never invent)

- Derive names, numbers, places, offers and the call to action from the speech (transcript) and from text
  clearly visible in frames (`frames.py ... -o temp/<job>/...`): signboard, uniform, screen, document. Use it as
  text only; never cut a logo out of a frame.
- Never invent a name, number, price, handle or claim. Anything uncertain goes into the ONE approval message
  as `[?word]` with its source (time in the video, speech or frame).
- Ask the user only for what cannot be derived (for example an Instagram handle, a brand to use, music or a logo
  file) and ask it once, inside the approval message. Without a music or logo file: the video's own sound, no logo.

## Fast order: ONE approval message (user rule, 2026-10-07)

No question lists. Apply your best guess to every doubtful word and flag it inline as `[?word]`.
Before asking, prepare everything: marked text, plan table, pictures found and cut out
(`scripts/cutout.py`), stills of every key moment (alternatives side by side when a choice matters),
the follow card on a still, credits. Send it in ONE message; the user answers once. After "ha" on the
text write it into your video's `temp/<job>/HOLAT.md` and go straight to the draft; after "ha" on the draft, the final.
Uzbek speech: transcribe with `--model yuldashev222/whisper-small-uz-v1-ct2`. Disease or key-term
names can go in a big red box (`~~term~~` with `captions.mark2_big: true` in a per-video style file,
`--style temp/<job>/style.json`). Pictures: cut-out stickers matching the exact word, under the
caption block, never over face, text or hands. Full-frame stock b-roll only when asked
(rejected on "doktor 1"; sample 15/16 analysis in `docs/NAMUNA_USLUBI.md` §5a).

## Honest limits (tell the user, do not fake)

- Read `docs/STUDIO.md` when comparing samples, making an approved draft, preparing a batch,
  suggesting emphasis, drawing handnotes/arrows/phone cards, making a cover or placing text behind
  a person. Preflight checks structure and warns about rhythm/color; the agent still reviews frames.
- Behind-person text uses the approved PPHumanSeg model; inspect hair/hand edges in stills.
  Handnotes use a handwriting font, arrows draw along a path. 3D type and custom illustrated scenes
  still need separate graphics (see `docs/NAMUNA_USLUBI.md` §7).
- Movie clips, music and logos come only from files the user gives.
- You judge frames, not motion or sound. For motion, take three close frames:
  `scripts/frames.py <video> --at 2.00,2.08,2.20`.

## Parallel work and handoff

Run `scripts/handoff.py show` first: every unfinished video is listed with its owner. Work only on
your assigned video. Claim/update it with `scripts/handoff.py set "..." --video <video> --agent
<claude|codex>`; read it with `show --video <video>`. Record every milestone and exact user approval.
Use `clear --video <video> --agent <owner>` when done: approvals remain in the completed note.
Project HOLAT.md is only for project-wide state. Never touch the other agent's folder or note.

Work only in your own temp/<job>/ and full per-video style.json; pass --style to pipeline,
compose, transcribe and compare_models, frames.py -o for your frame sheets, and compare_models
--out-dir temp/<job>/compare. Use distinct output names and set MONTAJ_AGENT in your terminal.
Heavy jobs wait FIFO and report the holder; MONTAJ_BUSY_TIMEOUT defaults to 7200 seconds.
Never delete locks manually. While another agent has an unfinished video, do not edit scripts/,
style/style.json, brands/, docs/ or skills, and do not run selftest. If code must change, stop
and tell the user. No git commits during parallel editing. Defer feedback, glossary and
AGENT_MEMORY to the end: one agent writes them when the other is idle. See docs/PARALLEL.md.
