# Solo yakuniy testlar

| Suite | Natija |
|---|---|
| test_quality.py | 20/20 OK |
| test_motion_design.py | 25/25 OK |
| test_motion.py | 15/15 OK |
| test_part0.py | 5/5 OK |
| test_sprint2.py | 21/21 OK |
| test_parallel.py | 8/8 OK |
| test_studio.py | 17/17 OK |
| test_agent_setup.py | 13/13 OK |
| test_takes.py | 17/17 OK |
| test_formats.py | 9/9 OK |
| test_sfx.py | 9/9 OK |
| test_transcribe.py --no-whisper | 9/9 OK |

Jami **168/168**. Takes to‘liq, --quick emas. sync_skills --check: sinxron. git diff --check: o‘tdi.

Izolyatsiyalangan, aynan yakuniy skript nusxasi selftest --no-whisper --offline: **43/43**.
Barcha script SHA256lari asosiy tree bilan qayta tenglashtirildi; offline ikki tarmoq tekshiruvini bajarmaydi.
Workspace: `temp\finish_selftest_20261010_000101`.

Asosiy loyihadagi selftest oldindan ochiq Doktor1/3 notes sabab rad etiladi; bu production pass deyilmaydi.
Guard yoki note tasdiqlari o‘zgartirilmadi; foydalanuvchi faqat Claude to‘xtaganini va shared continuationni tasdiqladi.

Bir sandbox run: parallel 8 test WinError5 atomic rename sabab failed; unchanged testlar normal Windows huquqlarida 8/8.
Birinchi failure log temp/style_study/finish_tests/test_parallel_sandbox_failure.log da saqlangan.
Oldingi run boshida skill manbalar/nusxalar farqi haqiqiy sabab bo‘lgan; sync --apply keyin setup 13/13.
Negative preflight unknown-preset xatosi selftestning kutilgan sinovi, oxirgi natija 43/43.

14 review proof: yuz/eksport o‘lchovlari bor; failed/unknown creative gates solo_finish.md da saqlangan.
GPU sinovi, yangi model/library/install/download, yangi transcript burn-in yoki sample assets eksporti bo‘lmadi.
