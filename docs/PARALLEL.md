# Ikki agent — ikki turli video

Claude Code va Codex bitta checkout'da ikki **turli** videoning reja, matn va grafikalarini
bir paytda tayyorlaydi. CPU ishlari FIFO navbatda bittadan bajariladi. Watcher yopiq bo'lsin.
Har agent AGENTS.md, PLAYBOOK, NAMUNA_USLUBI, AGENT_MEMORY va tegishli notes'ni o'qiydi.

## Boshlash: foydalanuvchi yuboradigan matnlar

Quyidagi video yo'llarini haqiqiy, turli nomli videolarga almashtiring. Brend bo'lsa uning
nomini ham yozing; brendsiz deb yozilsa umumiy uslub olinadi.

Claude Code'ga:

> Parallel montaj: input/video_a.mp4, brendsiz. Sen claude egasisan. Avval handoff.py show.
> Faqat shu video va temp/video_a/ bilan ishlagin, per-video style.json yaratib --style bilan
> ishlatgin. AGENTS.md dagi parallel qoidalarni bajar. Matn, reja, rasmlar va stillsni bitta
> xabarda ko'rsat; tasdiqni shu video eslatmasiga yoz. Codex papkasiga tegma, umumiy fayllarni
> o'zgartirma, selftest va commit qilma. Og'ir ish navbatda kutishi mumkin.

Codex'ga:

> Parallel montaj: input/video_b.mp4, brendsiz. Sen codex egasisan. Avval handoff.py show.
> Faqat shu video va temp/video_b/ bilan ishlagin, per-video style.json yaratib --style bilan
> ishlatgin. AGENTS.md dagi parallel qoidalarni bajar. Matn, reja, rasmlar va stillsni bitta
> xabarda ko'rsat; tasdiqni shu video eslatmasiga yoz. Claude papkasiga tegma, umumiy fayllarni
> o'zgartirma, selftest va commit qilma. Og'ir ish navbatda kutishi mumkin.

## Agent bajaradigan tekshirilgan buyruqlar

`<video>` asl fayl yo'li, `<job>` uning `common.slugify` bilan olingan nomi. Masalan
`doktor 2.mp4` -> `doktor_2`. Ikki manba bitta slug/temp nomiga tushmasin. `--video` handoff
uchun asl videoni bildiradi; asl fayl temp ichida bo'lsa ham shu nomdan job papkasi olinadi.

```powershell
$env:MONTAJ_AGENT = 'claude' # Codex o'z terminalida 'codex'
.venv\Scripts\python.exe scripts\handoff.py show
.venv\Scripts\python.exe scripts\handoff.py set "Boshlandi; video/brend, keyingi qadam..." --video input\video_a.mp4 --agent claude
Copy-Item -LiteralPath style\style.json -Destination temp\video_a\style.json
.venv\Scripts\python.exe scripts\pipeline.py input\video_a.mp4 --style temp\video_a\style.json
```

Copy-Item faqat **yangi** style fayli uchun: mavjud per-video sozlamalarni ustidan yozma.
Mavjud brend uchun pipeline/compose `--brand NOM` ham oladi. `load_style` avval per-video
style'ni, keyin brand.json style override'larini qo'llaydi; brendni parallel tahrir qilma.
Subtitr tasdig'idan oldingi chiqish kodi 3 odatiy. O'zbek nutqda skilldagi tekshirilgan
model qoidasiga amal qil; yangi model ruxsatsiz yuklanmaydi.

```powershell
.venv\Scripts\python.exe scripts\handoff.py show --video input\video_a.mp4
.venv\Scripts\python.exe scripts\handoff.py set "Matn yuborildi; fayl..., tasdiq kutilmoqda; keyingi buyruq..." --video input\video_a.mp4 --agent claude
.venv\Scripts\python.exe scripts\frames.py input\video_a.mp4 -o temp\video_a\source_frames.jpg --n 12
.venv\Scripts\python.exe scripts\compare_models.py input\video_a.mp4 --style temp\video_a\style.json --out-dir temp\video_a\compare --models small,yuldashev222/whisper-small-uz-v1-ct2
```

