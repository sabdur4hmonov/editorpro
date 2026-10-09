# B2_kinetic_creator

Creator/tutorial with confident hook and short kinetic emphasis.

Per-source notes are the evidence; these are hypotheses (medium), not testimony from the original editor.

## Recurring patterns and observations
- trajectory — pattern: s24, s26, s28. Evidence: their perception JSON; alternative: reused client template.
- material_cards — observation: s26. Evidence: their perception JSON; alternative: reused client template.
- relief_type — pattern: s22, s23, s28. Evidence: their perception JSON; alternative: reused client template.
- panel_wipes — pattern: s17, s24, s28. Evidence: their perception JSON; alternative: reused client template.
- active_pills — observation: s26. Evidence: their perception JSON; alternative: reused client template.
- caption_entrances — pattern: s22, s24, s27, s28. Evidence: their perception JSON; alternative: reused client template.
- behind_person — observation: s22, s26. Evidence: their perception JSON; alternative: reused client template.
- handwriting_stroke — observation: s12, s14. Evidence: their perception JSON; alternative: reused client template.
- true_3d_fold — observation: s23, s28. Evidence: their perception JSON; alternative: reused client template.
- audio_stems_beats — observation: s27. Evidence: their perception JSON; alternative: reused client template.

## Apply
Keep the brand palette/fonts, approved words and timings. Apply the motion/caption patch only to the per-video style. Recreate material graphics with our own assets. Preserve full-frame returns between graphic scenes; doctor-only guidance remains in notes.

## Limits
Unknown fonts, isolated sound levels, tiny microprint, unmeasured exits and exact easing remain unknown. Never turn candidate cut counts into rhythmic rules.

## Guruhga xos amaliy qaror
Creator/tutorial: kuchli qisqa urg‘u. Fan faqat nutqda haqiqiy ro‘yxat bo‘lsa, umumiy pivot va so‘z vaqti bilan. Number+numbered row+bir xil captionni uch marta ko‘rsatma.

Detector median: 22.2 cuts/min, shot 1.92s, speech 155wpm (peer_global_stats.md). Bu majburiy cut rejasi emas. Motion label/sticker default 430ms: s24 diagonal panel13 intervals@30; per-pill pop .12s distinct. Boshqa turdagi harakatga aynan shu durationni majburlama.

DNA patch caption/motion defaultlarni beradi; card/canvas geometriyasi va semantik vaqtlarni agent elements.json ga yozadi. Brand rang/shrift ustun. Bitta accent, asosiy caps so‘z kamdan-kam; har yangi element matndan dalillansin. Hook matni ≤.3s source candidate, hozir automatic preflight emas.

## O‘lchangan nishonlar (quality gate)
Kesish/min [12, 38] (median 22.2), grafika/min [8, 24], grafikalar orasida ≥ 0.6 s, sokin bo‘lak ≥ 2.0 s, subtitr [2.5, 14.0] % H, kirish animatsiyasi [3, 13] kadr (30 fps), birinchi yozuv ≤ 0.3 s, yuz yopilishi ≤ 5%, LUFS [-15.5, -13.5].
Dalil: global_stats B2: 12.3-38.1 cuts/min (median 22.2); s24 diagonal panel 13 f; s26 pill 6-8 f@25; s28 word 3 f.
Tekshiruv: `scripts/quality_gate.py` (docs/QUALITY_GATE.md).
