# B1_editorial_paper

Paper/document narrative; actual evidence and numbers, restrained serif contrast.

Per-source notes are the evidence; these are hypotheses (medium), not testimony from the original editor.

## Recurring patterns and observations
- trajectory — pattern: s35, s39, s40, s41. Evidence: their perception JSON; alternative: reused client template.
- material_cards — pattern: s29, s34, s35, s36, s39, s40, s41. Evidence: their perception JSON; alternative: reused client template.
- relief_type — pattern: s39, s40, s41. Evidence: their perception JSON; alternative: reused client template.
- panel_wipes — observation: s41. Evidence: their perception JSON; alternative: reused client template.
- active_pills — pattern: s34, s35, s39. Evidence: their perception JSON; alternative: reused client template.
- caption_entrances — pattern: s34, s35, s36, s39, s40, s41. Evidence: their perception JSON; alternative: reused client template.
- behind_person — pattern: s29, s35, s40, s41. Evidence: their perception JSON; alternative: reused client template. s36 bu oynada unproven.
- handwriting_stroke — observation: s34, s36. Evidence: their perception JSON; alternative: reused client template.
- true_3d_fold — pattern: s35, s39, s41. Evidence: their perception JSON; alternative: reused client template.

## Apply
Keep the brand palette/fonts, approved words and timings. Apply the motion/caption patch only to the per-video style. Recreate material graphics with our own assets. Preserve full-frame returns between graphic scenes; doctor-only guidance remains in notes.

## Limits
Unknown fonts, isolated sound levels, tiny microprint, unmeasured exits and exact easing remain unknown. Never turn candidate cut counts into rhythmic rules.

## Guruhga xos amaliy qaror
Hujjat/statistika/ta’lim: qog‘oz va bitta dalil kartochkasi, qoramtir matn. Real 3D bukilish deb aytma. Kartochka chiqishi ham yuzni yopmasin.

Detector median: 12.1 cuts/min, shot 2.52s, speech 141wpm (peer_global_stats.md). Bu majburiy cut rejasi emas. Motion label/sticker default 520ms: s35 ticket window13 intervals@25, not true fold emulation. Boshqa turdagi harakatga aynan shu durationni majburlama.

DNA patch caption/motion defaultlarni beradi; card/canvas geometriyasi va semantik vaqtlarni agent elements.json ga yozadi. Brand rang/shrift ustun. Bitta accent, asosiy caps so‘z kamdan-kam; har yangi element matndan dalillansin. Hook matni ≤.3s source candidate, hozir automatic preflight emas.

## O‘lchangan nishonlar (quality gate)
Kesish/min [5, 21] (median 12.1), grafika/min [6, 18], grafikalar orasida ≥ 0.8 s, sokin bo‘lak ≥ 3.0 s, subtitr [2.0, 8.0] % H, kirish animatsiyasi [8, 16] kadr (30 fps), birinchi yozuv ≤ 0.3 s, yuz yopilishi ≤ 3%, LUFS [-15.5, -13.5].
Dalil: global_stats B1: 5.7-20.9 cuts/min (median 12.1); s29 giant word fade 8-10 f, invert 2-4 f; s40 grid pull-out 13 f.
Tekshiruv: `scripts/quality_gate.py` (docs/QUALITY_GATE.md).
