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

The original 158-word transcript is cached and unapproved. Never rerun Whisper or burn it in
on the strength of this engineering demo. Follow the single approval packet, then render full
draft and stronger/subtle audio, then await draft approval for final.

Supporting source study: [Apple continuity/springs](https://developer.apple.com/videos/play/wwdc2023/10158/),
[School of Motion lesson transcript](https://schoolofmotion.com/blog/intro-to-the-graph-editor-in-after-effects),
[Remotion spring](https://www.remotion.dev/docs/spring). YouTube playback was unavailable;
local reference frames and the publisher's lesson transcript were inspected instead.

The resumed real format plan also exposed `_setups` expecting four values from the five-value
`_faces` row (x/y/w/h/yaw). `scripts/formats.py` now uses the first four for its mask;
`test_background_setups_accept_detector_boxes_with_yaw` reproduces that failure with two backgrounds.
