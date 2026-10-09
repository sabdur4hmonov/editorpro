# Video formatlari (8 namuna) — qo'llanma

Bu fayl `docs/formats/formats.json` dan yasaladi: `.venv\Scripts\python.exe scripts\formats.py guide`.
Qo'lda tahrir qilmang — JSON ni tahrir qilib, qayta yarating.

**Qanday ishlatiladi.** Montaj boshida: `formats.py plan VIDEO [--words temp/<nom>/orig.words.json]` xom videoni
o'lchaydi (yuz, ikki kishi, qarash yo'nalishi, yuz kattaligi, fonlar soni, kesishlar, silkinish, ovoz kadr ortidanmi,
bo'lingan ekran, tepadagi savol kartochkasi), formatni va uslub guruhini tanlaydi, sababini bir qatorda yozadi.
Tasdiq xabarida ikkala tanlov sababi bilan ko'rsatiladi. Aniq bo'lmasa (`needs_editor_judgement`) agent kadrlarga
qarab hal qiladi va kuzatganini `--features-extra '{"costume": true}'` bilan beradi. Foydalanuvchi tuzatsa:
`formats.py record VIDEO --format X --group Y --verdict approved|rejected` — keyingi o'xshash videoda hisobga olinadi.

**Dalil qoidasi.** Har xulosa: video, vaqt, kadr; ishonch; muqobil izoh. 3 tadan kam videoda ko'ringan = *kuzatuv*
(observation). Namunalar boshqalarning ishi: faqat uslub olinadi, logotip/musiqa/footage/shrift ko'chirilmaydi.
Belgilar xom videoga emas, tayyor videoga qarab o'lchangan: xom videoda kesish va grafika hali yo'q, shuning uchun
kesish/fon qoidalari klip papkasi yoki ko'p kadrli xom materialda ishlaydi.

| Format | Qisqacha | Dalil sinfi | Mos namunalar |
|---|---|---|---|
| **Talking head** (`talking_head`) | One speaker to camera in one (studio) setup; graphics explain the points around the body, not on the face. | pattern | s02 (high), s05 (high), s06 (high), s09 (medium), s16 (medium), s33 (high), s34 (medium), s40 (medium), s42 (high) |
| **Interview** (`interview`) | Guest answers an off-camera host (podcast or street mic); the person looks past the lens; small sentence subtitles. | pattern | s13 (high), s30 (high), s31 (medium), s32 (high), s36 (high), s38 (high), s15 (low) |
| **Kadr rakursli** (`kadr_rakursli`) | Cinematic multi-angle: the same person in many shots/places (wide, back, aerial, close), often voice-over; giant condensed word + scattered small words. | pattern | s14 (high), s22 (high), s12 (medium), s23 (medium), s27 (high), s26 (medium), s28 (medium) |
| **Syudjetli** (`syudjetli`) | Story / plot: staged scenes act out what is said (car, notebook, sticky notes, screenshots), the speaker is a character in his own story. | pattern | s29 (high), s19 (high), s11 (medium), s28 (medium) |
| **Obrazli** (`obrazli`) | Character / persona: the speaker plays a role (costume, theatre light), a metaphor carries the message; slow, dark, minimal text. | observation | s28 (medium), s24 (low) |
| **Savol javob** (`savol_javob`) | Answer to a follower question: the question card stays on screen, one selfie take, no other graphics. | observation | s30 (low) |
| **Tepa-past** (`tepa_past`) | Split screen: speakers on top, matching b-roll at the bottom, word-by-word captions in a black band between. | observation | — |
| **Birinchi yuzdan** (`birinchi_yuzdan`) | First person, extreme close-up into the lens; one take; a title + checklist builds next to the face as items are said. | observation | s04 (low), s10 (low) |

## Talking head (`talking_head`) — pattern

One speaker to camera in one (studio) setup; graphics explain the points around the body, not on the face.

