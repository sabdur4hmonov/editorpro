"""Measurements after Remotion delivery encode, including transition sheets every third frame."""
from __future__ import annotations
import json, math
from pathlib import Path
import common as C

def face_rect_cover(face,boxes):
    """Conservative occupied DOM rectangles; includes transparent glyph-box space."""
    x0,y0,x1,y1=face;area=max(1,(x1-x0)*(y1-y0))
    return min(1,sum(max(0,min(x1,b['x']+b['w'])-max(x0,b['x']))*
                     max(0,min(y1,b['y']+b['h'])-max(y0,b['y'])) for b in boxes)/area)

def face_checks(props,traces,public,style):
    import cv2,face_safety
    from types import SimpleNamespace
    mon=face_safety.FaceMonitor(SimpleNamespace(W=props['width'],H=props['height'],fps=props['fps']),[],style)
    cap=cv2.VideoCapture(str(Path(public)/props['video']));last=None;checked=faces=0;maximum=0;violations=[]
    excluded={e['id'] for e in props['elements'] if e['type'] in ('broll','scene','remotion_scene')}
    unknown=any(e['type']=='remotion_scene' for e in props['elements'])
    for row in sorted({r['frame']:r for r in traces}.values(),key=lambda r:r['frame']):
        ok,frame=cap.read()
        if ok:last=frame
        if last is None:break
        boxes=[b for b in row['boxes'] if b['opacity']>=.01 and b['id'] not in excluded]
        if not boxes or row['frame']>=props['videoFrames']:continue
        # A fully opaque full-frame replacement intentionally removes the speaker.
        if any(e['type']=='broll' and e.get('mode','full')=='full' and e['startFrame']+props['motion']['enterFrames']<=row['frame']<e['endFrame'] for e in props['elements']):continue
        checked+=1
        if mon.det is None:continue
        face=mon._face(last[...,::-1])
        if face is None:continue
        faces+=1
        for face in [face]+mon.extra_boxes:
            covered=face_rect_cover(face,boxes);maximum=max(maximum,covered)
            if covered>mon.limit:violations.append(dict(frame=row['frame'],at=row['frame']/props['fps'],cover=covered))
    cap.release()
    verification='unverified_custom_scene' if unknown else 'measured' if mon.det is not None and faces else 'unverified_no_face'
    return dict(method='Per active frame: YuNet on normalized speaker, expanded face box vs actual visible DOM rectangles. Conservative upper bound; NOT native changed-pixel coverage. Full opaque b-roll intentionally replaces speaker.',
                verification=verification,detector_available=mon.det is not None,frames_checked=checked,frames_with_face=faces,
                max_cover=maximum,limit=mon.limit,violations=violations,ok=verification=='measured' and not violations)

