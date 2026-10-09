# A_studio_explainer

Seated explainer; preserve speaker, semantic cards and one hero phrase.

Per-source notes are the evidence; these are hypotheses (medium), not testimony from the original editor.

## Recurring patterns and observations
- trajectory — observation: s25. Evidence: their perception JSON; alternative: reused client template.
- material_cards — observation: s33. Evidence: their perception JSON; alternative: reused client template.
- relief_type — observation: s25. Evidence: their perception JSON; alternative: reused client template.
- active_pills — observation: s25. Evidence: their perception JSON; alternative: reused client template.
- caption_entrances — observation: s33. Evidence: their perception JSON; alternative: reused client template.
- behind_person — observation: s05. Evidence: their perception JSON; alternative: reused client template.
- handwriting_stroke — observation: s25. Evidence: their perception JSON; alternative: reused client template.
- bespoke_illustration — observation: s09, s33. Evidence: their perception JSON; alternative: reused client template.

## Apply
Keep the brand palette/fonts, approved words and timings. Apply the motion/caption patch only to the per-video style. Recreate material graphics with our own assets. Preserve full-frame returns between graphic scenes; doctor-only guidance remains in notes.

## Limits
Unknown fonts, isolated sound levels, tiny microprint, unmeasured exits and exact easing remain unknown. Never turn candidate cut counts into rhythmic rules.

## Guruhga xos amaliy qaror
Seated doctor/explainer: katta doctor kadrini saqla, so‘zdagi real predmetni mos photo bilan ko‘rsat. Sarlavha va ayni so‘zli pillni yonma-yon takrorlama.

Detector median: 9.55 cuts/min, shot 2.62s, speech 146.5wpm (peer_global_stats.md). Bu majburiy cut rejasi emas. Motion label/sticker default 360ms: s25 phone rise ~10 intervals@25. Boshqa turdagi harakatga aynan shu durationni majburlama.

DNA patch caption/motion defaultlarni beradi; card/canvas geometriyasi va semantik vaqtlarni agent elements.json ga yozadi. Brand rang/shrift ustun. Bitta accent, asosiy caps so‘z kamdan-kam; har yangi element matndan dalillansin. Hook matni ≤.3s source candidate, hozir automatic preflight emas.

## O‘lchangan nishonlar (quality gate)
Kesish/min [0, 18.5] (median 9.55), grafika/min [4, 16], grafikalar orasida ≥ 0.8 s, sokin bo‘lak ≥ 3.0 s, subtitr [2.5, 6.0] % H, kirish animatsiyasi [6, 12] kadr (30 fps), birinchi yozuv ≤ 0.3 s, yuz yopilishi ≤ 3%, LUFS [-15.5, -13.5].
Dalil: global_stats A: cuts/min 0-18.5 (median 9.55); s42 poster entrance 7 f, check 4 f; s25 phone rise ~10 f@25; s33 prop 9 f@25.
Tekshiruv: `scripts/quality_gate.py` (docs/QUALITY_GATE.md).

## Sample 42 (s42) dan o‘rganilgan
- Bitta qotgan kadr, 0 kesish, zoom yo‘q (yuz kengligi 92-100 px doimiy). Energiya mazmundan: 15 tur, median 3.45 s.
- Grafika yuzga tegmaydi: plakatlar boshdan yuqorida chap/o‘ngda, jadval oyoqlar ustida.
- Belgi (check) tanlangan so‘zdan median 2 kadr keyin, g‘olib yorlig‘i yana ~6 kadrdan keyin; yangi juftlik keyingi
  savolning birinchi so‘zida (−6…+5 kadr), almashish 17 kadr.
- Kirish: shaffoflik + qisqa ko‘tarilish ~7 kadr, o‘ng plakat 2 kadr keyin. Rang faqat bosqichni bildiradi.
- Subtitr umuman yo‘q: rasm narsani ko‘rsatadi, yozuv faqat jadvalda. Bizda: grafika subtitrni takrorlamaydi.
- Davomli holat grafikasi (persistent state): ro‘yxat/reyting/solishtirishda ekran butun hikoyani jamlaydi.
