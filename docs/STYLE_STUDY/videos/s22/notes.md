# s22 — Codex pilot observations (completed with explicit unknowns)

Source SHA1:6d7a181c46a4aa6fcb60e5eed665b529a89939f2. B2_kinetic_creator.
All4overview pages,4dense strip pages and contact sheet opened visually.
Discovery times below are nominal labels; overview resolution0.2s, native strip
adjacent frames ~0.03337s. Exact decoded PTS/colour/motion checks follow below.
Do not treat an estimated bbox or easing hypothesis as a precise measurement.

## Literal screen text and imagery, in timeline order

- 0.0–0.9 (overview_01 first row): full-body woman in brown suit/headscarf in park,
  phone in hand. Magenta bar reveals **qimmat telefoningiz bor**, with white sparkle.
  First frame only a short purple bar; finished line by0.2. No opening camera cut.
- ~1.0–2.6 (overview_01, strips_01 rows1–3): collage of several separately coloured
  pieces: **lekin** on pale-purple starburst, **video** on yellow star,
  **bo‘lib** on blue rectangle with a decorative hash, **baribir** on cream pill,
  search-like pill ending **Ko‘rinmayapti?** (needs full-resolution literal check),
  pink blob **arzon** with white dots. They accumulate, then flatten/fade near2.5.
  White corner handles/outline are visible around the entire collage.
- 2.603 cut (strips_01 r3 cells3–4): close shot, phone shown to camera.
  Three separate stacked tabs: **telefonizni** / **alishtirishga** / **shoshilmang**.
  First two spellings retained as seen; check native pixels before normalising them.
  Magenta/blue/lime rectangles; words enter at different times above the head.
- 4.204 cut (strips_01 r4): torso/phone close-up; **1 Obyektivni arting**.
  Bold white on dark bar, enlarged outlined1 to the left. Bar grows from a tiny
  horizontal stroke at~4.23 to near full by~4.40; no overshoot yet proven.
- ~6.2–8.4 (overview_01): small white unboxed cumulative sentence:
  **kulmang, eng ko‘p uchraydigan xato shu**. Phone lens wiping visible.
- 8.408 cut (strips_01 r5): wide side view holding phone away. Purple bar:
  **2 Orqa kamerada oling**. Bar/number grow from small centre to full, around8.48–8.64.
- 11.044 cut (strips_02 r1): seated bench view. Lime bar:
  **3 30 fps da oling**. Number is outlined/angled and larger than label.
  Tiny line at~11.11; still enlarging by11.31. Entrance start/settle require wider strip.
- 13.780 cut (strips_02 r2): seated→standing/walking full-body shot; the same lime
  banner persists across the camera cut. Thus a new cut does not always re-enter text.
- 15.582 cut (strips_02 r5): full-screen portrait b-roll of a different woman outdoors
  in black dress/white sleeves. Green tip3 banner briefly persists into new footage,
  dims and is replaced by white caption **agar sekinlashtiradigan joylar kerak bo‘lsa**.
  B-roll is colour, shallow depth, not B&W; provenance of the sample clip is unknown.
- ~17.8 (overview_02): **sizga 60 fps ishlatganingiz ma‘qul** begins while same b-roll
  remains, then18.352 cut to second woman/portrait against warm sunset/urban bokeh.
- 19.753 cut (strips_03 r1): original presenter returns in sunlit full body.
  Teal bar **4 Yorug‘likni to‘g‘ri qo‘yish** grows from stroke~19.85 to full~20.02.
- 21.355 cut (strips_03 r2): same presenter different angle/closer framing; tip4
  stays continuously visible across cut, fixed screen placement.
- 23.490 cut (strips_03 r3): front view; white cumulative caption
  **Va eng muhimi** (larger) then **kadrni chiroyli qilib ovozni unutib qo‘ymang**
  in smaller two lines. First Va appears~23.59, eng by23.72. No coloured block.
