# Professional montaj: har ish uchun sifat tartibi

PLAYBOOK va NAMUNA_USLUBI asosiy ijodiy qo'llanma. Bu ro'yxat har bir videoda qaror,
tekshiruv va foydalanuvchi bahosini iz qoldirib saqlaydi. Ko'p effekt yaxshi montaj degani emas.

## 1. Reja — temp/<job>/plan.md

PLAYBOOK jadvaliga qo'shib yoz: maqsad, tomoshabin, asosiy fikr, platforma, brend,
foydalanuvchi bergan namuna, hook va yakuniy chaqiriq. Komediya pauzasini avtomatik kesma.
Har sahnada nima aytiladi, nima ko'rinadi, nega kerak va kesilgan videodagi vaqtini belgilagin.
Bor namuna bilan shrift/urg'u/rang/joylashuvni solishtir; namuna yo'q bo'lsa o'ylab topma.

## 2. Matn va vaqt

Matnni to'liq ko'rsat, ishonchi past so'zlar va takror kesilgan joylarni alohida ko'rsat.
HOLAT.md da aniq tasdiq bo'lmaguncha videoga subtitrni yozma. So'z vaqtlarini o'zgartirma.
Grafika aytilayotgan fikr vaqtida chiqsin, har subtitr bo'lagida bitta urg'u bo'lsin.

## 3. Kadr ko'rigi

Har hook, grafika va oddiy subtitrning o'rtasidan stills ol. O'tishlarda uchta yaqin kadr ol.
Xavfsiz zona, yuz, matn ustma-ust tushishi, o'qilish, rang va namuna bilan moslikni tekshir.
Muammo topilsa tuzat va qayta ko'r. Animatsiya ravonligini foydalanuvchi videoda tekshiradi.

## 4. Yakuniy ko'rik — temp/<job>/review.md

Quyidagi shablonni to'ldir. Har band: **o'tdi / xato / kutilmoqda / tegishli emas**, dalil bilan.
Tekshirilmagan bandni o'tdi deb yozma. Xato bo'lsa faylni tayyor deb e'lon qilma.

```markdown
# Yakuniy ko'rik
Video / brend:
Agent / sana:
Reja va namuna:
Subtitr tasdiqi: HOLAT.md dagi foydalanuvchi javobi, sana va tasdiqlangan matn fayli
Matn va kesish: ishonchi past so'zlar, takrorlar, hal etilmagan joylar
Hook va yakun: maqsadga mosligi
Kadr ko'rigi: stills fayli + tekshirilgan soniyalar + topilgan/tuzatilgan muammolar
Namuna bilan moslik: shrift, joy, rang, urg'u; qolgan farqlar
Eksport: ffprobe davomiylik/o'lcham/FPS/audio dalili, Tekshiruv va Platforma qatorlari
Ovoz: Nutq ustunligi qatori, ikki variant yo'li, foydalanuvchi tanlovi yoki kutilmoqda
Harakat: foydalanuvchi videoni ko'rganmi yoki kutilmoqda
Manbalar: credits.txt yoki tashqi material ishlatilmagan
Natija: tayyor / foydalanuvchi ko'rigi kutilmoqda / tuzatish kerak
O'rganilgan: AGENT_MEMORY.md yozuvi; feedback/glossary o'zgarishi; keyingi tavsiya
```

Hisobot uchun yangi maydonlarni elements.json/brand.json ga qo'shma: bu erkin Markdown.
Eksport qiymatlari mavjud style/brenddan olinadi; FPS yoki platforma talabini taxmin qilma.
Ovoz tanlovi va harakat ko'rigi agent tomonidan eshitilgan/ko'rilgan deb yozilmaydi.
