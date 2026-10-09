# Namuna motion design: maydonlar va chegaralar

Mavjud `motion` va `motion_override` davomiylik/easing/stagger ishlaydi. Yangi qo‘shimcha
`motion_design` umumiy style, brand.style yoki per-video style ichida bo‘lishi mumkin:

```json
{"motion_design":{"fast_blur_px":2,"material_seed":41,"paper_color":"#F4EEDF",
 "caption_recipes":{"proof":{"enter":"mask_up","sub":"typewriter","emphasis":"underline_draw"}}}}
```

Recipes mavjud 6 entrance va 4 emphasisdan foydalanadi; energy structure hook/problem/key_point/proof/cta
tanlaydi, energy yo‘q bo‘lsa key_point. Aniq cue `{clean,anim=none}` ustun. So‘z/vaqt o‘zgarmaydi.

## Keyframe harakati

`image`, `text`, `title`, `card`, `canvas` uchun `trajectory` ixtiyoriy.
Vaqt element startdan boshlab soniya; birinchi at=0, kamida2, o‘suvchi, end-start ichida.
Omitted qiymat oldingisidan qoladi. Ease kelayotgan segmentga tegishli:

```json
{"type":"card","start":1,"end":4,"text":"Tasdiqlangan matn","material":"ticket",
 "x":0.5,"y":0.65,"width":0.65,"height":0.14,"pivot":[0.2,0.5],
 "trajectory":[{"at":0,"dy":0.12,"scale":0.75,"rotate":-12,"opacity":0},
 {"at":0.52,"dy":0,"scale":1,"rotate":0,"opacity":1,"ease":"overshoot"},
 {"at":2.7},{"at":3,"dy":-0.04,"opacity":0,"ease":"soft"}]}
```

dx/dy frame ulushi -1..1; scale .05..3; rotate -180..180 **clockwise**; opacity0..1.
Ease linear/soft/snappy/spring/overshoot. Text pivot frame ulushi; card pivot kartochka ulushi.
Sprite rotation cache max16/24MB; video sprites cached emas. Image tezlik blur max8px (1920 reference).
Transform max24million raster pixels; CPU/xotira uchun katta zoomni qisqartiring.

## Card va panel

`card`: material paper/grid/ticket/polaroid/film/pill; width frame W, height frame H ulushi;
x/y markaz; text, font, font_size (1920 reference), weight, color (fon), text_color, radius (min dimension ulushi).
File bo‘lsa `photo_fraction` .1..9, center-crop; faqat o‘z/litsenziyali material.
`shape`: rounded/diagonal/arch. Text sig‘masa aniq xato; clipping shape chetini stillsda tekshir.
`active_at` absolute seconds va `active_color` sequential active pill holati; sound label event ishlaydi.
`anim` none/pop/fade; trajectory bo‘lsa u boshqaradi. Ticket perforatsiya; haqiqiy buklanish emas.

## Kompozitsiya kamerasi

`canvas`: start/end, optional background hex, optional trajectory; items text/title/image/card.
Child `at`/`end` **absolute cut-video seconds**, parent ichida. Nested canvas mumkin emas.
Child `behind_person` qo‘llanmaydi: aniq xato beradi; person ortidagi matnni top-level yozing.
Bitta trajectory barcha childlarni birga siljitadi. Shaffof canvas alfa to‘g‘ri premultiplied source-over;
render va editor alpha export bir xil build_elements foydalanadi. Frame tashqarisiga chiqqan camera
elementlarini stills/filmstripda tekshir: bu avtomatik safe-zone kafolati emas.

## Uzluksiz speaker layout

