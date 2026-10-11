"""Native FCP 7 XML + source cut list + editable SRT + ProRes alpha + audio stems.

Raster base preserves grade/zoom/context-dependent effects; source_cuts.xml is editable
source assembly. No claim of having tested an editor's GUI import is made here.
"""
from pathlib import Path
import argparse, copy, math, shutil, subprocess, xml.etree.ElementTree as ET
import numpy as np
import common as C
import compose as CP
import elements as E
from energy_curve import plain

def timecode(frame,fps):
    if fps!=int(fps) or fps<=0: raise C.MontajError('Only integer non-drop-frame timecode supported')
    fps=int(fps); seconds,ff=divmod(int(frame),fps); minutes,ss=divmod(seconds,60); hh,mm=divmod(minutes,60)
    return f'{hh:02}:{mm:02}:{ss:02}:{ff:02}'

def source_offset(path,fps):
    proc=C.run([C.need_tool('ffprobe'),'-v','error','-show_entries',
               'format_tags=timecode:stream_tags=timecode','-of','json',str(path)])
    import json,re
    data=json.loads(proc.stdout); tags=[data.get('format',{}).get('tags',{})]+[s.get('tags',{}) for s in data.get('streams',[])]
    tc=next((d['timecode'] for d in tags if d.get('timecode')),None)
    if not tc: return 0,'file-relative 00:00:00:00; embedded camera timecode absent'
    if not re.fullmatch(r'\d{2}:\d{2}:\d{2}:\d{2}',tc): raise C.MontajError('Drop-frame/unrecognised source timecode unsupported: '+tc)
    hh,mm,ss,ff=map(int,tc.split(':'))
    if mm>=60 or ss>=60 or ff>=fps: raise C.MontajError('Invalid embedded timecode: '+tc)
    return ((hh*60+mm)*60+ss)*int(fps)+ff,'embedded source timecode'

def cut_list(keep,fps,offset=0,speed=1):
    if speed!=1: raise C.MontajError('Editor export: speed != 1 needs a verified retime adapter')
    timecode(0,fps); result=[]; record=0; previous=-1
    for item in keep:
        a,b=(float(item['start']),float(item['end'])) if isinstance(item,dict) else map(float,item)
        if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b and a>=previous):
            raise C.MontajError('Cuts must be ordered non-overlapping positive ranges')
        ia,ib=round(a*fps),round(b*fps); length=ib-ia
        if length<=0: raise C.MontajError('Cut shorter than one frame')
        result.append(dict(source_in=ia,source_out=ib,record_in=record,record_out=record+length,
                           source_in_tc=timecode(offset+ia,fps),source_out_tc=timecode(offset+ib,fps)))
        record+=length; previous=b
    return result

def node(parent,name,value=None,**attrs):
    el=ET.SubElement(parent,name,{k:str(v) for k,v in attrs.items()})
    if value is not None: el.text=str(value)
    return el

def rate(parent,fps):
    r=node(parent,'rate'); node(r,'timebase',int(fps)); node(r,'ntsc','FALSE')

