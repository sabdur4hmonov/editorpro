import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {SCENES} from './scenes';
import {DEFAULT_THEME, Theme} from './theme';

export type OverlayProps = {
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  theme?: Partial<Theme>;
  scenes: Array<Record<string, any> & {type: string; from: number; duration: number}>;
};

// One transparent composition; each scene is a Sequence at its own frame. No background -> alpha output.
export const Overlay: React.FC<OverlayProps> = ({scenes, theme}) => {
  const t = {...DEFAULT_THEME, ...(theme ?? {})};
  return (
    <AbsoluteFill>
      {scenes.map((s, i) => {
        const Scene = SCENES[s.type];
        if (!Scene) throw new Error(`Unknown scene type: ${s.type}. Known: ${Object.keys(SCENES).join(', ')}`);
        return (
          <Sequence key={i} from={s.from} durationInFrames={s.duration} layout="none">
            <Scene {...s} theme={t} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
