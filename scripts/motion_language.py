"""Shared, overridable motion grammar. Absent/disabled section preserves legacy renders."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, random, unicodedata
from pathlib import Path
import common as C

ENTRANCES=('spring_pop','slide_overshoot','scale_blur','typewriter','mask_up','letter_cascade')
EMPHASIS=('scale_punch','colour_sweep','underline_draw','box_wipe')
# Explicit-only emphasis (variety keeps picking from EMPHASIS so saved choices stay reproducible).
EMPHASIS_EXTRA=('pop_overshoot','colour_flash','shake')
# Render-quality switches added after approved jobs: absent/False keeps every legacy frame identical.
NEW_KEYS=('subpixel','motion_blur','cuts','scrim','zoom_strength','preset','durations_frames','_polish_izoh')
SCRIM_STYLES=('soft','band','box')
# Per-brand presets: brand.json style.motion.preset; explicit motion keys still win.
PRESETS={
 'calm':{'speed':'slow','easing':{'enter':'soft','exit':'soft'},'overshoot':1.0,'stagger':{'word_ms':45},
         'choice':{'emphasis':'underline_draw'},'motion_blur':{'enabled':False},'scrim':{'style':'soft'},'zoom_strength':.6},
 'clinical':{'speed':'medium','easing':{'enter':'snappy','exit':'soft'},'overshoot':1.05,'stagger':{'word_ms':35},
             'choice':{'emphasis':'box_wipe'},'motion_blur':{'enabled':False},'scrim':{'style':'soft'},'zoom_strength':.8},
 'punchy':{'speed':'fast','easing':{'enter':'overshoot','exit':'snappy'},'overshoot':1.25,'stagger':{'word_ms':25},
           'choice':{'emphasis':'pop_overshoot'},'motion_blur':{'enabled':True},'scrim':{'style':'band'},'zoom_strength':1.2},
}
DEFAULTS={'enabled':False,'speed':'medium','scales':{'fast':.75,'medium':1.,'slow':1.3},
 'durations_ms':{'caption':260,'exit':160,'sticker':360,'title':300,'label':300,'follow':420,'transition':240,'punch':300,'hero':360},
 'easing':{'enter':'snappy','exit':'soft'},'spring':{'omega':12.,'zeta':.62},'overshoot':1.1,
 'stagger':{'word_ms':35,'letter_ms':24,'max_total_ms':180},
 'pairs':{'spring_pop':'scale_down','slide_overshoot':'slide_out','scale_blur':'blur','typewriter':'fade','mask_up':'mask_down','letter_cascade':'fade'},
 'blur':{'enabled':False,'max_px':3},'variety':True,'choice':{},
 'subpixel':False,'motion_blur':{'enabled':False,'samples':5,'min_px':6,'shutter':.5},
 'cuts':{'enabled':False,'offset_frames':2,'match_direction':True,'zoom_ease':True},
 'scrim':{'enabled':False,'style':'soft','max_alpha':.55,'min_contrast':4.5},'zoom_strength':None,'preset':None}

def config(style):
    over=style.get('motion',{}) or {}
    if not isinstance(over,dict): raise C.MontajError('motion must be an object.')
    video_over=style.get('motion_override',{}) or {}
    if not isinstance(video_over,dict): raise C.MontajError('motion_override must be an object.')
    over=C.deep_merge(over,video_over)
    preset=over.get('preset')
    if preset is not None and preset not in PRESETS: raise C.MontajError(f"motion.preset: {', '.join(PRESETS)}")
    cfg=C.deep_merge(copy.deepcopy(DEFAULTS),PRESETS.get(preset,{}))
    cfg=C.deep_merge(cfg,over)
    frames=cfg.get('durations_frames') or {}
    if frames:
        fps=float(style.get('video',{}).get('fps',30))
        for key,n in frames.items():
            if key not in cfg['durations_ms'] or not isinstance(n,(int,float)) or not 0<n<600:
                raise C.MontajError(f'motion.durations_frames.{key}: known key, 0 < frames < 600.')
            cfg['durations_ms'][key]=n*1000/fps
    if cfg['speed'] not in cfg['scales']: raise C.MontajError('motion.speed: fast | medium | slow')
    for v in list(cfg['durations_ms'].values())+list(cfg['scales'].values()):
        if not isinstance(v,(int,float)) or not 0 < v < 10000: raise C.MontajError('Motion durations/scales must be positive finite values.')
    for curve in cfg['easing'].values():
        if curve not in ('snappy','soft','spring','overshoot'): raise C.MontajError(f'Unknown motion easing: {curve}')
    choice=cfg.get('choice') or {}
    if choice.get('enter') and choice['enter'] not in ENTRANCES: raise C.MontajError('Unknown motion entrance.')
    if choice.get('sub') and choice['sub'] not in ENTRANCES: raise C.MontajError('Unknown motion sub entrance.')
    if choice.get('emphasis') and choice['emphasis'] not in EMPHASIS+EMPHASIS_EXTRA: raise C.MontajError('Unknown motion emphasis.')
    mb,cu,sc=cfg['motion_blur'],cfg['cuts'],cfg['scrim']
    if not 2<=int(mb['samples'])<=16 or not 0<float(mb['min_px'])<=200 or not 0<float(mb['shutter'])<=1:
        raise C.MontajError('motion.motion_blur: samples 2..16, min_px >0, shutter 0..1.')
    if not 0<=int(cu['offset_frames'])<=6: raise C.MontajError('motion.cuts.offset_frames: 0..6.')
    if sc['style'] not in SCRIM_STYLES or not 0<=float(sc['max_alpha'])<=.9:
        raise C.MontajError(f"motion.scrim: style {'/'.join(SCRIM_STYLES)}, max_alpha 0..0.9.")
    if cfg['zoom_strength'] is not None and not 0<=float(cfg['zoom_strength'])<=3:
        raise C.MontajError('motion.zoom_strength: 0..3.')
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

def frames(cfg,key,fps):
    """Configured duration in whole frames (lint/cue-sheet unit)."""
    return max(1,round(duration(cfg,key)*fps))

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
    # Render-quality switches do not re-roll an already saved entrance/emphasis choice.
    fingerprint=hashlib.sha256(json.dumps({k:v for k,v in mc.items() if k not in NEW_KEYS},sort_keys=True).encode()).hexdigest()
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
