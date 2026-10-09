# SFX kutubxonasi

Kategoriyalar: whoosh, pop, click, hit, riser, ding, swipe, typing, tick, impact. To'liq qo'llanma: `docs/SFX.md`.

- `synth_v2_NN.wav` — `scripts/sfx_synth.py` (numpy) bilan yasalgan, loyihaning o'z tovushi, har kategoriyada 4 ta.
  Eski `synth_01/02.wav` va tekis `pop.wav`... (v1, `scripts/make_sfx.py`) moslik uchun qoldi; v2 bor ekan ular tanlanmaydi.
- `real__<paket>__<nom>.wav` — sotib olingan to'plamdan `scripts/sfx_import.py` bilan import qilingan. Litsenziyasi
  tasdiqlangan haqiqiy fayl har doim sintezdan ustun. Bu fayllar gitga kirmaydi (`.gitignore`).
- `_preview/<kategoriya>.wav` — kategoriyani eshitib ko'rish uchun variantlar ketma-ket.
- `_inbox/` — sotib olingan zip/papka shu yerga; `_unsorted/` — nomidan kategoriya aniqlanmaganlar; `_licenses/` — paket litsenziyasi.
- `index.json` — `scripts/sfx_library.py` indeksi (manba, litsenziya, sha256, davomiylik).

Agent ovozni eshitmaydi: subtle/stronger va effekt tanlovini foydalanuvchi tinglab tasdiqlaydi.
