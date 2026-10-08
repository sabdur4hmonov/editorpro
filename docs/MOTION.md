# Motion va ovoz — Sprint 1

Claude va Codex uchun bir xil qo'llanma. Agent kadrni baholaydi; harakatni yoki ovozni
eshitib/ko'rib tasdiqladim demaydi. Filmstrip easingning kadrlar bo'yicha siljishini ko'rsatadi;
haqiqiy ritm va ovoz didini foydalanuvchi draftdan baholaydi. Matn tasdig'i o'z video HOLAT.md da bo'lsin.

## 1. Harakat tili

`style/style.json -> motion`, brendda `brand.json -> style.motion`, videoda to'liq
`temp/<video>/style.json`. Brend qiymatlari load_style paytida qo'llanadi; videoga alohida
o'zgartirish kerak bo'lsa nusxaga `motion_override: {"speed": "fast"}` kabi faqat kerakli
qiymatlarni yoz: bu bo'lim brend motion'dan keyin qo'llanadi. `--style`ga shu to'liq nusxani ber.
Umumiy/brend fayllarini parallel montajda tahrir qilma.

| Maydon | Vazifa |
|---|---|
| enabled | true yangi tizim; false eski animatsiyalar |
| speed / scales | fast 0.75, medium 1, slow 1.3: barcha davomiylik ko'paytmasi |
| durations_ms | caption 260, exit 160, sticker 360, title 300, label 300, follow 420, transition 240, punch 300 |
| easing.enter / exit | snappy (tez to'xtaydi), soft (yumshoq), spring (prujina), overshoot (joyidan o'tib qaytadi) |
| spring | omega 12, zeta 0.62; 0 < zeta < 1 |
| stagger | word_ms 35, letter_ms 24, max_total_ms 180 |
| pairs | entrance -> exit: scale_down / slide_out / blur / fade / mask_down |
| blur | enabled false CPU standarti; true fast pop/slide uchun max_px 3 arzon xiralik |
| variety / choice | avtomatik kombinatsiya yoki aniq enter/sub/emphasis |

Caption, title, sticker/icon/emoji, label, follow va b-roll fade umumiy davomiylik/easingdan
foydalanadi. Elementdagi aniq `anim`, `fade`, `stagger` va cue taglari ustun; eski presetlar ham mavjud.
Follow bosishidagi kichik harakatlar umumiy follow/punch/exit davomiyligiga bog'langan.
Qisqa elementlarda kirish/chiqish vaqtlarining ustma-ust tushishi cheklanadi.

Olti yangi kirish: `spring_pop`, `slide_overshoot`, `scale_blur`, `typewriter`, `mask_up`,
`letter_cascade`. To'rtta urg'u: `scale_punch`, `colour_sweep`, `underline_draw`, `box_wipe`.
`typewriter` so'zni harfma-harf ko'rsatadi; o‘/g‘ va tutuq belgisi ajralmaydi. So'z nutq vaqtida
boshlanadi; nutq va subtitle vaqtlari o'zgarmaydi. Yangi chiqish cue tugashidan OLDIN tugaydi,
keyingi cue ustidan eski matn qolmaydi. Har so'zga alohida rang yoki hamma urg'uni bir vaqtda qo'yma.

`motion_choice.json` video papkasida tanlov/seed/fingerprintni saqlaydi: draft/final bir xil.
Idle holatda brand bo'yicha `temp/.motion_history/` oxirgi kombinatsiyani takrorlamaydi.
Parallel holatda umumiy tarix yozilmaydi, `history_deferred: true`; yakunda bitta idle agent
oxirgi tugagan videoning tanlovini tarixga va deferred learningga o'tkazadi.
Parallel ikki job mustaqil seed oladi; tarixga umumiy yozish kechiktirilgani uchun ularning
kombinatsiyasi mutlaqo farqli bo'lishiga kafolat yo'q. Kerak bo'lsa o'z `choice`ni aniq belgila.

`glyph_audit.py` barcha shrift cmaplarini tekshiradi; renderer ishlatilgan shriftni ham tekshiradi.
Motion renderer yetishmagan belgini baseline bo'yicha mavjud boshqa shrift bilan chizadi
(avval Inter); qolgan harflar asl shriftda qoladi. Hech qaysi shrift qoplamasa aniq warning.
2026-10-08: 9 shriftdan Caveat'da `ʻ` (U+02BB) yo'q; Inter/Montserrat/Onest/Oswald/Playfair/Unbounded
o‘ g‘ ʻ ni qoplaydi. Ogohlantirishni yashirma: boshqa mavjud shriftni tanla yoki foydalanuvchiga ayt.
Yangi shrift ruxsatsiz yuklanmaydi.

## 2. Effektlar va ikki mix

`assets/sfx/<category>/` va har fayl yonida `.LICENSE.txt`, `.credit.json`.
Kategoriya: whoosh, pop, click, hit, riser, ding, swipe, typing, tick, impact.
Hozirgi yozuvlar sintez qilingan, haqiqiy yozib olingan effekt emas. 7 kategoriyada 2 variant;
hit/impact eski thud'ga qaytadi, typing yo'q. Haqiqiy ovozlar bilan to'ldirish: `assets/sfx/README.md`.
Brendning `sfx/<category>/` papkasi umumiydan avval tanlanadi; eski tekis fayllar ham ishlaydi.

