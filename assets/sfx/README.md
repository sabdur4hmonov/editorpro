# SFX kutubxonasi

Kategoriya papkalari: whoosh, pop, click, hit, riser, ding, swipe, typing, tick, impact.
Mavjud tovushlar scripts/make_sfx.py yordamida sintez qilingan. synth01 — eski loyiha WAV'i,
synth02 — shu ovozning balandroq pitch varianti. Bu haqiqiy field recording emas.
Har WAV yonida LICENSE.txt va credit.json bor. Eski 8 tekis fayl moslik uchun saqlangan.

7 kategoriya to'ldirilgan: whoosh, pop, click, riser, ding, swipe, tick (ikkitadan variant).
Yetishmayotgan alohida kategoriyalar: **hit, typing, impact**. Hit/impact vaqtincha thud.wav'dan
foydalanadi; typing avtomatik qo'yilmaydi. Haqiqiy yozib olingan variantlar barcha 10 kategoriyada yo'q.

Pixabay rasmiy API: https://pixabay.com/api/docs/ — image/video endpointlar; sound effects endpointi
hujjatlashtirilmagan. Brauzerdan avtomatik SFX yuklash yo'li qo'shilmagan.
Foydalanuvchi kerakli WAV/MP3ni va litsenziya matnini o'zi beradi: faylga original sahifa URL'i,
muallif, litsenziya va yuklangan sana qo'shilsin. Faqat tijoratda ruxsatli fayllar.
Bir kategoriyaga kamida 2 turli yozuv: immediate repeat'ni oldini olish mumkin bo'ladi.

Sintez kutubxonasini yaratish (mavjud fayllar --force'siz almashtirilmaydi):
`.venv\Scripts\python.exe scripts\make_sfx.py --library`.
Ovozni agent eshitmaydi: subtle/stronger tanlovni foydalanuvchi qiladi.
