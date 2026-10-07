---
name: transcribe-uz
description: Transcribe an Uzbek (or Russian/English) video with the project's whisper setup, then correct spelling without touching word timings, and get the user's approval of the text. Use when the user asks to transcribe a video, fix a transcript, or compare whisper models.
---

# /transcribe-uz — transcript first, corrected text, approved by the user

Argument: `<arguments supplied in the user prompt>` (video path). Talk to the user in **Uzbek**, short numbered steps. The user
is a beginner programmer.

**You cannot hear the audio.** Every correction you make is based on the logic of the text only
(spelling, grammar, context). You do not know what was actually said. Where the meaning is not
clear, do not guess: mark the place `needs_review` and ask the user.

Python is always `.venv/Scripts/python.exe`, run from the project root. Check `--help` before
using a flag you are not sure about.

## Parallel work and handoff

Run scripts/handoff.py show first; it lists all unfinished videos and owners. Work only on
your assigned video and its temp/<job>/; never touch the other agent's folder or note. Claim
and update yours with handoff.py set "..." --video VIDEO --agent OWNER, read with show --video
VIDEO, and record exact approvals there. clear --video VIDEO --agent OWNER marks done and
keeps approvals. Project HOLAT.md is for project-wide state only.
Use a full per-video temp/<job>/style.json copy, pass --style to transcribe, pipeline and
compare_models, and --out-dir temp/<job>/compare to compare_models. Set MONTAJ_AGENT in your
terminal. Heavy jobs wait FIFO and report the holder; MONTAJ_BUSY_TIMEOUT defaults to 7200s.
Never manually remove the lock. While another agent has an unfinished video, do not edit
scripts/, style/style.json, brands/, docs/ or skills, and do not run selftest. If a code change
is required, stop and tell the user. No git commits during parallel editing. Feedback, glossary
and AGENT_MEMORY are written at the end by one agent when the other is idle; until then keep
proposals in your own temp/<job>/deferred_learning.md. See docs/PARALLEL.md.

## Steps

1. **Transcribe** with the configured model (`style/style.json` → `whisper`):

   `.venv/Scripts/python.exe scripts/transcribe.py <video>`

   Output: `temp/<job>/orig.words.json` (word-by-word timings) and `temp/<job>/orig.srt`.
   - Exit code 4 means the model is not on this computer. Nothing was downloaded. Tell the user
     the size that was printed and ask. Only after a clear yes, re-run with `--allow-download`.
   - A different model for one run: `--model NAME`. Never change `style.json` unless the user asks.
   - If the script prints timing problems (`So'z vaqtlarida ... muammo`), show them to the user.
   - If the script warns that many words are squeezed into a fraction of a second
     (`... ta so'z ... soniyaga tiqilgan`), that text was almost certainly invented by whisper over
     laughter, applause or music (often at the very end). Check the frames at that time, then remove
     the run in `corrections.json` with `{"index": N, "count": K, "text": ""}` and tell the user.

2. **Read and correct — text only.**
   - List the words with their numbers:
     `.venv/Scripts/python.exe scripts/apply_corrections.py temp/<job>/orig.words.json --list`
   - Find Uzbek spelling mistakes and Latin-script mistakes: `o'` / `g'` and the tutuq belgisi,
     x/h and q/k confusions, words glued together or split apart, suffixes, capital letters in
     names, Cyrillic output where the video is Uzbek in Latin script.
   - Write ONLY `temp/<job>/corrections.json`. Format (see the script's `--help`/docstring):
     `{"corrections": [{"index": 5, "was": "kitop", "text": "kitob"}]}`
     Always include `was` (the current word) so a wrong number is caught.
   - Never edit `orig.words.json`, never edit an SRT by hand, never write `start`/`end` anywhere.
   - Keep the speaker's own words. Do not rephrase, shorten or "improve" style. Do not add words.
   - Not sure what the word should be (a name, a brand, a number, a garbled phrase)? Do not guess:
     `{"index": 20, "was": "...", "needs_review": true, "note": "nega shubhali"}` and leave the text.
   - Splitting one word into two or merging two into one is allowed (`"text": "ilm markazi"`, or
     `"count": 2`); the script divides the time evenly and marks the place `needs_review` itself.

3. **Apply:**

   `.venv/Scripts/python.exe scripts/apply_corrections.py temp/<job>/orig.words.json temp/<job>/corrections.json`

   Output: `orig.words.fixed.json`, `orig.fixed.srt`, `orig.fixed.txt`. The script proves that
   timings did not change and lists every `needs_review` place. If it reports an error, fix
   `corrections.json` (not the script, not the timings) and run it again.

4. **Show and get approval.** Show the user, in Uzbek:
   - the full corrected text (`orig.fixed.txt`),
   - the list of changes: was → now,
   - every `needs_review` place with its time, and your question about it,
   - words whisper itself was unsure about (marked `?` in `--list`).
   Ask: "Matn to'g'rimi?" Wait for a clear yes. If the user corrects something, update
   `corrections.json` and re-run step 3 (always from the original `orig.words.json`).
   **Until the user approves, do not go on to subtitles or rendering.**

## Comparing models

When the user wants to choose a model:

`.venv/Scripts/python.exe scripts/compare_models.py <video> --models small,yuldashev222/whisper-small-uz-v1-ct2`

It uses only the first 60 seconds, writes one set of files per model and a side-by-side table
(`temp/compare/<name>/compare.html`, `compare.txt`) with differing words highlighted.
- The video must contain real speech in the target language. Ask the user for a 1-minute test
  video; never build a synthetic one.
- Do not score or rank quality yourself: you cannot hear which model is right. Report speed and
  where the texts differ; the user listens and chooses.
- Exit code 4 = a model must be downloaded: tell the user the size, ask, then `--allow-download`.
- Write the chosen model into your per-video style during parallel editing. A shared
  style/style.json change requires the user's choice and an idle maintenance session.

5. **After approval — hand the text to the edit.**
   - A word whisper got wrong that will come up again (brand name, a person's name, a term):
     during parallel editing, record it only in your deferred_learning.md. At the end, one idle agent runs
     `.venv/Scripts/python.exe scripts/glossary.py add "wrong" "right" [--brand NAME]`.
   - Continue the edit with the approved words (whisper is not run again, timings stay):
     `.venv/Scripts/python.exe scripts/pipeline.py <video> --words temp/<job>/orig.words.fixed.json [--brand NAME]`
   - Do not run `pipeline.py` on this video without `--words` after this point: it would
     re-transcribe and overwrite `orig.words.json`.
