"""Opt-in frame-accurate engine. Cutting, transcription, approval and audio stay in Python.

Unsupported legacy elements fail explicitly: never silently drop an approved graphic.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, re, shutil, subprocess, time
from pathlib import Path
import common as C

DEFAULTS=dict(fps=30,concurrency=2,preset='soft',enter_sec=.32,exit_sec=.28,distance_px=36,
              segment_sec=4,supersample=1,fps_conversion='blend',blur=dict(enabled=False,intensity=2),
              backing='#162128E8',animation_cycle=['slide','wipe','pop'],qa_attempts=3,cache_max_gb=2)
SUPPORTED={'title','text','callout','lower_third','image','broll','scene','list','panel','stat','follow','label','remotion_scene','sfx'}

def settings(style):
    cfg=C.deep_merge(DEFAULTS,style.get('remotion',{}))
    durations={'soft':(.32,.28),'snappy':(.22,.20),'bouncy':(.40,.26)}
    if cfg['preset'] in durations:
        for key,value in zip(('enter_sec','exit_sec'),durations[cfg['preset']]):
            if key not in style.get('remotion',{}): cfg[key]=value
    if cfg['fps'] not in (30,60): raise C.MontajError('remotion.fps: 30 or 60')
    if cfg['concurrency'] not in (2,3): raise C.MontajError('remotion.concurrency: 2 or 3')
    if cfg['preset'] not in ('snappy','soft','bouncy'): raise C.MontajError('remotion.preset: snappy / soft / bouncy')
    if cfg['fps_conversion'] not in ('blend','mci','reject'): raise C.MontajError('fps_conversion: blend / mci / reject')
    for key in ('enter_sec','exit_sec'):
        if not .2<=float(cfg[key])<=.5: raise C.MontajError(f'remotion.{key}: .2 .. .5 seconds')
    if cfg['supersample'] not in (1,2): raise C.MontajError('supersample: 1 or 2')
    if not 1<=int(cfg['qa_attempts'])<=3: raise C.MontajError('qa_attempts: 1..3')
    if not 1<=float(cfg['segment_sec'])<=10: raise C.MontajError('segment_sec: 1..10')
    if not 0<=float(cfg['blur']['intensity'])<=4: raise C.MontajError('blur.intensity: 0..4 px')
    if not .1<=float(cfg['cache_max_gb'])<=10: raise C.MontajError('cache_max_gb: .1..10')
    if not cfg['animation_cycle'] or any(a not in ('slide','wipe','pop','highlight') for a in cfg['animation_cycle']):
        raise C.MontajError('animation_cycle: slide, wipe, pop, highlight')
    return cfg

def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def exact_audio(wav,total,work,style):
    """Post-normalization duration repair; no retiming or changes to existing samples."""
    import audio_mix
    actual=C.ffprobe_info(wav)['duration']
    if abs(actual-total)<1/48000:return wav
    dest=Path(work)/'exact_audio.wav'
    C.info(f'AUDIO duration repair: {actual:.6f}s -> {total:.6f}s (post-filter padding/trim, no time stretch)')
    C.run([C.need_tool('ffmpeg'),'-v','error','-y','-i',wav,'-af',
           f'apad=whole_dur={total:.9f},atrim=duration={total:.9f},asetpts=PTS-STARTPTS',
           '-c:a','pcm_s16le',dest],check=True)
    if style.get('audio',{}).get('room_tone'):audio_mix.fill_room_tone(dest)
    return dest

def prune_cache(enginework,active,limit):
    """Bound our visual cache, never delete another video's temp files."""
    root=Path(enginework).resolve();folder=root/'segments'
    if not C.is_inside(root,C.TEMP_DIR):raise C.MontajError('Cache cleanup must stay in temp')
    protected={Path(p).resolve() for p in active};files=list(folder.glob('*.mov'))
    size=sum(p.stat().st_size for p in files);removed=0
    for p in sorted(files,key=lambda p:p.stat().st_mtime):
        if size<=limit:break
        if p.resolve() in protected:continue
        size-=p.stat().st_size;p.unlink();p.with_suffix('.trace.json').unlink(missing_ok=True);removed+=1
    if size>limit:C.warn('Active visual segments exceed cache budget; retained for this delivery')
    return dict(bytes=size,removed=removed,limit_bytes=limit)