def write_xml(path,tracks,fps,width,height,total,name):
    """Fields from Apple's legacy xmeml Elements Catalog; no FCPX .fcpxml."""
    timecode(0,fps); root=ET.Element('xmeml',version='5'); seq=node(root,'sequence',id='sequence-1')
    node(seq,'name',name); node(seq,'duration',total); rate(seq,fps)
    media=node(seq,'media'); video=node(media,'video'); audio=node(media,'audio')
    fmt=node(node(video,'format'),'samplecharacteristics'); rate(fmt,fps)
    node(fmt,'width',width); node(fmt,'height',height); node(fmt,'pixelaspectratio','square'); node(fmt,'fielddominance','none')
    channels=node(node(audio,'format'),'samplecharacteristics'); node(channels,'depth',16); node(channels,'samplerate',48000)
    serial=0
    for track in tracks:
        tr=node(audio if track['kind']=='audio' else video,'track')
        for clip in track['clips']:
            serial+=1; file=Path(clip['file']).resolve(); info=C.ffprobe_info(file)
            item=node(tr,'clipitem',id=f'clip-{serial}'); node(item,'name',file.name)
            node(item,'duration',round(info['duration']*fps)); rate(item,fps)
            for key,value in [('start',clip['record_in']),('end',clip['record_out']),('in',clip['source_in']),('out',clip['source_out'])]: node(item,key,value)
            f=node(item,'file',id=f'file-{serial}'); node(f,'name',file.name); node(f,'pathurl',file.as_uri()); rate(f,fps)
            node(f,'duration',round(info['duration']*fps)); fm=node(f,'media')
            if track['kind']=='audio':
                sc=node(node(fm,'audio'),'samplecharacteristics'); node(sc,'depth',16); node(sc,'samplerate',info['sample_rate']); node(sc,'channelcount',info['channels'])
            else:
                sc=node(node(fm,'video'),'samplecharacteristics'); rate(sc,fps)
                node(sc,'width',info['width']); node(sc,'height',info['height']); node(sc,'pixelaspectratio','square'); node(sc,'fielddominance','none')
                tc=node(f,'timecode'); rate(tc,fps); node(tc,'frame',clip.get('timecode_offset',0)); node(tc,'displayformat','NDF')
                if clip.get('alpha'): node(item,'alphatype','straight')
            st=node(item,'sourcetrack'); node(st,'mediatype',track['kind']); node(st,'trackindex',clip.get('source_channel',1))
        node(tr,'enabled','TRUE'); node(tr,'locked','FALSE')
    ET.indent(root); C.guard_output(path); ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def read_xml(path):
    root=ET.parse(path).getroot()
    if root.tag!='xmeml' or root.attrib.get('version')!='5': raise C.MontajError('Not FCP 7 XML v5')
    tracks=[]
    for kind in ('video','audio'):
        for track in root.findall(f'./sequence/media/{kind}/track'):
            items=[]
            for el in track.findall('clipitem'):
                c={k:int(el.findtext(x)) for k,x in [('record_in','start'),('record_out','end'),('source_in','in'),('source_out','out')]}
                if c['record_out']<=c['record_in'] or c['source_out']<=c['source_in']: raise C.MontajError('Invalid XML clip range')
                c['pathurl']=el.findtext('file/pathurl'); items.append(c)
            tracks.append({'kind':kind,'clips':items})
    return tracks

def alpha_frame(layer,t,shape):
    black=np.zeros(shape,np.uint8); white=np.full(shape,255,np.uint8)
    layer.draw(black,t); layer.draw(white,t)
    opacity=np.clip(1-np.mean(white.astype(float)-black.astype(float),axis=2)/255,0,1)
    # Background-dependent filters cannot be reconstructed as a transparent overlay.
    if np.max(np.ptp(white.astype(float)-black.astype(float),axis=2))>4:
        raise C.MontajError('Layer depends on background; export it in the raster base')
    rgb=np.divide(black,opacity[:,:,None],out=np.zeros_like(black,dtype=float),where=opacity[:,:,None]>.001)
    return np.dstack((np.clip(rgb,0,255).astype(np.uint8),np.round(opacity*255).astype(np.uint8)))

def render_alpha(layer,path,start,end,style):
    w,h=style['video']['width'],style['video']['height']; fps=style['video']['fps']; count=round((end-start)*fps)
    C.guard_output(path); path.parent.mkdir(parents=True,exist_ok=True); log=path.with_suffix('.log')
    args=[C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','rgba',
          '-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','prores_ks','-profile:v','4',
          '-pix_fmt','yuva444p10le','-alpha_bits','16',str(path)]
    with log.open('wb') as err:
        proc=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=err)
        try:
            for i in range(count): proc.stdin.write(alpha_frame(layer,start+i/fps,(h,w,3)).tobytes())
            proc.stdin.close(); code=proc.wait(timeout=120)
        except BaseException:
            proc.kill(); proc.wait(); raise
    if code: raise C.MontajError('Alpha encode: '+log.read_text(errors='replace')[-500:])
    return {'file':str(path),'record_in':round(start*fps),'record_out':round(start*fps)+count,
            'source_in':0,'source_out':count,'alpha':True}

