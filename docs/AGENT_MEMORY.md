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
