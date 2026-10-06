# Video montaj tizimi — agentlar uchun qoidalar

Bu faylni Codex to'g'ridan-to'g'ri o'qiydi, Claude Code esa `CLAUDE.md` orqali (`@AGENTS.md`).
Montaj mantig'i agentda emas, `scripts/` dagi Python skriptlarida. Agentning ishi: skriptlarni
ishga tushirish, natijani tekshirish, kerak bo'lsa skript yoki `style/style.json` ni tuzatish.

## Loyiha nima

Reels/TikTok uchun vertikal (9:16, 1080x1920) videolarni avtomatik montaj qiladigan tizim:
nutqni matnga aylantiradi, jim joylar va takrorlarni kesadi, subtitr qo'yadi, ovozni me'yorlaydi
va yakuniy faylni chiqaradi. Asosiy til o'zbek, rus va ingliz ham bo'lishi mumkin.
Kompyuter: Windows, PowerShell, 4 yadro, 16 GB RAM. Standart holatda hammasi CPU'da ishlaydi.

## Papkalar

| Papka / fayl | Vazifasi |
|---|---|
| `input/` | Asl videolar. **Faqat o'qiladi.** |
| `output/` | Tayyor natijalar. Natija faqat shu yerga yoziladi. |
| `temp/` | Oraliq fayllar (har video uchun `temp/<nom>/`). Xohlagan payt o'chirsa bo'ladi. |
| `samples/` | Uslub namunasi bo'ladigan videolar. Faqat o'qiladi. |
| `style/style.json` | Barcha uslub qiymatlari. |
| `style/fonts/` | Qo'shimcha shriftlar (.ttf/.otf). Tizimda yo'q shriftni shu yerga tashlang. |
| `scripts/` | Montaj skriptlari. |
| `setup.ps1` | Muhitni tekshirish va o'rnatish. |
| `docs/TOOLS.md` | Ishlatilgan va qo'shimcha ochiq kodli tool'lar ro'yxati. |

`input/`, `output/`, `temp/`, `samples/`, `.venv/` va video/audio fayllar gitga kirmaydi.

## Uslub qoidalari

Hamma uslub qiymati `style/style.json` da turadi: o'lcham, fps, kesish chegaralari, subtitr
shrifti/rangi/joyi, ovoz balandligi, whisper modeli. **Qoidani o'zgartirish uchun shu faylni
tahrir qiling**, skript ichiga qiymat yozmang. Skriptlar har ishga tushganda faylni qayta o'qiydi.
`_izoh` kalitlari faqat tushuntirish.

## Skriptlarni ishga tushirish

Har doim `.venv` dagi Python bilan, loyiha papkasidan:

```powershell
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4
```

Har bir skriptda `--help` bor.

| Skript | Nima qiladi |
|---|---|
| `pipeline.py VIDEO` | Hammasini ketma-ket bajaradi. |
| `transcribe.py VIDEO` | So'z-so'z vaqtli matn: `temp/<nom>/orig.words.json`, `orig.srt`. |
| `auto_cut.py VIDEO [--words F] [--apply]` | Jim joy va takrorlar ro'yxati; `--apply` bilan kesadi. |
| `subtitles.py VIDEO SRT [--ass-only] [--approved]` | SRT dan uslubli subtitr (ASS), videoga yozish. |
| `render.py VIDEO [--subs F.ass] [--music F]` | Yakuniy format, loudnorm, musiqa. |
| `analyze_samples.py` | `samples/` tahlili, hisobot: `temp/analysis/report.json`. |
| `selftest.py` | Tizimni test video bilan sinaydi. |
| `check_env.py` | Kutubxonalar va ffmpeg bor-yo'qligini tekshiradi. |
| `bench_whisper.py` | Whisper tezligini o'lchaydi, model tavsiya qiladi. |

## Ish tartibi

1. **transcribe** — asl videodan matn va so'z vaqtlari.
2. **auto_cut** — kesish ro'yxatini ko'rsatadi, keyin kesadi. So'z vaqtlari yangi vaqt
   chizig'iga o'tkaziladi. Natija: `temp/<nom>/cut.mp4`, `cuts.json`.
3. **subtitles** — tekshiriladigan matn: `temp/<nom>/subs.srt`. Tasdiqdan keyin uslubli
   `subs.ass` yasaladi.
4. **render** — 9:16 ga moslash, subtitrni yozish, loudnorm, musiqa. Natija: `output/<nom>_final.mp4`.

Subtitr render bosqichida, video yakuniy o'lchamga keltirilgandan keyin yoziladi (shunda shrift
o'lchami har doim bir xil chiqadi va video ortiqcha marta qayta kodlanmaydi).

`pipeline.py` ikki marta ishga tushiriladi:

```powershell
# 1) Transkripsiya + kesish. Subtitr matnini ko'rsatib, 3-kod bilan to'xtaydi.
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4

# 2) Foydalanuvchi matnni tasdiqlagach (kerak bo'lsa temp\<nom>\subs.srt tuzatilgach):
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4 --approve-subs
```

