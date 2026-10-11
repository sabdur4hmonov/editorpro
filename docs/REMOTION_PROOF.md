# Remotion smoothness dalili — 2026-10-12

Doktor 5 ning oldin tasdiqlangan dastlabki 10,9 soniyasi ikki dvigatelda render qilindi. Asl klip, SRT, so‘z vaqtlari va 8,5–10,9 soniyadagi siydik namunasi surati bir xil. Asl input, video papkasi va eslatmasi o‘zgarmadi. Manba 25 fps; ikkala eksport 30 fps, 1080×1920.

Before — eski numeric-fps uslub; after — blend interpolation va yangi barqaror subtitr joylashuvi. Joylashuv ham o‘zgargani uchun bu faqat easingni alohida o‘lchagan tajriba emas. Musiqa va SFX qo‘shilmadi. Texnik tekshiruv professional did yoki ritm tasdig‘ini bermaydi.

| O‘lchov | Before native | After Remotion |
|---|---:|---:|
| Chiqish | 1080×1920, 328 kadr | 1080×1920, 328 kadr |
| Yuqori hududdagi takror kadr proxy | 9 nomzod | 0 |
| PTS teshigi | Native baseline hisobotida | 0 |
| Drift titrashi | Native: 1,196 px | DOM hold chegarasi ≤0,35 px; 0 buzilish — boshqa o‘lchov |
| Yuz xavfsizligi | Native changed-pixel: 4–8% ogohlantirish | 261 yuzli kadr; konservativ DOM to‘rtburchak ustma-ustligi 0% |
| Animatsiya xilma-xilligi | 6 bir xil blur bo‘lagi | Pop / slide / wipe; seed saqlangan |
| Audio/video oxiri farqi | Asl mixer | 0,00000033 s |

After: 328 DOM kadr, 1499 to‘rtburchak, 0 xato va 0 chiqish ogohlantirishi. Yuz va tezlikning turli usulda o‘lchangan natijalari bir xil metric sifatida taqqoslanmaydi. Final AAC ochilib tekshiriladi; Whisper so‘z boshlanishlari saqlanadi va kadrga yuqoriga yaxlitlash kechikishi ≤1 kadr. Ovoz didi, ma’no va interpolation sifati inson ko‘rigida qoladi.

## Performance / cache

Concurrency 2, Node heap 1536 MiB, CPU. Full 1080 visual bo‘laklar: 39,9 / 52,8 / 62,8 s, jami 155,5 s. Shu payt boshqa test yuklamasi ham bor edi. Native full before: 29,0 s. Yangi timeline sekinroq; cache o‘zgarmagan visual bo‘laklarni tejaydi, final encode va QA esa baribir ishlaydi (oxirgi cached eksport taxminan 1 daqiqa). Cold render tezlashgani da’vo qilinmaydi.

Oxirgi suratning dim qiymati o‘zgartirilganda: dastlabki 2 bo‘lak CACHE, oxirgisi RENDER — 53,944 s. Aynan avvalgi timeline qaytarilganda 3/3 CACHE. Har 4 s bo‘lak kalitida source, asset, config, subtitr, exit overlap, renderer kodi va versiya bor. Cache budjeti 2 GiB; faol bo‘laklar budjetdan oshsa ogohlantirib saqlanadi. O‘z jobining eskirgan media, bundle, staging va PCM oraliq fayllari muvaffaqiyatdan keyin tozalanadi.

60 fps + blur: 540×960 dagi 2 s / 120 kadr 22,9 s da render qilindi. Yuz gate qo‘shilishidan oldingi shu sinovda 0 DOM xato / 0 chiqish ogohlantirishi. 60 fps standart emas; CPU narxi va interpolation tekshiriladi. 2× supersampling ulangan va type-check qilingan, lekin benchmark qilinmadi, ushbu demo uchun kerak bo‘lmadi. GPU sinovi, install yoki download bo‘lmadi.

## Regression tests

13 suite, 205 test: Remotion 18, Studio 17, AgentSetup 13, Motion 15, MotionPolish 14, Smooth 22, Takes 17, Formats 9, Quality 20, MotionDesign 25, Sprint2 21, Part0 5, SFX 9. TypeScript va 7 egri chiziqli Node easing testi o‘tdi. Checklar yumshatilmadi.

Kod 74b455f da saqlangach, aynan 75 skript nusxasi bilan alohida snapshotda `selftest.py --no-whisper` qayta o‘tdi: **NATIJA: 45/45 tekshiruv o'tdi.** Production tugallanmagan eslatmalari o‘zgarmadi. Manifest: `temp/remotion_upgrade/selftest_snapshot/source_hashes.json`; log yonidagi `selftest.log` da.

Windows sandbox initially blocked Chrome localhost WebSocket (EACCES); approved external-sandbox rendering succeeded. Font/layout QA first caught zero rectangles and unsafe bounds; font/layout waits and real padding/asymmetric margins were corrected, checks retained. Post-normalization PCM was50–80ms short; flush tail and exact frame-grid trim fixed it without retiming speech. QA sheets usePillow timecodes because this FFmpeg build's drawtext/fontconfig crashed. Captured cache/QA/face failures retain old delivery.

## Artifacts

- output/motion_demo_AB.mp4 — same timestamps, left OLD/right REMOTION, speech only from after.
- output/motion_demo_before_full.mp4; output/motion_demo_after_final.mp4.
- temp/remotion_upgrade/ab.jpg; dispatch_stills.jpg.
- temp/remotion_upgrade/demo/qa/motion_demo_after_final/report.md and transition_*.jpg (every3rdframe).
- temp/remotion_upgrade/proof.json; demo/remotion/cache_proof.json.
- temp/remotion_upgrade/demo/credits.txt: Urine sample/Turbotorque/Public domain, Wikimedia; approved existing asset, no samples footage copied.

## Scope

New supported talking-head jobs use --engine remotion. Native/ASS and approved snapshots remain available. Custom advanced scenes/alpha overlays need retained standalone Remotion + native composition; full timeline refuses unverified/unsupported cases instead of silent loss. Full limits:docs/MOTION_LIMITATIONS.md. Usage:docs/how-to-use.md. Studio localhost IAB preview did not connect in this environment; headless outputs and compose dispatcher stills were verified.
