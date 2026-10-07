# Kengaytirilgan montaj vositalari — Claude va Codex uchun

Million videosi foydalanuvchi tomonidan bekor qilingan. Uni qayta boshlamang va tasdiq so'ramang.
Quyidagi buyruqlarda `<video>`, `<job>`, `<brend>` haqiqiy qiymatga almashtiriladi.
Har yangi video oldidan HOLAT.md, AGENT_MEMORY, PLAYBOOK, NAMUNA_USLUBI va notes o'qiladi.

## 1. Namuna bilan kadrma-kadr taqqoslash

```powershell
.venv\Scripts\python.exe scripts\studio.py compare "samples\sample 7.mp4" "output\video_draft.mp4" --at 0.8,2.0,2.08,2.2 --reference-at 1.2,3.0,3.08,3.2
```

`--n 8` teng oraliqdagi kadrlar; `--at` aniq vaqtlar, 120 tagacha. Vaqtlar bir-biriga mos
bo'lmasa namuna va biznikining `--reference-at` / `--at` vaqtlarini agent alohida belgilaydi.
Avtomatik vaqtlar davomiylik ulushi bo'yicha moslanadi, nutq mazmuni bo'yicha emas.
PNG/JPG rasmlar ham taqqoslanadi. JSON, HTML slayder, juft PNG va kontakt varaq hosil bo'ladi.

Agent matnning to'rt chegarasini kadrdan o'lchab `--box x0,y0,x1,y1` va
`--reference-box x0,y0,x1,y1` beradi (0..1). Hisobotda hudud kengligi/balandligi, yorqinlik,
kontrast, to'yinganlik va sariq piksel ulushi bor. Sariq kiyim/fon ham pikselga kiradi;
bu OCR yoki shriftni avtomatik aniqlash emas. Agent tanlangan hududni ko'rib tasdiqlaydi.
Yangi namunani avval `analyze_samples.py --no-whisper` bilan umumiy tahlil qilish mumkin.
Raqamlar yoki ko'rik asosida brend/uslub o'zgarishi foydalanuvchidan tasdiqlanadi.

## 2. Tez qoralama

```powershell
.venv\Scripts\python.exe scripts\pipeline.py <video> --brand <brend> --words temp\<job>\orig.words.fixed.json --draft --approve-subs
```

Bu buyruq faqat oldin ko'rsatilgan va HOLAT.md da tasdiqlangan matn uchun. Qoralama ham
subtitr tasdig'ini chetlab o'tmaydi. Brendsiz bo'lsa `--brand` yozilmaydi.
`style.json` ning `preview` bo'limi: 360x640 (9:16), 15 fps, ultrafast. Final 1080x1920/30 fps
sozlamalari o'zgarmaydi. Natija `_draft.mp4`, "QORALAMA" yozuvi bilan; final alohida `_final.mp4`.
To'g'ridan-to'g'ri `compose.py ... --draft --approved` ham ishlaydi.
Tezlik video, grafika va audio sarfiga bog'liq; `temp/studio_test/benchmark.json` sinov o'lchovi.

## 3. Render oldidan tekshiruv

Compose har safar `preflight.json` yozadi. Alohida tekshirish:

```powershell
.venv\Scripts\python.exe scripts\studio.py preflight temp\<job>\cut.mp4 --subs temp\<job>\subs.srt --elements temp\<job>\elements.json --brand <brend>
```

Vaqtlar, element turi, preset, fayllar va zarur model xatolari renderni to'xtatadi.
Ilmoq, vizual ritm, rangli urg'ular zichligi/ustma-ust tushishi, yakun va xavfsiz zona
ogohlantiriladi. Mezoni `style.json` ning `quality` bo'limida. Element end'i mavjud dvigatel
qoidasi bilan video oxirida kesiladi. Sokin sahnani ataylab qoldirish mumkin: rejada izohlang.
Kesish/avtomatik zoom barcha ijodiy hodisalarni bu evristika orqali aniqlash kafolatlanmaydi.
Xato yo'qligi mazmun, ovoz, yuz va harakat sifatini avtomatik tasdiqlamaydi.

## 4. Odam orqasida yozuv

```json
{"type":"title", "start":0, "end":1.8, "text":"*SARLAVHA*", "x":0.5, "y":0.18, "behind_person":true}
```

Model birinchi navbatda asl kadrdagi odamni ajratadi, matn chiziladi, so'ng odam yana ustiga
qaytariladi. Subtitr va boshqa oddiy grafikalar oldinda qoladi. Faqat text/title uchun.
Hozir stage/scene/broll/grade bilan bir sahnada ishlatilmaydi — fonning koordinatalari farq qiladi.
PPHumanSeg 6 163 938 bayt, SHA256 tekshiriladi, Apache-2.0; yangi kutubxona kerak emas.
Model 192x192 da hisoblaydi: soch, qo'l va xira chegaralarni haqiqiy kadrda tekshiring.
Har faol kadrda CPU hisoblaydi; faqat kerakli sarlavha oralig'ida ishlating.

