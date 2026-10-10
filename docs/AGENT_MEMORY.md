# Claude va Codex uchun umumiy tajriba

Har sessiya boshida o'qiladi. Bu jurnal Gitda saqlanadi; HOLAT.md esa hozirgi ish va
foydalanuvchi tasdiqlarini saqlaydi. Bir agent yozgan tajribani keyingisi ham qo'llaydi.

Har montajdan va texnik o'zgarishdan keyin pastga yoz:

Parallel montajda bu umumiy faylga darhol yozilmaydi: tajribani faqat o'z
temp/<video>/deferred_learning.md faylingga yoz. Oxirida boshqa agent idle bo'lgach,
bitta agent jurnal, feedback va glossary yozuvlarini umumiy fayllarga ko'chiradi.

- Sana, agent, video/brend yoki texnik vazifa.
- Nima ishladi / nima ishlamadi; sabab va dalil (fayl, vaqt, test, commit).
- Keyingi agent uchun takrorlanadigan aniq tavsiya.
- Holat: **tekshirilgan**, **foydalanuvchi tasdiqlagan** yoki **taxmin**.

Taxminni qoida deb qabul qilma. Tasdiqlanmagan didni brendga yozma. Mijoz fikri
`feedback.py` orqali tegishli notes.md ga, takroriy so'z xatosi `glossary.py` orqali lug'atga
yoziladi. Bu jurnal ularning o'rnini bosmaydi. Kalitlar va maxfiy ma'lumotlar yozilmaydi.
Tajriba o'zgarsa eski yozuvni yo'qotma: uning o'rnini bosuvchi yangi yozuvni ko'rsat.

## 2026-10-07 — Codex — HTML grafika — tekshirilgan

- Edge jarayoni taxminan 0.45 soniyada qaytgan, PNG taxminan 1.5 soniyada paydo bo'lgan.
  Jarayon tugashi fayl yozilib bo'lganini anglatmaydi.
- `scripts/html_render.py` PNG hajmi kamida 0.5 soniya o'zgarmasligini kutadi (10 soniya limit).
- Dalil: `b461176`, ketma-ket uchta to'liq selftest: 48/48.
- Keyingi agent: brauzer grafikasida jarayon kodi bilan birga fayl tayyorligini tekshir;
  xatoni yashirish uchun selftestni zaiflashtirma.

## 2026-10-07 — Codex — ikkala agent skilllari — tekshirilgan

- Manba: `docs/claude_skills/`; Claude nusxasi o'zgarishsiz, Codex nusxasida faqat
  `argument-hint` olib tashlanadi va `$ARGUMENTS` foydalanuvchi argumentlari izohiga almashtiriladi.
- Dalil: `9b54000`, to'rtta Codex skill formati tekshirilgan.
- Keyingi agent: nusxani alohida tahrir qilma; manbani yangilab `sync_skills.py --apply` ishlat.

## 2026-10-07 — Codex — umumiy setup va sifat tartibi — tekshirilgan

- Claude montaj/namuna nusxalarida manbadagi Handoff bo'limi yo'q edi; manbadan sinxronlandi.
  Codex nusxalari avvaldan mos edi. Manbalar o'zgartirilmadi.
- Mahalliy MCP state/guide/skills vositalari uchun; montajni mavjud Python skriptlari bajaradi.
  Codex configdagi serverni tanidi; Claude project configdagi serverni tanidi, tasdiq kutilmoqda.
