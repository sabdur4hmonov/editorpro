# Build review by claude (phase 5)
Status: **part 1 = diff reading of the UNCOMMITTED build** (read at 2026-10-09T20:47:42+05:00; git HEAD 865aeb1).
Part 2 (tests on the committed version + two recreations vs originals) follows after the codex build commit.
I changed no shared file. Line numbers refer to the working copy at that time.

## Scope read
scripts/motion_design.py (new, 431 lines), scripts/sample_groups.py (new, 69), scripts/test_motion_design.py (new, 22 tests),
diffs in elements.py (+20), motion.py (+28), sound_design.py (+8), AGENTS.md, docs/MOTION_DESIGN.md, docs/STYLE_STUDY/, docs/style_dna/, skills.

## Good
- Opt-in only: card/canvas/trajectory/layout_morph go through motion_design.build; every other element keeps the legacy class.
  caption_recipe only runs when motion_design.caption_recipes is set (no DNA patch sets it) -> approved videos (doktor 1) unchanged.
- Track validates keyframes (first at=0, increasing, finite, bounded) and clamps spring/overshoot output -> no invalid alpha/scale.
- Premultiplied RGBA source-over in M.blit is correct (colour and alpha use the same (255-a) term).
- layout_morph crops ONE source and moves the viewport (no two-face crossfade); stage morph refuses footer/progress/punch/... loudly
  instead of dropping them silently.
- Card text: shrinks to fit, then raises a clear error; never truncates.
- sample_groups: DNA only into temp/<video>/style.json; brand style applied after DNA; D requires a subtype; ambiguous rank -> agent judgement.
- No sample asset (logo, music, footage, font) found in docs/style_dna or the new code.

