"""Motion/audio evidence: filmstrip, aligned A/B, motion lint, slow-motion review, event stems, waveform."""
from __future__ import annotations
import argparse
import json
import math
import tempfile
import wave
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import common as C
import frames
import render as R

def timepoints(start, end, n, duration):
    if not 0 <= start < end <= duration + .001 or not 2 <= n <= 120:
        raise C.MontajError('Range: 0 <= start < end <= duration, N: 2..120.')
    return np.linspace(start, min(end, duration - .001), n).tolist()

def visual_sheet(videos, times, out, height=320):
    paths = [C.need_file(v, 'Video') for v in videos]
    if not times or len(times)>120 or not 80 <= height <= 1080:
        raise C.MontajError('Frames: 1..120; height: 80..1080.')
    for p in paths:
        duration = C.ffprobe_info(p)['duration']
        if any(not math.isfinite(t) or t < 0 or t >= duration for t in times):
            raise C.MontajError(f'Timestamp outside video: {p.name}')
    out = C.guard_output(out)
    if out.resolve() in [p.resolve() for p in paths]:
        raise C.MontajError('Sheet output cannot replace input.')
    font=ImageFont.load_default(size=16)
    cols=min(6,len(times)); rows=(len(times)+cols-1)//cols
    thumbs=[]
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='review_') as td:
        for vi,p in enumerate(paths):
            group=[]
            for i,t in enumerate(times):
                f=Path(td)/f'{vi}_{i}.jpg'
                if not frames.grab(p,t,f,height):
                    raise C.MontajError(f'Frame failed: {p.name}, {t:.4f}s')
                with Image.open(f) as im: group.append(im.convert('RGB').copy())
            thumbs.append(group)
    width=max(im.width for group in thumbs for im in group)
    cell_h=(height+28)*len(paths)
    sheet=Image.new('RGB',(cols*(width+8)+8,rows*(cell_h+8)+8),'#15171B')
    draw=ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        x=8+(i%cols)*(width+8); y=8+(i//cols)*(cell_h+8)
        for vi,group in enumerate(thumbs):
            yy=y+vi*(height+28)
            draw.text((x,yy),f'{vi+1}: {t:07.3f}s  {paths[vi].stem}',font=font,fill='white')
            sheet.paste(group[i],(x,yy+28))
    sheet.save(out)
    report={'output':str(out),'videos':[str(p) for p in paths],'times':times,'count':len(times)}
    C.write_json(report,out.with_suffix('.json'))
    return report

def pcm(path):
    with wave.open(str(path),'rb') as f:
        if f.getsampwidth()!=2: raise C.MontajError('Cue meter requires PCM s16 WAV.')
        sr=f.getframerate(); ch=f.getnchannels()
        data=np.frombuffer(f.readframes(f.getnframes()),np.int16).astype(np.float64)/32768
    return data.reshape(-1,ch),sr

def metrics(path, work):
    data,sr=pcm(path)
    peak=float(np.max(np.abs(data))) if data.size else 0
    meter=R.measure_loudness(['-i',str(path)],'[0:a]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[aout]',work)
    return {'sample_peak_dbfs': round(20*math.log10(max(peak,1e-12)),2),
            'loudness_lufs':meter['input_i'] if meter else None,
            'true_peak_dbtp':meter['input_tp'] if meter else None}

def waveform(path, events, out):
    data,sr=pcm(path); data=np.max(np.abs(data),axis=1)
    width,height=1600,360; samples=np.array_split(data,width-80)
    im=Image.new('RGB',(width,height),'#15171B'); d=ImageDraw.Draw(im)
    for i,chunk in enumerate(samples):
        amp=float(np.max(chunk)) if chunk.size else 0
        d.line((40+i,160-amp*125,40+i,160+amp*125),fill='#62A6E8')
    duration=len(data)/sr
    for i,e in enumerate(events):
        x=40+int(float(e['at'])/max(.001,duration)*(width-80))
        d.line((x,20,x,300),fill='#FFCF59')
        d.text((min(x,width-210),20+(i%4)*16),f"{e['at']:.3f}s {e['kind']}",fill='white')
    d.text((40,320),f'0s -> {duration:.3f}s | amplitude, event start markers',fill='white')
    im.save(out)

def audio_report(voice, additions, final, style, events, music, reduction, duck_sfx, duck_music, design_events=None):
    """Render each event with the SAME sidechain/gain as the bus; measure, do not infer taste.

    Stem meters are pre final-mix limiter; bus window includes other overlapping events.
    Music uses its actual loop, fade and duck chain. No unlicensed assets are fetched.
    """
    work=final.parent; v,sr=pcm(voice)
    rows=[]; specs=[dict(at=at,file=str(p),volume_db=vol,kind='sfx') for at,p,vol in events]
    for spec in specs:
        match=next((e for e in design_events or [] if abs(e['at']-spec['at'])<.0001),{})
        spec.update({k:match[k] for k in ('kind','category','visual_at','lead_frames_actual') if k in match})
        spec['bus']='sfx'
    if music:
        specs.append(dict(at=0,file=str(music),volume_db=float(style['audio'].get('music_volume_db',-20)),kind='music'))
    total=len(v)/sr
    keep=bool(style['audio'].get('export_stems',False))
    buses={name:np.zeros_like(v) for name in ('sfx','music')} if keep else {}
    with tempfile.TemporaryDirectory(dir=work,prefix='cue_') as td:
        for i,e in enumerate(specs):
            stem=Path(td)/f'{i}.wav'
            inputs=['-i',str(voice)]
            if e.get('bus')!='sfx': inputs += ['-stream_loop','-1']
            inputs+=['-i',e['file']]
            chain=f"[1:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo,volume={e['volume_db']}dB"
            duck=duck_music if e.get('bus')!='sfx' else duck_sfx
            if e.get('bus')!='sfx':
                fade=max(0,min(float(style['audio'].get('music_fade_sec',1.5)),total/3))
                chain+=f',atrim=0:{total}'
                if fade: chain+=f',afade=t=in:st=0:d={min(.5,fade)},afade=t=out:st={total-fade}:d={fade}'
            else: chain+=f",adelay={round(e['at']*1000)}:all=1"
            chain+=f',apad=whole_dur={total},atrim=0:{total}[raw]'
            if duck:
                threshold,ratio,attack,release=(.03,6,20,350) if e.get('bus')!='sfx' else (.05,4,5,160)
                chain+=f';[raw][0:a]sidechaincompress=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}[duck]'
            chain+=f";[{'duck' if duck else 'raw'}]volume={-reduction}dB[out]"
            C.run_ffmpeg_graph(inputs,chain,['-map','[out]','-t',str(total),'-c:a','pcm_s16le','-ar',str(sr),str(stem)],work)
            info=metrics(stem,work); a,_=pcm(stem)
            if keep:
                bus='sfx' if e.get('bus')=='sfx' else 'music'
                n=min(len(a),len(v)); buses[bus][:n]+=a[:n]
            active=np.max(np.abs(a),axis=1)>10**(-70/20)
            speech=np.sqrt(np.mean(v*v,axis=1))>10**(-45/20)
            n=min(len(active),len(speech)); active=active[:n]; speech=speech[:n]
            both=active&speech
            margin=None
            if both.any():
                vr=math.sqrt(float(np.mean(v[:n][both]**2)))
                ar=math.sqrt(float(np.mean(a[:n][both]**2)))
                margin=round(20*math.log10(max(vr,1e-12)/max(ar,1e-12)),2)
            rows.append(dict(e,**info,speech_margin_rms_db=margin,global_reduction_db=reduction,
                             measurement='rendered isolated stem, sidechain applied, before final limiter'))
    if keep:
        import subprocess
        stems=work/'stems'; stems.mkdir(exist_ok=True)
        shutil.copy2(voice,stems/'speech.wav')
        for name,data in buses.items():
            proc=subprocess.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y',
                 '-f','f32le','-ar',str(sr),'-ac','2','-i','-','-c:a','pcm_f32le',str(stems/(name+'.wav'))],
                 input=data.astype('<f4').tobytes(),capture_output=True)
            if proc.returncode: raise C.MontajError('Audio stem encode: '+proc.stderr.decode('utf-8','replace')[-400:])
    report={'events':rows,'voice':metrics(voice,work),'mix':metrics(final,work),
            'required_voice_margin_db':style['audio'].get('voice_margin_db',10),
            'bus_margin_percentile_db':__import__('audio_mix').voice_margin(voice,additions),
            'global_reduction_db':reduction,'note':'Bus margin before global reduction; individual stem RMS is a different meter.'}
    C.write_json(report,work/'audio_cues.json')
    lines=['# Audio cue sheet','', '| Time | Kind | File | Gain dB | Stem LUFS | True peak dBTP | Speech above stem RMS dB |',
           '|---|---|---|---:|---:|---:|---:|']
    for e in rows: lines.append(f"| {e['at']:.3f} | {e['kind']} | {e['file']} | {e['volume_db']} | {e['loudness_lufs']} | {e['true_peak_dbtp']} | {e['speech_margin_rms_db']} |")
    lines+=['','Meters are rendered isolated stems after ducking and global reduction, before the final limiter.',
            'LUFS covers the full timeline; short SFX may measure very low or return null. Listening approval is separate.']
    (work/'audio_cues.md').write_text('\n'.join(lines),encoding='utf-8')
    waveform(final,rows,work/'audio_waveform.png')
    return report