**Belgilangan namuna:** `samples/Talking head.mp4`
- 0.6-4.8 glowing serif digits 1/2/3 orbit the seated speaker, '1' scales up to ~45% H (overview_01)
- 5.6-9.4 phone screen recordings fly in as tilted 2.5D cards and fill the frame (overview_01)
- 12.8 keyword pair 'reelsda / probnyy' on glass bars, glow, ~5% H at 50-65% y (m_grid_12.8)
- measured: face 0.80, gaze_off 0.0, 3 setups (= inserted phone screens), 3.2 cuts/min, no full subtitles

**Mos namunalar (1-42):**
- s02 (high): seated, numbered list with thumbnails, 0 cuts (mosaic)
- s05 (high): seated on bench, list + big number 18, 8.8 cuts/min
- s06 (high): standing, glass right/wrong cards, 0 cuts in 95 s
- s09 (medium): seated + drawn graphic scenes
- s16 (medium): seated, phone UI cards
- s33 (high): seated at desk, grid statistics, prop entrance
- s34 (medium): standing on campus, one setup + paper cards
- s40 (medium): standing, one location, 8.5 cuts/min
- s42 (high): seated, locked camera, persistent bracket graphic, 0 cuts

**Xom videodan tanib olish:** one person, eyes to the lens (gaze_off <= 0.2), face in most frames, 1-3 backgrounds, little voice-over.
<br>Qoidalar (ball): face_ratio [0.7, None] → +2; gaze_off [None, 0.2] → +2; setups [None, 3] → +2; two_face_ratio [None, 0.25] → +1; vo_ratio [None, 0.25] → +1; face_height_median [0.06, 0.34] → +1; cuts_per_min [None, 12] → +1; gaze_off [0.4, None] → -4; face_height_median [0.4, None] → -3; top_card True → -4; setups [5, None] → -2; vo_ratio [0.4, None] → -2; split_line [0.9, None] → -6

**Tuzilma:** hook claim or number (<=1.5 s) -> numbered points, each with one visual -> short summary -> CTA (spoken or follow card).
**Kesish:** cuts only to remove silences/repeats; visual change comes from graphics and zoom punch every 2-4 s; calm 3-5 s stretches allowed.
**Subtitr:** full subtitles or keywords-only; preset `clean`, balandligi [3.0, 5.5] % H, joyi y [0.55, 0.72] — example uses keyword-only glass bars; samples A use lowercase lockups
**Grafika:** count, list, object, comparison, stat, screen; daqiqasiga [6, 16]
**B-roll:** rare; screen recordings / product shots as 2.5D cards rather than full cutaways
**Ovoz:** speech first; light SFX on graphic entrances (stronger + subtle rendered)
**Xatolar:** graphics over the face; a label repeating the subtitle; constant zoom pulsing; no calm stretch for a long explanation
**Sifat nishonlari (quality gate):** kesish/min [0, 18], grafika/min [4, 16], orasida kamida 0.8 s, sokin bo'lak 3.0 s, subtitr [2.5, 6.0] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 3%
**Uslub guruhlari:** A_studio_explainer, B2_kinetic_creator, B1_editorial_paper — seated/static speaker with explainer graphics (A members s02 s05 s06 s09 s16 s25 s33 s42)

## Interview (`interview`) — pattern

Guest answers an off-camera host (podcast or street mic); the person looks past the lens; small sentence subtitles.

**Belgilangan namuna:** `samples/Interview.mp4`
- one locked shot, headphones + mic, 0 cuts in 54.9 s (contact)
- one-line sentence subtitles, white ~2.4% H at 48-50% y, no word animation (m_grid_8.6)
- brand watermark at ~75% y
- measured: gaze_off 0.97, face 1.0, 2 setups

**Mos namunalar (1-42):**
- s13 (high): seated guest looking off-camera, B&W intro, office b-roll; gaze_off 0.43
- s30 (high): street mic interview, question title at top; gaze_off 0.54
- s31 (medium): two people standing (two_face 0.89) but both face the lens (gaze_off 0.13): duo-to-camera interview; detector ranks talking_head first
- s32 (high): graduate testimonials seated; two_face 0.43, gaze_off 0.49
- s36 (high): seated guest in profile; gaze_off 1.0
- s38 (high): two women seated conversation; two_face 0.41, gaze_off 0.65
- s15 (low): dark studio, speaker looks off-camera (gaze_off 0.62) but kinetic edit (B2)

