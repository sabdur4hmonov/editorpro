"""Event-driven local SFX: deterministic variants, frame lead and density."""
from __future__ import annotations
import hashlib, random
from pathlib import Path
import common as C
CATEGORIES=('whoosh','pop','click','hit','riser','ding','swipe','typing','tick','impact')
LEGACY={'hit':'thud','impact':'thud'}

def mix_gain(cfg):
    profiles=cfg.get('mixes',{})
    if profiles and set(profiles)!= {'subtle','stronger'}:
        raise C.MontajError('sfx.mixes must contain subtle and stronger gains in dB.')
    name=cfg.get('profile','subtle')
    if profiles and name not in profiles: raise C.MontajError(f'Unknown SFX mix profile: {name}')
    return float(cfg.get('mix_gain_db',0))+float(profiles.get(name,0))

def variants(category,brand_dir=None):
    import audio_mix
    from sfx_library import provenance
    dirs=([Path(brand_dir)/'sfx'] if brand_dir else [])+[C.ROOT/'assets/sfx']
    real, synth = [], []
    for folder in dirs:
        found=sorted(p for p in (folder/category).glob('*') if p.suffix.lower() in audio_mix.SFX_EXTS)
        for path in found:
            meta=provenance(path)
            if meta['kind']=='real' and meta['usable']: real.append(path)
            elif meta['kind']=='synthesized': synth.append(path)
        for ext in audio_mix.SFX_EXTS:
            path=folder/(LEGACY.get(category,category)+ext)
            if path.is_file():
                meta=provenance(path)
                if meta['kind']=='real' and meta['usable']: real.append(path)
                elif meta['kind']=='synthesized' and not found: synth.append(path)
    return real or synth

def gather(style,elements,cues,words,brand_dir=None):
    import elements as E
    cfg=style.get('sfx',{})
    offset=mix_gain(cfg)
    explicit=[{'at':float(e.get('at',e.get('start',0))),'name':e.get('name','pop'),
               'volume_db':float(e.get('volume_db',cfg.get('volume_db',-14)))+offset, 'kind':'manual'} for e in elements if e.get('type')=='sfx']
    if not cfg.get('enabled'): return explicit
    event_map=cfg.get('event_map',{})
    events=[]
    captions=E.CaptionLayer(E.Ctx(style,brand_dir),cues,words,max((c['end'] for c in cues),default=0))
    for item in captions.items:
        captions._prepare(item)
        for i,word in enumerate(item['block'].words):
            if word['emph']:
                events.append((E.word_reveal_time(item['cfg'],item['start'],i,item['times']),'hero')); break
    for el in elements:
        kind=el.get('type'); start=float(el.get('start',0))
        event={'image':'sticker','emoji':'sticker','icon':'sticker','broll':'broll_in','title':'title','stat':'number'}.get(kind)
        if event: events.append((start,event))
        if kind=='label': events.extend((float(i.get('at',start)),'label') for i in el.get('items',[]))
        if kind=='follow': events.append((start+float(el.get('tap',1.3)),'follow_tap'))
    fps=float(style['video']['fps']); lead=int(cfg.get('lead_frames',3))
    if not 2<=lead<=3: raise C.MontajError('sfx.lead_frames must be 2 or 3.')
    density=int(cfg.get('max_per_10_sec',3))
    if density<1: raise C.MontajError('sfx.max_per_10_sec must be positive.')
    gap=max(0,float(cfg.get('min_gap_sec',1.5)))
    seed=hashlib.sha256(str(style.get('motion',{}).get('choice',{})).encode()+str(cfg.get('seed',0)).encode()).digest()
    rng=random.Random(int.from_bytes(seed[:8],'big')); last={}; out=list(explicit)
    priority=cfg.get('event_priority',['broll_in','sticker','follow_tap','title','number','label','hero'])
    def event_rank(event):
        return (priority.index(event[1]) if event[1] in priority else len(priority), event[0])
    for visual,kind in sorted(events,key=event_rank):
        category=event_map.get(kind)
        if not category: continue
        at=max(0,visual-lead/fps)
        if any(abs(at-e['at'])<gap for e in out): continue
        times=[e['at'] for e in out]+[at]
        if any(sum(t-10<x<=t for x in times)>density for t in times): continue
        candidates=variants(category,brand_dir)
        if not candidates:
            C.warn(f'SFX category missing: {category}; event {kind} skipped.'); continue
        choices=[p for p in candidates if str(p)!=last.get(category)] or candidates
        path=rng.choice(choices); last[category]=str(path)
        out.append({'at':at,'visual_at':visual,'lead_frames_actual':round((visual-at)*fps,3),'kind':kind,
                    'category':category,'name':str(path),'volume_db':float(cfg.get('volume_db',-14))+offset})
    return sorted(out,key=lambda e:e['at'])

def alternate_mixes(video,rendered,work,style,total,elements,cues,words,music,brand_dir,primary_report):
    """Encode visuals once; mux measured alternate audio with stream copy."""
    import audio_mix
    cfg=style.get('sfx',{}); profiles=cfg.get('mixes',{})
    if not profiles or not cfg.get('enabled'): return {}
    if set(profiles)!= {'subtle','stronger'}:
        raise C.MontajError('sfx.mixes must contain subtle and stronger gains in dB.')
    primary=cfg.get('profile','subtle')
    result={primary:dict(file=str(rendered),audio=primary_report)}
    for name in profiles:
        if name==primary: continue
        other=C.deep_merge(style,{'sfx':{'profile':name}})
        dest=C.guard_output(rendered.with_name(rendered.stem+'_'+name+rendered.suffix),video)
        wav=audio_mix.build_audio(video,work/'audio_mixes'/rendered.stem/name/'final_audio.wav',other,total,music,
                                  gather(other,elements,cues,words,brand_dir),brand_dir)
        C.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y','-i',str(rendered),'-i',str(wav),
               '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a',str(style['audio'].get('bitrate','192k')),
               '-t',f'{total:.3f}','-movflags','+faststart',str(dest)])
        _,problems=C.verify_video(dest,style['video']['width'],style['video']['height'],total,need_audio=True)
        if problems: raise C.MontajError('Alternate mix: '+'; '.join(problems))
        result[name]=dict(file=str(dest),audio=dict(audio_mix.LAST_REPORT))
    C.write_json(result,work/'audio_mixes'/rendered.stem/'mixes.json')
    audio_mix.LAST_REPORT=primary_report
    return result
