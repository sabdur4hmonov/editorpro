// WebGL 3D (Three.js via @remotion/three). Renders on CPU with --gl=angle/swangle; keep scenes small.
import React from 'react';
import {ThreeCanvas} from '@remotion/three';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {interpolate, spring} from './motion';
import {useThree} from '@react-three/fiber';
import {SPRING, Theme} from './theme';

// R3F sometimes keeps its default camera aspect in headless renders; set it from the canvas size every frame.
const CameraFix: React.FC = () => {
  const {camera, size} = useThree();
  const cam = camera as any;
  cam.fov = 30; cam.aspect = size.width / size.height; cam.position.set(0, 0, 6); cam.lookAt(0, 0, 0);
  cam.updateProjectionMatrix();
  return null;
};

export type Box3D = {type: string; from: number; duration: number; color?: string; size?: [number, number, number];
  rotateFrom?: [number, number, number]; rotate?: [number, number, number]; x?: number; y?: number; scale?: number; exit?: number};

export const Box3DScene: React.FC<Box3D & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = spring({frame: f, fps, config: SPRING, durationInFrames: 14});
  const q = interpolate(f, [p.duration - (p.exit ?? 8), p.duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const r0 = p.rotateFrom ?? [0.9, -1.6, 0.3];
  const r1 = p.rotate ?? [0.35, -0.55, 0.05];
  const rot = r0.map((a, i) => a + (r1[i] - a) * s + q * 1.2) as [number, number, number];
  const sz = p.size ?? [1.6, 2.2, 0.25];
  // frame fractions -> world units (camera z=6, fov 30: visible height ~3.2 units)
  const vh = 2 * 6 * Math.tan((30 * Math.PI) / 360);
  const wx = ((p.x ?? 0.5) - 0.5) * vh * (width / height);
  const wy = (0.5 - (p.y ?? 0.4)) * vh;
  const sc = (p.scale ?? 1) * (0.6 + 0.4 * s) * (1 - 0.3 * q);
  return (
    <ThreeCanvas width={width} height={height} camera={{fov: 30, position: [0, 0, 6], near: 0.1, far: 100}}>
      <CameraFix />
      <ambientLight intensity={0.55} />
      <directionalLight position={[3, 4, 5]} intensity={1.2} />
      <directionalLight position={[-4, -2, 2]} intensity={0.35} />
      <mesh position={[wx, wy, 0]} rotation={rot} scale={[sc, sc, sc]}>
        <boxGeometry args={sz} />
        <meshStandardMaterial color={p.color ?? p.theme.accent} roughness={0.45} metalness={0.05} transparent opacity={1 - q} />
      </mesh>
    </ThreeCanvas>
  );
};
