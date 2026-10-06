# Tool'lar ro'yxati

Montaj tizimi uchun foydali ochiq kodli tool'lar. "Ishlatilmoqda" bo'limidagilar o'rnatiladi,
qolganlari ixtiyoriy: kerak bo'lganda, foydalanuvchidan so'rab qo'shiladi.

## Ishlatilmoqda

| Tool | Nima uchun | Manba |
|---|---|---|
| FFmpeg (Gyan build) | Kesish, subtitr, render, ovoz me'yori | https://github.com/GyanD/codexffmpeg |
| faster-whisper | Nutqni matnga aylantirish (CPU'da tez, int8) | https://github.com/SYSTRAN/faster-whisper |
| PySceneDetect | Namuna videolarda sahna kesishlarini topish | https://github.com/Breakthrough/PySceneDetect |
| OpenCV (opencv-python) | Kadrlarni tahlil qilish (rang, yorqinlik) | https://github.com/opencv/opencv-python |
| NumPy | Hisob-kitob | https://github.com/numpy/numpy |

## O'zbek tili uchun whisper modellari (sinab ko'rish kerak)

Standart `small` modeli o'zbek tilida ko'p xato qiladi. Hugging Face'da faster-whisper
formatidagi (CTranslate2) o'zbek tiliga moslangan modellar bor. Sifati bu loyihada hali
o'lchanmagan, shuning uchun avval bitta videoda `small` bilan solishtiring:

| Model | Asosi | Havola |
|---|---|---|
| `yuldashev222/whisper-small-uz-v1-ct2` | whisper-small (OvozifyLabs) | https://huggingface.co/yuldashev222/whisper-small-uz-v1-ct2 |
| `yuldashev222/uzbek_stt_v1-ct2` | whisper-medium (Kotib), sekinroq | https://huggingface.co/yuldashev222/uzbek_stt_v1-ct2 |

Sinash: `.venv\Scripts\python.exe scripts\transcribe.py input\video.mp4 --model yuldashev222/whisper-small-uz-v1-ct2 --language uz`
Yoqsa `style/style.json` da `whisper.model` ga shu nomni yozing.

## Ixtiyoriy (hozircha o'rnatilmagan)

| Tool | Qachon kerak bo'ladi | Manba |
|---|---|---|
| auto-editor | Jim joylarni kesishning tayyor, kuchliroq varianti (harakat bo'yicha ham kesadi) | https://github.com/WyattBlue/auto-editor |
| stable-ts | Whisper so'z vaqtlarini aniqroq qilish | https://github.com/jianfch/stable-ts |
| WhisperX | Aniq so'z vaqtlari va kim gapirayotganini ajratish (GPU bilan qulay) | https://github.com/m-bain/whisperX |
| pysubs2 | Subtitr fayllarini (ASS/SRT) murakkab tahrirlash | https://github.com/tkarabela/pysubs2 |
| ffmpeg-normalize | Ko'p faylning ovozini bir xil me'yorga keltirish | https://github.com/slhck/ffmpeg-normalize |
| DeepFilterNet | Ovozdagi shovqinni tozalash | https://github.com/Rikorose/DeepFilterNet |
| Silero VAD | Nutq bor joyni aniqlash (faster-whisper ichida allaqachon bor) | https://github.com/snakers4/silero-vad |
| MoviePy | Python'da murakkab kompozitsiya (rasm ustiga rasm, animatsiya) | https://github.com/Zulko/moviepy |
| Remotion | React bilan animatsiyali grafika va sarlavhalar | https://github.com/remotion-dev/remotion |

## Motion-grafika uchun (ishlatilmoqda)

| Narsa | Nima uchun | Manba va litsenziya |
|---|---|---|
| Pillow | Matn va shakllarni chizish | https://github.com/python-pillow/Pillow (MIT-CMU) |
| YuNet yuz modeli (`assets/models/face_yunet.onnx`) | Yuzni topish: zoom va 9:16 kesish | https://github.com/ShiqiYu/libfacedetection.train (BSD-3) |
| Shriftlar (`style/fonts/`): Inter, Montserrat, Onest, Oswald, Unbounded, Playfair Display, Caveat | Subtitr va sarlavhalar; hammasi lotin, kirill va o'zbek harflarini qo'llaydi | https://github.com/google/fonts (SIL OFL, tijoriy ishda bepul; litsenziyalar `style/fonts/LICENSES/`) |
| Ovoz effektlari (`assets/sfx/`) | pop, click, tick, thud, ding, whoosh, swipe, riser | `scripts/make_sfx.py` bilan noldan generatsiya qilingan, tashqi manba yo'q |

| Emoji rasmlari (`assets/emoji/`) | Matn ichidagi va alohida emoji | https://github.com/googlefonts/noto-emoji (Apache 2.0 / OFL) |
| Reels xavfsiz zonalari va eksport talablari | `style.json: platform` | https://github.com/kajisho5/ffmpeg-skill (MIT) jadvalidan olingan qiymatlar |

## Rasm, belgi va grafika (ishlatilmoqda)

| Narsa | Nima uchun | Manba va litsenziya |
|---|---|---|
| Phosphor Icons (`assets/icons/`) | 1500+ vektor belgi: `icon` elementi, `scripts/icons.py` | https://github.com/phosphor-icons/web (MIT) |
| Edge / Chrome (kompyuterda bor) | HTML/CSS/SVG ni PNG qilish: `scripts/html_render.py` | alohida o'rnatilmaydi |
| Openverse API | Kalitsiz stok rasm qidirish (CC0, jamoat mulki, CC BY) | https://api.openverse.org (kod: https://github.com/WordPress/openverse) |
| Wikimedia Commons API | Kalitsiz rasm qidirish (tarixiy, joylar, narsalar) | https://commons.wikimedia.org/w/api.php |
| Pexels API | Sifatli stok foto va b-roll video (bepul kalit) | https://www.pexels.com/api/documentation/ |
| Pixabay API | Stok foto va video (bepul kalit) | https://pixabay.com/api/docs/ |
| Gemini image API | AI rasm (kalit kerak, pullik bo'lishi mumkin; rasmga SynthID belgisi qo'yiladi) | https://ai.google.dev/gemini-api/docs/image-generation |

Yangi Python kutubxonasi qo'shilmagan: tarmoq so'rovlari standart `urllib` bilan.

## Harakatli grafika uchun (ixtiyoriy, o'rnatilmagan)

| Tool | Nima | Eslatma |
|---|---|---|
| HyperFrames | HTML → video, shaffof WebM/ProRes; Claude Code plagini bor | https://github.com/heygen-com/hyperframes (Apache-2.0), Node 22+. Qo'shish: `docs/HYPERFRAMES_PROMPT.md` |
| Remotion | React → video | Litsenziyasi kompaniyalar uchun pullik bo'lishi mumkin. `docs/REMOTION_PROMPT.md` |
| OpenMontage | Agentlar uchun to'liq video ishlab chiqarish tizimi | https://github.com/calesthio/OpenMontage (AGPL-3.0): kodi ko'chirilmaydi, faqat g'oya manbai |

Tashqi skill va plaginlar auditi: `docs/SKILLS_AUDIT.md`. Remotion: `docs/REMOTION_PROMPT.md`.