def validate(package):
    manifest=C.read_json(package/'manifest.json'); issues=[]
    for name in ('timeline.xml','source_cuts.xml'):
        tracks=read_xml(package/name)
        expected=manifest['timeline_tracks' if name=='timeline.xml' else 'source_tracks']
        if len(tracks)!=len(expected): issues.append(name+': track count mismatch')
        for a,b in zip(tracks,expected):
            if len(a['clips'])!=len(b['clips']): issues.append(name+': clip count mismatch')
            for x,y in zip(a['clips'],b['clips']):
                if any(x[k]!=y[k] for k in ('source_in','source_out','record_in','record_out')): issues.append(name+': range mismatch')
                if x['pathurl']!=Path(y['file']).resolve().as_uri(): issues.append(name+': file URL mismatch')
    cues=C.parse_srt(package/'captions.srt')
    if cues!=manifest['captions']: issues.append('SRT round-trip mismatch')
    for clip in manifest['graphics']:
        meta=C.ffprobe_info(clip['file'])
        if meta['vcodec']!='prores' or not meta.get('alpha'): issues.append('Graphics have no ProRes alpha: '+clip['file'])
        if abs(meta['duration']-(clip['source_out']/manifest['fps']))>1/manifest['fps']+.001: issues.append('Graphic duration mismatch')
    for name in ('speech','sfx','music'):
        meta=C.ffprobe_info(package/(name+'.wav'))
        if not meta['has_audio'] or abs(meta['duration']-manifest['duration'])>.1: issues.append(name+': invalid stem duration')
    if issues: raise C.MontajError('; '.join(issues))
    result={'ok':True,'parsed_xml':2,'captions':len(cues),'graphics':len(manifest['graphics']),
            'audio_stems':3,'gui_import':'UNVERIFIED: XML parsing is not an editor GUI test'}
    C.write_json(result,package/'validation.json'); return result

def conform_source(source,fps,work,end=None):
    """CFR working copy preserves source seconds; never relabel VFR as frame-accurate CFR."""
    original=C.ffprobe_info(source)
    if abs(original['fps']-fps)<=.0001:return source,None
    file=work/'source_conformed.mp4'
    required=min(original['duration'],float(end)) if end is not None else original['duration']
    C.info(f'EDITOR CFR: {original["fps"]} -> {fps} fps; 0..{required:.3f}s source copy')
    C.run([C.need_tool('ffmpeg'),'-hide_banner','-nostdin','-v','error','-y','-i',str(source),
           '-map','0:v:0','-t',str(required),'-vf',f'fps=fps={fps}:round=near','-an','-c:v','libx264','-crf','16','-preset','veryfast',str(file)])
    info=C.ffprobe_info(file)
    if abs(info['fps']-fps)>.0001 or abs(info['duration']-required)>2/fps:
        raise C.MontajError('CFR conform failed FPS/duration verification')
    note={'original_file':str(source),'original_average_fps':original['fps'],'working_file':str(file),
          'sequence_fps':fps,'method':'FFmpeg fps round=near; duplicate/drop to CFR; source seconds retained',
          'copied_source_seconds':[0,required],
          'max_time_grid_rounding_seconds':1/fps,'original_media_untouched':True}
    return file,note

