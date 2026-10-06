# Claude Code'da ishlatish

Bu loyiha Claude Code uchun tayyor: `CLAUDE.md` → `AGENTS.md` (qoidalar), `docs/PLAYBOOK.md`
(montajor qo'llanmasi). `/montaj` va `/brend` buyruqlari `docs/claude_skills/` da, ruxsatlar taklifi
`docs/claude_settings.example.json` da tayyor turibdi: chatdan `.claude/` papkasiga yozib bo'lmaydi,
shuning uchun pastdagi birinchi tekshiruv promptida Claude Code ularni sizdan so'rab o'rnatadi.
Codex ham xuddi shu `AGENTS.md` ni o'qiydi.

## 1. Ochish

1. Watcher oynasi ochiq bo'lsa yoping (bir vaqtda bitta agent ishlaydi).
2. PowerShell'da:

   ```powershell
   cd "D:\Coding projects\editor pro"
   claude
   ```

   Claude Code o'rnatilmagan bo'lsa (rasmiy hujjat: https://code.claude.com/docs/en/setup):
   `irm https://claude.ai/install.ps1 | iex`

## 2. Model va kuch darajasi

| Ish | Model | Effort |
|---|---|---|
| Montaj (`/montaj`), yangi brend, skript yozish/tuzatish | `/model opus` | `/effort high` |
| Oddiy qayta render, kichik tuzatish, savol-javob | `/model sonnet` | `/effort medium` |

Montajda kadrlarni ko'rib baho berish va reja tuzish bor, shuning uchun kuchli model kerak.

## 3. Birinchi marta: tekshiruv prompti

Model: **opus**, effort: **high**. Shu matnni Claude Code'ga tashlang:

```text
Read AGENTS.md, docs/PLAYBOOK.md and docs/CLAUDE_CODE.md fully. New files were delivered into this
folder from a chat session and may not be committed yet (scripts/script_align.py, images.py,
html_render.py, icons.py, frames.py; changes in common.py, pipeline.py, elements.py, watcher.py,
selftest.py; assets/icons, assets/html, docs). Verify everything works on this Windows machine and
report to me in Uzbek, short numbered points. Do not install anything. Never open or print .env.

1. Run `git status` and `git log --oneline -5`. If jobs/watcher.json has an alive_at from the last
   10 seconds, stop and ask me to close the watcher window.
2. Run `.venv/Scripts/python.exe scripts/selftest.py`. Show me the NATIJA line and every line of
   section 7 (script alignment, icon, HTML render through Edge/Chrome, online image search). If a
   check fails, find the real cause and fix it; do not skip or weaken a check.
3. Open temp/selftest/karta.png and, if the online search ran, temp/selftest/images/candidates.jpg.
   Tell me honestly whether they look right and which image sources answered.
4. Skills: docs/claude_skills/montaj/SKILL.md and docs/claude_skills/brend/SKILL.md are ready but
   not installed. Check their frontmatter against the current Claude Code skills documentation,
   then copy them to .claude/skills/montaj/SKILL.md and .claude/skills/brend/SKILL.md (ask me
   first). Tell me how to confirm that /montaj appears. docs/claude_skills/ stays the tracked source.
5. Permissions: docs/claude_settings.example.json is a PROPOSAL for .claude/settings.json (project
   scripts run without prompts; .env is never read; nothing is written into input/ or samples/).
   Check every rule against the current Claude Code permissions documentation (Bash prefix/wildcard
   syntax, Read/Edit/Write path syntax, and how commands really run here: Git Bash vs PowerShell,
   forward vs back slashes). Correct the rules if needed, show me the final file, and write it only
   after I say yes. Do not propose broader permissions than the example intends.
6. When the selftest passes, commit everything with a clear message. If you changed any script,
   run `.venv/Scripts/python.exe scripts/selftest.py --no-whisper --offline` before committing.
```

## 4. Kundalik ish

```text
/montaj input\video.mp4 BREND
```

Skript bo'lsa: video yoniga shu nomli `.txt` qo'ying (`input\video.txt`) — o'zi topadi.
Skript ichida `[rasm: ...]`, `[stat: 85%]` kabi eslatmalar yozsangiz, o'sha joyga qo'yiladi.

Yangi mijoz: `/brend NOM @instagram`

Erkin so'rov ham bo'ladi (model: opus, effort: high):

```text
Edit input\video.mp4 for brand BREND following docs/PLAYBOOK.md. I want a strong hook title in the
first 2 seconds, a b-roll photo when I mention the office, and an icon row for the three benefits.
Show me the subtitle text and stills before rendering. Answer in Uzbek.
```

## 5. Rasm manbalari uchun kalitlar (ixtiyoriy, lekin tavsiya)

Kalitsiz ham ishlaydi (Openverse, Wikimedia, belgilar, HTML grafika). Sifatli stok foto va b-roll
video uchun bepul kalit oling va loyiha papkasida `.env` nomli fayl yarating (o'zingiz, Notepad'da):

```text
PEXELS_API_KEY=bu_yerga_kalit
PIXABAY_API_KEY=bu_yerga_kalit
GEMINI_API_KEY=bu_yerga_kalit
```

- Pexels: https://www.pexels.com/api/ (bepul, soatiga 200 so'rov)
- Pixabay: https://pixabay.com/api/docs/ (bepul)
- Gemini (AI rasm, pullik bo'lishi mumkin): https://aistudio.google.com/apikey

`.env` gitga kirmaydi. Kalitni chatga yoki Claude Code'ga yozmang, faqat shu faylga.

AI rasm kaliti qo'shilgach bir marta tekshirtiring (model: **opus**, effort: **high**):

```text
I added GEMINI_API_KEY to .env (do not open or print that file). Verify scripts/images.py `ai`
against the current official docs at https://ai.google.dev/gemini-api/docs/image-generation:
endpoint, model id in style/style.json (images.ai.model), request body and where the image bytes
are in the response. Then run one real test:
`.venv/Scripts/python.exe scripts/images.py ai "flat minimal illustration of a yellow rocket on dark background" --name ai_test --out temp/selftest/images`
Open the result and show me. If the API differs from the code, fix scripts/images.py (keep the
key out of logs and errors), run `scripts/selftest.py --no-whisper --offline`, commit, and explain
in Uzbek what changed. Tell me the price per image if the docs state it.
```

## 6. Harakatli grafika kerak bo'lsa

Tizimdagi grafika (subtitr, kartochka, ro'yxat, belgi, HTML rasm) yetmasa va to'liq animatsiyali
sahna kerak bo'lsa: `docs/HYPERFRAMES_PROMPT.md` (HTML → shaffof video, Apache-2.0) yoki
`docs/REMOTION_PROMPT.md`. Ikkalasi ham Node.js talab qiladi, shuning uchun ixtiyoriy.
