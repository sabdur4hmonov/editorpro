# Klip papkasi: dubllarni tanlash (takes)

Foydalanuvchi papkaga ~10 ta qisqa klip tashlaydi (tartibi aralash, nomlari hech narsa anglatmasligi mumkin),
ba'zan skript ham beradi. Tizim yomon va takroriy urinishlarni topadi, har gapning eng yaxshi dublini so'z
chegarasida kesadi, to'g'ri tartibda yig'adi, keyin odatdagi ish (subtitr, elementlar, render) davom etadi.
**Asl fayllar o'zgarmaydi va o'chirilmaydi**: "olib tashlash" faqat montaj ro'yxatiga kirmaslik.

Kod: `scripts/takes.py` (pipeline papka berilganda birinchi bosqich qilib o'zi chaqiradi), yig'ish `scripts/assemble.py`,
skript bo'yicha subtitr `scripts/script_align.py`. Sozlamalar: `style/style.json` → `"takes"`. Testlar: `scripts/test_takes.py`.

## Ishga tushirish

| Agent | Buyruq |
|---|---|
| Claude Code | `/montaj input\<papka>`, `/namuna input\<papka>`, `/promo input\<papka>` |
| Codex | `$montaj input\<papka>`, `$namuna input\<papka>`, `$promo input\<papka>` |
| Qo'lda | `.venv\Scripts\python.exe scripts\pipeline.py input\<papka> --style temp\<nom>\style.json --prepare-only` |

Faqat tahlil: `scripts\takes.py input\<papka> [--style ...] [--script yo'l.txt]`. O'chirish: `pipeline.py ... --no-takes`
yoki papkaga o'z `clips.json` ingizni qo'ying (qo'lda ro'yxat ustun).

## Papkaga nima qo'yiladi

- Kliplar: `.mp4 .mov .mkv .webm .m4v` (video), `.m4a .mp3 .wav ...` (alohida ovoz → `voiceover`).
- Skript (ixtiyoriy): `script.txt` yoki `skript.txt` (yoki `--script`). Har qatorda bitta gap eng yaxshi; uzun
  paragraf ham bo'ladi (20 so'zdan uzun qator gaplarga bo'linadi). `*belgi*`, `**belgi**`, `[eslatma]` ishlaydi.

## Nima bo'ladi

| Bosqich | Skript bilan (A) | Skriptsiz (B) |
|---|---|---|
| Matn | Har klip transkripsiya (kesh `temp/<nom>/takes/`). Skriptdagi uzun so'zlar whisperga `hotwords` (faster-whisper 1.2.1 qo'llaydi; `script_hint: off` o'chiradi) | Har klip transkripsiya |
| Solishtirish | Kichik harf, tinishsiz, `o' o‘ oʻ ʻ ’ \`` bir xil, kirill → lotin, `20` ↔ `yigirma` mos (hisobotda belgilanadi) | xuddi shunday |
| Gap | Har klip skript gaplariga moslanadi: bir klipda bir nechta gap, bir gap bir nechta klipda (dubl). Har moslikda: ulush, 2-nomzod gap, farq | Gaplar pauza / "qaytadan" / qayta boshlash bo'yicha ajratiladi; deyarli bir xil gaplar bitta gapning dubllari. Faqat tartib so'zi boshqa gaplar ("birinchi set" / "ikkinchi set") dubl emas |
| Tartib | Skript tartibi; klipi yo'q gap "dubl yo'q" | Fayl nomidagi raqam → yozilgan vaqt (metadata) → mazmundan taklif (ilmoq boshida, chaqiriq oxirida, **taxminiy**) |
| Baholash | mos so'zlar; "ee/mm"; so'z takrori; ortiqcha so'z; to'xtatilgan urinish va keyin aytilgan "qaytadan"; ishonchi past so'zlar; uzun pauza; ovoz cho'qqisi kesilgan / juda past; xira, qorong'i, kuygan kadr, silkinish (1 fps, kichik kadr); yuz kadrda emas yoki 9:16 dan chiqadi (`face.py` modeli) | xuddi shunday |
| Tanlash | Eng yuqori ball; ballar `close_margin` dan yaqin → **close call**; to'liq dubl yo'q yoki boshqa gapga ham mos → **qaror kerak** | xuddi shunday |
| Kesish | Birinchi so'z boshi − `pad_in`, oxirgi so'z oxiri + `pad_out`, `nudge` ichida eng jim nuqtaga suriladi, oldingi/keyingi so'zga o'tmaydi, `fade_ms` ovoz fade. Gapdan oldingi gap, "qaytadan", buzuq urinish tashqarida qoladi. Bir klipdagi ketma-ket gaplar bitta bo'lak | xuddi shunday |
| Nutqsiz klip | Kliplar tartibidagi qo'shnisidan keyin **taklif** (hamisha tasdiqqa chiqadi) | xuddi shunday |
| Tekshiruv | Yig'ilgan video pipeline'da qayta transkripsiya qilinadi va skript bilan solishtiriladi: qamrov %, tushib qolgan, ortiqcha, tartibi boshqa so'zlar | tanlangan dubllar matni bilan |
| Ulanishlar | Har ulanish: so'z o'rtasidan kesilmaganmi, qora kadr, chertish (click) | xuddi shunday |

Shundan keyin pipeline odatdagidek: jimlik kesish (takror qidirish o'chiq: dubllar hal qilingan), `subs.srt`
(A rejimda matn skriptdan — `temp/<nom>/script.lines.txt`, faqat montajga tushgan gaplar; B rejimda transkripsiyadan,
odatdagi `[?so'z]` belgilari bilan). **Subtitr matni tasdig'i hech bir rejimda o'tkazib yuborilmaydi.**

## Natijalar (`temp/<nom>/`)

| Fayl | Nima |
|---|---|
| `report.html` | Bitta fayl: har gap, tanlangan klip va dubl, ball va sabab, 2-nomzod, kesish kirish/chiqish kadrlari, status rangi, nutqsiz kliplar, pastda tekshiruv |
| `takes.json` | To'liq tahlil (agent o'qiydi) |
| `clips.json` | `assemble.py` ro'yxati (`in`/`out`/`fade`, `lines`, `take`). Qo'lda o'zgartirilsa ustidan yozilmaydi: taklif `takes.clips.json` ga |
| `script.lines.txt` | A rejim: subtitr uchun joylangan gaplar |

Status: yashil **yaxshi**, sariq **close call**, qizil **qaror kerak**, kulrang **dubl yo'q**, ko'k **qo'lda**.

## Qo'lda tanlash (keyingi ishga tushirishda ustun)

`temp/<nom>/takes.override.json` (agent foydalanuvchi aytgani bo'yicha yozadi) yoki `input/<papka>/takes.override.json`
(foydalanuvchining o'zi). Gap raqamlari va dubl nomlari `report.html` dagidek (`klip.mp4 #2`).

```json
{
  "pin":   [{"clip": "IMG_0007.MOV", "line": 4}],
  "force": [{"line": 2, "clip": "IMG_0003.MOV", "take": 2}, {"line": 5, "clip": "IMG_0009.MOV", "in": 1.2, "out": 4.8}],
  "exclude": ["IMG_0011.MOV"],
  "place": [{"clip": "taom.MOV", "after_line": 3}, {"clip": "b-roll.MOV", "skip": true}],
  "order": [2, 1, 3, 4],
  "clip_order": ["c.mov", "a.mov", "b.mov"],
  "clips": {"ovoz.m4a": {"role": "voiceover", "cover": [{"file": "input/papka/taom.MOV"}]}, "a.mov": {"focus_x": 0.3}}
}
```

`pin` — klip shu gapga tegishli; `force` — shu dubl (yoki `in`/`out` oralig'i) tanlansin; `exclude` — klip umuman olinmasin;
`place` — nutqsiz klip joyi (`after_line: 0` boshida); `order` — B rejimda gaplar tartibi; `clip_order` — kliplar tartibi;
`clips` — assemble maydonlari (rol, `cover`, `focus_x`, `keep_audio`).

## Agent tartibi (bitta tasdiq xabari)

1. Pipeline chiqargan "Tasdiqqa chiqadigan qarorlar" ro'yxatini va `report.html` ni o'qi. Nutqsiz kliplar va
   noaniq dubllar uchun kadrlarni ko'r (`frames.py <klip> --n 6 -o temp/<nom>/...`), taklifingni override bilan yoz.
2. BITTA tasdiq xabarida: `report.html` yo'li, tartib va uning manbasi, har "close call" / "qaror kerak" / "dubl yo'q"
   gap (tanloving va sababi), nutqsiz kliplar joyi, belgilangan subtitr matni (`[?]` bilan), stills.
3. Past ishonchli qaror hech qachon jim qabul qilinmaydi. Foydalanuvchi javobini override faylga yoz, qayta ishga tushir.

## Aniqlik va halol chegaralar

`scripts/test_takes.py` (whisper ishlatmaydi): 13 fixture holat (harf xatolari, tushib qolgan so'zlar, aralash tartib,
dubllar, ikki o'xshash gap, bitta klipda ikki gap, nutqsiz klip, uzun paragraf skript, skriptsiz rejim, close call,
override, kesish nuqtalari) + media bilan to'liq yo'l + sintetik aniqlik o'lchovi (whisperga o'xshash xatolar: so'zlarning
25% ida harf xatosi, 6% tushib qolgan; har gapda 1-3 dubl, biri toza). 2026-10-08 natija (80 stsenariy, uch xil urug'):

| Rejim | Gapga moslash | Eng yaxshi dubl | Tartib | Nutqsiz klip |
|---|---|---|---|---|
| Skript bilan | 99.1-99.8% | 98.1-99.8% | 98.8% | 100% |
| Skriptsiz | 96.1-98.0% | 96.3-98.6% | 90.0-96.3% | 100% |

- Bu sintetik matn: haqiqiy o'zbek nutqi, whisper xatolari va kadr chegaralari (xiralik, silkinish, qorong'ilik)
  haqiqiy kliplarda hali o'lchanmagan. Chegaralar `style.json` → `takes.limits` da; jonli sinovdan keyin sozlanadi.
- `hotwords` whisperni skript so'zlariga yaqinlashtiradi: buzuq dubl ham to'g'riroq yozilishi mumkin. Shubha bo'lsa
  `script_hint: "off"`. Yakuniy tekshiruv (yig'ilgan video) hotwords'siz.
- Silkinish 1 fps da o'lchanadi: tez harakatlanadigan odam ham "silkinish" bo'lib ko'rinishi mumkin (jarima kichik).
- Kadrdagi yozuv va mazmunni tizim tushunmaydi: nutqsiz klip joyini agent kadrga qarab taklif qiladi, foydalanuvchi tasdiqlaydi.

## Jonli sinov (haqiqiy kliplar kerak)

- `input\takes_skript\`: 3-4 klip + `script.txt` (bitta gap kamida ikki marta aytilgan, bittasida "qaytadan").
- `input\takes_skriptsiz\`: 3-4 klip, skriptsiz (nomlari raqamsiz bo'lsa ham bo'ladi).
- Keyin: `/montaj input\takes_skript` (Codex: `$montaj input\takes_skript`) va `report.html` ni birga ko'ramiz.
