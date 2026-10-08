"""Measured speech dynamics + explicitly labelled transcript heuristics, CPU only."""
from pathlib import Path
import argparse, copy, math, re
import numpy as np
from PIL import Image, ImageDraw
import common as C

DEFAULTS = {
    'enabled':False,'weights':{'rate':.3,'loudness':.25,'speech':.2,'structure':.25},
    'rate_reference_wps':4,'loudness_floor_dbfs':-42,'loudness_ceiling_dbfs':-14,
    'smooth_seconds':3,'hook_seconds':2,
    'structure':{'hook':.8,'problem':.6,'key_point':.5,'proof':.75,'cta':.65},
    'keywords':{'problem':['xato','qiyin','og‘ir','kasal','muammo','problem'],
                'proof':['natija','misol','statistika','foiz','masalan'],
                'cta':['yoziling','obuna','buyurtma','bog‘lan','subscribe']},
    'ranges':{'zoom':[1.015,1.11],'shot_seconds':[7,2.8],'caption_intensity':[.4,1.15],
              'element_gap_seconds':[6,3],'sfx_per_10s':[1,3],'sfx_gain_db':[-6,0],
              'background_speed':[.3,1.1]},
    'zoom_hold_seconds':1.4,'zoom_ease_seconds':.22,'beat':{'threshold':1.6,'min_gap_sec':.25}
}

def config(style):
    cfg=C.deep_merge(DEFAULTS,style.get('dynamics',{}))
    for key, pair in cfg['ranges'].items():
        if len(pair)!=2 or not all(math.isfinite(float(v)) for v in pair):
            raise C.MontajError(f'dynamics.ranges.{key}: two finite values required')
    if cfg['rate_reference_wps']<=0 or cfg['loudness_ceiling_dbfs']<=cfg['loudness_floor_dbfs']:
        raise C.MontajError('dynamics rate/loudness range invalid')
    if sum(cfg['weights'].values())<=0 or any(v<0 for v in cfg['weights'].values()):
        raise C.MontajError('dynamics weights must be nonnegative and nonzero')
    if any(v<=0 for k,p in cfg['ranges'].items() if k!='sfx_gain_db' for v in p):
        raise C.MontajError('dynamics ranges must be positive (except gain dB)')
    return cfg

def decode_audio(video,sr=16000):
    import subprocess
    meta=C.ffprobe_info(video)
    if not meta['has_audio']: return np.zeros(round(meta['duration']*sr),np.float32),sr
    proc=subprocess.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-i',str(video),
                '-vn','-ac','1','-ar',str(sr),'-f','f32le','-'],capture_output=True)
    if proc.returncode: raise C.MontajError('Energy audio decode: '+proc.stderr.decode('utf-8','replace')[-400:])
    return np.frombuffer(proc.stdout,'<f4'),sr

def plain(text):
    import elements as E
    return ' '.join(w for w,_,_ in E.parse_markup(E.split_cue_tag(text)[2]))

def structure(text, at, cfg):
    text=text.lower().replace('ʻ','‘').replace("'",'‘')
    if at<cfg['hook_seconds']: return 'hook'
    for label in ('cta','problem','proof'):
        if any(k in text for k in cfg['keywords'][label]): return label
    return 'proof' if re.search(r'\d',text) else 'key_point'

def value(style,at,key):
    rows=style.get('_energy',{}).get('seconds',[])
    if not rows: return 1 if key not in ('sfx_gain_db',) else 0
    row=rows[min(len(rows)-1,max(0,int(at)))]
    return row['controls'][key]

def clock(style,t):
    rows=style.get('_energy',{}).get('seconds',[])
    if not rows: return t
    i=min(len(rows)-1,max(0,int(t))); row=rows[i]
    return row['background_clock']+(t-i)*row['controls']['background_speed']

