# Ovoz effektlari (SFX): sintez, sotib olinadigan to'plam va import

Agent ovozni eshitmaydi. Bu yerdagi hamma raqam o'lchov (balandlik, davomiylik), "yaxshi eshitiladi" degan da'vo emas.
Yoqdi-yoqmadi qarori foydalanuvchida: har renderda `stronger` (asosiy) va `_subtle` (ikkinchi) variant chiqadi.

## Hozirgi kutubxona (sintez, v2)

`scripts/sfx_synth.py` faqat numpy bilan 10 kategoriyada 4 tadan variant yasaydi:
`assets/sfx/<kategoriya>/synth_v2_NN.wav` (+ `credit.json`, `LICENSE.txt`). Har biri qat'iy seed'dan:
qayta ishga tushirilsa aynan shu fayl chiqadi.

| Kategoriya | Qanday yasalgan | Qayerda ishlatiladi (`style.json` → `sfx.event_map`) |
|---|---|---|
| whoosh | 3 qatlam: o'rta shovqin polosasi ko'tarilib-tushadi, yuqori "havo", past gumburlash; chapdan o'ngga panorama | sticker, title, hero object kirishi |
| swipe | qisqa yuqori shovqin, chastotasi ko'tariladi | b-roll kirishi |
| pop | pasayuvchi sinus + kichik "chertish" | katta so'z |
| click | qisqa yuqori shovqin + ping + past "tok" | label, follow tugmasi, pill |
| tick | qisqa yuqori ton | sanash, ro'yxat |
| hit | o'rta "zarb": shovqin chaqnashi + pasayuvchi tana + sub | hero object qo'nishi |
| impact | katta zarb: 40–140 Hz sub, knock, past o'tkazgichli "crash", yengil saturatsiya | katta raqam/hero kirishi |
| riser | shovqin polosasi va garmonik ton 1.2–2 s ko'tariladi | bo'lim oldidan |
| ding | qo'ng'iroq obertonlari (1, 2, 2.76, 5.4) | raqam/natija |
| typing | 4–7 tasodifiy klaviatura bosishi | yozuv terilishi |

**Balandlik qoidasi:** eng baland 100 ms oynaning RMS'i −15 dBFS, sample peak ≤ −1 dBFS. Juda qisqa zarbali
tovushlarda (click, typing) peak chegarasi ustun bo'ladi: RMS 1–3 dB pastroq qoladi (`test_sfx.py` tekshiradi).
Har kategoriya uchun eshitib ko'rish fayli: `assets/sfx/_preview/<kategoriya>.wav` (variantlar ketma-ket, 0.35 s oraliq).

```powershell
.venv\Scripts\python.exe scripts\sfx_synth.py                        # yetishmaganini yasaydi
.venv\Scripts\python.exe scripts\sfx_synth.py --only whoosh --variants 6 --force
```

## Qaysi fayl ishlatiladi

`sound_design.variants()`: **litsenziyasi tasdiqlangan haqiqiy fayl bo'lsa doim u**; bo'lmasa sintezning eng yangi
versiyasi (`synth_version`). Brend papkasi (`brands/<nom>/sfx/<kategoriya>/`) loyiha kutubxonasidan oldin qaraladi.
Bir kategoriyada ketma-ket bir xil fayl takrorlanmaydi.

## Nima sotib olish kerak (tavsiya)

Bitta to'plam yetadi, agar shu kategoriyalarni qamrasa. Format: WAV (44.1/48 kHz, 16/24-bit), MP3 ham ishlaydi.
Litsenziya: **tijoratda, ijtimoiy tarmoq va mijoz videolarida ishlatish mumkin** (royalty-free, commercial use).
Atribut talab qilinsa, uni ham yozib qo'ying.

| Kategoriya | Nechta (kamida / yaxshi) | Nimaga e'tibor |
|---|---|---|
| whoosh | 6 / 12 | qisqa (0.3–0.8 s), har xil balandlikda; "swoosh", "pass-by" |
| swipe / transition | 4 / 8 | 0.2–0.5 s, keskin boshlanmasin |
| pop | 6 / 10 | yumshoq, "bubble", "UI pop" |
| click | 4 / 8 | UI tugma, sichqoncha |
| tick | 2 / 4 | soat, taymer |
| hit | 4 / 6 | quruq zarb, uzun reverbsiz |
| impact | 4 / 6 | "cinematic hit/boom", 1 s atrofida |
| riser | 3 / 6 | 1–3 s, oxiri keskin to'xtaydi |
| ding | 3 / 6 | bildirishnoma, "success" |
| typing | 2 / 4 | klaviatura, yozuv mashinkasi |

Fayl yoki papka nomlarida shu so'zlar bo'lsa (`whoosh`, `click`, `impact`, `riser` ...) import ularni o'zi joylaydi.

## Import qadamlari

1. Sotib olingan zip yoki papkani `assets\sfx\_inbox\` ga tashlang (papka bo'lmasa yarating).
2. Bir marta do'kon va litsenziyani yozib, ishga tushiring:

```powershell
.venv\Scripts\python.exe scripts\sfx_import.py --shop "Do'kon nomi" --license "Litsenziya nomi yoki havolasi"
```

3. Skript har faylni: ffmpeg bilan 48 kHz stereo WAV ga o'tkazadi; bosh va oxiridagi jimlikni (−50 dBFS dan past)
   kesadi; balandlikni sintez bilan bir xil qoidaga keltiradi; nomidan kategoriyani topadi; natija
   `assets/sfx/<kategoriya>/real__<paket>__<nom>.wav`. Aniqlanmaganlari `assets/sfx/_unsorted/` ga tushadi:
   ularni kerakli kategoriya papkasiga o'zingiz ko'chiring va `.venv\Scripts\python.exe scripts\sfx_library.py` ni ishga tushiring.
4. Paket uchun litsenziya eslatmasi: `assets/sfx/_licenses/<paket>.md`. Kutubxona indeksi: `assets/sfx/index.json`.
5. Asl zip `_inbox/_done/<paket>/` ga ko'chadi (o'chirilmaydi).

**Git:** sotib olingan audio (`real__*`, `_inbox/`, `_unsorted/`) gitga kirmaydi (`.gitignore`): do'kon litsenziyasi
odatda qayta tarqatishni taqiqlaydi. Gitda faqat `index.json` va `_licenses/*.md` saqlanadi. Yangi kompyuterda paketni
qayta import qiling.

Zip ichidagi xavfli yo'llar (`..`, to'liq yo'l) o'tkazib yuboriladi; faqat audio fayllar o'qiladi.

## Tekshiruv

`scripts/test_sfx.py`: sintez determinizmi va variantlar farqi, balandlik/peak, shakl o'lchovlari (whoosh ko'tarilib
tushadi, riser oxirigacha ko'tariladi, impact'da past chastota ko'p), import (zip xavfsizligi, jimlik kesish,
normalizatsiya, kategoriya, `_unsorted`, litsenziya eslatmasi, indeks), `.gitignore` qoidalari, real > sintez.
