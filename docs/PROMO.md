# Restoran / mahsulot promo: mustaqil ish tartibi

Foydalanuvchi faqat kliplarni beradi. Taom nomlari, set raqamlari, narx, taklif va chaqiriqni agent
**nutqdan va kadrlardan** topadi. Namuna 20 bitta misol, qolip emas: har promo o'z uslub yo'nalishida.
Skill: `/promo` (Claude Code), `$promo` (Codex) — manba `docs/claude_skills/promo/SKILL.md`.

## Ishga tushirish (bitta qator)

Kliplar `input/<promo nomi>/` papkasida (nom bo'yicha tartib, masalan `01_...mp4`, `02_...mp4`).

| Agent | Foydalanuvchi yozadi |
|---|---|
| Claude Code | `/promo input\<promo nomi>` |
| Codex | `$promo input\<promo nomi>` |

Brend bo'lsa oxiriga brend nomi qo'shiladi (`brands/<nom>/` mavjud bo'lsa). Boshqa hech narsa kerak emas.

## 1. Mustaqillik qoidalari (majburiy)

1. **Nutq.** Har speech va voiceover klip transkripsiya qilinadi (o'zbekcha: `yuldashev222/whisper-small-uz-v1-ct2`).
   Taom nomlari, set raqamlari, narx, taklif (necha kishilik, chegirma, yetkazib berish) va chaqiriq shu matndan olinadi.
2. **Kadr.** `frames.py <klip> --n 8 -o temp/<nom>/...` va kerakli soniyada `--at`: qutidagi nom, forma,
   peshlavha, menyu, narx yorlig'i **faqat aniq o'qilsa** matn sifatida olinadi. Logotip kadrdan kesib
   olinmaydi va logotip fayli sifatida ishlatilmaydi.
3. **Hech narsa o'ylab topilmaydi.** Aytilmagan yoki aniq ko'rinmagan narx, nom, raqam yo'q. Shubhali narsa
   tasdiq xabarida `[?so'z]` va manbasi bilan: `[?Mol kochalkasi] (04_kochalka.mp4 1.2 s nutq)`,
   `[?990 000] (07_narx.mp4 2.1 s: "to'qqiz yuz to'qson ming")`.
4. **Dubllar va rollar** (`speech`, `product`, `voiceover`; qadoqlash/joy kadrlari `product`) agent tomonidan aniqlanadi.
   Papka berilganda pipeline avval dubl tanlashni ishlatadi (`docs/TAKES.md`): har gapning eng yaxshi dubli so'z
   chegarasida kesiladi, nutqsiz kliplar `product` bo'lib joyi taklif qilinadi, `temp/<nom>/report.html` chiqadi.
   Transkripsiyadan keyin **"Kliplar bo'yicha nutq"** jadvali ham chiqadi. Agent kadrlarni ko'rib rollar, ovoz
   `cover` va joylarni `temp/<nom>/takes.override.json` ga (`clips`, `place`) yozadi, qayta ishga tushiradi va
   ro'yxatni tasdiq xabarida ko'rsatadi.
5. **So'raladigan yagona narsa** (bir marta): obuna kartochkasi uchun Instagram manzili. Berilmasa `follow`
   handle'siz (`icon`). Musiqa va logotip faqat foydalanuvchi bergan fayldan; berilmasa kliplarning o'z ovozi
   qoladi (`product_audio: keep`, standart) va logotip qo'yilmaydi.

## 2. Uslub yo'nalishlari (har promo o'zgacha)

Ma'lumot: `style/promo_looks.json` (faqat mavjud preset, element, style kalitlari). Vosita: `scripts/promo_looks.py`.

| Yo'nalish | Namunalar | Qachon | Ilmoq / qahramon / narx | Ko'rinish |
|---|---|---|---|---|
| `warm_glow` | 20, 6 | qorong'i iliq joy, gril/go'sht, jonli nutq, set+narx | `{promo}` kursiv porlovchi | `look: warm`, shisha yorliq, yon so'zlar |
| `clean_minimal` | 2, 7, 8, 10, 13 | yorug' kafe, desert, qahva, sokin nutq | `{single}` / `*oq katta*` / `{clean}` | `look: natural`, porlashsiz, accent oq yoki yumshoq |
| `bold_caps` | 5, 14, 17 | fast food, aksiya, tez baland nutq | `{caps}` / `{heavy}` / `{caps}` | `look: punchy`, to'yingan taom rangi, qattiq yorliq |
| `editorial_serif` | 3, 12, 18 | premium restoran, milliy taom, sekin kamera | `{serif}` | `look: film`, krem/oltin accent, serif yon so'zlar |
| `fresh_marker` | 13, 2 | salat, ichimlik, kunduzgi yorug'lik | `{caps}` / `{clean}` + `==marker==` | `look: cool`, yashil/yorqin taom rangi |

Hamma yo'nalishda ovoz ostidagi bo'laklar `{vo}`, taomlar `label`, odam yonidagi so'zlar `aside`.

Tanlash tartibi:

1. `promo_looks.py list` — yo'nalishlar va oxirgi promolar. **Oxirgi promo yo'nalishi takrorlanmaydi**
   (`apply` rad etadi; faqat foydalanuvchi so'rasa `--allow-repeat`).
2. Kontent va kadrdan tanla: taom ranglari va joy (qorong'i/yorug', iliq/sovuq), nutq energiyasi, mahsulot turi.
   Kerak bo'lsa namunalarni ko'r (`frames.py "samples/sample N.mp4" -o temp/<nom>/sN.jpg`).
3. `promo_looks.py palette temp/<nom>/<nom>.mp4 --out temp/<nom>/palette.json` — kadrdagi asosiy ranglar,
   `accent_warm`, `accent_food`, subtitr zonasi yorqinligi (0.6 dan yuqori: soya/gradiyent kerak).
4. `promo_looks.py apply <yo'nalish> --style temp/<nom>/style.json --accent "#RRGGBB"` — per-video uslubga yozadi
   (umumiy `style/style.json` ga emas).
5. Tasdiq xabarida bir qator sabab: "bold_caps: yorqin burger ranglari va tez nutq; accent #FF5A1F burger qizilidan".
6. Final tayyor bo'lgach: `promo_looks.py record <yo'nalish> --job <nom> --accent "#RRGGBB"` (gitda saqlanadi).

## 3. Ish tartibi

1. `handoff.py show`; video eslatmasini egalash (`handoff.py set ... --video input\<promo nomi> --agent ...`).
2. `pipeline.py input\<promo nomi> --style temp\<nom>\style.json --prepare-only` (per-video style: umumiy
   `style.json` nusxasi + o'zbek modeli). Dubl tanlash qarorlari, `report.html` va "Kliplar bo'yicha nutq" jadvalini
   ko'r, rollar/joylarni `takes.override.json` ga yoz, qayta ishga tushir. Product oraliqlari jimlik deb kesilmaydi.
3. Kadrlar (`frames.py`), palitra, yo'nalish (§2).
4. Matn: nutqdagi nomlar va narx; VO bo'laklari `{vo}`, qahramon/narx yo'nalish belgilari bilan. Odam yonida
   chiqadigan so'zlar subtitrdan olinadi (`corrections.json` `"text": ""`) va `aside` ga yoziladi.
5. `elements.json` (§5), taom yorlig'i rasmi mijoz kadridan (`frames.py --at`, `cutout.py`).
6. **Bitta tasdiq xabari:** klip rollari jadvali, `[?]` belgili to'liq matn (manbasi bilan), topilgan nomlar/narx/taklif
   (qayerdan), reja jadvali, yo'nalish + bir qator sabab, stills, Instagram manzili savoli (bir marta).
7. "ha" -> draft -> "ha" -> final; `promo_looks.py record`; review.md, AGENT_MEMORY (parallel bo'lsa deferred_learning).

## 4. Namuna 20 tahlili (warm_glow misoli)

`samples/sample 20.MP4` (46 s, 1440x2560, 60 fps HEVC), 2026-10-08 o'lchangan (`temp/sample20_study/`),
`temp/promo_test/` da sinab namuna bilan solishtirilgan (`studio.py compare`). O'lchamlar 1080x1920 ga.

| Vaqt | Kadr | Ovoz | Ekranda |
|---|---|---|---|
| 0-1.4 | oshpaz kameraga | oshpaz | kichik so'zlar yuzning chap va o'ngida birin-ketin |
| 1.4-3.4 | oshpaz | oshpaz | katta kursiv sariq porlovchi "5 kishilik" (~165 px, kenglik 81%), ostida "set ...... so'rashdi" |
| 3.6-5.4 | oshpaz + stol | oshpaz | oq kursiv "4 ta set" oshpaz orqasida (qalpoq oldida) |
| 5.5-15 | taomlar makro | musiqa | tepada shisha yorliq (x 0.26-0.74, y 0.15-0.25): kesilgan taom + "1-set" + nom, har taomda sakrab almashadi |
| 15-34 | taomlar | ovoz | kichik qalin oq subtitr (~40 px, y 0.70), so'zlar aytilganda |
| 35-38.5 | oshpaz | oshpaz | kichik qator, keyin katta sariq "990,000" (sanamaydi), o'ngda "so'm" |
| 39-46 | qadoqlash, oshpaz | musiqa/oshpaz | oxirida qo'lyozma so'zlar yuz yonida |

## 5. Elementlar

```json
{"elements": [
  {"type": "aside", "start": 0.3, "end": 1.4, "stagger": 0.3,
   "items": [{"at": 0.3, "text": "juda\nham", "side": "left"}, {"at": 0.6, "text": "ko'pchilik\nbizdan", "side": "right"}]},
  {"type": "title", "start": 3.4, "end": 5.45, "text": "*4 ta set* tayyorlab qo'ydik", "preset": "promo",
   "y": 0.34, "size": 1.15, "behind_person": true},
  {"type": "label", "start": 5.48, "end": 8.93, "y": 0.2, "items": [
    {"at": 5.48, "kicker": "1-set", "name": "Mol qovurg'asi", "image": "temp/<nom>/images/qovurga.cut.png"},
    {"at": 6.57, "kicker": "2-set", "name": "Qo'yning qo'li", "image": "temp/<nom>/images/qol.cut.png"}]},
  {"type": "aside", "start": 19.5, "end": 21.4, "font": "Caveat", "size": 0.9, "dy": -0.04, "stagger": 0.35,
   "items": [{"at": 19.5, "text": "Go'sht\nta'midan", "side": "left"}, {"at": 20.4, "text": "zavq-\nlaning", "side": "right"}]}
]}
```

`label`: `x`, `y`, `width` (0.5), `size`, `image_size` (0.085), `color`, `kicker_color`, `glass`, `font`.
`aside`: `spread` (0.27), `dy` (0), `size` (0.75), `font`, `color`, `weight`, `stagger`, `margin` (0.05);
item: `at`, `text`, `side` (left/right), `end`, `dy`, `size`, `stagger`. Matndagi nomlar va raqamlar faqat nutq/kadrdan.
`behind_person` broll/stage/scene/grade bilan bir videoda ishlatilmaydi (assemble kadrlari broll emas).

## 6. Tezlik (bu kompyuter, CPU)

60 fps HEVC 1440x2560 yig'ish ~34 s / 10 s; to'liq render 1080x1920 ~63 s / 10 s; bitta HEVC to'g'ridan ~82 s / 10 s.

## 7. Halol chegaralar

- Kirish/chiqish harakatlari (qiyshiq kirish, surilib chiqish) aniq takrorlanmaydi: mavjud `pop`/`fade`/`blur`.
- Narx sanab chiqmaydi (`stat` bor, lekin kursiv emas). Kamera harakati kadrning o'zida bo'lishi kerak.
- Kadrdagi yozuvni agent ko'rib o'qiydi (OCR yo'q): aniq o'qilmasa `[?]`.
- Musiqa va logotip faqat foydalanuvchi faylidan; ovozni agent eshitmaydi, tanlovni foydalanuvchi qiladi.
