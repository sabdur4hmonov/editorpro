# Restoran / mahsulot promo retsepti (namuna 20)

Manba: `samples/sample 20.MP4` (46 s, 1440x2560, 60 fps HEVC). 2026-10-08 da kadrma-kadr o'lchangan
(`temp/sample20_study/`), tizimda `temp/promo_test/` da sinab ko'rilgan va namuna bilan solishtirilgan
(`studio.py compare`). O'lchamlar 1080x1920 kadrga keltirilgan.

## 1. Kadrlar tartibi (namuna 20)

| Vaqt | Kadr | Ovoz | Ekranda |
|---|---|---|---|
| 0-1.4 | oshpaz kameraga | oshpaz | kichik so'zlar yuzning chap va o'ng tomonida birin-ketin ("juda / ham", "ko'pchilik / bizdan") |
| 1.4-3.4 | oshpaz | oshpaz | katta kursiv sariq porlovchi ibora "5 kishilik", ostida kichik "set ...... so'rashdi" (ikki chetga) |
| 3.6-5.4 | oshpaz + stol | oshpaz | oq kursiv "4 ta set" oshpaz **orqasida** (qalpoq oldida), ostida "tayyorlab ... qo'ydik" |
| 5.5-15 | taomlar makro, sekin kamera | musiqa | tepada shisha yorliq: kesilgan taom rasmi + "1-set" + nom; har taomda almashadi, sakrab chiqadi |
| 15-34 | taomlar makro | ovoz (VO) | kichik qalin oq subtitr, pastroq (y ~0.70), so'zlar aytilganda chiqadi |
| 35-38.5 | oshpaz | oshpaz | kichik qator "5 kishilik setlarimiz narxi", keyin katta sariq "990,000", o'ngda "so'm" |
| 39-44 | qadoqlash | musiqa | matnsiz |
| 44.6-46 | oshpaz qutini ushlab | oshpaz | qo'lyozma so'zlar yuzning ikki yonida ("Go'sht ta'midan / zavqlaning") |

Kesishlar: 31 ta, taom kadrlari 1-2 s. Rang: iliq, kontrastli (`look.preset: warm` yoki `punchy`).
Musiqa va effekt: namunada fon musiqa bor; tanlovni foydalanuvchi tinglab qiladi (agent eshitmaydi).

## 2. Namuna -> tizim

