# Remotion qo'shimchasi uchun prompt (ixtiyoriy)

Bu faqat har videoga maxsus chizilgan sahnalar kerak bo'lganda kerak (masalan mahsulot animatsiyasi,
murakkab diagramma). Oddiy montaj uchun shart emas.

Qanday ishlatiladi: `D:\Coding projects\editor pro` papkasida Claude Code'ni oching va pastdagi
matnni joylang. Tavsiya: model **Opus**, effort **high** (loyiha qurish murakkab ish).
Boshlashdan oldin watcher oynasini yoping (bir vaqtda bitta agent ishlaydi).

```
Read AGENTS.md first and follow its rules. This repo already has a working FFmpeg + Python
montage system (scripts/, brands/, style/). Do NOT replace or refactor it.

Goal: add Remotion ONLY as an optional generator of custom motion-graphics clips with a
transparent background. The existing compositor (scripts/compose.py) already overlays
transparent videos: an element {"type": "broll", "mode": "full", "file": "<clip>"} or
{"type": "image", "file": "<clip>", ...} in temp/<job>/elements.json accepts ProRes 4444
(.mov) and VP9-alpha (.webm).

Steps, and stop to ask me before each install:
1. Check Node.js LTS (winget OpenJS.NodeJS.LTS). I am a solo editor, so the free Remotion
   license applies; remind me of https://www.remotion.pro/license.
2. Create a Remotion project in remotion/ (TypeScript, blank template). Install the official
   agent skills with: npx skills add remotion-dev/skills
   Confirm the exact current commands from the Remotion docs before running them; do not guess.
3. Make one composition "Overlay" (1080x1920, 30 fps) that reads props from a JSON file:
   brand colors and font from brands/<name>/brand.json, plus a list of scenes.
4. Add scripts/remotion_overlay.py: takes --brand, --props FILE, --out temp/<job>/overlays/NAME.mov,
   runs the Remotion render with a transparent background (confirm the correct flags for
   ProRes 4444 with alpha in the Remotion docs), concurrency 2, prints free RAM first, and
   verifies with ffprobe that the output has an alpha channel.
5. Test: render a 3-second overlay, add it to an elements.json as a full-frame broll, run
   .venv\Scripts\python.exe scripts\compose.py with --stills, look at the stills, report.
6. Update AGENTS.md (short section "Remotion overlays") and git commit.

I am a beginner: explain each step briefly in Uzbek. Add remotion/node_modules and
remotion/out to .gitignore. Never touch input/ or samples/.
```
