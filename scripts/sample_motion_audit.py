"""Read-only sample inventory; reuse hash-matched studies, never invent easing or SFX."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import common as C

def audit(out: Path):
    cached = {}
    for p in (C.ROOT/'docs/STYLE_STUDY/videos').glob('*/perception.json'):
        d=C.read_json(p); cached[d.get('sha1')]=dict(d, report=str(p.relative_to(C.ROOT)))
    rows=[]; seen={}; out.mkdir(parents=True, exist_ok=True)
    for p in sorted(C.SAMPLES_DIR.rglob('*')):
        if p.suffix.lower() not in C.VIDEO_EXTS: continue
        with p.open('rb') as stream: sha=hashlib.file_digest(stream, 'sha1').hexdigest()
        meta=C.ffprobe_info(p); d=cached.get(sha,{}); animations=d.get('animations',[])
        duplicate=seen.get(sha); seen[sha]=str(p.relative_to(C.ROOT))
        row=dict(file=str(p.relative_to(C.ROOT)),sha1=sha,duration=meta['duration'],fps=meta['fps'],
                 duplicate_of=duplicate,study=d.get('report'),family=d.get('type'),
                 observation=d.get('observation'),animations=animations,
                 text_examples=d.get('texts',[])[:3],audio_measurement=d.get('audio',{}).get('method'),
                 coverage=d.get('coverage','New overview; native opening strip; unknown easing/SFX retained'))
        stem=C.slugify(p.stem)
        if not d and not duplicate:
            sheet=out/(stem+'_overview.jpg'); strip=out/(stem+'_opening.jpg')
            for image,rate,tile,length in ((sheet,12/max(meta['duration'],1),'4x3',meta['duration']),
                                          (strip,min(meta['fps'],30)/3,'6x2',min(1.5,meta['duration']))):
                if not image.exists():
                    C.run([C.need_tool('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',p,
                           '-t',str(length),'-an','-vf',f'fps={rate},scale=270:-2,tile={tile}:padding=3',
                           '-frames:v','1',image],check=True)
            row['overview']=str(sheet.relative_to(C.ROOT)); row['opening_strip']=str(strip.relative_to(C.ROOT))
        rows.append(row); C.info(f"SAMPLE: {p.name} {meta['fps']:g}fps {'cache' if d else 'overview'}")
    C.write_json(dict(files=len(rows),unique=len(seen),rows=rows),out/'inventory.json')
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--out',default='temp/remotion_upgrade/samples')
    args=ap.parse_args(); rows=audit(C.guard_output(Path(args.out)))
    C.info(f'SAMPLES: {len(rows)} files; inventory.json')
if __name__=='__main__': C.run_main(main)