Pixabay [rasmiy API hujjatida](https://pixabay.com/api/docs/) rasm va video endpointlari bor;
SFX endpointi hujjatlashtirilmagan. Saytdagi Sound Effects bo'limini API deb qabul qilma.
SFX yuklash avtomatizatsiyasi qo'shilmadi; foydalanuvchi fayl va litsenziyasini o'zi beradi.
`sfx_library.py` mahalliy fayllarni SHA256/duration/source/licence bilan indekslaydi.
Litsenziya/source sidecarlari bor real fayllar sintezdan ustun; manbasi yo'q real fayl
UNVERIFIED deb yoziladi va avtomatik tanlanmaydi. 2026-10-09 inventar: 22 sintez, 0 real.
B-roll/sticker/follow voqealari hero captionlardan oldin zichlik joylarini oladi;
limit hamma 10s oynalarda saqlanadi. `sfx.event_priority` bilan tartibni almashtirish mumkin.

HTML PNG hajmi 0.5s barqaror va rasm to'liq ochiladigan bo'lsin, browser qaytgach 10s limit.
Xatoda bir marta yangi profil bilan retry; har jarayon 120s chegaralangan. Aniq warning va
video `.html_render/browser_attempts.jsonl`da UTC vaqt, urinish, code, timeout va stderr tail bor.

`sfx.event_map`: hero -> pop, sticker -> whoosh, broll_in -> swipe, title -> whoosh,
label -> click, number -> ding, follow_tap -> click. Avtomatik effekt 3 kadr oldin boshlanadi
(`lead_frames` 2 yoki 3); video boshi sababli manfiy vaqt 0 ga cheklanadi va haqiqiy lead yoziladi.
`min_gap_sec` 1.5 va `max_per_10_sec` 3 zichlikni cheklaydi. Seedli variant tasodifiy tanlanadi,
kamida ikki variant bo'lsa ketma-ket bir fayl qaytarilmaydi. Qo'lda yozilgan `sfx` vaqti o'zgarmaydi.

Standart `sfx.mixes: {"subtle": -18, "stronger": -2}`, `profile: "stronger"` (foydalanuvchi tanlovi 2026-10-09).
Bu bazaviy `volume_db` ustiga qo'shiladigan dB; barcha effektga, qo'lda berilganga ham qo'llanadi.
`compose` vizualni bir marta kodlaydi, keyin ikkinchi mixni shu video oqimiga biriktiradi:
`<nom>.mp4` va `<nom>_stronger.mp4`. `audio_mixes/<output stem>/<profile>/`da audio,
`audio_cues.json`, `audio_cues.md`, `audio_waveform.png`; `mixes.json`da natija yo'llari.
SFX o'chiq bo'lsa juft effekt mix yaratilmaydi. Musiqa faqat foydalanuvchi faylidan.

Nutq alohida me'yorlanadi, ducking va mavjud `audio.voice_margin_db` saqlanadi. Cue sheetda
fayl/time, vizual time/lead, dB gain, real stem peak/LUFS, speech-above-stem RMS va global
pasaytirish bor. LUFS butun timeline bo'yicha; qisqa effekt juda past yoki null bo'lishi mumkin.
Stem limiterdan OLDIN o'lchanadi; yakuniy WAVning meter'i ham alohida bor. Busning 5-percentil
nutq ustunligi boshqa o'lchov: RMS bilan teng deb aytma. Kuchli mix ham nutqni bosmasligi shart.
Ikki variantni chatda tinglat, tanlovni foydalanuvchi aytadi; natijani o'z HOLAT.mdga yoz.

## 3. Tekshirish vositalari

Loyiha ildizida `.venv` Python bilan (CLIlar kod/--help orqali tekshirilgan):

```powershell
.venv\Scripts\python.exe scripts\review_tools.py filmstrip output\video_final.mp4 --start 2 --end 2.7 --n 12 -o temp\video\motion.jpg
.venv\Scripts\python.exe scripts\review_tools.py ab temp\video\before.mp4 output\video_final.mp4 --end 12 --at 1,2,4,6,10 -o temp\video\ab.jpg
.venv\Scripts\python.exe scripts\review_tools.py audio output\video_final.mp4 --events temp\video\audio_mixes\video_final\subtle\audio_cues.json -o temp\video\waveform.png
.venv\Scripts\python.exe scripts\glyph_audit.py
.venv\Scripts\python.exe scripts\test_motion.py
```

Filmstrip: istalgan oralig'ida 2..120 kadr, har birida soniya. `--at` aniq vaqtlar (1..120).
A/B ikki videoda aynan bir vaqtda kadr oladi, out-of-range xato beradi; sidecar JSON dalilni saqlaydi.
Waveform markerlari voqea boshlanishi; agent ovozni eshitganini bildirmaydi.

## 4. Sprint 1 A/B dalili

`temp/sprint1/before.mp4` eski 31560ed kodi bilan avval renderlangan; keyin kod o'zgartirilgan.
`doktor_1/cut.mp4`ning 0..12s bo'lagi, 1080x1920/30fps. Matn, vaqtlar, kadr va elementlar bir xil;
original job fayllari SHA256 manifest bilan himoyalangan. Bu texnik A/B, yangi kontent montaji emas.
Boshlanishdagi 6.3s sokin oraliq va 12s kesmada CTA yo'qligi ataylab saqlangan, preflight ogohlantiradi.
`after_full.mp4`, `after_draft.mp4` + stronger mixlar, A/B sheet va ikkala caption/sticker filmstrip
shu papkada. Draft 304x540/30fps; full 1080x1920/30fps. Filmstrip stillsdan olinadi, harakat didi
va audio yoqqani faqat foydalanuvchi tomonidan baholanadi.

```powershell
# Faqat saqlangan original baseline mavjud bo'lsa; before qayta yaratilmaydi.
.venv\Scripts\python.exe scripts\sprint1_demo.py
# Faqat taqqoslash varaqlarini qayta olish:
.venv\Scripts\python.exe scripts\sprint1_demo.py --reports-only
```
