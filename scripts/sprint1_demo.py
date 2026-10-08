"""Render the unchanged, already-captured Sprint 1 baseline clip with new motion/SFX.

No baseline is regenerated: before.mp4 must predate these changes.
"""
from __future__ import annotations
import argparse, hashlib, shutil
from pathlib import Path
import common as C
import compose, motion_language as ML, review_tools, sound_design, audio_mix

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',default='temp/sprint1')
    ap.add_argument('--reports-only',action='store_true')
    ap.add_argument('--audio-only',action='store_true',help='Rebuild two mixes without re-encoding identical video frames')
    a=ap.parse_args(); root=Path(a.baseline).resolve()
    C.busy_acquire('Sprint 1 motion A/B, codex')
    before=C.need_file(root/'before.mp4','Original before render')
    clip=C.need_file(root/'clip.mp4','Same baseline clip')
    manifest=C.read_json(root/'baseline_manifest.json')
    for name,digest in manifest['hashes'].items():
        if hashlib.sha256((Path(manifest['source_job'])/name).read_bytes()).hexdigest()!=digest:
            raise C.MontajError(f'Baseline original changed: {name}')
    after=root/'after_full.mp4'; draft=root/'after_draft.mp4'
    if not a.reports_only and not a.audio_only:
        base=C.read_json(root/'before_style.json'); current=C.load_style()
        style=C.deep_merge(base,{key:current[key] for key in ('motion','hardware','sfx')})
        # Draft also uses 30fps so the 3-frame SFX lead and animation cadence match.
        style['preview'].update(height=540,fps=30)
        fullwork=root/'after_full'; fullwork.mkdir(exist_ok=True)
        style=ML.choose(style,fullwork)
        C.write_json(style,root/'after_style.json')
        words=C.read_json(root/'words.json')['words']; cuts=C.read_json(root/'cuts.json')
        for name,out,lowres in (('after_full',after,False),('after_draft',draft,True)):
            work=root/name; work.mkdir(exist_ok=True)
            local=work/'clip.mp4'
            if not local.exists(): shutil.copy2(clip,local)
            C.write_json(style,work/'style.json')
            meta=compose.compose(local,out,style,root/'subs.srt',words,cuts,root/'elements.json',draft=lowres)
            C.write_json(meta,work/'result.json'); compose.print_report(meta,style)
    if a.audio_only:
        style=C.read_json(root/'after_style.json')
        style['sfx']=C.load_style()['sfx']
        C.write_json(style,root/'after_style.json')
        words=C.read_json(root/'words.json')['words']; cues=C.parse_srt(root/'subs.srt')
        els=compose.read_elements(root/'elements.json')
        for name,out,lowres in (('after_full',after,False),('after_draft',draft,True)):
            work=root/name; st=compose.draft_style(style) if lowres else style
            wav=audio_mix.build_audio(clip,work/'audio_mixes'/name/'subtle'/'final_audio.wav',st,12,
                                       sfx=sound_design.gather(st,els,cues,words))
            primary=dict(audio_mix.LAST_REPORT)
            mux=root/(name+'_remux.mp4')
            C.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y','-i',str(out),'-i',str(wav),
                   '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','12','-movflags','+faststart',str(mux)])
            mux.replace(out)
            meta=C.read_json(work/'result.json'); meta['audio']=primary
            meta['mixes']=sound_design.alternate_mixes(clip,out,work,st,12,els,cues,words,None,None,primary)
            meta['checks']=compose.check_export(out,st,C.ffprobe_info(out))
            meta['checks'].append(('Nutq ustunligi','ok',f"{primary.get('margin_db')} dB (talab 10)"))
            C.write_json(meta,work/'result.json')
    # Exact timestamps in both exports; sequence focuses on caption and heart entrance.
    times=[.1,.25,.5,6.3,6.45,6.6,10.067,10.133,10.2,10.267,10.4,10.6]
    review_tools.visual_sheet([before,after],times,root/'ab_sheet.jpg',360)
    for label,video in (('before',before),('after',after)):
        review_tools.visual_sheet([video],review_tools.timepoints(10,10.7,12,12),root/(label+'_filmstrip.jpg'),320)
        review_tools.visual_sheet([video],review_tools.timepoints(6.23,6.93,12,12),root/(label+'_caption_filmstrip.jpg'),320)
    print('SPRINT 1 DEMO:',root)
    return 0
if __name__=='__main__': C.run_main(main)