```powershell
.venv\Scripts\python.exe scripts\person_mask.py
# Faqat yangi kompyuterda, shu hajmga foydalanuvchi rozi bo'lgach:
.venv\Scripts\python.exe scripts\person_mask.py --download --allow-download
```

Model manbasi va litsenziyasi assets/models/pphumanseg.credit.json / pphumanseg-LICENSE.txt da.

## 5. Urg'u takliflari — tasdiqdan oldin

```powershell
.venv\Scripts\python.exe scripts\studio.py suggest temp\<job>\orig.words.json --keyword sifat --keyword natija
```

`emphasis.suggested.json` faqat taklif: raqam + birlik yoki agent bergan kalit so'z oq katta
ibora sifatida belgilanadi. Har bo'lakda bitta ibora; rang avtomatik ko'paytirilmaydi.
Ishonchi past/needs_review matn va avvaldan belgilangan bo'laklar o'tkaziladi. Ma'noli iborani
agent tanlaydi; hech qanday "AI biladi" tasdiqi yo'q. Agent faylni ko'rib, kerakli takliflarni
qabul qilgach mavjud `apply_corrections.py` bilan alohida tuzatilgan so'zlar fayliga qo'llaydi.
Asl matn va vaqtlar o'zgarmaydi; keyin matn to'liq foydalanuvchiga ko'rsatiladi.

## 6. Yangi grafikalar

```json
{"elements": [
  {"type":"handnote", "start":1, "end":2.8, "text":"qisqa izoh", "x":0.3, "y":0.32, "font":"Caveat"},
  {"type":"arrow", "start":1, "end":2.8, "points":[[0.2,0.25],[0.6,0.2],[0.7,0.4]], "draw_sec":0.6, "color":"#FFFFFF"},
  {"type":"phone", "start":3, "end":5, "name":"Berilgan ism", "handle":"@berilgan_manzil", "bio":"Berilgan izoh", "width":0.3, "y":0.32},
  {"type":"profile", "start":5, "end":7, "name":"Berilgan ism", "handle":"@berilgan_manzil", "avatar":"temp/job/images/avatar.png", "width":0.5, "y":0.3},
  {"type":"stat", "start":7, "end":9, "value":85, "suffix":"%", "ring":true, "label":"Videoda aytilgan natija"}
]}
```

Namuna qiymatlari haqiqiy montajda o'ylab topilmaydi: ism/manzil/raqam mijoz yoki nutqdan.
Phone/profile'da `image` bo'lsa mijozning haqiqiy skrinshoti ko'rsatiladi; aks holda faqat
berilgan name/handle/bio/avatar chiziladi. Obunachi soni va boshqa statistika uydirilmaydi.
Arrow: 3 nuqta egri chiziq (start/control/end), 2 yoki 4..32 nuqta siniq yo'l.
Handnote qo'lyozma shrift va so'zlarning chiqishi; haqiqiy qalam izi/3D simulyatsiyasi emas.
Stat + ring avvaldan bor edi; qayta yaratilmagan.

## 7. Muqova

```powershell
.venv\Scripts\python.exe scripts\studio.py cover <video> --title "Tasdiqlangan sarlavha" --at 2.4 --brand <brend>
```

Brendning shrift/rang/logotipi bilan 1080x1920 PNG; standart nom `_cover.png`.
Kadrni va faktga mos qisqa sarlavhani agent tanlaydi, foydalanuvchiga chatda ko'rsatadi.

## 8. Bir nechta videoni matn bosqichiga tayyorlash

```powershell
.venv\Scripts\python.exe scripts\studio.py batch input --brand <brend> --resume
```

Faqat papkaning bevosita ichidagi videolar ketma-ket ishlanadi; render yo'q.
`--no-cut` komediya/sahna videolari uchun. Model yo'q yoki skript xato bersa navbat to'xtaydi,
model yuklanmaydi va xato yashirilmaydi. Har video uchun subs.srt, JSON holat va log saqlanadi.
`--resume` faqat shu navbatdagi, manbasi/sozlamasi o'zgarmagan tayyor matnni saqlaydi.
Bir xil ish nomiga tushadigan ikki video yoki boshqa manbaga tegishli temp papkasi rad etiladi.
Bekor qilingan videolar bo'lgan umumiy papkani navbatga bermang; faqat tanlangan faol topshiriqlar.
Har matn alohida ko'rsatiladi va HOLAT.md ga tasdiqi alohida yoziladi. Navbatning tugashi tasdiq emas.

## 9. Sinov va chatda ko'rish

`test_studio.py` sintetik video bilan to'liq namuna uslub renderini va qoralamani, manba
saqlanishini, matn navbatini, modelni, yangi grafikalarni va himoyalarni tekshiradi.
Bu haqiqiy gapiruvchi-odam videosining sifat sinovi o'rnini bosmaydi: u foydalanuvchi video bergach.
Har montajda stills, draft va final shu chatda mutlaq fayl yo'li bilan ko'rsatiladi.
Ovoz va harakat bo'yicha foydalanuvchi bahosi review.md, feedback va umumiy tajribada saqlanadi.
