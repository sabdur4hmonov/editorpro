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
NEW_KEYS=('subpixel','motion_blur','cuts','scrim','zoom_strength','preset','durations_frames','_polish_izoh','variety_plan','min_exit_frames')
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

# ---------------------------------------------------------------- variety: per-cue / per-element motion plan
# One signature move per video plus 2-3 others, picked by role and energy; seeded so a re-render is identical,
# recorded per brand so the next video differs. Absent motion.variety_plan (approved styles): nothing changes.
STRONG = ('spring_pop', 'slide_overshoot', 'letter_cascade')
SOFT = ('mask_up', 'scale_blur', 'typewriter')
STICKER_MOVES = ('spring', 'pop', 'slide_left', 'slide_right', 'drop', 'fade_drift', 'rise')
STRONG_STICKER = ('spring', 'pop', 'slide_left', 'slide_right', 'drop')
TRANSITIONS = ('cut', 'push', 'mask', 'flash', 'fade')
ENTER_EASES = ('spring', 'overshoot', 'snappy', 'soft')
VARIETY = {'enabled': False, 'others': 3, 'max_run': 3, 'max_share': .6, 'jitter_frames': 2, 'ease_jitter': .03,
           'zoom_skip': .35, 'zoom_range': [1.04, 1.10], 'entrances': list(ENTRANCES)}
ROLE_ORDER = ('hook', 'number', 'question', 'list', 'key', 'hero', 'calm')


def variety_cfg(style):
    cfg = C.deep_merge(copy.deepcopy(VARIETY), (style.get('motion') or {}).get('variety_plan') or {})
    if not 1 <= int(cfg['max_run']) <= 10 or not .2 <= float(cfg['max_share']) <= 1:
        raise C.MontajError('motion.variety_plan: max_run 1..10, max_share 0.2..1.')
    if any(e not in ENTRANCES for e in cfg['entrances']) or len(cfg['entrances']) < 2:
        raise C.MontajError('motion.variety_plan.entrances: kamida 2 ta ma’lum entrance.')
    return cfg


def energy_level(style, t):
    """0 calm .. 1 peak from the energy curve; None when the video has no curve."""
    if not style.get('_energy', {}).get('seconds'):
        return None
    import energy_curve
    return min(1., max(0., (float(energy_curve.value(style, t, 'caption_intensity')) - .4) / .75))


def role_of(text, index, start):
    import re
    plain = re.sub(r'\{[^}]*\}', '', text).strip()
    low = plain.lower()
    if index == 0 or start < 1.5:
        return 'hook'
    if re.search(r'\d', plain) or '!!' in plain:
        return 'number'
    if plain.rstrip('*_=~! ').endswith('?'):
        return 'question'
    if re.match(r"^\W*(\d+[.)-]|birinchi|ikkinchi|uchinchi|to.rtinchi|beshinchi|first|second|third|первое|второе)", low):
        return 'list'
    if '==' in plain or '~~' in plain or re.search(r'(^|\s)_[^_]+_', plain):
        return 'key'
    if '*' in plain:
        return 'hero'
    return 'calm'


def _rng(seed, *salt):
    return random.Random(int.from_bytes(hashlib.sha256(json.dumps([seed, *salt]).encode()).digest()[:8], 'big'))


def setup_variety(style, job):
    """Signature + others for this video; saved in job/motion_variety.json, brand history avoids repeats."""
    vc = variety_cfg(style)
    if not vc['enabled'] or style.get('_variety'):
        return style
    job = Path(job); path = job / 'motion_variety.json'
    fingerprint = hashlib.sha256(json.dumps(vc, sort_keys=True).encode()).hexdigest()
    if path.is_file():
        saved = C.read_json(path)
        if saved.get('fingerprint') == fingerprint:
            return dict(style, _variety=saved['plan'])
    history = C.TEMP_DIR / '.motion_history' / f"{C.slugify(style.get('_brand') or 'general')}_variety.json"
    last = C.read_json(history).get('last', {}) if history.is_file() else {}
    seed = int.from_bytes(hashlib.sha256(str(job.resolve()).encode()).digest()[:8], 'big')
    rng = _rng(seed, 'setup')
    def pick(pool, avoid, k):
        pool = list(pool); rng.shuffle(pool)
        pool.sort(key=lambda x: x == avoid)
        return pool[0], pool[1:1 + k]
    sig, others = pick(vc['entrances'], last.get('signature'), int(vc['others']))
    pool = [sig] + others
    for need in (STRONG, SOFT):            # peaks need a strong entrance, calm parts a soft one
        if not any(p in need for p in pool):
            have = [e for e in vc['entrances'] if e in need]
            if have and others:
                others[-1] = rng.choice(have); pool = [sig] + others
    st_sig, st_others = pick(STICKER_MOVES, last.get('sticker'), 3)
    tr_sig, tr_others = pick(TRANSITIONS, last.get('transition'), 2)
    em_sig = pick(EMPHASIS, last.get('emphasis'), 0)[0]
    plan = {'signature': sig, 'others': others, 'sticker': st_sig, 'sticker_others': st_others,
            'transition': tr_sig, 'transition_others': tr_others, 'emphasis': em_sig, 'seed': seed}
    import handoff
    parallel = any(Path(row['note']).parent.resolve() != job.resolve() for row in handoff.unfinished_notes())
    if not parallel:
        history.parent.mkdir(parents=True, exist_ok=True)
        with C.file_mutex(history.with_suffix('.lock')):
            C.atomic_text(history, json.dumps({'last': {'signature': sig, 'sticker': st_sig, 'transition': tr_sig,
                                                        'emphasis': em_sig}, 'job': str(job)}, ensure_ascii=False))
    C.atomic_text(path, json.dumps({'plan': plan, 'fingerprint': fingerprint, 'history_deferred': parallel}, ensure_ascii=False))
    return dict(style, _variety=plan)


