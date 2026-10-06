# Video montaj tizimi — agentlar uchun qoidalar

Bu faylni Codex to'g'ridan-to'g'ri o'qiydi, Claude Code esa `CLAUDE.md` orqali (`@AGENTS.md`).
Montaj mantig'i agentda emas, `scripts/` dagi Python skriptlarida. Agentning ishi: skriptlarni
ishga tushirish, natijani tekshirish, matn va grafik elementlarni tayyorlash, kerak bo'lsa skript,
brend yoki `style/style.json` ni tuzatish.

**Har bir montajdan oldin `docs/PLAYBOOK.md` ni o'qi**: unda montajor kabi o'ylash tartibi bor
(reja jadvali, nima aytilsa nima ko'rsatiladi, rasm topish zinapoyasi, tekshirish aylanasi).

## Loyiha nima

Foydalanuvchi montajor, har xil brendlar uchun Reels/TikTok (9:16, 1080x1920) videolar qiladi.
Tizim: nutqni matnga aylantiradi, jim joy va takrorlarni kesadi, kesishda zoom qiladi, animatsiyali
subtitr va grafik elementlar qo'yadi, brend logotipi va oxirgi kadrni qo'shadi, ovozni me'yorlaydi.
Asosiy til o'zbek, rus va ingliz ham bo'ladi. Kompyuter: Windows, 4 yadro, 16 GB RAM, NVIDIA yo'q
(hammasi CPU'da).

## Papkalar

| Papka / fayl | Vazifasi |
|---|---|
| `input/` | Asl videolar. **Faqat o'qiladi.** |
| `output/` | Tayyor natijalar (brend tanlansa `output/<brend>/`). Natija faqat shu yerga yoziladi. |
| `temp/` | Oraliq fayllar (har video uchun `temp/<nom>/`). Xohlagan payt o'chirsa bo'ladi. |
| `samples/` | Uslub namunasi bo'ladigan videolar (brend bo'yicha `samples/<brend>/`). Faqat o'qiladi. |
| `style/style.json` | Umumiy (standart) uslub qiymatlari. |
| `style/fonts/` | Shriftlar: Inter, Montserrat, Onest, Oswald, Unbounded, Playfair Display, Caveat. |
| `brands/<nom>/` | Brend profili: `brand.json`, `logo.png`, `fonts/`, `music/`, `sfx/`. |
| `assets/sfx/` | Ovoz effektlari: pop, click, tick, thud, ding, whoosh, swipe, riser. |
| `assets/models/` | Yuzni topish modeli (YuNet). |
| `assets/emoji/` | Emoji rasmlari (Noto, bitta zip ichida). |
| `assets/icons/` | 1500+ vektor belgi (Phosphor, MIT): `icon` elementi va `icons.py`. |
| `assets/html/` | HTML grafika namunasi (`shablon.html`). |
| `.env` | Maxfiy kalitlar (stok va AI rasm xizmatlari). Gitga kirmaydi, o'qib ko'rsatilmaydi. |
| `docs/claude_skills/` | Claude Code uchun `/montaj` va `/brend` buyruqlari (manba; `.claude/skills/` ga ko'chiriladi). |
| `docs/PLAYBOOK.md` | Montajor qo'llanmasi: qaror qabul qilish tartibi. **Har montajda o'qiladi.** |
| `scripts/` | Montaj skriptlari. |
| `jobs/` | Watcher topshiriqlari va natijalari (chatdan montaj). |
| `setup.ps1`, `start_watcher.bat` | Muhitni o'rnatish; watcher'ni ochish. |
| `docs/TOOLS.md` | Ishlatilgan va qo'shimcha ochiq kodli tool'lar. |
| `docs/SKILLS_AUDIT.md` | Tashqi skill va plaginlar auditi; Remotion haqida xulosa. |
| `docs/REMOTION_PROMPT.md` | Remotion'ni maxsus sahnalar uchun qo'shish prompti (ixtiyoriy). |

`input/`, `output/`, `temp/`, `samples/`, `jobs/`, `.venv/` va video fayllar gitga kirmaydi.

## Uslub va brendlar

- Umumiy qiymatlar `style/style.json` da. **Qoidani o'zgartirish uchun shu faylni tahrir qiling**,
  skript ichiga qiymat yozmang. `_izoh` kalitlari faqat tushuntirish.
- Har brend uchun `brands/<nom>/brand.json`. Uning `"style"` bo'limidagi qiymatlar `style.json`
  dagi shu nomli qiymatni almashtiradi (rang, shrift, subtitr uslubi, logotip, oxirgi kadr, musiqa).
  Yangi brend: `brands/_shablon` dan nusxa olinadi. Brend `--brand NOM` bilan tanlanadi.
- Fayl yo'llari (`logo.file`, `audio.music_file`, elementlardagi `file`) avval brend papkasidan,
  keyin loyiha papkasidan qidiriladi.
- Mijoz brendi haqida bilmagan narsani (rang, shrift, logotip) o'ylab topma: foydalanuvchidan so'ra.

### Yangi mijoz (brend) qo'shish

1. Foydalanuvchidan so'raladigan narsalar: brend nomi, logotip (shaffof fonli PNG), asosiy rang,
   Instagram manzili, bor bo'lsa shrift va musiqa. Yoqqan videolari bo'lsa `samples/<brend>/` ga.
2. `.venv\Scripts\python.exe scripts\new_brand.py NOM --title "Nomi" --handle @manzil --logo yo'l\logo.png`
   Rang berilmasa logotipdan olinadi (natijani foydalanuvchiga ko'rsatib tasdiqlat).
3. Namunalar bo'lsa: `analyze_samples.py --brand NOM`, kadrlarni ko'rib `brand.json` ni to'ldir
   (subtitr uslubi, joyi, rang ishlovi). Ovoz haqida taxmin qilma: eshita olmaysan, so'ra.
4. `--stills` bilan bitta videoda ko'rsatib, foydalanuvchi rozi bo'lgach commit qil.

## Skriptlar

Har doim `.venv` dagi Python bilan, loyiha papkasidan. Har birida `--help` bor.

```powershell
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4 --brand NOM
```

| Skript | Nima qiladi |
|---|---|
| `pipeline.py VIDEO` | Hammasini ketma-ket bajaradi. |
| `transcribe.py VIDEO` | So'z-so'z vaqtli matn: `temp/<nom>/orig.words.json`, `orig.srt`. |
| `auto_cut.py VIDEO` | Jim joy, takror va qo'lda berilgan oraliqlarni kesadi (`--apply`). |
| `script_align.py` | Tayyor skript matnini nutq vaqtlariga tekislaydi (pipeline `--script` shuni chaqiradi). |
| `images.py` | Stok rasm/b-roll qidirish (`search`), yuklash (`pick`), AI rasm (`ai`), manbalar (`credits`). |
| `html_render.py` | HTML/CSS/SVG sahifani shaffof PNG qiladi (Edge/Chrome orqali): agent o'zi chizadi. |
| `icons.py` | Belgilarni qidirish (`find`), ko'rish (`sheet`), PNG qilish (`png`). |
| `frames.py VIDEO` | Tayyor videodan kadrlar varag'i (natijani ko'rib tekshirish uchun). |
| `compose.py VIDEO` | Motion render: zoom, subtitr animatsiyasi, elementlar, brend, ovoz. |
| `subtitles.py`, `render.py` | Eski oddiy dvigatel (`captions.engine: ass`): ASS subtitr va render. |
| `audio_mix.py`, `make_sfx.py` | Ovozni yig'ish; ovoz effektlarini generatsiya qilish. |
| `face.py VIDEO` | Yuz joylashuvini topadi. |
| `new_brand.py NOM` | Yangi brend papkasi va `brand.json` yaratadi. |
| `analyze_samples.py` | `samples/` tahlili: `temp/analysis/report.json`. |
| `selftest.py`, `check_env.py`, `bench_whisper.py` | Sinov, muhit tekshiruvi, whisper tezligi. |
| `watcher.py` | Chatdan kelgan topshiriqlarni bajaradi. |

## Ish tartibi

1. **transcribe** — asl videodan matn va so'z vaqtlari.
2. **auto_cut** — kesish ro'yxatini ko'rsatadi, keyin kesadi: `temp/<nom>/cut.mp4`, `cuts.json`.
   So'z vaqtlari kesilgan videoga o'tkaziladi (`cut.words.json`).
3. **subtitr matni** — `temp/<nom>/subs.srt`. Foydalanuvchi tekshiradi, agent belgilar qo'yadi.
4. **compose** — yakuniy render: `output/<nom>_final.mp4`.

`pipeline.py` ikki bosqichda ishlaydi:

```powershell
# 1) Transkripsiya + kesish. Subtitr matnini ko'rsatib, 3-kod bilan to'xtaydi.
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4 --brand NOM

# (ixtiyoriy) render qilmasdan ko'rish: shu soniyalardagi kadrlar temp\<nom>\stills.jpg ga chiqadi
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4 --brand NOM --stills 1.5,4,9

# 2) Foydalanuvchi matnni tasdiqlagach:
.venv\Scripts\python.exe scripts\pipeline.py input\video.mp4 --brand NOM --approve-subs
```

Ikkinchi ishga tushirish oldingi ishni qayta bajarmaydi, tuzatilgan `subs.srt` va (bo'lsa)
`temp/<nom>/elements.json` ni ishlatadi. Chiqish kodi 3 xato emas, "tasdiq kutilmoqda" degani.
`--force` hammasini boshidan boshlaydi (oldingi matn `subs.prev.srt` da qoladi).

### Tayyor skript bilan ishlash (`--script`)

Foydalanuvchi videoda nima deyilganini matn qilib bersa (`input/<video nomi>.txt` yoki
`--script yo'l.txt`), subtitr matni **skriptdan**, vaqti **whisperdan** olinadi. Video yonida shu
nomli `.txt` bo'lsa pipeline uni o'zi topadi (`--no-script` o'chiradi).

- Skriptda belgilar ishlaydi (`*katta*`, `**rangli**`, `!!juda katta!!`). Har qator alohida subtitr bo'lagi.
- `[kvadrat qavs]` ichidagi yozuv aytilmaydi, u montaj eslatmasi: `[rasm: tog']`, `[stat: 85%]`.
  Har eslatmaning videodagi vaqti `temp/<nom>/script.notes.json` da (`notes[].at`). Ularni bajar.
- Chiqishda farqlar ko'rsatiladi: boshqacha eshitilgan so'zlar, skriptda yo'q lekin aytilgan gap
  (whisper matni qoladi, tekshir), skriptda bor lekin aytilmagan gap (subtitrga qo'yilmaydi).
- Skript videoga mos kelmasa (35% dan kam so'z topilsa) xato beradi: noto'g'ri fayl berilgan.
- Tasdiq qoidasi o'zgarmaydi: matn baribir foydalanuvchiga ko'rsatiladi.
- Asl whisper so'zlari `cut.whisper.words.json` da qoladi.

Kesishni boshqarish (vaqtlar asl video bo'yicha, soniyalarda): `--remove 10-15,22.5-24` (olib
tashlash), `--trim 5-42` (faqat shu oraliq qolsin), `--no-silence`, `--no-repeats`, `--no-cut`,
`--silence-db -40`. Kesish sozlamasi o'zgarsa transkripsiya qayta qilinmaydi, lekin `subs.srt`
qaytadan yaratiladi.

## Subtitr matni va belgilar

`subs.srt` matniga belgilar qo'yiladi (vaqt qatorlariga tegilmaydi):

| Belgi | Natija |
|---|---|
| `*so'z*` | katta |
| `**so'z**` | katta va brend rangida |
| `!!so'z!!` | juda katta va rangli (raqam, asosiy so'z) |
| `_so'z_` | faqat rangli, o'lchami o'zgarmaydi |

- Bir bo'lakda bitta asosiy ibora belgilanadi; qolgan so'zlar o'zi kichik bo'ladi. Har bo'lakka
  belgi qo'yish shart emas: belgisiz bo'lak o'rtacha o'lchamda chiqadi, raqamlar o'zi ajratiladi.
- Ma'no tashiydigan so'zni belgilang (raqam, natija, mahsulot nomi), bog'lovchini emas.
- Uslub `captions.preset`: `clean` (toza, kichik harf), `glow` (baland KATTA harf, porlash),
  `box` (asosiy so'z rangli qutida), `serif` (nafis kursiv). Joyi: `captions.position_y`.

## Grafik elementlar (`temp/<nom>/elements.json`)

Vaqtlar **kesilgan video** bo'yicha (soniya). `x`, `y`, `width` kadrga nisbatan 0..1.

```json
{"elements": [
  {"type": "title", "start": 0, "end": 2.4, "text": "TOP 5\n**muzqaymoq**", "y": 0.22},
  {"type": "list", "start": 2.5, "end": 9, "x": 0.09, "y": 0.3,
   "items": [{"at": 2.6, "text": "birinchi"}, {"at": 4.1, "text": "ikkinchi", "image": "rasm.png"}]},
  {"type": "sfx", "at": 2.6, "name": "pop"}
]}
```

| type | Nima | Asosiy maydonlar |
|---|---|---|
| `title`, `text` | Sarlavha yoki erkin matn (belgilar ishlaydi, `\n` yangi qator) | `text`, `x`, `y`, `size`, `preset`, `font`, `color`, `anim` |
| `list` | Raqamli ro'yxat, qatorlar o'z vaqtida chiqadi | `items[{at, text, image}]`, `x`, `y`, `style` (badge/plain), `numbered` |
| `choice` | To'g'ri/noto'g'ri kartochkasi (✗ ✓ va matn) | `items[{at, text, ok}]`, `y`, `color` |
| `stat` | Katta raqam sanab chiqadi, halqa to'ladi | `value`, `suffix`, `label`, `ring`, `x`, `y`, `size` |
| `voice` | Ovozli xabar pleyeri | `y`, `width`, `length` |
| `image` | Rasm yoki kichik video ustma-qatlam | `file`, `x`, `y`, `width`, `radius`, `anim` (pop/fade/none), `border` (oq hoshiya, 0.012), `border_color`, `rotate` (gradus) |
| `icon` | Vektor belgi (1500+), ostida ixtiyoriy yozuv | `name`, `x`, `y`, `size`, `bg` (none/circle/square/glass), `color`, `bg_color`, `style` (fill/bold), `text` |
| `broll` | Qo'shimcha kadr: `mode` `full` (to'liq ekran) yoki `split` (tepada gapiruvchi) | `file`, `mode`, `fade`, `offset` |
| `zoom` | Qo'lda zoom | `scale`, `x`, `y`, `ease` |
| `sfx` | Ovoz effekti | `at`, `name`, `volume_db` |
| `callout` | Panel ichidagi matn: `style` `glass` (orqasi xira), `dark`, `accent` | `text`, `x`, `y`, `width`, `style` |
| `lower_third` | Ism va lavozim plashkasi | `name`, `role`, `x`, `y` |
| `emoji` | Katta emoji, sakrab chiqadi | `emoji`, `x`, `y`, `size` |

Har elementda `start` va `end` bor. Elementlarni matn mazmuniga qarab qo'ying: nima aytilayotgan
bo'lsa, o'sha paytda ko'rinsin (so'z vaqtlari `cut.words.json` da). Subtitr bilan ustma-ust
tushmasin: subtitr `position_y` atrofida turadi. Yo'q faylni o'ylab topma: rasm kerak bo'lsa
pastdagi "Rasm va grafika" bo'limi bo'yicha top yoki chiz. Render qilishdan oldin `--stills` bilan
ko'rib tekshir.

Logotip va oxirgi kadr elementlarga yozilmaydi: ular brenddan (`logo`, `endcard`) olinadi.

- **Emoji** subtitr va istalgan matn ichida ishlaydi (rasm qilib chiziladi). Bayroqlar yo'q.
- **Shaffof fonli video** (After Effects yoki Remotion'dan ProRes 4444 `.mov`, yoki alfa kanalli
  `.webm`): `image` elementi bilan istalgan joyga, `broll` + `"mode": "full"` bilan butun kadr ustiga
  qo'yiladi. Tayyor animatsiya to'plamlari (obuna tugmasi, plashka) shu yo'l bilan ishlatiladi.
- `choice` uchun `"style": "glass"` shisha ko'rinish beradi.

## Rasm va grafika (o'zing top yoki chiz)

Fayllar `temp/<nom>/images/` ga tushadi (brendga doimiy kerak bo'lsa `--out brands/NOM/assets`).
`elements.json` da `file` loyiha papkasiga nisbatan yoziladi: `temp/<nom>/images/tog.jpg`.

```powershell
# Belgi qidirish (inglizcha), keyin elements.json da {"type": "icon", "name": "rocket-launch", ...}
.venv\Scripts\python.exe scripts\icons.py find rocket

# O'zing chizish: HTML yoz (namuna: assets\html\shablon.html), PNG qil
.venv\Scripts\python.exe scripts\html_render.py temp\video\gfx\karta.html -o temp\video\images\karta.png --trim --brand NOM

# Stok rasm: qidir -> temp\video\images\candidates.jpg ni OCHIB KO'R -> tanla
.venv\Scripts\python.exe scripts\images.py search "student studying laptop" --video input\video.mp4 --orient portrait
.venv\Scripts\python.exe scripts\images.py pick 3 --name talaba --video input\video.mp4

# Stok b-roll video (Pexels yoki Pixabay kaliti kerak)
.venv\Scripts\python.exe scripts\images.py search "city traffic night" --kind video --video input\video.mp4

# AI rasm (GEMINI_API_KEY kerak; birinchi marta foydalanuvchidan so'ra)
.venv\Scripts\python.exe scripts\images.py ai "tavsif inglizcha" --name nom --video input\video.mp4
```

- Manbalar: `pexels`, `pixabay` (bepul kalit kerak, sifatli foto va video), `openverse`, `wikimedia`
  (kalitsiz). Faqat tijoratda ishlatsa bo'ladigan litsenziyalar olinadi (`style.json`: `images`).
- Kalitlar `.env` faylida: `PEXELS_API_KEY=...`, `PIXABAY_API_KEY=...`, `GEMINI_API_KEY=...`.
  Kalitni foydalanuvchi o'zi yozadi. **`.env` ni ochma, ekranga chiqarma, commit qilma.**
- Har yuklangan fayl yonida `<fayl>.credit.json` (manba, muallif, litsenziya). Render oxirida
  `Rasm manbalari` ro'yxati chiqadi va `temp/<nom>/credits.txt` ga yoziladi: uni foydalanuvchiga ayt.
- HTML sahifada: shriftlar nomi bilan ishlaydi (`font-family: "Inter"`), brend rangi `var(--accent)`,
  kadr o'lchami `var(--W)`/`var(--H)`, fon shaffof, internetdan hech narsa yuklanmaydi. Bitta kadr
  olinadi (animatsiya yo'q): harakatni elementning `anim`i beradi.
- `html_render.py` Edge yoki Chrome'ni o'zi topadi (`MONTAJ_BROWSER` bilan almashtirsa bo'ladi).
- AI rasm API'si (`images.py ai`) hujjat bo'yicha yozilgan, lekin kalitsiz sinab ko'rilmagan:
  birinchi ishlatishda natijani tekshir, xato bersa `style.json` dagi `images.ai` va rasmiy
  hujjatni (ai.google.dev/gemini-api/docs/image-generation) solishtirib tuzat.

## Ko'rinish va ovoz sozlamalari (`style.json` yoki `brand.json`)

| Bo'lim | Nima | Qiymatlar |
|---|---|---|
| `look` | Rang ishlovi | `preset`: off, natural, warm, cool, punchy, film; qo'shimcha: `contrast`, `saturation`, `warmth`, `sharpen`, `vignette`, `grain`, `lut` (.cube) |
| `zoom` | Kesishdagi yaqinlashtirish | `punch_in`, `slow_push`, `enabled` |
| `audio.voice` | Nutqni tozalash | off, clean, denoise, strong |
| `audio.music_file` | Fon musiqa (nutq paytida o'zi pasayadi) | fayl yo'li, `music_volume_db` |
| `sfx` | Avtomatik ovoz effektlari | `enabled`, `on_big_word`, `on_element` |
| `cut.speed` | Butun video tezligi | 1.0 (o'zgarmaydi) … 1.15 |
| `progress_bar` | Tepadagi/pastdagi ko'rsatkich chiziq | `enabled`, `position`, `color` |
| `platform` | Xavfsiz zona va eksport talablari | `safe`, `max_duration`, `lufs` |

Ovozga tegishli tanlovni (voice, sfx, musiqa balandligi) agent o'zi hal qilmaydi: ikki variantni
render qilib, foydalanuvchi tinglab tanlaydi.

## Montaj sifati qoidalari

Render qilishdan oldin `--stills` bilan tekshiriladigan ro'yxat:

1. Birinchi 1.5 soniyada kuchli boshlanish: sarlavha yoki eng muhim gap, harakat darhol boshlansin.
2. Bir kadrda bitta asosiy narsa: brend rangi bir vaqtda ko'pi bilan bitta elementda.
3. Har 3 soniyada yangi narsa (kesish, zoom, element), lekin orada sokin joylar ham qolsin.
4. Matn xavfsiz zona ichida (stills rasmidagi ko'k ramka), yuzni va bir-birini yopmasin.
5. Subtitrda har bo'lakda bitta urg'u; hamma so'zni belgilab tashlama.
6. Elementlar gapga mos paytda chiqsin (so'z vaqtlari bo'yicha), aytilishidan oldin emas.
7. Oxirida aniq chaqiriq (oxirgi kadr yoki matn): bitta harakat.
8. Platforma tekshiruvi `[OK]` bo'lsin; `OGOH` chiqsa foydalanuvchiga ayt.

## Qoidalar

1. **`input/` dagi fayllarni hech qachon o'zgartirma, ko'chirma yoki o'chirma.** `samples/` ham shunday.
2. **Natija faqat `output/` ga**, oraliq fayllar faqat `temp/` ga yoziladi.
3. **Subtitr matnini videoga yozishdan oldin foydalanuvchiga ko'rsat va tasdiqlatib ol.**
   O'zbek tilida whisper xato qiladi. Matnni to'liq ko'rsat, "ishonchi past" so'zlarni alohida ayt.
   `--approve-subs` va `--approved` ni faqat foydalanuvchi "ha" degandan keyin ishlat.
   Kesilgan takrorlar ro'yxatini ham ko'rsat: noto'g'ri kesilgan bo'lsa `--no-repeats` bilan qayta ishla.
   `--stills` faqat ko'rish uchun, unga tasdiq kerak emas.
4. **Katta o'chirish yoki o'rnatishdan oldin so'ra.** (`temp/` ni tozalash, yangi dastur yoki
   kutubxona, model yuklash, `.venv` ni qayta yaratish.) Kutubxonalar faqat `.venv` ichiga o'rnatiladi.
5. **Skript xato bersa, sababini top va tuzat. Jim o'tib ketma**, xatoni yashirma, bosqichni
   tashlab ketma. Tuzata olmasang, nima bo'lganini va nimani sinaganingni foydalanuvchiga ayt.
6. Bilmagan narsangni taxmin qilma: buyruq yoki parametrni avval `--help` yoki koddan tekshir.
7. Foydalanuvchi boshlang'ich dasturchi: har qadamni oddiy o'zbek tilida, qisqa tushuntir.
8. Mualliflik huquqi: **musiqa, kino lavhasi va logotip** faqat foydalanuvchi bergan fayldan olinadi.
   Rasm va b-roll: foydalanuvchi bergan, `images.py` orqali topilgan (litsenziyasi yozib qo'yiladi),
   o'zing chizgan (HTML, belgi) yoki AI yaratgan bo'lishi mumkin. Boshqa yo'l bilan (brauzerdan
   saqlab, Google rasmlardan) rasm olinmaydi. Ishlatilgan manbalarni hisobotda ayt.
9. Stok rasm qidirish va yuklash uchun har safar so'rash shart emas (foydalanuvchi ruxsat bergan).
   Pullik narsa (AI rasm) birinchi marta ishlatilganda so'raladi.

## Agentlar bilan ishlash

- **Bir vaqtda faqat bitta agent ishlaydi** (Claude Code yoki Codex). Ikkalasi birga ishlamaydi.
- Ishni boshlashdan oldin `git status` va `git log --oneline -5` ni ko'r: oldingi agent nima qilgan.
- Skript, `style.json`, brend yoki shu faylni o'zgartirgach, **darhol `git commit` qil**.
- Skriptni o'zgartirgach `.venv\Scripts\python.exe scripts\selftest.py --no-whisper` ni ishga tushir.

## Chatdan montaj (watcher)

Claude chatda (Cowork) bu kompyuterda buyruq ishga tushira olmaydi, faqat papkaga fayl yoza va
o'qiy oladi. Shuning uchun `scripts/watcher.py` bor: foydalanuvchi `start_watcher.bat` ni ikki
marta bosib ochadi, oyna ochiq turguncha `jobs/inbox/` ga tushgan topshiriqlar bajariladi.

- Topshiriq: `jobs/inbox/<id>.json`. Natija: `jobs/done/<id>.json`, log: `jobs/logs/<id>.log`,
  kadrlar: `jobs/preview/<id>.jpg`. Watcher tirikligi: `jobs/watcher.json` (`alive_at`).
- Faqat tayyor amallar: `pipeline`, `analyze`, `selftest`, `preview`, `images`, `html`, `git_commit`,
  `install_deps`.
  Ixtiyoriy buyruq yo'q; har bir maydon tekshiriladi, noma'lum narsa rad etiladi.
  Yangi amal kerak bo'lsa, foydalanuvchidan so'rab `watcher.py` ga qo'shiladi.
- Misol: `{"action": "pipeline", "video": "input/video.mp4", "options": {"brand": "NOM"}}`.
  `video` loyihadan tashqaridagi to'liq yo'l ham bo'lishi mumkin (fayl faqat o'qiladi).
  `pipeline` sozlamalari: `brand`, `approve_subs`, `stills` (sonlar ro'yxati), `remove`, `trim`,
  `no_silence`, `no_repeats`, `no_cut`, `no_subs`, `force`, `language`, `model`, `silence_db`,
  `music`, `engine`, `script` (skript fayli), `no_script`.
- `images`: `{"action": "images", "video": "...", "options": {"search": "so'z", "kind": "photo", "n": 8,
  "orient": "portrait"}}` → natijada `candidates` va `preview` (nomzodlar varag'i). Keyin
  `{"options": {"pick": [3], "name": "tog"}}` yoki `{"options": {"ai": "tavsif", "name": "nom"}}`.
- `html`: `{"action": "html", "html": "temp/<nom>/gfx/karta.html", "output": "temp/<nom>/images/karta.png",
  "options": {"trim": true, "brand": "NOM"}}` (ikkala yo'l ham `temp/` ichida bo'lishi shart).
- Natijada: `subs_text` (matn), `words` (so'z va vaqtlari), `cuts` (kesilgan joylar),
  `low_confidence_words`, `brands`, `preview`, `output_info`, `notes` (joylashuv ogohlantirishlari),
  `checks` (platforma tekshiruvi), `script` (eslatmalar va farqlar), `credits` (rasm manbalari).
  Xuddi shu holat `temp/<nom>/result.json` ga ham yoziladi.
- Tartib: 1) `pipeline` → `need_approval`; 2) matnni foydalanuvchiga ko'rsatish, `subs.srt` ga
  tuzatish va belgilar, `elements.json` yozish; 3) `stills` bilan ko'rib tekshirish;
  4) foydalanuvchi tasdiqlagach `"approve_subs": true`.
- Claude Code va Codex watcher'siz, to'g'ridan-to'g'ri skriptlarni ishlatadi. Ular ishlayotganda
  watcher oynasi yopiq bo'lsin (bir vaqtda bitta agent).

## Claude Code'da ishlatish

- `/montaj input\video.mp4 NOM` — to'liq montaj. `/brend NOM` — yangi mijoz qo'shish.
  Manbasi `docs/claude_skills/`; ishlashi uchun `.claude/skills/` ga ko'chirilgan bo'lishi kerak
  (`docs/CLAUDE_CODE.md` dagi birinchi tekshiruv prompti buni qiladi). Ko'chirilmagan bo'lsa ham
  shu fayl va `docs/PLAYBOOK.md` bo'yicha oddiy so'rov bilan ishlayveradi.
- Ruxsatlar taklifi `docs/claude_settings.example.json` da (loyiha skriptlari so'rovsiz ishlaydi,
  `.env` o'qilmaydi, `input/` va `samples/` ga yozilmaydi). `.claude/settings.json` ga faqat
  foydalanuvchi rozi bo'lgach yoziladi. Batafsil: `docs/CLAUDE_CODE.md`.
- Codex shu faylni (`AGENTS.md`) va `docs/PLAYBOOK.md` ni o'qib xuddi shu ishni qiladi.

## Natijani tekshirish

Har renderdan keyin kutilgan natijani `ffprobe` bilan solishtir (`pipeline.py` va `compose.py`
buni o'zi ham qiladi va mos kelmasa xato beradi):

```powershell
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of default=nw=1 output\video_final.mp4
```

- **Davomiylik**: kesilgan video uzunligi (+ oxirgi kadr yoqilgan bo'lsa `endcard.duration`), ±0.5 s.
- **O'lcham**: `style.json` dagi `video.width` x `video.height` (1080x1920).
- **Ovoz**: ovoz oqimi bor (`codec_type=audio`).
- Ko'rinishni ham tekshir: `--stills` yoki watcher `preview` rasmida matn o'qiladimi, elementlar
  yuzni yoki bir-birini yopmayaptimi.

## Namuna videolardan uslub olish

1. Foydalanuvchi yoqqan uslubdagi videolarni `samples/` ga tashlaydi.
2. `.venv\Scripts\python.exe scripts\analyze_samples.py`
3. `temp/analysis/report.json` va har video uchun `temp/analysis/<nom>/sheet_*.jpg` ni ko'rib chiq.
4. Xulosani foydalanuvchiga ko'rsat. U rozi bo'lsa tegishli `brand.json` yoki `style.json` ga yoz.

## Texnik eslatmalar

- Muhit holati: `temp/setup_report.txt`. NVIDIA yo'q: `video.use_nvenc` `false`, whisper `cpu`/`int8`.
- Motion render: ffmpeg kadrlarni ochadi → Python (Pillow + OpenCV) har kadrga zoom va qatlamlarni
  chizadi → ffmpeg kodlaydi. Yangi element turi `scripts/elements.py` ga `Layer` sinfi qilib qo'shiladi.
- Gorizontal manba `video.fit: auto` da yuz atrofidan 9:16 qilib kesiladi; yuz topilmasa xira fon.
- HDR (telefon) videolari oddiy rangga o'tkaziladi (FFmpeg da zscale va tonemap bo'lsa).
- FFmpeg 7+ da uzun filtr grafigi `-/filter_complex fayl` orqali beriladi (eski
  `-filter_complex_script` FFmpeg 9 da olib tashlangan): `common.run_ffmpeg_graph`.
- Eski dvigatelda (ASS) Windows yo'lidagi `:` va `\` muammosi `common.filter_path` da hal qilingan.
- Remotion bu loyihada yo'q. Maxsus sahna kerak bo'lsa `docs/REMOTION_PROMPT.md` bo'yicha
  qo'shiladi va natijasi shaffof video sifatida ustiga qo'yiladi.
- Tashqi skill o'rnatishdan oldin `docs/SKILLS_AUDIT.md` ni o'qi va foydalanuvchidan so'ra.
