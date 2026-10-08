"""Same doktor_1 0..12s + longer 14..38s, isolated source copies and reproducible review."""
from pathlib import Path
import argparse,copy,hashlib,shutil
import common as C
import compose as CP
import review_tools as RT
import motion_language as ML

ROOT=C.TEMP_DIR/'sprint2'; JOB=C.TEMP_DIR/'doktor_1'

def isolate(name,start,end):
    work=ROOT/name; work.mkdir(parents=True,exist_ok=True); clip=work/'cut.mp4'
    if not clip.is_file():
        C.run_ffmpeg_graph(['-i',str(JOB/'cut.mp4')],
          f'[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v];[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a]',
          ['-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','16','-c:a','aac','-b:a','256k',str(clip)],work)
    cues=[dict(c,start=max(start,c['start'])-start,end=min(end,c['end'])-start) for c in C.parse_srt(JOB/'subs.srt') if c['start']<end and c['end']>start]
    words=[dict(w,start=max(start,w['start'])-start,end=min(end,w['end'])-start) for w in C.read_json(JOB/'cut.words.json')['words'] if w['start']<end and w['end']>start]
    C.write_srt(cues,work/'subs.srt'); C.write_json({'words':words},work/'words.json')
    return work,words

def shifted(elements,start,end):
    out=[]
    for e in elements:
        at=e.get('start',e.get('at',0)); stop=e.get('end',at+.5)
        if at>=end or stop<=start: continue
        el=copy.deepcopy(e)
        for key in ('start','at','end'):
            if key in el: el[key]=max(0,min(end,float(el[key]))-start)
        # Internal item timestamps are absolute in this project's elements format.
        for item in el.get('items',[]):
            for key in ('at','end'):
                if key in item: item[key]-=start
        out.append(el)
    return out

def style(enabled):
    base=C.read_json(JOB/'style.json'); current=C.load_style()
    st=C.deep_merge(base,{k:current[k] for k in ('motion','hardware','sfx','dynamics','broll')})
    st['motion']['choice']=C.read_json(C.TEMP_DIR/'sprint1/after_full/motion_choice.json')['choice']
    st['preview'].update(height=540,fps=30); st['sfx']['profile']='stronger'; st['dynamics']['enabled']=enabled
    st['endcard']['enabled']=False
    return st

def verify_source():
    path=ROOT/'baseline_manifest.json'
    hashes={n:hashlib.sha256((JOB/n).read_bytes()).hexdigest() for n in ('style.json','subs.srt','cut.words.json','elements.json','cuts.json')}
    if path.is_file():
        if C.read_json(path)['hashes']!=hashes: raise C.MontajError('Original doktor_1 job changed during A/B')
    else:C.write_json({'hashes':hashes,'ranges':[[0,12],[14,38]],'subtitle_policy':'existing approved text unchanged; user authorised technical Sprint2 comparison'},path)

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('phase',choices=('before','after','after-existing','reports'))
    ap.add_argument('--selected',default='temp/sprint2/approval/selected_elements.json')
    ap.add_argument('--only',choices=('short','long'),help='Render/report just one comparison range'); a=ap.parse_args()
    C.busy_acquire('Sprint2 comparison '+a.phase); ROOT.mkdir(exist_ok=True);verify_source()
    original=CP.read_elements(JOB/'elements.json')
    if a.phase=='before':
        for name,start,end in [('short',0,12),('long',14,38)]:
            if a.only and a.only!=name:continue
            work,words=isolate(name,start,end); output=ROOT/(name+'_before.mp4')
            if output.exists(): C.info('Existing baseline preserved: '+str(output)); continue
            st=style(False); C.write_json(st,work/'before_style.json'); el=work/'before_elements.json'
            C.write_json({'elements':shifted(original,start,end)},el)
            meta=CP.compose(work/'cut.mp4',output,st,work/'subs.srt',words,None,el,draft=name=='long')
            C.write_json(meta,work/'before_result.json')
    elif a.phase in ('after','after-existing'):
        chosen=[]
        if a.phase=='after':
            selection=C.need_file(a.selected,'Approved B-roll selection'); chosen=CP.read_elements(selection)
            approved_plan=C.read_json(selection.parent/'broll_plan.json')
            if not approved_plan.get('approval'): raise C.MontajError('Written B-roll approval missing')
        else: C.info('Energy-only comparison: original approved elements retained; new B-roll choice pending')
        # Replace corresponding old sticker intervals, keeping all other editorial choices.
        enriched=[e for e in original if not any(e.get('type') in ('image','broll') and abs(e.get('start',0)-c['start'])<2 for c in chosen)]+chosen
        for name,start,end in [('short',0,12),('long',14,38)]:
            if a.only and a.only!=name:continue
            work,words=isolate(name,start,end); st=style(True); C.write_json(st,work/'style.json')
            # An excerpt beginning at 14s is not a new hook. Preserve original structure context.
            st['dynamics']['hook_seconds']=max(0,float(st['dynamics']['hook_seconds'])-start)
            C.write_json(st,work/'style.json')
            el=work/'elements.json';C.write_json({'elements':shifted(enriched,start,end)},el)
            modes=[('short_after_full',False),('short_after_draft',True)] if name=='short' else [('long_after',True)]
            for label,draft in modes:
                rw=work/label;rw.mkdir(exist_ok=True);shutil.copy2(work/'cut.mp4',rw/'cut.mp4')
                meta=CP.compose(rw/'cut.mp4',ROOT/(label+'.mp4'),st,work/'subs.srt',words,None,el,draft=draft)
                C.write_json(meta,rw/'result.json')
                for check in meta['checks']:
                    if check[1]=='xato': raise C.MontajError('Demo export check failed: '+str(check))
    else:
        for name,total,at in [('short',12,7.7),('long',24,15.06)]:
            if a.only and a.only!=name:continue
            before=ROOT/(name+'_before.mp4');after=ROOT/('short_after_full.mp4' if name=='short' else 'long_after.mp4')
            RT.visual_sheet([before,after],[.1,1,3,5,total*.5,total-1],ROOT/(name+'_ab.jpg'),360)
            for label,file in [('before',before),('after',after)]:
                RT.visual_sheet([file],RT.timepoints(at-.05,at+.65,12,total),ROOT/(name+'_'+label+'_filmstrip.jpg'),320)
    verify_source(); C.info('SPRINT2 '+a.phase+' READY: '+str(ROOT))
if __name__=='__main__': C.run_main(main)
