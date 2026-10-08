"""Read font cmap with stdlib: Uzbek glyph coverage, no extra install."""
from pathlib import Path
import argparse, struct
import common as C
REQUIRED='ogOG‘’ʻ'

def missing(path,required=REQUIRED):
    b=Path(path).read_bytes()
    if b[:4]==b'ttcf': return ['unverified TTC collection']
    u16=lambda o: struct.unpack_from('>H',b,o)[0]
    u32=lambda o: struct.unpack_from('>I',b,o)[0]
    table=None
    for i in range(u16(4)):
        o=12+i*16
        if b[o:o+4]==b'cmap': table=u32(o+8)
    if table is None: return list(required)
    found=set()
    for i in range(u16(table+2)):
        r=table+4+i*8; platform,encoding=u16(r),u16(r+2)
        if platform not in (0,3): continue
        s=table+u32(r+4); fmt=u16(s)
        if fmt==12:
            for j in range(u32(s+12)):
                o=s+16+j*12; lo,hi,glyph=u32(o),u32(o+4),u32(o+8)
                found.update(ch for ch in required if lo<=ord(ch)<=hi and glyph+ord(ch)-lo!=0)
        elif fmt==4:
            n=u16(s+6)//2
            for ch in required:
                code=ord(ch)
                for j in range(n):
                    end=u16(s+14+2*j); start=u16(s+16+2*n+2*j)
                    if start<=code<=end:
                        delta=u16(s+16+4*n+2*j); ro=s+16+6*n+2*j; off=u16(ro)
                        glyph=(code+delta)&65535 if not off else u16(ro+off+2*(code-start))
                        if off and glyph: glyph=(glyph+delta)&65535
                        if glyph: found.add(ch)
                        break
    return [ch for ch in required if ch not in found]

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('folder',nargs='?',default='style/fonts'); a=p.parse_args()
    rows=[]
    for f in sorted(Path(a.folder).rglob('*')):
        if f.suffix.lower() not in ('.ttf','.otf','.ttc'): continue
        absent=missing(f); rows.append({'file':str(f),'missing':absent})
        C.info(f"{'OGOH' if absent else 'OK'}: {f.name}: {absent or 'o‘ g‘ ʻ glyphs present'}")
    if not rows: raise C.MontajError('No fonts found.')
if __name__=='__main__': C.run_main(main)
