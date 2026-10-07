# Codex bilan ishlash

Joriy umumiy sozlama: [AGENT_SETUP.md](AGENT_SETUP.md). To'rtta skill va mahalliy MCP
tayyor; qayta o'rnatishdan oldin `sync_skills.py --check` bilan tekshiring. Ikkala agentning
tajribasi [AGENT_MEMORY.md](AGENT_MEMORY.md), har video sifat tartibi [EDIT_QUALITY.md](EDIT_QUALITY.md).

Codex loyihadagi `AGENTS.md` ni o'zi o'qiydi: montaj qoidalari, skriptlar va uslub o'sha yerda. Claude Code
ham xuddi shu faylni o'qiydi. Ikki turli videoda parallel ishlash mumkin: [PARALLEL.md](PARALLEL.md).
Har video eslatmasi va egasi alohida, CPU ishlari navbatda. Pastdagi eski o'rnatish promptlari
faqat boshqa agentning unfinished videosi bo'lmagan texnik sessiyada ishlatiladi; montajda
per-video handoff va parallel qoidalar AGENTS.md bo'yicha ustun.

## Model va kuch

Codex'da eng kuchli modelni va `high` kuchni (reasoning effort) tanlang. Rasmiy hujjatga ko'ra bular
`config.toml` dagi `model` va `model_reasoning_effort` kalitlari; aniq model nomini va qanday
almashtirishni birinchi promptda Codex'ning o'zi aytib beradi (taxmin qilinmaydi).

## Birinchi marta: o'rnatish prompti

Codex'ni loyiha papkasida (`D:\Coding projects\editor pro`) oching va shuni yuboring:

```
You are joining an existing project as the second agent. Claude Code is the first; the user runs
you one at a time and switches when one of you hits a usage limit. Talk to me in Uzbek, in short
numbered steps. I am a beginner programmer and a professional video editor.

Do this setup now. Do not edit scripts, style/ or brands/ in this run.

1. Read fully: AGENTS.md, docs/PLAYBOOK.md, docs/NAMUNA_USLUBI.md. They are the source of truth.
   Never guess a command, flag or field: check --help or the code first.
2. Run: .venv\Scripts\python.exe scripts\handoff.py show
   Tell me what state the project is in and whether there is unfinished work.
3. Run: .venv\Scripts\python.exe scripts\selftest.py
   Report the result line. If a check fails, find the real cause and tell me; do not weaken a check.
4. Skills. docs/claude_skills/ has four skills written for Claude Code: montaj, namuna, brend,
   transcribe-uz. Check YOUR current official skills documentation for (a) the folder where
   repo-level skills must live, (b) the required SKILL.md frontmatter, (c) how I invoke a skill.
   Tell me what you found, then ask me before copying. When I agree, install the four skills
   there, changing only what your format requires (for example Claude-only frontmatter fields or
   the $ARGUMENTS placeholder). Keep the instructions themselves identical. docs/claude_skills/
   stays the tracked source: if a skill changes there later, yours must be updated from it.
5. Tell me exactly which model and reasoning effort you are running with now, and the exact way
   to set the strongest model with high effort in my Codex (config file key or command). Quote
   your documentation; if you are not sure, say so.
6. Confirm these rules back to me in one short list:
   - separate videos may be edited in parallel; start with handoff.py show and use handoff.py
     set "..." --video VIDEO --agent codex after every milestone; respect ownership and CPU queue
   - never open, print or commit .env; never write into input/ or samples/
   - subtitle text is shown to me and approved before it is burned in; an approval counts only
     if it is written in HOLAT.md, otherwise ask again
   - new downloads, installs and deletions need my yes first
   - no commits during parallel editing; shared changes and selftest only when the other agent is idle; never merge
   - you cannot hear audio or see motion: for sound choices render two variants and let me listen
7. Commit only if you added files (skills). Then write handoff.py set with what you did.
```

## O'z video sessiyasini davom ettirish (limit tugaganda)

Avvalgi egasi o'z video sessiyasini davom ettirishi uchun:

```
Continue YOUR assigned video <VIDEO>. First run
.venv\Scripts\python.exe scripts\handoff.py show, then show --video <VIDEO>; read git status and git log -5.
Tell me in Uzbek, in 3-5 lines, where the work stands and what you will do next, then continue
from the "next step" in the note. Do not redo finished steps and do not assume any approval that
is not written in THIS video's note. Keep writing handoff.py set "..." --video <VIDEO> --agent
<your name> as you go. If another agent owns this video, stop and tell me; never overwrite its note.
Respect AGENTS.md parallel rules: only your folder and style, no shared edits/selftest/commits.
```

Claude Code uchun bu promptda: `/model opus`, `/effort high`. Codex uchun: eng kuchli model, `high`.

## Montaj buyurish

Skillar o'rnatilgach Codex'da `/skills` orqali yoki nomi bilan chaqiriladi (aniq usulini 4-qadamda
Codex aytadi). Skillsiz ham ishlaydi:

```
Edit input\video.mp4 for brand NAME in the sample style. Follow docs/claude_skills/namuna/SKILL.md.
```
