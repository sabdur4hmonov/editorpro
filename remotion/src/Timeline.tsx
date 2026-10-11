import React, {useLayoutEffect} from 'react';
import {AbsoluteFill, OffthreadVideo, Img, staticFile, useCurrentFrame, useVideoConfig, Sequence, Freeze, delayRender, continueRender, cancelRender} from 'remotion';
import {eased, clamp, PRESETS} from './easing.mjs';
import {SCENES} from './scenes';
import {DEFAULT_THEME, ensureFont} from './theme';
import {loadFont} from '@remotion/fonts';
const localLoaded=new Set<string>();

export type TimelineProps = {
  width:number; height:number; fps:number; durationInFrames:number;
  video:string; videoFrames:number; font:string; fallback:string;
  color:string; accent:string; motion:Record<string,any>; safe:Record<string,number>;
  captions:Array<any>; elements:Array<any>; transitions:Array<any>; trace?:boolean; fonts?:Record<string,string>; ghost?:boolean;
};
const media=(file:string)=>staticFile(file);
// The same envelope drives both footage and words of a transition group.
export const envelope=(frame:number,start:number,end:number,m:any)=>{
  const inP=clamp((frame-start)/m.enterFrames), outP=clamp((frame-end)/m.exitFrames);
  return {enter:eased(inP,m.curve,m),out:eased(outP,'easeInOutCubic'),
    opacity:clamp(eased(inP,'easeOutCubic'))*(1-eased(outP,'easeInOutCubic'))};
};
const movement=(p:number,animation:string,distance:number)=>({
  x:animation==='slide'?(1-p)*distance:0,
  y:animation==='wipe'?(1-p)*distance:0,
  scale:animation==='pop'?Math.max(.1,.78+.22*p):1,
});

const Captions:React.FC<{p:TimelineProps}> = ({p})=>{
  const f=useCurrentFrame();
  return <>{p.captions.map(c=>{
    if(f<c.startFrame || f>c.endFrame+p.motion.exitFrames) return null;
    const exit=envelope(f,c.startFrame,c.endFrame,p.motion).out;
    const linked=p.transitions.find(t=>t.id===c.transitionGroup);
    const linkedE=linked?envelope(f,linked.startFrame,linked.endFrame,p.motion):null;
    // Position and width are precomputed for the WHOLE phrase, including invisible words.
    return <div key={c.id} style={{position:'absolute',left:0,top:0,
      opacity:linkedE?clamp(eased(clamp((f-linked!.startFrame+1)/p.motion.enterFrames),'easeOutCubic')):undefined,
      translate:linkedE?`${(1-linkedE.enter)*p.motion.distance}px 0px`:undefined}}>
      {c.words.map((w:any)=>{
    const progress=eased(clamp((f-w.frame+1)/p.motion.enterFrames),c.animation==='pop'?'spring':p.motion.curve,p.motion);
        const a=movement(progress,c.animation,p.motion.distance);
        const visible=f>=w.frame && f<=c.endFrame+p.motion.exitFrames;
        const opacity=visible && !(p.ghost && f>=w.frame+p.motion.enterFrames && f<c.endFrame) ? clamp(eased(clamp((f-w.frame+1)/p.motion.enterFrames),'easeOutCubic'))*(1-exit):0;
        const blur=p.motion.blur.enabled?Math.min(p.motion.blur.intensity,Math.abs(1-progress)*p.motion.blur.intensity):0;
        return <span key={w.id} data-motion-id={w.id} data-role="caption" data-word-frame={w.frame}
          data-phase={f<w.frame+p.motion.enterFrames?'enter':f>=c.endFrame?'exit':'hold'}
          style={{position:'absolute',left:w.x+a.x-exit*p.motion.distance*.5,top:w.y+a.y+exit*12,
            width:w.width,boxSizing:'border-box',whiteSpace:'pre',fontSize:w.size,fontWeight:w.weight,fontFamily:`"${p.font}", "${p.fallback}"`,
            color:w.emphasis?p.accent:p.color,lineHeight:1.12,opacity,scale:a.scale,
            transformOrigin:'center',filter:blur?`blur(${blur}px)`:undefined,
            clipPath:c.animation==='wipe'?`inset(${(1-clamp(progress))*100}% 0 0 0)`:undefined,
            background:w.box?p.motion.backing:undefined,borderRadius:8,padding:w.box?`0 ${8*p.width/1080}px`:0}}>{w.text}</span>;
      })}
    </div>;
  })}</>;
};