# ---------------------------------------------------------------- motion lint (blit trace -> curves, flags)

LINT_LIMITS = {'min_frames': 4, 'linear_cv': .12, 'linear_min_px': 1.0, 'jump_px': 8.0, 'jump_rel': .6,
               'at_once': 5, 'cut_jump_px': 2.0, 'drift_max_px': 1.5}


def _runs(mask):
    """[(i0, i1)] inclusive runs of True; gaps of one still frame are merged (spring settle)."""
    out = []
    for i, m in enumerate(mask):
        if not m:
            continue
        if out and i - out[-1][1] <= 2:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [tuple(r) for r in out]


def lint_rows(rows, fps, k=1.0, cuts=(), offset_frames=2, frame_range=None):
    """Frame-by-frame position/scale/opacity of every traced sprite -> animations + flags.

    Pixels are normalised to a 1080x1920 frame (divide by k). A run touching the traced range edge is
    reported but never flagged short. Flags: short, linear, velocity_jump, all_at_once,
    caption_on_cut, jump_at_cut, direction_mismatch; drift_jitter = mean |2nd difference| of slow drifts.
    """
    from collections import defaultdict
    L = LINT_LIMITS
    tracks = defaultdict(dict)
    for r in rows:
        tracks[(r[1], r[2])].setdefault(r[0], r)          # first call wins if a tag repeats in a frame
    lo = frame_range[0] if frame_range else None
    hi = frame_range[1] - 1 if frame_range else None
    cut_f = [int(round(c * fps)) for c in cuts or ()]
    anims, flags, jitters, steps, cue_onset = [], [], [], 0, {}
    starts = defaultdict(set)
    exits, entries = [], []
    for key, by_f in tracks.items():
        fs = sorted(by_f)
        segs, cur = [], [fs[0]]
        for a, b in zip(fs, fs[1:]):
            if b == a + 1:
                cur.append(b)
            else:
                segs.append(cur)
                cur = [b]
        segs.append(cur)
        for seg in segs:
            arr = np.array([by_f[f][3:9] for f in seg], np.float64)
            x, y, w, h, sc, op = (arr[:, i] for i in range(6))
            x, y, w = x / k, y / k, w / k
            if seg[0] != lo and op[0] < .98:
                starts[seg[0]].add(key)
            if key[0] == 'captions' and seg[0] != lo:
                cue = key[1].split(':')[0]
                if seg[0] < cue_onset.get(cue, (1 << 30, ''))[0]:
                    cue_onset[cue] = (seg[0], '/'.join(key))
            if len(seg) < 2:
                continue
            # an edge-anchored draw-on/wipe moves its bbox centre by half the growth: not a move
            dpos = np.maximum(0, np.hypot(np.diff(x), np.diff(y)) - .5 * np.hypot(np.diff(w), np.diff(h / k)))
            dsc = np.abs(np.diff(w)) / np.maximum(w[:-1], 1)
            dop = np.abs(np.diff(op))
            moving = (dpos > .05) | (dsc > .002) | (dop > .01)
            moving &= ~((dsc > .15) & (dpos < .05) & (dop < .01))   # one-frame content swap (marker on/off)
            for c in cut_f:                                  # caption/sticker that stays across a cut
                if seg[0] < c <= seg[-1] and c - 1 in by_f:
                    i = seg.index(c) - 1
                    if dpos[i] > L['cut_jump_px'] and not (moving[max(0, i - 1)] and moving[min(len(dpos) - 1, i + 1)]):
                        flags.append({'flag': 'jump_at_cut', 'track': '/'.join(key), 'frame': c, 'px': round(float(dpos[i]), 2)})
            for i0, i1 in _runs(moving):
                f0, f1 = seg[i0], seg[i1 + 1]
                v = dpos[i0:i1 + 1]
                n = i1 - i0 + 1
                n += int(i0 == 0 and op[0] < .98) + int(i1 == len(dpos) - 1 and op[-1] < .2)  # from/to nothing
                edge = (lo is not None and f0 <= lo) or (hi is not None and f1 >= hi)
                a = {'track': '/'.join(key), 'start': f0, 'end': f1, 'frames': n, 'max_px': round(float(v.max()), 2),
                     'mean_px': round(float(v.mean()), 2), 'scale_rel': round(float(dsc[i0:i1 + 1].sum()), 3),
                     'opacity': [round(float(op[i0]), 2), round(float(op[i1 + 1]), 2)], 'flags': []}
                if n < L['min_frames'] and not edge:
                    if v.max() > 1.5 or dsc[i0:i1 + 1].max() > .01 or dop[i0:i1 + 1].max() > .2:
                        a['flags'].append('short')
                    else:
                        steps += 1          # isolated <=1.5 px hop after rest: integer-placement stair, not a move
                if n >= 6 and v.mean() >= L['linear_min_px'] and v.std() / max(v.mean(), 1e-6) < L['linear_cv']:
                    a['flags'].append('linear')
                vmax = float(v.max())
                ext = np.concatenate([[0.], v, [0.]])            # from rest and back to rest
                for j in range(1, len(ext)):
                    jump = abs(ext[j] - ext[j - 1])
                    fade_hidden = (j == 1 and op[i0] < .6) or (j == len(ext) - 1 and op[min(i1 + 1, len(op) - 1)] < .6)
                    if jump > max(L['jump_px'], L['jump_rel'] * vmax) and not fade_hidden and not edge:
                        a['flags'].append('velocity_jump')
                        break
                slow = v < L['drift_max_px']
                if n >= 8 and slow.sum() >= 8 and v[slow].sum() > 1:
                    # only consecutive slow deltas: entrance/exit acceleration is not jitter
                    d2 = np.abs(np.diff(x[i0:i1 + 2], 2)) + np.abs(np.diff(y[i0:i1 + 2], 2))
                    both = slow[:-1] & slow[1:]
                    if both.sum() >= 6:
                        a['drift_jitter'] = round(float(d2[both].mean()), 3)
                        jitters.append(a['drift_jitter'])
                vec = (float(x[i1 + 1] - x[i0]), float(y[i1 + 1] - y[i0]))
                if key[0] == 'captions' and math.hypot(*vec) > 2:
                    (exits if op[i1 + 1] < op[i0] - .3 else entries).append((f0, f1, vec, '/'.join(key)))
                anims.append(a)
                flags += [{'flag': fl, 'track': a['track'], 'frame': f0} for fl in a['flags']]
    for f0, track in cue_onset.values():        # a caption (cue) onset, not each later word reveal
        if any(c - 1 <= f0 < c + offset_frames for c in cut_f):
            flags.append({'flag': 'caption_on_cut', 'track': track, 'frame': f0})
    for f, keys in sorted(starts.items()):
        if len(keys) >= L['at_once']:
            flags.append({'flag': 'all_at_once', 'frame': f, 'count': len(keys)})
    for c in cut_f:
        out = [e for e in exits if abs(e[1] - c) <= 2]
        inn = [e for e in entries if 0 <= e[0] - c <= 4]
        for e in out:
            for g in inn:
                dot = e[2][0] * g[2][0] + e[2][1] * g[2][1]
                if dot < 0:
                    flags.append({'flag': 'direction_mismatch', 'frame': c, 'exit': e[3], 'enter': g[3]})
    counts = {}
    for fl in flags:
        counts[fl['flag']] = counts.get(fl['flag'], 0) + 1
    summary = {'animations': len(anims), 'flags': sum(counts.values()), 'by_flag': counts,
               'drift_jitter_px': round(float(np.mean(jitters)), 3) if jitters else None, 'pixel_steps': steps,
               'tracks': len(tracks)}
    return {'summary': summary, 'flags': flags, 'animations': anims, 'fps': fps, 'cuts': list(cuts or ()),
            'limits': dict(L, offset_frames=offset_frames)}


