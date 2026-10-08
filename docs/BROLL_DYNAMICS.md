# B-roll va nutq energiyasi

`broll_system.py` caption matnidan object/action/place/number/abstract momentlarni leksikon bilan
rank qiladi, uzoq cue/visualdan uzoq joylarga bonus beradi. Bu semantic AI emas; exact fit agent
tomonidan kadrdan tekshiriladi. Sozlamalar `style.json: broll`, brend `style.broll`, per-video style.

```powershell
.venv\Scripts\python.exe scripts\broll_system.py prepare temp\video\cut.mp4 --subs temp\video\subs.srt --style temp\video\style.json --out-dir temp\video\broll --local temp\video\images
.venv\Scripts\python.exe scripts\broll_system.py accept temp\video\broll\broll_plan.json --selection '{"m01":"auto"}' --approval "Foydalanuvchining aynan javobi" --style temp\video\style.json
.venv\Scripts\python.exe scripts\broll_system.py reject temp\video\broll\broll_plan.json --moment m01 --number 2 --reason "adult instead of child" --history temp\video\broll\broll_history.json
# Barcha agentlar idle bo'lgandagina umumiy tarixga ko'chir:
.venv\Scripts\python.exe scripts\broll_system.py sync-history temp\video\broll\broll_history.json
```

PowerShell versiyasi JSON argument qo'shtirnoqlarini o'zgartirsa, shu funksiyani Python helperda
JSON dict bilan chaqir; mazmunni buzilgan buyruq bilan taxminan ishlatma.
`--moments` JSON ro'yxati aniq start/end/query bilan override; `--no-stock` mahalliy tekshiruv.
`--kind photo|video|mixed` candidate_kind override; mixed avval video, keyin foto qidiradi.
`assets/library/` ixtiyoriy; yo'q bo'lsa xato emas. Har material `.credit.json`, optional `.asset.json`
`tags` bilan keladi. Noma'lum manbali fayl ishlatilmaydi. Litsenziya nomi huquqiy kafolat emas;
original manba, shartlar va attribution saqlanadi. Cutoutning manbasi original bilan bir xil.

## Aniq o'lchovlar

| Check | O'lchov va chegarasi |
|---|---|
| 9:16 crop | Markaziy crop rect va qolgan maydon/original maydon. Subject kesilmaganini isbotlamaydi. Cutout butun holda fitted preview. |
| Resolution | Original piksel va full 9:16 crop piksel; kamida 540x960. Alpha sticker native eni >=260, bo'yi >=100; finalda 24% eni uchun. |
| Duration | ffprobe davomiyligi rejalangan intervaldan kam bo'lmasin. Rasmda cheklov yo'q. |
| Colour fit | CIE Lab medianlarining Euclidean masofasi, HSV o'rtacha saturation. Saturation <=.035 monochrome warning/fail; grading didi alohida. |
| Text/watermark/logo | Canny mayda konturlar soni va burchak edge ulushi. OCR/logotip tanish emas; doim human_review_required. |
| Semantic | Sarlavha/tag/query tokenlari va predmet anchor mosligi. Yosh, harakat va aniq predmet agent ko'rish tekshiruvini talab qiladi. |
| Source | `.credit.json` litsenziya maydoni; original sahifa/attribution agent tomonidan tekshiriladi. |

Video candidate 0, min_seconds/2 va min_seconds nuqtalarida tekshiriladi. Bu barcha frame'larni
ko'rish yoki motion hukmi emas. Faqat ko'rishdan o'tgan `visual_review: "ok"` auto uchun eligible.
Agent aniq ko'rilgan dalilni `visual_notes`ga yozadi; taxminni fact deb yozmaydi.

Har moment uchun 3 ustunli sheet, barcha sheetlar **bitta tasdiq xabarida**. Har xil source avval;
kam bo'lsa bir suratning cutout/original variantlari ekani aytiladi. Yetarli nomzod bo'lmasa bo'sh
ustun qoladi; kuchsiz yoki mos kelmagan klip qo'shilmaydi. User raqam/auto/none tanlaydi, javob
o'z video HOLAT.mdga so'zma-so'z. `accept` matn tasdig'ini chetlab o'tmaydi.
Rang saqlanadi, pastda gradient; tanlangan interval 2.5–4s. So'zga aniq mos vaqt, klinik natija
o'ylab chiqarilmaydi. Generated suggestion `automatic: true` orqali element zichligiga bo'ysunadi.

`style/broll_history.json`: accepted/rejected va aynan sabab. Auto avval bu tarixni o'qiydi;
exact rejected asset keskin pasayadi; oq-qora/adult/generic sababi mos nomzod rankini tushiradi.
Tanlanmagan = rejected emas. Parallel tarix o'z jobida, umumiy sync faqat hamma idle bo'lgach.

## Energiya

```powershell
.venv\Scripts\python.exe scripts\energy_curve.py temp\video\cut.mp4 --words temp\video\cut.words.json --subs temp\video\subs.srt --elements temp\video\elements.json --style temp\video\style.json --out-dir temp\video\energy
```

Per second: word starts / second; mono decoded audio RMS dBFS; word interval uniondan pause.
RMS LUFS emas, interval pauzasi VAD emas. Hook/problem/key_point/proof/CTA keyword/raqam
heuristikasi; `dynamics.structure_overrides [{start,end,label}]` bilan tuzatiladi.
Vaznlar, smoothing va hamma diapazon `dynamics` style keylarida.

Egri chiziq zoom kuchi va visual punch-cut oralig'i, captionning move/scale/blur miqdori,
automatic element oralig'i, SFX 10s density/gain, backgroundning uzluksiz clock tezligini
boshqaradi. Explicit user element o'chirilmaydi. **Nutq kesishlari, matn va so'z vaqtlari o'zgarmaydi.**
`energy.json` raw feature, controls, rejali eventlar va skip qilingan automatic elementlarni saqlaydi;
`energy_curve.png` zoom/element vaqtlarini ko'rsatadi. Audio cue sheet SFXning haqiqiy vaqtini beradi.

`--music USER_FILE` faqat mavjud NumPy spectral-flux onset candidates beradi (`beats.json`).
Bu aniq BPM/beat grid emas, yangi kutubxona kerak emas; avtomatik musiqa qidirilmaydi.
Filmstrip va A/B ko'rish, subtle/stronger tinglash tasdig'i texnik metrikadan alohida.