Split broll yoki stage: `transition:"layout_morph"`, optional `transition_seconds`.
Speaker bir marta crop/resize qilinadi; ikki yuzning alpha blendi yo‘q. Legacy fade default saqlanadi.
Split chegarasi rangi `motion_design.seam_color` (default #EBEBEB).
Stage morph footer/progress/punch/shake/flash bilan hozir qo‘llanmaydi: aniq xato beradi.

## Matn materiali

Caption style yoki text/title `stroke`:

```json
{"stroke":{"width":2,"color":"#F7CB60","outline_only":false,
 "depth":12,"dx":0.8,"dy":1,"depth_color":"#614737"}}
```

Depth reference1920 px (0..64), dx/dy -2..2, fonts/fallback o‘/g‘ uchun mavjud tizim.
outline_only ring qiladi; glow mavjud maydon orqali. Relief tekis extrusion, mesh/lighting haqiqiy3D emas.

## Guruh tanlash

`sample_groups.py --help`; `list`, `select --features <json>`, `apply GROUP --style temp/<video>/style.json --reason "dalil"`.
Features: seated_explainer/static_speaker/interview/testimonial/multiple_speakers/creator/tutorial/documents/campus/promo/product/showcase/vlog booleans.
Bu agentning kadr/mazmun kuzatuvlariga asoslangan ochiq rank, avtomatik vision classifier emas.
D uchun --subtype promo/showcase/vlog; brand berilsa --brand bilan uning style patchi oxirida qo‘llanadi.
D subtype presetlari: promo=promo, showcase=single, vlog=clean. DNA patch caption/motion default,
grafika geometriyasi va semantik cuts agent rejasidan olinadi. Native timing defaultlar universal o‘rtacha emas.
DNA suggested_accent tavsiya; mavjud font/accent avtomatik almashtirilmaydi.
Ambiguous rank -> agent dalilli editorial judgement va ONE approvalda guruh/sabab.

## Tekshiruv

`test_motion_design.py`: trajectory continuity/bounds, RGBA/RGB parity, pivot, material mask,
active states, camera co-motion, Uzbek/identity text, relief, recipe override, SFX lead/density va group precedence.
Eski suites ham ishlaydi. `review_tools.py filmstrip`/`ab`, paired cue/waveform va energy chizmasi.
CPU proof va manba gaplari `docs/STYLE_STUDY/`; motion/ovoz didini foydalanuvchi tekshiradi.

## Invert chaqnash

`{"type":"flash","at":2,"duration":0.1,"mode":"invert","amount":1}` — 30fpsda uch interval.
Mode color legacy default; invert kadr rangini tanlangan vaqt davomida teskari qiladi. Originaldan SFX olinmaydi.
Bu source-dependent effect: editor export uni raster base ichiga oladi, mustaqil transparent grafika emas.
Canvas/TrackedText full-frame RGBA allocation/warp qiladi; CPUda qisqa sahnalarga cheklang.

## Ma’noli obyekt animatsiyalari

`group`: `layout: fan|stack|spread`, `items[{at,text,image}]` (1–12, o‘suvchi vaqt, enddan kichik),
`active`, `active_color`, `color`, `text_color`, `material`, `font_size`, `exit: fade|collapse|none`.
Fan: **bitta pivot**, `pivot:[x,y]`, `angle_from`, `spread` (-180..180), `length` (W ulushi), `thickness` (H ulushi).
Stack/spread: `x,y,width,height,columns,gap,step_x,step_y`. Timing motion.label va motion.exit;
aytilmagan band yoki ma’nosiz 1..5 yorliqlarni o‘ylab topma.

`hero`: `file` (o‘z/litsenziyali cutout) yoki MIT `icon`; `x,y,size`, `from:[x,y]`, `path:[[x,y],...]`,
`rotate_from`, `rotate`, `tilt_from:{x,y}`, `tilt:{x,y}`, `trail:0..1`, `blur:0..16`, `depth:0..1`,
`float`, `exit:fly|fade|none`. `duration` optional, standart motion.durations_ms.hero × speed scale.
Catmull path, oldingi 4 kadrning alpha izlari, tezlikka mos blur va floating shadow — CPU 2.5D; haqiqiy 3D emas.
Hero va group itemlari SFX eventlariga ulanadi; mavjud lead/density/nutq margin cheklovi saqlanadi.

Yuzni barcha kadrda tekshirish, hide_captions, repeat check va sifat gate: `docs/QUALITY.md`.