## Problems (ranked)
| # | Where | Problem | Suggested fix |
|---|---|---|---|
| 1 | docs/STYLE_STUDY/README.md, disagreements.md, coverage.json ("independent_peer_review": false) | Committed docs would state "mustaqil peer review yo'q". It exists: temp/style_study/review_by_claude.md (19:58), pilot_review_claude.md, merge_review_by_claude.md. The 6 disagreements there (s32 spoken CTA, s33 pull-out, s30/s36 behind-person unproven, Whisper tail hallucination, long hooks) are not merged | merge or reject each with a reason; fix the README sentence before commit |
| 2 | docs/style_dna/D_cinematic_commercial style_patch | subtype is required by sample_groups.apply but the patch ignores it: showcase and vlog also get captions.preset "promo" (big glowing italic price style) | per-subtype patch, or no caption preset for showcase/vlog |
| 3 | docs/style_dna/*/style_patch | The patches only set caption preset + motion choice + title duration. None of the measured group numbers are used (cut rhythm, caption size, entrance frames, hook text <= 0.3 s, single accent). The new card/canvas/relief tools are not referenced by any patch, so "apply GROUP" does not change the look beyond the entrance choice | either say so in the playbook ("patch = captions only; graphics are agent choices"), or add the measured values |
| 4 | motion_design.CanvasLayer / TrackedText draw | Allocates a full HxWx4 canvas (8 MB) and, with a trajectory, warps the whole frame every frame; TrackedText also runs np.nonzero over the full frame. Fine for short elements; on a 60 s canvas this is a big CPU cost on this 4-core machine | crop to the children bbox, or cache when the child is static |
| 5 | CanvasLayer children + compose.py:402-412 | behind_person is decided on TOP-LEVEL elements only (segmenter is created only if a top-level element has behind_person; `behind` = top-level layers). A canvas item with behind_person:true is silently drawn in FRONT of the person. (Top-level text with a trajectory is fine: TrackedText copies behind_person.) Not covered by a test | reject behind_person in canvas items with a clear error, or support it |
| 6 | motion_design.MotionBroll.draw | seam colour hard-coded 235 (light grey); other styles read colours from style.json | style key |
| 7 | elements.ELEMENT_TYPES | "card": None, "canvas": None — only safe because build_elements routes them first; any future direct ELEMENT_TYPES[kind](...) call crashes with "NoneType is not callable" | point them to motion_design classes via a lazy factory |
| 8 | gap_report rule candidates | invert (negative) flash (s25, s29 x7, s33) is not built; FlashLayer is colour-only | log as a gap or add flash mode "invert" |

## Not yet checked (part 2)
- test_motion_design, test_studio, test_agent_setup, test_takes, selftest --no-whisper on the committed tree (codex is running its own now).
- Two recreations vs their originals on native-frame strips (temp/style_study/codex/proof/ does not exist yet).
- sync_skills --check after commit.

## Part 2a — two recreations vs originals (native frames), 2026-10-09T21:17:03+05:00, build still uncommitted
Sheets: review_claude/ab_B2_s26.jpg, review_claude/ab_A_s33.jpg (tools/claude_ab_strips.py; original every 1-3 native frames, own every 2-3).
Proofs: output/style_study_A.mp4, output/style_study_B2.mp4 (540x960, 30 fps). Codex comparison.json says: technique/geometry, different content.

### B2 proof vs s26 "pill fan" (s26 4.2-7.4 vs own 1.2-3.2)
| Aspect | s26 original | Own proof | Verdict |
|---|---|---|---|
| Geometry | pills rotate out of ONE shared pivot like a colour-swatch fan, above the head | 5 pills in a horizontal ROW at chest, each with its own pivot | **not reproduced**: a row, not a fan (canvas/pivot could do it: same x/y + increasing rotate) |
| Content | each pill = a spoken item word (актёры, локация, реквизит, сценарий, монтаж) | pills say "1 2 3 4 5" | the speech says only "besh xil dori"; no items enumerated -> pills carry no information |
| Timing | one pill per spoken item, 4.3-7.9 (~0.7 s apart, synced to finger counting) | all 5 in 0.48 s (1.26-1.74), not tied to words | not synced |
| Layout | pills do not overlap text | pills overlap each other (width 0.18, spacing 0.13; visible 1.87-3.10) and sit just above the caption | layout fault |
| Hierarchy | one object (fan) + one caption | relief "5" + pills 1-5 + caption "besh xil dori" = the number five three times at once | breaks "one main thing per frame" |
| Look | neon lime glow on a dark set | flat pastel pills, no glow | colour choice OK (own accent), glow absent |
| Second card | — | "vitaminlarni" pill right above the caption "vitaminlarni" (same word twice) | redundant |

### A proof vs s33 "rotated prop" (s33 1.50-2.02 vs own 4.90-5.80)
| Aspect | s33 original | Own proof | Verdict |
|---|---|---|---|
| Object | big photographic prop (calculator, ~60 % frame width) flies in from the right, rotating, motion-blurred, on a grid canvas | small cream pill "o'pkasi" at chest | different technique: tag, not a prop entrance |
| Duration | ~9 frames to rest (1.62 -> 1.98, ease-out) | ~17 frames (0.567 s), soft | slower, no blur (fast_blur_px only applies to image, not card) |
| Redundancy | — | pill "o'pkasi" directly above the caption "o'pkasi" | same word twice |
| layout_morph (0.8-1.7, 3.2-4.1) | (not from s33) | works: one source, face size constant, no double face, thin seam; full frame restored | **agree, best part of the build** |
| Caption over b-roll | — | white caption sits on the grey smog b-roll 1.27-1.67 and 3.33-3.47: low contrast | move caption to the speaker half while split is active |

### Conclusion part 2a
- The proofs prove the **mechanics** (trajectory, card, relief, layout_morph render without errors, single-face morph). They do **not** yet reproduce
  the two reference **techniques**: s26 fan geometry + per-item sync, s33 big prop entrance with motion blur.
- Two repeated design faults: the card repeats the caption word; several representations of the same number at once.
- Suggest for iteration 4: B2 = same pivot fan with real items from speech (or skip the fan when the speech has no list);
  A = image prop (licensed/own drawn object) with trajectory + fast_blur, 9-10 frames; never duplicate the caption word in a card.
