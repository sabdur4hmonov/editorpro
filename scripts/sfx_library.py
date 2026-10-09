"""Index local SFX with honest per-file provenance; never download or invent a licence."""
from pathlib import Path
import argparse, hashlib
import common as C

def provenance(path):
    credit = path.with_suffix(path.suffix+'.credit.json')
    data = C.read_json(credit) if credit.is_file() else {}
    licence = path.with_suffix(path.suffix+'.LICENSE.txt')
    if not licence.is_file():
        data['license_verified'] = False
    else:
        text = licence.read_text(encoding='utf-8').strip()
        data['license_verified'] = bool(text) and not text.startswith('UNVERIFIED')
    synth = data.get('kind') == 'synthesized' or str(data.get('source','')).startswith('scripts/make_sfx.py')
    if path.stem in ('pop','click','tick','thud','ding','whoosh','swipe','riser') and path.parent == C.ROOT/'assets/sfx':
        synth = True
        data.setdefault('source', 'scripts/make_sfx.py original synthesis')
        data.setdefault('license', 'Project-original generated audio; no third-party recording')
    return dict(data, kind='synthesized' if synth else 'real',
                usable=bool(data.get('source') and data.get('license') and data['license_verified']))

def index(folder):
    import audio_mix
    rows=[]
    for path in sorted(Path(folder).rglob('*')):
        if path.suffix.lower() not in audio_mix.SFX_EXTS or not path.is_file(): continue
        if any(part.startswith('_') for part in path.relative_to(folder).parts[:-1]): continue  # _inbox/_preview/_unsorted
        meta=provenance(path)
        if not meta.get('source'):
            meta.update(source='UNKNOWN: user supplied; original page not provided',
                        license='UNVERIFIED', license_verified=False, usable=False)
            C.write_json(meta,path.with_suffix(path.suffix+'.credit.json'))
            if not path.with_suffix(path.suffix+'.LICENSE.txt').exists():
                path.with_suffix(path.suffix+'.LICENSE.txt').write_text('UNVERIFIED: supply source page and licence before use.\n',encoding='utf-8')
        info=C.ffprobe_info(path)
        file = str(path.resolve().relative_to(C.ROOT)) if C.is_inside(path,C.ROOT) else str(path.resolve())
        rows.append(dict(meta, file=file,category=path.parent.name if path.parent!=Path(folder) else path.stem,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),duration=info['duration']))
    C.write_json({'files':rows},Path(folder)/'index.json')
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--folder',default='assets/sfx'); a=p.parse_args()
    folder=C.guard_output(Path(a.folder)); rows=index(folder)
    C.info(f'SFX INDEX: {len(rows)} files; real usable {sum(r["kind"]=="real" and r["usable"] for r in rows)}; '
           f'unverified {sum(not r["usable"] for r in rows)}')
if __name__=='__main__': C.run_main(main)
