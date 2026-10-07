---
name: brend
description: Onboard a new client brand into this video editing project (brand folder, colours, fonts, logo, caption style, end card). Use when the user names a new client or brand, or gives a client's Instagram.
---

# /brend — add a new client brand

Arguments: `<arguments supplied in the user prompt>`. Talk to the user in **Uzbek**, short numbered steps.

1. Read `AGENTS.md` sections "Uslub va brendlar" and "Yangi mijoz (brend) qo'shish".
2. Collect what exists; never invent brand facts. Needed: brand name, logo (transparent PNG),
   main colour, Instagram handle. Optional: font files, music, reference reels in
   `samples/<brand>/`, product/office photos for `brands/<brand>/assets/`.
3. If the user gave an Instagram handle, you may look at the public profile with WebFetch to note
   visible colours, tone and typical content. Instagram often blocks this: if it fails, say so and
   ask the user for 3–5 screenshots or reference reels instead. Do not download images from the
   profile; logos and photos must come from the user.
4. Create the brand: `.venv/Scripts/python.exe scripts/new_brand.py <name> --title "..." --handle @... --logo <path>`
   (check `--help` for the exact options). Show the detected accent colour and confirm it.
5. If reference reels exist: `scripts/analyze_samples.py --brand <name>`, open the generated
   sheets, and fill `brands/<name>/brand.json` (caption preset and position, look preset, zoom).
   Ask about anything audio-related; you cannot hear.
6. Prove it on a real frame: run `/montaj`-style `--stills` on any video with `--brand <name>`,
   show the image, adjust until the user agrees.
7. `git commit` the new brand folder.