def asset(path,work,brand=None):
    path=Path(path)
    if not path.is_absolute():
        path=next((root/path for root in (brand,C.ROOT) if root and (root/path).is_file()),C.ROOT/path)
    C.need_file(path,'Remotion asset')
    key=digest(path); folder=Path(work)/'remotion/public/assets'
    dest=folder/(key+path.suffix.lower()); folder.mkdir(parents=True,exist_ok=True)
    if not dest.is_file(): shutil.copyfile(path,dest)
    return dest.relative_to(Path(work)/'remotion/public').as_posix()

def clean_word(text):
    return re.sub(r'[^\w]+','',C.strip_markup(text).lower().replace('‘',"'").replace('ʻ',"'").replace('’',"'"))

def caption_plan(cues,words,style,W,H,fps,cfg):
    """Use approved spelling with source word starts; reserve the whole phrase before first reveal."""
    import motion as M, elements as E
    fonts=M.Fonts([C.brand_dir(style)/'fonts' if C.brand_dir(style) else C.ROOT/'style/fonts',C.ROOT/'style/fonts'])
    cap=style.get('captions',{}); family=cap.get('font','Inter'); size=float(cap.get('size_main',74))*H/1920
    safe=style['platform']['safe']; maxw=W*(1-safe['left']-safe['right'])-2*cfg['distance_px']*W/1080
    result=[]
    for ci,c in enumerate(cues):
        tokens=E.parse_markup(re.sub(r'^\{[^}]+\}\s*','',c['text']))
        available=[(i,w) for i,w in enumerate(words or []) if float(w['start'])<c['end']+.04 and float(w['end'])>c['start']-.04]
        cursor=0; aligned=[]
        for text,level,newline in tokens:
            norm=clean_word(text)
            if not norm: continue
            match=next((j for j in range(cursor,len(available)) if clean_word(available[j][1]['word'])==norm),None)
            if match is None: raise C.MontajError(f'Remotion word alignment: {text!r} @ {c["start"]:.2f}s; correct approved JSON/SRT, no guessed timing')
            source=available[match][1];cursor=match+1
            aligned.append(dict(id=f'c{ci}w{len(aligned)}',text=text,frame=math.ceil(float(source['start'])*fps-1e-7),
                                startMs=float(source['start'])*1000,endMs=float(source['end'])*1000,
                                timestampMs=None,confidence=source.get('probability'),
                                emphasis=level in ('accent','big_accent','huge','mark','mark2'),box=level in ('mark','mark2'),
                                weight=700,size=size*(1.25 if level!='normal' else 1),width=0))
        if not aligned: continue
        # Fixed line breaking with accurate font advances (including Uzbek fallback characters).
        lines=[]; line=[]; advance=0
        for word in aligned:
            font=fonts.get(family,word['size'],700);width=font.getlength(word['text']+' ')+(16*W/1080 if word['box'] else 0)
            if width>maxw: raise C.MontajError(f'Single word too wide for safe area: {word["text"]}')
            if line and advance+width>maxw: lines.append((line,advance)); line=[];advance=0
            word['width']=width;line.append(word);advance+=width
        if line: lines.append((line,advance))
        if len(lines)>3: raise C.MontajError(f'Caption {ci}: >3 lines; split approved SRT without changing words')
        line_height=max(w['size'] for w in aligned)*1.2
        y=cap.get('position_y',.64)*H-len(lines)*line_height/2
        for li,(line,width) in enumerate(lines):
            x=(safe['left']*W+(1-safe['right'])*W-width)/2
            for word in line: word.update(x=x,y=y+li*line_height);x+=word['width']
        result.append(dict(id=f'c{ci}',startFrame=min(w['frame'] for w in aligned),
                           endFrame=math.ceil(c['end']*fps),animation=cfg['animation_cycle'][ci%len(cfg['animation_cycle'])],words=aligned))
    return result,fonts,family