**Xom videodan tanib olish:** person turned away from the lens (gaze_off >= 0.4) and/or two people in frame; mic/headphones; long answers.
<br>Qoidalar (ball): gaze_off [0.4, None] → +4; gaze_off [0.8, None] → +2; two_face_ratio [0.3, None] → +3; vo_ratio [None, 0.3] → +1; face_ratio [0.65, None] → +1; split_line [0.9, None] → -4; mic_or_headphones True → +2; interviewer_voice True → +3

**Tuzilma:** strongest answer first (cold open) -> question as title -> answer -> second answer / proof -> name + CTA.
**Kesish:** keep long calm answers (C median shot 8 s); cut repeats and the host's filler; b-roll only where the guest names something concrete.
**Subtitr:** sentence subtitles, one line; preset `clean`, balandligi [2.2, 3.5] % H, joyi y [0.48, 0.7] — no word-by-word animation in the example
**Grafika:** name_tag, question_title, stat, object; daqiqasiga [1, 6]
**B-roll:** sparse, concrete nouns only; never during an emotional answer
**Ovoz:** room tone kept; music very low or none; SFX minimal (sfx off or subtle)
**Xatolar:** kinetic word animation over a calm answer; graphics every 3 s; cutting the guest's pauses that carry emotion; covering the mic/face with a name tag
**Sifat nishonlari (quality gate):** kesish/min [0, 20], grafika/min [0, 6], orasida kamida 2.0 s, sokin bo'lak 6.0 s, subtitr [2.0, 4.0] % H, birinchi yozuv ≤ 1.5 s, yuzni yopish ≤ 2%
**Uslub guruhlari:** C_interview_testimonial, A_studio_explainer — small captions, long calm answers, name tags (C members s04 s08 s10 s13 s30 s31 s32 s38)

## Kadr rakursli (`kadr_rakursli`) — pattern

Cinematic multi-angle: the same person in many shots/places (wide, back, aerial, close), often voice-over; giant condensed word + scattered small words.

**Belgilangan namuna:** `samples/Kadr rakursli.mp4`
- 0.2-2.4 giant red condensed 'DARAXT' ~22% H (10-34% y) behind a wind turbine, small words spread across the width at 40% y appear one by one (m_grid_1.6)
- 3.8 'SAHRO' fades in on a new desert shot
- 4.6-6.0 motion-blurred running shot, words 'ko'kat u joyda / 2yil tursa' spread with big gaps ~4% H (m_grid_5.8)
- 6.2-8.0 same face ages (grey beard) in a static close-up
- measured: 10 setups, 19.4 cuts/min (median shot 2.1 s), voice-over 58%, face height median 0.07 (wide shots)

**Mos namunalar (1-42):**
- s14 (high): same speaker in 7 park setups, 18.7 cuts/min
- s22 (high): 13 setups, walking shots, 22.7 cuts/min
- s12 (medium): 13 setups, 22.2 cuts/min, film b-roll
- s23 (medium): 11 setups, 27 cuts/min
- s27 (high): 13 setups, voice-over 62%, wide shots (face 0.05), 38 cuts/min
- s26 (medium): 12 setups, on-camera speech (vo 0.0)
- s28 (medium): 11 setups, 30 cuts/min (also syudjetli/obrazli traits)

**Xom videodan tanib olish:** many different backgrounds (setups >= 5), frequent cuts, wide/back shots with small faces, often voice-over.
<br>Qoidalar (ball): setups [5, None] → +2; cuts_per_min [10, None] → +2; face_height_median [None, 0.12] → +2; vo_ratio [0.5, None] → +2; dark True → -2; face_ratio [None, 0.5] → +1

