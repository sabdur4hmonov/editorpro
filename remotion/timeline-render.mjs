// JSON-in, high-quality ProRes cached visual segments out. FFmpeg owns final audio/encode.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {selectComposition,renderMedia,renderStill} from '@remotion/renderer';
const here=path.dirname(fileURLToPath(import.meta.url));
const [jobFile]=process.argv.slice(2);
if(!jobFile) {console.log('node timeline-render.mjs JOB.json (props, cache, outputs, concurrency, scale, stillFrames)');process.exit(1);}
const job=JSON.parse(fs.readFileSync(jobFile,'utf8')),p=job.props;
if(![2,3].includes(job.concurrency)) throw Error('Concurrency must be 2 or 3');
const hash=(s)=>createHash('sha256').update(s).digest('hex');
const sources=(dir)=>fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?sources(path.join(dir,e.name)):[path.join(dir,e.name)]);
const srcHash=hash([...sources(path.join(here,'src')),fileURLToPath(import.meta.url),path.join(here,'package-lock.json')].sort().map(f=>f+hash(fs.readFileSync(f))).join(''));
const serveUrl=await bundle({entryPoint:path.join(here,'src','index.ts'),publicDir:job.publicDir,outDir:path.join(job.cache,'..','bundle')});
const browserExecutable=job.browser;
if(!browserExecutable || !fs.existsSync(browserExecutable)) throw Error('Installed browser missing; no automatic download allowed');
const composition=await selectComposition({serveUrl,id:'Timeline',inputProps:p,browserExecutable});
fs.mkdirSync(job.cache,{recursive:true});
const common={serveUrl,composition,inputProps:p,browserExecutable,chromiumOptions:{gl:'angle'},
  concurrency:job.concurrency,scale:job.scale??1,imageFormat:'png',logLevel:'warn'};
const traces=[],segments=[],report=[];
const onBrowserLog=(log)=>{if(log.text.startsWith('MOTION_QA:')) traces.push(JSON.parse(log.text.slice(10)));};
if(job.stillFrames) {
  for(const frame of job.stillFrames) await renderStill({...common,frame,imageFormat:'png',output:path.join(job.cache,`still_${frame}.png`),onBrowserLog});
} else {
  for(let start=0;start<p.durationInFrames;start+=job.segmentFrames) {
    const end=Math.min(p.durationInFrames-1,start+job.segmentFrames-1);
    // Unchanged timeline ranges keep their pixels even when another phrase/graphic changes.
    const filtered={...p,captions:p.captions.filter(c=>c.startFrame<=end&&c.endFrame+p.motion.exitFrames>=start),
      elements:p.elements.filter(e=>e.startFrame<=end&&e.endFrame+p.motion.exitFrames>=start),
      transitions:p.transitions.filter(e=>e.startFrame<=end&&e.endFrame+p.motion.exitFrames>=start)};
    const key=hash(JSON.stringify({srcHash,filtered,start,end,scale:job.scale,version:'4.0.534'}));
    const out=path.join(job.cache,key+'.mov'),trace=path.join(job.cache,key+'.trace.json');
    const hit=fs.existsSync(out)&&fs.existsSync(trace); const t0=Date.now();
    if(hit) traces.push(...JSON.parse(fs.readFileSync(trace,'utf8')));
    else {
      const first=traces.length;
      await renderMedia({...common,inputProps:filtered,codec:'prores',proResProfile:'4444',pixelFormat:'yuva444p10le',
        muted:true,outputLocation:out,frameRange:[start,end],onBrowserLog});
      fs.writeFileSync(trace,JSON.stringify(traces.slice(first)));
    }
    segments.push(out); report.push({start,end,key,hit,seconds:(Date.now()-t0)/1000});
    console.log(`SEGMENT ${start}-${end}: ${hit?'CACHE':'RENDER'} ${report.at(-1).seconds.toFixed(1)}s`);
  }
}
fs.writeFileSync(job.result,JSON.stringify({segments,report,traces}));