def _choose(prefs, seq, counts, quota, max_run):
    """First preference that keeps the run <= max_run and the share under quota."""
    for cand in prefs + [p for p in seq[-1:]]:
        run = 0
        for prev in reversed(seq):
            if prev != cand:
                break
            run += 1
        if run < max_run and counts.get(cand, 0) < quota:
            return cand
    return min(prefs, key=lambda c: counts.get(c, 0))


def caption_plan(style, cues, fps):
    """Per cue: entrance/sub/emphasis/exit from role + energy, plus seeded ±frames and ±easing."""
    vp, vc = style.get('_variety'), variety_cfg(style)
    if not vp or not vc['enabled']:
        return None
    mc = config(style)
    pool = [vp['signature']] + [o for o in vp['others'] if o != vp['signature']]
    strong = [p for p in pool if p in STRONG]; soft = [p for p in pool if p in SOFT]
    n = len(cues); quota = max(1, int(vc['max_share'] * n))
    seq, counts, out = [], {}, []
    for i, cue in enumerate(cues):
        role = role_of(cue['text'], i, cue['start'])
        lvl = energy_level(style, cue['start'])
        calm, peak = lvl is not None and lvl < .35, lvl is not None and lvl > .75
        # category by role and energy; inside it the signature leads, then the least-used other
        rank = lambda group: sorted(group, key=lambda e: (e != vp['signature'], counts.get(e, 0)))
        group = {'hook': strong, 'number': strong, 'question': soft, 'list': [p for p in pool if p == 'slide_overshoot'] or strong,
                 'key': rank(soft) if calm else [vp['signature']] + soft, 'hero': soft if calm else strong,
                 'calm': strong if peak else soft}[role]
        prefs = list(dict.fromkeys(rank(group) + rank(pool)))
        enter = _choose(prefs, seq, counts, quota, int(vc['max_run']))
        seq.append(enter); counts[enter] = counts.get(enter, 0) + 1
        alt = 'scale_punch' if vp['emphasis'] != 'scale_punch' else 'underline_draw'
        emph = {'number': 'pop_overshoot', 'key': 'box_wipe', 'question': 'colour_sweep', 'list': 'underline_draw',
                'hero': vp['emphasis'] if counts[enter] % 2 else alt}.get(role, vp['emphasis'])
        r = _rng(vp['seed'], 'cue', i, cue['start'])
        jit = r.randint(-int(vc['jitter_frames']), int(vc['jitter_frames'])) * 1000 / fps
        out.append({'role': role, 'energy': None if lvl is None else round(lvl, 2), 'enter': enter,
                    'sub': enter if enter in SOFT else (soft[0] if soft else 'mask_up'), 'emphasis': emph,
                    'exit': mc['pairs'].get(enter, 'fade'), 'jitter_ms': round(jit, 1),
                    'ease_k': round(1 + r.uniform(-1, 1) * float(vc['ease_jitter']), 4)})
    return out


