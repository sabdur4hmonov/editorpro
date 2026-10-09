# s23 self-check (claude, phase 2c)

| # | Claim | How checked | Result | Note |
|---|---|---|---|---|
| 1 | Hook title slides in from the right over ~12 frames, ease-out | m_text_0.17-0.70: x0 per frame 39.4, 39.4, 36.8, 34.6, 32.8, 31.1, 29.6, 28.5, 27.4, 26.4, 25.6, 24.7 | confirmed | Deltas shrink 2.6 -> 0.8 %/frame = ease-out; motion continues past 0.54 s (end not captured) |
| 2 | Hook zoom: no hard cut; first measured as push-in 1.00->1.24 | ECC + YuNet face height (261 px at 0.05 s, 220 at 0.8, 287 at 2.4) + strips | **contradicted, fixed** | My ECC tool had the scale sign inverted. Corrected tool: PULL-OUT 1.00->0.81 (0-0.73 s), then push-in to 1.04 (1.6-2.6 s). Meta still: pull-out 1.36x->1.0, not push-in. cc dip at 1.6 = flicker exit, frames continuous |
| 3 | Title exits by single-frame flicker (4 frames) | m_frames_1.45-1.95 frames #3-#8 | confirmed | — |
| 4 | Caps titles in the list assemble letter-by-letter in random order in 8 frames | strips_02 r5 + white-mask pixel count 0, 2917, 4975, 8581, 9211, 13147, 14409, 17071, 17832, 20985 | confirmed | Growth is stepwise, not a fade |
| 5 | List b-roll is darkened and desaturated vs speaker shots | HSV means at 9 times | confirmed for 11.7-22 s (sat 45-47, val 52-62 vs speaker 84-99 / 106-116) | **Contradiction**: 8.3 s speaker shot I called "grey" is darker (val 80) but NOT desaturated (sat 89). perception colour scene 4.44-8.94 says "low saturation": true for 5.0 (sat 64) only. |
| 6 | All text sits at chest height 46-62 % | m_grid at 0.6, 3.5, 12.3, 22.3, 26.5, 30.3 | partly | Exceptions: chat bubble 30-36 %, 7.7 caption 34-40 % |
| 7 | Speech pauses removed | m_rhythm: 0 gaps >= 0.3 s over 33.1 s | confirmed (whisper word times) | Word end times of fine-tuned whisper can over-extend; gaps of 0.2-0.3 s could exist |
| 8 | Cuts land on audio onsets more than chance | m_audio: 7/15 within 2 frames vs chance 0.26 | unsure | Onsets include speech syllables; this is not evidence of beat-cutting |
