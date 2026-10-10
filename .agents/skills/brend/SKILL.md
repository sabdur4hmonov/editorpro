---
name: brend
description: Onboard a new client brand into this video editing project (brand folder, colours, fonts, logo, caption style, end card). Use when the user names a new client or brand, or gives a client's Instagram.
---

# /brend — add a new client brand

Motion configuration is `brand.json -> style.motion` (`docs/MOTION.md`; `preset` calm/clinical/punchy
sets timing, easing, emphasis, blur, scrim and zoom strength); preview the selected
durations/easing and show a filmstrip, plus subtle/stronger sound mixes for the user's choice.
Per-file SFX licences are required. A future laptop follows `docs/NEW_LAPTOP.md`; GPU capability
is not a completed GPU test. Never install/download without the user's approval.

Arguments: `<arguments supplied in the user prompt>`. Talk to the user in **Uzbek**, short numbered steps.

Run scripts/handoff.py show first. If another agent owns an unfinished video, stop and tell the
user: brands/, scripts/, style/style.json, docs/ and skills must not change, selftest must not
run, and there are no git commits during parallel editing. Brand onboarding and shared feedback,
glossary and AGENT_MEMORY updates run at the end by one agent when the other is idle.
Never touch another agent's temp/<video>/ folder or note. An editing agent uses only its own
temp/<video>/ and per-video style.json, records milestones with handoff.py set --video VIDEO
--agent OWNER, and lets heavy jobs wait FIFO (MONTAJ_BUSY_TIMEOUT defaults to 7200 seconds).
Project HOLAT.md remains project-wide. See docs/PARALLEL.md.

1. Read `AGENTS.md` sections "Uslub va brendlar" and "Yangi mijoz (brend) qo'shish".
2. Collect what exists; never invent brand facts. Needed: brand name, logo (transparent PNG),
   main colour, Instagram handle. Optional: font files, music, reference reels in
   `samples/<brand>/`, product/office photos for `brands/<brand>/assets/`.
3. If the user gave an Instagram handle, you may look at the public profile with WebFetch to note
   visible colours, tone and typical content. Instagram often blocks this: if it fails, say so and
   ask the user for 3–5 screenshots or reference reels instead. Do not download images from the
   profile; logos and photos must come from the user.
4. Create the brand: `.venv/Scripts/python.exe scripts/new_brand.py <name> --title "..." --handle @... --logo <path>`
   (check `--help` for the exact options). Show the detected accent colour and confirm it.
5. If reference reels exist: `scripts/analyze_samples.py --brand <name>`, open the generated
   sheets, and fill `brands/<name>/brand.json` (caption preset and position, look preset, zoom).
   Ask about anything audio-related; you cannot hear.
6. Prove it on a real frame: run `/montaj`-style `--stills` on any video with `--brand <name>`,
   show the image, adjust until the user agrees.
7. `git commit` the new brand folder.

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
