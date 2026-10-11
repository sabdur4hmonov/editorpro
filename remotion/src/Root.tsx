import React from 'react';
import {Composition} from 'remotion';
import {Overlay, OverlayProps} from './Overlay';
import {Timeline, TimelineProps} from './Timeline';

const demo: OverlayProps = {
  width: 1080, height: 1920, fps: 30, durationInFrames: 150,
  scenes: [
    {type: 'kinetic', from: 0, duration: 45, text: 'REJA', sub: ['avval', 'keyin', 'chiroy'], y: 0.18},
    {type: 'fold_card', from: 40, duration: 50, text: 'Tahlil', sub: '1-qadam', y: 0.6},
    {type: 'extrude', from: 90, duration: 60, text: '7', y: 0.25, x: 0.72, w: 0.4},
  ],
};

// Size, fps and length come from the props file (--props), so one composition serves every job.
export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="Overlay"
    component={Overlay as React.FC<any>}
    defaultProps={demo}
    durationInFrames={demo.durationInFrames}
    fps={demo.fps}
    width={demo.width}
    height={demo.height}
    calculateMetadata={({props}) => {
      const p = props as unknown as OverlayProps;
      return {durationInFrames: p.durationInFrames, fps: p.fps, width: p.width, height: p.height};
    }}
  />
  <Composition id="Timeline" component={Timeline as React.FC<any>}
    defaultProps={{width:1080,height:1920,fps:30,durationInFrames:90,video:'',videoFrames:90,
      font:'Inter',fallback:'Oswald',color:'#FFFFFF',accent:'#F4BE4F',safe:{},
      motion:{...{curve:'easeOutCubic',enterFrames:10,exitFrames:8,distance:36,blur:{enabled:false,intensity:0}}},
      captions:[],elements:[],transitions:[]} as TimelineProps}
    width={1080} height={1920} fps={30} durationInFrames={90}
    calculateMetadata={({props})=>{const p=props as unknown as TimelineProps;
      return {width:p.width,height:p.height,fps:p.fps,durationInFrames:p.durationInFrames};}}/>
  </>
);
