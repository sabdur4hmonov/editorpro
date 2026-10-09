# s29 self-check (claude, phase 2c)

| # | Claim | How checked | Result | Note |
|---|---|---|---|---|
| 1 | Giant caps keywords fade in over 8-10 frames; sub words come first | m_frames_16.15-16.75 (16.19 faint -> 16.59 full), 28.70-29.50 (28.78 -> 29.14), 45.45-46.05 (45.53 -> 45.85) | fade confirmed (3 instances, ONE video); order **partly contradicted** (codex pilot review): LEKIN appears first, sub line from ~16.55; sub-first holds for INTERVYU and MAQSADLAR | Earlier overview reading of MAQSADLAR as "mask up from the bottom" was WRONG: dense frames show an opacity fade |
| 2 | Invert + white panel wipe is the main transition (2-3 frames) | strips_04 r3/r5/r6 (32.18, 34.82, 37.46), strips_05 r4-6 (46.62, 47.66, 48.58), m_frames_7.40-8.10 | confirmed (7 instances) | Panel direction varies: left (32-37) and top (46.6) |
| 3 | B&W = setbacks, colour = wins | HSV saturation at 22 times: B&W 20.8-28.1 (sat 12-18), 38.0 (sat 8); wins 47-49 (sat 80-104) | confirmed | The 28-37 s office scenes are colour but low-ish saturation (36-63) |
| 4 | Speaker shot 16.2-20.7 has a camera move | ECC said continuous push-in to 1.38 -> after sign fix, pull-out to 0.72; YuNet face height 212, 197, 183, 183, 202, 212 | **partly contradicted** | Real motion = pull-out then push-in, about 0.86x, not 0.72x. ECC is biased by the giant text overlay; face size is the better measure here |
| 5 | Text positions: giant caps at chest (52-74 % y), single words 62-65 % | m_grid_frames.jpg 17.2 / 39.4 / 46.3 | confirmed | Arc titles at the top (8-30 %) are the exception (hook only) |
| 6 | Stacked panels scroll up ~7 frames at 11.54 | m_frames_11.50-12.15: divider rises from ~38 % to ~30 % between 11.54 and 11.82 | confirmed | Third panel appears at the bottom at the same time |
| 7 | Quiet single-word section 39.3-45.0 has no graphics | overview_05 rows 1-4 (every 0.2 s) | confirmed | — |
