# Remotion motion yo‘li

1. `handoff.py show`, AGENTS va PLAYBOOKni o‘qi. Umumiy kod faqat boshqa agent idle bo‘lsa o‘zgaradi.
2. Asl pipeline bilan tayyorla; transkripsiya va kesish o‘sha skriptlarda qoladi:

```powershell
.venv\Scripts\python.exe scripts\pipeline.py "input\video.mp4" --engine remotion --prepare-only
```

3. Matnni ko‘rsatib foydalanuvchi tasdig‘ini video HOLAT.md ga yoz. Whisperni qayta yuritma; tuzatilgan so‘z va SRT saqlansin.
4. Grafik `elements.json` bilan reja tayyorla. Remotion native grafik turlari: title/text/callout/lower_third, image, broll(full/split), scene, list/panel, stat, follow. Murakkab kutubxona sahnasi standalone overlay + native compose orqali (full timeline custom-scene face coverage tekshirilmagani uchun eksportni to‘xtatadi). Mos kelmagan legacy tur aniq xato beradi; hech narsa jim tushirib qoldirilmaydi.
5. Avval stills, keyin draft:

```powershell
.venv\Scripts\python.exe scripts\pipeline.py "input\video.mp4" --engine remotion --stills 0.3,1.6,4.2
.venv\Scripts\python.exe scripts\pipeline.py "input\video.mp4" --engine remotion --approve-subs --draft
```

6. Draft tasdiqlangach `--draft`ni olib tashla. Brand mavjud bo‘lsa `--brand NOM`; yangi brand shabloni `brands/_template/`, mavjud `_shablon` ham qolgan. Tasdiqlangan per-video style uchun `--style temp\<video>\style.json`.
7. `temp/<video>/qa/<export>/report.md` va transition sheetsni och. Texnik QA did/ritm tasdig‘i emas. Cache faqat o‘zgargan 4s bo‘laklarni render qiladi; exit overlap qo‘shni segmentni ham invalidatsiya qiladi.

## Sozlamalar

`style.remotion` (brand.json ichida), yoki per-video to‘liq style.json `remotion`:

```json
{"fps":30,"concurrency":2,"preset":"soft","enter_sec":0.32,"exit_sec":0.28,"distance_px":36,"animation_cycle":["slide","wipe","pop"],"blur":{"enabled":false,"intensity":2},"supersample":1,"fps_conversion":"blend","segment_sec":4,"qa_attempts":3,"cache_max_gb":2}
```

Preset soft/snappy/bouncy. Duration override yozilmasa preset davomiyligi qo‘llanadi; 0.2–0.5s chegarada. Motion tanlovi source SHA seed + caption index bilan deterministik; original so‘z startMs/endMs saqlanadi, render onsets ceil(start*fps), bir kadrdan kechikmaydi. So‘z ichidagi o‘/g‘/apostrophe bo‘linmaydi.

`remotion_scene` renderer maydoni (full timeline face QA hozir unverified; production uchun standalone overlay/native yo‘li):

```json
{"type":"remotion_scene","start":1.2,"end":3.4,"scene":{"type":"draw","shape":"underline","stroke":"#F4BE4F","text":""}}
```

Sahna maydonlari remotion/README.md da. Scene vaqti kadrda, root element vaqti soniyada. Sample materialni eksportga ko‘chirma.

## O‘rnatish / preview

Bu kompyuterda Node24 va Remotion4.0.534 allaqachon bor. Bu upgrade install/download qilmaydi.
Yangi kompyuter uchun docs/NEW_LAPTOP.md; paketlarning aniq versiyalari remotion/package-lock.json da.

```powershell
cd remotion
node node_modules\@remotion\cli\remotion-cli.js studio src/index.ts --props "..\temp\<video>\remotion\props.json" --public-dir "..\temp\<video>\remotion\public"
```

Studio Timeline composition job props bilan ochiladi; render ishlashi Studio UI tasdig‘i emas. Sandbox mahalliy Chrome WebSocketni bloklasa, agent sandboxdan tashqarida ruxsatli render qiladi. `.env` o‘qilmaydi.

Eski flow uchun `--engine motion` yoki `--engine ass`. Umumiy standart motion saqlangan; Remotion shabloni opt-in. Legacy tasdiqlangan numeric fps/renderlar qayta dizayn qilinmaydi.

API manbalar: [OffthreadVideo](https://www.remotion.dev/docs/offthreadvideo), [renderMedia](https://www.remotion.dev/docs/renderer/render-media), [spring](https://www.remotion.dev/docs/spring), [render CLI](https://www.remotion.dev/docs/cli/render). API mosligi installed4.0.534 types va real render bilan tekshiriladi.

Cache2GiB: eski visual segmentlar tozalanadi, active segment katta bo'lsa ogohlantiriladi va saqlanadi. Successful render staging/concat/PCM scratchni tozalaydi; proof reports va visual cache qoladi.

Rang ishlovi/LUT existing look_filters orqali normalizationda; video.grain existing grain_filter orqali final encode da. Subtitle/Whisper/cut scripts qayta yozilmagan.
