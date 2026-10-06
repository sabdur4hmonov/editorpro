# HyperFrames'ni qo'shish (ixtiyoriy)

**Nima:** HyperFrames (https://github.com/heygen-com/hyperframes, Apache-2.0) HTML/CSS va
animatsiyani videoga aylantiradi, shaffof fonli natija ham beradi (WebM yoki ProRes 4444 MOV).
Instagramda "Claude Code bilan montaj" qilayotganlarning ko'pi motion-grafikani shu yoki Remotion
bilan qiladi. Bizda u **faqat harakatli ustma-qatlam** yasash uchun kerak bo'ladi: kesish, subtitr,
brend, ovoz va yakuniy render o'zimizning `scripts/` da qoladi.

**Qachon kerak:** oddiy elementlar (`stat`, `list`, `icon`, `callout`, HTML rasm) yetmaganda:
harakatli grafik, logotip animatsiyasi, murakkab kinetik matn.

**Talablar (README bo'yicha):** Node.js 22+ va FFmpeg. Node o'rnatilmagan bo'lsa bu yangi dastur,
Claude Code avval so'raydi.

**Holat:** bu chatdan sinab ko'rilmagan (bulutda npm yopiq). Quyidagi prompt Claude Code'ga
o'rnatib, bitta test bilan isbotlashni topshiradi.

Model: **opus**, effort: **high**.

```text
Read AGENTS.md, docs/PLAYBOOK.md and docs/HYPERFRAMES_PROMPT.md. I want HyperFrames added to this
project ONLY as a generator of transparent animated overlays. Cutting, captions, brand, audio and
the final render stay in scripts/. Answer me in Uzbek, short numbered steps.

1. Check prerequisites: `node --version` (needs 22+), `ffmpeg -version`. If Node is missing or
   older, stop and ask me before installing anything (tell me the exact winget command you would run).
2. Read the current HyperFrames README and docs/guides/rendering.mdx from
   https://github.com/heygen-com/hyperframes and follow THEM, not your memory, for install and
   render commands. At the time this file was written the README said:
     claude plugin marketplace add heygen-com/hyperframes
     claude plugin install hyperframes@hyperframes
   and transparent output was `npx hyperframes render --format webm --output overlay.webm`
   (or `--format mov` for ProRes 4444). Verify these are still correct before running them.
3. Create the HyperFrames workspace in `motion/` at the project root (not inside scripts/). Add
   `motion/node_modules/` and render caches to .gitignore.
4. Build one test composition: a 3-second 1080x1920 transparent overlay with an animated stat
   card ("+85%" counting up, brand accent colour from brands/demo/brand.json, font Inter from
   style/fonts). Leave html/body background unpainted so the output stays transparent.
5. Render it to `temp/hyperframes/test_overlay.webm`. Prove the alpha channel exists:
   `ffmpeg -c:v libvpx-vp9 -i temp/hyperframes/test_overlay.webm -frames:v 1 -pix_fmt rgba temp/hyperframes/frame.png`
   and check the PNG really has transparent pixels (use Python + Pillow from .venv).
6. Put it on a real video through our compositor: add
   {"type": "broll", "mode": "full", "file": "temp/hyperframes/test_overlay.webm", "start": 1, "end": 4}
   to an elements.json for temp/selftest's test video, run compose/pipeline with --stills at 1.5,2.5,3.5
   and open the stills. The overlay must sit on top of the footage with the footage visible around it.
7. If everything works: document the workflow in AGENTS.md (a short "Harakatli ustma-qatlam
   (HyperFrames)" section: where compositions live, the render command, how to place the result),
   run `.venv/Scripts/python.exe scripts/selftest.py --no-whisper --offline`, and commit.
8. If something does not work on this machine (4 cores, no GPU), tell me plainly what failed and
   what you tried. Do not leave a half-installed setup: remove what you added or explain what remains.
```
