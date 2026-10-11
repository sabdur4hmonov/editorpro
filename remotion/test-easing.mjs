import {strict as assert} from 'node:assert';
import {CURVES,eased,lerp} from './src/easing.mjs';
for(const [name,fn] of Object.entries(CURVES)) {
  assert(Math.abs(fn(0))<1e-9,name); assert(Math.abs(fn(1)-1)<1e-9,name);
  for(let i=0;i<=100;i++) assert(Number.isFinite(fn(i/100)),name);
}
assert(lerp(0,11,.13)%1!==0,'subpixel motion must remain fractional');
assert(eased(.8,'easeOutBack')>1,'overshoot preserved');
assert.throws(()=>eased(.4,'linear'),/Unknown easing/);
assert.throws(()=>eased(.4,'spring',{damping:-1}),/Positive/);
console.log('EASING: 7 curves; endpoints, finite range, subpixel, overshoot and invalid config OK');
