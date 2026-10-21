import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Theme,ensureFont} from './theme';
// @ts-ignore -- runtime module is also exercised by node:test without a TS loader.
import {stateAt,validateStates} from './continuity.mjs';

type Content={eyebrow?:string;title?:string;subtitle?:string;icon?:'plane'|'calendar'|'document'|'chat';badge?:string};
export type CardState=Content & {at:number;duration:number;x:number;y:number;w:number;h:number;radius:number;rotate:number;opacity:number;curve?:string};
type Props={duration:number;theme:Theme;states:CardState[];fontSize?:number;background?:string;stroke?:string};
const Symbol:React.FC<{kind:Content['icon'];color:string}>=({kind,color})=><svg viewBox="0 0 100 100" width="100%" height="100%" fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
 {kind==='plane'?<><path d="M12 44 87 16 59 90 45 58 12 44Z"/><path d="m45 58 42-42"/></>:
 kind==='calendar'?<><rect x="15" y="22" width="70" height="65" rx="12"/><path d="M15 40h70M32 13v20M68 13v20M30 55h10m15 0h12M30 70h10m15 0h12"/></>:
 kind==='document'?<><path d="M25 12h33l19 20v56H25Z M58 12v20h19M38 48h27M38 61h27M38 74h15"/></>:
 <path d="M22 18h56q10 0 10 10v34q0 10-10 10H44L22 88V72q-10 0-10-10V28q0-10 10-10ZM29 38h42M29 52h28"/>}
</svg>;

// A single clipped surface survives every state change; no remount, no scale-stretched type.
export const ContinuityCard:React.FC<Props>=(p)=>{
 const f=useCurrentFrame(),{fps,width:W,height:H}=useVideoConfig();
 validateStates(p.states);ensureFont(p.theme.font);
 const {box,from,to,mix,index}=stateAt(f/fps,p.states);
 const contentKeys=['eyebrow','title','subtitle','icon','badge'] as const;
 const changed=index>0&&contentKeys.some(k=>from[k]!==to[k]);
 const sharedMain=index>0&&from.title===to.title&&from.icon===to.icon&&from.eyebrow===to.eyebrow;
 // A compact state often only removes secondary text. Keep the same title/icon
 // alive instead of crossfading two vertically offset copies of identical text.
 const subMix=from.subtitle===to.subtitle?1:to.subtitle?mix:1-mix;
 const badgeMix=from.badge===to.badge?1:to.badge?mix:1-mix;
 const layers=sharedMain?[{s:{...to,subtitle:to.subtitle??from.subtitle,badge:to.badge??from.badge,
   w:from.w+(to.w-from.w)*mix,h:from.h+(to.h-from.h)*mix},opacity:1,dy:0,sub:subMix,badge:badgeMix}]:
  changed?[{s:from,opacity:1-mix,dy:-14*mix,sub:1,badge:1},{s:to,opacity:mix,dy:14*(1-mix),sub:1,badge:1}]:
  [{s:to,opacity:1,dy:0,sub:1,badge:1}];
 return <AbsoluteFill><div data-motion-id="continuity-card" style={{position:'absolute',left:(box.x-box.w/2)*W,top:(box.y-box.h/2)*H,width:box.w*W,height:box.h*H,
  opacity:box.opacity,rotate:`${box.rotate}deg`,borderRadius:box.radius*W,background:p.background??p.theme.paper,color:p.theme.ink,
  border:`${W*.0015}px solid ${p.stroke??'#D9DFE5'}`,boxSizing:'border-box',overflow:'hidden',
  boxShadow:`0 ${W*.012}px ${W*.035}px rgba(12,27,43,.10)`,fontFamily:p.theme.font}}>
  {/* Each content snapshot keeps its own final layout while the parent mask morphs.
      Letting flex use the moving card width rewrapped titles mid-entrance. */}
  {layers.map(({s,opacity,dy,sub,badge},i)=><div key={i} data-card-content={index===0?0:index-1+i} style={{position:'absolute',left:'50%',top:'50%',
   width:s.w*W,height:s.h*H,opacity,transform:`translate(-50%, -50%) translateY(${dy*W/1080}px)`,
   display:'flex',alignItems:'center',padding:W*.035,gap:W*.028,boxSizing:'border-box'}}>
   {s.icon?<div style={{flexShrink:0,width:W*.082,height:W*.082,background:'#E8F0ED',borderRadius:W*.019,padding:W*.016}}><Symbol kind={s.icon} color={p.theme.accent}/></div>:null}
   <div style={{minWidth:0,flex:1}}>
    {s.eyebrow?<div style={{fontSize:W*.023,fontWeight:600,letterSpacing:W*.0015,color:'#64717E',marginBottom:W*.012}}>{s.eyebrow}</div>:null}
    {s.title?<div style={{fontSize:(p.fontSize??.058)*W,fontWeight:650,letterSpacing:-W*.002,lineHeight:1.08,whiteSpace:'pre-line'}}>{s.title}</div>:null}
    {s.subtitle?<div style={{fontSize:W*.027,fontWeight:450,lineHeight:1.3,color:'#52606F',marginTop:W*.014*sub,
      maxHeight:W*.027*1.3*sub,opacity:sub,overflow:'hidden',whiteSpace:'pre-line'}}>{s.subtitle}</div>:null}
   </div>
   {s.badge?<div style={{fontSize:W*.025,fontWeight:600,color:p.theme.accent,alignSelf:'flex-start',opacity:badge}}>{s.badge}</div>:null}
  </div>)}
 </div></AbsoluteFill>;
};
