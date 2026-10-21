import React from 'react';
import {AbsoluteFill,useCurrentFrame,useVideoConfig} from 'remotion';
import {ensureFont,Theme} from './theme';
// @ts-ignore -- shared deterministic module, tested directly by Node.
import {progress} from './continuity.mjs';

type Props={duration:number;theme:Theme;title:string;subtitle:string;eyebrow?:string;
 kind:'calendar'|'record'|'form'|'flow';number?:string};

// Original semantic paper graphics. There is no copied reference artwork or official form facsimile.
export const PaperExplainer:React.FC<Props>=(p)=>{
 const frame=useCurrentFrame(),{fps,width:W,height:H}=useVideoConfig(),t=frame/fps;
 ensureFont(p.theme.font);
 const curve=(at:number,d=.76)=>progress(t,at,d,'settledSpring',{damping:28,stiffness:180,mass:1});
 const a=curve(.14),b=curve(.23),c=curve(.33),d=curve(.43);
 const fade=(q:number,dy=25)=>({opacity:q,transform:`translateY(${(1-q)*dy*W/1080}px)`});
 const doc=<svg width="100%" height="100%" viewBox="0 0 160 190" fill="none">
  <path d="M30 13h70l33 34v126q0 9-9 9H30q-9 0-9-9V22q0-9 9-9Z" fill="#FFFFFF" stroke="#D8DFE4" strokeWidth="2"/>
  <path d="M100 13v34h33M43 80h62M43 98h62M43 116h42" stroke="#9DAFB6" strokeWidth="5" strokeLinecap="round"/>
  <rect x="43" y="139" width="44" height="9" rx="4" fill={p.theme.accent} opacity=".6"/>
 </svg>;
 return <AbsoluteFill style={{background:p.theme.paper,color:p.theme.ink,fontFamily:p.theme.font,
  backgroundImage:'radial-gradient(ellipse at 50% 35%, #FFFFFF 0%, transparent 65%)'}}>
  <div style={{position:'absolute',left:W*.09,top:H*.16,fontSize:W*.027,fontWeight:550,
   letterSpacing:W*.0015,color:'#63737F',...fade(a)}}>{p.eyebrow??''}</div>
  <div style={{position:'absolute',left:W*.09,top:H*.245,width:W*.75,height:H*.30,
   background:'#FFFFFF',borderRadius:W*.045,boxShadow:`0 ${W*.018}px ${W*.04}px rgba(30,45,56,.075)`,
   border:`${W*.001}px solid #E7EBEE`,boxSizing:'border-box',...fade(a,35)}}>
   <svg aria-hidden="true" viewBox="0 0 1000 90" preserveAspectRatio="none" style={{position:'absolute',
    left:0,bottom:-W*.023,width:'100%',height:W*.065,overflow:'visible',filter:`drop-shadow(0 ${W*.008}px ${W*.010}px rgba(30,45,56,.045))`}}>
    <path d="M0 0H1000V30Q850 15 690 35T400 37Q230 17 0 50Z" fill="#FFFFFF"/>
   </svg>
   <div style={{position:'absolute',left:W*.055,top:W*.04,fontSize:W*.027,color:p.theme.accent,fontWeight:600,...fade(b)}}>{p.number??''}</div>
   <div style={{position:'absolute',left:W*.055,top:H*.065,right:W*.045,...fade(b)}}>
    <div style={{fontSize:W*.064,fontWeight:650,lineHeight:1.12,letterSpacing:-W*.002}}>{p.title}</div>
    <div style={{fontSize:W*.031,fontWeight:450,color:'#526370',lineHeight:1.35,marginTop:W*.018,...fade(c)}}>{p.subtitle}</div>
   </div>
   {p.kind==='calendar'?<div style={{position:'absolute',left:W*.055,right:W*.055,bottom:H*.035,display:'flex',gap:W*.012}}>
    {Array.from({length:6},(_,i)=>{const q=curve(.45+i*.065,.58);return <div key={i} style={{flex:1,height:W*.062,
     borderRadius:W*.014,background:i===5?p.theme.accent:'#E9F0EE',opacity:q,
     transform:`translateY(${(1-q)*W*.018}px)`,display:'flex',alignItems:'center',justifyContent:'center',
     color:i===5?'#FFFFFF':'#567367',fontSize:W*.025,fontWeight:550}}>{i+1}</div>;})}
   </div>:p.kind==='flow'?<div style={{position:'absolute',left:W*.055,right:W*.055,bottom:H*.035,display:'flex',alignItems:'center',gap:W*.018,...fade(d)}}>
    {['Qaytish','CBP','Izoh'].map((s,i)=><React.Fragment key={s}><div style={{flex:1,background:i===1?'#E8F0ED':'#F5F7F8',borderRadius:W*.017,
     padding:`${W*.019}px 0`,textAlign:'center',fontSize:W*.027,fontWeight:550,color:i===1?p.theme.accent:'#526370'}}>{s}</div>
     {i<2?<div style={{color:'#9BADB3',fontSize:W*.026}}>→</div>:null}</React.Fragment>)}
   </div>:<div style={{position:'absolute',right:W*.055,bottom:H*.018,width:W*.15,height:W*.18,...fade(d)}}>{doc}</div>}
  </div>
  <div style={{position:'absolute',left:W*.09,top:H*.57,width:W*.75,height:1,background:'#DDE4E8',opacity:c}}/>
 </AbsoluteFill>;
};