**Tuzilma:** image-led: one strong word per shot; metaphor carried by locations; the speaker appears in a few anchor close-ups.
**Kesish:** cut on phrases, shot median ~2 s (1.2-3.2), each sentence a new angle; hold the emotional close-up longer.
**Subtitr:** keyword titles + scattered small words, no full subtitle block; preset `caps`, balandligi [2.0, 22.0] % H, joyi y [0.1, 0.55] — giant word can sit behind the person/object (behind_person)
**Grafika:** keyword_title, object; daqiqasiga [6, 20]
**B-roll:** the footage IS the b-roll: many angles of the same subject; stock only for metaphors
**Ovoz:** music bed under voice-over is typical (agent cannot judge); whoosh on hard location changes
**Xatolar:** full subtitles covering the cinematic image; graphics cards that fight the scenery; same angle twice in a row
**Sifat nishonlari (quality gate):** kesish/min [10, 40], grafika/min [4, 20], orasida kamida 0.6 s, sokin bo'lak 2.0 s, subtitr [2.0, 24.0] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 5%
**Uslub guruhlari:** B2_kinetic_creator, D_cinematic_commercial, B1_editorial_paper — kinetic creator edits with many walking/location shots (B2 s12 s14 s22 s23 s26 s27 s28)

## Syudjetli (`syudjetli`) — pattern

Story / plot: staged scenes act out what is said (car, notebook, sticky notes, screenshots), the speaker is a character in his own story.

**Belgilangan namuna:** `samples/Syudjetli.mp4`
- 0.2-2.6 'MEN ISHDAN' red condensed caps (~10% H) + white 'bo'shadim' stacked at the top while he walks to a car (overview_01)
- 2.8-5.0 'VA onlayn maktab' lockup builds word by word (m_grid_4.6)
- 6.8 '7K$' red number + 'pul topish kerak' on a brick-wall close-up
- 10.0 '"MAC" BILAN' over a Dutch-angle laptop shot (m_grid_10.4)
- 15.0-16.0 profile-activity cards stack up one per word; 16.4 grid of view-count screenshots
- 17.6-19.0 notebook page turns: 'KONTENT MARKETING' -> 'AUDITORIYA YIG'ISH + SOTUV' written by hand
- measured: 16 setups, 24.8 cuts/min, voice-over 38%

**Mos namunalar (1-42):**
- s29 (high): staged visa story with an actress, B&W for setbacks, 20.9 cuts/min
- s19 (high): brand story ad with actors and chat UI, 13.9 cuts/min
- s11 (medium): staged family/subway scenes + speaker, 15.2 cuts/min
- s28 (medium): skit: same actor as human (warm) and AI (blue)

**Xom videodan tanib olish:** many setups (>= 8), staged inserts with props or other actors, speaker sometimes absent while talking (voice-over 20-50%).
<br>Qoidalar (ball): setups [8, None] → +2; cuts_per_min [15, None] → +1; face_ratio [0.4, 0.85] → +1; vo_ratio [0.2, 0.55] → +2; staged_scenes True → +4; props True → +2

**Tuzilma:** setup (status quo) -> turning point -> problem with a number -> plan -> proof (screens, numbers) -> offer -> CTA.
**Kesish:** one shot per sentence (median 2.3 s); match the action to the words (car on 'ishdan', laptop on 'MAC').
**Subtitr:** lockup titles carry the speech: red hero word + white small words, word by word; no extra subtitle block; preset `caps`, balandligi [4.0, 11.0] % H, joyi y [0.08, 0.32]
**Grafika:** keyword_title, object, stat, stack, screen; daqiqasiga [8, 24]
**B-roll:** staged own footage first; screenshots/proof as stacked cards
**Ovoz:** music + SFX on scene changes are typical (agent cannot judge)
**Xatolar:** subtitles AND lockup titles at the same time (double text); props that do not match the word; slow first scene
**Sifat nishonlari (quality gate):** kesish/min [12, 40], grafika/min [6, 24], orasida kamida 0.6 s, sokin bo'lak 2.0 s, subtitr [3.0, 12.0] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 5%
**Uslub guruhlari:** B2_kinetic_creator, B1_editorial_paper, D_cinematic_commercial — story edits with staged scenes and kinetic lockups (s29 B1, s19/s11 D, s28 B2)

## Obrazli (`obrazli`) — observation

