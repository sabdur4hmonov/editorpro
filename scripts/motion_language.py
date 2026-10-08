"""Shared, overridable motion grammar. Absent/disabled section preserves legacy renders."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, random, unicodedata
from pathlib import Path
import common as C

ENTRANCES=('spring_pop','slide_overshoot','scale_blur','typewriter','mask_up','letter_cascade')
EMPHASIS=('scale_punch','colour_sweep','underline_draw','box_wipe')
DEFAULTS={'enabled':False,'speed':'medium','scales':{'fast':.75,'medium':1.,'slow':1.3},
 'durations_ms':{'caption':260,'exit':160,'sticker':360,'title':300,'label':300,'follow':420,'transition':240,'punch':300},
 'easing':{'enter':'snappy','exit':'soft'},'spring':{'omega':12.,'zeta':.62},'overshoot':1.1,
 'stagger':{'word_ms':35,'letter_ms':24,'max_total_ms':180},
 'pairs':{'spring_pop':'scale_down','slide_overshoot':'slide_out','scale_blur':'blur','typewriter':'fade','mask_up':'mask_down','letter_cascade':'fade'},
 'blur':{'enabled':False,'max_px':3},'variety':True,'choice':{}}

def config(style):
    over=style.get('motion',{}) or {}
    if not isinstance(over,dict): raise C.MontajError('motion must be an object.')
    video_over=style.get('motion_override',{}) or {}
    if not isinstance(video_over,dict): raise C.MontajError('motion_override must be an object.')
    over=C.deep_merge(over,video_over)
    cfg=C.deep_merge(copy.deepcopy(DEFAULTS),over)
    if cfg['speed'] not in cfg['scales']: raise C.MontajError('motion.speed: fast | medium | slow')
    for v in list(cfg['durations_ms'].values())+list(cfg['scales'].values()):
        if not isinstance(v,(int,float)) or not 0 < v < 10000: raise C.MontajError('Motion durations/scales must be positive finite values.')
    for curve in cfg['easing'].values():
        if curve not in ('snappy','soft','spring','overshoot'): raise C.MontajError(f'Unknown motion easing: {curve}')
    choice=cfg.get('choice') or {}
    if choice.get('enter') and choice['enter'] not in ENTRANCES: raise C.MontajError('Unknown motion entrance.')
    if choice.get('sub') and choice['sub'] not in ENTRANCES: raise C.MontajError('Unknown motion sub entrance.')
    if choice.get('emphasis') and choice['emphasis'] not in EMPHASIS: raise C.MontajError('Unknown motion emphasis.')
    for value in cfg['stagger'].values():
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1000:
            raise C.MontajError('motion.stagger: finite milliseconds, 0..1000.')
    if not 0<float(cfg['spring']['zeta'])<1 or not 0<float(cfg['spring']['omega'])<=30:
        raise C.MontajError('motion.spring: 0 < zeta < 1, 0 < omega <= 30.')
    if not 0<=float(cfg['blur']['max_px'])<=8 or not 0<=float(cfg['overshoot'])<=3:
        raise C.MontajError('motion: blur max 0..8px, overshoot 0..3.')
    if any(v not in ('scale_down','slide_out','blur','fade','mask_down') for v in cfg['pairs'].values()):
        raise C.MontajError('Unknown motion exit pair.')
    return cfg

def duration(cfg,key):
    return max(.001,float(cfg['durations_ms'][key])*float(cfg['scales'][cfg['speed']])/1000)

def curve(p,cfg,phase='enter'):
    import motion as M
    mode=cfg['easing'][phase]
    if mode=='soft': return M.ease_in_out(p)
    if mode=='spring': return M.spring(p,float(cfg['spring']['omega']),float(cfg['spring']['zeta']))
    if mode=='overshoot': return M.ease_back(p,float(cfg['overshoot']))
    return M.ease_out(p)

def caption_cfg(style,cfg):
    mc=config(style)
    if not mc['enabled']: return cfg
    out=dict(cfg); choice=mc.get('choice') or {}
    entrance=choice.get('enter','slide_overshoot')
    out.update(animation=entrance,anim_main=entrance,anim_sub=choice.get('sub','mask_up'),
               anim_ms=duration(mc,'caption')*1000,exit=mc['pairs'].get(entrance,'fade'),
               exit_ms=duration(mc,'exit')*1000,letter_ms=mc['stagger']['letter_ms'],
               intro_ms=duration(mc,'title')*1000,slide_ms=duration(mc,'caption')*1000,
               track_ms=duration(mc,'title')*1000,slide_in=0.,intro_scale=1.,
               emphasis=choice.get('emphasis','underline_draw'),_motion=mc)
    return out

def clusters(text):
    """Uzbek digraph + apostrophe and Unicode combining marks form one animation unit."""
    units=[]
    for ch in text:
        if units and (unicodedata.combining(ch) or ch in "'‘’ʻʼ`´" and units[-1][-1:].isalpha()):
            units[-1]+=ch
        else: units.append(ch)
    return units

def choose(style,job):
    mc=config(style)
    if not mc['enabled'] or not mc['variety'] or mc.get('choice'): return style
    job=C.guard_output(Path(job)/'motion_choice.json').parent; path=job/'motion_choice.json'
    fingerprint=hashlib.sha256(json.dumps(mc,sort_keys=True).encode()).hexdigest()
    if path.is_file():
        saved=C.read_json(path)
        if saved.get('fingerprint')==fingerprint:
            return C.deep_merge(style,{'motion':{'choice':saved['choice']}})
    history=C.TEMP_DIR/'.motion_history'/f"{C.slugify(style.get('_brand') or 'general')}.json"
    import handoff
    parallel=any(Path(row['note']).parent.resolve()!=job.resolve() for row in handoff.unfinished_notes())
    seed=int.from_bytes(hashlib.sha256(str(job.resolve()).encode()).digest()[:8],'big')
    rng=random.Random(seed)
    def pick(previous):
        options=[{'enter':en,'sub':ENTRANCES[(i+2)%len(ENTRANCES)],'emphasis':em} for i,en in enumerate(ENTRANCES) for em in EMPHASIS]
        options=[o for o in options if o!=previous]
        return rng.choice(options)
    if parallel:
        choice=pick(C.read_json(history).get('last',{}) if history.is_file() else {})
    else:
        history.parent.mkdir(parents=True,exist_ok=True)
        with C.file_mutex(history.with_suffix('.lock')):
            choice=pick(C.read_json(history).get('last',{}) if history.is_file() else {})
            C.atomic_text(history,json.dumps({'last':choice,'job':str(job)},ensure_ascii=False))
    C.atomic_text(path,json.dumps({'choice':choice,'fingerprint':fingerprint,'seed':seed,'history_deferred':parallel},ensure_ascii=False))
    return C.deep_merge(style,{'motion':{'choice':choice}})

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--style',required=True); ap.add_argument('--job',required=True)
    a=ap.parse_args(); st=choose(C.load_style(a.style),Path(a.job)); C.info(json.dumps(config(st),ensure_ascii=False,indent=2))
if __name__=='__main__': C.run_main(main)