def lint_curves(rows, report, out_dir, k=1.0, max_tracks=8):
    """One PNG per layer: x, y, width (scale), opacity per frame; red ticks = flagged frames."""
    import cv2
    from collections import defaultdict
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    layers = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        layers[r[1]][r[2]].setdefault(r[0], r)
    moving = {a['track'] for a in report['animations']}
    flagged = defaultdict(set)
    for fl in report['flags']:
        if 'track' in fl:
            flagged[fl['track'].split('/')[0]].add(fl['frame'])
    colours = [(66, 135, 245), (245, 166, 35), (80, 200, 120), (220, 80, 200), (60, 200, 220), (240, 220, 60),
               (160, 120, 255), (255, 120, 120)]
    written = []
    for li, (layer, tracks) in enumerate(sorted(layers.items())):
        names = [t for t in tracks if f'{layer}/{t}' in moving][:max_tracks]
        if not names:
            continue
        frames_all = sorted({f for t in names for f in tracks[t]})
        f0, f1 = frames_all[0], max(frames_all[-1], frames_all[0] + 1)
        W, ph, pad = 960, 150, 40
        img = np.full((pad + 4 * (ph + 28), W, 3), 24, np.uint8)
        cv2.putText(img, f'{layer}  frames {f0}-{f1}', (10, 26), cv2.FONT_HERSHEY_SIMPLEX, .6, (230, 230, 230), 1, cv2.LINE_AA)
        for pi, (label, col) in enumerate((('x px', 3), ('y px', 4), ('width px', 5), ('opacity', 8))):
            top = pad + pi * (ph + 28)
            cv2.putText(img, label, (10, top + 14), cv2.FONT_HERSHEY_SIMPLEX, .45, (180, 180, 180), 1, cv2.LINE_AA)
            vals = [tracks[t][f][col] / (1 if col == 8 else k) for t in names for f in tracks[t]]
            vmin, vmax = min(vals), max(vals)
            span = max(vmax - vmin, 1e-6 if col == 8 else 1.0)
            cv2.rectangle(img, (60, top + 20), (W - 10, top + 20 + ph), (60, 60, 60), 1)
            for f in flagged.get(layer, ()):
                if f0 <= f <= f1:
                    xx = int(60 + (f - f0) / (f1 - f0) * (W - 70))
                    cv2.line(img, (xx, top + 20), (xx, top + 20 + ph), (230, 60, 60), 1)
            for ti, t in enumerate(names):
                pts = [(int(60 + (f - f0) / (f1 - f0) * (W - 70)),
                        int(top + 20 + ph - (tracks[t][f][col] / (1 if col == 8 else k) - vmin) / span * ph))
                       for f in sorted(tracks[t])]
                cv2.polylines(img, [np.int32(pts)], False, colours[ti % len(colours)][::-1], 1, cv2.LINE_AA)
            cv2.putText(img, f'{vmin:.1f}..{vmax:.1f}', (W - 160, top + 14), cv2.FONT_HERSHEY_SIMPLEX, .4, (160, 160, 160), 1)
        path = out_dir / f'curves_{li:02d}_{C.slugify(layer)}.png'
        cv2.imwrite(str(path), img)
        written.append(str(path))
    return written