Character / persona: the speaker plays a role (costume, theatre light), a metaphor carries the message; slow, dark, minimal text.

**Belgilangan namuna:** `samples/Obrazli.mp4`
- magician / joker character on a dark stage, spotlights, black frames between beats (contact 2.96-14.8)
- 28.8-31.8 card trick close-up; tiny light captions 'Nozik / harakatlar / natijasi' stepped, ~2.5% H at 70-78% y (m_grid_31.0)
- 32.0-35.0 single word per beat 'BU', 'HARAKATLAR', 'SHUNCHALIK' ~1.5% H at the top
- 62.1 'ko'rishga qiluvchi' top-left in negative space
- measured: dark, voice-over 58%, 6 setups, 15.9 cuts/min but long holds (max 17.8 s)

**Mos namunalar (1-42):**
- s28 (medium): the same actor plays an AI double, colour-coded blue vs warm
- s24 (low): dark theatrical look, small captions (dark=true)

**Xom videodan tanib olish:** costume / character or theatrical lighting (agent), dark frames, long voice-over passages.
<br>Qoidalar (ball): dark True → +2; vo_ratio [0.4, None] → +2; face_ratio [None, 0.6] → +1; costume True → +5; theatre_light True → +2

**Tuzilma:** mysterious opening -> reveal of the metaphor -> transfer to the real topic -> offer -> calm ending.
**Kesish:** slow; long holds and black beats; cut on gestures, not on words.
**Subtitr:** tiny single words / short phrases in negative space, stepped; preset `single`, balandligi [1.2, 3.0] % H, joyi y [0.1, 0.8]
**Grafika:** keyword_small; daqiqasiga [0, 4]
**B-roll:** none; the performance is the picture
**Ovoz:** mood music and room tone (agent cannot judge)
**Xatolar:** big kinetic captions; stickers/emoji; filling every pause
**Sifat nishonlari (quality gate):** kesish/min [4, 20], grafika/min [0, 4], orasida kamida 3.0 s, sokin bo'lak 6.0 s, subtitr [1.0, 3.5] % H, birinchi yozuv ≤ 2.0 s, yuzni yopish ≤ 2%
**Uslub guruhlari:** D_cinematic_commercial, B2_kinetic_creator — cinematic, image-first edit (D)

## Savol javob (`savol_javob`) — observation

Answer to a follower question: the question card stays on screen, one selfie take, no other graphics.

**Belgilangan namuna:** `samples/Savol javob.mp4`
- Instagram question sticker 'Qanaqa savollar bor? / Aka kursizni tekinga padarka qilaszmi?' at 5-10% y for the whole video (overview_01)
- phone selfie, one take, 1.7 cuts/min, no subtitles
- measured: top_card true, face height 0.36, gaze_off 0.0

**Mos namunalar (1-42):**
- s30 (low): question title at the top 'O'ZINGIZNI QANDAY HIS QILYAPSIZ?' (interviewer question, not a follower question)

**Xom videodan tanib olish:** persistent question card at the top (top_card) or the user gives the question; selfie framing; single take.
<br>Qoidalar (ball): top_card True → +5; setups [None, 2] → +1; cuts_per_min [None, 3] → +1; gaze_off [None, 0.1] → +1; question_given True → +4

**Tuzilma:** question card from frame 0 -> direct answer in the first sentence -> reason / example -> advice -> CTA (ask more questions).
**Kesish:** remove silences and repeats only; keep it one continuous take feeling.
**Subtitr:** optional small subtitles below the face; the question card is the main text; preset `clean`, balandligi [2.5, 4.0] % H, joyi y [0.6, 0.75]
**Grafika:** question_card; daqiqasiga [0, 3]
**B-roll:** none
**Ovoz:** voice only
**Xatolar:** hiding the question after the first seconds; heavy graphics that make it look less personal
**Sifat nishonlari (quality gate):** kesish/min [0, 8], grafika/min [0, 3], orasida kamida 3.0 s, sokin bo'lak 8.0 s, subtitr [2.0, 4.5] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 2%
**Uslub guruhlari:** A_studio_explainer, C_interview_testimonial — single speaker, calm, text-light (A defaults with fewer graphics)

