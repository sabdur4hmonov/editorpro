// Opt-in, deterministic motion for persistent objects. Legacy easing stays untouched.
export const minimumJerk = (t) => {
  const p = Math.max(0, Math.min(1, t));
  return p * p * p * (10 + p * (-15 + 6 * p));
};

// Physical response, then a C2 blend to rest. Unlike end-value normalization,
// this arrives with zero velocity; it never cuts a moving spring off at p=1.
export function settledSpring(t, {damping = 22, stiffness = 180, mass = 1, seconds = .65} = {}) {
  if (![t,damping,stiffness,mass,seconds].every(Number.isFinite) ||
      Math.min(damping,stiffness,mass,seconds) <= 0) throw Error('Invalid spring parameters');
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const w = Math.sqrt(stiffness / mass), z = damping / (2 * Math.sqrt(stiffness * mass));
  const s = t * seconds;
  let y;
  if (Math.abs(z - 1) < 1e-6) y = 1 - Math.exp(-w*s) * (1+w*s);
  else if (z < 1) {
    const wd = w * Math.sqrt(1-z*z);
    y = 1 - Math.exp(-z*w*s) * (Math.cos(wd*s)+z*w/wd*Math.sin(wd*s));
  } else {
    const a=-w*(z-Math.sqrt(z*z-1)), b=-w*(z+Math.sqrt(z*z-1));
    y=1-(b*Math.exp(a*s)-a*Math.exp(b*s))/(b-a);
  }
  return y + (1-y)*minimumJerk((t-.7)/.3);
}

export const CONTINUITY_PRESETS = {
  editorial: {curve:'minimumJerk', duration:.48, stagger:.08, exit:.32},
  soft: {curve:'minimumJerk', duration:.60, stagger:.10, exit:.40},
  tactile: {curve:'settledSpring', duration:.65, stagger:.07, exit:.36},
};

export function progress(time, start, duration, curve='minimumJerk', spring={}) {
  if (![time,start,duration].every(Number.isFinite) || duration<=0) throw Error('Invalid motion clock');
  if (!['minimumJerk','settledSpring'].includes(curve)) throw Error(`Unknown continuity curve: ${curve}`);
  if (time<=start) return 0;
  if (time>=start+duration) return 1;
  const p=(time-start)/duration;
  if (curve==='minimumJerk') return minimumJerk(p);
  if (curve==='settledSpring') return settledSpring(p,{...spring,seconds:duration});
  throw Error(`Unknown continuity curve: ${curve}`);
}

const KEYS=['x','y','w','h','radius','rotate','opacity'];
export function validateStates(states) {
  if (!Array.isArray(states) || states.length<2) throw Error('At least two states required');
  states.forEach((s,i)=>{
    if (!Number.isFinite(s.at) || s.at<0 || !Number.isFinite(s.duration) || s.duration<0 ||
        (i>0 && (s.duration<=0 || s.at<states[i-1].at+states[i-1].duration)))
      throw Error('States must be ordered, non-overlapping, with positive travel duration');
    if (KEYS.some(k=>!Number.isFinite(s[k])) || s.w<=0 || s.h<=0 || s.radius<0 || s.opacity<0 || s.opacity>1)
      throw Error('Invalid state geometry');
    if (i>0 && !['minimumJerk','settledSpring'].includes(s.curve??'minimumJerk')) throw Error('Unknown state curve');
  });
}

// One clock for size, centre, corner radius, rotation, opacity and content handoff.
// Coordinates remain fractional. Text itself is never stretched with the card.
export function stateAt(time, states) {
  if (!Number.isFinite(time)) throw Error('Invalid sample time');
  let index=0;
  for(let i=1;i<states.length;i++) if(time>=states[i].at) index=i;
  const to=states[index], from=states[Math.max(0,index-1)];
  const p=index===0?1:progress(time,to.at,to.duration,to.curve??'minimumJerk',to.spring);
  const box=Object.fromEntries(KEYS.map(k=>[k,from[k]+(to[k]-from[k])*p]));
  // Opacity cannot overshoot even when geometry has a spring.
  box.opacity=Math.max(0,Math.min(1,box.opacity));
  return {box,from,to,index,mix:Math.max(0,Math.min(1,p))};
}
