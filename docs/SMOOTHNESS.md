# Silliqlik tekshiruvi — 2026-10-11 yakuni

Kod: `ee1002b`–`6286c6c` (Claude). Codex limitdan keyin dalillar, testlar va muharrir hisobotini yakunladi; renderer qayta o'zgartirilmadi.

Muharrir sahifasi: `temp/smooth/finish/report.html`. Unda 7 finalning oldin/keyin raqamlari, 25% ovozsiz kliplar, kadrlar va normal tezlikdagi final havolalari bor. Sahifadagi 77 mahalliy havola tekshirildi. `temp/` gitga kirmaydi: dalil papkasini o'chirmang.

## O'lchovlar

- Effektsiz 6 s sinov: 25→30 fps da 180 kadrning 30 tasi takror, har 6 kadrda; 25→25 da 150 kadr, takror va tushib qolish 0 (`temp/smooth/passthrough.json`).
- Yakuniy MP4dagi konservativ takror detektori: doktor1 **78→0**, doktor2 **111→0**, doktor3 **30→3**, doktor4 **73→15**, doktor5 **37→31**, Nilem07 **9→0**, championship **9→0**. Vaqtlar `temp/smooth/finish/measurements.json`da.
- Championship final AAC: pauzaga nisbatan kesish teshigi **−18.2…−11.0 → −0.4…+5.4 dB** (nutq yaqin bo'lgan bitta nuqta N/A). Doktor2 **−14.2→−4.0 dB**. Bu final fayldan qayta o'lchov; oldingi pre-encode raqamlaridan biroz farq qiladi.
- Saqlangan xom RGB: doktor4 (3/9.6/26 s), doktor5 (4/10/30 s), olti post-fix checkpointda maksimal farq **0 piksel**. Bu eski sozlamalar saqlanishi dalili; fps/grain o'zgargan v25 eksportlari bitma-bit bir xil degani emas.
- Nilem09 V11 allaqachon 25 fps, chiqish detektorida 0 takror; eksport o'zgartirilmadi. Dastlabki F3 dagi «27/27 bir xil» umumiy tanlovdan olingan: SRTdagi `anim_main=mask_up` va `anim_sub=slide_overshoot` override'larini hisoblamaydi.

## Qo'llangan chegara

Yangi videolar: manba fps, 20 ms equal-power kesish, ALAC oraliq audio, xona shovqini, CRF17 slow/grain2, minimal exit, o'qilish, rol/energiya asosidagi seeded variety. `look.match_cuts` ixtiyoriy. Maydonlar `AGENTS.md` va `docs/MOTION.md`da; Claude/Codex skilllari sinxron.

7 ta `_v25` faqat F1/F2/F8/F9/F13 texnik o'zgarishlari bilan (CRF16) qayta chiqarilgan. Tasdiqlangan per-video uslub/matn qayta tuzilmagan. Qolgan 3/15/31 takror nomzodi eski b-roll/sahna kliplarida; ularni qayta chizish bu texnik eksportda bajarilmagan. Qisqa animatsiya, drift va bir xillik ogohlantirishlari hisobotda saqlangan.

Detektor chiqishning kichraytirilgan yuqori qismidagi farqni o'lchaydi; barcha takrorlarni topishi kafolatlanmaydi. Audio mezoni kesish atrofidagi 5 ms minimumni 60 ms oldingi pauza bilan solishtiradi; N/A pass emas. Variety demo 7 cue: 3/2/2, eng uzun takror3, ulush42.9%; bitta b-roll butun motion tizimiga real-video dalil emas. Muharrir ritm va ovozni o'zi baholaydi.

## Tekshiruv dalili

- Yangi qayta tekshiruv: **14/14 suite o'tdi**; `temp/smooth/finish/tests.json` va alohida loglar. `test_smooth`:22, motion_polish:14, motion:15, motion_design:25, quality:20, formats:9, sfx:9, sprint2:21, studio:17, takes:17, part0:5, agent_setup:13, parallel:8, transcribe:9 (`--no-whisper`).
- Claude izolyatsiyalangan selftest: **NATIJA: 43/43 tekshiruv o'tdi.** `temp/finish_selftest_20261011_162256/selftest.log`; 71 Python skript SHA256 hozirgi kodga teng (`temp/smooth/finish/verification.json`). Shu run qayta ishlatildi, qayta bajarildi deb da'vo qilinmaydi; whisper/offline cheklovi saqlangan.
- SFX testi izolyatsiyada `.venv`/Git yo'qligidan yiqildi; o'zgarmagan test asl repositoryda faqat vaqtinchalik fixture bilan o'tdi. Navbat/agent testi sandbox Temp'da atomic rename WinError5 va Edge PNG to'sig'iga uchradi; ayni testlar sandbox tashqarisida izolyatsiyalangan papkada o'tdi. Eski xato loglari saqlandi, checklar zaiflashtirilmadi.
- Eski video egalarining papkalari/eslatmalari, `input/`, `samples/` va eski eksportlar o'zgartirilmadi. Muharrirning vaqt kodli tasdig'i hali olinmagan.

Muharrirga: normal finalni ovozi bilan ko'rsating, keyin 25% juftlikni. Javob formati: **fayl + vaqt + sezilgan muammo**. Vaqt kodli fikrlar `feedback.py add --at ... --editor ...` orqali; keyingi videolarga takrorlanadigan qoida, tasdiqlangan per-video stilga emas.
