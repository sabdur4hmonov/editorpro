# Namuna uslubi: `samples/` dagi videolar qanday qilingan va tizimda qanday takrorlanadi

Yangi 42-sonli namuna va 8 format: `docs/STYLE_STUDY/videos/s42/`, `docs/FORMATS.md`.
Eski 14 misol quyida saqlanadi, lekin endi hamma videoga bir xil retsept qo‘yilmaydi.
Format + family tanlovi, ma’noli fan/hero obyektlari, barcha kadrda yuz tekshiruvi va pro-quality gate:
`docs/QUALITY.md`, `docs/MOTION_DESIGN.md`. Stronger default, subtle ikkinchi; foydalanuvchi ko‘rigi alohida.

Bu fayl 14 ta namuna videoni kadrma-kadr o'rganish natijasi. Maqsad: tizim chiqargan video
namunalardagi bilan bir xil ko'rinsin. O'lchamlar namunalardan o'lchab olingan va tizim chizgan
yozuv namuna yozuvining yoniga qo'yib solishtirilgan (namuna 7, 8, 10, 11, 13, 14).

Agent uchun buyruq: `/namuna` (`docs/claude_skills/namuna/SKILL.md`).

## 1. Namunalarda nima takrorlanadi

| Narsa | Namunada | Tizimda |
|---|---|---|
| Shrift | Zich grotesk, kichik harf, harflar deyarli tegib turadi | Inter, `tracking -0.06` |
| Ikki pog'ona | Asosiy ibora katta, qolgani ostida kichik; kichik qator asosiy qator **kengligiga teng** | `*ibora*` + `fit_sub` |
| So'z chiqishi | Har so'z xiralikdan ochiladi va **o'ngroqdan sirg'alib** joyiga keladi | `animation: blur`, `slide_in` |
| Blok harakati | Butun yozuv sekin kattalashadi, tugagach xiralashib yo'qoladi, keyingisi ustidan chiqadi | `drift`, `exit: blur` |
| Urg'u rangi | Sariq, porlaydi; oldida yulduzcha: `*3 oyda` | `**ibora**`, `\*` |
| Juda katta raqam | `*3 oy` ekranning yarmi, ostida rangli qutidagi izoh | `!!\*3 oy!! ==kerak bo'ladi==` |
| Marker | So'z avval sariq, keyin ustidan quti chapdan o'ngga surtiladi | `==so'z==`, `~~so'z~~` |
| Sarlavha | Tor KATTA harflar tepadan tushadi, sariq porlaydi | `{caps}` |
| Qalin so'z | Juda qalin so'z harfma-harf sakrab chiqadi, tepasida rangli yorliq | `{heavy}` |
| Bitta so'z | Bir-ikki so'zdan, tez almashadi | `{single}` |
| Atoqli ot | `Rus`, `Instagram`, `SMM` bosh harfda qoladi, gap boshi kichik | `case: smart` |
| Joyi | Kadrning o'rtasi, ko'krak atrofida | `position_y 0.56` |

## 2. Subtitr uslublari (`captions.preset` yoki bo'lak boshida `{uslub}`)

