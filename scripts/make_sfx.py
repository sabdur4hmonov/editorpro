"""Asosiy ovoz effektlarini (SFX) ffmpeg bilan sintez qilib, assets/sfx/ ga yozadi.

    python scripts/make_sfx.py

Fayllar noldan generatsiya qilinadi (hech qayerdan yuklab olinmaydi), shuning uchun litsenziya
muammosi yo'q. O'z effektlaringiz bo'lsa, shu nomlar bilan assets/sfx/ yoki brands/<nom>/sfx/ ga
tashlang: shular ishlatiladi.
"""
from __future__ import annotations

import argparse
import shutil

import common as C

SFX_DIR = C.ROOT / "assets" / "sfx"

# nom: (manba (lavfi), qo'shimcha filtr)
RECIPES = {
    "pop": ("aevalsrc='0.7*sin(2*PI*(480+1100*exp(-t*45))*t)*exp(-t*30)':d=0.16:s=48000", "afade=t=out:st=0.12:d=0.04"),
    "click": ("aevalsrc='0.8*(random(0)*2-1)*exp(-t*260)':d=0.05:s=48000", "highpass=f=1800"),
    "tick": ("aevalsrc='0.6*sin(2*PI*2400*t)*exp(-t*140)':d=0.06:s=48000", "afade=t=out:st=0.04:d=0.02"),
    "thud": ("aevalsrc='0.95*sin(2*PI*(52+80*exp(-t*20))*t)*exp(-t*13)':d=0.35:s=48000", "afade=t=out:st=0.28:d=0.07"),
    "ding": ("aevalsrc='0.34*sin(2*PI*1318.5*t)*exp(-t*5)+0.24*sin(2*PI*1975.5*t)*exp(-t*7)"
             "+0.12*sin(2*PI*2637*t)*exp(-t*9)':d=0.9:s=48000", "afade=t=out:st=0.7:d=0.2"),
    "whoosh": ("anoisesrc=d=0.55:c=pink:r=48000:a=0.9",
               "bandpass=f=1500:width_type=o:w=2.2,volume='pow(sin(PI*t/0.55),2)':eval=frame,volume=6dB"),
    "swipe": ("anoisesrc=d=0.28:c=white:r=48000:a=0.7",
              "highpass=f=2500,volume='pow(t/0.28,2)':eval=frame,afade=t=out:st=0.24:d=0.04"),
    "riser": ("anoisesrc=d=1.2:c=pink:r=48000:a=0.8",
              "highpass=f=700,volume='pow(t/1.2,3)':eval=frame,afade=t=out:st=1.15:d=0.05,volume=4dB"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Asosiy ovoz effektlarini generatsiya qiladi (assets/sfx/).")
    ap.add_argument("--force", action="store_true", help="Bor fayllarni ham qayta yasash")
    ap.add_argument('--library',action='store_true',help='Category folders, 2 synthesized variants, per-file provenance; no downloads')
    args = ap.parse_args()
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg = C.need_tool("ffmpeg")
    made = 0
    for name, (source, chain) in RECIPES.items():
        out = SFX_DIR / f"{name}.wav"
        if out.exists() and not args.force:
            continue
        C.run([ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i", source,
               "-af", chain + ",aformat=channel_layouts=stereo,alimiter=limit=0.9",
               "-ar", "48000", "-c:a", "pcm_s16le", out])
        made += 1
        C.info(f"  {name}.wav ({C.ffprobe_info(out)['duration']:.2f}s)")
    if args.library:
        from sound_design import CATEGORIES
        for category in CATEGORIES:
            folder=SFX_DIR/category; folder.mkdir(exist_ok=True)
            source=SFX_DIR/f'{category}.wav'
            if not source.is_file():
                (folder/'README.md').write_text('Dedicated samples missing. User supplies licensed files and source/license sidecars. No automatic download.\n',encoding='utf-8')
                continue
            for n in (1,2):
                target=folder/f'synth_{n:02d}.wav'
                if not target.exists():
                    if n==1: shutil.copy2(source,target)
                    else: C.run([ffmpeg,'-hide_banner','-nostdin','-v','error','-y','-i',str(source),'-af','asetrate=52800,aresample=48000','-c:a','pcm_s16le',str(target)])
                C.write_json({'source':'scripts/make_sfx.py original synthesis; variant 2 rate-shifted',
                              'license':'Project-original generated audio; no third-party recording',
                              'category':category,'kind':'synthesized'},target.with_suffix('.wav.credit.json'))
                target.with_suffix('.wav.LICENSE.txt').write_text('Original sound synthesized by this project. No external recording or stock license. Generated for project use.\n',encoding='utf-8')
        for source in SFX_DIR.glob('*.wav'):
            if source.stem in RECIPES:
                source.with_suffix('.wav.LICENSE.txt').write_text('Project-original synthesis: scripts/make_sfx.py. No third-party recording. Generated for project use.\n',encoding='utf-8')
    C.info(f"Tayyor: {made} ta yangi effekt, papka: {SFX_DIR}")
    return 0


if __name__ == "__main__":
    C.run_main(main)
