"""Measured technical/style gate. A score never establishes creative or sound approval.

python scripts/quality_gate.py VIDEO --style STYLE --plan PLAN --result RESULT
    [--subs SUBS --elements ELEMENTS --cuts CUT_TIMES_JSON -o REPORT]
Cut times must be verified source/output edit times, not a scene detector's unreviewed candidates.
Missing measurements remain unknown. Final enforcement is opt-in: quality.enforce_final.
"""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import common as C
import elements as E
import graphics_ideas as GI
import motion_language as ML

VISUAL = {'calendar', 'panel', 'logo_sting', 'mask_reveal', 'hero', 'group', 'image', 'icon', 'card', 'canvas', 'title', 'text', 'stat',
          'list', 'choice', 'broll', 'label', 'aside', 'callout', 'follow', 'phone', 'handnote'}


def editorial_cut_times(cuts):
    """Output boundaries from applied auto_cut keep/speed, or explicit verified times.

    Unknown source/detector candidates are not guessed. Native keep is the applied edit plan.
    """
    if not isinstance(cuts, dict):
        return None
    if 'times' in cuts:
        return list(cuts['times'])
    if 'keep' not in cuts:
        return None
    speed=float(cuts.get('speed',1.0))
    if not math.isfinite(speed) or speed<=0:
        raise C.MontajError('Quality cut plan: speed > 0 kerak.')
    ends=[];pos=0
    for seg in cuts['keep']:
        length=float(seg['end'])-float(seg['start'])
        if not math.isfinite(length) or length<=0:
            raise C.MontajError('Quality cut plan: keep interval noto‘g‘ri.')
        pos+=length/speed;ends.append(pos)
    return ends[:-1]