## Tepa-past (`tepa_past`) — observation

Split screen: speakers on top, matching b-roll at the bottom, word-by-word captions in a black band between.

**Belgilangan namuna:** `samples/Tepa-past.mp4`
- top 0-40%: two people at a desk with a laptop (m_grid_2.0)
- 40-46%: black band with word-by-word captions, active word white, others grey ~3% H
- 46-100%: b-roll that shows exactly what is said (burning car, cup, TikTok clips), cut every ~3 s while the top stays
- measured: split_line 1.0, two_face 1.0, 15.7 cuts/min (bottom)

**Mos namunalar (1-42):** topilmadi — qoidalar *kuzatuv*.

**Xom videodan tanib olish:** persistent horizontal seam in the middle (split_line >= 0.9) in finished videos; for raw footage: a conversation/talking head plus enough topic b-roll.
<br>Qoidalar (ball): split_line [0.9, None] → +8; two_face_ratio [0.3, None] → +1; broll_available True → +3

**Tuzilma:** story told by the speakers; every concrete noun gets a bottom clip; top never cuts away.
**Kesish:** top: continuous; bottom: one clip per idea, 2-4 s.
**Subtitr:** karaoke band between the halves (active word white, rest grey); preset `karaoke`, balandligi [2.5, 3.5] % H, joyi y [0.42, 0.46]
**Grafika:** broll_bottom; daqiqasiga [10, 24]
**B-roll:** mandatory and continuous (broll mode split, layout_morph in/out)
**Ovoz:** speech only from the top; b-roll muted
**Xatolar:** b-roll that does not match the words; captions over the faces; empty bottom half
**Sifat nishonlari (quality gate):** kesish/min [8, 30], grafika/min [8, 24], orasida kamida 1.5 s, sokin bo'lak 0 s, subtitr [2.0, 4.0] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 2%
**Uslub guruhlari:** C_interview_testimonial, B2_kinetic_creator — conversation on top (C), continuous b-roll below

## Birinchi yuzdan (`birinchi_yuzdan`) — observation

First person, extreme close-up into the lens; one take; a title + checklist builds next to the face as items are said.

**Belgilangan namuna:** `samples/Birinchi yuzdan.mp4`
- face fills the right half (face height 0.65 of frame), eyes to the lens (contact)
- title 'Kontent yaratish / formulasi :' white + yellow bold at 18-30% y on the left, from frame 0 (m_grid_6.7)
- checklist adds one line per spoken item (0.29 -> 7.83), ~4.5% H, 35-72% y left, never over the face
- measured: 1 setup, 0 cuts, gaze_off 0.0, landscape 4:3 source

**Mos namunalar (1-42):**
- s04 (low): selfie round-video testimonials inside the edit
- s10 (low): selfie round-video testimonials inside the edit

**Xom videodan tanib olish:** very large face (face_height >= 0.4) looking into the lens, single take, no cuts.
<br>Qoidalar (ball): face_height_median [0.4, None] → +4; gaze_off [None, 0.1] → +1; setups [None, 1] → +1; cuts_per_min [None, 3] → +1; top_card True → -2

**Tuzilma:** title states the topic -> each spoken step appears as a checklist line -> last line = action.
**Kesish:** single take; remove only silences.
**Subtitr:** checklist lines instead of subtitles (or tiny subtitles); preset `clean`, balandligi [3.5, 5.5] % H, joyi y [0.15, 0.75]
**Grafika:** list; daqiqasiga [4, 40]
**B-roll:** none
**Ovoz:** voice only
**Xatolar:** list over the face; all items shown before they are said
**Sifat nishonlari (quality gate):** kesish/min [0, 6], grafika/min [2, 50], orasida kamida 0.4 s, sokin bo'lak 0 s, subtitr [3.0, 6.0] % H, birinchi yozuv ≤ 0.3 s, yuzni yopish ≤ 2%
**Uslub guruhlari:** A_studio_explainer, B1_editorial_paper — single take explainer with a list (A list technique s02 s05)
