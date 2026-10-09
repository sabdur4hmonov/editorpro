# Capability gap report

Count = distinct sample numbers/hashes, not number of occurrences. Evidence = each sample perception JSON. Original author method unknown.

| Rank | Technique | Before | Witnesses | Build / limitation |
|---|---|---|---|---|
| 1 | caption_entrances (14) | exists | s22, s24, s27, s28, s30, s33, s34, s35, s36, s37, s38, s39, s40, s41 | existing six entrances and Uzbek cluster fallback; extend recipes |
| 2 | material_cards (12) | missing | s21, s26, s29, s32, s33, s34, s35, s36, s38, s39, s40, s41 | paper/grid/ticket/polaroid/film sprite |
| 3 | trajectory (12) | partial | s21, s24, s25, s26, s28, s31, s32, s35, s37, s39, s40, s41 | shared keyframes, pivots, camera canvas; no true 3D |
| 4 | behind_person (7) | exists | s05, s22, s26, s29, s35, s40, s41 | PPHumanSeg; no invented perfect hair mask |
| 5 | relief_type (8) | partial | s22, s23, s25, s28, s31, s39, s40, s41 | outline and flat extrusion; existing glow retained |
| 6 | panel_wipes (7) | partial | s17, s24, s28, s31, s32, s37, s41 | moving viewport/mask; alpha and diagonal mask |
| 7 | true_3d_fold (6) | missing | s23, s28, s31, s35, s39, s41 | 2D/2.5D approximation only; external Blender/AE export optional |
| 8 | active_pills (5) | partial | s25, s26, s34, s35, s39 | cards with timed active state; fan via keyframes |
| 9 | bespoke_illustration (5) | partial | s09, s11, s19, s33, s37 | HTML/icons/canvas support; agent must draw original semantic scene |
| 10 | handwriting_stroke (5) | partial | s12, s14, s25, s34, s36 | arrow path exists; exact handwritten stroke remains external |
| 11 | audio_stems_beats (4) | partial | s21, s27, s31, s37 | mixed-track measurements cannot separate stems or prove beat synchrony |
| 12 | single_source_layout (4) | partial | s30, s31, s32, s38 | interpolate one speaker viewport; preserve legacy layouts |

Build order excludes already-existing entrances; priority: trajectory + materials, relief type, panel masks, active states and speaker morph. Exact 3D/folds, hand-drawn strokes, extracted musical beats and unknown font identity remain gaps; no new installation is silently required.

## Analysis coverage
All41 have cached metadata/audio and report folders; 1–20 deliberately brief reuse. New21–41 have overview visual review and literal inventory, but small unreadable text and unmeasured individual animation exits/easing remain explicit nulls. The study does not establish frame-exact measurements for EVERY animation. These limits are not hidden by a completeness claim.

## Builddan keyingi haqiqiy holat

Trajectory/card/canvas/active state/flat relief/one-speaker layout_morph qo‘shildi; test_motion_design.py mustaqil alpha, geometriya, frame boundary va brand precedence testlari. Six caption entrance mavjud modul qayta ishlatildi. flash.mode=invert (2–4 source frames candidate, foydalanuvchi didi bilan) endi mavjud; source-dependent raster, mustaqil alpha effect emas.

Static diagonal/arch card mask mavjud; HARAKATLI video panel wipe hali partial. Haqiqiy 3D/tracked type/fold missing; qo‘lyozma stroke partial. Hook ≤.3s, bir accent va rare giant caps — peer qo‘shgan qoidalar; hook automatic preflight yo‘q. Behind-person witnessesdan s30/s36 chiqarildi (7 tasdiqlangan avvalgi kuzatuv), occlusion yo‘qligi salbiy isbot ham emas.

Proofs3iteration tugadi: mexanika ishlaydi, professional reference reproduction hali teng emas. A kichik pill kalkulyator propiga teng emas va captionni qaytaradi; B2 row shared-pivot fan emas, ortiqcha "5" takrori; B1 chiqishda yuzni qisqa yopadi; C chiqishda safe-zone chetiga yaqinlashishi mumkin; D pan originaldan ancha qisqa. Kontrast A smog oynasida ritm ko‘rigi bilan qayta baholansin. Foydalanuvchining ≤3 iteration chegarasi sabab keyingi render qilinmadi.

CPU: Canvas/TrackedText full-frame RGBA alloc/warp qiladi; qisqa sahnalarda ishlat. Bbox/static-child caching keyingi optimizatsiya. Agent ovoz didini yoki harakatning professionalligini tasdiqlamaydi. 925672a/1926d6e build mustaqil Claude reviewdan o‘tgan (build_review_claude_committed.md); so‘nggi solo continuation hali mustaqil qayta ko‘rilmagan.

## Solo continuation (avvalgi iteration3 hisobotini almashtirmaydi)

Shared-pivot fan/stack/spread, original obyekt hero/path/trail/2.5D, semantic graphics proposals,
caption-label no-repeat va per-frame face safety qo‘shildi. Missing-face/unknown hech qachon gate pass emas.
B1 exit yuz muammosi tuzatildi; A label o‘rniga original o‘pka grafika, B2 row o‘rniga haqiqiy fan.
Caption masking asl matn va so‘z vaqtlarini o‘zgartirmaydi. Yangi skilllar format rejasini eski
universal talking-head qoidalaridan ustun qo‘yadi; sokin suhbatga majburiy follow/SFX/grafika yo‘q.

14 yangi qisqa proof, original-vs-new PTS strips, kuchli/sokin mix va texnik gate:
`solo_finish.md` / `solo_proof_summary.json`, `temp/style_study/finish/gallery.html`.
A/C/D gate o‘tdi; B1/B2 cut density fail saqlandi. To‘liq source texnikasi bilan tenglik da’vo qilinmaydi:
yo‘q dialog/rakurs/syujet/rolni bitta doktor kadri bilan yaratib bo‘lmaydi. D hali reference pan emas.
True3D/fold/haqiqiy pen stroke foydalanuvchi tomonidan keyingi GPU laptopgacha kechiktirilgan.
