# D_cinematic_commercial

Heterogeneous commercial/showcase/vlog; select a subtype before copying rhythm.

Per-source notes are the evidence; these are hypotheses (medium), not testimony from the original editor.

## Recurring patterns and observations
- trajectory — observation: s21, s37. Evidence: their perception JSON; alternative: reused client template.
- material_cards — observation: s21. Evidence: their perception JSON; alternative: reused client template.
- panel_wipes — observation: s37. Evidence: their perception JSON; alternative: reused client template.
- caption_entrances — observation: s37. Evidence: their perception JSON; alternative: reused client template.
- bespoke_illustration — pattern: s11, s19, s37. Evidence: their perception JSON; alternative: reused client template.
- audio_stems_beats — observation: s21, s37. Evidence: their perception JSON; alternative: reused client template.

## Apply
Keep the brand palette/fonts, approved words and timings. Apply the motion/caption patch only to the per-video style. Recreate material graphics with our own assets. Preserve full-frame returns between graphic scenes; doctor-only guidance remains in notes.

## Limits
Unknown fonts, isolated sound levels, tiny microprint, unmeasured exits and exact easing remain unknown. Never turn candidate cut counts into rhythmic rules.

## Guruhga xos amaliy qaror
Bitta uslub emas: promo narx/mahsulot, showcase minimal single-caption, vlog clean-caption. Kamera canvas faqat mazmun yordam berganda; aralash group medianini cut rate sifatida ishlatma.

Detector median: 13.9 cuts/min, shot 1.66s, speech 140.5wpm (peer_global_stats.md). Bu majburiy cut rejasi emas. Motion label/sticker default 667ms: s37 canvas pan20 intervals@30; heterogeneous, subtype required. Boshqa turdagi harakatga aynan shu durationni majburlama.

DNA patch caption/motion defaultlarni beradi; card/canvas geometriyasi va semantik vaqtlarni agent elements.json ga yozadi. Brand rang/shrift ustun. Bitta accent, asosiy caps so‘z kamdan-kam; har yangi element matndan dalillansin. Hook matni ≤.3s source candidate, hozir automatic preflight emas.

## O‘lchangan nishonlar (quality gate)
Kesish/min [0, 46] (median 13.9), grafika/min [2, 20], grafikalar orasida ≥ 0.6 s, sokin bo‘lak ≥ 2.0 s, subtitr [1.5, 12.0] % H, kirish animatsiyasi [4, 14] kadr (30 fps), birinchi yozuv ≤ 0.5 s, yuz yopilishi ≤ 5%, LUFS [-17.5, -13.5].
Dalil: global_stats D: 0-46 cuts/min (median 13.9), subtype decides; s20 promo -17 LUFS.
Tekshiruv: `scripts/quality_gate.py` (docs/QUALITY_GATE.md).