const Graphic:React.FC<{el:any;p:TimelineProps}> = ({el,p})=>{
  const f=useCurrentFrame();
  const e=envelope(f,el.startFrame,el.endFrame,p.motion);
  const a=movement(e.enter,el.animation??'slide',p.motion.distance);
  const style:React.CSSProperties={position:'absolute',left:el.x*p.width,top:el.y*p.height,
    width:el.width*p.width,opacity:e.opacity,translate:`${a.x-e.out*p.motion.distance*.5}px ${a.y}px`,
    scale:a.scale,rotate:`${(el.rotate??0)+(1-e.enter)*(el.rotateFrom??0)}deg`,
    transform:'translate(-50%, -50%)',fontFamily:`"${el.font??p.font}", "${p.fallback}"`,
    color:el.color??p.color,fontSize:el.size??64,textAlign:'center',fontWeight:el.weight??700,
    borderRadius:el.radius??20,overflow:'hidden'};
  const attr={'data-motion-id':el.id,'data-role':'graphic','data-safe-required':['title','text','callout','lower_third','list','panel','stat','follow'].includes(el.type)?'true':'false','data-phase':f<el.startFrame+p.motion.enterFrames?'enter':f>=el.endFrame?'exit':'hold'};
  if(el.type==='image') return <div {...attr} style={style}><Img src={media(el.file)} style={{width:'100%',display:'block'}}/></div>;
  if(el.type==='broll') return <AbsoluteFill {...attr} style={{opacity:e.opacity,translate:`${a.x}px 0px`,top:el.mode==='split'?'50%':0,height:el.mode==='split'?'50%':'100%',overflow:'hidden'}}>
    {/\.(mp4|mov|webm|mkv)$/i.test(el.file)?<Sequence from={el.startFrame} durationInFrames={el.endFrame-el.startFrame+p.motion.exitFrames+1} layout="none"><OffthreadVideo src={media(el.file)} muted trimBefore={el.offsetFrames??0}
      style={{width:'100%',height:'100%',objectFit:'cover',objectPosition:`${(el.focus_x??.5)*100}% center`,filter:`brightness(${1-(el.dim??0)}) grayscale(${el.bw?1:0})`}}/></Sequence>:
      <Img src={media(el.file)} style={{width:'100%',height:'100%',objectFit:'cover',filter:`brightness(${1-(el.dim??0)}) grayscale(${el.bw?1:0})`}}/>}
      <AbsoluteFill style={{background:'linear-gradient(transparent 45%, rgba(0,0,0,.75))'}}/>
    </AbsoluteFill>;
  if(el.type==='scene') return <AbsoluteFill {...attr} style={{opacity:e.opacity,background:el.background?.color1??'#15212a'}}/>;
  if(el.type==='list' || el.type==='panel') {
    return <div {...attr} style={{...style,background:p.motion.backing,padding:24}}>
      {el.title && <div>{el.title}</div>}{el.items.map((it:any,i:number)=>{
        const progress=eased(clamp((f-it.frame)/p.motion.enterFrames),p.motion.curve,p.motion);
        return <div key={i} style={{opacity:f>=it.frame?clamp(progress):0,translate:`${(1-progress)*p.motion.distance}px 0px`,padding:8}}>{it.text}</div>;
      })}</div>;
  }
  if(el.type==='stat') return <div {...attr} style={style}>{(el.value*clamp(e.enter)).toFixed(el.decimals??0)}{el.suffix}<div style={{fontSize:'40%'}}>{el.label}</div></div>;
  if(el.type==='follow') {
    const tap=eased(clamp((f-(el.tapFrame??el.startFrame+p.fps))/p.motion.enterFrames),'easeOutBack');
    return <div {...attr} style={{...style,background:p.motion.backing,padding:24}}><div>{el.name??''}</div><div>{el.handle??''}</div>
      <div style={{background:p.accent,color:'#15212a',borderRadius:20,padding:12,scale:1+.035*(1-tap)}}>{f>=(el.tapFrame??Infinity)?el.done??'Obuna bo‘ldingiz':el.button??'Obuna bo‘ling'}</div></div>;
  }
  if(el.type==='remotion_scene') {
    const Scene=SCENES[el.scene.type];
    return <Sequence from={el.startFrame} durationInFrames={el.endFrame-el.startFrame+p.motion.exitFrames} layout="none">
      <Scene {...el.scene} theme={{...DEFAULT_THEME,font:p.font,display:el.font??p.font,text:p.color,accent:p.accent}}/>
    </Sequence>;
  }
  return <div {...attr} style={{...style,background:el.backing?p.motion.backing:undefined,padding:el.backing?20:0}}>{el.text}</div>;
};

