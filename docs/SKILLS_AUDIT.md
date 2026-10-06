# Skill va plaginlar auditi (2026-10-06)

Quyidagi omborlar yuklab olinib, kodi o'qildi (faqat README emas): ko'rsatmalar, skriptlar,
tarmoqqa chiqish, fayl o'chirish va tashqi kalit talab qilishi tekshirildi. Hech biri bu
loyihaga **o'rnatilmagan**: foydali g'oya va qiymatlar o'zimizning skriptlarga ko'chirilgan.

| Ombor | Nima | Xulosa |
|---|---|---|
| `remotion-dev/skills` | Remotion rasmiy qoidalari (faqat matn, 12 skill) | Xavfsiz. Remotion qo'shilsa shart. O'rnatish: `npx skills add remotion-dev/skills` (README shunday deydi). |
| `remotion-dev/claude-code-plugin` | Shu skillarning Claude Code plagini ko'rinishi (`.claude-plugin/` bor) | Xavfsiz, lekin README "ichki paket, hujjati yo'q" deydi. Skillarning o'zi yetadi. |
| `kajisho5/ffmpeg-skill` (MIT) | 42 ta FFmpeg asbobi: kesish, subtitr, HDR, LUT, tekshiruv | Sifatli va toza: tarmoq so'rovi yo'q, `shell=True` yo'q, faqat o'z vaqtinchalik fayllarini o'chiradi. Bizdagi skriptlar bilan 80% ustma-ust. O'rnatilmadi; Reels xavfsiz zonalari va platforma talablari shundan olindi. |
| `MakeMyClip/editor` (MIT) | Node 24 dagi 19 asbob + brauzer timeline | Kichik loyiha, 1.0 dan oldin, Node 24 talab qiladi. Kerak emas. |
| `AgriciDaniel/claude-shorts` (MIT) | Uzun videodan qisqa kliplar, Remotion subtitr | Linux/bash, GPU whisper va mediapipe talab qiladi. Windows'da to'g'ridan-to'g'ri ishlamaydi. G'oya: segment tanlash. |
| `bradautomates/claude-video` (MIT) | `/watch`: havoladan video yuklab (yt-dlp), kadr va matn chiqaradi | Ishlaydi, lekin transkripsiya uchun bulut kalitlari (Groq/OpenAI/Gemini) ixtiyoriy; brauzer cookie'laridan foydalanish imkoni bor. Bizda `analyze_samples.py` shu ishni lokal qiladi. |
| `taoufik123-collab/claude-watch` (MIT) | Yuqoridagining montajorcha varianti (kesish tezligi, "hook" tahlili) | Xuddi shunday; g'oyalari `analyze_samples.py` da bor. |
| `haidrrrry/claude-remotion-skill` (MIT) | Motion-dizayn qoidalari (Remotion uchun) | Kod emas, dizayn qoidalari. Ular bizning dvigatelga ko'chirildi: prujinali kirish, tez chiqish, ketma-ket paydo bo'lish, rang ishlovi, "nafas olish". |
| `runesleo/claude-video-kit` (MIT) | Ssenariydan tushuntiruvchi video (TTS bilan) | Bizning ishga (xom videoni montaj qilish) mos emas. |
| `zhuyansen/awesome-claude-video-skills` (CC0) | 244 ta video skill ro'yxati | Faqat katalog. Qidirish uchun foydali. |

## Remotion haqida xulosa

Remotion React kodi bilan video chizadi va brauzerda render qiladi. Kuchli tomoni: har videoga
maxsus sahna yozish oson. Zaif tomoni bu kompyuterda: video karta yo'q, render sekin; Node va
Chromium kerak; chatdan (watcher orqali) boshqarib bo'lmaydi, faqat Claude Code bilan.

Shuning uchun tartib: asosiy montaj bizning Python dvigatelida qoladi (tez, sinalgan, chatdan
ishlaydi). Remotion kerak bo'lsa **faqat maxsus sahnalar** uchun ishlatiladi: u shaffof fonli
video (ProRes 4444) chiqaradi, biz uni `image` yoki `broll` elementi qilib ustiga qo'yamiz.
Buning uchun tayyor prompt: `docs/REMOTION_PROMPT.md`.

Litsenziya (LICENSE.md bo'yicha): yakka shaxs, 3 xodimgacha bo'lgan tijoriy tashkilot va
notijorat tashkilotlar uchun bepul; kattaroq kompaniyaga pullik litsenziya kerak.
Manba: https://github.com/remotion-dev/remotion/blob/main/LICENSE.md