| Uslub | Qaysi namuna | Qachon ishlatiladi |
|---|---|---|
| `clean` | 2, 7, 8, 10, 11 | **Asosiy.** Deyarli hamma gap shu uslubda |
| `caps` | 5, 10 | Boshidagi ilmoq sarlavhasi, bo'lim sarlavhasi (tepada, `y=0.2`) |
| `heavy` | 14 | Bitta kuchli so'z, energiyali video. Chapga tekislangan |
| `italic` | 6 | Hissiyotli, yengil gap; qiya sariq sarlavha |
| `serif` | 3, 12 | Ism, tanishtirish, nafis mavzu (soat, zargarlik) |
| `single` | 12 | Tez gapirilgan joy, b-roll ustida |
| `marker` | 13 | Intervyu, uzun gap; kichik, chapda, bir necha qator |
| `karaoke` | 4, 10 | Ovozli xabar sahnasi ostida (Har So'z Bosh Harfda) |
| `glow`, `box` | | Eski uslublar: KATTA harf porlash; so'z rangli qutida |
| `promo` | 20 | Katta kursiv porlovchi ibora va narx, kichik so'zlar ikki chetga (restoran promo, `docs/PROMO.md`) |
| `vo` | 20 | Ovoz ostidagi (voice-over) kichik qalin oq subtitr, y 0.70 |

Bitta videoda uslublar aralashadi (namunalarda ham shunday): asosiy uslub `style.json`/`brand.json`
da, alohida bo'lak uchun matn boshiga belgi qo'yiladi:

```
{caps,y=0.2}**KELINGLAR** hozir sizlarga
**\*3 oyda Rus tilini** o'rgana olaman deb o'ylaysizmi?
{heavy,x=0.07,y=0.3}==Kamerani== *sekin* yaqinlashtirsangiz
{clean,anim_main=flicker,anim_sub=bar}*10 yil* orqaga qaytganingizda
```

Belgi ichida bo'sh joy bo'lmaydi. Sozlamalar: `y`, `x` (0..1), `size` (ko'paytma), `align`,
`anim`, `anim_main`, `anim_sub`, `exit`, `case`, `reveal`, `color`, `accent`.

## 3. Matn belgilari

| Belgi | Natija |
|---|---|
| `*so'z*` | katta (oq) |
| `**so'z**` | katta va sariq (porlaydi) |
| `!!so'z!!` | juda katta va sariq |
| `_so'z_` | faqat sariq, o'lchami o'zgarmaydi |
| `==so'z==` | marker: urg'u rangidagi quti surtiladi |
| `~~so'z~~` | ikkinchi marker (qizil quti, oq yozuv) |
| `\*` | oddiy yulduzcha: `**\*3 oyda**` → `*3 oyda` |

**Blok qoidasi.** Qisqa gapda (9 so'zgacha, 56 belgigacha) urg'uli ibora bo'lsa gap bo'linmaydi:
bitta bo'lakda asosiy ibora katta, qolgani ostida kichik chiqadi. Urg'u qo'yilmagan gap odatdagidek
3-4 so'zdan bo'linadi. Shuning uchun **har gapda bitta asosiy ibora belgilash** namuna ko'rinishini
beradi. O'chirish: `captions.lockup_chars: 0`.

## 4. Animatsiyalar (`animation`, `anim_main`, `anim_sub`)

| Nomi | Harakat | Namuna |
|---|---|---|
| `blur` | xiralikdan ochiladi | hammasida |
| `fade` | shunchaki ochiladi | 4, 12 |
| `pop` | prujina bilan kattalashadi | |
| `rise` | pastroqdan chiqib o'tiradi | 6, 12 (kichik so'zlar) |
| `flicker` | ikki marta miltillab yonadi | 7 ("10 yil") |
| `bar` | avval oq to'rtburchak, keyin so'z | 7 (kichik so'zlar) |
| `letters` | harflar birin-ketin sakraydi (`letter_from`: below/above) | 5, 14 |
| `ltrack` | harflar keng chiqib zichlashadi | 6 |

Blok sozlamalari: `slide_in` (so'z o'ngdan sirg'alishi, em), `intro_scale`, `drift` (sekin o'sish),
`exit` (`blur`, `fade`, `drop`, `none`), `fit_sub` (kichik qatorni asosiy kenglikka moslash).

## 5. Elementlar (namunalardagi qaytariladigan grafikalar)

| Namunada | Element | Eslatma |
|---|---|---|
| Obuna kartochkasi: doira, @manzil, tugma bosiladi (9, 12, 14) | `follow` | `handle` (ixtiyoriy), `logo`, `name` yoki `icon` (brendsiz: `icon`, handle'siz), `button`, `done`, `tap` |
| To'liq ekranli rangli sahna, katak fon (4, 8, 9, 11) | `scene` | ustiga `voice`, `text`, `image`, `stat` qo'yiladi |
| Ovozli xabar pleyeri (4, 8, 10, 13) | `voice` | `scene` ichida yoki video ustida |
| Oq-qora kadr (13 boshi, 14) | `grade` `mode: bw` | ilmoq yoki "to'xtab qolgan" joy |
| Sahna almashganda chaqnash (3) | `flash` | `at` |
| Raqamli ro'yxat va rasmchalar (2, 5) | `list` | `items[{at, text, image}]` |
| To'g'ri / xato shisha kartochkalar (6) | `choice` `style: glass` | |
| Katta raqam va halqa (1, 11) | `stat` | |
| Ism plashkasi, burchak yozuvi (3) | `lower_third`, `text` | |
| Kino lavhasi ustida yozuv (7, 12) | `broll` + subtitr | lavhani faqat foydalanuvchi beradi |
| Mahsulot, logotip rasmlari (2, 3) | `image` | mijoz fayllari |
| Qo'lyozma izoh va strelka (12, 14) | `handnote`, `arrow` | Caveat matn, chizilib chiqadigan egri yo'l |
| Telefon/profil (3) | `phone`, `profile` | faqat mijoz bergan rasm yoki name/handle/bio/avatar |
| Sarlavha odam orqasida (5, 7, 10) | `text/title` + `behind_person: true` | PPHumanSeg; soch chetlarini kadrda tekshir |

## 5a. To'liq ekranli b-roll (namuna 15, 16) — 2026-10-07 o'lchangan

Kesish vaqtlari PySceneDetect bilan aniqlangan (`ContentDetector(threshold=27)`), har bo'lak o'rtasidagi kadr
ko'rib chiqilgan (`frames.py --at`).

| Namuna | B-roll oraliqlari (s) | Ko'rinishi |
|---|---|---|
| 15 | 5.11–6.01, 6.01–6.77, 9.68–11.18, 13.38–14.38, 14.38–15.38, 17.98–19.65, 19.65–20.85 | **oq-qora**, qoraytirilgan, 0.8–1.7 s, ketma-ket ikki klip ham bo'ladi |
| 15 | 26.99–27.89, 27.89–28.83, 29.43–32.0 | **rangli** (hammasi oq-qora emas) |
| 16 | 14.28–16.64, 16.64–18.36 | rangli, iliq, odam orqadan / yelka ustidan (yuz markazda emas) |

- Gapiruvchining ovozi b-roll ostida davom etadi, klipning o'z ovozi yo'q. Kirish va chiqish **keskin kesish**.
- Subtitr b-roll ustida qoladi. Namuna 15 da b-roll ustidagi subtitr boshqa uslubda (tor KATTA harf + kichik
  izoh), gapiruvchi kadrida oddiy kichik harfli. Foydalanuvchi so'rasa bir xil uslub qoldiriladi.
- Namuna 16 dagi shakl bilan o'tish (to'q sariq "uy" shakli kadrni supuradi, 7.95–8.15) faqat telefon maketi
  sahnasiga kirishda; b-roll'lar keskin kesish bilan.
- Namuna 16 da 7.5–13.1 telefon maketi sahnasi (fon naqshli, ichida xiralashtirilgan video).

Tizimda: `{"type": "broll", "mode": "full", "file": "...mp4", "offset": 0.5, "focus_x": 0.5, "bw": true, "dim": 0.3}`.
`bw` oq-qora, `dim` qoraytirish (oq kiyim/och fon ustida 0.4–0.45, aks holda oq subtitr o'qilmaydi), `focus_x`
gorizontal klipning qaysi qismi 9:16 ga qoladi. `grade` elementi b-roll'ga ta'sir qilmaydi (u avval chiziladi).
Kamera suriladigan klipda `offset` ni kompozitsiya yaxshi joyga qo'y va oxirgi kadrni ham tekshir.
B-roll ichiga tushgan stiker-rasmlarni olib tashla. Bola klipida yuz markazda bo'lmasin (orqadan, qo'llar).

## 6. Namunadagi video tuzilishi (shunday rejala)

1. **0-2 s, ilmoq.** Katta sarlavha (`{caps}` yoki `{heavy}`) + bitta harakat (zoom, `grade bw`).
2. **Asosiy qism.** Har gapda bitta urg'u (`clean`). Har 3-4 soniyada bitta element: ro'yxat, rasm,
   raqam. Sanab o'tilsa `list`, taqqoslansa `choice`, raqam aytilsa `!!raqam!!` yoki `stat`.
3. **Dalil.** Mijoz ovozi bo'lsa `scene` + `voice` + `{karaoke}` (namuna 4, 8, 10).
4. **Oxiri.** `follow` kartochkasi (2.5-3.5 s), tugma bosiladi.

## 7. Hozircha avtomatik emas (halol ro'yxat)

`docs/STUDIO.md` da namuna taqqoslash, draft, preflight va yangi elementlar tartibi bor.

- **Yozuv odam orqasida** PPHumanSeg bilan ishlaydi, ammo 192x192 model soch/qo'l chetlarini
  mukammal ajratmaydi. Har kerakli sahna kadrlarini tekshiring; yoqmasa oddiy oldingi sarlavha ishlating.
- **Maxsus chizilgan sahnalar** (9: tarvuz, pazl, miya; 5: kalkulyator; 3: logotipli daraxt sxema).
  Bular har video uchun qo'lda chizilgan. Tizimda o'rniga `scene` + HTML grafika (`html_render.py`)
  + mijoz rasmlari ishlatiladi: o'xshash chiqadi, lekin aynan o'sha emas.
- **Qo'lyozma** Caveat shriftida, **strelka** chizilib chiqadi; haqiqiy qalam harakati, 3D harflar (1),
  odam atrofidagi kontur (14) uchun alohida mijoz animatsiyasi/qo'lda grafika kerak.
- **Kino lavhalari, musiqa, logotip**: faqat foydalanuvchi bergan fayldan.
- **Ovoz**: agent eshitmaydi. Effekt va musiqa ikki variantda render qilinib, foydalanuvchi tanlaydi.

## 8. Sprint 1 — umumiy motion va o'lchanadigan ovoz

`docs/MOTION.md` — ikkala agent uchun retsept. Yangi `motion` bo'limi davomiylik, easing,
stagger va enter/exit juftlarini caption/title/sticker/label/follow/b-rollga beradi; brend
`style.motion`, video `motion_override` bilan boshqaradi. Olti yangi word entrance va to'rtta
urg'u eski presetlarni to'ldiradi; `motion_choice.json` qayta renderda tanlovni saqlaydi.
o‘/g‘/tutuq belgisi harf animatsiyasida ajralmaydi; glyph audit missing belgiga ogohlantiradi.

Namuna kirish tezligini taxminiy "smooth" deb baholama: `review_tools.py filmstrip`da 12
yaqin timecoded kadrni ko'r, o'zgarishda `ab` bir xil soniyalarda oldin/keyin ko'rsatsin.
Caption o'qilishi, overshootning safe zone/yuzga kirishi, exitning keyingi cuega o'tishi tekshiriladi.
Haqiqiy harakat didini foydalanuvchi draftda baholaydi.

SFX eventdan 2–3 kadr oldin, takrorlanmagan variant va 10s zichlik limiti bilan keladi.
Compose subtle/stronger audio va cue sheet + markerli waveform chiqaradi; nutq margin qoidasi
saqlanadi. Ikkalasini chatda tinglat, javobni video HOLAT.mdga yoz. Pixar/kinodan ovoz ko'chirma;
faqat mahalliy litsenziyali SFX. Hozir kutubxona sintez, haqiqiy yozuvlar hali kerak.
Parallel umumiy motion tarixi/learningni bitta idle agent yakunda yozadi.

Sprint 2: `docs/BROLL_DYNAMICS.md` bo'yicha b-roll nomzodlari va nutq energiyasi.
Har momentga 3 ustunli sheet; hammasini bitta xabarda ko'rsat, user raqam/auto tanlasin.
Exact match, rang, 2.5–4s, pastki gradient; kuchsiz nomzoddan ko'ra hech narsa yaxshi.
Bir suratning cutout nusxalari alohida source emasligini ayt. Auto oldidan agent ko'rish tekshiruvi,
matn va tanlov tasdiqlari o'z HOLAT.mdda. Rejected sababini broll_history saqlaydi, parallel sync yo'q.
`dynamics` sokin joyni sokin, peakni kuchli qiladi; nutqni qayta kesmaydi. Energy image, filmstrip,
A/B va ikkala audio mixni chatda ko'rsat. Stronger umumiy default, har yangi videoda tinglash alohida.
Glyph yetishmasa `font_fallback.py` o'sha belgini mavjud shriftga almashtiradi; so'z va apostrof ajralmaydi.
Qo'lda davom ettirish uchun editor eksporti: `docs/EXPORT.md`, GUI tasdiqlanmagan chegaralarni ayt.

## 41 namuna: yangi guruh DNA

`docs/STYLE_STUDY/README.md` va `docs/style_dna/` beshta family. `/namuna` va `$namuna` content/footage bo‘yicha eng yaqinini tanlaydi, per-video stylega apply qiladi va ONE approvalda guruh/sababni aytadi. Brend rang/shrift va user feedback ustun. Har3s qoidasi ijodiy qo‘llanma: intervyuning sokin gapini majburan effekt bilan bo‘lmang. Texnikalar `docs/MOTION_DESIGN.md`; tekshirilmagan easing/3D/ovoz yashirilmaydi.