- Dalil: `test_agent_setup.py` uchta test (skill yangilanishi, manba yetishmasa yozmaslik,
  haqiqiy stdio protokoli va ruxsat etilmagan so'rovlar); selftest --no-whisper: 44/44.
- Keyingi agent: har montajda EDIT_QUALITY.md bo'yicha review.md to'ldir, natijadan tajriba yoz.
  MCP mavjudligi o'zi montaj sifati yoki ovoz tanlovi tasdiqlanganini bildirmaydi.

## 2026-10-07 — chat (Claude) — Codex limitda to'xtagan ishni tekshirish — tekshirilgan

- Codex studio.py, person_mask.py, --draft, --prepare-only, behind_person, handnote/arrow/phone/profile
  ishini commit qilmasdan limitga yetgan. Fayllar butun: hammasi kompilyatsiya bo'ladi, kesilgan fayl yo'q,
  PPHumanSeg modeli hash bilan mos, skill nusxalari sinxron.
- Topilgan ikki muammo, ikkalasi `scripts/selftest.py` da va tuzatildi:
  1. Sinov `handoff.py set` bilan haqiqiy HOLAT.md ustidan yozib, keyin o'chirib yuborardi. Endi baytma-bayt
     saqlab, `finally` ichida joyiga qaytaradi.
  2. "Namuna uslubi" sinovidagi 9-subtitr sinov klipidan (~7.4 s) tashqariga chiqardi; yangi avtomatik
     preflight buni to'g'ri rad etdi. Sinov vaqtlari klip ichiga sig'dirildi, preflight zaiflashtirilmadi.
- Dalil: to'liq selftest 47/47, test_studio.py 10/10, test_agent_setup.py 3/3 (bulut nusxasida);
  namuna 7 kadrida behind_person, handnote, arrow, profile ko'rib tekshirildi (soch cheti biroz notekis).
- Keyingi agent: yangi himoya (preflight) eski sinovni yiqitsa, sinov ma'lumotini to'g'rilang, himoyani
  bo'shashtirmang. Limit tugashidan oldin commit qilinmagan ishni keyingi agent avval tekshirib commit qiladi.

## 2026-10-07 — Claude — "doktor 1" (brendsiz, birinchi to'liq haqiqiy montaj) — foydalanuvchi tasdiqlagan

Nima sekinlashtirdi (keyingi safar takrorlanmasin):
- **Whisper small o'zbekchada yaroqsiz.** Matn butunlay buzildi; men buni sheva deb noto'g'ri taxmin qildim.
  `yuldashev222/whisper-small-uz-v1-ct2` (HF keshida) gaplarni deyarli to'g'ri yozdi. O'zbek videoda darhol shu
  model: `--model yuldashev222/...` (per-language standart taklif qilingan, foydalanuvchi javobi kutilmoqda).
- **Savollar ro'yxati.** Har shubhali so'zni alohida so'rash foydalanuvchini charchatdi. Endi: taxminni o'zing
  qo'llab `[?so'z]` bilan belgila, matn + reja + stills + rasmlar bitta xabarda (skilllarga yozildi).
- **Rasm tanlash.** Ramkali stok foto rad etildi; kesilgan stiker kerak (`scripts/cutout.py`). Har rasm so'zga
  ANIQ mos bo'lsin ("ba'zilari umuman mos emas" - foydalanuvchi). Joyi subtitr ostida, yuz/matn/qo'l ustida emas.
  Bitta model hamma rasmda toza kesmaydi: IS-Net (och fonda och teri) va BiRefNet (probirka, stetoskop) ni
  `--sheet` da solishtir. Asl rasmdagi izoh/harf bo'lsa `cv2.inpaint` bilan tozala (yurak modeli).
- **To'liq ekranli stok b-roll rad etildi** (Pixabay, 3 klip). Faqat so'ralganda; namuna 15/16 tahlili
  `NAMUNA_USLUBI.md` §5a da. `grade` b-roll'ga ta'sir qilmaydi -> `broll.bw/dim/focus_x` qo'shildi.
- `images.py pick` OXIRGI qidiruvning `candidates.json` idan tanlaydi: bir necha qidiruvdan keyin noto'g'ri rasm
  yuklandi (kislorod). Har qidiruvdan keyin json nusxasini saqla va pick'dan oldin qaytar.
- Lug'at o'zgarsa pipeline opts o'zgaradi va qo'lda belgilangan `subs.srt` qayta yoziladi: tayyor ishni qayta
  render qilganda `--no-glossary` qo'sh yoki belgilarni `corrections.json` ga ham yoz (shunday qilindi).

Ishladi:
- Per-video uslub: `style.json` nusxasi `temp/<job>/style.json`, `--style` bilan (load_style faylni to'liq almashtiradi).
- Kasallik nomlari `~~nom~~` + `captions.mark2_big: true` (katta qizil quti, #E5383B to'q ko'k forma ustida o'qiladi).
- Follow handle'siz: `icon` + kattaroq tugma (commit b9b3b8b, d4f44a0).
- Dalil: commitlar b9b3b8b, d4f44a0, 2ad30c0, b56cb12, d2b23aa, 633bc2c; test_studio 13/13, selftest 44/44;
  `output/doktor_1_final.mp4` 1080x1920 30 fps -14.0 LUFS, platforma [OK].

Ochiq: finalda yuz manbaga nisbatan yumshoqroq (4K->1080 keyin zoom INTER_LINEAR, crf 20) - taklif berildi, kutilmoqda.

## 2026-10-07 — Codex — ikki video parallel montaji — tekshirilgan

- Avvalgi bir-agent tartibi yangilandi: ikki turli video parallel tayyorlanadi, ammo CPU ishlari
  FIFO navbatda bittadan. MONTAJ_AGENT egani, MONTAJ_BUSY_TIMEOUT kutish limitini bildiradi
  (standart 7200s). Heartbeat 5s va stale 25s saqlandi; token va OS qulfi eski egani yangi
  egani o'chirishdan, claim/heartbeat/release poygasidan himoyalaydi.
- handoff.py set/show/clear --video: temp/<video>/HOLAT.md, agent egasi va status. Begona egaga
  yozish/clear va bir xil temp nomiga boshqa manbani yozish rad etiladi. Project HOLAT.md umumiy
  state uchun qoladi. Clear video note'ni o'chirmaydi, status done qilib matn/tasdiqlarni saqlaydi.
  Har set'da joriy holat bilan tegishli avvalgi tasdiqlarni ham saqla: set yangi holatni almashtiradi.
- Haqiqiy to'qnashuv: html_render.py umumiy temp/.html_render/profile ishlatardi. Endi har
  videoda temp/<video>/.html_render/profile va --style. Ikki parallel qizil/ko'k PNG alohida
  profillarda tekshirildi. Edge bolalar jarayoni PNG tayyor bo'lgach ham profil SQLite faylini
  qisqa ushlab turishi mumkin: test cleanup faqat PermissionError'da 30s gacha qayta urinadi,
  to'liq tozalash talabini saqlaydi; doimiy xato bo'lsa test yiqiladi.
- Dalil: test_agent_setup.py 11/11 (7 qulf/ownership sinovi, parallel HTML, 3 sync/MCP sinovi),
  test_studio.py 13/13, yakuniy selftest --no-whisper: 44/44. Selftestdagi eski darhol-rad-qulf tekshiruvi yangi talablarga mos:
  kutish chiqishi + aniq limit xatosi talab qilinadi, boshqa egaga ish boshlash taqiqlangan.
- Keyingi agent: docs/PARALLEL.md promptlarini ishlat. Avval o'z --video note'ingni egala,
  keyin to'liq per-video style nusxasi; frames -o, compare_models --out-dir va boshqa
  yordamchi natijalar o'z papkangda. Boshqa unfinished video bor paytda umumiy kod/docs/brend/
  skilllar va selftestga tegma; kod kerak bo'lsa to'xta va foydalanuvchiga ayt. Parallel commit
  yo'q; yakunda bitta idle agent deferred_learning yozuvlarini umumlashtiradi.

## 2026-10-08 — Claude — "doktor 2" (parallel, deferred) va restoran promo setup (namuna 20) — tekshirilgan

doktor 2 (output/doktor_2_final.mp4, foydalanuvchi "ha" bilan, effektli):
- Bo'lak belgisi (`{caps}` ...) presetning o'z `glow` ini qaytarardi: qizil so'zlar atrofida tuman. Tuzatildi:
  `CaptionLayer._cue_cfg` uslub faylidagi `font`, `accent` va endi `glow` ni ham saqlaydi. `captions.glow: null`
  porlashni o'chirmaydi (caption_cfg None ni o'tkazib yuboradi): o'chirish `{"blur": 0, "opacity": 0}`.
- `behind_person` broll/stage/scene/grade bilan BIR VIDEODA ishlamaydi (preflight butun video bo'yicha rad etadi).
- B-roll gapga aniq mos bo'lsin; oq xalatda yalpiz/oq yozuv o'qilmaydi (feedback.py ga yozildi).

Restoran promo (namuna 20, `docs/PROMO.md`, `/promo` skilli):
- Yangi: `assemble.py` (speech/product/voiceover kliplari -> bitta asosiy video; product oraliqlari `protect`
  bilan jimlik kesishidan himoyalangan), pipeline papka/clips.json qabul qiladi; presetlar `promo`
  (kursiv porlovchi, `sub_justify`) va `vo`; elementlar `label` (taom yorlig'i) va `aside` (yuz yonidagi so'zlar).
- Namuna 20 kliplarida sinov (`temp/promo_test`, `studio.py compare`): "5 kishilik", yorliq, VO subtitr, narx,
  qo'lyozma joyi va o'lchami namunaga ustma-ust tushdi. Sinov kadrlarida namunaning o'z yozuvi ham bor (tayyor
  video) - taqqoslashda ikkita matn ko'rinadi, bu kutilgan.
- Tezlik (CPU): 60 fps HEVC 1440x2560 yig'ish ~34 s / 10 s; to'liq render ~63 s / 10 s; HEVC to'g'ridan ~82 s / 10 s.
- Namuna musiqasi doimiy bo'lgani uchun sinovda jimlik kesilmadi; himoya sintetik test bilan isbotlangan.
- Dalil: test_studio 16/16 (3 yangi: promo/justify/glow, label/aside, assemble+protect), test_agent_setup 11/11
  (sync soni NAMES dan hisoblanadi), selftest --no-whisper 44/44.
- Keyingi agent: promo ishida birinchi ishga tushirish `temp/<nom>/clips.json` shablon yaratadi - rollarni
  tekshirmasdan davom etma. Yon so'zlar subtitrdan olib tashlanadi (`corrections.json` "text": ""), aks holda ikki marta chiqadi.

## 2026-10-08 — Claude — promo mustaqil ish va uslub xilma-xilligi — tekshirilgan

- Foydalanuvchi qoidasi: promo uchun faqat kliplar beriladi. Nom, set, narx, taklif, chaqiriq faqat nutqdan yoki
  kadrda aniq ko'ringan yozuvdan; shubhali -> `[?]` + manba (klip + vaqt). Yagona savol: Instagram manzili (bir marta).
  Musiqa/logotip faylsiz: kliplarning o'z ovozi (`product_audio` standarti endi `keep`), logotipsiz.
  Shu qoidalar AGENTS.md "Mustaqil ish" va namuna/montaj/promo skilllarida (## Autonomy).
- Rollar: pipeline transkripsiyadan keyin "Kliplar bo'yicha nutq" jadvalini chiqaradi (`assemble.report`): ovozli
  lekin so'zsiz klip -> product bo'lishi mumkin.
- Uslub: `style/promo_looks.json` da 5 yo'nalish (warm_glow, clean_minimal, bold_caps, editorial_serif,
  fresh_marker), `promo_looks.py palette/apply/record`; `apply` oxirgi promo yo'nalishini rad etadi
  (`style/promo_history.json`). Sinov promo tarixga yozilmagan.
- Topilgan xato: `load_history(path=HISTORY_PATH)` standart qiymati import paytida qotib qolardi; test
  yo'lni almashtirganda `record` va `apply` boshqa fayllarni ishlatardi. Endi yo'l chaqiruv paytida olinadi.
- Codex: `$promo input\<papka>`, Claude: `/promo input\<papka>`; test_agent_setup promo skillini ikkala nusxada tekshiradi.
- Dalil: test_studio 17/17, test_agent_setup 12/12, selftest --no-whisper 44/44, sync_skills --check sinxron.
- Keyingi agent: promoni yo'nalish tanlamasdan boshlama; palette natijasini va bir qator sababni tasdiq xabariga yoz;
  final tayyor bo'lgach `promo_looks.py record` (aks holda keyingi promo takrorlanishi mumkin).

## 2026-10-08 — Claude — klip papkasi: dubl tanlash (takes) — tekshirilgan (sintetik), jonli sinov kutilmoqda

- Yangi: `scripts/takes.py` (docs/TAKES.md), pipeline papka berilganda birinchi bosqich (`--no-takes` o'chiradi; papkada
  o'z `clips.json` bo'lsa qo'lda ro'yxat ustun). A rejim `script.txt` bilan (gaplarga Smith-Waterman moslash, 2-nomzod va
  farq), B rejim skriptsiz (gaplar guruhi; tartib: nomdagi raqam -> metadata -> mazmun, oxirgisi taxminiy).
- Mavjud kod qayta ishlatildi: assemble (in/out + yangi `fade`), script_align (norm, align_pairs, subtitr skriptdan),
  transcribe (`hotwords` qo'shildi, faster-whisper 1.2.1 qo'llaydi), face.py modeli, glossary. Yangi kutubxona yo'q.
- Topilgan xato: `script_align.norm` `ʻ` va `ʼ` ni harf deb qoldirardi (isalnum True): `oʻzbek` != `o'zbek`. Tuzatildi.
- Saboqlar (sintetik o'lchovdan): (1) "ee" jarimasi so'z yetishmasligidan kuchsiz bo'lsa to'ldiruvchili dubl tanlanadi -
  `weights.coverage` 60 (1 so'z ~8 ball), filler 8; (2) "qaytadan" faqat darhol oldidagi dublga tegishli (orada <=1 so'z);
  (3) to'xtatilgan urinishlar guruhlashda "ko'prik" bo'lmasin: avval oddiy gaplar, keyin urinishlar biriktiriladi;
  (4) tartib so'zi ("ikkinchii") yumshoq taniladi, aks holda "birinchi set"/"ikkinchi set" dubl bo'lib qo'shiladi.
- Dalil: test_takes 17/17 (aniqlik: skript bilan 99.6/99.3/98.8%, skriptsiz 97.8/97.8/96.3% - gap/dubl/tartib),
  test_studio 17/17, test_agent_setup 13/13, selftest --no-whisper 45/45, sync_skills --check sinxron.
- Taxmin (hali isbotlanmagan): kadr chegaralari (`takes.limits`: blur_var, dark_luma, shake_px) va o'zbek whisper
  ishonchi bilan `speech_min_prob` haqiqiy kliplarda sozlanmagan. Birinchi jonli sinovda report.html ni ko'rib sozla.
- Keyingi agent: papka montajida pipeline chiqargan "Tasdiqqa chiqadigan qarorlar" ro'yxatini BITTA tasdiq xabariga
  qo'sh; foydalanuvchi javobini `temp/<nom>/takes.override.json` ga yoz; qo'lda tahrirlangan clips.json ustidan yozilmaydi.

## 2026-10-08 — Codex — Sprint 1: motion, caption, SFX va dalil vositalari — texnik tekshirilgan

- Baseline kod o'zgarmasdan 31560ed holatida renderlandi: doktor_1 cut.mp4 0..12s,
  `temp/sprint1/before.mp4`, 1080x1920/30. Original job fayllari SHA256 manifest bilan
  tekshiriladi; after shu matn/vaqt/elementlardan olinadi. Draft 304x540/30, full
  1080x1920/30; ikkalasida subtle/stronger mix. A/B, caption/sticker filmstrip va cue
  sheet/waveform shu papkada. Temp dalili gitda yo'q, boshqa laptopga qo'lda ko'chiriladi.
- `motion` davomiylik/easing/stagger/enter-exit/optional blur uchun umumiy manba.
  6 yangi caption entrance va 4 emphasis bor; o‘/g‘/tutuq clusterlari tracking va
  harf animatsiyasida ajralmaydi. motion_choice.json draft/final tanlovini saqlaydi.
  Parallel boshqa unfinished video bor paytda umumiy tarix yozilmaydi; kombinatsiya
  farqlanishi kafolatlanmaydi, yakunda bitta idle agent tarixni yangilaydi.
- Glyph audit: 9 global fontdan Caveat'da U+02BB (`ʻ`) yo'q, qolgan 8 o'tdi. Renderer
  ishlatilgan brend/global fontni ham tekshiradi. Yangi shrift yuklanmadi.
- SFX hero vaqti raw markupdan emas, rendererning haqiqiy word_reveal_time hisobidan
  olinadi. Avtomatik effekt 3 kadr oldin, manfiy vaqt 0ga cheklanadi; zichlik 3/10s va
  gap 1.5s, variant ketma-ket takrorlanmaydi. Nutqni alohida me'yorlash va mavjud
  voice-margin tekshiruvi o'zgarmadi. Cue sheet real stem peak/LUFS, gain, relative
  speech, visual time va leadni yozadi; stem limiterdan oldin, final WAV alohida o'lchanadi.
- 12s dalilda 4 hero SFX: subtle nutqdan 21.4dB past; stronger 10dB past (3.8dB
  qo'shimcha pasaytirish). Yakuniy AAC: ikkalasi -14.1 LUFS, peak -1.4/-1.5 dBTP,
  platforma barcha qatorlari OK. Musiqa yo'q. Audio didi va real-time harakat sifati
  foydalanuvchi tomonidan HALI TANLANMAGAN/TASDIQLANMAGAN.
- Kutubxona 10 kategoriya: 7 tasida 2 sintez variant va per-file license/provenance;
  dedicated hit/typing/impact yo'q (hit/impact eski thud fallback). Haqiqiy yozib olingan
  effektlar barcha kategoriyada hali yo'q. Pixabay rasmiy API hujjatida SFX endpoint
  hujjatlashtirilmagan: foydalanuvchi litsenziyali fayllarni beradi, avtomatik download yo'q.
- Real regressiya: colour_sweep white sprite va accent glow paddinglari turlicha bo'lib,
  selftest broadcasting xatosi berdi. Sprite originlari bo'yicha merge qilindi; unequal
  padding, letter cascade/typewriter regressiya testi qo'shildi. Mavjud checklar zaiflashtirilmadi.
- test_agent_setup bir urinishda Edge exit 0 bilan 10s ichida PNG yaratmadi (12/13).
  Ichki browser sababi aniqlanmagan; takror va yakuniy run 13/13 o'tdi. html_render.py
  hamda uning checki o'zgartirilmadi. Muammo qaytsa browser stderr/profile va PNG
  vaqtini o'lchang; tasdiqlanmagan sababni CPU yukiga bog'lamang.
- Dalil: test_motion 15/15; test_takes 17/17; test_studio 17/17; test_agent_setup 13/13;
  oxirgi selftest --no-whisper 45/45; 5 skill Claude/Codex nusxalari sync --checkda teng,
  Codex frontmatter validatorida valid. Navbat bilan o'tgan studio benchmark tezlik
  taqqoslash uchun ishonchli emas; uni mustaqil CPU benchmark deb taqdim etmang.
- NVENC, faster-whisper CUDA va ONNX auto/CPU fallback qo'shildi; init/inference fallback
  mock bilan tekshirildi. Bu CPU kompyuterda GPU ishi sinovdan o'tkazilmadi, hech narsa
  o'rnatilmadi/yuklanmadi. NEW_LAPTOP.md rasmiy manbalar va tasdiqlanmagan qadamlarni ajratadi;
  ORT latest CUDA13 va CT2 CUDA12 mosligini yangi laptopda alohida tekshirish kerak.
- Keyingi agent: MOTION.md va NEW_LAPTOP.mdni o'qi. Technical A/Bdagi 6.3s sokin kesma
  va CTA yo'qligi baseline mazmunini saqlash uchun izohlangan. Stillsda yuz ochiq;
  yurak stikerining qo'l ustiga tushishi baseline joylashuvi, yangi ijodiy QA tasdig'i emas.
  Userga ikki mixni tinglat, tanlovni HOLATga yoz; tayyor yangi video deb taxmin qilma.

## 2026-10-09 — Codex — Sprint 2 Part 0 — foydalanuvchi tanlovi va texnik tuzatishlar

- User javobi aynan: "Stronger — kuchliroq"; umumiy sfx.profile stronger, feedback va HOLATga yozildi.
- User SFX source/licence saqlamagan ("yoq"). Disk inventarida yangi real fayl topilmadi:
  22 sintez fayli. sfx_library.py manba, licence, SHA256 va davomiylik indeksini yaratadi;
  ma'lum sintez provenance saqlanadi, noma'lum real fayl UNVERIFIED, avtomatik tanlanmaydi.
  Real fayl verified sidecar bilan berilsa birinchi, sintez faqat fallback. Yuklash bo'lmadi.
- SFX priority b-roll/stickerga zichlik ichida joy beradi; hero captionlar barcha joyni
  egallab qo'ymaydi. 10s oynalar va min gap saqlandi.
- Font fallback har belgi bo'yicha: Caveat o/g o'z shriftida, yetishmagan U+02BB Inter'dan,
  bir baseline va fallbackning haqiqiy glyph pikseli test bilan tekshirildi. Motion/phone
  grafik draw yo'llari bir xil fallbackdan foydalanadi. HTML browser CSS fallbacki alohida.
- Edge PNG yo'q/corrupt/timeout bo'lsa bir marta yangi profil bilan bounded retry;
  aniq warning, har attempt UTC vaqt/code/seconds/stderr bilan job JSONL logida. Eski
  no-PNG ichki sabab topildi deb aytilmaydi. Failure hamon aniq xato, checklar susaymadi.
- Dalil: test_part0 5/5, test_motion 15/15, haqiqiy agent setup/HTML 13/13, selftest
  --no-whisper 45/45. Keyingi agent real fayllarning sahifasini taxmin qilmasin.


## 2026-10-09 — Codex: Sprint 2, measured dynamics and native editor package

- Part 0 separate commit 7241191, user chose exactly "Stronger — kuchliroq".
  Source/licence reply "yoq"; disk still has 22 synthesized / 0 real SFX, no invented licence.
- B-roll ranks concrete/action/place/number/abstract and long static spans across short captions.
  Mixed video/photo search + existing credited cutouts + optional assets/library. This machine has
  no assets/library directory. Candidate checks measure 9:16 retained area/native pixels/duration,
  sampled Lab/HSV, text-like Canny contours/corner density. They do NOT identify watermarks/logos.
  Transparent preview background excluded from colour measurement. Short video's final seek is
  kept two frame periods before duration; a real regression test revealed that late seek failure.
- Exact semantics/age/action require visual review. Bad diving helmet, alcohol and generic/ordinary
  bed search results excluded. Oversize 30MB limit and HTTP429 reported, never relabelled usable.
  3-column sheets for oxygen/urine/bed shown together; some columns are the same photo's cutouts.
  User selection is STILL PENDING: no new candidate burned in, no accepted history fabricated.
  broll_history stores actual accepted/rejected reasons; latest asset decision wins, old votes cannot
  outvote a new rejection. Shared sync refuses unfinished videos; per-job history survives.
- Energy: measured word starts/sec, mono RMS dBFS, interval-union pause; structure is explicitly a
  keyword/number heuristic with manual overrides. Style drives zoom/visual punches, caption amplitude,
  automatic element interval, SFX density/gain, continuous backdrop clock. Explicit elements retained;
  original speech cuts/text/word timing unchanged. Longer excerpt starts at 14s, not a fresh hook.
  NumPy spectral-flux onset candidates need no install; not a guaranteed BPM grid.
- Native FCP7 xmeml v5 source cuts/main timeline, editable SRT, per-graphic ProRes 4444 straight alpha,
  post-ducking/pre-limiter speech/SFX/music stems. Base grade/zoom/context effects rasterized; word
  animation is not transferred to editable captions. Stereo stems become six audio channel tracks.
  Actual doktor_1 source is 25fps, sequence 30fps; FFmpeg fps round=near CFR prefix copy in temp,
  original untouched, source seconds + frame-grid rounding documented. No embedded TC => file relative.
  Both native cuts.json dict ranges and pair shorthand tested; unsupported drop-frame/speed rejected.
- Real 12s export passed parsing: 2 XML, 7 captions, 1 alpha graphic, 3 stems; actual alpha encode/decode
  and corrupted-XML detection tests. GUI imports into Resolve/Premiere UNVERIFIED. Official docs and
  SRT/menu uncertainties in docs/EXPORT.md. No new install or GPU execution.
- Studio uncovered direct Pillow use of Font wrapper in cover; fixed via fallback draw with mt anchor,
  test covers missing Caveat glyph and positioning. Checks were not weakened.
- Evidence temp/sprint2: 12s full 1080x1920/30fps + draft and 24s draft, paired mixes, A/B, 12-frame
  filmstrips, energy plots and audio cue sheets. These demonstrate dynamics with OLD approved elements;
  new B-roll waits for selection. Stronger bus margin 14.90dB short / 12.58dB long (rule 10dB).
  Full render checks OK; excerpt preflight notes missing CTA/static span, preserved intentionally.
  Motion/audio taste approval PENDING. Original job SHA256 manifest unchanged.
- Required tests: takes 17/17, studio 17/17 (draft benchmark 3.44x), agent setup 13/13,
  motion 15/15, part0 5/5, sprint2 21/21, isolated selftest --no-whisper 45/45.
  Selftest must run ALONE through completion, not just start while idle: spawning a job mid-test
  made its busy-lock check fail; final isolated rerun passed. Keep that guard/check intact.
- Source skills updated then sync_skills --apply / --check for Claude and Codex.
  Next: user chooses recommended oxygen1/urine3/bed1, auto or none; record verbatim, accept then
  sprint2_demo.py after / reports. Do not fabricate a selection or claim the whole sprint is approved.

## 2026-10-09 — Codex style study, solo finish after Claude limit

- 41 source report folders +5 DNA/playbooks; 1–20 brief reuse,21–41 overview/literal discovery + selected native PTS events. Every animation/exit/microprint is NOT fully measured; coverage.json.
- Independent Claude analysis/merge/diff and two initial proof reviews found and reconciled; historical_* records and reply_by_codex.md. Final committed tests/iteration3 not independently Claude-reviewed.
- New opt-in trajectory, procedural paper/grid/ticket/polaroid/film/pill, pivot/active state, canvas camera, flat relief, one-source layout morph; reused captions/energy/SFX/export. Canvas child behind_person rejected clearly; per-style seam; callable registry; invert flash raster source effect. D promo/showcase/vlog use distinct caption presets, brand last.
- 5 approved doctor excerpts 5.57–8.20s, three iterations each, before/after + stronger/subtle + frame/time/alpha numbers; A full1080x1920/30. Original41 SHA1 and approved doctor source hashes unchanged. Peer video folders/notes untouched.
- Quality gaps: B1 exit briefly covers face; A tag repeats caption and does not recreate the big calculator; B2 row is not shared-pivot fan, duplicate representations of five. Do not label professional equivalence or creative approval. ≤3 iteration cap respected.
- Source count threshold≥3 distinct hashes; source invert candidates2–4frames, source cut detectors remain candidates, not universal cut rate. Onset != beat, RMS != LUFS, reference mixed track != isolated SFX margin. Agent cannot judge sound taste.
- Main selftest refuses preserved unfinished Claude video note; no guard weakened. Run unchanged source copy with isolated temp/notes and --no-whisper --offline; production precondition remains. Final tests in docs/STYLE_STUDY/tests.md.
- 4-core CPU full RGBA canvas/TrackedText is costly; use short scenes; static child/bbox cache still future work. True3D/fold, exact handwriting, video diagonal wipes and exhaustive timing/font identity remain gaps. No install/upload/new library.

## 2026-10-10 — Codex — Claude solo continuation, Part 2

- User explicitly confirmed "Ha, Claude to‘xtagan; hammasini yakunla". Parts1 c395c33 and3 fce6560
  reused, not rebuilt. Source docs/claude_skills remain authoritative; restored .claude/skills and
  .agents/skills synchronized. Old untracked .codex/.claude duplicate preserved, not committed/deleted.
- Semantic graphics_ideas proposals are lexical, not comprehension: agent verifies the full sentence.
  count/object/list/process/comparison suggestions never establish a clinical cause or invented item.
  No-repeat checks visible caption intervals (including partial hidden spans), apostrophe variants,
  simple suffixes and nested canvas text. Masking does not change approved words or original timings.
- Group fan has ONE pivot, active last item, per-item spoken at; stack/spread supported. Signed spread
  accepted, unreachable/reversed item times rejected. Hero uses original/licensed image or MIT icon,
  motion language duration/easing, path/rotation, bounded trail/blur and 2.5D tilt/shadow. True3D deferred.
- YuNet checks every detected face on every active overlay frame, including exits after split/stage;
  missing/no-face remains unverified. Pixel-change>40 proxy can miss low-contrast or undetected faces.
  It caught real caption-face overlap when A captions were moved to y=.49; moving to .59 fixed it.
- Quality gate uses DNA+format plan, actual fitted font size, configured entrance intervals, density,
  calm stretch, face/export/speech/LUFS. Native auto_cut keep/speed becomes output cut boundaries.
  Unknown remains unknown; no-graphic entrance is N/A. Intra-group stagger is not a new scene.
  Strict no_repeat/enforce_final is per-video; legacy approved jobs are not silently redesigned.
- User history now changes compatible style-group ranking as well as format; graphics rank reads
  local+global same-format choices. Actual approvals only; local history deferred during parallel work.
  Skills explicitly prioritize selected format over old universal lockup/yellow/follow/every3s recipe.
- New test_quality 20/20 covers these regressions. Existing 12 suites total 168/168 (transcribe --no-whisper).
  Sandbox parallel suite initially failed with WinError5 on atomic rename in sandbox Temp; unchanged
  tests passed outside sandbox. No test assertion or lock timeout weakened. Final isolated selftest
  result is recorded separately in STYLE_STUDY/tests.md; production Doctor1/3 notes remain open.
- Earlier memory line "final committed version not Claude-reviewed" was stale: original review in
  temp/style_study/build_review.md includes acceptance/tests of 925672a/1926d6e. Tracked verbatim as
  STYLE_STUDY/build_review_claude_committed.md; newest solo changes have no independent Claude review.

## 2026-10-10 — Codex — proof checkpoint and next real video

- Part2 saved as 508fa16. Final 12 suites168/168; latest isolated selftest43/43, exact final script hashes
  rechecked. Offline/--no-whisper scope and preserved production note guard in STYLE_STUDY/tests.md.
- 14 own approved-content short review exports, stronger/subtle, actual-PTS reference-vs-new sheets,
  same-clip A/B, cue sheets/waveforms in temp/style_study/finish/gallery.html. Original sample media
  used in analysis JPEGs only; no export copies logos/footage/audio/font. Old proofs retained.
- A now an original lung hero (0.36s,54% configured width); B2 ONE pivot fan with count icons, no
  fake medicine names. A/C/D technical gates pass; B1/B2 still fail source cut cadence. No target
  changed to inflate score. C unnecessary photo removed. No matching claim for absent raw formats.
- Manual limitations recorded: B2 fan low in platform UI area, D calendar decorative numeral should
  be calendar-blank on real edit. These are review demonstrations, not approved platform finals.
  Technical score does not establish every design/semantic issue or sound/motion taste.
- Sample42 bracket cannot be transferred to a doctor count as invented medical winners. A/B2
  sixth saved iteration cap respected; no new footage/list/dialog/role fabricated to fix a failed gate.
- Doctor4 AND5 already have final exports/completed notes, so "whichever lacks final" has no eligible
  job. Doctor1/3 notes remain open. User now asks to save promptly and trial a NEW video from scratch.
  Read new input path/job and use normal ONE approval message before burn-in; keep creative/raw-format
  trial and user sound judgment outstanding. Reuse cache and selected format/family docs to save tokens.

## 2026-10-11 — Claude — motion wishlist: lint, sub-pixel, kesish, scrim, blur, shablonlar
- Yangi switchlar `style.motion` da default o'chiq (subpixel, cuts, scrim, motion_blur, preset, durations_frames); per-video doktor 1-5 kadr farqi 0. style/style.json (yangi videolar) subpixel+cuts+scrim yoqildi: A/B gate 66.7→76.9, drift jitter 1.33→0.12 px.
- `review_tools.py lint/slowmo`: blit trace'dan bayroqlar va curve PNG. Edge-anchored wipe markazi harakat emas; 1 px zinapoya `pixel_steps`, short emas. Cue onset kesishda, so'z reveal emas.
- Motion blur render narxi 12 s qismda shovqindan kichik; default o'chiq (punchy preset yoqadi). Emphasis extra (pop_overshoot/colour_flash/shake) faqat aniq tanlanganda: variety fingerprint o'zgarmaydi.
- Yangi elementlar: calendar, panel, logo_sting, mask_reveal, image `push`. pil_sprite origin = markaz (calendar xatosi shundan edi).
