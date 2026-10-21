# Persistent-card motion — opt-in USA-lawyer continuation

The existing overlay renderer accepts `type: continuity_card`. Do not replace the legacy spring,
approved video styles or the full timeline engine. The new scene is standalone transparent video;
native compose is the retained path for alpha compositing and full-video face checks.

Files: `remotion/src/continuity.mjs`, `remotion/src/ContinuityCard.tsx`.
Registration: `remotion/src/scenes.tsx`. Test: `node --test remotion/continuity.test.mjs`.

## Timing and layout

Root/scene `from`, `duration`, `durationInFrames` are frames. A state's `at` and `duration`
are SECONDS relative to its scene. States are ordered, non-overlapping; initial geometry
may use duration 0. x/y are centres; w/h/radius are normalized to the output size
(radius uses width). Values remain fractional. Opacity is bounded 0–1.

`minimumJerk` is a rest-to-rest quintic. `settledSpring` evaluates under/critical/overdamped
response, then blends its final tail to rest. This is an editorial easing model, not Apple's
original spring implementation or a velocity-preserving retargeting engine. The state validator
deliberately rejects overlapping/interrupting transitions.

One clipped surface persists through position/size/radius/rotation/opacity changes. Changed
content snapshots retain their final layout during entry, so a widening parent mask cannot
reflow the title. When the title/icon remain the same, a single main-content layer survives the
compact morph; the secondary text/badge fade away. Content geometry follows the same transition
clock, including its starting layout, so no state-boundary snap is introduced.

`theme` controls font, ink, accent and paper; per-scene background/stroke/fontSize are optional.
Test with the longest real title at BOTH endpoint widths; multi-line subtitles need a separate
layout review because the current compact reveal reserves one subtitle line. Do not claim this
to be a generic text auto-fit engine. Source fps must be preserved by the caller.

## Resumed proof and remaining work

2026-10-21 USA-lawyer props/review remain in ignored `temp/usa_lawyer/`:
`study/RESEARCH.md`, `review/entry_ab.jpg`, `review/morph_native.jpg`, `review/exit_native.jpg`,
`review/motion_geometry.json`, `review/review_checks.json`, `RESUME.md`, `APPROVAL.md`.
The preview is five 3.5s excerpts, 540x960/30fps, without subtitles/audio. ProRes4444 alpha
is decoded and checked against detected expanded YuNet boxes on every active excerpt frame.
That does not prove full-video safety, caption timing, audio balance or user rhythm approval.

The original 158-word transcript is cached. The engineering demo alone did not authorize a full
subtitle export. Later, the user explicitly requested the complete captioned edit with speech/SFX
before taste review (2026-10-21); `temp/usa_lawyer/v2/authorization.md` records that instruction.
It supersedes the earlier wait for this job, without claiming uncertain spellings were verified.
Never rerun Whisper over the preserved originals.

Supporting source study: [Apple continuity/springs](https://developer.apple.com/videos/play/wwdc2023/10158/),
[School of Motion lesson transcript](https://schoolofmotion.com/blog/intro-to-the-graph-editor-in-after-effects),
[Remotion spring](https://www.remotion.dev/docs/spring). YouTube playback was unavailable;
local reference frames and the publisher's lesson transcript were inspected instead.

The resumed real format plan also exposed `_setups` expecting four values from the five-value
`_faces` row (x/y/w/h/yaw). `scripts/formats.py` now uses the first four for its mask;
`test_background_setups_accept_detector_boxes_with_yaw` reproduces that failure with two backgrounds.

## Full-edit revision after user feedback

The user rejected removal of the small secondary line. For persistent information, keep title,
subtitle and icon in every state and retain the card's width/height through entry, hold and exit.
The USA-lawyer revision uses opacity plus a small vertical move, without a compact morph.

`type: paper_explainer` adds an original opaque explanatory scene, rendered with the same
standalone overlay renderer. Props: `title`, `subtitle`, optional `eyebrow`/`number`, and
`kind: calendar | flow | record | form`. It requires root/scene duration in frames and a theme.
The title and secondary line remain present; local Inter and deterministic staged spring clocks
produce fractional placement. The calendar illustrates six elapsed months; flow shows
Qaytish → CBP → Izoh. Document drawings are schematic, not official form reproductions.
Do not reuse those semantic labels for unrelated footage without changing the component.

Opaque scenes enter native compose as full b-roll; transparent continuity cards enter as image
overlays so the native per-frame face measurement remains active. Give each element its actual
entry `duration` (including an already-rendered entrance), rather than measuring an unused
global sticker default. Technical scores do not establish professional taste or sound approval.

A verified continuous applied cut list has no audio joins to meter. The gate now marks only
that exact case as not applicable; missing cut evidence and unmetered existing joins remain
unknown. `test_audio_joins_na_only_for_verified_empty_cut_list` protects this distinction.

The native retry also isolates each caption's scrim under its own trace identity: adjacent
sentences are separate surfaces, rather than a single object teleporting between box sizes.
`motion.resting_snap: false` is an opt-in for continuously fractional placement at rest and
during fades. It avoids a final rounding hop after a slow move; the default remains `true`
to preserve previously approved pixel-sharp resting frames. Motion-polish regressions cover
both the default and opt-out. The revision uses authored fade/blur/mask entrances, rather
than legacy `rise` (whose fixed spring/amplitude does not use `captions.rise_px`).
