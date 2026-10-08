"""Transcript moments, measured candidates, one approval sheet and reason-aware history."""
from pathlib import Path
import argparse, hashlib, json, re, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import common as C
import images, frames
import cv2
from energy_curve import plain

DEFAULTS={'min_seconds':2.5,'max_seconds':4,'min_crop_width':540,'min_crop_height':960,
          'min_score':.48,'max_moments':3,'static_seconds':6,'mode':'split',
          'candidate_kind':'mixed',
          'lower_gradient':{'from':.52,'amount':.5},'colour_required':True,
          'lexicon':{'object':{'kislorod':'medical oxygen mask equipment','yurak':'anatomical heart model',
             'siydik':'urine specimen container','pnevmoniya':'anatomical lung model','karavot':'hospital bed',
             'qon':'blood sample tube','fast':'fast food burger','dori':'medicine tablets'},
             'action':{'yugur':'child running outdoors','ovqat':'child eating meal'},
             'place':{'klinika':'medical clinic interior','shahar':'city traffic'},
             'abstract':{'xato':'mistake explanation','natija':'result explanation'}}}

def cfg(style): return C.deep_merge(DEFAULTS,style.get('broll',{}))
def tokens(text): return set(re.findall(r"[\w‘ʻ']+",str(text).lower()))
def asset_id(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def relevance(candidate, moment):
    """Conservative lexical retrieval gate, followed by mandatory visual review."""
    query=tokens(moment['query'])-{'medical','equipment','anatomical','model'}
    title=tokens(candidate.get('title','')+' '+' '.join(candidate.get('tags',[])))
    aliases={'urinalysis':'urine','hospital':'hospital','non-rebreather':'oxygen'}
    title|={value for key,value in aliases.items() if key in candidate.get('title','').lower()}
    anchors=query&{'oxygen','urine','bed','heart','lung','child','burger','blood'}
    return bool(title&query) and (not anchors or bool(title&anchors))

def moments(cues,style,elements=None):
    config=cfg(style); found=[]
    for cue in cues:
        text=plain(cue['text']); reasons=[]; queries=[]; score=0
        for kind,lex in config['lexicon'].items():
            for key,query in lex.items():
                if key in text.lower():
                    reasons.append(kind+': '+key); queries.append(query)
                    score+= {'object':4,'action':3,'place':3,'abstract':1}[kind]
        if re.search(r'\d',text): score+=2; reasons.append('number: prefer factual graphic')
        if cue['end']-cue['start']>=config['static_seconds']:
            score+=1; reasons.append('long static caption stretch')
        visual_events=[float(e.get('start',e.get('at',0))) for e in elements or [] if e.get('type') not in ('sfx','zoom')]
        if visual_events and min(abs(cue['start']-at) for at in visual_events)>=config['static_seconds']:
            score+=1; reasons.append('far from existing visual event')
        if not reasons: continue
        duration=min(config['max_seconds'],max(config['min_seconds'],cue['end']-cue['start']))
        found.append(dict(id=f'm{len(found)+1:02}',start=cue['start'],end=cue['start']+duration,
                          speech_end=cue['end'],text=text,query=queries[0] if queries else text,
                          score=score,reasons=reasons,method='lexical heuristic; exact semantic fit needs visual review'))
    # Long static stretches can span many short captions; do not require a long cue.
    total=max((c['end'] for c in cues),default=0)
    changes=sorted({0,total,*[float(e.get('start',e.get('at',0))) for e in elements or []
                    if e.get('type') not in ('sfx',) and 0<=float(e.get('start',e.get('at',0)))<=total]})
    for a,b in zip(changes,changes[1:]):
        if b-a<config['static_seconds']:continue
        related=[m for m in found if a<=m['start']<b]
        if related:
            for m in related:
                m['score']+=1;m['reasons'].append(f'long static visual span {a:.2f}..{b:.2f}s')
        else:
            text=' '.join(plain(c['text']) for c in cues if c['start']<b and c['end']>a)
            found.append(dict(id=f'm{len(found)+1:02}',start=a,end=min(b,a+config['max_seconds']),
                 speech_end=b,text=text,query='',score=1,reasons=[f'long static visual span {a:.2f}..{b:.2f}s'],
                 method='Requires a content-specific query/graphic; generic stock is not substituted'))
    return sorted(found,key=lambda x:(-x['score'],x['start']))

def local_assets(folders):
    out=[]
    for folder in folders:
        folder=Path(folder)
        if not folder.is_dir(): continue
        for p in sorted(folder.rglob('*')):
            if p.suffix.lower() not in C.VIDEO_EXTS|{'.png','.jpg','.jpeg','.webp'}: continue
            credit=p.with_name(p.name+'.credit.json')
            # Candidate sheets and unknown stock files must not masquerade as usable assets.
            if not credit.is_file(): continue
            meta=C.read_json(credit)
            side=p.with_name(p.name+'.asset.json')
            tags=C.read_json(side).get('tags',[]) if side.is_file() else []
            out.append(dict(file=str(p),tags=tags,credit=meta,title=meta.get('title',p.stem),origin='local'))
    return out

def preview(path,at,work):
    if Path(path).suffix.lower() not in C.VIDEO_EXTS:
        with Image.open(path) as source:
            if source.mode=='RGBA':
                background=Image.new('RGBA',source.size,'#26343F')
                return Image.alpha_composite(background,source).convert('RGB')
            return source.convert('RGB')
    work.mkdir(parents=True,exist_ok=True); out=work/(hashlib.sha256(str(path).encode()).hexdigest()[:12]+f'_{at:.3f}.jpg')
    if not frames.grab(Path(path),at,out,960): raise C.MontajError(f'Broll preview failed: {path}')
    return Image.open(out).convert('RGB')

def crop_metrics(im):
    w,h=im.size; ratio=9/16
    cw,ch=(h*ratio,h) if w/h>ratio else (w,w/ratio)
    rect=[round((w-cw)/2),round((h-ch)/2),round((w+cw)/2),round((h+ch)/2)]
    return rect,round(cw*ch/(w*h),4)

def colour_vector(im,mask=None):
    array=np.array(im.resize((160,160)),np.float32)/255
    lab=cv2.cvtColor(array,cv2.COLOR_RGB2LAB)
    hsv=cv2.cvtColor(array,cv2.COLOR_RGB2HSV)
    valid=np.ones((160,160),bool) if mask is None else np.array(mask.resize((160,160),Image.Resampling.NEAREST))>32
    if not valid.any(): return np.zeros(3),0
    return np.median(lab[valid],axis=0),float(np.mean(hsv[:,:,1][valid]))

def inspect(candidate,footage,moment,style,work):
    path=Path(candidate['file']); config=cfg(style); image=path.suffix.lower() not in C.VIDEO_EXTS
    if image:
        with Image.open(path) as source: w,h=source.size; alpha=source.mode=='RGBA' and source.getchannel('A').getextrema()[0]<255
        duration=None
    else:
        info=C.ffprobe_info(path); w,h=info['width'],info['height']; duration=info['duration']; alpha=info.get('alpha',False)
    # Seeking beyond the final decoded frame yields no PNG even before format.duration.
    last_safe=max(0,duration-2/max(1,info['fps'])) if not image else 0
    times=[0] if image else [0,min(last_safe,config['min_seconds']/2),min(last_safe,config['min_seconds'])]
    shots=[preview(path,t,work) for t in times]
    rect,retained=crop_metrics(shots[0]); cropped=shots[0].crop(rect)
    if alpha:
        # Stickers are fitted in their entirety; they are not full-screen b-roll crops.
        cropped=Image.new('RGB',(540,960),'#26343F')
        fitted=ImageOps.contain(shots[0],(500,850))
        cropped.paste(fitted,((540-fitted.width)//2,(960-fitted.height)//2))
    if alpha and image:
        with Image.open(path) as source: lab,sat=colour_vector(source.convert('RGB'),source.getchannel('A'))
    else:
        colours=[colour_vector(shot.crop(crop_metrics(shot)[0])) for shot in shots]
        lab=np.median([c[0] for c in colours],axis=0);sat=min(c[1] for c in colours)
    reference,_=colour_vector(footage)
    distance=float(np.linalg.norm(lab-reference))
    # Canny + small rectangular contour count: suspicious text-like strokes, not OCR.
    text_count=0;corner_edges=0
    for shot in shots:
        gray=cv2.cvtColor(np.array(shot.crop(crop_metrics(shot)[0]).resize((270,480))),cv2.COLOR_RGB2GRAY)
        edges=cv2.Canny(gray,80,160); contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        boxes=[cv2.boundingRect(c) for c in contours]
        text_count=max(text_count,sum(2<=bw<=40 and 3<=bh<=30 and .1<bw/max(1,bh)<4 for x,y,bw,bh in boxes))
        corner_edges=max(corner_edges,float(np.mean(np.concatenate([edges[:90,:70].ravel(),edges[-90:,-70:].ravel()]))/255))
    full_cw,full_ch= ((h*9/16,h) if w/h>9/16 else (w,w*16/9))
    checks={'crop_9_16':{'rect_on_preview':rect,'retained_area':retained,'measure':'center 9:16 crop; retained source area fraction; subject not verified'},
            'resolution':{'width':w,'height':h,'crop_width':round(full_cw),'crop_height':round(full_ch),
                          'ok':(w>=260 and h>=100) if alpha else (full_cw>=config['min_crop_width'] and full_ch>=config['min_crop_height']),
                          'measure':'source center-crop pixel dimensions; alpha sticker uses its native footprint'},
            'duration':{'seconds':duration,'ok':image or duration>=moment['end']-moment['start'],'measure':'ffprobe duration >= requested in/out; still images have no duration limit'},
            'colour':{'lab_median_distance':round(distance,2),'mean_saturation':round(sat,3),
                      'ok':not config['colour_required'] or sat>.035,'sample_seconds':times,
                      'measure':'median CIE Lab across samples; minimum sampled HSV mean saturation; alpha excludes transparent background'},
            'text_watermark_logo':{'textlike_contours':int(text_count),'corner_edge_fraction':round(corner_edges,3),
                                  'status':'human_review_required','sample_seconds':times,
                                  'measure':'maximum sampled Canny small-contour count and corner edge density; not OCR, logo identification or absence proof'},
            'semantic':{'status':'human_review_required','measure':'title/query token overlap ranks retrieval; exact object/age/action needs agent/user visual review'},
            'license':{'ok':bool(candidate.get('credit',{}).get('license')),'measure':'source credit sidecar exists; license terms still apply'}}
    score=.7-.15*min(1,distance/70)+.15*retained
    score+=.1*len(tokens(moment['query'])&tokens(candidate.get('title','')+' '+' '.join(candidate.get('tags',[]))))/max(1,len(tokens(moment['query'])))
    checks['semantic']['retrieval_match']=relevance(candidate,moment)
    usable=all(checks[k]['ok'] for k in ('resolution','duration','colour','license')) and relevance(candidate,moment)
    return dict(candidate,id=asset_id(path),alpha=alpha,checks=checks,score=round(score if usable else 0,4),
                technical_ok=usable,visual_review=None,preview=str(work/(asset_id(path)[:12]+'.jpg'))),cropped

def history_score(candidate,moment,history):
    adjustment=0; cwords=tokens(candidate.get('title','')+' '+' '.join(candidate.get('tags',[])))
    exact=[e for e in history.get('entries',[]) if e['asset_id']==candidate['id']]
    if exact:
        # Latest explicit decision wins; old approvals cannot outvote a new rejection.
        adjustment=-1 if exact[-1]['status']=='rejected' else .05
    seen=set()
    for entry in history.get('entries',[]):
        similar=entry['asset_id']==candidate['id']
        reason=entry.get('reason','').lower()
        if reason in seen:continue
        seen.add(reason)
        if entry['status']=='rejected':
            if ('black and white' in reason or 'oq-qora' in reason) and candidate['checks']['colour']['mean_saturation']<.035: adjustment-=.7
            if ('adult' in reason or 'katta odam' in reason) and cwords&{'adult','man','woman'} and tokens(moment['query'])&{'child','children','baby'}: adjustment-=.7
            if 'generic' in reason and not cwords&tokens(moment['query']): adjustment-=.3
    return round(candidate['score']+adjustment,4)

def contact_sheet(moment,candidates,out):
    cellw,cellh=320,680; im=Image.new('RGB',(cellw*3,cellh),'#15171B'); d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(C.ROOT/'style/fonts/Inter.ttf'),16)
    for i in range(3):
        x=i*cellw; d.text((x+8,8),f"{moment['id']} | {moment['start']:.2f}s | {i+1}",font=font,fill='white')
        if i>=len(candidates):
            d.text((x+8,100),'NO SUITABLE CANDIDATE\nPrefer none over a weak clip',font=font,fill='#FFAD75'); continue
        c=candidates[i]; shot=Image.open(c['preview']); shot=ImageOps.fit(shot,(300,533))
        im.paste(shot,(x+10,40))
        d.text((x+8,582),f"score {c['rank']:.2f} | {c['origin']}\n{Path(c['file']).name[:29]}\ntechnical {'OK' if c['technical_ok'] else 'FAIL'}; visual review required",font=font,fill='white')
    C.guard_output(out); im.save(out)

def prepare(video,cues,style,work,folders,moment_list=None,stock=True,history=None,kind=None):
    work.mkdir(parents=True,exist_ok=True); config=cfg(style); local=local_assets(folders)
    history=history or {'entries':[]}; ranked=moments(cues,style)
    chosen=moment_list or ranked[:config['max_moments']]; allresults=[]; total=C.ffprobe_info(video)['duration']
    for moment in chosen:
        moment=dict(moment); moment['end']=min(total,moment['end'])
        if moment['end']-moment['start']<config['min_seconds']: continue
        folder=work/moment['id']; folder.mkdir(exist_ok=True)
        frame=preview(video,moment['start'],folder/'frames')
        pool=sorted([c for c in local if relevance(c,moment)],key=lambda c:-len(tokens(moment['query'])&tokens(c['title']+' '+' '.join(c['tags']))))[:8]
        if stock and moment['query'].strip():
            kind=kind or config['candidate_kind']
            if kind not in ('photo','video','mixed'): raise C.MontajError('broll.candidate_kind: photo/video/mixed required')
            for media_kind in (('video','photo') if kind=='mixed' else (kind,)):
                stockdir=folder/('stock_'+media_kind)
                data=images.search(moment['query'],stockdir,9,media_kind,'any')
                for c in data['candidates']:
                    if not relevance(c,moment): continue
                    try: result=images.pick([c['n']],stockdir)[0]
                    except C.MontajError as exc:
                        C.warn(f"{moment['id']}: candidate download rejected: {exc}")
                        continue
                    pool.append(dict(file=str(result['file']),credit=result['credit'],title=c.get('title',''),tags=[],origin='stock'))
                    if len(pool)>=12: break
        candidates=[]
        for c in pool:
            measured,crop=inspect(c,frame,moment,style,folder/'frames')
            crop.save(measured['preview']); measured['rank']=history_score(measured,moment,history)
            candidates.append(measured)
        candidates=sorted([c for c in candidates if c['technical_ok']],key=lambda c:-c['rank'])
        # Keep provenance diversity when a suitable local cutout exists.
        selected=[]
        for origin in ('local','stock'):
            item=next((c for c in candidates if c['origin']==origin and c['technical_ok']),None)
            if item: selected.append(item)
        def source_key(c):
            credit=c.get('credit',{})
            return (credit.get('source'),credit.get('id')) if credit.get('id') else c['id']
        seen={source_key(c) for c in selected}
        for c in candidates:
            if source_key(c) not in seen and len(selected)<3:
                selected.append(c); seen.add(source_key(c))
        selected+= [c for c in candidates if c not in selected][:max(0,3-len(selected))]
        selected=selected[:3]
        for i,c in enumerate(selected,1): c['number']=i
        sheet=folder/'candidates.jpg'; contact_sheet(moment,selected,sheet)
        allresults.append(dict(moment=moment,candidates=selected,sheet=str(sheet)))
    report={'moments':allresults,'ranked_moments':ranked,'approval':None,'history_snapshot':history,
            'rule':'Show every 3-candidate sheet together once. User picks numbers or auto. Weak/semantically wrong candidates omitted.'}
    C.write_json(report,work/'broll_plan.json'); return report

def accept(plan,selections,approval,style,history,work):
    if not approval.strip(): raise C.MontajError('Written user approval is required')
    output=[]; config=cfg(style); entries=list(history.get('entries',[]))
    for group in plan['moments']:
        moment=group['moment']; choice=selections.get(moment['id'],'none')
        if choice=='none': continue
        candidates=group['candidates']
        eligible=[c for c in candidates if c['technical_ok'] and c['rank']>=config['min_score'] and c.get('visual_review')=='ok']
        c=max(eligible,key=lambda c:c['rank']) if choice=='auto' and eligible else next((c for c in candidates if c['number']==choice),None)
        if c is None or c not in eligible:
            C.warn(f"{moment['id']}: weak or visually unchecked candidate skipped"); continue
        entries.append(dict(asset_id=c['id'],status='accepted',reason=approval,moment=moment['text'],file=c['file']))
        if c['alpha']:
            output.append(dict(type='image',start=moment['start'],end=moment['end'],file=c['file'],x=.25,y=.68,width=.24,anim='pop'))
        else:
            output.append(dict(type='broll',start=moment['start'],end=moment['end'],file=c['file'],mode=config['mode'],
                               bw=False,lower_gradient=config['lower_gradient']))
    plan['approval']=approval; C.write_json(plan,work/'broll_plan.json')
    C.write_json({'entries':entries},work/'broll_history.json')
    C.write_json({'elements':output},work/'selected_elements.json')
    return output,{'entries':entries}

def reject(history,candidate,reason):
    if not reason.strip(): raise C.MontajError('Rejection reason required')
    history.setdefault('entries',[]).append(dict(asset_id=candidate['id'],status='rejected',reason=reason,file=candidate['file']))
    return history

def sync_history(local_history):
    """Publish only at idle, as shared learning; per-video file always survives."""
    import handoff
    if handoff.unfinished_notes():
        C.warn('Shared broll_history deferred: unfinished videos exist; retain own job history')
        return False
    path=C.ROOT/'style/broll_history.json'
    with C.file_mutex(C.TEMP_DIR/'.broll_history.guard'):
        data=C.read_json(path) if path.is_file() else {'entries':[]}
        for row in local_history.get('entries',[]):
            if row not in data['entries']: data['entries'].append(row)
        C.atomic_text(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return True

def main():
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('prepare'); q.add_argument('video'); q.add_argument('--subs',required=True); q.add_argument('--style')
    q.add_argument('--out-dir',required=True); q.add_argument('--local',action='append',default=['assets/library'])
    q.add_argument('--moments'); q.add_argument('--history'); q.add_argument('--no-stock',action='store_true')
    q.add_argument('--kind',choices=('photo','video','mixed'),help='Overrides broll.candidate_kind')
    q=s.add_parser('accept'); q.add_argument('plan'); q.add_argument('--selection',required=True,help='JSON mapping moment id to number/auto/none')
    q.add_argument('--approval',required=True); q.add_argument('--style'); q.add_argument('--history')
    q=s.add_parser('reject'); q.add_argument('plan'); q.add_argument('--moment',required=True); q.add_argument('--number',type=int,required=True)
    q.add_argument('--reason',required=True); q.add_argument('--history',required=True)
    q=s.add_parser('sync-history'); q.add_argument('history')
    a=p.parse_args(); history_path=Path(a.history) if getattr(a,'history',None) else C.ROOT/'style/broll_history.json'
    history=C.read_json(history_path) if history_path.is_file() else {'entries':[]}
    if a.command=='prepare':
        plan=prepare(Path(a.video),C.parse_srt(a.subs),C.load_style(a.style),C.guard_output(a.out_dir),a.local,
                     C.read_json(a.moments) if a.moments else None,not a.no_stock,history,a.kind)
        C.info(f'BROLL: {len(plan["moments"])} sheets; '+str(Path(a.out_dir)/'broll_plan.json'))
    elif a.command=='accept':
        plan=C.read_json(a.plan); accept(plan,json.loads(a.selection),a.approval,C.load_style(a.style),history,Path(a.plan).parent)
    elif a.command=='reject':
        plan=C.read_json(a.plan); group=next(g for g in plan['moments'] if g['moment']['id']==a.moment)
        candidate=next(c for c in group['candidates'] if c['number']==a.number)
        C.write_json(reject(history,candidate,a.reason),C.guard_output(a.history))
    else: sync_history(history)
if __name__=='__main__': C.run_main(main)