def export(video,source,cuts,style,subs,words,elements,work):
    work=C.guard_output(work); work.mkdir(parents=True,exist_ok=True)
    style=C.resolve_fps(style,video); fps=style['video']['fps']; timecode(0,fps)
    offset,tc_note=source_offset(source,fps)
    listing=cut_list(cuts['keep'],fps,offset,cuts.get('speed',1))
    if not listing: raise C.MontajError('Editor export requires at least one source cut')
    native_cuts=dict(cuts,keep=[dict(start=c['source_in']/fps,end=c['source_out']/fps) for c in listing])
    working_source,conform=conform_source(source,fps,work,listing[-1]['source_out']/fps+1/fps)
    duration=C.ffprobe_info(video)['duration']; total=round(duration*fps)
    if abs(listing[-1]['record_out']-total)>1: raise C.MontajError('Cut list does not match supplied cut video duration')
    st=copy.deepcopy(style); st.setdefault('audio',{})['export_stems']=True
    st.setdefault('sfx',{})['render_both_mixes']=False; st['endcard']['enabled']=False
    # Context-dependent effects live in the base; sprite graphics remain independently editable.
    context={'stage','scene','grade','broll','flash','zoom'}
    base_elements=[e for e in elements if e['type'] in context]
    raster=work/'base_elements.json'; C.write_json({'elements':base_elements},raster)
    base_style=copy.deepcopy(st); base_style['captions']['engine']='off'; base_style['sfx']['enabled']=False
    CP.compose(video,work/'base.mp4',base_style,None,words,native_cuts,raster)
    import energy_curve as EC, audio_mix as AM, motion_language as ML
    st=ML.choose(st,work); cues=C.parse_srt(subs); st,enriched=EC.prepare(video,words,cues,elements,st,work)
    import sound_design as SD
    events=SD.gather(st,enriched,cues,words,C.brand_dir(st))
    AM.build_audio(video,work/'mix.wav',st,duration,sfx=events,brand_dir=C.brand_dir(st))
    # Audio mix uses its own export directory; copy only the explicitly named stems.
    for name in ('speech','sfx','music'):
        candidates=[work/(name+'.wav'),work/'stems'/(name+'.wav')]
        found=next((p for p in candidates if p.is_file()),None)
        if found is None: raise C.MontajError('Missing rendered stem: '+name)
        if found!=work/(name+'.wav'): shutil.copy2(found,work/(name+'.wav'))
    ctx=E.Ctx(st,C.brand_dir(st)); graphics=[]
    cutmeta=C.ffprobe_info(video)
    face=CP.F.detect(video,quiet=True,style=st) if st.get('zoom',{}).get('face_aware',True) else None
    _,fit=CP.fit_graph(cutmeta,st,face,C.brand_dir(st))
    ctx.anchor=CP.face_in_output(cutmeta,ctx.W,ctx.H,face,fit)
    for index,el in enumerate(elements):
        if el['type'] in context|{'sfx'}: continue
        if el.get('behind_person'): raise C.MontajError('Behind-person layer needs a footage mask; cannot export an independent sprite')
        layers=E.build_elements(ctx,[el],duration)
        for j,layer in enumerate(layers):
            start=max(0,layer.start); end=min(duration,layer.end)
            if end<=start: continue
            graphics.append(render_alpha(layer,work/'graphics'/f'{index:03}_{j}_{el["type"]}.mov',start,end,st))
            layer.close()
    clean=[dict(c,text=plain(c['text'])) for c in cues]; C.write_srt(clean,work/'captions.srt')
    # Parser normalises SRT precision and cue IDs. Store its canonical output for round-trip comparison.
    clean=C.parse_srt(work/'captions.srt')
    base=dict(file=str(work/'base.mp4'),record_in=0,record_out=total,source_in=0,source_out=total)
    tracks=[dict(kind='video',clips=[base])]+[dict(kind='video',clips=[g]) for g in graphics]
    for name in ('speech','sfx','music'):
        file=work/(name+'.wav')
        for ch in range(1,C.ffprobe_info(file)['channels']+1):
            tracks.append(dict(kind='audio',clips=[dict(base,file=str(file),source_channel=ch)]))
    raw=[dict(c,file=str(working_source),timecode_offset=offset) for c in listing]; source_tracks=[dict(kind='video',clips=raw)]
    v=st['video']; write_xml(work/'timeline.xml',tracks,fps,v['width'],v['height'],total,'Montaj layers')
    write_xml(work/'source_cuts.xml',source_tracks,fps,v['width'],v['height'],total,'Original source cuts')
    manifest=dict(fps=fps,duration=duration,source=str(source),source_timecode=tc_note,source_conform=conform,cut_list=listing,
                  timeline_tracks=tracks,source_tracks=source_tracks,captions=clean,graphics=graphics,
                  base_contains=base_elements,limitations=['Base motion/grade/context effects are rasterized; source timeline has original framing',
                  'Animated captions remain editable SRT; word animation is not transferred',
                  'Stems precede final mix limiter; summing is not bit-identical to delivery audio','GUI imports not tested on this machine'])
    C.write_json(manifest,work/'manifest.json'); return validate(work)

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('export'); q.add_argument('video'); q.add_argument('--source',required=True); q.add_argument('--cuts',required=True)
    q.add_argument('--style'); q.add_argument('--subs',required=True); q.add_argument('--words',required=True)
    q.add_argument('--elements',required=True); q.add_argument('--out-dir',required=True); q.add_argument('--approved',action='store_true')
    q=sub.add_parser('validate'); q.add_argument('folder')
    a=p.parse_args()
    if a.command=='validate': result=validate(Path(a.folder))
    else:
        if not a.approved: raise C.MontajError('Subtitle approval must be recorded in HOLAT before export --approved')
        C.busy_acquire('editor export: '+Path(a.video).name)
        result=export(Path(a.video),Path(a.source),C.read_json(a.cuts),C.load_style(a.style),Path(a.subs),
                      C.read_json(a.words)['words'],C.read_json(a.elements)['elements'],Path(a.out_dir))
    C.info('EXPORT [OK]: '+str(result))
if __name__=='__main__': C.run_main(main)