| Namunadagi narsa | Tizimda | Eslatma |
|---|---|---|
| Ko'p klip (oshpaz, taomlar, qadoqlash) | `pipeline.py <papka yoki clips.json>` -> `assemble.py` | product kadrlari jimlik deb kesilmaydi |
| Yuz yonidagi so'zlar | `aside` elementi | joyi yuzdan hisoblanadi, kadr ichida qisiladi |
| "5 kishilik" katta kursiv sariq | `{promo}**5 kishilik** set so'rashdi` | kichik so'zlar ikki chetga (`sub_justify`) |
| "4 ta set" odam orqasida | `title` + `preset: promo` + `behind_person: true` | broll/stage/scene/grade bilan bir videoda emas |
| Taom yorlig'i | `label` elementi (`items` har taom uchun) | rasm: `cutout.py` bilan kesilgan PNG |
| Ovoz ostidagi subtitr | `{vo}...` bo'lak belgisi | preset `vo`: 44 px qalin, y 0.70 |
| Narx | `{promo}5 kishilik setlarimiz narxi !!990,000!! so'm` | uch qator o'zi bo'linadi, "so'm" o'ngga; sanab chiqish yo'q (namunada ham yo'q) |
| Qo'lyozma so'zlar | `aside` + `font: "Caveat"`, `size: 0.9`, `dy: -0.04` | |
| 60 fps HEVC 1440x2560 | assemble/pipeline o'zi 30 fps 1080x1920 ga keltiradi | |

## 3. Ish tartibi

1. Kliplar `input/<promo nomi>/` papkasiga, nom bo'yicha tartibda: `01_oshpaz.mp4`, `02_qovurga.mp4` ...
   Alohida yozilgan ovoz bo'lsa `ovoz.m4a`.
2. Birinchi ishga tushirish shablon yaratadi: `temp/<nom>/clips.json` (ovozli klip speech, ovozsiz product,
   audio fayl voiceover). Tartib, rol, `in`/`out` va voiceover `cover` larini to'g'rilang.
   Format va rollar: `scripts/assemble.py` boshidagi izoh.
3. `.venv\Scripts\python.exe scripts\pipeline.py input\<promo> --style temp\<nom>\style.json`
   (per-video uslub: `look.preset: warm`, kerak bo'lsa `zoom.enabled: false`, o'zbek nutqi uchun uz model).
4. Matn: oshpaz gaplari odatdagidek tuzatiladi; VO bo'laklari boshiga `{vo}`, asosiy iboralar `{promo}`.
   Yuz yonida chiqadigan so'zlar subtitrdan olinadi (`corrections.json` da `"text": ""`) va `aside` ga yoziladi.
5. `elements.json`: `aside` (boshi va oxiri), `title` behind_person ("4 ta set"), `label` (taomlar, vaqtlari
   `segments.json` dagi product bo'laklari boshidan), kerak bo'lsa `sfx`.
6. `--stills` bilan tekshirish, foydalanuvchi tasdig'i, draft, final.

## 4. Elementlar namunasi

```json
{"elements": [
  {"type": "aside", "start": 0.3, "end": 1.4, "stagger": 0.3,
   "items": [{"at": 0.3, "text": "juda\nham", "side": "left"}, {"at": 0.6, "text": "ko'pchilik\nbizdan", "side": "right"}]},
  {"type": "title", "start": 3.4, "end": 5.45, "text": "*4 ta set* tayyorlab qo'ydik", "preset": "promo",
   "y": 0.34, "size": 1.15, "behind_person": true},
  {"type": "label", "start": 5.48, "end": 8.93, "y": 0.2, "items": [
    {"at": 5.48, "kicker": "1-set", "name": "Mol qovurg'asi", "image": "temp/<nom>/images/qovurga.cut.png"},
    {"at": 6.57, "kicker": "2-set", "name": "Qo'yning qo'li", "image": "temp/<nom>/images/qol.cut.png"}]},
  {"type": "aside", "start": 19.5, "end": 21.4, "font": "Caveat", "size": 0.9, "dy": -0.04, "stagger": 0.35,
   "items": [{"at": 19.5, "text": "Go'sht\nta'midan", "side": "left"}, {"at": 20.4, "text": "zavq-\nlaning", "side": "right"}]}
]}
```

`label`: `x`, `y` (panel markazi), `width` (0.5), `size`, `image_size` (0.085), `color`, `kicker_color`, `glass`.
`aside`: `spread` (yuzdan masofa, 0.27), `dy` (0), `size` (0.75), `font`, `color`, `stagger`, `margin` (0.05);
item: `at`, `text`, `side`, `end`, `dy`, `size`, `stagger`.
Taom yorlig'i rasmi: mijoz kadridan kesilgan taom (`frames.py --at` bilan kadr, `cutout.py` bilan fonsiz PNG).

## 5. O'lchangan tezlik (bu kompyuter, CPU)

- 60 fps HEVC 1440x2560 kliplarni yig'ish (`assemble.py`): ~34 s har 10 s video uchun.
- To'liq render (1080x1920, crf 17, slow, behind_person bilan): ~63 s har 10 s.
- Bitta HEVC faylni yig'ishsiz to'g'ridan-to'g'ri: ~82 s har 10 s (dekodlash + kesish + render).
- 46 s promo uchun taxminan: yig'ish ~2.5 daqiqa + render ~5 daqiqa.

## 6. Halol chegaralar

- "5 kishilik" ning qiyshiq holda kirishi va o'ngga surilib chiqishi aynan takrorlanmagan: `pop` kirish va `fade` chiqish.
- Narx raqami sanab chiqmaydi (namunada ham birdaniga chiqadi); kerak bo'lsa `stat` elementi bor, lekin u kursiv emas.
- Kamera harakati (makro, sekin surilish) kadrning o'zida bo'lishi kerak: tizim faqat sekin zoom qo'shadi.
- Musiqa faqat mijoz bergan fayldan.
