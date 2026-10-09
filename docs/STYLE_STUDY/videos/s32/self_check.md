# s32 self-check

| Claim | Check/evidence | Result | Caveat |
|---|---|---|---|
| Photo is on a dark paper grid | s32 1.200s videos/s32/overview_01.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| Ticket rotates, not a plain fade | s32 4.800s videos/s32/overview_01.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| White person silhouette transition | s32 11.800s videos/s32/overview_02.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| Photo smaller at left with caption on right | s32 21.800s videos/s32/overview_03.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| Both 200 and 1% visible | s32 30.600s videos/s32/overview_04.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| Stable two-panel frame while inner clips change | s32 38.800s videos/s32/overview_05.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| 1000 is third badge, not a numeric change of 100 | s32 48.200s videos/s32/overview_06.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |
| Logo outro on wide two-person shot | s32 58.200s videos/s32/overview_07.jpg (5fps discovery, ±0.2s) | discovery confirmed; native timing separate | ±0.2s; exact font/method unknown |

Numeric safeguards: source hash checked by owned_source; zero-duration words flagged; word-gap != silence; RMS != LUFS; cuts_on_beat.tested=false. See measurement JSONs.
Selected native strips/keyframes are separately linked. No unmeasured animation duration is substituted with a guess.

Native verification 20.96–21.84s: building/photo reflow, 22 elapsed frame intervals; evidence `codex\measurements\s32\native_ed483accc017.json`. Method/easing not known; censored window retained.
