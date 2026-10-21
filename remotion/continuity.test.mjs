import test from 'node:test';
import assert from 'node:assert/strict';
import {minimumJerk,settledSpring,progress,stateAt,validateStates} from './src/continuity.mjs';
const base={at:0,duration:0,x:.5,y:.7,w:.6,h:.16,radius:.03,rotate:0,opacity:0,title:'A'};
const states=[base,{...base,at:.2,duration:.6,w:.8,opacity:1,title:'B'},
 {...base,at:2,duration:.4,w:.8,h:.08,opacity:1,title:'C'}];
test('rest-to-rest curves have exact endpoints and near-zero terminal velocity',()=>{
 for(const fn of [minimumJerk,settledSpring]){
  assert.equal(fn(-1),0);assert.equal(fn(0),0);assert.equal(fn(1),1);assert.equal(fn(2),1);
  const e=1e-5;assert.ok(Math.abs((fn(1)-fn(1-e))/e)<1e-5);
  assert.ok(Math.abs((fn(e)-fn(0))/e)<.001);
 }
});
test('all physical damping regimes settle without NaN or cutoff',()=>{
 for(const damping of [12,2*Math.sqrt(180),45]){
  for(let i=0;i<=1000;i++)assert.ok(Number.isFinite(settledSpring(i/1000,{damping})));
  assert.ok(Math.abs(1-settledSpring(.99999,{damping}))<1e-8);
 }
});
test('state boundaries and holds preserve position, dimensions, content clock',()=>{
 validateStates(states);
 assert.equal(stateAt(.1,states).box.opacity,0);
 assert.equal(stateAt(.2,states).box.w,.6);
 assert.equal(stateAt(.8,states).box.w,.8);
 assert.equal(stateAt(1.5,states).box.w,.8);
 assert.deepEqual(stateAt(2-1e-9,states).box,stateAt(2,states).box);
 assert.equal(stateAt(2,states).mix,0);assert.equal(stateAt(2.4,states).mix,1);
});
test('fractional geometry and fps-independent wall-clock timing',()=>{
 for(const fps of [25,30,60]){
  const p=stateAt(.4*fps/fps,states);assert.ok(p.box.w>.6&&p.box.w<.8);
  assert.notEqual(p.box.w*1080,Math.round(p.box.w*1080));
  for(let f=0;f<3*fps;f++){const b=stateAt(f/fps,states).box;assert.ok(b.w>0&&b.h>0&&b.opacity>=0&&b.opacity<=1);}
 }
});
test('invalid clocks, curves and overlapping states fail loudly',()=>{
 assert.throws(()=>progress(0,0,0));assert.throws(()=>progress(0,0,1,'linear'));
 assert.throws(()=>settledSpring(.5,{mass:0}));assert.throws(()=>stateAt(NaN,states));
 assert.throws(()=>validateStates([base,{...base,at:1,duration:.5},{...base,at:1.2,duration:.5}]));
 assert.throws(()=>validateStates([base,{...base,at:1,duration:1,w:-1}]));
});
