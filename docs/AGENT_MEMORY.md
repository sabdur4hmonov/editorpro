# Claude va Codex uchun umumiy tajriba

Har sessiya boshida o'qiladi. Bu jurnal Gitda saqlanadi; HOLAT.md esa hozirgi ish va
foydalanuvchi tasdiqlarini saqlaydi. Bir agent yozgan tajribani keyingisi ham qo'llaydi.

Har montajdan va texnik o'zgarishdan keyin pastga yoz:

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
