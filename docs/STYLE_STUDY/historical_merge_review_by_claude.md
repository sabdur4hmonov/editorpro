# Merge review by claude (phase 4 check, before build commit)
Written 2026-10-09T20:35+05:00. Reads codex/gap_report.md, patterns.md, disagreements.md, questions_for_me.md, groups/*/.
I do not edit codex files; codex decides what to take. Evidence paths are in review_by_claude.md.

## 1. A peer review exists — the merge says it does not
`codex/disagreements.md`, `coverage.json` ("independent_peer_review": false) and every `groups/*/review_by_codex.md`
("Claude hit its usage limit; no independent peer agreement is claimed") were written before / without reading
`review_by_claude.md` (19:58) and `pilot_review_claude.md`. Please merge its disagreements, or say which ones you reject and why.

## 2. Disagreements that should change the merge
| Item | Merge now | My evidence | Suggested change |
|---|---|---|---|
| s32 CTA | null | transcript tail: "forprepga keling va shunaqa kuchli mentorlar bilan ..." | spoken CTA exists (C group) |
| s33 zoom_blur | "push" | rv_A1 row 4: pull-out reveal 9.45 -> 9.69, ~6 f | direction = pull-out |
| s30, s36 behind_person | witnesses | no occlusion in native frames s30 1.05-1.57, s36 0.65-1.17 | drop as witnesses (pattern still holds via s05 s22 s26 s29 s35 s40 s41) |
| s36 letter_resolve | technique | title already complete at 36.65 | unproven |
| Whisper tail "o'zbekistonda o'tmoqda" | — | s29 s30 s36 s38 s39 after speech ends | not speech, not CTA |
| s31/s32 hook 7.0-7.5 s | hook | — | split hook (<= 3 s) and intro |

## 3. Rule candidates (>= 3 videos, native evidence) missing from gap_report / patterns
| Candidate | Witnesses | Build status (my reading of scripts/) |
|---|---|---|
| First on-screen text within 0.3 s | 22 of 24 checked (s01-s20 briefs + s23 s26 s28 s29) | measurable in preflight; not a check today |
| Invert (negative) flash transition, 2-4 frames | s25, s29 (7x), s33 | missing: `flash` is colour-only, no invert |
| Typewriter text (1 letter / 1-2 frames) | s28, s29, s33, s37, s38 | exists (`typewriter` anim in elements.py) |
| Single accent colour for all emphasis | s25 orange, s26 lime, s28 lime, s30 yellow | config rule (brand accent), document in playbook |
| Giant condensed caps keyword, rare (4-5 per video) | s29, s34, s05, s07 | exists (`caps` preset); "rare" is the rule |

## 4. Quality of the merge files
- All five playbooks share the same "Apply" and "Limits" text (Limits even mentions D in the B2/C playbooks), and every
  technique has the same "alternative" string. A playbook should say per group: when to use, numbers (cut median, caption
  size, entrance frames), and what not to do. Numbers are already measured: review_claude/global_stats.md and my frame counts
  (diagonal panel 13 f, giant word fade 8-10 f, invert 2-4 f, badge spring overshoot s22).
- C playbook: "long calm answers legitimate" — agree (global_stats: C ~6 cuts/min vs B2 ~22).
- D: agree it is three modes; style_dna for D should be marked "do not apply as one style".

## 5. What I will check in build_review.md (after the build commit)
Diff read; test_motion_design + test_studio + test_agent_setup + selftest --no-whisper (only if nobody is mid-render);
two recreations vs originals on native-frame strips; that no sample asset (logo, music, footage, font) is in outputs.
