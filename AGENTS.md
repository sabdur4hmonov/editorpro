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
| `style/style.json` | Umumiy (standart) uslub qiymatlari. Brendsiz videolar shu bilan qilinadi. |
| `style/notes.md`, `brands/<nom>/notes.md` | **Foydalanuvchi fikrlari** (umumiy va brend bo'yicha). Har montajda o'qiladi. |
| `style/glossary.json`, `brands/<nom>/glossary.json` | Lug'at: whisper doim xato yozadigan so'zlar (avtomatik to'g'rilanadi). |
| `style/fonts/` | Shriftlar: Inter, Montserrat, Onest, Oswald, Unbounded, Playfair Display, Caveat. |
| `brands/<nom>/` | Brend profili: `brand.json`, `logo.png`, `notes.md`, `glossary.json`, `fonts/`, `music/`, `sfx/`. |
| `assets/sfx/` | Ovoz effektlari, 10 kategoriya papkasi (whoosh, swipe, pop, click, tick, hit, impact, riser, ding, typing): sintez v2 + import qilingan haqiqiy fayllar (`real__*`, gitga kirmaydi). `docs/SFX.md`. |
| `assets/models/` | Yuzni topish modeli (YuNet). |
| `assets/emoji/` | Emoji rasmlari (Noto, bitta zip ichida). |
| `assets/icons/` | 1500+ vektor belgi (Phosphor, MIT): `icon` elementi va `icons.py`. |
| `assets/html/` | HTML grafika namunasi (`shablon.html`). |
| `.env` | Maxfiy kalitlar (stok va AI rasm xizmatlari). Gitga kirmaydi, o'qib ko'rsatilmaydi. |
| `docs/claude_skills/` | Claude Code uchun `/montaj`, `/namuna`, `/brend`, `/transcribe-uz` buyruqlari (manba; `.claude/skills/` ga ko'chiriladi). |
| `docs/PLAYBOOK.md` | Montajor qo'llanmasi: qaror qabul qilish tartibi. **Har montajda o'qiladi.** |
| `docs/FORMATS.md`, `docs/formats/formats.json` | 8 video formati (Talking head, Interview, Kadr rakursli, Syudjetli, Obrazli, Savol javob, Tepa-past, Birinchi yuzdan): tanib olish, tuzilma, kesish, subtitr, grafika, b-roll, ovoz, xatolar, sifat nishonlari; mos namunalar 1-42. |
| `docs/SFX.md` | Ovoz effektlari: numpy sintez v2, sotib olinadigan to'plam tavsiyasi, `_inbox` dan import, litsenziya, git qoidasi. |
| `docs/TAKES.md` | Klip papkasi: yomon/takroriy dubllarni topish, eng yaxshisini so'z chegarasida kesish, tartib, `report.html`. |
| `docs/PROMO.md` | Restoran/mahsulot promo retsepti (namuna 20): ko'p klip, yorliq, narx, ovoz subtitri. `/promo` skilli. |
| `docs/NAMUNA_USLUBI.md` | Namuna videolar (`samples/`) uslubi: subtitr uslublari, animatsiyalar, elementlar. |
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

### Brendsiz video

Brend aytilmasa `--brand` yozilmaydi: `style/style.json` dagi umumiy uslub ishlatiladi (logotipsiz,
oxirgi kadrsiz), natija `output/` ga tushadi. Umumiy eslatmalar (`style/notes.md`) va umumiy lug'at
(`style/glossary.json`) baribir qo'llanadi. Brend haqida hech narsa o'ylab topilmaydi.

### Foydalanuvchi fikrlaridan o'rganish (majburiy)

Foydalanuvchi montaj haqida fikr bildirsa ("subtitr pastroq tursin", "bu rang yoqmadi", "effekt baland"):

1. Darhol yozib qo'y: `.venv\Scripts\python.exe scripts\feedback.py add "fikr" [--brand NOM] [--video yo'l]`.
   Faqat shu brendga tegishli bo'lsa `--brand`, hamma videoga tegishli bo'lsa brendsiz (umumiy).
2. Sozlamaga aylanadigan fikrni `brand.json` (yoki umumiy bo'lsa `style.json`) ga ham yoz: eslatma
   "nega"ni saqlaydi, sozlama esa uni har safar bajaradi.
3. Whisper bir so'zni ikkinchi marta xato yozsa, lug'atga qo'sh:
   `.venv\Scripts\python.exe scripts\glossary.py add "xato" "to'g'ri" [--brand NOM]`.
4. Har montaj boshida `pipeline.py` eslatmalarni ko'rsatadi: ularni o'qi va amal qil. Eslatmaga zid
   ish qilma; eslatmalar bir-biriga zid bo'lsa eng yangisi ustun, shubha bo'lsa so'ra.
5. O'zgarishdan keyin commit qil (eslatma va lug'at fayllari gitda saqlanadi).

Parallel montajda bu umumiy yozuvlar kechiktiriladi: fikr/lug'at/tajriba takliflarini faqat
o'z `temp/<video>/deferred_learning.md` faylingga yoz. Ikkala video tugab, boshqa agent
bo'sh bo'lgach, bitta agent feedback, glossary, AGENT_MEMORY va umumiy sozlamalarni yangilab commit qiladi.

### Yangi mijoz (brend) qo'shish

Boshqa agentning tugallanmagan video eslatmasi bo'lsa brend yaratma yoki tahrir qilma;
foydalanuvchiga aytib kut. Mavjud brend fayllari parallel montajda faqat o'qiladi.

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
| `pipeline.py VIDEO` | Hammasini ketma-ket bajaradi. VIDEO o'rniga klip papkasi berilsa avval `takes.py` (dubl tanlash), keyin `assemble.py` yig'adi; `clips.json` berilsa to'g'ridan yig'adi (`--no-takes`). |
| `takes.py PAPKA` | Klip papkasi: har klip transkripsiyasi, skript (`script.txt`) yoki skriptsiz gaplarga moslash, dubllarni baholash (sabab bilan), eng yaxshisini so'z chegarasida kesish, tartib, nutqsiz klip joyi taklifi; `temp/<nom>/clips.json`, `report.html`, `takes.json`; qo'lda: `takes.override.json`. `--verify` yig'ilgan videoni tekshiradi. |
| `promo_looks.py` | Promo uslub yo'nalishlari: `list`, `palette VIDEO` (kadr ranglari, accent taklifi), `apply NOM --style temp/<nom>/style.json --accent`, `record` (tarix, takrorni rad etadi). |
| `assemble.py PAPKA/clips.json` | Ko'p klipli montaj: speech/product/voiceover kliplarini tartib bilan bitta asosiy videoga yig'adi (style o'lchami va fps), `temp/<nom>/segments.json`; product oraliqlari jimlik deb kesilmaydi. |
| `transcribe.py VIDEO` | So'z-so'z vaqtli matn: `temp/<nom>/orig.words.json`, `orig.srt`. |
| `auto_cut.py VIDEO` | Jim joy, takror va qo'lda berilgan oraliqlarni kesadi (`--apply`). |
| `script_align.py` | Tayyor skript matnini nutq vaqtlariga tekislaydi (pipeline `--script` shuni chaqiradi). |
| `images.py` | Stok rasm/b-roll qidirish (`search`), yuklash (`pick`), AI rasm (`ai`), manbalar (`credits`). |
| `html_render.py` | HTML/CSS/SVG sahifani shaffof PNG qiladi (Edge/Chrome orqali): agent o'zi chizadi. |
| `icons.py` | Belgilarni qidirish (`find`), ko'rish (`sheet`), PNG qilish (`png`). |
| `cutout.py` | Rasmdan fonni olib tashlaydi (rembg: IS-Net standart, BiRefNet `--model birefnet-general --suffix cutb`); `--sheet` bilan tekshirish varag'i. BRIA modellari tijoratda taqiqlangan, rad etiladi. |
| `frames.py VIDEO` | Tayyor videodan kadrlar varag'i (natijani ko'rib tekshirish uchun). |
| `compose.py VIDEO` | Motion render: zoom, subtitr animatsiyasi, elementlar, brend, ovoz. |
| `subtitles.py`, `render.py` | Eski oddiy dvigatel (`captions.engine: ass`): ASS subtitr va render. |
| `audio_mix.py`, `make_sfx.py` | Ovozni yig'ish; eski (v1) effekt generatori. |
| `formats.py` | Xom videoni o'lchab formatni aniqlaydi (`detect`), uslub guruhi bilan bitta reja (`plan` → `temp/<nom>/edit_plan.json`, tasdiq xabari uchun 2 qator sabab), foydalanuvchi tuzatishini yozadi (`record` → `style/choice_history.json`), `guide` → docs/FORMATS.md. |
| `sfx_synth.py` | SFX sintez v2 (numpy): 10 kategoriya × 4 variant, bir xil balandlik, `_preview/`. |
| `sfx_import.py` | Sotib olingan to'plam: `assets/sfx/_inbox/` → konvert, jimlik kesish, normalizatsiya, kategoriya, litsenziya eslatmasi, indeks (`--shop`, `--license`). |
| `face.py VIDEO` | Yuz joylashuvini topadi. |
| `reactions.py VIDEO --words ...` | Nutqsiz baland joylarni topadi (kulgu, qarsak): effekt va emoji vaqti uchun. Taxmin, kadrdan tekshir. |
| `new_brand.py NOM` | Yangi brend papkasi va `brand.json` yaratadi. |
| `analyze_samples.py` | `samples/` tahlili: `temp/analysis/report.json`. |
| `compare_models.py` | Whisper modellarini bitta videoda yonma-yon solishtiradi (ball qo'ymaydi). |
| `apply_corrections.py` | Transkripsiya matnini tuzatadi, vaqtlarga tegmaydi (`words.fixed.json`). |
| `glossary.py` | Lug'at: `add "xato" "to'g'ri" [--brand NOM]`, `list`, `remove`. |
| `feedback.py` | Foydalanuvchi fikrlari: `add "matn" [--brand NOM]`, `show`. |
| `handoff.py` | `show` barcha tugallanmagan video egalarini ko'rsatadi. `set "matn" --video VIDEO --agent NOM`, `show --video VIDEO`, `clear --video VIDEO --agent NOM`. Loyiha eslatmasi uchun `--video` yozilmaydi. |
| `selftest.py`, `test_transcribe.py`, `check_env.py`, `bench_whisper.py` | Sinov, muhit tekshiruvi, whisper tezligi. |
| `watcher.py` | Chatdan kelgan topshiriqlarni bajaradi. |

Transkripsiya uchun `transcribe-uz` skilli (`docs/claude_skills/transcribe-uz/`) va
`scripts/transcribe.py` ishlatiladi. Model `style.json` ning `whisper` bo'limida; kompyuterda yo'q
model ruxsatsiz yuklanmaydi (chiqish kodi 4). Modellarni solishtirish: `scripts/compare_models.py`;
matnni vaqtga tegmasdan tuzatish: `scripts/apply_corrections.py`. Tasdiqlangan matn montajga
`pipeline.py VIDEO --words temp\<nom>\orig.words.fixed.json` bilan beriladi (whisper qayta ishlamaydi).
`transcribe.py` dan keyin pipeline'ni `--words` siz ishga tushirma: u `orig.words.json` ni qayta yozadi
va tuzatishlar raqami mos kelmay qoladi.

## Ish tartibi

0. **takes** (faqat klip papkasi) — dubllar tanlanadi, so'z chegarasida kesiladi, tartiblanadi va bitta videoga
   yig'iladi (`docs/TAKES.md`). Past ishonchli qarorlar (close call, qaror kerak, nutqsiz klip joyi, taxminiy tartib)
   tasdiq xabariga chiqadi, jim qabul qilinmaydi.
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
| `**so'z**` | katta va brend rangida (porlaydi) |
| `!!so'z!!` | juda katta va rangli (raqam, asosiy so'z) |
| `_so'z_` | faqat rangli, o'lchami o'zgarmaydi |
| `==so'z==`, `~~so'z~~` | marker: so'z ustidan rangli quti surtiladi (ikkinchisi qizil, rangi `captions.highlight2.color`; `captions.mark2_big: true` bo'lsa `~~so'z~~` asosiy ibora kabi katta va blok bo'ladi) |
| `\*` | oddiy yulduzcha: `**\*3 oyda**` ekranda `*3 oyda` |
| `{uslub,y=0.2}` (bo'lak boshida) | shu bo'lak boshqa uslubda va joyda: `{caps}`, `{heavy}`, `{single}` ... |

- **Bir gapda bitta asosiy ibora belgilanadi**; qolgan so'zlar o'zi kichik bo'lib, asosiy ibora ostiga
  uning kengligida joylashadi ("blok"). Urg'uli qisqa gap (9 so'zgacha) bitta bo'lak bo'lib qoladi,
  urg'usiz gap 3-4 so'zdan bo'linadi. Belgisiz bo'lakda raqamlar o'zi ajratiladi.
- Ma'no tashiydigan so'zni belgilang (raqam, natija, mahsulot nomi), bog'lovchini emas.
- Uslub `captions.preset`: `clean` (asosiy: namunalardagi kichik harfli zich uslub), `caps` (tor KATTA
  sarlavha), `heavy` (juda qalin so'z, harfma-harf), `italic`, `serif`, `single` (bir-ikki so'zdan),
  `marker` (kichik, chapda, marker bilan), `karaoke` (ovozli xabar sahnasi), `glow`, `box`,
  `promo` (katta kursiv porlovchi ibora/narx, kichik so'zlar ikki chetga: `sub_justify`), `vo` (ovoz ostidagi kichik qalin subtitr).
  Bo'lak belgisida (`{caps}` ...) uslub faylidagi `captions.font`, `accent` va `glow` saqlanadi.
  Joyi: `captions.position_y`. Atoqli otlar matnda qanday yozilsa shunday chiqadi (`Rus`, `SMM`).
- **Namunalardagidek video** uchun: `docs/NAMUNA_USLUBI.md` va `/namuna` skilli
  (`docs/claude_skills/namuna/`). Tuzatilgan matnda (`corrections.json`) belgilar va `{uslub}` ham
  yozilsa bo'ladi: `{uslub}` bilan boshlangan so'z yangi bo'lak boshlaydi.

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
| `image` | Rasm yoki kichik video ustma-qatlam (shaffof PNG: `cutout.py` - hoshiyasiz stiker) | `file`, `x`, `y`, `width`, `radius`, `anim` (pop/fade/none), `border` (oq hoshiya, 0.012), `border_color`, `rotate` (gradus), `wiggle` (tebranish, gradus), `push` (umri davomida sekin yaqinlashish, 0.06 = 6%) |
| `icon` | Vektor belgi (1500+), ostida ixtiyoriy yozuv | `name`, `x`, `y`, `size`, `bg` (none/circle/square/glass), `color`, `bg_color`, `style` (fill/bold), `text` |
| `broll` | Qo'shimcha kadr: `mode` `full` (to'liq ekran) yoki `split` (tepada gapiruvchi); ovozi o'chiq | `file`, `mode`, `fade`, `offset`, `focus_x` (9:16 kesish joyi), `bw` (oq-qora), `dim` (qoraytirish 0..1) |
| `zoom` | Qo'lda zoom | `scale`, `x`, `y`, `ease` |
| `sfx` | Ovoz effekti | `at`, `name`, `volume_db` |
| `callout` | Panel ichidagi matn: `style` `glass` (orqasi xira), `dark`, `accent` | `text`, `x`, `y`, `width`, `style` |
| `lower_third` | Ism va lavozim plashkasi | `name`, `role`, `x`, `y` |
| `emoji` | Katta emoji, sakrab chiqadi. `sticker: true` oq hoshiyali stiker | `emoji`, `x`, `y`, `size`, `sticker`, `rotate`, `wiggle` |
| `stage` | Videoni (yoki uning bir qismini) yumaloq kartochkaga oladi, orqasiga **yangi harakatli fon** chizadi | `crop [x0,y0,x1,y1]`, `width`, `y`, `radius`, `border`, `background`, `footer {text, from}`, `progress`, `punch [{at, scale}]`, `shake [{at, amp}]`, `flash [{at}]` |
| `label` | Mahsulot yorlig'i: shisha panel, kesilgan rasm, kichik yozuv ("1-set") va nom; `items` bo'yicha almashadi | `items[{at, name, kicker, image}]`, `x`, `y`, `width`, `size`, `image_size`, `glass` |
| `aside` | So'zlar odam yonida (yuzdan chap/o'ng), birin-ketin; qo'lyozma uchun `font: Caveat` | `items[{at, text, side, end, dy}]`, `spread`, `dy`, `size`, `font`, `color`, `stagger`, `margin` |
| `calendar` | Kalendar varag'i: oy, katta kun, kun atrofida halqa chiziladi | `month`, `day`, `label`, `mark_at`, `x`, `y`, `width`, `accent` |
| `panel` | Shisha panel: sarlavha + 1-4 qator pastdan chiqadi | `title`, `lines` yoki `text`, `x`, `y`, `width`, `tint`, `tint_alpha` |
| `logo_sting` | Logo prujina bilan chiqadi, ustidan yorug'lik o'tadi | `file` (yo'q bo'lsa style.logo), `x`, `y`, `width` |
| `mask_reveal` | Matn o'tish: rangli parda ustidagi matn ichidan video ochiladi | `text`, `color`, `size`, `y`, `hold` |
| `follow` | Obuna kartochkasi: doira (logotip, nom yoki belgi), @manzil, tugma bosiladi | `handle` (ixtiyoriy), `logo`, `name` yoki `icon`, `button`, `done`, `tap`, `x`, `y`, `size`, `color` |
| `scene` | To'liq ekranli chizilgan fon (ustiga matn, rasm, `voice` qo'yiladi) | `background {color1..4, pattern: dots/grid/none, rays, sparks}`, `fade` |
| `grade` | Vaqtincha oq-qora (`mode: bw`) yoki qoraytirish (`dim`) | `mode`, `amount`, `fade` |
| `flash` | Qisqa chaqnash (sahna almashganda) | `at`, `duration`, `color`, `amount` |
| `burst` | Emoji "otilib chiqadi" (kulgu, qarsak joyida) | `at`, `emoji` (bitta yoki ro'yxat), `count`, `duration`, `x [dan, gacha]` |
| `confetti` | Konfetti (yutuq, taqdirlash joyida) | `at`, `duration`, `count`, `origin` (sides/top) |

Har elementda `start` va `end` bor. Elementlarni matn mazmuniga qarab qo'ying: nima aytilayotgan
bo'lsa, o'sha paytda ko'rinsin (so'z vaqtlari `cut.words.json` da). Subtitr bilan ustma-ust
tushmasin: subtitr `position_y` atrofida turadi. Yo'q faylni o'ylab topma: rasm kerak bo'lsa
pastdagi "Rasm va grafika" bo'limi bo'yicha top yoki chiz. Render qilishdan oldin `--stills` bilan
ko'rib tekshir.