Ikkinchi ishga tushirish oldingi ishni qayta bajarmaydi va tuzatilgan `subs.srt` ni ishlatadi.
`--force` hammasini boshidan boshlaydi (oldingi matn `subs.prev.srt` da qoladi).
Chiqish kodi 3 xato emas, "tasdiq kutilmoqda" degani.

## Qoidalar

1. **`input/` dagi fayllarni hech qachon o'zgartirma, ko'chirma yoki o'chirma.** `samples/` ham shunday.
2. **Natija faqat `output/` ga**, oraliq fayllar faqat `temp/` ga yoziladi.
3. **Subtitr matnini videoga yozishdan oldin foydalanuvchiga ko'rsat va tasdiqlatib ol.**
   O'zbek tilida whisper xato qiladi. Matnni to'liq ko'rsat, "ishonchi past" so'zlarni alohida ayt.
   `--approve-subs` va `--approved` ni faqat foydalanuvchi "ha" degandan keyin ishlat.
   Kesilgan takrorlar ro'yxatini ham ko'rsat: noto'g'ri kesilgan bo'lsa `--no-repeats` bilan qayta ishla.
4. **Katta o'chirish yoki o'rnatishdan oldin so'ra.** (`temp/` ni tozalash, yangi dastur yoki
   kutubxona, model yuklash, `.venv` ni qayta yaratish.) Kutubxonalar faqat `.venv` ichiga o'rnatiladi.
5. **Skript xato bersa, sababini top va tuzat. Jim o'tib ketma**, xatoni yashirma, bosqichni
   tashlab ketma. Tuzata olmasang, nima bo'lganini va nimani sinaganingni foydalanuvchiga ayt.
6. Bilmagan narsangni taxmin qilma: buyruq yoki parametrni avval `--help` yoki koddan tekshir.
7. Foydalanuvchi boshlang'ich dasturchi: har qadamni oddiy o'zbek tilida, qisqa tushuntir.

## Agentlar bilan ishlash

- **Bir vaqtda faqat bitta agent ishlaydi** (Claude Code yoki Codex). Ikkalasi birga ishlamaydi.
- Ishni boshlashdan oldin `git status` va `git log --oneline -5` ni ko'r: oldingi agent nima qilgan.
- Skript, `style.json` yoki shu faylni o'zgartirgach, **darhol `git commit` qil** (qisqa, aniq xabar bilan).
- Skriptni o'zgartirgach `.venv\Scripts\python.exe scripts\selftest.py --no-whisper` ni ishga tushir.

## Natijani tekshirish

Har renderdan keyin kutilgan natijani `ffprobe` bilan solishtir (`pipeline.py` va `render.py`
buni o'zi ham qiladi va mos kelmasa xato beradi):

```powershell
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of default=nw=1 output\video_final.mp4
```

- **Davomiylik**: kesilgan video uzunligiga teng (±0.5 s), asl videodan uzun emas.
- **O'lcham**: `style.json` dagi `video.width` x `video.height` (1080x1920).
- **Ovoz**: ovoz oqimi bor (`codec_type=audio`).

## Namuna videolardan uslub olish

1. Foydalanuvchi yoqqan uslubdagi 3–5 ta videoni `samples/` ga tashlaydi.
2. `.venv\Scripts\python.exe scripts\analyze_samples.py`
3. `temp/analysis/report.json` ni o'qi. `summary.suggested_style` raqamli tavsiya beradi.
4. Har video uchun `temp/analysis/<nom>/sheet_*.jpg` rasmlarini **o'zing ko'rib chiq**: subtitr joyi,
   shrift turi va o'lchami, rang va kontur, ajratib ko'rsatilgan so'z rangi, effektlar, rang uslubi.
5. Xulosani foydalanuvchiga ko'rsat. U rozi bo'lsa `style/style.json` ga yoz va commit qil.

## Muhit haqida

- Video karta va o'rnatilgan dasturlar holati: `temp/setup_report.txt` (`setup.ps1` yozadi).
- NVIDIA karta bo'lmasa `video.use_nvenc` `false` turadi va whisper `cpu` / `int8` da ishlaydi.
- FFmpeg 7+ da uzun filtr grafigi `-/filter_complex fayl` orqali beriladi (eski
  `-filter_complex_script` FFmpeg 9 da olib tashlangan). Buni `common.run_ffmpeg_graph` hal qiladi.
- Windows'da subtitr filtri yo'lidagi `:` va `\` muammosi `common.filter_path` da hal qilingan:
  ffmpeg loyiha papkasidan ishga tushadi, yo'l nisbiy va to'g'ri sleshli bo'ladi, qolgan maxsus
  belgilar ekranlanadi. Subtitr yo'lini qo'lda yig'ma, shu funksiyani ishlat.
