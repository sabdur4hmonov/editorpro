# Montajor qo'llanmasi (agent uchun)

Bu fayl "qanday tugmani bosish" haqida emas (u `AGENTS.md` da), balki **yaxshi montajor qanday
o'ylashi** haqida. Har bir videoda shu tartib bo'yicha ishla. Foydalanuvchi faqat xom video va
brend nomini beradi; qolgan qarorlar senda.

## 0. Nima berilgan

| Narsa | Qayerda | Bo'lmasa |
|---|---|---|
| Xom video | `input/` yoki to'liq yo'l | so'ra |
| Brend | `brands/<nom>/` | yangi brend och (`AGENTS.md`: "Yangi mijoz") yoki umumiy uslub |
| Skript (nima deyilgani) | `input/<video nomi>.txt` yoki `--script` | whisper matni + foydalanuvchi tekshiruvi |
| Mijoz rasmlari, mahsulot surati | `brands/<nom>/assets/` | 4-bo'limdagi zinapoya |
| Namuna videolar | `samples/<brend>/` | brend uslubi `brand.json` da |
| Foydalanuvchi fikrlari | `style/notes.md`, `brands/<nom>/notes.md` | pipeline boshida chiqadi: **o'qi va amal qil** |
| Lug'at | `style/glossary.json`, `brands/<nom>/glossary.json` | avtomatik qo'llanadi |

Brend aytilmagan bo'lsa bu **brendsiz video**: `--brand` yozilmaydi, umumiy uslub ishlatiladi,
logotip va oxirgi kadr qo'yilmaydi. Brend haqida hech narsa o'ylab topma.

Avval video turini aniqla (xom videodan 8-12 kadr olib qara: `frames.py`):

| Tur | Belgilari | Nima qilinadi |
|---|---|---|
| Gapiruvchi odam (xom) | bitta odam kameraga gapiradi | to'liq montaj: kesish, zoom, subtitr, elementlar, effektlar |
| Sahna, intervyu, konsert | bir necha odam, tomoshabin, kulgu, musiqa | `--no-cut`, zoom o'chiq, subtitr; effekt kam yoki yo'q |
| Tayyor Reels (ichida yozuv, stiker bor) | kadrga yozuv va belgilar allaqachon yozilgan | bor narsani o'chirib bo'lmaydi; faqat ustiga qo'shiladi, joyini kadrga qarab tanla. Xom manbani so'ra |

Skript bo'lsa ish ancha aniq chiqadi: matn xatosiz, va sen videoda nima deyilganini bilasan
(ovozni eshita olmaysan). Skript ichidagi `[rasm: ...]`, `[stat: 85%]` kabi eslatmalar
foydalanuvchining to'g'ridan-to'g'ri ko'rsatmasi: vaqti `temp/<nom>/script.notes.json` da.

## 1. Avval tushun, keyin kes

Birinchi `pipeline.py` ishga tushgach (`need_approval`), hech narsa qo'ymasdan oldin matnni o'qi va
o'zing uchun **reja jadvali** tuz (`temp/<nom>/plan.md` ga yoz):

| Vaqt | Aytilgan gap | Vazifasi | Ekranda nima bo'ladi |
|---|---|---|---|
| 0.0–1.8 | "3 oyda ingliz tili..." | ilmoq (hook) | sarlavha + zoom |
| 1.8–6.0 | "birinchidan..." | 1-fikr | ro'yxat 1-qator + belgi |
| ... | | | |
| oxiri | "yoziling" | chaqiriq | oxirgi kadr |

Vazifalar: **ilmoq** (birinchi 2 soniya), **va'da** (nima o'rganadi), **fikrlar** (har biri alohida),
**dalil** (raqam, natija, misol), **chaqiriq** (bitta harakat). Videoda ilmoq yo'q bo'lsa
(salomlashishdan boshlansa), eng kuchli gapni topib foydalanuvchiga boshiga ko'chirishni taklif qil
(`--remove`/`--trim` bilan) yoki sarlavha bilan ilmoq yasa.

## 2. Nima aytilsa, nima ko'rsatiladi

