# Review by claude of codex phase-2 reports (started 2026-10-09T19:47:50+05:00)

Method: for each codex claim I extract EVERY native frame around it (`claude_measure.py frames`, files in
`review_claude/` or my own video folders) and check it. Verdict: agree / disagree / unsure + evidence.
Where codex wrote "native timing separate", I add the measured frame count here so phase 4 has numbers.

## General findings (all codex solo reports so far: s21 s24 s25 s26 s27 s28)
| # | Finding | Evidence | Verdict / request |
|---|---|---|---|
| G1 | Self-checks are discovery-only: every row says "discovery confirmed; native timing separate" at ±0.2 s from 5 fps overview pages; no native-frame check is reported in the self_check files | codex/analysis/s2x/self_check.md | weak — self-check should verify against exact frames (task 2c). My measurements below fill part of the gap |
| G2 | "Critical eye" paragraph is the same template sentence in every report | codex/analysis/*/intent.md | weak — no video-specific strong/weak/excessive judgement |
| G3 | Behind-person text was found by codex (s26 ОШИБКА, s28 digits) and missed by me | my m_behind_check.jpg (s26 0.8/2.5, s28 22.4) | **agree; codex stronger here**. My s26/s28 reports corrected |

## Measured presets from codex's techniques (native frames)
| Video | Codex technique | My native-frame measurement | Verdict |
|---|---|---|---|
| s24 2.6 | hero_lockup (small intro + tall caps) | SOHASIDA fades grey->white over 9 frames (2.333 -> 2.600 @30 fps); small words "Lekin media" present first; a red vertical bar appears on the first letter at 2.767 | agree; adds: **same 8-10 frame opacity fade as s29 (3 cues)** -> 2 videos |
| s24 15.6 | diagonal_wipe | slanted white-edged panel enters from the right in ~13 frames (15.333 -> 15.733), ease-out (big early steps, small late); OPERATORLAR rides on the panel; b-roll inside is B&W; a second slanted divider continues moving | agree; measured |
| s25 1.8 | hero_lockup | ODAMGA EMAS assembles **letter by letter in random order** over 9 frames (1.50 -> 1.82 @25 fps); orange accent letter | agree on lockup; adds: **same random-letter assemble as s23 list titles** -> 2 videos |
| s25 6.8 | phone_rise | phone mockup rises from the bottom edge over ~10 frames (6.62 -> 7.02), slight tilt | agree |
| s25 20.8 | stagger_pills | three orange glowing pills at chest; the third grows from small to full in ~3-4 frames (20.50 -> 20.62) | agree (pop, no visible overshoot at 25 fps) |
| s27 0.6 | mixed_type | "content" (heavy serif) slides in from the left with horizontal motion blur, 6 frames (0.300 -> 0.500); photo cards pop one by one (0.30-0.60) | agree |
| s27 3.4 | horizontal_track | pink outlined word repeats scroll horizontally BEHIND the walking person (continuous, ~5 % width/frame) | agree; behind-person + scroll |
| s27 8.8 | film_frame | dark rounded film-frame border around b-roll; single-word captions, new word cross-fades in ~3 frames (8.934 -> 9.034) | agree |

## Batch 2 (2026-10-09T19:50:05+05:00) — sheets review_claude/rv_A1.jpg, rv_B1.jpg, rv_B1b.jpg, rv_C.jpg, rv_D.jpg (14 native frames per claim, label #k = t0 + k/fps)
| Video t | Codex technique | Native-frame result | Verdict |
|---|---|---|---|
| s25 13.4 | arrow_draw around head | orange glowing stroke draws progressively around the head over ~13 frames (13.25 -> 13.77 @25), a second arc follows; "GEO bilan" words appear one per 2-3 frames | agree |
| s25 41.7 | negative_flash | paper card -> 2 inverted frames -> normal at #4 (41.55 -> 41.71) | agree; **same invert flash as s29** (2 videos; codex also reports it for s33) |
| s33 1.8 | rotated_prop | calculator rotates + translates in, ~9 frames ease-out (1.65 -> 2.01), display text types on | agree |
| s33 9.6 | zoom_blur "push" | extreme close-up with radial blur **pulls OUT** to a medium shot in ~6 frames (9.45 -> 9.69); caption slides in with motion blur | partly disagree: direction is pull-out (reveal), not push |
| s33 22.6 | grid statistics paragraph | small paragraph types ~1 letter/frame; heading drifts up slowly | agree |
| s35 1.0 | orbit_collage | small photos move along a curve around a glowing €8000; script word "stipendiya" writes on | agree |
| s36 0.8 | behind_type | glowing caps at the top; I see no head occlusion in frames 0.65-1.17 | unsure — not proven behind-person here |
| s36 5.6 | paper_camera | scrapbook paper collage, slow camera drift; word fades in | agree |
| s36 36.8 | letter_resolve | title already complete at 36.65; only the sub words appear one by one | unsure — resolve not in this window |
| s39 24 | extruded_number | 3D extruded "2008" rotates over the head; a white light streak sweeps around the body | agree |
| s39 45 | card_fan | gold cards appear above the head one by one, ~3 frames each | agree |
| s40 1.4 | grid_pullout | pull-out on a grid paper of many small cards, ~13 frames ease-out (30 fps) | agree |
| s40 5.4 | red_oval | faint hand-drawn stroke draws on above "100% GACA" over 14+ frames | agree (very low contrast) |
| s41 1.0 | behind_extrusion | red serif SAT'DAN behind the person (head over letters); "1570 OLGANMAN" goes from motion-blur to sharp in ~8 frames (0.85 -> 1.12) | agree; behind-person + defocus/motion-blur-to-sharp entrance |
| s41 22 | split_panels | three B&W panels Harvard / Stanford / Yale with serif titles, static | agree |
| s41 41 | canvas_pan | white grid canvas pans/scales, polaroids, peach paper shape; text appears line by line | agree |
| s30 1.2 | behind_person | yellow condensed caps at the top; no occlusion visible 1.05-1.57; a neon line icon (graduate) on the chest | unsure for behind-person |
| s30 21.4 | glass_numbers | neon "1 2" at chest, static in the window | agree (no entrance in window) |
| s31 0.6 | extruded_title | 3D metal letters AMERIKAGA standing on the grass, **camera-tracked** (perspective changes with the camera); the US flag sky cross-fades out in ~6 frames | agree; this is 3D tracked text (we cannot do this) |
| s31 14.6 | card_stack | glass cards IELTS / GPA / Score at chest | agree |
| s38 0.8 | money_blur | flying banknote particles with motion blur over the speaker, ENG QIMMAT caps | agree |
| s38 24 | year_type | "2024" types digit by digit (~2 frames per digit), then "yil" | agree |
| s37 2.6 | canvas_pan | teal grid canvas pans left; caps type letter by letter | agree |
| s37 45.8 | three_panels | three stacked campus panels, then a yellow-orange **light-leak burn** to white in ~4 frames (46.0 -> 46.1) | agree + adds light-leak transition |
| s21 3.8 | paper_shadow | moving leaf shadow on orange paper inside an editor UI; banknotes pop in; "PUL" handwriting writes on | agree |
| s21 12.8 | arrow_draw | banknotes slide in from the right; "1$ = 7 so'm" types on | partly: arrow already present in the window; slide-in confirmed |
| s32 21.8 | card_reflow | rounded photo card shrinks to the left while quote words appear one by one | agree |
| s32 30.4 | number_map | static diagram in this window | agree (no motion measured) |

### Patterns now seen in >= 2 different videos (native frames, mine + codex)
| Pattern | Videos | Count | Frames |
|---|---|---|---|
| Text behind the person (head occludes letters) | s26, s28, s41 (+ s05, s07, s10 from the old study) | 3 new + 3 old | — |
| Giant condensed caps opacity fade-in | s29 (3 cues), s24 | 2 | 8-10 |
| Random-order letter assemble | s23 (list titles), s25 | 2 | 8-9 |
| Invert (negative) flash transition | s29 (7x), s25, s33 (codex) | 3 | 2-4 |
| Typewriter text (letter per 1-2 frames) | s29, s33, s37, s38, s28 | 5 | — |
| Hand-drawn stroke / arrow draw-on | s25, s26, s40, s21 | 4 | 13-14 |
| Grid-paper / scrapbook canvas backgrounds | s21, s33, s35, s36, s37, s40, s41, s32 | 8 | — |
| Single accent colour for all emphasis | s26 lime, s28 lime, s25 orange, s30 yellow | 4 | — |
| Comment-keyword CTA | s23, s28 (+ codex: check others) | 2 | — |
| 3D tracked / extruded text | s31, s39, s23 | 3 | — (not in our system) |
| Light-leak burn transition | s37 | 1 (observation) | 4 |

## Batch 3 (2026-10-09T19:57:23+05:00) — samples 1-20 brief re-check + global numbers
- `videos/s01..s20/brief_claude.md`: loudness, cut stats, speech, cut position, native hook frames
  (review_claude/hooks_01..03.jpg), techniques (earlier study confirmed on mosaics).
- **Hook timing (native frames):** first on-screen text by <= 0.3 s in 18/20 old samples (not s03, s20); 0 frames in s04, s05, s07, s15.
  In my 21-41 videos: s23 0.17, s26 0.20, s28 0.30, s29 0.30. -> rule candidate (>= 3 videos): **hook text on screen within 0.3 s**.
- **Transcript fix:** s04/s08 were labelled ru; they are Uzbek (+ Russian testimonial parts). s08 re-transcribed with the uz model
  (mean prob 0.78 -> 0.80, readable). s04 is mixed; kept the ru transcript (uz model scored 0.72 vs 0.73) — treat s04 words as low confidence.
- **Global stats** (`review_claude/global_stats.md`, all 41): per group medians —
  A: 9.6 cuts/min, median shot 2.6 s, 147 wpm | B1: 12.1 cuts/min, 2.5 s, 141 wpm | B2: 22.2 cuts/min, 1.9 s, 155 wpm |
  C: 6.2 cuts/min, 8.0 s, 135 wpm | D: 13.9 cuts/min, 1.7 s, 141 wpm. Loudness median -14.2 to -14.5 LUFS in every group
  (s01 -17.4, s20 -17.0, s37 -15.3 are the exceptions); true peak above 0 dBTP in 8 samples (s18 s21 s27 s31 s39 s41 + others) —
  platform normalisation, not a style choice. Our system's -14 LUFS / -1.5 dBTP target already matches.

## Per-group verdict on codex conclusions (2026-10-09T19:58:16+05:00)
Strongest = verified on native frames (agree). Weakest = disagree / unproven / method problem.

| Group | codex strongest (agree) | codex weakest |
|---|---|---|
| A studio explainer (s25 s33 + s02-s16 brief) | s25 arrow_draw; s25 phone_rise; s25 stagger_pills; s33 rotated_prop; s33 grid_statistics typewriter; s25 invert flash | (1) s33 zoom_blur called "push" — it is a pull-out reveal (rv_A1 row 4). (2) all techniques "medium" — no calibration even when native frames make them certain. (3) critical-eye text is a template |
| B1 editorial paper (s35 s36 s39 s40 s41 + s34 pilot) | s41 behind_extrusion; s39 extruded_number + light streak; s39 card_fan; s40 grid_pullout; s35 orbit_collage; s34 pilot (all 6 rows agree) | (1) s36 behind_type: no occlusion visible 0.65-1.17 s (unproven). (2) s36 letter_resolve: title already complete in my window (unproven). (3) s40 red_oval is very low contrast — reliance as a "rule" is weak |
| B2 kinetic creator (s24 s26 s27 s28 + s22 pilot) | s24 diagonal_wipe (13 f); s26 behind-person hook (I missed it); s27 horizontal_track behind person; s27 film_frame; s22 badge spring overshoot; s22 letter cascade | (1) s26/s28 self_checks discovery-only (±0.2 s) though native checks were cheap. (2) s28 intent misses the main device: same actor as human (warm) vs AI (blue) colour-coded skit. (3) s26 fan "pivot" timing vs spoken items not checked against the transcript |
| C interview / testimonial (s30 s31 s32 s38) | s31 extruded_title (3D tracked); s31 card_stack; s38 money_blur; s38 year_type; s32 card_reflow | (1) **s32 CTA = null, but the speaker says "forprepga keling va shunaqa kuchli mentorlar bilan ..." at the end** (transcript tail) -> disagree. (2) s30 behind_person unproven (no occlusion 1.05-1.57). (3) hooks of 7.0-7.5 s (s31, s32) are long for a "hook"; I would split hook (<= 3 s) and intro |
| D cinematic / commercial (s21 s37) | s21 paper_shadow; s37 canvas_pan typewriter; s37 three_panels (+ light-leak) | (1) s21 arrow_draw: arrow already present in my window; only slide-in confirmed. (2) s37 is a vlog walkthrough; style DNA for D mixes very different things (showcase, promo, ad, vlog) — suggest D is NOT merged into one DNA, or split D1 showcase/ad, D2 vlog/promo |

### Cross-cutting notes for phase 4 (merge)
- Whisper tail hallucination "o'zbekistonda o'tmoqda" appears in s29 s30 s36 s38 s39 (after the speech ends, probably the brand outro / music). Do not read it as speech or CTA.
- Brand testimonial endings (s38 "tavsiya qilaman", s39 "forprep jamoasiga rahmat") are a soft CTA, not "none".
- Patterns with >= 3 videos (rule candidates, native evidence): text behind the person; invert flash; typewriter text; hand-drawn stroke draw-on;
  grid/scrapbook canvas; single accent colour; 3D extruded text (we cannot build tracked 3D); hook text <= 0.3 s; giant condensed caps keywords.
- Observations (< 3): random-letter assemble (s23, s25, s34?), opacity-fade caps 8-10 f (s24, s29), light leak (s37), money particles (s11, s38).
