// Overlay scene library. Every scene is transparent (no background) and is placed by fractions of the frame.
// What our Python engine cannot do and these add: real CSS 3D (folds, page turns, extruded type with perspective),
// sampled motion blur (CameraMotionBlur / Trail), SVG stroke drawing, crisp spring kinetic type.
import React from 'react';
import {AbsoluteFill, Easing, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {interpolate, spring} from './motion';
import {CameraMotionBlur, Trail} from '@remotion/motion-blur';
import {evolvePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {ensureFont, SPRING, SPRING_SOFT, Theme} from './theme';

export type Base = {
  type: string;
  from: number;          // start frame (absolute, set by Overlay)
  duration: number;      // frames
  x?: number;            // centre, fraction of width
  y?: number;            // centre, fraction of height
  w?: number;            // width, fraction of width
  exit?: number;         // exit frames (default 8)
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// 0..1 exit progress over the last `exit` frames (exits faster than entrances: design rule).
const useExit = (duration: number, exit = 8) => {
  const f = useCurrentFrame();
  return interpolate(f, [duration - exit, duration], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
};

// opacity lives on the outer fill: opacity inside a preserve-3d chain flattens CSS 3D in Chrome.
const Place: React.FC<{x?: number; y?: number; w?: number; children: React.ReactNode; persp?: number; opacity?: number}> = ({x = 0.5, y = 0.4, w = 0.7, children, persp = 1400, opacity = 1}) => {
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{perspective: persp, opacity}}>
      <div style={{position: 'absolute', left: x * width - (w * width) / 2, top: y * height, width: w * width,
        transform: 'translateY(-50%)', transformStyle: 'preserve-3d'}}>{children}</div>
    </AbsoluteFill>
  );
};

const src = (file: string) => (file.startsWith('http') ? file : staticFile(file));

// ---------------------------------------------------------------- 3D fold card (s35 ticket unfold, ~16 f)
export type FoldCard = Base & {text: string; sub?: string; image?: string; hinge?: 'top' | 'left'; h?: number; color?: string; textColor?: string; size?: number};
export const FoldCardScene: React.FC<FoldCard & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  ensureFont(p.theme.font);
  const s = spring({frame: f, fps, config: SPRING, durationInFrames: 16});
  const q = useExit(p.duration, p.exit);
  const hinge = p.hinge ?? 'top';
  const ang = interpolate(s, [0, 1], [-100, 0]) + q * 95;
  const rot = hinge === 'top' ? `rotateX(${ang}deg)` : `rotateY(${-ang}deg)`;
  const shade = interpolate(Math.abs(ang), [0, 100], [0, 0.55], clamp);
  return (
    <Place x={p.x} y={p.y} w={p.w ?? 0.62}>
      <div style={{transformOrigin: hinge === 'top' ? '50% 0%' : '0% 50%', transform: rot, opacity: 1 - q * 0.6,
        borderRadius: 22, overflow: 'hidden', background: p.color ?? p.theme.paper, height: (p.h ?? 0.16) * height,
        boxShadow: `0 ${26 * (1 - shade)}px 50px rgba(0,0,0,${0.28 * (1 - shade)})`, display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center', position: 'relative', fontFamily: p.theme.font}}>
        {p.image ? <Img src={src(p.image)} style={{width: '100%', height: '62%', objectFit: 'cover'}} /> : null}
        <div style={{color: p.textColor ?? p.theme.ink, fontSize: p.size ?? 64, fontWeight: 800, textAlign: 'center', padding: '0 5%', lineHeight: 1.05}}>{p.text}</div>
        {p.sub ? <div style={{color: p.textColor ?? p.theme.ink, opacity: 0.7, fontSize: (p.size ?? 64) * 0.5, marginTop: 8}}>{p.sub}</div> : null}
        <div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, rgba(0,0,0,${shade}) 0%, rgba(0,0,0,0) 70%)`}} />
      </div>
    </Place>
  );
};

// ---------------------------------------------------------------- page turn (front -> back)
export type PageTurn = Base & {front: string; back: string; turnAt?: number; h?: number; color?: string; backColor?: string; size?: number};
export const PageTurnScene: React.FC<PageTurn & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  ensureFont(p.theme.font);
  const enter = spring({frame: f, fps, config: SPRING, durationInFrames: 12});
  const turn = spring({frame: f - (p.turnAt ?? Math.round(p.duration * 0.45)), fps, config: SPRING_SOFT, durationInFrames: 18});
  const q = useExit(p.duration, p.exit);
  const face = (text: string, bg: string, back = false) => (
    <div style={{position: 'absolute', inset: 0, backfaceVisibility: 'hidden', transform: back ? 'rotateY(180deg)' : undefined,
      background: bg, borderRadius: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
      color: p.theme.ink, fontFamily: p.theme.font, fontWeight: 800, fontSize: p.size ?? 60, padding: '0 6%', boxShadow: '0 30px 60px rgba(0,0,0,.25)'}}>{text}</div>
  );
  return (
    <Place x={p.x} y={p.y} w={p.w ?? 0.6}>
      <div style={{height: (p.h ?? 0.2) * height, position: 'relative', transformStyle: 'preserve-3d',
        transform: `translateY(${(1 - enter) * 120}px) rotateY(${turn * 180}deg) scale(${0.9 + 0.1 * enter - 0.1 * q})`, opacity: enter * (1 - q)}}>
        {face(p.front, p.color ?? p.theme.paper)}
        {face(p.back, p.backColor ?? p.theme.accent, true)}
      </div>
    </Place>
  );
};

// ---------------------------------------------------------------- extruded 3D type (s39 number, s41 behind extrusion)
export type Extrude = Base & {text: string; depth?: number; color?: string; side?: string; size?: number; tiltX?: number; tiltY?: number; font?: string};
export const ExtrudeScene: React.FC<Extrude & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const font = p.font ?? p.theme.display;
  ensureFont(font);
  const s = spring({frame: f, fps, config: SPRING, durationInFrames: 14});
  const q = useExit(p.duration, p.exit);
  const depth = p.depth ?? 26;
  const size = p.size ?? 300;
  const step = size * 0.012;
  const ry = interpolate(s, [0, 1], [70, p.tiltY ?? -30]) + noise2D('y', f / 60, 0) * 3;
  const rx = (p.tiltX ?? 14) + noise2D('x', 0, f / 60) * 2;
  const layers = Array.from({length: depth}, (_, i) => depth - 1 - i);   // back to front
  return (
    <Place x={p.x} y={p.y} w={p.w ?? 0.9} persp={1100} opacity={Math.min(1, s * 2) * (1 - q)}>
      <div style={{position: 'relative', height: size * 1.2, transformStyle: 'preserve-3d',
        transform: `rotateX(${rx}deg) rotateY(${ry}deg) scale(${0.7 + 0.3 * s})`}}>
        {layers.map((i) => (
          <div key={i} style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: font, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: -2,
            color: i === 0 ? (p.color ?? p.theme.text) : (p.side ?? '#5b4a3a'),
            transform: `translateZ(${-i * step}px)`, filter: i === 0 ? 'none' : `brightness(${0.85 - i / (depth * 2.2)})`}}>{p.text}</div>
        ))}
      </div>
    </Place>
  );
};

// ---------------------------------------------------------------- kinetic title with motion blur
export type Kinetic = Base & {text: string; sub?: string[]; color?: string; size?: number; font?: string; stagger?: number; upper?: boolean; italic?: boolean};
export const KineticScene: React.FC<Kinetic & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const font = p.font ?? p.theme.display;
  ensureFont(font); ensureFont(p.theme.font);
  const q = useExit(p.duration, p.exit);
  const letters = Array.from(p.text);
  const st = p.stagger ?? 2;
  return (
    <CameraMotionBlur shutterAngle={180} samples={6}>
      <Place x={p.x} y={p.y} w={p.w ?? 0.92}>
        <div style={{display: 'flex', justifyContent: 'center', fontFamily: font, fontWeight: 800, fontSize: p.size ?? 220,
          lineHeight: 0.95, color: p.color ?? p.theme.text, textTransform: p.upper === false ? 'none' : 'uppercase',
          fontStyle: p.italic ? 'italic' : 'normal', opacity: 1 - q}}>
          {letters.map((ch, i) => {
            const s = spring({frame: f - i * st, fps, config: SPRING, durationInFrames: 10});
            return <span key={i} style={{display: 'inline-block', whiteSpace: 'pre',
              transform: `translateY(${(1 - s) * 140 + q * -60}px) scale(${0.6 + 0.4 * s})`, opacity: s}}>{ch}</span>;
          })}
        </div>
        {p.sub?.length ? (
          <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 18, fontFamily: p.theme.font, fontSize: 46,
            color: p.color ?? p.theme.text, opacity: 0.92 * (1 - q), width: '100%'}}>
            {p.sub.map((w, i) => {
              const s = spring({frame: f - 8 - i * 5, fps, config: SPRING_SOFT, durationInFrames: 12});
              return <span key={i} style={{opacity: s, transform: `translateY(${(1 - s) * 30}px)`}}>{w}</span>;
            })}
          </div>
        ) : null}
      </Place>
    </CameraMotionBlur>
  );
};

// ---------------------------------------------------------------- hand-drawn stroke (underline / circle / arrow)
export type Draw = Base & {shape?: 'underline' | 'circle' | 'arrow'; d?: string; color?: string; stroke?: number; h?: number; drawFrames?: number};
const SHAPES: Record<string, string> = {
  underline: 'M 20 70 C 220 52, 520 86, 980 58',
  circle: 'M 520 40 C 820 30, 980 160, 900 300 C 820 430, 260 440, 120 320 C 10 220, 120 60, 560 52',
  arrow: 'M 60 300 C 300 260, 560 200, 860 80 M 860 80 L 760 90 M 860 80 L 820 170',
};
export const DrawScene: React.FC<Draw & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const q = useExit(p.duration, p.exit);
  const d = p.d ?? SHAPES[p.shape ?? 'underline'];
  const prog = interpolate(f, [0, p.drawFrames ?? 14], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const {strokeDasharray, strokeDashoffset} = evolvePath(prog, d);
  const w = (p.w ?? 0.8) * width;
  return (
    <AbsoluteFill>
      <svg viewBox="0 0 1000 450" width={w} height={(p.h ?? 0.2) * height}
        style={{position: 'absolute', left: (p.x ?? 0.5) * width - w / 2, top: (p.y ?? 0.5) * height - ((p.h ?? 0.2) * height) / 2, opacity: 1 - q}}>
        <path d={d} fill="none" stroke={p.color ?? p.theme.accent} strokeWidth={p.stroke ?? 14} strokeLinecap="round"
          strokeLinejoin="round" strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} />
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- counter
export type Counter = Base & {value: number; start?: number; prefix?: string; suffix?: string; color?: string; size?: number; decimals?: number; label?: string};
export const CounterScene: React.FC<Counter & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  ensureFont(p.theme.display); ensureFont(p.theme.font);
  const s = spring({frame: f, fps, config: SPRING_SOFT, durationInFrames: 24});
  const q = useExit(p.duration, p.exit);
  const v = (p.start ?? 0) + (p.value - (p.start ?? 0)) * s;
  return (
    <Place x={p.x} y={p.y} w={p.w ?? 0.8}>
      <div style={{textAlign: 'center', opacity: Math.min(1, s * 3) * (1 - q), transform: `scale(${0.8 + 0.2 * s})`}}>
        <div style={{fontFamily: p.theme.display, fontWeight: 800, fontSize: p.size ?? 230, color: p.color ?? p.theme.accent,
          fontVariantNumeric: 'tabular-nums', textShadow: `0 0 40px ${p.color ?? p.theme.accent}66`}}>
          {p.prefix ?? ''}{v.toFixed(p.decimals ?? 0)}{p.suffix ?? ''}
        </div>
        {p.label ? <div style={{fontFamily: p.theme.font, fontSize: 52, color: p.theme.text, marginTop: -10}}>{p.label}</div> : null}
      </div>
    </Place>
  );
};

// ---------------------------------------------------------------- object fly-in with real motion trail (s33 prop)
export type Fly = Base & {image: string; fromX?: number; fromY?: number; rotateFrom?: number; rotate?: number; enter?: number; tilt?: number};
const FlyInner: React.FC<Fly & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = spring({frame: f, fps, config: SPRING, durationInFrames: p.enter ?? 11});
  const q = useExit(p.duration, p.exit);
  const x = interpolate(s, [0, 1], [p.fromX ?? 1.3, p.x ?? 0.5]) + q * 1.2;
  const y = interpolate(s, [0, 1], [p.fromY ?? (p.y ?? 0.35) - 0.08, p.y ?? 0.35]);
  const rot = interpolate(s, [0, 1], [p.rotateFrom ?? 40, p.rotate ?? -4]) + q * 25;
  const w = (p.w ?? 0.5) * width;
  const float = Math.sin(f / fps * Math.PI * 2 / 2.4) * 0.004 * height * s;
  return (
    <AbsoluteFill style={{perspective: 1500}}>
      <Img src={src(p.image)} style={{position: 'absolute', width: w, left: x * width - w / 2, top: y * height - w / 2 + float,
        transform: `rotate(${rot}deg) rotateY(${(1 - s) * (p.tilt ?? -35)}deg)`, filter: 'drop-shadow(0 30px 40px rgba(0,0,0,.35))'}} />
    </AbsoluteFill>
  );
};
export const FlyScene: React.FC<Fly & {theme: Theme}> = (p) => (
  <Trail layers={6} lagInFrames={0.6} trailOpacity={0.6}><FlyInner {...p} /></Trail>
);

import {Box3DScene} from './three_scenes';

export const SCENES: Record<string, React.FC<any>> = {
  box3d: Box3DScene,
  fold_card: FoldCardScene, page_turn: PageTurnScene, extrude: ExtrudeScene, kinetic: KineticScene,
  draw: DrawScene, counter: CounterScene, fly: FlyScene,
};

// ---------------------------------------------------------------- light leak over a cut (cinematic formats)
import {lightLeak} from '@remotion/effects/light-leak';
import {Solid} from 'remotion';
export type Leak = Base & {seed?: number; hueShift?: number};
export const LightLeakScene: React.FC<Leak & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return <Solid width={width} height={height}
    effects={[lightLeak({seed: p.seed ?? 0, hueShift: p.hueShift ?? 0,
      progress: interpolate(f, [0, p.duration - 1], [0, 1], clamp)})]} />;
};
SCENES.light_leak = LightLeakScene;

// editorial scenes (Nilem references 44/47)
import {BehindWordScene, CardWallScene, CtaScene, EndGridScene, PillsScene, PriceCardScene, ReliefScene, SheetsScene} from './editorial';
Object.assign(SCENES, {card_wall: CardWallScene, pills: PillsScene, relief: ReliefScene, sheets: SheetsScene,
  price_card: PriceCardScene, cta: CtaScene, end_grid: EndGridScene, behind_word: BehindWordScene});