def analyze(samples,sr,words,cues,total,style,elements=None):
    cfg=config(style); rows=[]; weights=cfg['weights']; denom=sum(weights.values())
    for second in range(math.ceil(total)):
        end=min(second+1,total); span=max(.001,end-second)
        chunk=samples[round(second*sr):round(end*sr)]
        rms=math.sqrt(float(np.mean(chunk.astype(np.float64)**2))) if chunk.size else 0
        db=20*math.log10(max(rms,1e-6))
        count=sum(second<=w['start']<end for w in words or [])
        intervals=sorted((max(second,w['start']),min(end,w['end'])) for w in words or []
                         if w['start']<end and w['end']>second)
        spoken=0; previous=second
        for a,b in intervals:
            spoken+=max(0,b-max(a,previous)); previous=max(previous,b)
        text=' '.join(plain(c['text']) for c in cues if c['start']<end and c['end']>second)
        label=structure(text,second,cfg)
        for override in cfg.get('structure_overrides',[]):
            if override['start']<=second<override['end']:
                if override['label'] not in cfg['structure']: raise C.MontajError('Unknown dynamics structure label')
                label=override['label']
        features={'rate':min(1,count/span/cfg['rate_reference_wps']),
                  'loudness':float(np.clip((db-cfg['loudness_floor_dbfs'])/
                    (cfg['loudness_ceiling_dbfs']-cfg['loudness_floor_dbfs']),0,1)),
                  'speech':min(1,spoken/span),'structure':cfg['structure'][label]}
        raw=sum(features[k]*weights[k] for k in weights)/denom
        rows.append(dict(at=second,words_per_second=count/span,rms_dbfs=round(db,2),
                         pause_fraction=round(1-spoken/span,3),structure=label,raw=raw))
    energies=np.array([r['raw'] for r in rows]); radius=max(0,int(cfg['smooth_seconds'])//2)
    bgclock=0
    for i,row in enumerate(rows):
        e=float(np.mean(energies[max(0,i-radius):i+radius+1])); row['energy']=round(e,4)
        row['controls']={k:round(float(lo+(hi-lo)*e),4) for k,(lo,hi) in cfg['ranges'].items()}
        row['background_clock']=bgclock; bgclock+=row['controls']['background_speed']
    plan=[]; last=-float('inf')
    for cue in cues:
        at=float(cue['start']); row=rows[min(len(rows)-1,int(at))] if rows else None
        if row and at-last>=row['controls']['shot_seconds']:
            if not any(e.get('type') in ('broll','stage','scene') and e.get('start',0)<=at<e.get('end',total) for e in elements or []):
                plan.append(dict(type='zoom',start=at,end=min(total,at+cfg['zoom_hold_seconds']),
                                 scale=row['controls']['zoom'],ease=cfg['zoom_ease_seconds'],origin='energy_visual_cut'))
                last=at
    selected=[]; skipped=[]; last_element=-float('inf')
    for el in sorted(elements or [],key=lambda e:e.get('start',e.get('at',0))):
        at=float(el.get('start',el.get('at',0)))
        gap=rows[min(len(rows)-1,max(0,int(at)))]['controls']['element_gap_seconds'] if rows else 0
        # Explicit user elements are always preserved; density gates only generated suggestions.
        if el.get('automatic') and el.get('type') not in ('sfx','zoom'):
            if at-last_element<gap: skipped.append(el); continue
            last_element=at
        selected.append(el)
    return dict(seconds=rows,events=plan,elements=selected,skipped_automatic_elements=skipped,
                structure_method='keyword/number heuristic, editable; not semantic proof',
                measurements='WPS from word starts; RMS dBFS of decoded mono; pause from union of word intervals',
                cut_policy='Visual punch cuts only; original speech cuts and subtitle timings never changed')

def curve_image(report,out):
    rows=report['seconds']; w,h=1500,520; im=Image.new('RGB',(w,h),'#15171B'); d=ImageDraw.Draw(im)
    d.text((35,18),'Energy: WPS + mono RMS + word pauses + transcript heuristic | planned visual cuts',fill='white')
    for p in (0,.25,.5,.75,1):
        y=450-p*350; d.line((40,y,w-40,y),fill='#33343A'); d.text((5,y-7),str(p),fill='white')
    n=max(1,len(rows)); points=[(40+(i+.5)/n*(w-80),450-r['energy']*350) for i,r in enumerate(rows)]
    if len(points)>1: d.line(points,fill='#69C7DD',width=4)
    for i,row in enumerate(rows):
        if i%max(1,n//15)==0:
            x=40+i/n*(w-80); d.text((x,463),f'{i}s',fill='white'); d.text((x,490),row['structure'],fill='#AAAAAA')
    for e in report['events']+report.get('elements',[]):
        at=e.get('start',e.get('at',0)); x=40+at/n*(w-80)
        color='#FFBC59' if e['type']=='zoom' else '#BE9BFF'
        d.line((x,65,x,450),fill=color); d.text((x,45 if e['type']=='zoom' else 70),f"{e['type']} {at:.1f}",fill=color)
    C.guard_output(out); im.save(out)

def prepare(video,words,cues,elements,style,work):
    if not config(style)['enabled']: return style,elements
    data,sr=decode_audio(video); total=C.ffprobe_info(video)['duration']
    report=analyze(data,sr,words,cues,total,style,elements)
    C.write_json(report,work/'energy.json'); curve_image(report,work/'energy_curve.png')
    return C.deep_merge(style,{'_energy':report}),report['elements']+report['events']

def beats(samples,sr,cfg):
    # Spectral positive flux, NumPy only; no BPM/beat-grid certainty claim.
    win,hop=1024,256
    if len(samples)<win or not np.any(samples): return []
    frames=np.lib.stride_tricks.sliding_window_view(samples,win)[::hop]
    spectra=np.abs(np.fft.rfft(frames*np.hanning(win),axis=1))
    flux=np.maximum(0,np.diff(spectra,axis=0)).sum(axis=1)
    threshold=float(np.mean(flux)+cfg['threshold']*np.std(flux)); out=[]
    for i in range(1,len(flux)-1):
        at=(i+1)*hop/sr
        if flux[i]>threshold and flux[i]>flux[i-1] and flux[i]>=flux[i+1] and (not out or at-out[-1]>=cfg['min_gap_sec']): out.append(round(at,3))
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('video'); p.add_argument('--words',required=True)
    p.add_argument('--subs',required=True); p.add_argument('--elements'); p.add_argument('--style'); p.add_argument('--out-dir',required=True); p.add_argument('--music')
    a=p.parse_args(); work=C.guard_output(a.out_dir); work.mkdir(parents=True,exist_ok=True)
    st=C.load_style(a.style); st['dynamics']=dict(st.get('dynamics',{}),enabled=True)
    words=C.read_json(a.words)['words']; cues=C.parse_srt(a.subs)
    elements=C.read_json(a.elements)['elements'] if a.elements else []
    st,_=prepare(Path(a.video),words,cues,elements,st,work)
    if a.music:
        data,sr=decode_audio(a.music); C.write_json({'onset_candidates':beats(data,sr,config(st)['beat']), 'method':'spectral flux, heuristic'},work/'beats.json')
    C.info(f'ENERGY: {len(st["_energy"]["seconds"])} seconds, {len(st["_energy"]["events"])} visual cuts')
if __name__=='__main__': C.run_main(main)
