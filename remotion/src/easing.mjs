// Shared normalized curves. Coordinates remain floating point; only timeline frames are quantized.
export const clamp = (p) => Math.max(0, Math.min(1, p));
export const easeOutCubic = (p) => 1 - (1 - clamp(p)) ** 3;
export const easeInOutCubic = (p) => (p = clamp(p)) < .5 ? 4*p**3 : 1-(-2*p+2)**3/2;
export const easeInOutQuart = (p) => (p = clamp(p)) < .5 ? 8*p**4 : 1-(-2*p+2)**4/2;
export const easeOutExpo = (p) => (p = clamp(p)) === 1 ? 1 : 1-2**(-10*p);
export const easeOutBack = (p) => {p=clamp(p)-1; return 1+2.70158*p**3+1.70158*p**2;};
export function spring(p, {damping=20, stiffness=140, mass=.8, seconds=.35}={}) {
  p=clamp(p); if (p===0 || p===1) return p;
  if (![damping,stiffness,mass,seconds].every(x=>Number.isFinite(x)&&x>0)) throw Error('Positive finite spring parameters required');
  const w=Math.sqrt(stiffness/mass), z=damping/(2*Math.sqrt(stiffness*mass)), t=p*seconds;
  const response=(s)=>{
    if (z<1) {const wd=w*Math.sqrt(1-z*z); return 1-Math.exp(-z*w*s)*(Math.cos(wd*s)+z*w/wd*Math.sin(wd*s));}
    if (Math.abs(z-1)<1e-6) return 1-Math.exp(-w*s)*(1+w*s);
    const a=-w*(z-Math.sqrt(z*z-1)), b=-w*(z+Math.sqrt(z*z-1));
    return 1-(b*Math.exp(a*s)-a*Math.exp(b*s))/(b-a);
  };
  return response(t)/response(seconds);
}
export const PRESETS = {
  snappy: {curve:'easeOutExpo', enter:.22, exit:.20, damping:20, stiffness:180},
  soft: {curve:'easeOutCubic', enter:.32, exit:.28, damping:24, stiffness:120},
  bouncy: {curve:'spring', enter:.40, exit:.26, damping:16, stiffness:150},
};
export const CURVES = {easeOutCubic,easeInOutCubic,easeInOutQuart,easeOutExpo,easeOutBack,spring};
export function eased(p, name='easeOutCubic', config={}) {
  const curve=CURVES[name]; if (!curve) throw Error(`Unknown easing: ${name}`);
  return curve(p,config);
}
export const lerp = (a,b,p,name='easeOutCubic',config={}) => a+(b-a)*eased(p,name,config);
