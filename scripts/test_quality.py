"""Regression tests for semantic graphics, temporal face safety and honest quality gates."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import common as C
import compose as CP
import elements as E
import face_safety as FS
import graphics_ideas as G
import motion_design as MD
import quality_gate as Q
import sound_design as SD


def style():
    s=C.load_style(); s['video'].update(width=180,height=320,fps=30)
    s['motion']['enabled']=True; s['quality']['no_repeat']=True
    return s

class GraphicsTests(unittest.TestCase):
    def test_repeat_apostrophe_and_suffix(self):
        c=[dict(start=0,end=3,text='*dorilar* o‘pkaga zarar')]
        e=[dict(type='card',start=1,end=2,text='dori')]
        self.assertEqual(len(G.repeat_violations(e,c)),1)
        self.assertTrue(G._same("o'pka", "o'pkasi"))

    def test_repeat_needs_written_exception(self):
        c=[dict(start=0,end=3,text='dorilar')]; e=[dict(type='text',start=0,end=2,text='dorilar',allow_repeat=True)]
        self.assertFalse(G.repeat_violations(e,c)[0]['allowed'])
        e[0]['repeat_reason']='This explicit correction quotes the spoken word.'
        self.assertTrue(G.repeat_violations(e,c)[0]['allowed'])

    def test_partial_hidden_caption_still_checked_outside_span(self):
        c=[dict(start=0,end=4,text='dori')]
        e=[dict(type='group',start=1,end=2,hide_captions=True),dict(type='card',start=2.1,end=3,text='dori')]
        self.assertEqual([(r['start'],r['end']) for r in G.visible_cues(c,e)],[(0,1),(2,4)])
        self.assertEqual(len(G.repeat_violations(e,c)),1)

    def test_hidden_spans_do_not_change_source_cues_or_word_times(self):
        s=style(); ctx=E.Ctx(s); cues=[dict(start=0,end=3,text='o‘g‘il')]; before=copy.deepcopy(cues)
        layer=CP.build_layers(ctx,s,cues,None,[dict(type='text',start=1,end=2,text='tahlil',hide_captions=True)],3,3)
        cap=next(l for l in layer if isinstance(l,E.CaptionLayer)); im=np.zeros((320,180,3),np.uint8)
        cap.draw(im,1.5); self.assertFalse(im.any())
        cap.draw(im,2.2); self.assertTrue(im.any()); self.assertEqual(cues,before)

    def test_preflight_enforces_only_opted_in_no_repeat(self):
        import studio
        s=style(); cues=[dict(start=0,end=2,text='dori')]; els=[dict(type='card',start=0,end=2,text='dori')]
        self.assertTrue(studio.preflight(s,cues,els,2,False)['errors'])
        s['quality']['no_repeat']=False
        self.assertFalse(studio.preflight(s,cues,els,2,False)['errors'])

    def test_ideas_use_spoken_objects_and_numbers(self):
        w=[dict(word=x,start=i,end=i+.2) for i,x in enumerate(['25%','foiz','telefon','birinchi','qon','ikkinchi','yurak'])]
        ideas=G.moments(w)
        self.assertTrue(any(d['type']=='stat' for d in ideas))
        self.assertTrue(any(d.get('icon')=='device-mobile' for d in ideas))
        self.assertTrue(any(d['type']=='list' and len(d['items'])==2 for d in ideas))

class ObjectTests(unittest.TestCase):
    def test_signed_fan_and_spoken_item_timing(self):
        ctx=E.Ctx(style()); el=dict(type='group',start=0,end=3,pivot=[.9,.7],spread=-55,angle_from=-110,
                                  items=[dict(at=.3,text='qon'),dict(at=1.2,text='yurak')])
        l=MD.GroupLayer(ctx,el); self.assertLess(l.items[1]['target'],l.items[0]['target'])
        im=np.zeros((320,180,3),np.uint8); l.draw(im,.1); self.assertFalse(im.any())
        l.draw(im,.7); self.assertTrue(im.any())
        self.assertEqual(l.items[1]['at'],1.2)

    def test_group_rejects_unreachable_or_reversed_items(self):
        ctx=E.Ctx(style())
        for times in ([2],[1,.3]):
            with self.assertRaises(C.MontajError):
                MD.GroupLayer(ctx,dict(type='group',start=0,end=2,items=[dict(at=t,text='qon') for t in times]))

    def test_hero_settles_and_exits_on_path(self):
        ctx=E.Ctx(style()); l=MD.HeroLayer(ctx,dict(type='hero',start=0,end=3,icon='heart',x=.25,y=.7,
                               duration=.36,float=False,trail=.7,depth=.4))
        self.assertAlmostEqual(l.state(1)[0],.25*180)
        self.assertAlmostEqual(l.state(1)[1],.7*320)
        self.assertGreater(abs(l.state(2.99)[0]-l.state(1)[0]),30)
        im=np.full((320,180,3),60,np.uint8); l.draw(im,.2); self.assertTrue(np.any(im!=60))

    def test_group_and_hero_sfx_respect_density_and_lead(self):
        s=style(); s['sfx'].update(enabled=True,min_gap_sec=.1,max_per_10_sec=2,event_map={'sticker':'whoosh','label':'pop'})
        els=[dict(type='hero',start=1,end=2),dict(type='group',start=2,end=6,items=[dict(at=2),dict(at=3),dict(at=4)])]
        with patch.object(SD,'variants',return_value=[C.ROOT/'assets/sfx/pop.wav']):
            e=SD.gather(s,els,[],[])
        self.assertEqual(len(e),2); self.assertTrue(any(r['kind']=='sticker' for r in e))
        self.assertTrue(all(r['lead_frames_actual']==3 for r in e))

class FaceTests(unittest.TestCase):
    def monitor(self, replacing=False):
        ctx=E.Ctx(style()); l=SimpleNamespace(el_type='hero',el_ref='1:hero',active=lambda t:True)
        m=FS.FaceMonitor(ctx,[l],ctx.style,scale_h=320)
        m.det=object(); m._face=lambda frame:(40,40,100,100)
        return m

    def test_exit_violation_even_when_middle_is_safe(self):
        m=self.monitor(); im=np.zeros((320,180,3),np.uint8)
        for i in range(60):
            m.before(im,i/30); drawn=im.copy()
            if i>=55: drawn[40:70,40:100]=255
            m.after(drawn,i/30,i)
        rep=m.report(); self.assertFalse(rep['ok']); self.assertEqual(rep['violations'][0]['start_frame'],55)
        self.assertEqual(rep['frames_checked'],60)

    def test_missing_detector_or_face_is_not_verified(self):
        m=self.monitor(); m.det=None; self.assertFalse(m.report()['ok'])
        m.det=object(); m._face=lambda f:None
        m.before(np.zeros((320,180,3),np.uint8),0)
        self.assertEqual(m.report()['verification'],'unverified_no_face')

    def test_split_layout_is_not_a_blanket_skip(self):
        m=self.monitor(); m.overlays += [SimpleNamespace(el_type='stage',active=lambda t:True)]
        im=np.zeros((320,180,3),np.uint8); m.before(im,1)
        im[40:100,40:100]=255; m.after(im,1,30)
        self.assertFalse(m.report()['ok'])

    def test_second_smaller_face_is_also_protected(self):
        m=self.monitor()
        def boxes(frame):
            m.extra_boxes=[(120,40,150,70)]
            return (40,40,100,100)
        m._face=boxes
        im=np.zeros((320,180,3),np.uint8);m.before(im,1)
        im[40:70,120:150]=255;m.after(im,1,30)
        r=m.report();self.assertFalse(r['ok']);self.assertEqual(r['violations'][0]['face_rank'],1)

    def test_graphics_history_changes_rank_only_for_same_format(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            p=Path(td)/'history.json'
            C.write_json({'decisions':[{'type':'object','format':'interview','verdict':'rejected'},
                                      {'type':'count','format':'talking_head','verdict':'approved'}]},p)
            with patch.object(G,'HISTORY',p):
                h=G.history_weights({'format':'talking_head'})
            self.assertNotIn('object',h);self.assertEqual(h['count'],1)

class GateTests(unittest.TestCase):
    def test_audio_joins_na_only_for_verified_empty_cut_list(self):
        result={'smoothness':{'held_frames':0,'source_fps':30,'fps':30,'cuts':[],'caption_lag':[]}}
        for cuts, expected in (([], 'not_applicable'), (None, 'unknown'), ([2], 'unknown')):
            with self.subTest(cuts=cuts):
                r=Q.evaluate(style(),[dict(start=0,end=10,text='qon')],[],10,
                             {'style_group':'C_interview_testimonial'},result,cuts)
                states={x['key']:x['status'] for x in r['measurements']}
                self.assertEqual(states['cut_audio_holes'],expected)
                self.assertEqual(states['face_coverage'],'unknown')

    def test_applied_native_cut_plan_uses_output_time_and_speed(self):
        self.assertEqual(Q.editorial_cut_times({'keep':[{'start':5,'end':9},{'start':15,'end':21}], 'speed':2}),[2])
        self.assertEqual(Q.editorial_cut_times({'keep':[{'start':0,'end':9}]}),[])
        self.assertEqual(Q.editorial_cut_times({'times':[2,5]}),[2,5])
        self.assertIsNone(Q.editorial_cut_times({'candidate_cuts':[2,5]}))
        with self.assertRaises(C.MontajError):Q.editorial_cut_times({'keep':[], 'speed':0})

    def test_word_synced_fan_stagger_is_not_a_new_scene_each_item(self):
        s=style();c=[dict(start=0,end=10,text='qon')]
        e=[dict(type='group',start=1,end=2,items=[dict(at=1,text='yurak'),dict(at=1.07,text='jigar')]),
           dict(type='hero',start=4,end=5,icon='pill')]
        r=Q.evaluate(s,c,e,10,{'style_group':'A_studio_explainer'})
        row=next(x for x in r['measurements'] if x['key']=='event_spacing')
        self.assertEqual(row['status'],'pass');self.assertIn(1.07,r['item_event_times'])

    def test_no_graphic_entrance_is_na_but_missing_face_stays_unknown(self):
        r=Q.evaluate(style(),[dict(start=0,end=10,text='qon')],[],10,{'style_group':'C_interview_testimonial'})
        states={x['key']:x['status'] for x in r['measurements']}
        self.assertEqual(states['entrance_frames_30fps'],'not_applicable');self.assertEqual(states['face_coverage'],'unknown')

    def test_missing_evidence_never_full_pass(self):
        r=Q.evaluate(style(),[dict(start=0,end=10,text='qon')],[],10,{'style_group':'A_studio_explainer'})
        self.assertEqual(r['status'],'needs_fix_or_measurement')
        self.assertTrue(any(r['key']=='face_coverage' and r['status']=='unknown' for r in r['measurements']))
        self.assertFalse(r['creative_approval'])

    def test_face_and_speech_fail_despite_high_other_scores(self):
        result={'face_safety':{'verification':'measured','max_cover':.3},'checks':[('export','ok','')],
                'audio':{'additions':True,'margin_db':3},'integrated_lufs':-14}
        r=Q.evaluate(style(),[dict(start=0,end=10,text='qon')],[],10,{'style_group':'A_studio_explainer'},result,[])
        bad={x['key'] for x in r['fix_list']}; self.assertIn('face_coverage',bad); self.assertIn('voice_margin',bad)

if __name__=='__main__': unittest.main(verbosity=2)
