// Adapter for reusable overlay scenes: an omitted easing can no longer create linear motion.
import {interpolate as remotionInterpolate, spring as remotionSpring} from 'remotion';
import {easeOutCubic} from './easing.mjs';
export const interpolate=(input:number,inputRange:readonly number[],outputRange:readonly number[],options?:Parameters<typeof remotionInterpolate>[3])=>
  remotionInterpolate(input,inputRange,outputRange,{easing:easeOutCubic,...options});
export const spring:typeof remotionSpring=(options)=>remotionSpring(options);
