# s42 notes (claude) — "This or that" tournament bracket, the deepest-studied sample
Source: samples/sample 42.mp4, 56.05 s, 720x1280 @ 30 fps, -15.0 LUFS / TP -0.6 / LRA 3.8. English speech, 95 words.
Evidence: review_claude/s42_A1.jpg (entrance, check), s42_B.jpg (pair change, check, bracket label, semifinal, final, end),
s42_C.jpg (champion), m_activity.json (frame-exact activity per screen region), transcript word times, YuNet face width,
pixel colour medians. All times are sample timeline; frame = 1/30 s.

## What happens (timeline)
- **One shot, no cuts, no zoom.** content27/adaptive detectors: 0 cuts. Camera locked: face width 97.3 px (0.5 s),
  99.5 (30 s), 92.2 (54.5 s). (ECC claimed a stepped 1.00->1.40 push; rejected — the poster overlays fooled it.)
- **Frame 0:** an empty 16-slot bracket (white lines, 8 slots per side) already sits over the speaker's legs/chair
  (6-94 % x, 47-79 % y). The face (≈43-57 % x, 31-41 % y) is never covered for the whole video.
- **15 matches**, each "A or B? → A." The two candidate posters (2:3 portrait, ≈0.23 W each) sit top-left / top-right,
  10-30 % y, i.e. above the head line and on both sides of it.
  - Poster entrance (0.033-0.267): opacity 0→1 with a short rise; right poster starts **2 frames** after the left; ~7 frames.
  - Choice: a white hand-drawn **check mark** under the chosen poster, drawn in ~4 frames. Lag from the spoken choice word
    onset: median **2 frames** (0-11 f; the long ones are hesitations "Hmm, Blippi", "Oh, Blue's Clues").
  - The winner's name pops into the next bracket slot (1 frame) about **6 frames after** the check.
  - Next pair: old pair dissolves while the new pair rises in, **16-19 frames** (median 17) total, starting on the next
    question's first word (−6 … +5 frames). Check → next pair median 0.87 s. Match length median **3.45 s** (2.2-5.6).
- **Round colour coding:** round-2 labels white; semifinal labels peach (#EEBB91); final pink (#DEA3AB);
  champion = big crimson pill (#B62842) "Bluey" at the chest, pops in ~5 frames at 54.87, small settle 55.40-55.57.
- **No subtitles at all.** All on-screen text = show names in bracket pills (label height 22-23 px of 1280 = 1.75 % H).
- **Sound (measured only):** speech median −17.7 dB, gaps median −34.6 dB (RMS per 23 ms, mixed track); onset rate 1.73/s.
  No claim about music or SFX.

## What makes it look professional (each = evidence + why it works, hypothesis)
1. **One visual system, no exceptions.** Same poster positions, same check, same label style for 15 rounds (s42_B, contact).
   The viewer learns the grammar in 2 s and then only watches the *content* (which show wins).
2. **Persistent state graphic.** The bracket accumulates every decision; the screen at 50 s is the story of the whole video.
   This is progress you can see — a retention device (people stay to see the champion). Alternative: format convention of the
   "bracket" trend (likely), not the editor's invention.
3. **Graphics never touch the face.** Posters above-and-beside the head, bracket over legs. Face box free in every sampled frame.
4. **Timing locked to speech, not to a beat.** Pairs change on the question's first word; check on the answer word (median
   +2 frames). Nothing appears before it is said.
5. **Small, quiet motion.** Entrances are opacity + short rise (~7 f), the only "big" moment is the champion pill. No zoom,
   no shake, no flashes — the content (fast answers) supplies the energy (match median 3.45 s).
6. **Colour as information.** Accent colours appear only to mark later rounds and the winner; otherwise white.
7. **Image = meaning.** The poster IS the thing being named — the graphic shows, the speech names. No text repeats speech.
8. **Clean ending:** payoff (champion) then out after 1.2 s; no CTA card.

## Limits
- Exact easing curves are estimated from 7-14 native frames, not from keyframes.
- Posters are copyrighted show art: for our videos the equivalent must be our own/licensed images (images.py, cutout, HTML).
