"""Motion/audio evidence: filmstrip, aligned A/B, measured event stems and waveform."""
from __future__ import annotations
import argparse
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
    a=ap.parse_args()
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
