// Editorial scenes measured on the Nilem references (samples 44 and 47, docs/STYLE_STUDY/nilem_43_47.md and
// temp/style_study/review_claude/n44_open_a.jpg, n47_detail.jpg). Generic: every text, image and time comes from props.
import React from 'react';
import {AbsoluteFill, Easing, Img, OffthreadVideo, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {interpolate, spring} from './motion';
import {Trail} from '@remotion/motion-blur';
import {evolvePath} from '@remotion/paths';
import {ensureFont, Theme} from './theme';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const src = (f: string) => (f.startsWith('http') ? f : staticFile(f));
const ease = Easing.bezier(0.22, 1, 0.36, 1);          // smooth, no bounce (user: "smooth", no overshoot)
const SMOOTH = {damping: 200, mass: 0.8, stiffness: 120};

// ---------------------------------------------------------------- letter scatter (s44 0.00-0.33, 3.00-3.50)
// Letters appear in a seeded random order, ~1 frame apart, each flickering in over 2 frames.
export const Scatter: React.FC<{text: string; at: number; step?: number; style: React.CSSProperties; seed?: string; out?: number}> = ({text, at, step = 1, style, seed = 's', out}) => {
  const f = useCurrentFrame();
  const chars = Array.from(text);
  const order = chars.map((_, i) => i).sort((a, b) => random(`${seed}${a}`) - random(`${seed}${b}`));
  const rank: number[] = [];
  order.forEach((idx, r) => (rank[idx] = r));
  const fade = out === undefined ? 1 : interpolate(f, [out, out + 6], [1, 0], clamp);
  return (
    <span style={{...style, display: 'inline-block', whiteSpace: 'pre', opacity: fade}}>
      {chars.map((c, i) => {
        const t = f - at - rank[i] * step;
        const o = t < 0 ? 0 : t < 1 ? 0.35 : t < 2 ? 0.75 : 1;
        return <span key={i} style={{opacity: o}}>{c}</span>;
      })}
    </span>
  );
};

// ---------------------------------------------------------------- s44 hook: speaker card shrinks into a portfolio wall
export type CardWall = {type: string; from: number; duration: number; video: string; videoStartSec?: number;
  tiles: string[]; bg?: string; label?: string; title?: string; sub?: string; hookWord?: string; hookSub?: string;
  shrinkAt: number; shrinkEnd: number; growAt: number; growEnd: number; titleAt: number; subAt: number; cardScale?: number};
export const CardWallScene: React.FC<CardWall & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  ['Montserrat', 'Oswald', 'Inter'].forEach(ensureFont);
  const shrink = interpolate(f, [p.shrinkAt, p.shrinkEnd], [0, 1], {...clamp, easing: ease});
  const grow = interpolate(f, [p.growAt, p.growEnd], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const k = shrink * (1 - grow);                                    // 0 = full frame, 1 = small card
  const scale = 1 - (1 - (p.cardScale ?? 0.36)) * k;
  const border = 14 * Math.min(1, k * 4);
  const radius = 34 * Math.min(1, k * 3);
  const cardY = H * 0.58 * k + H * 0.5 * (1 - k);                  // card centre moves slightly down
  const cols = 3, rows = 4, gap = 22;
  const top0 = p.title ? H * 0.235 : H * 0.04;
  const tw = (W - gap * (cols + 1)) / cols, th = (H * 0.98 - top0 - gap * (rows + 1)) / rows;
  const drift = interpolate(f, [p.shrinkAt, p.growAt], [0, -60], clamp);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: p.bg ?? '#7A0E14', opacity: Math.min(1, k * 3)}}>
        {p.tiles.slice(0, cols * rows).map((t, i) => {
          const r = Math.floor(i / cols), c = i % cols;
          const s = spring({frame: f - p.shrinkAt - (r + c) * 2, fps, config: SMOOTH, durationInFrames: 14});
          return <div key={i} style={{position: 'absolute', left: gap + c * (tw + gap), top: top0 + gap + r * (th + gap) + drift * (c % 2 ? 1 : 0.6),
            width: tw, height: th, borderRadius: 14, overflow: 'hidden', opacity: s, transform: `scale(${0.9 + 0.1 * s})`,
            background: '#EDE8E1'}}><Img src={src(t)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /></div>;
        })}
      </AbsoluteFill>
      {/* speaker card */}
      <div style={{position: 'absolute', left: W / 2 - (W * scale) / 2, top: cardY - (H * scale) / 2, width: W * scale, height: H * scale,
        borderRadius: radius, overflow: 'hidden', background: '#fff', padding: border, boxSizing: 'border-box'}}>
        <div style={{width: '100%', height: `calc(100% - ${k * 70}px)`, borderRadius: Math.max(0, radius - 8), overflow: 'hidden', position: 'relative'}}>
          <OffthreadVideo src={src(p.video)} muted startFrom={Math.round((p.videoStartSec ?? 0) * fps)}
            style={{width: W, height: H, transform: `scale(${(W * scale - 2 * border) / W})`, transformOrigin: '0 0', position: 'absolute', left: 0, top: 0}} />
          {p.hookWord ? (
            <div style={{position: 'absolute', left: 0, right: 0, top: '49%', textAlign: 'center', transform: `scale(${scale})`, transformOrigin: '50% 0%'}}>
              <Scatter text={p.hookWord} at={0} step={1} seed="hook" style={{fontFamily: 'Montserrat', fontWeight: 700, fontSize: 118, color: p.theme.ink, letterSpacing: 2}} />
              <div><Scatter text={p.hookSub ?? ''} at={6} step={1} seed="hooksub" style={{fontFamily: 'Inter', fontWeight: 500, fontSize: 46, color: p.theme.ink}} /></div>
            </div>
          ) : null}
        </div>
        {p.label ? <div style={{height: k * 70, overflow: 'hidden', textAlign: 'center', fontFamily: 'Inter', fontWeight: 500, fontSize: 40,
          color: '#2a2a2a', lineHeight: '64px', opacity: k}}>{p.label}</div> : null}
      </div>
      {/* title on the wall */}
      {p.title ? (
        <div style={{position: 'absolute', top: H * 0.07, left: 0, right: 0, textAlign: 'center', opacity: 1 - grow}}>
          <Scatter text={p.title} at={p.titleAt} step={1} seed="title" style={{fontFamily: 'Oswald', fontWeight: 700, fontSize: 150, color: '#fff', letterSpacing: 1}} />
          {p.sub ? <div><Scatter text={p.sub} at={p.subAt} step={1} seed="tsub" style={{fontFamily: 'Inter', fontWeight: 500, fontSize: 54, color: '#fff'}} /></div> : null}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- s47 dark pills that stack (17.0-18.7)
export type Pills = {type: string; from: number; duration: number; items: Array<{at: number; text: string; icon?: string}>;
  x?: number; y?: number; gap?: number; size?: number; exit?: number};
export const PillsScene: React.FC<Pills & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  ensureFont('Inter');
  const size = p.size ?? 52;
  const exit = interpolate(f, [p.duration - (p.exit ?? 7), p.duration], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  return (
    <AbsoluteFill>
      {p.items.map((it, i) => {
        const t = f - it.at;
        if (t < 0) return null;
        const e = interpolate(t, [0, 6], [0, 1], {...clamp, easing: ease});
        const blur = (1 - e) * 10;
        return (
          <div key={i} style={{position: 'absolute', left: (p.x ?? 0.5) * W, top: (p.y ?? 0.42) * H + i * (p.gap ?? 0.058) * H,
            transform: `translate(-50%, -50%) translateX(${(1 - e) * 90 - exit * 120}px) scale(${0.92 + 0.08 * e})`,
            opacity: e * (1 - exit), filter: `blur(${blur}px)`, display: 'flex', alignItems: 'center', gap: 18,
            background: 'rgba(20,21,24,0.9)', borderRadius: 999, padding: `${size * 0.32}px ${size * 0.6}px`,
            color: '#fff', fontFamily: 'Inter', fontWeight: 600, fontSize: size, whiteSpace: 'nowrap'}}>
            <span>{it.text}</span>
            {it.icon ? <Img src={src(it.icon)} style={{width: size * 1.05, height: size * 1.05}} /> : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- s47 relief words that fly in (MEBEL 7.0-7.4, RAZVETKA 8.6-9.0)
export type Relief = {type: string; from: number; duration: number;
  words: Array<{at: number; text: string; from?: 'left' | 'right' | 'bottom'; exitAt?: number; y?: number}>;
  helpers?: Array<{at: number; text: string; x?: number; y?: number}>; checkAt?: number; checkX?: number; checkY?: number;
  front?: string; side?: string; size?: number; depth?: number};
const ReliefWord: React.FC<{w: Relief['words'][number]; p: Relief}> = ({w, p}) => {
  const f = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  const t = f - w.at;
  const s = spring({frame: t, fps, config: {damping: 22, mass: 0.8, stiffness: 150}, durationInFrames: 11});
  const out = w.exitAt === undefined ? 0 : interpolate(f, [w.exitAt, w.exitAt + 7], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  if (t < 0 || out >= 1) return null;
  const dir = w.from ?? 'left';
  const sx = dir === 'left' ? -0.75 : dir === 'right' ? 0.75 : 0.25;
  const sy = dir === 'bottom' ? 0.35 : 0.06;
  const x = interpolate(s, [0, 1], [sx, 0]) - out * 0.45;
  const y = interpolate(s, [0, 1], [sy, 0]) + out * 0.25;
  const ry = interpolate(s, [0, 1], [dir === 'right' ? -70 : 70, -14]);
  const rz = interpolate(s, [0, 1], [dir === 'bottom' ? -18 : 10, -4]) - out * 12;
  const depth = p.depth ?? 22, size = p.size ?? 190;
  const step = size * 0.011;
  return (
    <AbsoluteFill style={{perspective: 1200, opacity: Math.min(1, s * 3) * (1 - out)}}>
      <div style={{position: 'absolute', left: W * (0.5 + x), top: H * ((w.y ?? 0.47) + y), transform: 'translate(-50%, -50%)', transformStyle: 'preserve-3d'}}>
        <div style={{position: 'relative', transformStyle: 'preserve-3d', transform: `rotateX(16deg) rotateY(${ry}deg) rotateZ(${rz}deg)`}}>
          {Array.from({length: depth}, (_, i) => depth - 1 - i).map((i) => (
            <div key={i} style={{position: i === 0 ? 'relative' : 'absolute', left: 0, top: 0, fontFamily: 'Montserrat', fontWeight: 800,
              fontSize: size, lineHeight: 1, letterSpacing: -2, whiteSpace: 'nowrap', transform: `translateZ(${-i * step}px)`,
              color: i === 0 ? (p.front ?? '#61656C') : (p.side ?? '#2F3136'), filter: i === 0 ? 'none' : `brightness(${1 - i / (depth * 2.4)})`}}>{w.text}</div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
export const ReliefScene: React.FC<Relief & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  ensureFont('Montserrat'); ensureFont('Inter');
  const end = interpolate(f, [p.duration - 7, p.duration], [1, 0], clamp);
  const check = 'M 40 120 L 110 190 L 260 30';
  const cp = p.checkAt === undefined ? 0 : interpolate(f, [p.checkAt, p.checkAt + 9], [0, 1], {...clamp, easing: ease});
  const {strokeDasharray, strokeDashoffset} = evolvePath(cp, check);
  return (
    <AbsoluteFill style={{opacity: end}}>
      {p.words.map((w, i) => <Trail key={i} layers={5} lagInFrames={0.5} trailOpacity={0.5}><ReliefWord w={w} p={p} /></Trail>)}
      {(p.helpers ?? []).map((h, i) => {
        const e = interpolate(f, [h.at, h.at + 6], [0, 1], {...clamp, easing: ease});
        return <div key={i} style={{position: 'absolute', left: (h.x ?? 0.5) * W, top: (h.y ?? 0.56) * H, transform: `translate(-50%, -50%) translateX(${(1 - e) * 40}px)`,
          opacity: e, fontFamily: 'Inter', fontWeight: 500, fontSize: 54, color: '#55595F', whiteSpace: 'nowrap'}}>{h.text}</div>;
      })}
      {p.checkAt !== undefined ? (
        <svg viewBox="0 0 300 220" width={170} height={125} style={{position: 'absolute', left: (p.checkX ?? 0.78) * W - 85, top: (p.checkY ?? 0.55) * H - 62}}>
          <path d={check} fill="none" stroke="#D3202C" strokeWidth={30} strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} />
        </svg>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- s44 red scene: drawings land as a stack + scatter title + brand pill
export type Sheets = {type: string; from: number; duration: number; images: string[]; bg?: string; title?: string; titleAt?: number;
  pill?: string; pillAt?: number; dropEvery?: number; inFrames?: number; outFrames?: number};
export const SheetsScene: React.FC<Sheets & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  ensureFont('Oswald'); ensureFont('Inter');
  const inF = p.inFrames ?? 7, outF = p.outFrames ?? 7;
  const wipeIn = interpolate(f, [0, inF], [1, 0], {...clamp, easing: ease});
  const wipeOut = interpolate(f, [p.duration - outF, p.duration], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const every = p.dropEvery ?? 7;
  const rots = [-8, 6, -3, 9, -5, 4];
  return (
    <AbsoluteFill style={{transform: `translateY(${(wipeIn + wipeOut) * 100}%)`, background: p.bg ?? '#7A0E14', overflow: 'hidden'}}>
      {p.images.map((im, i) => {
        const s = spring({frame: f - 4 - i * every, fps, config: {damping: 18, mass: 0.9, stiffness: 120}, durationInFrames: 14});
        if (f - 4 - i * every < 0) return null;
        const off = [[-0.07, -0.06], [0.08, -0.01], [-0.05, 0.05], [0.06, 0.09], [0, 0.02], [0.03, -0.04]][i % 6];
        return <div key={i} style={{position: 'absolute', left: W * (0.5 + off[0]), top: H * (0.52 + off[1]), width: W * 0.7, height: W * 0.49,
          transform: `translate(-50%, -50%) translateY(${(1 - s) * -H * 0.45}px) rotate(${rots[i % rots.length] * (0.4 + 0.6 * s)}deg) scale(${1.08 - 0.08 * s})`,
          background: '#fff', padding: 12, borderRadius: 10, boxShadow: '0 18px 40px rgba(60,0,0,0.35)'}}>
          <Img src={src(im)} style={{width: '100%', height: '100%', objectFit: 'cover', borderRadius: 4}} /></div>;
      })}
      {p.title ? <div style={{position: 'absolute', top: H * 0.1, width: '100%', textAlign: 'center'}}>
        <Scatter text={p.title} at={p.titleAt ?? 6} step={1} seed="sheets" style={{fontFamily: 'Oswald', fontWeight: 700, fontSize: 150, lineHeight: 1.0, color: '#fff'}} /></div> : null}
      {p.pill ? (() => {
        const e = interpolate(f, [p.pillAt ?? 20, (p.pillAt ?? 20) + 8], [0, 1], {...clamp, easing: ease});
        return <div style={{position: 'absolute', top: H * 0.83, left: '50%', transform: `translate(-50%, -50%) scale(${0.9 + 0.1 * e})`, opacity: e,
          background: '#D3202C', border: '5px solid #fff', borderRadius: 999, padding: '18px 54px', color: '#fff', fontFamily: 'Inter',
          fontWeight: 800, fontSize: 50, letterSpacing: 1, whiteSpace: 'nowrap'}}>{p.pill}</div>;
      })() : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- photo card + price (s44 card language)
export type PriceCard = {type: string; from: number; duration: number; image: string; label?: string; x?: number; y?: number; w?: number;
  priceAt?: number; value: number; prefix?: string; suffix?: string; unit?: string};
export const PriceCardScene: React.FC<PriceCard & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  ensureFont('Oswald'); ensureFont('Inter');
  const e = interpolate(f, [0, 9], [0, 1], {...clamp, easing: ease});
  const out = interpolate(f, [p.duration - 7, p.duration], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const w = (p.w ?? 0.5) * W;
  const s = spring({frame: f - (p.priceAt ?? 20), fps, config: SMOOTH, durationInFrames: 18});
  const v = Math.round(p.value * s);
  return (
    <AbsoluteFill style={{opacity: 1 - out}}>
      <div style={{position: 'absolute', left: (p.x ?? 0.7) * W - w / 2, top: (p.y ?? 0.62) * H - w * 0.7,
        width: w, transform: `translateX(${(1 - e) * 110}px) rotate(${(1 - e) * 4 + 2}deg)`, opacity: e,
        background: '#fff', padding: 12, borderRadius: 26}}>
        <div style={{width: '100%', height: w * 1.05, borderRadius: 18, overflow: 'hidden'}}>
          <Img src={src(p.image)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.08 - 0.08 * (f / p.duration)})`}} /></div>
        {p.label ? <div style={{textAlign: 'center', fontFamily: 'Inter', fontWeight: 500, fontSize: 38, color: '#2a2a2a', padding: '14px 0 6px'}}>{p.label}</div> : null}
        {f >= (p.priceAt ?? 20) ? (
          <div style={{position: 'absolute', left: -w * 0.2, top: -w * 0.16, background: '#D3202C', color: '#fff', borderRadius: 22,
            padding: '10px 30px 14px', fontFamily: 'Oswald', fontWeight: 700, transform: `scale(${0.7 + 0.3 * s}) rotate(-4deg)`, opacity: Math.min(1, s * 2)}}>
            <div style={{fontSize: 120, lineHeight: 1}}>{p.prefix ?? ''}{v}{p.suffix ?? ''}</div>
            {p.unit ? <div style={{fontFamily: 'Inter', fontWeight: 600, fontSize: 40, marginTop: 2}}>{p.unit}</div> : null}
          </div>) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- CTA pill with ringing icon
export type Cta = {type: string; from: number; duration: number; text: string; icon?: string; sub?: string; subAt?: number; y?: number};
export const CtaScene: React.FC<Cta & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  ensureFont('Inter');
  const e = interpolate(f, [0, 7], [0, 1], {...clamp, easing: ease});
  const out = interpolate(f, [p.duration - 5, p.duration], [0, 1], clamp);
  const ring = Math.sin(f * 1.6) * 14 * (Math.floor(f / 12) % 2 === 0 ? 1 : 0.15);
  const se = interpolate(f, [p.subAt ?? 18, (p.subAt ?? 18) + 7], [0, 1], {...clamp, easing: ease});
  return (
    <AbsoluteFill style={{opacity: 1 - out}}>
      <div style={{position: 'absolute', left: W / 2, top: (p.y ?? 0.44) * H, transform: `translate(-50%, -50%) translateX(${(1 - e) * 100}px)`,
        opacity: e, filter: `blur(${(1 - e) * 10}px)`, display: 'flex', alignItems: 'center', gap: 22, background: '#D3202C',
        borderRadius: 999, padding: '22px 46px', color: '#fff', fontFamily: 'Inter', fontWeight: 800, fontSize: 56, whiteSpace: 'nowrap'}}>
        {p.icon ? <Img src={src(p.icon)} style={{width: 66, height: 66, transform: `rotate(${ring}deg)`}} /> : null}
        <span>{p.text}</span>
      </div>
      {p.sub ? <div style={{position: 'absolute', left: W / 2, top: (p.y ?? 0.44) * H + 100, transform: `translate(-50%, 0) translateX(${(1 - se) * 60}px)`,
        opacity: se, background: 'rgba(20,21,24,0.9)', borderRadius: 999, padding: '14px 34px', color: '#fff', fontFamily: 'Inter', fontWeight: 500,
        fontSize: 44, whiteSpace: 'nowrap'}}>{p.sub}</div> : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- s47 end: white liquid wipe -> grid paper -> stacked brand words
export type EndGrid = {type: string; from: number; duration: number; words: string[]; tagline?: string; handle?: string; wipe?: number; every?: number};
export const EndGridScene: React.FC<EndGrid & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  ensureFont('Inter');
  const wipe = p.wipe ?? 9;
  const c = interpolate(f, [0, wipe], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  // two curved white fronts closing from the sides (s47 35.76-36.08)
  const r = W * (0.1 + 1.2 * c);
  const path = `M 0 0 L ${r * 0.55} 0 Q ${r} ${H / 2} ${r * 0.55} ${H} L 0 ${H} Z M ${W} 0 L ${W - r * 0.55} 0 Q ${W - r} ${H / 2} ${W - r * 0.55} ${H} L ${W} ${H} Z`;
  const every = p.every ?? 5;
  const base = wipe + 3;
  return (
    <AbsoluteFill>
      {c < 1 ? <svg width={W} height={H} style={{position: 'absolute'}}><path d={path} fill="#F7F5F1" /></svg> : null}
      {c >= 1 ? (
        <AbsoluteFill style={{background: '#F7F5F1', backgroundImage: 'linear-gradient(#E3DED6 1.5px, transparent 1.5px), linear-gradient(90deg, #E3DED6 1.5px, transparent 1.5px)',
          backgroundSize: '54px 54px'}}>
          <div style={{position: 'absolute', left: W * 0.14, top: H * 0.36}}>
            {p.words.map((w, i) => {
              const t = f - base - i * every;
              const e = interpolate(t, [0, 5], [0, 1], {...clamp, easing: ease});
              const col = interpolate(t, [0, 8], [150, 26], clamp);
              return <div key={i} style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 150, lineHeight: 0.98, letterSpacing: -4,
                color: `rgb(${col},${col},${col})`, opacity: e, transform: `translateY(${(1 - e) * 24}px)`}}>{w}</div>;
            })}
            {p.tagline ? (() => {
              const e = interpolate(f, [base + p.words.length * every + 4, base + p.words.length * every + 10], [0, 1], {...clamp, easing: ease});
              return <div style={{fontFamily: 'Inter', fontWeight: 500, fontSize: 50, color: '#3a3a3a', marginTop: 18, opacity: e}}>{p.tagline}</div>;
            })() : null}
          </div>
          {p.handle ? <div style={{position: 'absolute', bottom: H * 0.2, width: '100%', textAlign: 'center', fontFamily: 'Inter', fontWeight: 600,
            fontSize: 44, color: '#D3202C', opacity: interpolate(f, [base + 18, base + 26], [0, 1], clamp)}}>{p.handle}</div> : null}
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- s47 0.36-0.84: giant stacked word BEHIND the person
// The person is put back on top from per-frame cut-outs (PPHumanSeg alpha from scripts/person_mask.py), so the word
// sits behind the head and body. Cut-out pixels equal the video pixels, so the overlay is seamless.
export type BehindWord = {type: string; from: number; duration: number; text: string; lines?: number; cutouts: string[];
  y?: number; size?: number; colors?: string[]; appear?: number; font?: string};
export const BehindWordScene: React.FC<BehindWord & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const font = p.font ?? 'Oswald';
  ensureFont(font);
  const n = p.lines ?? 3;
  const size = p.size ?? 330;
  const cols = p.colors ?? ['rgba(240,232,224,0.92)', 'rgba(240,232,224,0.55)', 'rgba(240,232,224,0.28)'];
  const e = interpolate(f, [p.appear ?? 0, (p.appear ?? 0) + 3], [0, 1], clamp);
  const out = interpolate(f, [p.duration - 6, p.duration], [0, 1], clamp);
  const cut = p.cutouts[Math.min(p.cutouts.length - 1, f)];
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', top: (p.y ?? 0.035) * H, width: '100%', textAlign: 'center', opacity: e * (1 - out)}}>
        {Array.from({length: n}, (_, i) => (
          <div key={i} style={{fontFamily: font, fontWeight: 700, fontSize: size, lineHeight: 0.86, color: cols[i % cols.length],
            letterSpacing: -2, transform: `translateY(${(1 - e) * 20}px)`}}>{p.text}</div>
        ))}
      </div>
      {e * (1 - out) > 0 ? <Img src={src(cut)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} /> : null}
    </AbsoluteFill>
  );
};
