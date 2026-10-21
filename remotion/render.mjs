// Render a transparent overlay clip for the Python compositor.
//
//   node render.mjs <props.json> <out.mov> [--still FRAME] [--webm]
//
// props.json: {width, height, fps, durationInFrames, theme?, scenes:[{type, from, duration, ...}]}
// Image paths in scenes (image / file keys) may be project-relative (e.g. temp/<job>/images/x.png): they are
// copied into public/job/<hash>/ so Remotion can serve them; the props passed to Remotion use the copies.
// Output: ProRes 4444 with alpha (yuva444p10le), verified with ffprobe (pix_fmt must contain 'a').
// Browser: Remotion's own Chrome Headless Shell when present, otherwise the installed Chrome.
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: node render.mjs <props.json> <out.mov> [--still FRAME] [--webm]');
  process.exit(2);
}
const [propsFile, outFile] = args;
const still = args.includes('--still') ? Number(args[args.indexOf('--still') + 1]) : null;
const webm = args.includes('--webm');

const props = JSON.parse(fs.readFileSync(propsFile, 'utf8'));
for (const k of ['width', 'height', 'fps', 'durationInFrames', 'scenes']) {
  if (props[k] === undefined) throw new Error(`props.${k} kerak`);
}
// fonts
fs.mkdirSync(path.join(HERE, 'public', 'fonts'), {recursive: true});
for (const f of fs.readdirSync(path.join(ROOT, 'style', 'fonts'))) {
  if (f.endsWith('.ttf')) fs.copyFileSync(path.join(ROOT, 'style', 'fonts', f), path.join(HERE, 'public', 'fonts', f));
}
// assets
const job = createHash('sha1').update(path.resolve(propsFile)).digest('hex').slice(0, 10);
const jobDir = path.join(HERE, 'public', 'job', job);
fs.mkdirSync(jobDir, {recursive: true});
// every string value that names an existing media file (any depth: tiles[], images[], items[].icon, video ...)
const MEDIA = /\.(png|jpe?g|webp|svg|gif|mp4|mov|webm|m4v)$/i;
const copied = new Map();
const relink = (v) => {
  if (typeof v === 'string' && MEDIA.test(v) && !v.startsWith('http') && !v.startsWith('job/')) {
    const abs = path.isAbsolute(v) ? v : path.join(ROOT, v);
    if (!fs.existsSync(abs)) throw new Error(`Fayl topilmadi: ${v}`);
    if (!copied.has(abs)) {
      const name = `${copied.size}_${path.basename(abs).replace(/\s+/g, '_')}`;
      fs.copyFileSync(abs, path.join(jobDir, name));
      copied.set(abs, `job/${job}/${name}`);
    }
    return copied.get(abs);
  }
  if (Array.isArray(v)) return v.map(relink);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, relink(x)]));
  return v;
};
props.scenes = relink(props.scenes);
const resolved = path.join(jobDir, 'props.json');
fs.writeFileSync(resolved, JSON.stringify(props));

const shell = path.join(HERE, 'node_modules', '.remotion', 'chrome-headless-shell');
const haveShell = fs.existsSync(shell) && fs.readdirSync(shell).some((d) => !d.endsWith('.zip') && !d.endsWith('.lock'));
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const browser = haveShell ? [] : (fs.existsSync(chrome) ? [`--browser-executable=${chrome}`] : []);
// Execute the already-installed CLI directly: no shell parsing, npx lookup or implicit install.
const cli = path.join(HERE, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
if (!fs.existsSync(cli)) throw new Error('Installed Remotion CLI missing; install requires user approval.');
fs.mkdirSync(path.dirname(path.resolve(outFile)), {recursive: true});
const common = ['src/index.ts', 'Overlay', path.resolve(outFile), `--props=${resolved}`, '--gl=angle', ...browser];
const cmd = still !== null
  ? ['still', ...common, `--frame=${still}`]
  : ['render', ...common, '--image-format=png', '--concurrency=2',
     ...(webm ? ['--codec=vp9', '--pixel-format=yuva420p'] : ['--codec=prores', '--prores-profile=4444', '--pixel-format=yuva444p10le'])];
const t0 = Date.now();
const r = spawnSync(process.execPath, [cli, ...cmd], {cwd: HERE, stdio: 'inherit', shell: false, windowsHide: true});
if (r.status !== 0) process.exit(r.status ?? 1);
if (still === null) {
  const p = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=pix_fmt,width,height,nb_frames',
    '-of', 'json', path.resolve(outFile)], {encoding: 'utf8'});
  const st = JSON.parse(p.stdout).streams[0];
  if (!/a/.test(st.pix_fmt.replace('yuv', '').replace('p', ''))) {
    console.error(`XATO: alfa kanali yo'q (${st.pix_fmt})`);
    process.exit(3);
  }
  console.log(`REMOTION OVERLAY [OK]: ${outFile} ${st.width}x${st.height} ${st.pix_fmt} ${st.nb_frames} kadr, ${((Date.now() - t0) / 1000).toFixed(1)} s`);
}