| Gapda nima bor | Element | Eslatma |
|---|---|---|
| Raqam, foiz, narx, muddat | `stat` yoki subtitrda `!!85%!!` | bir vaqtda bitta katta raqam |
| Sanab o'tish (birinchi, ikkinchi...) | `list` | har qator o'z gapi boshlanganda chiqadi |
| To'g'ri/noto'g'ri, afsona/haqiqat | `choice` | |
| Ism, lavozim, mutaxassis | `lower_third` | birinchi marta ko'ringanda |
| Mavhum tushuncha (o'sish, vaqt, pul, g'oya) | `icon` (+ `text`) | `icons.py find` bilan top |
| Aniq narsa, joy, mahsulot | `image` (kartochka) yoki `broll` (to'liq ekran) | 4-bo'lim |
| Jadval, grafik, ilova ekrani, sxema | HTML chizib `image` | `html_render.py` |
| Hissiyot, hazil | `emoji` yoki subtitrda emoji | kam ishlat |
| Muhim ibora | `callout` yoki subtitr belgisi | ikkalasi birga emas |
| Mavzu almashishi | `zoom` + `sfx` (whoosh) | |
| Chaqiriq (obuna, yozilish) | brend `endcard`, `icon` (instagram-logo) + `text` | |

Har bir elementdan oldin o'zingdan so'ra: **bu tomoshabinga tushunishga yordam beradimi yoki
shunchaki joy to'ldiryaptimi?** Yordam bermasa qo'yma.

## 3. Ritm va zichlik

- Har 2–4 soniyada ko'zga yangi narsa: kesish, zoom, element yoki subtitr urg'usi. Lekin har 10
  soniyada kamida bitta "toza" joy qolsin (faqat odam va subtitr).
- Bir kadrda bitta asosiy narsa. Katta element turganda subtitr urg'usini o'chir (belgisiz qoldir).
- Yuzni yopma. Elementlar tepada (y 0.12–0.38), subtitr pastroqda (`captions.position_y`).
- `broll` to'liq ekran bo'lsa 1.2–3 soniya; undan uzun bo'lsa odam yo'qolib qoladi.
- Rasm kartochkasi (`image`) uchun: `width` 0.4–0.62, `radius` 24–40, kerak bo'lsa `border` 0.012
  va `rotate` ±3..6 (qo'lda qo'yilgandek ko'rinadi). Ketma-ket ikki rasm bir xil joyda turmasin.
- Brend rangi (accent) bir vaqtda bitta joyda. Shrift faqat brendniki.
- Ovoz effekti (`sfx`) element chiqqan kadrda: `pop` (kichik), `whoosh` (katta/b-roll), `ding`
  (to'g'ri javob, natija), `tick` (ro'yxat). Har elementga emas: 10 soniyada 2–3 ta.
- **Asl ovoz birinchi.** Effekt va musiqa nutqqa halaqit bermasligi kerak: tizim buni o'zi ta'minlaydi
  (nutq paytida pasaytiradi va o'lchaydi), sen esa effektni iloji boricha so'zlar orasidagi pauzaga
  yoki gap boshiga qo'y. Render oxiridagi `Nutq ustunligi` qatorini tekshir.

## 4. Rasm topish zinapoyasi

Rasm kerak bo'lsa yuqoridan pastga yur, birinchi mos kelganida to'xta:

1. **Mijozniki** — `brands/<nom>/assets/`, foydalanuvchi bergan fayllar. Mahsulot, ofis, jamoa,
   natija skrinshotlari doim haqiqiy bo'lishi kerak: ularni stok yoki AI bilan almashtirma, so'ra.
2. **Belgi** — `python scripts/icons.py find SO'Z` → `icon` elementi. Tez, toza, brend rangida.
3. **O'zing chiz** — HTML/CSS/SVG yoz (`temp/<nom>/gfx/*.html`, namuna: `assets/html/shablon.html`),
   `html_render.py` bilan PNG qil. Grafik, jadval, telefon ekrani, chat oynasi, sxema, taqqoslash
   kartochkasi, narx yorlig'i — bularning hammasi shu yo'l bilan. Brend rangi `var(--accent)`.
4. **Stok** — `images.py search "inglizcha so'z" --video ...` → `candidates.jpg` ni **o'zing ko'r**
   → `images.py pick N --name nom`. B-roll video uchun `--kind video` (Pexels/Pixabay kaliti kerak).
5. **AI** — `images.py ai "tavsif" --name nom` (faqat `GEMINI_API_KEY` bo'lsa; pullik bo'lishi
   mumkin, birinchi marta foydalanuvchidan so'ra).

Qoidalar:

- Nomzodlar varag'ini ko'rmasdan tanlama. Suv belgisi (watermark), matn yozilgan, sifati past,
  mavzuga aloqasiz rasmni olma. Hech biri mos kelmasa boshqa so'z bilan qidir yoki 2–3 bosqichga qayt.
- Qidiruv so'zi inglizcha va aniq: "teacher" emas, "teacher explaining at whiteboard classroom".
- Vertikal kadr uchun `--orient portrait` (to'liq ekran b-roll), kartochka uchun `any`.
- Tanilgan odam yuzi, boshqa brend logotipi, kino/multfilm kadri, mashhur asar — olinmaydi.
- Litsenziya `*.credit.json` ga yoziladi. `CC BY` bo'lsa muallifni post tavsifida ko'rsatish shart:
  render oxirida `Rasm manbalari` chiqadi, uni foydalanuvchiga albatta ayt.
- AI yaratgan realistik rasm ishlatilsa foydalanuvchiga ayt: Instagramda "AI info" belgisi kerak.
- Faktni buzadigan rasm qo'yma (masalan mijozning haqiqiy natijasi o'rniga o'ylab topilgan grafik).
  HTML grafikdagi har bir raqam videoda aytilgan yoki foydalanuvchi bergan bo'lishi shart.

## 5. Tekshirish aylanasi (o'tkazib yuborilmaydi)

1. `elements.json` yozilgach: har element o'rtasidagi vaqtlar bilan `--stills` (bir martada 12
   tagacha). Rasmni **och va qara**: o'qiladimi, yuzni yopmadimi, xavfsiz zonadami, chiroylimi.
2. Yomon ko'ringan narsani tuzat, yana `--stills`. Ko'ngling to'lmaguncha renderga o'tma.
3. Subtitr matni + reja + stills rasmini foydalanuvchiga ko'rsat. Tasdiqdan keyin `--approve-subs`.
4. Renderdan keyin: `python scripts/frames.py output/..._final.mp4` (yoki watcher `preview`) bilan
   kadrlar varag'ini ol va ko'r; `Tekshiruv` va `Platforma` qatorlari `[OK]` ekanini tekshir.
5. Hisobot: natija fayli, nima qilingani (qisqa), rasm manbalari, ovoz bo'yicha savol (musiqa,
   effektlar yoqdimi — sen eshita olmaysan), keyingi tuzatish uchun taklif.
6. Foydalanuvchi javobidagi har bir fikrni `feedback.py add` bilan yoz, sozlamaga aylanadiganini
   `brand.json`/`style.json` ga kirit, takrorlangan whisper xatosini `glossary.py add` bilan lug'atga
   qo'sh. Keyingi videoda o'sha xato takrorlanmasligi kerak.

## 6. Halol chegaralar

- Ovozni eshitmaysan: musiqa balandligi, effektlar, nutq tozaligi bo'yicha foydalanuvchi tinglaydi.
- Harakatni ko'rmaysan, faqat kadrlarni: animatsiya tezligi shubhali bo'lsa bir-biriga yaqin 3
  kadr ol: `frames.py VIDEO --at 2.0,2.1,2.25`.
- AI video (Kling, Veo, Seedance kabi) bu tizimda yaratilmaydi. Foydalanuvchi shunday klip bersa,
  u oddiy `broll` sifatida qo'yiladi.
- Murakkab harakatli sahna (3D, personaj animatsiyasi) kerak bo'lsa: `docs/REMOTION_PROMPT.md`.