export const Timeline:React.FC<TimelineProps>=(p)=>{
  const f=useCurrentFrame(); const {fps}=useVideoConfig();
  ensureFont(p.font); ensureFont(p.fallback);
  for(const [family,file] of Object.entries(p.fonts??{})) {
    const key=family+file;
    if(!localLoaded.has(key)) {localLoaded.add(key);loadFont({family,url:staticFile(file),weight:'100 900'});}
  }
  for(const el of p.elements) if(el.font) ensureFont(el.font);
  const active=p.transitions.find(t=>t.type==='broll' && f>=t.startFrame && f<=t.endFrame+p.motion.exitFrames);
  const cut=p.transitions.find(t=>t.type==='cut' && f>=t.startFrame && f<t.startFrame+p.motion.enterFrames);
  const cutP=cut?eased(clamp((f-cut.startFrame+1)/p.motion.enterFrames),p.motion.curve,p.motion):1;
  const group=active?envelope(f,active.startFrame,active.endFrame,p.motion):null;
  useLayoutEffect(()=>{
    if(!p.trace) return;
    const handle=delayRender('Measure final font/layout geometry');
    let released=false,disposed=false;
    const release=()=>{if(!released) {released=true;continueRender(handle);}};
    const measure=(deadline:number)=>{
    if(disposed) {release();return;}
    const rect=document.querySelector('[data-timeline]')?.getBoundingClientRect();
    if(!rect || !rect.width || !rect.height) {
      if(performance.now()>deadline) {cancelRender(new Error('QA viewport has no measurable size'));release();return;}
      requestAnimationFrame(()=>measure(deadline));return;
    }
    const sx=p.width/rect.width,sy=p.height/rect.height;
    const boxes=Array.from(document.querySelectorAll<HTMLElement>('[data-motion-id]')).filter(el=>!el.closest('[data-trail-copy]')).map(el=>{
      const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
      let opacity=Number(cs.opacity),parent=el.parentElement;
      while(parent && parent!==document.querySelector('[data-timeline]')) {opacity*=Number(getComputedStyle(parent).opacity);parent=parent.parentElement;}
      return {id:el.dataset.motionId,role:el.dataset.role,safeRequired:el.dataset.safeRequired==='true',phase:el.dataset.phase,wordFrame:Number(el.dataset.wordFrame),
        x:(r.left-rect.left)*sx,y:(r.top-rect.top)*sy,w:r.width*sx,h:r.height*sy,opacity};
    });
    console.log('MOTION_QA:'+JSON.stringify({frame:f,boxes}));
    release();
    };
    document.fonts.ready.then(()=>requestAnimationFrame(()=>measure(performance.now()+3000)));
    return ()=>{disposed=true;release();};
  },[f,p.trace]);
  return <AbsoluteFill data-timeline style={{backgroundColor:'#0e151c'}}>
    {cut && <Freeze frame={cut.startFrame-1}><OffthreadVideo src={media(p.video)} muted style={{width:'100%',height:'100%',objectFit:'cover'}}/></Freeze>}
    <AbsoluteFill style={{opacity:(group&&active?.mode!=='split'?1-group.opacity:1)*clamp(cutP),translate:cut?`${(1-cutP)*p.motion.distance}px 0px`:undefined}}>
      <OffthreadVideo src={media(p.video)} muted style={{width:'100%',height:'100%',objectFit:'cover'}}/>
    </AbsoluteFill>
    {p.elements.map(el=>f>=el.startFrame&&f<=el.endFrame+p.motion.exitFrames?<Graphic key={el.id} el={el} p={p}/>:null)}
    {p.motion.blur.enabled && [.25,.5].map(lag=><AbsoluteFill data-trail-copy key={lag} style={{opacity:Math.min(.14,p.motion.blur.intensity*.05)}}>
      <Freeze frame={f-lag}><Captions p={{...p,ghost:true}}/></Freeze></AbsoluteFill>)}
    <AbsoluteFill style={{opacity:clamp(cutP),translate:cut?`${(1-cutP)*p.motion.distance}px 0px`:undefined}}><Captions p={p}/></AbsoluteFill>
  </AbsoluteFill>;
};
