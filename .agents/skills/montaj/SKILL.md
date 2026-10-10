---
name: montaj
description: Edit a raw talking-head video into a finished vertical Reel for a brand using this project's scripts (cut, captions, graphics, images, brand, audio). Use when the user gives a raw video and asks to edit / montaj it.
---

# /montaj — full edit of one video

Use docs/FORMATS.md and formats.py plan to choose the format separately from the style family.
Put both reasons in the ONE approval. Read docs/QUALITY.md for sentence-reviewed graphics_ideas,
shared-pivot group/hero objects, per-video quality.no_repeat and quality.enforce_final, temporal
face_safety and quality_gate fix lists. Unknown is not pass; technical scores cannot approve taste.
Stronger is primary, subtle second. User verdicts update existing histories; parallel entries
stay in the own job. Reuse cached words/features and load only the selected format/family guide.

Read `docs/MOTION.md` for shared motion settings, per-video `motion_override`, persisted
`motion_choice.json`, Uzbek glyph warnings, timecoded filmstrips and aligned A/B sheets.
Before showing motion, run `review_tools.py lint` (flags, curve PNGs) and `slowmo` strips; fix flags,
never edit an approved per-video style (doktor 1-5) to opt into the new motion switches.
After subtitle approval, show compose's subtle/stronger mixes with each cue sheet/waveform;
the user judges motion and sound, technical meters are not listening approval. During parallel
editing keep choices/learning in your own job; shared history is deferred until idle.
New machine migration and untested GPU paths: `docs/NEW_LAPTOP.md`. No unapproved installs/downloads.

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

The selected format plan takes precedence over generic caption, graphic cadence and follow-card
recipes above. Preserve calm answers and natural endings; never invent a CTA or clinical statement.

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