def evaluate(style, cues, elements, duration, plan, result=None, cut_times=None):
    import sample_groups as SG
    group = plan.get('style_group') or style.get('sample_group', {}).get('id')
    dna = C.read_json(SG.DNA_DIR / group / 'style_dna.json') if group in SG.FAMILIES else {}
    targets = C.deep_merge(dna.get('quality_targets', {}), plan.get('quality_targets', {}))
    if not math.isfinite(duration) or duration <= 0:
        raise C.MontajError('Quality gate: duration > 0 kerak.')
    rows = []
    def add(key, value, target=None, hard=False, method=''):
        if value is None:
            state = 'unknown'
        elif isinstance(target, (list, tuple)):
            state = 'pass' if target[0] <= value <= target[1] else 'fail'
        elif isinstance(target, (int, float)):
            state = 'pass' if value <= target else 'fail'
        else:
            state = 'pass' if value else 'fail'
        rows.append(dict(key=key, value=value, target=target, status=state, hard=hard, method=method))
    visual = [el for el in elements if el.get('type') in VISUAL]
    starts = sorted(set(float(el.get('start', 0)) for el in visual))
    events = sorted(set(starts + [float(it.get('at', el.get('start', 0))) for el in visual for it in el.get('items', [])]))
    add('cuts_per_min', None if cut_times is None else len([t for t in cut_times if 0 < t < duration])*60/duration,
        targets.get('cuts_per_min'), method='verified editorial cuts; zoom/overlay changes are not cuts')
    add('graphics_per_min', len(visual)*60/duration, targets.get('graphics_per_min'), method='top-level visual element starts; group children separately in event spacing')
    gaps = [b-a for a, b in zip(starts, starts[1:]) if b>a]
    min_gap = min(gaps) if gaps else duration
    add('event_spacing', min_gap >= targets.get('min_gap_s', 0), method=f'min top-level graphic start gap {min_gap:.3f}s; intra-group word-synced stagger is measured separately')
    spans = sorted((max(0, float(el.get('start', 0))), min(duration, float(el.get('end', duration)))) for el in visual)
    calm, end = 0.0, 0.0
    for a, b in spans:
        calm = max(calm, a-end); end = max(end, b)
    calm = max(calm, duration-end)
    add('calm_stretch', calm >= min(duration, targets.get('calm_stretch_s', 0)), method=f'longest span without added graphic {calm:.3f}s; captions/source motion can remain')
    first = min([c['start'] for c in cues] + [el['start'] for el in visual if el.get('text') or any(i.get('text') for i in el.get('items', []))], default=None)
    add('hook_text_s', first, targets.get('hook_text_s'), method='first planned text onset; spoken/practical hook still needs editorial review')
    ctx = E.Ctx(style, C.brand_dir(style))
    cap = E.CaptionLayer(ctx, cues, None, duration)
    sizes, ys, xs = [], [], []
    for item in cap.items:
        cap._prepare(item)
        b = item['block']; cx, cy = cap._center(b, item['cfg'])
        sizes += [s/ctx.H*100 for s in b.line_sizes]
        ys.append(cy/ctx.H); xs.append(cx/ctx.W)
    cap.close()
    add('caption_size_pct_h', sorted(sizes)[len(sizes)//2] if sizes else None,
        targets.get('caption_size_pct_h'), method='median actual fitted font line size / render height; NOT ink bbox or unidentified reference font')
    pos = targets.get('caption_position_y')
    if pos is not None:
        add('caption_position_y', sorted(ys)[len(ys)//2] if ys else None, pos, method='actual fitted caption centres')
    mc = ML.config(style)
    frame_lengths = []
    for el in visual:
        key = 'hero' if el['type']=='hero' else ('label' if el['type'] in ('group', 'label', 'card') else 'sticker')
        seconds = float(el.get('duration', ML.duration(mc, key)))
        frame_lengths.append(seconds*30)
    if frame_lengths:
        add('entrance_frames_30fps', sorted(frame_lengths)[len(frame_lengths)//2],
            targets.get('entrance_frames_30fps'), method='configured entrance seconds × 30; output native frame counts recorded separately; no claim of exact source easing')
    else:
        rows.append(dict(key='entrance_frames_30fps',value=None,target=targets.get('entrance_frames_30fps'),
                         status='not_applicable',hard=False,method='No added graphics: no graphic entrance exists to measure. Caption entrances still require filmstrip review.'))
    duplicates = [r for r in GI.repeat_violations(elements, cues) if not r['allowed']]
    add('no_repeat', not duplicates, hard=True, method=f'{len(duplicates)} duplicate caption/label conflicts')
    result = result or {}
    safety = result.get('face_safety', {})
    verified = safety.get('verification') == 'measured' or safety.get('frames_with_face', 0)>0
    add('face_coverage', safety.get('max_cover') if verified else None,
        targets.get('max_face_cover', .03), hard=True,
        method='EVERY overlaid frame, YuNet expanded box changed-pixel share; low-contrast overlays and missed faces remain limitations')
    add('export', all(r[1]!='xato' for r in result['checks']) if result.get('checks') else None, hard=True,
        method='ffprobe/platform actual render checks')
    audio = result.get('audio', {})
    add('voice_margin', float(audio['margin_db']) >= float(style.get('audio', {}).get('voice_margin_db', 10))
        if audio.get('additions') and audio.get('margin_db') is not None else (True if audio and not audio.get('additions') else None),
        hard=True, method='measured additions relative to speech; never change the voice to boost SFX')
    # Integrated loudness is a separate measurement: never use RMS in its place.
    add('lufs', result.get('integrated_lufs'), targets.get('lufs'), method='ffmpeg ebur128, supplied measured integrated LUFS')
    lint = result.get('motion_lint')
    if lint:  # only when the render traced its blits; legacy reports keep their rows unchanged
        add('motion_lint_flags_per_min', round(lint['flags']*60/duration, 2), targets.get('motion_lint_flags_per_min', 6),
            method='review_tools.lint_rows: short/linear/velocity-jump/at-once/caption-on-cut/jump/direction flags')
        if lint.get('drift_jitter_px') is None:
            rows.append(dict(key='drift_jitter_px', value=None, target=None, status='not_applicable', hard=False,
                             method='no slow drift (<1.5 px/frame for 8+ frames) in this render'))
        else:
            add('drift_jitter_px', lint['drift_jitter_px'], targets.get('drift_jitter_px', .15),
                method='mean |2nd difference| of slow drifts as placed; integer placement shows 1 px stair steps')
    smooth = result.get('smoothness')
    if smooth:  # permanent smoothness check (measured after the render)
        add('held_frames', smooth['held_frames'], 0, method=f"isolated repeats of the decoded picture, {smooth['source_fps']:g} -> {smooth['fps']:g} fps")
        bad = [r for r in smooth['cuts'] if r['dip_db'] < SMOOTH_LIMITS['cut_dip_db'] or r['click'] > SMOOTH_LIMITS['cut_click']]
        add('cut_audio_holes', len(bad) if smooth['cuts'] else None, 0, method='5 ms min vs room tone (dip) and sample step (click) at editorial cuts')
        late = [r for r in smooth['caption_lag'] if not SMOOTH_LIMITS['caption_early_ms'] <= r['lag_ms'] <= SMOOTH_LIMITS['caption_late_ms']]
        add('caption_lag', len(late) if smooth['caption_lag'] else None, 0, method='cue onset vs its first spoken word, -150..+80 ms')
    variety = result.get('variety')
    if variety:  # mechanical repetition: run of identical animations <= 3, no type over 60 %
        for key in ('captions', 'motion'):
            rep = variety[key]
            if rep['n'] >= 4:
                add(f'{key}_variety_run', rep['longest_run'], targets.get('variety_max_run', 3),
                    method=f'longest run of identical consecutive {key} animations; counts {rep["counts"]}')
                add(f'{key}_variety_share', rep['max_share'], targets.get('variety_max_share', .6),
                    method=f'largest single {key} animation share of {rep["n"]}')
    contrast = result.get('caption_contrast')
    if contrast:
        add('caption_contrast_min', min(c[2] for c in contrast) >= targets.get('caption_contrast', 4.5),
            method=f'WCAG ratio text vs measured background after adaptive scrim, {len(contrast)} cue/shot samples')
    known = [r for r in rows if r['status'] in ('pass','fail')]
    score = round(100*sum(r['status']=='pass' for r in known)/len(known), 1) if known else None
    fixes = [dict(key=r['key'], status=r['status'], value=r['value'], target=r['target'], method=r['method'])
             for r in rows if r['status'] in ('fail','unknown')]
    return dict(schema=1, group=group, format=plan.get('format'), targets=targets, measurements=rows,
                score=score, known=len(known), total=sum(r['status']!='not_applicable' for r in rows), fix_list=fixes,
                status='measured_pass' if not fixes else 'needs_fix_or_measurement',
                creative_approval=False, sound_approval=False,
                caption_centres={'x':xs, 'y':ys}, item_event_times=events, repeat_conflicts=duplicates)



# ---------------------------------------------------------------- smoothness check (after every render)
SMOOTH_LIMITS = {'held_frames': 0, 'cut_dip_db': -10.0, 'cut_click': 3.0, 'caption_late_ms': 80, 'caption_early_ms': -150,
                 'drift_jitter_px': .15, 'max_run': 3, 'max_share': .6}


def held_frames(hashes):
    """Isolated exact repeats of the decoded source picture while it moves (25->30 style duplication)."""
    out = []
    for i in range(2, len(hashes)):
        if hashes[i] == hashes[i - 1] and hashes[i - 1] != hashes[i - 2] and (i + 1 >= len(hashes) or hashes[i + 1] != hashes[i]):
            out.append(i)
    return out


def cut_audio_rows(wav, cut_times, sr=48000):
    """Per editorial cut: 5 ms minimum vs the room tone before it (dip) and the largest sample step (click)."""
    import wave
    import numpy as np
    with wave.open(str(wav), 'rb') as w:
        ch, sr = w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, ch).mean(1).astype(np.float32) / 32768
    db = lambda v: 20 * math.log10(max(1e-7, float(np.sqrt(np.mean(v * v))) if len(v) else 1e-7))
    rows = []
    for t in cut_times:
        n = int(t * sr)
        if n < int(.15 * sr) or n > len(x) - int(.05 * sr):
            continue
        room = db(x[n - int(.12 * sr):n - int(.03 * sr)])
        low = min(db(x[i:i + 240]) for i in range(n - int(.02 * sr), n + int(.02 * sr) - 240, 120))
        step = np.abs(np.diff(x[n - int(.02 * sr):n + int(.02 * sr)]))
        ref = np.percentile(np.abs(np.diff(x[max(0, n - sr // 2):n + sr // 2])), 99) + 1e-6
        rows.append({'t': round(t, 3), 'dip_db': round(low - room, 1), 'click': round(float(step.max() / ref), 2)})
    return rows


def caption_lag_rows(cues, words):
    """Cue onset minus the start of its first spoken word (text-matched within 1 s)."""
    import re
    norm = lambda s: re.sub(r'[^\w]', '', str(s).lower().replace('‘', '').replace('’', '').replace("'", ''))
    rows = []
    for c in cues:
        toks = [norm(t) for t in re.sub(r'\{[^}]*\}|[*_=~!]', ' ', c['text']).split() if norm(t)]
        cand = [w for w in words or [] if toks and norm(w.get('word', w.get('text', ''))) == toks[0] and abs(float(w['start']) - c['start']) < 1]
        if cand:
            w = min(cand, key=lambda w: abs(float(w['start']) - c['start']))
            rows.append({'t': round(c['start'], 3), 'lag_ms': round((c['start'] - float(w['start'])) * 1000)})
    return rows


def smoothness(fps, source_fps, hashes, wav=None, cut_times=(), cues=(), words=None, lint=None, variety=None, anims=None):
    """Permanent smoothness check: frame cadence, sub-pixel jitter, cut clicks/holes, caption lag, repetition.
    Returns rows + warnings with time codes; never raises (a measurement, not a render blocker)."""
    L, warn = SMOOTH_LIMITS, []
    held = held_frames(hashes)
    if len(held) > L['held_frames']:
        gaps = sorted({b - a for a, b in zip(held, held[1:])})[:3]
        warn.append(f"{len(held)} takror kadr (source {source_fps:g} -> {fps:g} fps), oraliq {gaps} kadr; birinchi "
                    + ', '.join(C.fmt_time(i / fps) for i in held[:5]))
    cuts = cut_audio_rows(wav, cut_times) if wav and cut_times else []
    for r in cuts:
        if r['dip_db'] < L['cut_dip_db'] or r['click'] > L['cut_click']:
            warn.append(f"kesish {C.fmt_time(r['t'])}: ovoz teshigi {r['dip_db']} dB, klik {r['click']}")
    lag = caption_lag_rows(list(cues), words)
    for r in lag:
        if r['lag_ms'] > L['caption_late_ms'] or r['lag_ms'] < L['caption_early_ms']:
            warn.append(f"subtitr {C.fmt_time(r['t'])}: so'zdan {r['lag_ms']} ms {'kech' if r['lag_ms'] > 0 else 'erta'}")
    jitter = (lint or {}).get('drift_jitter_px')
    if jitter is not None and jitter > L['drift_jitter_px']:
        warn.append(f"sekin driftda piksel titrashi {jitter} px (subpixel yoqilmagan bo'lishi mumkin)")
    for f in (lint or {}).get('flag_rows', [])[:5]:
        warn.append(f"animatsiya {C.fmt_time(f['frame'] / fps)}: {f['flag']} ({f.get('track', '')})")
    rep = variety or {}
    if not rep and anims:
        import motion_language as ML
        rep = {'captions': ML.variety_report(anims)}
    for key, r in rep.items():
        if r.get('n', 0) >= 4 and (r['longest_run'] > L['max_run'] or r['max_share'] > L['max_share']):
            warn.append(f"{key}: bir xil animatsiya ketma-ket {r['longest_run']} marta, eng ko'p tur {round(r['max_share'] * 100)}% "
                        f"({r['counts']})")
    return {'fps': fps, 'source_fps': source_fps, 'held_frames': len(held), 'held_at': held[:50], 'cuts': cuts,
            'caption_lag': lag, 'drift_jitter_px': jitter, 'lint_flags': (lint or {}).get('flags'),
            'repetition': rep, 'warnings': warn, 'limits': L}


def markdown(rep):
    text = [f"# Sifat dalili — {rep['format']} / {rep['group']}", '',
            f"Holat: **{rep['status']}**. O‘lchangan ball: {rep['score']} ({rep['known']}/{rep['total']} mezon).",
            'Bu ball professional did, harakat yoki ovoz tasdig‘i emas. Unknown mezon o‘tdi hisoblanmaydi.', '',
            '| Mezon | Natija | Nishon | Holat |', '|---|---|---|---|']
    text += [f"| {r['key']} | {r['value']} | {r['target']} | {r['status']} |" for r in rep['measurements']]
    text += ['', '## Tuzatish / o‘lchash', '']+[f"- {r['key']}: {r['method']}" for r in rep['fix_list']]
    return '\n'.join(text)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video'); p.add_argument('--style', required=True); p.add_argument('--plan', required=True)
    p.add_argument('--result', required=True); p.add_argument('--subs'); p.add_argument('--elements'); p.add_argument('--cuts')
    p.add_argument('-o','--out')
    a=p.parse_args(); video=C.need_file(a.video,'Video'); work=video.parent if C.is_inside(video,C.TEMP_DIR) else C.job_dir(video)
    s=C.read_json(a.style); plan=C.read_json(a.plan); result=C.read_json(a.result)
    sp=Path(a.subs) if a.subs else work/'subs.srt'; ep=Path(a.elements) if a.elements else work/'elements.json'
    cuts=editorial_cut_times(C.read_json(a.cuts)) if a.cuts else None
    rep=evaluate(s,C.parse_srt(sp) if sp.is_file() else [], C.read_json(ep).get('elements',[]) if ep.is_file() else [],
                 C.ffprobe_info(video)['duration'], plan,result,cuts)
    dest=C.guard_output(Path(a.out) if a.out else work/'quality_gate.json'); C.write_json(rep,dest)
    dest.with_suffix('.md').write_text(markdown(rep),encoding='utf-8')
    C.info(f"QUALITY: {rep['status']}; score {rep['score']}; measured {rep['known']}/{rep['total']}; {dest}")
    return 0 if rep['status']=='measured_pass' else 3

if __name__=='__main__': C.run_main(main)