- 26.493 cut (strips_03 r5): three-quarter view. Individual rotated/displaced letters
  appear separately: Y at~26.59 then o/m…; **Yomon ovoz** completes by~27.2.
  Lime smaller strip **yaxshi videoni ham buzadi** underneath, not the same font size.
  Do not infer a real per-letter Bézier path from one discovery strip.
- ~27.8 (overview_03): round orange-edged logo badge appears below the caption.
  **KASB MARKAZI** is legible logo text, sample brand only; never reuse its asset.
- 28.395 cut (strips_03 r6): wider front presenter; small teal rounded word tabs:
  **telefon** (~28.4–28.6), **bilan** (~28.8), **professional** (~29.0–29.2),
  **kontent** (~29.4–29.6), **olishni** (~29.8–30.0), **o‘rganmoqchi** (~30.2–30.4),
  **bo‘lsangiz** (~30.6–31.0), **obuna** (~31.2), **bo‘ling** (~31.4–end).
  Need native timing to bracket every replacement. Not all words share one cue.
- 28.4–31.7 (overview_04/strips_04): round logo and white handle pill **@kasbmarkazi**
  below caption. Around30.3 orange gradient circle sweeps across pill to right;
  resolves into **obuna bo‘ling** and an orange check. No sound category inferred.

## Cuts verified from image neighbours

Both detectors agree on12candidate cuts. Each changes camera angle, shot scale,
subject/footage or pose discontinuously in the viewed neighbouring cached frames:
2.603,4.204,8.408,11.044,13.780,15.582,18.352,19.753,21.355,23.490,26.493,28.395.
Text entrances at4.23/8.48/etc are separate from those camera cuts.

## Pending measurements and uncertainties

- Full-resolution literals for hook search pill and the two spelling variants above.
- Exact PTS onset/end/settle for every text and sticker; phase0 strip labels nominal.
- Per-ROI glyph bounds/colour, separating outlined number from rectangular banner.
- Camera transform measurements with background features (walking is not auto zoom).
- Transcript/language/word rate and pauses; cached phase0 classification currently null.
- Mixed-track onset/RMS analysis, short-term loudness; isolated SFX/music/voice unknown.
# Pilot completion corrections / exact evidence

- Contact/overview times are discovery timestamps only; final native strips use decoded
  PTS. Keyframe reference: codex/measurements/s22/key_24b78583c4d1/index.json.
- Literal screen words corrected from native views: `telefonizni`, `ko‘rinyaptimi?`,
  `kulmang, eng ko‘p uchraydigan xato shu`; these are not replaced by Whisper spelling.
- Green advice badge is NOT a short6frame pop: it grows to76.543% fill width around
 11.545 then contracts to61.728% first trough around12.145–12.245. ~24% peak/trough
 ratio; first trough is not proven final rest (the badge continues slight bobbing).
 Largest green component curve in m_green_component.json excludes detached number3.
- Background RANSAC11.478–13.58 stays near1.0 while badge scales. White mask at4.204
 contains bright background/clothing before caption onset: rejected for text measurements.
- Caption3 stays across camera cuts13.78 and15.582; fade5frames into new b-roll,
 overlapping word `agar` around15.717. Native b821f262ba22be cells2–7.
- Yomon ovoz letters rotate/translate/scale into place26.594–27.127 (~16intervalframes).
 Not a pure opacity reveal; per-letter delays vary.
- Follow component gradient/check observed30.330–30.864 (~16intervalframes).
- Audio remeasured from mixed track:64EBU rows in m_mixed_audio.json; mixed mono median
 RMS in/outside transcribed-word spans −15.118/−20.275dBFS, NOT separated speech/music.
 Isolated music LUFS, SFX categories, ducking and musical beat alignment remain unknown.
- Frame grid bounds/size mostly manual estimates±2percent; original font names unknown.
 All creative conclusions are observations from one video, not production rules.

