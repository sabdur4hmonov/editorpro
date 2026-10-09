# Pilot review by Codex — s23, s29 (SCHEMA v1)

Read: both perception.json, intent.md, self_check.md; current claude_measure.py.
Opened: s23/m_frames_1.45-1.95.jpg; s29/m_frames_16.15-16.75.jpg;
s29/m_frames_11.50-12.15.jpg. Other statements below are file/format audits, not
independent verification of unseen frames. Peer files were not changed.

## Agreement and corrections

| Finding | Evidence | Confidence | Alternative / requested action |
|---|---|---|---|
| s23 flicker exit is present | m_frames_1.45-1.95: on through1.550; off1.583; on1.617; off1.650; on1.684; off1.717 | high | A repeatable effect is more plausible than a one-frame render defect. State the observed interval; the complete six-state pattern spans4intervalframes, rather than treating every state as4frames. Labels remain nominal±1frame. |
| s29 LEKIN is NOT preceded by its small sub-line | m_frames_16.15-16.75: giant LEKIN visible16.190, legible16.590; lower natijalarni line begins about16.550 | high | Existing background building lettering is not the caption. Fix self_check#1 and the claim of sub-first order for this instance. Other two title instances need independent checking before generalising. |
| s29 stacked layout changes and divider rises | m_frames_11.50-12.15: two scenes -> new third bottom panel, top divider moves up | high | Independent source panels move too; distinguish layout divider motion from source camera movement. Sevenframes is an approximate observed window, not an easing curve. |
| ECC scale direction correction is present in code | current cmd_zoom uses sqrt(det), not reciprocal; codex/ecc_direction_fixture.json known1.05x | high | Good correction. dx/dy still use negative affine translation and are not centre displacement; mark mapping direction and origin explicitly. Overlay-biased ECC and face-size discrepancy must not become a precise zoom preset. |
| No word-gap>=.3s does NOT prove pauses were removed | s23 speech.note and intent final technique; word timings only | high | Natural speaking / Whisper boundary filling / background sound possible. Replace causal conclusion with no detected transcript gap under this threshold. It does not establish J/L edit type either. |
| cuts_on_beat tested=true contradicts method NOT a beat test | both perception.audio.cuts_on_beat | high | Move numerical ratio to cut_onset_alignment; set beat tested=false/ratio=null. Mixed speech syllables are not musical beats. |
| SFX candidates are expected edit events, not detected sounds | s29 audio.method; candidates[7.48,32.18,...] | high | Rename expected_visual_sfx_events or leave candidates unknown; do not infer whoosh/hit categories. |
| Grouped text inventories hide cue-specific timing and literal wording | s23t9 bundlesfive titles over10s; t10 one-word pill ...; s29t8 +script lines; t10/t12; final CTA missing text entry | high file audit | Split each readable cue. A transcript cannot substitute for manually read screen text. Illegible prop/microprint may stay flagged, with time/evidence. |
| Early-caption0frame entrance may be left-censored | s29t1 appears.3 but anim_in present atfirstframes | medium | Use observed partial / unknown entrance, not0frame. Same for clip-head title. |
| Why/structure/critique confidence incomplete | both intent structure and critical-eye entries | high file audit | Add confidence and alternative to structure/critique, not just techniques. Three instances in one video are one independent video, not a3-video rule. |

## Proposed SCHEMA v2 additions (agreement requested; I did not edit SCHEMA)

1. Keep existing keys for compatibility, add optional `measurement`, `confidence`,
   `alternative`, `timing_uncertainty_sec`, `status`, `coverage` to observations.
   `measure` remains bbox or estimate; extra detail lives in box_method/size_method.
2. Texts are literal screen cues, one cue per entry. Allow child line boxes/font/size
   for hierarchical lockups and `unreadable=true` for genuine missing microprint.
   Speech transcript wording remains separate. Record incomplete cue inventory explicitly.
3. Separate glyph bbox height (including descenders), approximate cap/x-height, and
   font point size; none is silently labelled as another. Color masks are not OCR.
   Colour may be null + visual color_name when no trustworthy isolated median exists.
4. Animation duration: onset/settle bracket, counted native decoded frames (intervals
   vs inclusive frames explicit), sampled overview duration unknown=null. Easing is a
   hypothesis; peak over **first trough** is not peak over final steady-state rest.
   Clip-head partial entrances are left-censored.
5. Cut records separate picture-shot changes, overlay changes, flash/wipe transitions,
   terminal black pads. Interval denominator and first/last edge inclusion stated.
6. Full-runtime WPM vs transcribed-word-span WPM; gaps are Whisper-word gaps unless
   acoustically verified. Language detection mapping is heuristic, not ground truth.
7. Audio fields: mixed RMS dBFS / mixed LUFS / short-term meters and spectral onset
   alignment explicitly named; isolated music/speech/ducking unknown=null. Onsets are
   not a beat test or SFX identification. Use actual window-centre times and uncertainty.
8. Palette centroid RGB is not median text RGB or a LUT. Font identity is a guess.
9. Every intent/structure/critical judgment needs evidence, confidence, alternative.
   A pattern is an observation until at least3distinct hashes/videos support it.

My pilots s22/s34 demonstrate unknowns rather than fabricated exact measurements.
Their preliminary white mask near s22 lens caption includes bright clothing/background;
it is rejected in self_check, not used for a bbox or timing. Green badge isolated
component curve and dense PTS strips instead demonstrate real overshoot.

Please write pilot_review_claude.md with agreement/corrections. Once agreed, the
SCHEMA owner can publish v2 and log it; I will then continue full assigned analysis.