Logotip va oxirgi kadr elementlarga yozilmaydi: ular brenddan (`logo`, `endcard`) olinadi.

**Ijodiy joylashuv (`stage`)** fonni almashtirish kerak bo'lganda ishlatiladi: tayyor Reels (ichidagi
xira fon o'rniga), gorizontal video, sahna/komediya chiqishi. Kartochka ichidagi tasvir `crop` bilan
tanlanadi (asl kadrga nisbatan 0..1); tashqarisi chizilgan fon: sahna projektorlari, suzuvchi yorug'lik,
uchqunlar (`background`: `color1..4`, `rays`, `sparks`, `pattern` dots/none). `punch` - kulgili gap
tugaganda tasvir bir zum yaqinlashadi, `shake` - silkinadi, `flash` - fon chaqnaydi. `title`/`text` da
`stagger` (so'zlar birin-ketin) va `loop: "bob"` (sekin tebranish), `tracking` (harf oralig'i) bor.
`stage` bo'lsa subtitr kartochka ostida turadi (`captions.position_y`), sarlavha ustida. Namuna:
`brands/million/` va uning `temp/<nom>/elements.json` fayli.

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
| `audio.voice_margin_db` | Nutq bor joyda qo'shimchalar nutqdan kamida shuncha dB past | 10 (kattaroq = qo'shimchalar sokinroq) |
| `sfx` | Avtomatik ovoz effektlari (standart: yoqilgan) | `enabled`, `volume_db`, `duck`, `min_gap_sec`, `on_big_word`, `on_element` |
| `cut.speed` | Butun video tezligi | 1.0 (o'zgarmaydi) … 1.15 |
| `progress_bar` | Tepadagi/pastdagi ko'rsatkich chiziq | `enabled`, `position`, `color` |
| `platform` | Xavfsiz zona va eksport talablari | `safe`, `max_duration`, `lufs` |

**Nutq birinchi.** Asl ovoz alohida me'yorlanadi: musiqa yoki effekt qo'shilsa ham nutq balandligi
o'zgarmaydi. Musiqa va effektlar nutq paytida o'zi pasayadi, keyin o'lchanadi: natijada `Nutq
ustunligi` qatori chiqadi (qo'shimchalar nutqdan necha dB past). `OGOH` bo'lsa foydalanuvchiga ayt.
Agent ovozni eshita olmaydi: yoqdi-yoqmadi tanlovini (voice, effekt turi, musiqa balandligi) o'zi hal
qilmaydi, ikki variantni render qilib foydalanuvchiga tinglatadi va tanlovni eslatmaga yozadi.
Sahna chiqishi, intervyu, konsert kabi "tayyor ovozli" videolarda effektni kam ishlat yoki o'chir
(`sfx.enabled: false`), jim joylarni kesma (`--no-cut`): pauza va kulgu mazmunning bir qismi.

## Mustaqil ish (hamma montajlar)

- Ism, raqam, narx, taom/mahsulot nomi, taklif va chaqiriq faqat **nutqdan** (transkripsiya) yoki kadrda
  **aniq ko'ringan** yozuvdan (peshlavha, forma, quti, menyu, narx yorlig'i; `frames.py`) olinadi. Kadrdagi
  logotip faqat matn sifatida o'qiladi, kesib logotip fayli qilinmaydi.
- Hech narsa o'ylab topilmaydi. Shubhali narsa tasdiq xabarida `[?so'z]` va manbasi (klip + vaqt) bilan.
- Foydalanuvchidan faqat topib bo'lmaydigan narsa so'raladi, bir marta, tasdiq xabari ichida (masalan
  Instagram manzili). Musiqa va logotip fayli berilmasa: videoning o'z ovozi, logotipsiz.
- Klip papkasi (bir nechta dubl, skript bilan yoki skriptsiz): `docs/TAKES.md`. Kliplar tartibi, dubl tanlovi va nutqsiz
  klip joyi past ishonchli bo'lsa tasdiq xabarida; javob `temp/<nom>/takes.override.json` ga yoziladi.
- Promo (ko'p klipli restoran/mahsulot) uchun: `docs/PROMO.md`, `/promo` (Codex: `$promo`). Har promo o'z
  uslub yo'nalishida (`style/promo_looks.json`, `scripts/promo_looks.py`); oxirgi promo yo'nalishi takrorlanmaydi
  (`style/promo_history.json`).

## Montaj sifati qoidalari

### Format va ma’noli motion (solo finish)

- `docs/FORMATS.md` + eng yaqin family playbook, keyin `docs/QUALITY.md`: format va uslubni alohida tanla,
  ikkala sababni BITTA tasdiq xabariga yoz. Xom videoda aniqlagichni taxmin sifatida tekshir.
- `graphics_ideas.py ideas/apply/check`: taklifni to‘liq gapdan tekshir. Obyekt/miqdor/jarayon/dalil ma’no qo‘shsin;
  subtitrni takrorlovchi kartochka qo‘yma. Yangi jobda `quality.no_repeat: true` va full finalda `quality.enforce_final: true`.
- `group` bir pivotli fan/stack/spread va `hero` obyekt yo‘li/trail/blur mavjud (`docs/MOTION_DESIGN.md`).
  Sample asset/aytilmagan ro‘yxat/uydirma raqam bilan demo tuzma; raw footage bo‘lmagan rakurs/rolni tayyor deb da’vo qilma.
- Compose `face_safety.json`ni barcha faol overlay kadrlarda (exit/split ham) va `edit_plan.json` bo‘lsa
  `quality_gate.json/.md`ni yozadi. Unknown o‘lchov pass emas; fix_listni tuzat/o‘lcha. Native filmstrip va odam ko‘rigi shart.
- Stronger asosiy, subtle ikkinchi. Grafik/B-roll/format/takes user qarorlari mavjud history/feedback yo‘liga;
  parallel umumiy tarixga yozma. Token tejash: cached transcript/features/reportlarni qayta ishlat,
  faqat tanlangan family/format hujjatini o‘qi, kod o‘zgarsa tegishli sinovni ishlat; natijani taxmin qilma.

### Silliqlik (smoothness) — har renderda

- `video.fps: "source"`: chiqish = manba fps (25 -> 25). 25->30 takror kadr (har 6-kadr "tutilish") taqiqlangan.
  VFR/g'alati fps bir marta, kirishda eng yaqin standartga. Draft ham manba fps da (faqat o'lcham kichik).
- Kesish: `cut.crossfade_ms` 20 ms equal-power crossfade (nolga fade yo'q, xona shovqini uzilmaydi);
  oraliq ovoz ALAC (`cut.intermediate_audio`), AAC faqat oxirida bir marta. `audio.room_tone`: raqamli sukunat yo'q.
- Final: CRF 17 slow + `video.grain` 2 (banding). `motion.min_exit_frames` 5; subtitr kesishdan 2 kadr keyin;
  `subtitles.min_on_screen` 0.7 s / `max_cps` 20 qisqa bo'laklarni qo'shni bilan birlashtiradi (so'z vaqti o'zgarmaydi).
- `motion.variety_plan`: har bo'lak/element rol + energiya bo'yicha (imzo + 2-3 variant, ketma-ket <=3, bitta tur <=60%,
  seed bilan bir xil qayta render, brend tarixi). `look.match_cuts` ixtiyoriy (default o'chiq).
- Compose har renderdan keyin `temp/<nom>/smoothness.json` yozadi va `SMOOTH:` ogohlantirishlarini vaqt kodi bilan
  chiqaradi (takror kadr, kesishdagi ovoz teshigi/klik, subtitr kechikishi, drift titrashi, lint, bir xillik);
  quality gate'ga qatorlar qo'shiladi. Ogohlantirishni foydalanuvchiga ayt, "silliq" deb da'vo qilma: muharrir hal qiladi.
- Muharrir vaqt kodli izohi: `feedback.py add "matn" --at 12.3,40 --editor NOM [--brand B]`; takrorlanadigan
  bo'lsa `--rule motion.min_exit_frames=6` → `style/rules.json` yoki `brands/<b>/rules.json`, keyingi render amal qiladi
  (tasdiqlangan per-video stilga tegmaydi).
- Tasdiqlangan per-video stillar (raqamli fps) aynan avvalgidek chiziladi; texnik qayta render faqat yangi nom bilan (`_v25`).

### Motion va ovoz dalili (Sprint 1)

- `docs/MOTION.md` ni o'qi: umumiy `motion`, brend `style.motion`, per-video `motion_override`.
  Davomiylik/easing/stagger shu yerdan; `motion_choice.json` draft/final tanlovini saqlaydi.
- `review_tools.py filmstrip` bilan timecoded yaqin kadrlarni tekshir, o'zgarishda `ab` orqali
  bir xil vaqtdagi before/afterni ko'rsat. Bu foydalanuvchining haqiqiy ritm tasdig'i o'rnini bosmaydi.
- o‘/g‘/tutuq belgisi harf animatsiyasida ajralmaydi; glyph audit warningni yashirma.
  Caveat'da U+02BB yo'q, mavjud boshqa shriftni tanla yoki foydalanuvchiga ayt.
- Compose subtle/stronger mix, audio cue sheet va markerli waveform beradi. Ikkalasini chatda
  tinglat; agent eshitganini da'vo qilmaydi. Nutq margin qoidasi saqlanadi.
- Parallel umumiy motion tarixi yozilmaydi (`history_deferred`); o'z choice/deferred learningni
  saqla, yakunda bitta idle agent tarixni yangilaydi.
- Yangi kompyuter: `docs/NEW_LAPTOP.md`. Hardware auto + CPU fallback; capability GPU sinovi emas.
  Bu kompyuterda GPU sinovi yo'q, yangi install/download avval foydalanuvchi ruxsati bilan.

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

- Ikkala agentning doimiy tajribasi `docs/AGENT_MEMORY.md` da: **har sessiya boshida o'qi**.
  Parallel montajdagi tajribani o'z `temp/<video>/deferred_learning.md` faylingga yoz;
  oxirida boshqa agent bo'sh bo'lganda bitta agent jurnalga ko'chiradi. Texnik ishda jurnalni
  faqat boshqa agentning tugallanmagan videosi yo'q paytda yoz. Taxmin va dalilni farqlagin.
- Har montajda `docs/EDIT_QUALITY.md` bo'yicha reja va `temp/<nom>/review.md` tayyorla.
  Tekshirilmagan sifat yoki tasdiqlanmagan ovoz tanlovini "o'tdi" deb yozma.
- Sessiya boshida `scripts/sync_skills.py --check` ni `.venv` Python bilan ishlat.
  Nusxalar eskirgan bo'lsa va boshqa agentning tugallanmagan videosi bo'lmasa `--apply`: manba `docs/claude_skills/`, Claude nusxasi
  `.claude/skills/`, Codex nusxasi `.agents/skills/`. Nusxalarni alohida tahrir qilma.
- Ikkala agent uchun MCP va foydalanish tartibi: `docs/AGENT_SETUP.md`.
- Kengaytirilgan montaj vositalari: `docs/STUDIO.md`. Compose avtomatik preflight qiladi;
  ijodiy ogohlantirishlarni reja bilan tekshir. Draft subtitr tasdig'ini chetlab o'tmaydi.
  Batch faqat matn bosqichigacha. Har montajda stills/draft/finalni shu chatda ko'rsat.

- **Claude Code va Codex ikki TURLI videoda parallel ishlashi mumkin.** Har agent faqat
  o'z videosi, `temp/<video>/` va shu papkadagi to'liq `style.json` nusxasi bilan ishlaydi;
  buyruqlarga `--style temp/<video>/style.json` beriladi. Asl video/samples faqat o'qiladi,
  natija output/ da har video uchun alohida nomga yoziladi. Bir xil temp nomiga tushadigan
  videolarni parallel bermang; ikkinchi agent boshqa agentning papkasi yoki eslatmasiga tegmaydi.
  PowerShell'da agent o'z terminalida `$env:MONTAJ_AGENT='claude'` yoki `'codex'` deb belgilaydi.
- **Ishni boshlashdan oldin** `.venv\Scripts\python.exe scripts\handoff.py show` ni ishga tushir: oldingi
  agent qoldirgan eslatma (`HOLAT.md`), band belgisi, `temp/` dagi oxirgi ishlar holati va git ko'rinadi.
  `show` har tugallanmagan video va egasini sanaydi. Faqat o'zingga topshirilgan videoni
  davom ettir yoki `handoff.py set "Boshlandi ..." --video VIDEO --agent NOM` bilan egala.
  Boshqa agent egallagan videoni olmang. `show --video VIDEO` o'z eslatmangni to'liq ko'rsatadi.
- **Ish davomida holatni yozib bor** (limit ogohlantirmasdan tugaydi, oxirida yozishga ulgurmaysan):
  `.venv\Scripts\python.exe scripts\handoff.py set "..." --video VIDEO --agent claude|codex`. Qachon: matn tasdiqqa
  yuborilganda, foydalanuvchi javob berganda, `elements.json` yozilganda, render boshlanishidan oldin va
  tugagach. Nima yoziladi: qaysi video va brend, nima qilindi, foydalanuvchidan nima kutilmoqda (uning
  javobi bo'lsa so'zma-so'z), keyingi qadamning aniq buyrug'i. Eslatma `temp/<video>/HOLAT.md` da.
  Video tugasa `handoff.py clear --video VIDEO --agent NOM`: status done, matn/tasdiqlar saqlanadi.
  Loyiha `HOLAT.md` faqat umumiy setup/qarorlar uchun; parallel montajda ustidan yozma.
- Foydalanuvchi tasdiqlari (subtitr matni, yuklashga ruxsat) eslatmada yozilgan bo'lsagina kuchda.
  Video tasdig'i o'z video eslatmasiga, umumiy ruxsat loyiha HOLAT.md ga yoziladi.
  Yozilmagan yoki boshqa videoga tegishli tasdiqni taxmin qilma: qayta so'ra.
- Og'ir ishlar (`pipeline`, `compose`, `transcribe`, `compare_models`) bir vaqtda bittadan ishlaydi:
  ikkinchisi egani ko'rsatib FIFO navbatda kutadi (`temp/.busy.json`, `.busy.queue/`).
  Standart limit 7200 soniya (2 soat); `$env:MONTAJ_BUSY_TIMEOUT='900'` kabi sekundlarda
  o'zgartiriladi. Limit tugasa aniq xato, ish boshlanmaydi. Heartbeat 5s, eski belgi 25s dan
  keyin to'siq bo'lmaydi; belgilarni qo'lda o'chirma. compare_models ga `--out-dir
  temp/<video>/compare` ber: natija boshqa video papkasiga yozilmasin.
- Ishni boshlashdan oldin `git status` va `git log --oneline -5` ni ko'r: oldingi agent nima qilgan.
- **Boshqa agentning tugallanmagan video eslatmasi bor ekan** `scripts/`, `style/style.json`,
  `brands/`, `docs/`, skilllar va umumiy fayllarni tahrir qilma; selftest ham ishlatma.
  Kodni tuzatish kerak bo'lsa, o'z ishingni to'xtat va foydalanuvchiga ayt.
- **Parallel montajda git commit yo'q.** Feedback, glossary va AGENT_MEMORY oxirida,
  boshqa agent bo'sh bo'lganda bitta agent tomonidan yoziladi. Shu yakuniy bosqichdan
  keyin commit qil. Branch almashish va merge ham parallel montajda qilinmaydi.
- Umumiy texnik o'zgarishlar faqat boshqa agentning tugallanmagan videosi yo'q paytda:
  `.venv\Scripts\python.exe scripts\selftest.py --no-whisper` va tegishli testlar, keyin commit.

## Chatdan montaj (watcher)

Claude chatda (Cowork) bu kompyuterda buyruq ishga tushira olmaydi, faqat papkaga fayl yoza va
o'qiy oladi. Shuning uchun `scripts/watcher.py` bor: foydalanuvchi `start_watcher.bat` ni ikki
marta bosib ochadi, oyna ochiq turguncha `jobs/inbox/` ga tushgan topshiriqlar bajariladi.

- Topshiriq: `jobs/inbox/<id>.json`. Natija: `jobs/done/<id>.json`, log: `jobs/logs/<id>.log`,
  kadrlar: `jobs/preview/<id>.jpg`. Watcher tirikligi: `jobs/watcher.json` (`alive_at`).
- Faqat tayyor amallar: `pipeline`, `transcribe`, `model`, `compare`, `corrections`, `frames`, `analyze`,
  `selftest`, `preview`, `images`, `html`, `git`, `git_commit`, `install_deps`.
  Ixtiyoriy buyruq yo'q; har bir maydon tekshiriladi, noma'lum narsa rad etiladi.
  Yangi amal kerak bo'lsa, foydalanuvchidan so'rab `watcher.py` ga qo'shiladi.
- Misol: `{"action": "pipeline", "video": "input/video.mp4", "options": {"brand": "NOM"}}`.
  `video` loyihadan tashqaridagi to'liq yo'l ham bo'lishi mumkin (fayl faqat o'qiladi).
  `pipeline` sozlamalari: `brand`, `approve_subs`, `stills` (sonlar ro'yxati), `remove`, `trim`,
  `no_silence`, `no_repeats`, `no_cut`, `no_subs`, `force`, `language`, `model`, `silence_db`,
  `music`, `engine`, `script` (skript fayli), `no_script`, `words` (temp/ ichidagi words.fixed.json),
  `no_glossary`, `elements` (temp/ ichidagi boshqa elementlar fayli), `output` (natija nomi, kengaytmasiz:
  `output/<nom>.mp4`; ikki variantni yonma-yon saqlash uchun, masalan effektli va effektsiz).
- `watcher.py` yangilansa watcher o'zi qayta ishga tushadi (navbat bo'sh bo'lganda). `jobs/watcher.json`
  dagi `version` yangi ekanini tekshir; eski bo'lsa foydalanuvchi oynani yopib qayta ochadi.
- `transcribe`: `{"action": "transcribe", "video": "...", "options": {"model": "...", "language": "uz",
  "allow_download": false}}` → `words` ([raqam, start, end, so'z, ishonch]), `timing_issues`.
  `model`: `{"options": {"name": "...", "allow_download": false}}` → model bormi, hajmi qancha.
  `compare`: `{"video": "...", "options": {"models": ["small", "..."], "seconds": 60}}` → `table`, `models`.
  Model yo'q bo'lsa natija `need_download` (hech narsa yuklanmaydi). `allow_download: true` faqat
  foydalanuvchi shu hajmga rozi bo'lgach yoziladi.
- `corrections`: `{"words": "temp/<nom>/orig.words.json", "corrections": "temp/<nom>/corrections.json"}` →
  `text` (tuzatilgan matn), `needs_review`. `{"options": {"list": true}}` so'zlarni raqami bilan chiqaradi.
- `frames`: `{"video": "...", "options": {"n": 8}}` yoki `{"at": [2.0, 2.1]}` → `preview` (kadrlar varag'i).
- `git`: `{"options": {"op": "status"}}` (branch, o'zgarishlar, log) yoki `{"op": "branch", "name": "yangi-nom"}`
  (yangi branch ochib, unga o'tadi). Merge, reset, o'chirish yo'q: ularni foydalanuvchi o'zi qiladi.
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

- `/montaj input\video.mp4 NOM` — to'liq montaj. `/namuna input\video.mp4 NOM` — namunalardagidek montaj.
  Video o'rniga klip papkasi (`input\papka`, ixtiyoriy `script.txt`) berilsa avval dubl tanlash (`docs/TAKES.md`);
  Codex'da `$montaj input\papka`, `$namuna input\papka`.
  `/promo input\papka` — ko'p klipli restoran/mahsulot promo, mustaqil (`docs/PROMO.md`). Codex'da `$promo input\papka`.
  `/brend NOM` — yangi mijoz qo'shish. `/transcribe-uz video` — matn va tuzatish.
  Manbasi `docs/claude_skills/`; ishlashi uchun `.claude/skills/` ga ko'chirilgan bo'lishi kerak
  (`docs/CLAUDE_CODE.md` dagi birinchi tekshiruv prompti buni qiladi). Ko'chirilmagan bo'lsa ham
  shu fayl va `docs/PLAYBOOK.md` bo'yicha oddiy so'rov bilan ishlayveradi.
- Ruxsatlar taklifi `docs/claude_settings.example.json` da (loyiha skriptlari so'rovsiz ishlaydi,
  `.env` o'qilmaydi, `input/` va `samples/` ga yozilmaydi). `.claude/settings.json` ga faqat
  foydalanuvchi rozi bo'lgach yoziladi. Batafsil: `docs/CLAUDE_CODE.md`.
- Codex shu faylni (`AGENTS.md`) va `docs/PLAYBOOK.md` ni o'qib xuddi shu ishni qiladi. O'rnatish va navbat
  almashish promptlari: `docs/CODEX.md`.

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

- Sprint 2: `docs/BROLL_DYNAMICS.md` va `docs/EXPORT.md`ni o'qi. B-roll momentlari matndan
  leksik rank qilinadi, semantic moslik agent tomonidan kadrdan tekshiriladi. Har momentga
  3 ustun, hamma sheet bir tasdiq xabarida; user raqam/auto/none. Crop/colour/text proxy
  logo yoki watermark yo'qligini isbotlamaydi. Kuchsiz yoki unchecked candidate ishlatilmaydi.
- B-roll accepted/rejected aynan sabab bilan per-video `broll_history.json`; umumiy
  `style/broll_history.json`ga `sync-history` faqat barcha agent idle bo'lgach. Tanlanmagan rejected emas.
- `dynamics` WPS/RMS/word pause va structure heuristicdan boshqariladi; labelni tekshir/override qil.
  Caption intensity, zoom/visual-cut, automatic element/SFX density, background speed style keylarida.
  Matn/so'z vaqti va speech cut o'zgarmaydi; explicit element o'chirilmaydi. Energy/filmstrip/A/B
  va paired audio cue sheets chatda. Stronger default — bu yangi video ovozi tasdiqlandi degani emas.
- Editor eksportida XML/SRT/MOV/stem qayta parse qilinadi; GUI import alohida, tekshirilmagan deb ayt.
  FCP7 XML, integer NDF sequence fps, speed=1; source FPS farqida CFR working copy,
  original seconds + frame grid yaxlitlash manifestda. Drop-frame/retime aniq xato.
  Base motion/context raster, original source cut timeline va editable caption alohida.

- Muhit holati: `temp/setup_report.txt`. NVIDIA yo'q: hardware/whisper `auto` CPU/int8 tanlaydi;
  eski per-video cpu/int8 ham ishlaydi. Yangi laptop tartibi: `docs/NEW_LAPTOP.md`.
- Motion render: ffmpeg kadrlarni ochadi → Python (Pillow + OpenCV) har kadrga zoom va qatlamlarni
  chizadi → ffmpeg kodlaydi. Yangi element turi `scripts/elements.py` ga `Layer` sinfi qilib qo'shiladi.
- Gorizontal manba `video.fit: auto` da yuz atrofidan 9:16 qilib kesiladi; yuz topilmasa xira fon.
- HDR (telefon) videolari oddiy rangga o'tkaziladi (FFmpeg da zscale va tonemap bo'lsa).
- FFmpeg 7+ da uzun filtr grafigi `-/filter_complex fayl` orqali beriladi (eski
  `-filter_complex_script` FFmpeg 9 da olib tashlangan): `common.run_ffmpeg_graph`.
- Eski dvigatelda (ASS) Windows yo'lidagi `:` va `\` muammosi `common.filter_path` da hal qilingan.
- Remotion o'rnatilgan: `--engine remotion` opt-in timeline; eski native motion/ASS va shaffof overlay yo'li saqlanadi. `docs/how-to-use.md` va `docs/MOTION_LIMITATIONS.md`.
- Tashqi skill o'rnatishdan oldin `docs/SKILLS_AUDIT.md` ni o'qi va foydalanuvchidan so'ra.

## 41 namuna va motion design (solo style study)

- Montaj boshida eng yaqin family `docs/style_dna/` dan: A explainer, B1 paper/document,
  B2 creator, C interview, D commercial (promo/showcase/vlog subtype). Guruh va dalilli sabab ONE approvalda.
- `sample_groups.py select/apply` faqat per-video style; brand va user feedback ustun.
- `docs/MOTION_DESIGN.md` maydonlarni tekshir: trajectory/pivot, card/canvas, active state,
  single-source layout_morph, outline/flat relief. Native filmstrips bilan timing/geometryni tekshir.
- Sokin intervyu uchun majburiy har3s grafika yo‘q. Ovoz va motion didi foydalanuvchi ko‘rigi.
- Tadqiqot manbalari/chegaralari `docs/STYLE_STUDY/`. ≥3 distinct hashes pattern, kamrog‘i observation;
  easing/font/isolated SFX/true3D noma’lum bo‘lsa null va honest limitation.
- Claude limit holatida bu sessiyada foydalanuvchi Codex solo shared build/tests/commitni aniq ruxsat berdi;
  bu kelajakdagi parallel ish cheklovini bekor qilmaydi. Oldingi video notes saqlandi.


## Remotion timeline: ikkala agent uchun

- `docs/style-analysis.md` barcha mavjud namunalar inventari; `docs/how-to-use.md` buyruqlari.
  Eski FFmpeg/Whisper kesish, matn tasdiqi, native motion/ASS saqlanadi. Yangi engine opt-in;
  tasdiqlangan videoni avtomatik qayta dizayn qilma. Yangi supported talking-head jobda
  `--engine remotion` tanla; legacy/unsupported grafik bo‘lsa native yo‘l va uning QA sini ishlat.
- Remotion har position/scale/opacity/rotation interpolationni `remotion/src/easing.mjs`
  yoki `motion.ts` orqali o'tkazadi. Linear faqat progress/time mapping kabi constant-speed ishlar.
  Pixel koordinatasini integerga yaxlitlama; frame/indexni yaxlitlash bundan alohida.
- Brand `style.remotion` / per-video `remotion`: soft/snappy/bouncy, enter/exit 0.2-0.5s;
  footage va text umumiy transition clock, outgoing exit davomida incoming enter.
  Whisper word start/end saqlanadi, butun gap layouti oldindan band qilinadi. o'/g'/apostrophe ajralmaydi.
- CPU: concurrency2 (ko'pi bilan3), default30fps;60fps va2x faqat o'lchangan render vaqti bilan.
  Native source-fps qoidasi qoladi; Remotion mismatched source uchun blend/mci/reject tanlovi aniq.
  Oddiy25->30 duplicate fps conversion yo'q; blend ghost/MCI warp inson ko'rigida tekshiriladi.
- Har yangi render `temp/<job>/qa/<export>/report.md`: real DOM/safe area/word onset/jitter,
  final frame PTS/count/hold proxy/audio va har3-kadr transition sheets. Unknown pass emas.
  Caption/text geometry xatolari to'xtaydi; max3 xavfsiz auto repair, check yumshatilmaydi.
  Inson ritm, ovoz didi, yuz va semantic sifati filmstrip/draftda tasdiqlaydi; agent "silliq" deb taxmin qilmaydi.
- Local fonts + character fallback; `remotion/motion_choice.json` seed/preset/cycle saqlaydi.
  Unsupported native graphic aniq xato; silent drop yo'q. Custom remotion_scene face geometry unverified: production standalone overlay/native yo‘li.
- Cache faqat o'z job/remotion ichida; active segment saqlanadi, eski segmentlar2GiB budgetga tozalanadi.
  Staging/concat/audio scratch muvaffaqiyatdan keyin o'chadi;30GiB free disk warning. Boshqa jobga tegma.