`frames.py` ning standart temp/frames/ papkasini ishlatma: `-o` bilan o'z papkangni ber.
`studio.py compare` / `cover` / `suggest` hisobot va yordamchi fayllariga ham o'z papkangdagi
`--out` yo'lni ber; final muqova output/ da faqat o'z videong nomi bilan. Umumiy batch/
analysis papkalarini parallel ishda ishlatma. Subtitr, rasm, HTML, audio variant, review va
deferred_learning faqat o'z video papkangda. Input va samples faqat o'qiladi.
HTML grafika HTML'i ham shu video papkasida bo'lsin; html_render.py --style o'z style faylingni
oladi, vaqtinchalik sahifa/PNG va brauzer profilini temp/<video>/.html_render/ da saqlaydi.

Tasdiqni foydalanuvchi so'zma-so'z javobi, tasdiqlangan matn fayli va video bilan `set --video`
orqali yoz. Faqat shundan so'ng `pipeline ... --words temp/<job>/orig.words.fixed.json
--style temp/<job>/style.json --draft --approve-subs`; draft tasdiqlangach final. Har render
boshi/oxiri ham shu eslatmada. Output nomlarini ikki video orasida bir xil qilib bermang.

## Qulf va kutish

MONTAJ_AGENT faqat o'z terminalingga tegishli; tizim bo'ylab umumiy muhitga yozma.
`temp/.busy.json` hozirgi CPU egasi, `.busy.queue/*.json` navbat chiptalari.
OS fayl qulfi claim/heartbeat/release poygasini himoyalaydi; heartbeat 5s, stale 25s.
Eski jarayonning release'i yangi egani o'chirmaydi. Yangi buzilgan/yarim JSON darhol
stale hisoblanmaydi: faylning yoshiga qarab himoyalanadi.

Kutish limiti standart 7200 soniya. Shu terminalda o'zgartirish:

```powershell
$env:MONTAJ_BUSY_TIMEOUT = '900'
```

Navbat egani va limitni chiqaradi, egasi almashsa yoki 15s o'tsa yangilaydi. Limit tugasa
ish boshlanmaydi, o'z chipta tozalanadi, haqiqiy egaga tegilmaydi. Keyin shu buyruqni qayta
ishga tushirish mumkin. Lock/queue fayllarini agent qo'lda o'chirmaydi.

## Tugatish va umumiy o'rganish

```powershell
.venv\Scripts\python.exe scripts\handoff.py clear --video input\video_a.mp4 --agent claude
```

Bu note'ni o'chirmaydi: status done bo'ladi, matn/tasdiqlar saqlanadi. `show` barcha
unfinished note'larni egasi bilan sanaydi; `show --video` tugagan note'ni ham o'qiydi.
Begona agent set/clear qila olmaydi. Limitda qolgan unfinished video avvalgi egasida qoladi;
agent almashtirish kerak bo'lsa foydalanuvchiga ayt, begona note'ni o'zing qayta yozma.

Boshqa agentning unfinished videosi bor paytda scripts/, style/style.json, brands/, docs/
yoki skills tahriri va selftest taqiqlangan. Kod muammosi bo'lsa agent to'xtab foydalanuvchiga
aytadi. Parallel montajda commit/branch almashish/merge yo'q. Feedback, glossary, AGENT_MEMORY
takliflari har agentning deferred_learning.md faylida turadi. Ikkala video tugab boshqa agent
idle bo'lgach, bitta agent ularni umumiy fayllarga ko'chirib, tegishli sinovlarni o'tkazib commit qiladi.
Loyiha HOLAT.md faqat umumiy state uchun; parallel montajda uning ustidan yozilmaydi.
