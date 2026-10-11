# Remotion timeline va shaffof overlay

Yangi full-timeline yo'li `pipeline.py --engine remotion`: `docs/how-to-use.md`.
FFmpeg kesish/ovoz/final encode, Whisper va subtitle approval saqlanadi. Quyidagi
maxsus overlay kutubxonasi ham ishlaydi. Easing `src/easing.mjs` orqali umumiy.

# Remotion overlay sahnalari (ixtiyoriy, ikkala agent uchun)

Native montaj Python dvigatelida ham qoladi (`scripts/compose.py`). Overlay yo'li bizning dvigatel qila olmaydigan
**maxsus shaffof sahnalar** uchun: haqiqiy CSS 3D (buklanadigan kartochka, sahifa aylanishi, hajmli 3D matn),
WebGL 3D obyekt (Three.js), namunaviy motion blur, SVG chiziq chizish, yorug'lik chaqnashi (light leak).
Natija ProRes 4444 (alfa) `.mov`, uni `elements.json` da `broll` `mode: full` qilib ustiga qo'yamiz.

## Litsenziya va o'rnatilganlar (2026-10-10)

- Remotion 4.0.534: yakka shaxs va 3 xodimgacha tijoriy tashkilotga **tekin** (https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).
  Foydalanuvchi yakka montajor. Kattaroq kompaniya nomidan ishlansa pullik litsenziya kerak.
- Paketlar (`package.json`, aniq versiyalar): remotion, @remotion/cli, fonts, transitions, motion-blur, paths, shapes,
  noise, layout-utils, three (+ three, @react-three/fiber), effects, light-leaks, lottie; react 19.1; typescript 5.8.
- Node.js v24.18 kompyuterda bor edi. Rasmiy agent skillari (matn): `~/.claude/skills/remotion-*` va
  `~/.agents/skills/remotion-*` (Codex) — best-practices, markup, render, captions, docs, studio, upgrade.
- Brauzer: Remotion'ning Chrome Headless Shell yuklanishi tarmoqda uzildi; `render.mjs` o'rnatilgan Chrome'ni
  (`C:/Program Files/Google/Chrome/Application/chrome.exe`, v154) ishlatadi. `HtmlInCanvasMotionBlur` uchun 157+ kerak
  (headless shell yuklansa ishlaydi); hozir `CameraMotionBlur` / `Trail` ishlatiladi.
- Shriftlar: `style/fonts` (OFL) `public/fonts` ga nusxa. Internetdan shrift yuklanmaydi.

## Ishlatish

```powershell
cd remotion
node render.mjs ..\temp\<nom>\overlays\scene.json ..\temp\<nom>\overlays\scene.mov      # shaffof ProRes 4444
node render.mjs ..\temp\<nom>\overlays\scene.json ..\temp\<nom>\overlays\f30.png --still 30   # bitta kadr
npx remotion studio src/index.ts                                                         # brauzerda ko'rish
```

`scene.json`: `{"width":1080,"height":1920,"fps":30,"durationInFrames":N,"theme":{...},"scenes":[...]}`.
Har sahna: `type`, `from` (kadr), `duration` (kadr), `x`, `y` (markaz, kadr ulushi), `w` (kenglik ulushi), `exit` (kadr).
Rasm yo'llari loyihaga nisbatan (`temp/<nom>/images/x.png`) — skript o'zi `public/job/` ga ko'chiradi.
`theme`: `accent`, `text`, `paper`, `ink`, `font`, `display` (brend/per-video style'dan oling, o'ylab topmang).

| type | Nima | Asosiy maydonlar | Namuna dalili |
|---|---|---|---|
| `fold_card` | Ilgakdan ochiladigan 3D kartochka (~16 kadr) | `text`, `sub`, `image`, `hinge` top/left, `h`, `color`, `size` | s35 ticket unfold 13 f@25 |
| `page_turn` | Kartochka aylanib orqa tomoni ochiladi | `front`, `back`, `turnAt`, `color`, `backColor` | s39 card fan, s41 |
| `extrude` | Hajmli 3D matn/raqam, perspektiva, sekin tebranish | `text`, `depth`, `size`, `tiltX`, `tiltY`, `side`, `font` | s39 extruded number, s41 |
| `kinetic` | Katta sarlavha harfma-harf + motion blur, kichik so'zlar keng tarqalgan | `text`, `sub[]`, `size`, `stagger` | Kadr rakursli DARAXT, s29 |
| `draw` | Qo'lda chizilgandek chiziq: underline/circle/arrow yoki `d` | `shape`, `d`, `stroke`, `drawFrames`, `h` | s25/s34/s36 stroke |
| `counter` | Raqam sanab chiqadi, porlash | `value`, `start`, `prefix`, `suffix`, `label`, `decimals` | s05 "18" |
| `fly` | Rasm/obyekt aylanib, iz (Trail) bilan uchib kiradi | `image`, `fromX`, `fromY`, `rotateFrom`, `rotate`, `tilt`, `enter` | s33 prop 9 f@25 |
| `box3d` | WebGL 3D quti (kitob/telefon/karta shakli), yorug'lik | `size [w,h,d]`, `rotateFrom`, `rotate`, `scale`, `color` | — |
| `light_leak` | Kesish ustidagi yorug'lik chaqnashi | `seed`, `hueShift` | Kadr rakursli, Obrazli |

## Qoidalar (montajda)

- Faqat nutqda aytilgan/ko'ringan narsa; namunadan logo/footage/musiqa/shrift olinmaydi.
- Yuzni yopmasin: render qilingan klipni `elements.json` ga qo'ygach compose `face_safety.json` o'lchaydi
  (`broll full` almashtiruvchi qatlam sifatida o'tkazib yuboriladi — shuning uchun overlay joyini stillsda o'zingiz tekshiring;
  light_leak yuzni ataylab bir zum yopadi, faqat kesishda 15-30 kadr).
- Tezlik (bu kompyuter, CPU, concurrency 2): 150 kadr ProRes ~42 s; WebGL kadr ~ bir xil. Har sahnani alohida kichik klip qiling.
- Avval `--still` bilan ko'ring, keyin to'liq render. Klipni `temp/<nom>/overlays/` ga yozing (output/ ga emas).

## Sinov natijalari

`out/demo.mov` (kinetic + fold_card + extrude) compose ustida: `temp/remotion_test/stills.jpg` — to'g'ri tushdi.
`out/leak.mov` light leak + circle stroke: alfa yuva444p12le, 60 kadr 29 s.
