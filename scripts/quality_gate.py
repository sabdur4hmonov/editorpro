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

VISUAL = {'hero', 'group', 'image', 'icon', 'card', 'canvas', 'title', 'text', 'stat',
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
    known = [r for r in rows if r['status'] in ('pass','fail')]
    score = round(100*sum(r['status']=='pass' for r in known)/len(known), 1) if known else None
    fixes = [dict(key=r['key'], status=r['status'], value=r['value'], target=r['target'], method=r['method'])
             for r in rows if r['status'] in ('fail','unknown')]
    return dict(schema=1, group=group, format=plan.get('format'), targets=targets, measurements=rows,
                score=score, known=len(known), total=sum(r['status']!='not_applicable' for r in rows), fix_list=fixes,
                status='measured_pass' if not fixes else 'needs_fix_or_measurement',
                creative_approval=False, sound_approval=False,
                caption_centres={'x':xs, 'y':ys}, item_event_times=events, repeat_conflicts=duplicates)


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
