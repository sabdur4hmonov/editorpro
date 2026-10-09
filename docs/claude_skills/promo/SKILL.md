---
name: promo
description: Edit a restaurant or product promo from a folder of separate clips (chef or staff talking, food close-ups, packing, voice-over) fully on its own - item names, sets, price, offer and call to action come only from the speech and clearly visible text in frames, clip roles are decided by the agent, and every promo gets its own look from docs/PROMO.md. Use when the user gives promo footage, a clip folder, or asks for a promo / reklama video.
argument-hint: "<clip folder in input/ or clips.json> [brand]"
---

# /promo — autonomous multi-clip promo

Use docs/FORMATS.md for format and the existing promo system for D subtype/look; report both
reasons in the ONE approval. Read docs/QUALITY.md: semantic object/count/process graphics,
group/hero per docs/MOTION_DESIGN.md, per-video no_repeat/enforce_final, every overlay-frame
face safety and measured quality fix lists. Unknown is not pass. Use only spoken products/prices.
Stronger primary, subtle second; taste remains user review. Record real user verdicts through
existing histories (local during parallel work). Reuse cached transcripts/features to save tokens.

Read `docs/MOTION.md`: shared motion, per-video `motion_override`, recorded choice, glyph
warnings, timecoded filmstrips for labels/price/follow and aligned before/after sheets.
After subtitle approval, show compose's subtle/stronger mixes and cue sheets/waveforms.
The user judges sound and motion; do not claim technical meters prove taste. Parallel shared
history/learning waits until idle. Migration: `docs/NEW_LAPTOP.md`; GPU paths are untested here.

Arguments: `$ARGUMENTS` (clip folder or `clips.json`, optional existing brand).
Talk to the user in **Uzbek**, short numbered steps. Read first, fully: `docs/PROMO.md`, then `AGENTS.md`,
`docs/PLAYBOOK.md`, `docs/AGENT_MEMORY.md`. Never guess a field or flag: check `--help`, `scripts/assemble.py`,
`scripts/promo_looks.py`, `scripts/elements.py`. Python is `.venv/Scripts/python.exe` from the project root.
Never read `.env`. Never write into `input/` or `samples/`.

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

## Autonomy (the user gives only the clips)

1. Everything comes from the footage: transcribe all speech and voice-over clips; read clearly visible text in
   frames (box, uniform, signboard, menu, price tag) with `frames.py` - as text only, never cut out a logo.
2. Item names, set numbers, price, offer and call to action only if said or clearly visible. Never invent.
   Uncertain -> `[?word]` with its source (clip + time) in the approval message.
3. Decide the clip roles yourself from the sound, the "Kliplar bo'yicha nutq" table, `report.html` and the frames;
   write roles and voice-over `cover` into `temp/<job>/takes.override.json` -> `clips` and re-run (a hand-edited
   `clips.json` wins over the takes proposal). Show the role list in the approval message.
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

## Sprint 2 shared tools

Read `docs/BROLL_DYNAMICS.md` and `docs/EXPORT.md` before using these tools.
Rank visual moments from the transcript; measure crop/resolution/duration/colour and
text-like contours, then visually check exact object/action/age. Proxy checks do not
prove watermark/logo absence. Show all 3-column moment contact sheets in ONE approval
message; user selects numbers/auto/none, recorded verbatim in the video's HOLAT.md.
Prefer colour, a lower gradient, 2.5–4s and exact match; a weak clip is worse than none.
Explain when columns are variants of the same source. Unchecked candidates never auto-render.
Accepted/rejected with the user's reason go in per-video broll_history.json; publish to
style/broll_history.json only after every other agent is idle. Not selected is not rejected.
Dynamics uses measured WPS/RMS/word pauses and a labelled transcript-structure heuristic.
Brand/per-video style keys control zoom, visual-cut/automatic-element/SFX density,
caption intensity and background speed; preserve explicit user elements and speech timings.
Show energy curve, timecoded filmstrips/A-B and BOTH audio mixes/cue sheets in this chat.
Stronger is the general default, not approval of an unheard new mix.
For hand finishing export native FCP7 XML, editable SRT, ProRes alpha graphics and three
audio stems; parse back, disclose rasterised base motion and unverified GUI imports.
Never infer paid-plugin/OTIO/FCPXML support. No new downloads or installs for beat detection.

## Sample study family selection (42 references + 8 formats)

Read `docs/STYLE_STUDY/README.md`, then only the closest `docs/style_dna/<group>/playbook.md`.
Observe footage and transcript: seated explainer -> A; document/campus narrative -> B1;
creator/tutorial -> B2; interview/testimonial -> C; promo/showcase/vlog -> D (state subtype).
Use `scripts/sample_groups.py select --features temp/<job>/sample_features.json -o temp/<job>/sample_selection.json`
with observed boolean features (see --help/code). This is an explainable heuristic, not automated visual understanding.
If ambiguous, use editorial judgement and record an evidence-based reason; do not add another approval round.
Apply: `scripts/sample_groups.py apply GROUP --style temp/<job>/style.json --reason "footage/content evidence"`
(D: `--subtype promo|showcase|vlog`; named brand: `--brand NAME` so brand style overrides DNA).
Say the group, subtype if needed, and why in the ONE approval message. Keep brand fonts/colours and user feedback.
Use measured source frame intervals as examples, converting seconds to output fps; they are not universal tempos.
Use `card`, `canvas`, `trajectory`, `layout_morph`, optional stroke relief per `docs/MOTION_DESIGN.md`.
These are 2D/2.5D tools; exact 3D/folds/custom pen strokes remain external work, not a claimed match.
Never reuse sample logos, footage, music or fonts in output. Check actual approved words, faces and safe zones;
preserve calm answers instead of forcing new graphics every3s. Show native filmstrips and paired audio cues.