def slowmo(video, at, out_dir, fps=None, before=3, after=8, speed=.25):
    """Per animation start: a 25% speed clip (each frame held 4x, no interpolation) + 12-frame strip."""
    video = C.need_file(video, 'Video')
    meta = C.ffprobe_info(video)
    fps = float(fps or meta.get('fps') or 30)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for f in at:
        f = int(f)
        lo, hi = max(0, f - before), f + after + 1
        times = [(i + .5) / fps for i in range(lo, hi) if (i + .5) / fps < meta['duration']]
        strip = out_dir / f'strip_f{f:05d}.jpg'
        visual_sheet([video], times, strip, height=320)
        clip = C.guard_output(out_dir / f'slow_f{f:05d}.mp4', video)
        C.run([C.need_tool('ffmpeg'), '-hide_banner', '-nostdin', '-v', 'error', '-y', '-ss', f'{lo / fps:.4f}',
               '-t', f'{(hi - lo) / fps:.4f}', '-i', str(video), '-an', '-vf',
               f'setpts={1 / speed:g}*PTS,fps={fps:g},scale=-2:960', '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast',
               str(clip)])
        made.append({'frame': f, 'strip': str(strip), 'clip': str(clip), 'speed': speed})
    return made


def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='cmd',required=True)
    for name in ('filmstrip','ab'):
        p=sub.add_parser(name); p.add_argument('video')
        if name=='ab': p.add_argument('after')
        p.add_argument('--start',type=float,default=0); p.add_argument('--end',type=float,required=True)
        p.add_argument('--n',type=int,default=12); p.add_argument('--at'); p.add_argument('--height',type=int,default=320)
        p.add_argument('-o','--output',required=True)
    p=sub.add_parser('audio'); p.add_argument('video'); p.add_argument('-o','--output',required=True)
    p.add_argument('--events',required=True,help='audio_cues.json from compose')
    p=sub.add_parser('lint',help='trace every animation of a compose job (no encode) -> flags + curve PNGs')
    p.add_argument('video'); p.add_argument('--style'); p.add_argument('--brand'); p.add_argument('--subs')
    p.add_argument('--words'); p.add_argument('--elements'); p.add_argument('--cuts')
    p.add_argument('--start',type=float,default=0); p.add_argument('--end',type=float,required=True)
    p.add_argument('-o','--output',required=True,help='report folder')
    p=sub.add_parser('slowmo',help='25%% speed clip + 12-frame strip around animation starts')
    p.add_argument('video'); p.add_argument('--frames',help='comma frame numbers'); p.add_argument('--lint',help='motion_lint.json')
    p.add_argument('--max',type=int,default=6); p.add_argument('-o','--output',required=True)
    a=ap.parse_args()
    if a.cmd=='lint':
        import compose
        style=C.load_style(a.style,a.brand)
        words=C.read_json(a.words).get('words') if a.words else None
        res=compose.compose(C.need_file(a.video,'Video'),None,style,C.need_file(a.subs,'SRT') if a.subs else None,words,
                            C.read_json(a.cuts) if a.cuts else None,C.need_file(a.elements,'elements') if a.elements else None,
                            trace=(a.start,a.end))
        rng=[int(round(res['range'][0]*res['fps'])),int(round(res['range'][1]*res['fps']))]
        mc=__import__('motion_language').config(style)
        rep=lint_rows(res['rows'],res['fps'],res['k'],res['cuts'],mc['cuts']['offset_frames'],rng)
        rep['curves']=lint_curves(res['rows'],rep,a.output,res['k'])
        C.write_json(rep,Path(a.output)/'motion_lint.json'); C.write_json(res,Path(a.output)/'trace_rows.json')
        C.info(json.dumps(rep['summary'],ensure_ascii=False))
        C.info(f'REVIEW READY: {a.output}'); return
    if a.cmd=='slowmo':
        if a.frames: at=[int(x) for x in a.frames.split(',') if x.strip()]
        elif a.lint:
            rep=C.read_json(a.lint); seen=[]
            for an in sorted(rep['animations'],key=lambda r:(not r['flags'],r['start'])):
                if all(abs(an['start']-f)>6 for f in seen): seen.append(an['start'])
            at=sorted(seen[:a.max])
        else: raise C.MontajError('slowmo: --frames yoki --lint kerak.')
        made=slowmo(a.video,at,a.output); C.write_json(made,Path(a.output)/'slowmo.json')
        C.info(f'REVIEW READY: {a.output} ({len(made)} strip)'); return
    if a.cmd=='audio':
        video=C.need_file(a.video,'Video')
        out=C.guard_output(a.output,video); wav=C.guard_output(out.with_suffix('.wav'),video)
        C.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y','-i',a.video,'-vn','-c:a','pcm_s16le',str(wav)])
        report=C.read_json(a.events); waveform(wav,report['events'],out)
    else:
        dur=C.ffprobe_info(a.video)['duration']
        ts=[float(x) for x in a.at.split(',')] if a.at else timepoints(a.start,a.end,a.n,dur)
        visual_sheet([a.video,a.after] if a.cmd=='ab' else [a.video],ts,a.output,a.height)
    C.info(f'REVIEW READY: {a.output}')

if __name__=='__main__': C.run_main(main)
