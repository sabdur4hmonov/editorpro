# Ma’noli grafika va sifat dalili

Montajni avval format (`docs/FORMATS.md`), keyin uslub oilasi (`docs/style_dna/`) bo‘yicha rejalashtir.
Bu ikki o‘q: savol-javob tuzilmasi intervyu kadri yoki tepa-past joylashuvi bilan birga bo‘lishi mumkin.
Aniqlagich tayyor 8 misolda 7/8: bu xom videoda kafolatlangan aniqlik emas. Costume/role/POVni agent tekshiradi.

## Bir reja, bir tasdiq

1. `scripts/formats.py plan VIDEO --words WORDS [--format FORMAT --group GROUP --reason DALIL]`:
   `edit_plan.json`. Ambiguous natijada formatni kadrdan tanla; `FORMAT:` va `USLUB:` sabablarini BITTA tasdiq xabariga qo‘sh.
2. `scripts/graphics_ideas.py ideas VIDEO --words WORDS --subs SUBS`: `graphics_ideas.json`.
   Lexical takliflar to‘liq gap ma’nosini tushunmaydi. Taqqoslash/ketma-ketlik/ro‘yxat haqiqatan aytilganmi, tekshir.
   Har urg‘uda obyekt, miqdor, taqqoslash, jarayon yoki dalil tanla. Tibbiy natija yoki sababni o‘ylab topma.
3. Tekshirilgan IDlargina `graphics_ideas.py apply VIDEO --ids 1,3` bilan qo‘shiladi.
   Joylashuv taxminiy; yuz monitori va stills bilan tuzat. O‘z HTML/MIT icon/berilgan/litsenziyali rasm ishlat.
4. Per-video style: `quality.no_repeat: true`. Tekshiruv `studio.preflight` va compose’da.
   Yorliqning kamida 80% ma’noli so‘zi shu vaqtdagi subtitrda bo‘lsa xato. Apostrof variantlari va oddiy suffixlar tenglashtiriladi.
   `hide_captions: true` **faqat element oralig‘ida** asosiy subtitrni yashiradi; asl matn/vaqtlar o‘zgarmaydi.
   Zarur takror uchun `allow_repeat: true` + mazmunli `repeat_reason`; oddiy dekoratsiyani oqlash uchun emas.
5. `graphics_ideas.py record VIDEO --id N --verdict approved|rejected --note "foydalanuvchi javobi"`.
   Boshqa ochiq note bo‘lsa tarix o‘z jobida; keyingi shu format ranki local + umumiy tarixni o‘qiydi.
   `formats.py record` faqat barcha agent idle paytda (umumiy style/choice_history.json); bu format va uslubga ham ta’sir qiladi.
   B-roll/takesning mavjud tarix/feedback yo‘li saqlanadi. Agent o‘z tanlovini user approval deb yozmaydi.

## Yuzni vaqt davomida tekshirish

Compose HAR BIR faol overlay kadrini YuNet bilan tekshiradi. Fit/zoom/split/stage chizilgandan so‘ng yuz topiladi,
grafikadan oldingi va keyingi kengaytirilgan face box solishtiriladi. Chiqish/transition ham tekshiriladi.
Flash o‘zi overlay xatosi hisoblanmaydi, ammo undan oldingi grafika tekshiriladi. Hisobot `face_safety.json`.
3% standart yuqori chegara per-video `quality.max_face_cover` bilan boshqariladi.

Bu pixel-change o‘lchovi alpha overlapning matematik isboti emas: 40 darajadan kichik kontrast, model topmagan yuz,
profil yoki haqiqiy segmentation xatosi qolishi mumkin. YuNet yo‘q → xato; yuz topilmadi → UNVERIFIED;
unknown hech qachon sifat gate’da pass emas. Still/draftni odam tekshiradi.

## Pro-quality gate

Compose jobida `edit_plan.json` bo‘lsa `quality_gate.json/.md` avtomatik chiqadi. Alohida:

```powershell
.venv\Scripts\python.exe scripts\quality_gate.py temp\video\cut.mp4 --style temp\video\style.json --plan temp\video\edit_plan.json --result temp\video\render_result.json --cuts temp\video\verified_cuts.json
```

`verified_cuts.json`: `{"times":[2.4,5.9]}` — faqat tekshirilgan editorial kesishlar; kamera zoomi overlay kesishi emas.
Pipeline qo‘llagan native `cuts.json` (`keep`, `speed`) ham o‘qiladi: kesishlar output vaqtiga o‘tkaziladi.
Render natijasi pipeline resultidagi metadata bilan adashtirilmasin: `checks`, `audio`, `face_safety`, `integrated_lufs` kerak.
Quality nishonlari family DNA + per-video rejaning `quality_targets` birlashmasidan keladi; brand/user niyati ustun.
Qisqa texnika sinovini to‘liq hikoya zichligi bilan tenglashtirma. Nishonni ball ko‘tarish uchun o‘zgartirma.

O‘lchanadi: editorial cuts/min, top-level graphics/min va oralig‘i (group ichidagi stagger alohida event_times), grafikadan holi eng uzun vaqt,
birinchi yozuv vaqti, haqiqiy fitted caption line size/H va x/y, konfiguratsiyadagi entrance sekundlari×30,
yuzning barcha overlay kadrlaridagi yopilishi, eksport tekshiruvlari, nutq margin, loudnormdan integrated LUFS.
Caption size font balandligi, ink bbox emas. Timing konfiguratsiya; harakatni native filmstrip bilan alohida tekshir.
Original shrift/easing noma’lum bo‘lsa aynan match deyilmaydi.

Score faqat ma’lum mezonlar ulushi, yonida coverage N/M ko‘rsatiladi. Unknown va failed → fix_list.
Added graphic yo‘q bo‘lsa uning entrance’i N/A, lekin yuz/ovoz noma’lumligi baribir unknown; sokin formatni keraksiz grafika bilan to‘ldirma.
`quality.enforce_final: true` qo‘yilganda full render fix_list bo‘lsa final sifatida qabul qilinmaydi
(review eksporti saqlanadi, skript xato beradi); draftni tuzatish uchun chiqarish mumkin.
Yakun: o‘lchovlar pass + foydalanuvchining draft/ovoz ko‘rigi. Avtomatik ball professional didni tasdiqlamaydi.
Eski tasdiqlangan joblar o‘zgarmasin: yangi qat’iy no_repeat/enforce_final per-video opt-in.