def element_plan(style, elements):
    """Moves for elements without explicit motion: stickers enter, b-roll transitions, panel easing, still push."""
    vp, vc = style.get('_variety'), variety_cfg(style)
    if not vp or not vc['enabled']:
        return elements, []
    stickers = [vp['sticker']] + vp['sticker_others']; trans = [vp['transition']] + vp['transition_others']
    order = sorted(range(len(elements)), key=lambda i: float(elements[i].get('start', elements[i].get('at', 0)) or 0))
    out = [dict(e) for e in elements]; moves = []
    seqs, counts = {}, {}
    n_kind = {}
    for i in order:
        k = out[i].get('type')
        n_kind[k] = n_kind.get(k, 0) + 1
    side = 1
    for i in order:
        el, kind = out[i], out[i].get('type')
        t = float(el.get('start', el.get('at', 0)) or 0)
        lvl = energy_level(style, t); peak, calm = lvl is not None and lvl > .75, lvl is not None and lvl < .35
        quota = lambda group: max(1, int(vc['max_share'] * max(4, n_kind.get(kind, 1))))
        if kind in ('image', 'icon', 'emoji') and not any(x in el for x in ('anim', 'enter')):
            prefs = ([m for m in stickers if m in STRONG_STICKER] if peak else [m for m in stickers if m not in STRONG_STICKER] if calm else []) + stickers
            m = _choose(list(dict.fromkeys(prefs)), seqs.setdefault('sticker', []), counts.setdefault('sticker', {}), quota('sticker'), int(vc['max_run']))
            if m in ('slide_left', 'slide_right'):          # alternate sides so nothing looks mechanical
                m = 'slide_left' if side > 0 else 'slide_right'; side = -side
            seqs['sticker'].append(m); counts['sticker'][m] = counts['sticker'].get(m, 0) + 1
            el['enter'] = m; moves.append((t, kind, m))
            if kind == 'image' and 'push' not in el and float(el.get('end', t)) - t > 1.5:
                r = _rng(vp['seed'], 'push', i); el['push'] = round(r.choice((1, 1, -1)) * r.uniform(.03, .07), 3)
        elif kind == 'broll' and not any(x in el for x in ('fade', 'transition')):
            prefs = (['push', 'mask', 'flash'] if peak else ['cut', 'fade'] if calm else []) + trans
            m = _choose([p for p in dict.fromkeys(prefs) if p in trans] or trans, seqs.setdefault('broll', []),
                        counts.setdefault('broll', {}), quota('broll'), int(vc['max_run']))
            seqs['broll'].append(m); counts['broll'][m] = counts['broll'].get(m, 0) + 1
            el['transition'] = m; el['transition_dir'] = side; side = -side; moves.append((t, 'broll', m))
        elif kind in ('label', 'list', 'stat', 'follow', 'callout', 'lower_third', 'card', 'group', 'hero', 'calendar',
                      'panel', 'voice', 'choice') and 'ease_mode' not in el:
            prefs = (['spring', 'overshoot'] if peak else ['soft', 'snappy'] if calm else []) + list(ENTER_EASES)
            m = _choose(list(dict.fromkeys(prefs)), seqs.setdefault('panel', []), counts.setdefault('panel', {}), quota('panel'), int(vc['max_run']))
            seqs['panel'].append(m); counts['panel'][m] = counts['panel'].get(m, 0) + 1
            el['ease_mode'] = m; moves.append((t, kind, m))
    return out, moves


def zoom_variety(style, bounds, punch, push, min_seg):
    """Cut zooms: some cuts none, others 104-110% eased in over a varied time, then a slow push."""
    vp, vc = style.get('_variety'), variety_cfg(style)
    plan, moves, seq = [], [], []
    lo, hi = (float(x) for x in vc['zoom_range'])
    for i, (t0, t1) in enumerate(bounds):
        r = _rng(vp['seed'], 'zoom', i)
        run_on = len(seq) >= int(vc['max_run']) and all(s == 'in' for s in seq[-int(vc['max_run']):])
        if i == 0 or t1 - t0 < min_seg or r.random() < float(vc['zoom_skip']) or run_on:
            plan.append((t0, t1, 1.0, 1.0)); seq.append('none'); moves.append((t0, 'zoom', 'none'))
            continue
        level = round(r.uniform(lo, hi), 3); tin = min((t1 - t0) * .5, r.uniform(.35, .8))
        plan += [(t0, t0 + tin, 1.0, level), (t0 + tin, t1, level, level + push * min(1., (t1 - t0) / 4))]
        seq.append('in'); moves.append((t0, 'zoom', f'in{int(round((level - 1) * 100))}'))
    return plan, moves


def variety_report(seq):
    """Counts, longest run of identical consecutive moves, and the largest single-type share."""
    counts, run, best, prev = {}, 0, 0, None
    for m in seq:
        counts[m] = counts.get(m, 0) + 1
        run = run + 1 if m == prev else 1
        best, prev = max(best, run), m
    share = max(counts.values()) / len(seq) if seq else 0
    return {'n': len(seq), 'counts': counts, 'longest_run': best, 'max_share': round(share, 3)}


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--style',required=True); ap.add_argument('--job',required=True)
    a=ap.parse_args(); st=choose(C.load_style(a.style),Path(a.job)); C.info(json.dumps(config(st),ensure_ascii=False,indent=2))
if __name__=='__main__': C.run_main(main)
