"""Select a sample family from agent-observed footage/content; apply per-video DNA."""
from __future__ import annotations
import argparse,copy,re
from pathlib import Path
import common as C

DNA_DIR=C.ROOT/'docs/style_dna'
FAMILIES=('A_studio_explainer','B1_editorial_paper','B2_kinetic_creator','C_interview_testimonial','D_cinematic_commercial')
FEATURES={'seated_explainer','interview','testimonial','creator','tutorial','documents','campus',
          'promo','product','showcase','vlog','multiple_speakers','static_speaker'}
WEIGHTS={
 'A_studio_explainer':{'seated_explainer':5,'static_speaker':3,'tutorial':2},
 'B1_editorial_paper':{'documents':5,'campus':3},
 'B2_kinetic_creator':{'creator':5,'tutorial':3},
 'C_interview_testimonial':{'interview':5,'testimonial':5,'multiple_speakers':3},
 'D_cinematic_commercial':{'promo':5,'product':4,'showcase':5,'vlog':5}}

def select(features):
    if not isinstance(features,dict) or set(features)-FEATURES:
        raise C.MontajError('features: known observed boolean keys only: '+', '.join(sorted(FEATURES)))
    if any(not isinstance(v,bool) for v in features.values()):raise C.MontajError('features qiymati true/false bo‘lsin.')
    ranked=sorted(({'group':g,'score':sum(w for k,w in weights.items() if features.get(k)),
                     'evidence_features':[k for k in weights if features.get(k)]} for g,weights in WEIGHTS.items()),
                  key=lambda row:(-row['score'],row['group']))
    top=ranked[0];gap=top['score']-ranked[1]['score']
    return {'selected':top['group'] if top['score']>0 and gap>=2 else None,'ranked':ranked,
            'needs_editor_judgement':top['score']==0 or gap<2,
            'method':'transparent heuristic from agent-observed footage/content; no automatic scene understanding',
            'confidence':'medium' if top['score']>0 and gap>=2 else 'low'}

def apply(group,style,reason,subtype=None,brand_patch=None):
    if group not in FAMILIES:raise C.MontajError('Unknown sample family.')
    if not str(reason).strip():raise C.MontajError('Group reason kerak: kuzatilgan kadr/mazmunni yozing.')
    if group=='D_cinematic_commercial' and subtype not in ('promo','showcase','vlog'):
        raise C.MontajError('D group uchun subtype promo/showcase/vlog kerak.')
    dna=C.read_json(DNA_DIR/group/'style_dna.json')
    result=C.deep_merge(copy.deepcopy(style),dna['style_patch'])
    if subtype:
        result=C.deep_merge(result,dna.get('subtype_patches',{}).get(subtype,{}))
    if brand_patch:result=C.deep_merge(result,brand_patch)
    result['sample_group']={'id':group,'reason':reason,'subtype':subtype,'schema':dna['schema'],
                            'evidence':dna['members'],'sound_approval':'pending'}
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    se=sub.add_parser('select');se.add_argument('--features',required=True,help='JSON file with observed boolean features');se.add_argument('-o','--output')
    aa=sub.add_parser('apply');aa.add_argument('group',choices=FAMILIES);aa.add_argument('--style',required=True)
    aa.add_argument('--reason',required=True);aa.add_argument('--subtype',choices=('promo','showcase','vlog'));aa.add_argument('--brand')
    a=ap.parse_args()
    if a.command=='list':
        for group in FAMILIES:C.info(group+': '+C.read_json(DNA_DIR/group/'style_dna.json')['description'])
    elif a.command=='select':
        result=select(C.read_json(a.features))
        if a.output:
            dest=Path(a.output).resolve()
            if not C.is_inside(dest,C.TEMP_DIR):raise C.MontajError('Selection report faqat temp/ ga.')
            C.write_json(result,dest)
        import json;C.info(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        path=Path(a.style).resolve()
        if not C.is_inside(path,C.TEMP_DIR):raise C.MontajError('DNA faqat per-video temp/<video>/style.json ga yoziladi.')
        style=C.read_json(C.need_file(path,'Per-video style'))
        brand=a.brand or style.get('brand') or style.get('_brand')
        if brand and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',brand):raise C.MontajError('Brend nomi noto‘g‘ri.')
        patch=C.read_json(C.need_file(C.ROOT/'brands'/brand/'brand.json','Brand')).get('style',{}) if brand else None
        C.write_json(apply(a.group,style,a.reason,a.subtype,patch),path)
        C.info('SAMPLE GROUP [OK]: '+a.group+'; '+a.reason)
    return 0
if __name__=='__main__':C.run_main(main)