def elements_plan(elements,style,work,W,H,fps,cfg):
    planned=[]
    for i,el in enumerate(elements):
        typ=el['type']
        if typ not in SUPPORTED: raise C.MontajError(f'Remotion does not support legacy element {typ!r}; use native motion or an explicit remotion_scene')
        if typ=='sfx': continue
        out=dict(el,id=f'e{i}',startFrame=math.ceil(el['start']*fps),endFrame=math.ceil(el['end']*fps),
                 x=float(el.get('x',(style['platform']['safe']['left']+1-style['platform']['safe']['right'])/2)),y=float(el.get('y',.32)),width=float(el.get('width',.65)))
        if typ=='lower_third': out.update(type='text',text=el['name']+'\n'+el.get('role',''),backing=True)
        if typ=='label': raise C.MontajError('Animated label item switching needs explicit remotion_scene; not silently flattened')
        if typ in ('callout','title','text'): out['text']=C.strip_markup(el.get('text',''));out['backing']=typ=='callout'
        if typ in ('image','broll'):
            media=el['file']
            if typ=='broll' and Path(media).suffix.lower() in ('.mp4','.mov','.webm','.mkv'):
                source=Path(media)
                if not source.is_absolute():source=next((r/source for r in (C.brand_dir(style),C.ROOT) if r and (r/source).is_file()),C.ROOT/source)
                C.need_file(source,'B-roll')
                key=hashlib.sha256(f'{digest(source)}:{W}:{H}:{fps}:{cfg["fps_conversion"]}'.encode()).hexdigest()
                media=Path(work)/'remotion'/('broll_'+key+'.mp4')
                if not media.exists():normalize_media(source,media,W,H,fps,cfg['fps_conversion'])
            out['file']=asset(media,work,C.brand_dir(style));out['offsetFrames']=round(el.get('offset',0)*fps)
        if typ in ('panel','list'):
            out['items']=[dict(it,frame=math.ceil(it.get('at',el['start']+j*.15)*fps))
                          if isinstance(it,dict) else dict(text=it,frame=math.ceil((el['start']+j*.15)*fps))
                          for j,it in enumerate(el.get('items',el.get('lines',[])))]
        if typ=='follow': out['tapFrame']=math.ceil(float(el.get('tap',el['start']+1))*fps)
        if typ=='remotion_scene':
            def relink(obj):
                if isinstance(obj,dict): return {k:asset(v,work,C.brand_dir(style)) if k in ('file','image','video') and v else relink(v) for k,v in obj.items()}
                if isinstance(obj,list): return [relink(v) for v in obj]
                return obj
            out['scene']=relink(el['scene']);out['scene'].setdefault('duration',out['endFrame']-out['startFrame'])
        planned.append(out)
    return planned