def output_checks(video,props,folder,cuts=None):
    import quality_gate as Q
    folder=Path(folder);fps=props['fps'];meta=C.ffprobe_info(video)
    holds=Q.output_holds(video,fps)
    warnings=[f'Possible duplicate/hold @ {i/fps:.3f}s' for i in holds]
    pts=C.run([C.need_tool('ffprobe'),'-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time',
               '-of','json',video],check=True)
    stamps=[float(f['best_effort_timestamp_time']) for f in json.loads(pts.stdout)['frames'] if 'best_effort_timestamp_time' in f]
    gaps=[(i,round(b-a,6)) for i,(a,b) in enumerate(zip(stamps,stamps[1:])) if abs((b-a)-1/fps)>1/fps*.2]
    if gaps:warnings.append(f'Irregular frame spacing: {gaps[:10]}')
    if len(stamps)!=props['durationInFrames']:warnings.append(f'Frame count {len(stamps)} expected {props["durationInFrames"]}')
    audio_dur=C.run([C.need_tool('ffprobe'),'-v','error','-select_streams','a:0','-show_entries','stream=duration,start_time',
                     '-of','json',video],check=True)
    a=json.loads(audio_dur.stdout)['streams'];drift=abs(float(a[0].get('duration',meta['duration']))-len(stamps)/fps) if a else None
    if drift is None or drift>.05:warnings.append(f'Audio duration drift: {drift}')
    # Actual final AAC, not the intermediate WAV.
    wav=folder/'qa_audio.wav'
    C.run([C.need_tool('ffmpeg'),'-v','error','-y','-i',video,'-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',wav],check=True)
    audio=Q.cut_audio_rows(wav,Q.editorial_cut_times(cuts) or []) if cuts else []
    wav.unlink(missing_ok=True)
    for r in audio:
        if r.get('hole_db') is not None and r['hole_db'] < -6: warnings.append(f'Cut audio hole: {r}')
    # Every third frame in the active entrance/exit, capped to 12 panels per contact sheet.
    events=sorted(set([c['startFrame'] for c in props['captions']]+[e['startFrame'] for e in props['elements']]))
    sheets=[]
    for i,event in enumerate(events):
        start=max(0,event-3);end=min(props['durationInFrames']-1,event+max(props['motion']['enterFrames'],props['motion']['exitFrames'])+3)
        frames=list(range(start,end+1,3));express='+'.join(f'eq(n,{f})' for f in frames)
        dest=folder/f'transition_{i:03d}_{event/fps:.3f}s.jpg'
        C.run([C.need_tool('ffmpeg'),'-v','error','-y','-i',video,'-an','-vf',
               f"select='{express}',scale=216:-2,tile=6x2:padding=3",
               '-frames:v','1',dest],check=True)
        from PIL import Image,ImageDraw,ImageFont
        with Image.open(dest) as sheet:
            draw=ImageDraw.Draw(sheet);font=ImageFont.truetype(str(C.ROOT/'style/fonts/Inter.ttf'),14)
            tile_h=round(props['height']*216/props['width'])+3
            for j,frame in enumerate(frames[:12]):
                x=(j%6)*219+5;y=(j//6)*tile_h+5
                draw.rectangle((x-2,y-2,x+105,y+18),fill='black');draw.text((x,y),f'{frame/fps:.3f}s / f{frame}',font=font,fill='white')
            sheet.save(dest)
        sheets.append(str(dest))
    return dict(warnings=warnings,holds=holds,pts_count=len(stamps),frame_gaps=gaps,audio_drift_s=drift,cut_audio=audio,
                transition_sheets=sheets,measurements='Rendered upper-band MAD hold proxy; frame PTS; decoded final AAC; browser DOM geometry separately')

def markdown(qa):
    output=qa.get('output',{});warnings=output.get('warnings',[])
    rows=['# Remotion QA','',f"DOM: {qa['measured_frames']} frames, {qa['rectangles']} rectangles; errors {len(qa['errors'])}.",
          f"Output: {output.get('pts_count')} frames; PTS gaps {len(output.get('frame_gaps',[]))}; audio drift {output.get('audio_drift_s')} s.",
          f"FPS conversion: {qa.get('fps_conversion')}; intermediate ProRes4444, final delivery x264/AAC once.",
          f"Cache hits: {sum(s['hit'] for s in qa.get('segments',[]))}/{len(qa.get('segments',[]))}.",'',
          '## Warnings','']+(['- '+w for w in warnings] or ['- None in measured checks.'])
    rows+=['','## What is measured','',output.get('measurements',''),'','Word onset tolerance <=1 frame; static hold movement <=.35px/frame. Entrance/exit velocity is intentional. Bounding boxes are measured in the browser after local fonts load, not assumed from configuration.','',
           '## Human review still required','']+['- '+s for s in qa['unverified']]
    rows+=['','## Filmstrips','']+['- ['+Path(p).name+']('+str(Path(p).resolve()).replace('\\','/')+')' for p in output.get('transition_sheets',[])]
    rows+=['','## Attempts','',json.dumps(qa.get('attempts',[]),ensure_ascii=False)]
    return '\n'.join(rows)+'\n'