def normalize_media(video,dest,W,H,fps,mode):
    src=C.ffprobe_info(video)
    mismatch=abs(src['fps']-fps)>.01
    if mismatch and mode=='reject': raise C.MontajError(f'Source {src["fps"]} -> {fps} needs interpolation; fps_conversion reject')
    vf=f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1'
    if mismatch:
        vf+=f',minterpolate=fps={fps}:mi_mode={mode}'
        C.warn(f'FPS {src["fps"]:g}->{fps}; {mode} interpolation. Blend may ghost; MCI may warp. Human review required.')
    C.run([C.need_tool('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',video,'-an','-vf',vf,
           '-c:v','libx264','-crf','0','-preset','ultrafast','-pix_fmt','yuv420p','-threads','2',dest],check=True)
    return src

def dom_qa(props,traces):
    """Actual browser rectangles/opacity. Hold drift differs from intentional entrance velocity."""
    safe=props['safe'];W,H=props['width'],props['height'];bounds=(safe['left']*W,safe['top']*H,(1-safe['right'])*W,(1-safe['bottom'])*H)
    rows={};errors=[];warnings=[];velocities={}
    unique={int(t['frame']):t for t in traces}
    missing=sorted(set(range(props['durationInFrames']))-set(unique))
    if missing: errors.append(dict(kind='trace_missing',frames=missing[:10]))
    for frame,t in sorted(unique.items()):
        for b in t['boxes']:
            if not all(isinstance(b.get(k),(int,float)) and math.isfinite(b[k]) for k in ('x','y','w','h','opacity')):
                errors.append(dict(kind='invalid_geometry',frame=frame,id=b.get('id')));continue
            if b['opacity']<.01: continue
            rows.setdefault(b['id'],[]).append(dict(b,frame=frame))
            if (b['role']=='caption' or b.get('safeRequired')) and (b['x']<bounds[0]-.5 or b['y']<bounds[1]-.5 or b['x']+b['w']>bounds[2]+.5 or b['y']+b['h']>bounds[3]+.5):
                errors.append(dict(kind='safe_area',frame=frame,id=b['id']))
    expected={w['id']:w['frame'] for c in props['captions'] for w in c['words']}
    for id,start in expected.items():
        actual=rows.get(id,[])
        if not actual or abs(actual[0]['frame']-start)>1: errors.append(dict(kind='caption_desync',id=id,expected=start,actual=actual[0]['frame'] if actual else None))
    for id,rr in rows.items():
        for a,b in zip(rr,rr[1:]):
            if b['frame']-a['frame']!=1: continue
            velocity=math.hypot(b['x']-a['x'],b['y']-a['y'])
            velocities.setdefault(id+':'+b['phase'],[]).append(velocity)
            if a['phase']==b['phase']=='hold' and velocity>.35: errors.append(dict(kind='hold_jitter',id=id,frame=b['frame'],px=velocity))
            if velocity>props['motion']['distance']*1.5: errors.append(dict(kind='position_jump',id=id,frame=b['frame'],px=velocity))
    return dict(errors=errors[:200],warnings=warnings,measured_frames=len(unique),rectangles=sum(len(t['boxes']) for t in unique.values()),
                velocity_px_per_frame={k:dict(mean=sum(v)/len(v),maximum=max(v),samples=len(v)) for k,v in velocities.items()},
                limits=dict(word_start_tolerance_frames=1,hold_drift_px=.35),
                unverified=['SFX taste / rhythm','semantic quality','optical interpolation artifacts','caption glyph visual quality'])

def compose(video,out,style,srt=None,words=None,cuts=None,elements_file=None,music=None,nvenc=None,
            stills=None,stills_out=None,draft=False,trace=None):
    import compose as native, audio_mix, energy_curve, motion_language as ML
    if trace: raise C.MontajError('Native blit trace unavailable in Remotion; use qa/report.md DOM trace')
    cfg=settings(style); source=C.ffprobe_info(video)
    work=video.parent if C.is_inside(video,C.TEMP_DIR) else C.job_dir(video)
    enginework=work/'remotion';enginework.mkdir(parents=True,exist_ok=True)
    public=enginework/'public';(public/'fonts').mkdir(parents=True,exist_ok=True)
    for fontfile in (C.ROOT/'style/fonts').glob('*.ttf'):
        target=public/'fonts'/fontfile.name
        if not target.exists():shutil.copyfile(fontfile,target)
    if shutil.disk_usage(enginework).free<30*1024**3: C.warn('DISK: less than 30 GiB free')
    cfg['distance_px']*=.5 if draft else 1
    style=C.deep_merge(style,{'video':{'fps':cfg['fps']}})
    if draft: style=native.draft_style(style)
    style=ML.setup_variety(ML.choose(style,work),work)
    W,H=style['video']['width'],style['video']['height'];fps=cfg['fps']
    cues=C.parse_srt(srt) if srt else [];elements=native.read_elements(elements_file)
    style,elements=energy_curve.prepare(video,words,cues,elements,style,work)
    shift=int(digest(video)[:8],16)%len(cfg['animation_cycle'])
    cfg['animation_cycle']=cfg['animation_cycle'][shift:]+cfg['animation_cycle'][:shift]
    caps,fonts,family=caption_plan(cues,words,style,W,H,fps,cfg)
    font=fonts.get(family,74,700);fallback=fonts.get('Oswald',74,700)
    local_fonts={family:asset(font.primary.path,work),'Oswald':asset(fallback.primary.path,work)}
    key=hashlib.sha256(json.dumps(dict(source=digest(video),W=W,H=H,fps=fps,mode=cfg['fps_conversion']),sort_keys=True).encode()).hexdigest()
    mediafile=enginework/(key+'.mp4')
    if not mediafile.is_file(): normalize_media(video,mediafile,W,H,fps,cfg['fps_conversion'])
    total=source['duration']+(style.get('endcard',{}).get('duration',2.2) if style.get('endcard',{}).get('enabled') else 0)
    planned=elements_plan(elements,style,work,W,H,fps,cfg)
    logo=style.get('logo',{})
    if logo.get('file'): planned+=elements_plan([dict(type='image',file=logo['file'],start=0,end=source['duration'],width=logo.get('width',.26),x=.5,y=.12)],style,work,W,H,fps,cfg)
    if total>source['duration']:
        ec=style['endcard'];planned+=elements_plan([dict(type='follow',start=source['duration'],end=total,name=ec.get('text',''),handle=ec.get('handle',''),button=ec.get('button',''),y=.5)],style,work,W,H,fps,cfg)
    preset={'soft':('easeOutCubic',24,120),'snappy':('easeOutExpo',20,180),'bouncy':('spring',16,150)}[cfg['preset']]
    motion=dict(curve=preset[0],damping=preset[1],stiffness=preset[2],seconds=cfg['enter_sec'],
                enterFrames=math.ceil(cfg['enter_sec']*fps),exitFrames=math.ceil(cfg['exit_sec']*fps),distance=cfg['distance_px'],
                blur=cfg['blur'],backing=cfg['backing'])
    transitions=[e for e in planned if e['type']=='broll']
    import quality_gate
    transitions += [dict(id=f'cut{i}',type='cut',startFrame=round(t*fps),endFrame=round(t*fps)+motion['enterFrames'])
                    for i,t in enumerate(quality_gate.editorial_cut_times(cuts) or []) if t>0]
    for caption in caps:
        link=next((e for e in transitions if e['type']=='broll' and e['startFrame']<=caption['startFrame']<e['endFrame']),None)
        if link:caption['transitionGroup']=link['id']
    props=dict(width=W,height=H,fps=fps,durationInFrames=round(total*fps),video=asset(mediafile,work),videoFrames=round(source['duration']*fps),
               font=family,fallback='Oswald',fonts=local_fonts,color=style.get('captions',{}).get('color','#FFFFFF'),
               accent=style.get('captions',{}).get('accent','#F4BE4F'),motion=motion,safe=style['platform']['safe'],
               captions=caps,elements=planned,transitions=transitions,trace=True)
    total=props['durationInFrames']/fps
    C.write_json(dict(engine='remotion',source_sha256=digest(video),preset=cfg['preset'],cycle=cfg['animation_cycle'],
                      captions=[dict(id=c['id'],animation=c['animation']) for c in caps]),enginework/'motion_choice.json')
    node=C.need_tool('node');browser=next((p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.is_file()),None)
    if not browser: raise C.MontajError('Installed Chrome/Edge missing; no browser downloaded automatically')
    job=dict(props=props,browser=str(browser),concurrency=cfg['concurrency'],scale=cfg['supersample'],cache=str(enginework/'segments'),publicDir=str(public),
             segmentFrames=round(cfg['segment_sec']*fps),result=str(enginework/'render-result.json'))
    def run_job():
        C.write_json(job,enginework/'job.json')
        logfile=enginework/'renderer.log'
        with logfile.open('w',encoding='utf-8') as log:
            proc=subprocess.run([node,'--max-old-space-size=1536',str(C.ROOT/'remotion/timeline-render.mjs'),str(enginework/'job.json')],cwd=C.ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        lines=logfile.read_text(encoding='utf-8',errors='replace').splitlines()
        for line in lines:
            if line.startswith('SEGMENT'):C.info(line)
        if proc.returncode:
            C.info('\n'.join(line for line in lines[-18:] if 'MOTION_QA:' not in line))
            raise C.MontajError(f'Remotion renderer failed ({proc.returncode}); log {logfile}; previous final retained')
        return C.read_json(enginework/'render-result.json')
    if stills:
        job['stillFrames']=[min(props['durationInFrames']-1,max(0,round(t*fps))) for t in stills];run_job()
        from PIL import Image,ImageDraw
        thumbs=[]
        for t,f in zip(stills,job['stillFrames']):
            im=Image.open(Path(job['cache'])/f'still_{f}.png').convert('RGB');im.thumbnail((270,480));ImageDraw.Draw(im).text((8,8),f'{t:.3f}s',fill='yellow');thumbs.append(im)
        sheet=Image.new('RGB',(270*min(4,len(thumbs)),480*math.ceil(len(thumbs)/4)))
        for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*270,(i//4)*480))
        dest=C.guard_output(stills_out or work/'stills.jpg');sheet.save(dest)
        return dict(stills=str(dest),count=len(stills),notes=[])
    out=C.guard_output(out,video);qa_dir=work/'qa'/out.stem;qa_dir.mkdir(parents=True,exist_ok=True)
    # Flush normalization/filter buffers beyond delivery end, then trim on the frame grid.
    # Applying output -t before these filters can leave the PCM ~50-80 ms short.
    mix_style=C.deep_merge(style,{'audio':{'room_tone':False}})
    wav=audio_mix.build_audio(video,enginework/'audio'/'final_audio.wav',mix_style,total+.15,music,native.gather_sfx(style,elements,cues,words),C.brand_dir(style))
    wav=exact_audio(wav,total,enginework,style)
    attempts=[];result=None
    for attempt in range(cfg['qa_attempts']):
        result=run_job();qa=dom_qa(props,result['traces']);attempts.append(dict(attempt=attempt+1,errors=qa['errors']))
        if not qa['errors']:break
        kinds={e['kind'] for e in qa['errors']}
        if kinds <= {'safe_area'} and attempt+1<cfg['qa_attempts']:
            C.warn(f'QA retry {attempt+2}: caption size -10%, fixed safe layout')
            adjusted=C.deep_merge(style,{'captions':{'size_main':float(style.get('captions',{}).get('size_main',74))*.9}})
            props['captions']=caption_plan(cues,words,adjusted,W,H,fps,cfg)[0];style=adjusted
        elif attempt+1<cfg['qa_attempts']:
            C.warn('QA cannot safely infer repair for '+','.join(sorted(kinds)));break
    C.write_json(dict(qa,attempts=attempts),qa_dir/'report.json')
    if qa['errors']:
        (qa_dir/'report.md').write_text('# QA FAILED\n'+json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
        raise C.MontajError(f'Remotion QA failed; report {qa_dir}; previous final retained')
    concat=enginework/'concat.txt'
    concat.write_text('\n'.join("file '"+str(Path(p).resolve()).replace('\\','/').replace("'","'\\''")+"'" for p in result['segments']),encoding='utf-8')
    staging=enginework/'delivery.mp4'
    C.run([C.need_tool('ffmpeg'),'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',concat,'-i',wav,
           '-map','0:v:0','-map','1:a:0','-vf',f'scale={W}:{H}:flags=lanczos,format=yuv420p','-c:v','libx264',
           '-crf',str(23 if draft else max(16,min(18,int(style['video'].get('crf',17))))),'-preset','veryfast' if draft else 'slow',
           '-threads','2','-c:a','aac','-b:a','192k','-t',str(total),'-movflags','+faststart',staging],check=True)
    meta,problems=C.verify_video(staging,W,H,total,need_audio=True)
    if problems: raise C.MontajError('Remotion final verification: '+'; '.join(problems))
    import remotion_qa
    output_qa=remotion_qa.output_checks(staging,props,qa_dir,cuts)
    qa.update(output=output_qa,segments=result['report'],fps_conversion=cfg['fps_conversion'] if abs(source['fps']-fps)>.01 else 'native')
    qa['cache']=prune_cache(enginework,result['segments'],cfg['cache_max_gb']*1024**3)
    C.write_json(qa,qa_dir/'report.json');(qa_dir/'report.md').write_text(remotion_qa.markdown(qa),encoding='utf-8')
    shutil.copyfile(staging,out);staging.unlink();concat.unlink(missing_ok=True)
    meta=C.ffprobe_info(out);meta.update(notes=output_qa['warnings'],checks=native.check_export(out,style,meta),audio=dict(audio_mix.LAST_REPORT),qa=str(qa_dir/'report.md'),draft=draft)
    if style.get('sfx',{}).get('enabled') and style.get('sfx',{}).get('mixes'):
        import sound_design
        meta['mixes']=sound_design.alternate_mixes(video,out,work,style,total,elements,cues,words,music,C.brand_dir(style),dict(audio_mix.LAST_REPORT))
    for scratch in (enginework/'exact_audio.wav',enginework/'audio'/'final_audio.wav'):
        scratch.unlink(missing_ok=True)
    C.info(f"REMOTION QA: {qa['measured_frames']} frames, {len(qa['errors'])} errors; {len(output_qa['warnings'])} output warnings")
    return meta

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('video');ap.add_argument('--subs');ap.add_argument('--words');ap.add_argument('--elements');ap.add_argument('--brand');ap.add_argument('--style');ap.add_argument('--draft',action='store_true');ap.add_argument('--approved',action='store_true');ap.add_argument('-o','--output',required=True)
    args=ap.parse_args()
    if args.subs and not args.approved: raise C.MontajError('Show subtitle text and save user approval before --approved')
    video=C.need_file(args.video,'Video');C.busy_acquire(f'Remotion {video.name}')
    compose(video,Path(args.output),C.load_style(args.style,args.brand),Path(args.subs) if args.subs else None,C.read_json(args.words)['words'] if args.words else None,elements_file=Path(args.elements) if args.elements else None,draft=args.draft)
if __name__=='__main__':C.run_main(main)
