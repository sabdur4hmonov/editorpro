"""Shared motion design invariants: bounded keyframes, premultiplied alpha, single source morph."""
import copy
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import common as C
import elements as E
import motion as M
import motion_language as ML
import motion_design as P
import cv2
import numpy as np


class MotionProTests(unittest.TestCase):
    def setUp(self):
        self.cfg = ML.config({'motion': {'enabled': True}})

    def test_track_exact_endpoints_and_hold(self):
        track = P.Track([{'at': 0, 'dx': -.15, 'opacity': 0},
                         {'at': .3, 'dx': 0, 'opacity': 1}, {'at': 1, 'scale': 1.04}], 1, self.cfg)
        self.assertEqual(track.at(-1)['opacity'], 0)
        self.assertEqual(track.at(.3)['dx'], 0)
        self.assertEqual(track.at(5)['scale'], 1.04)
        fractional=P.Track([{'at':0},{'at':2.6,'dx':.1}],2.8-.2,self.cfg)
        self.assertEqual(fractional.at(2.6)['dx'],.1)

    def test_trajectory_continuity_each_segment_boundary(self):
        for easing in P.EASINGS:
            tr = P.Track([{'at': 0, 'dx': -.1, 'scale': .7}, {'at': .4, 'dx': 0, 'scale': 1, 'ease': easing},
                          {'at': 1, 'dx': .02}], 1, self.cfg)
            for key in ('dx', 'scale'):
                self.assertLess(abs(tr.at(.4-1e-7)[key]-tr.at(.4+1e-7)[key]), .001)

    def test_reject_invalid_time_unknown_fields_and_nonfinite(self):
        for frames in ([], [{'at': 0}], [{'at': .1}, {'at': .4}],
                       [{'at': 0}, {'at': 0}], [{'at': 0}, {'at': 2}],
                       [{'at': 0}, {'at': .4, 'scale': float('nan')}],
                       [{'at': 0}, {'at': .4, 'dx': float('inf')}],
                       [{'at': 0}, {'at': .4, 'ease': 'invented'}],
                       [{'at': 0}, {'at': .4, 'speed': 10}],
                       [{'at': 0}, {'at': .4, 'opacity': 2}]):
            with self.subTest(frames=frames), self.assertRaises(C.MontajError):
                P.Track(frames, 1, self.cfg)

    def test_spring_bounds_alpha_and_scale(self):
        tr = P.Track([{'at': 0, 'scale': .05, 'opacity': 0},
                      {'at': .5, 'scale': 3, 'opacity': 1, 'ease': 'spring'}], 1, self.cfg)
        for t in np.linspace(0, 1, 201):
            values = tr.at(float(t))
            self.assertTrue(all(math.isfinite(v) for v in values.values()))
            self.assertTrue(.05<=values['scale']<=3 and 0<=values['opacity']<=1)

    def test_morph_limits_and_both_exit_entrance_smooth(self):
        for length in (.2, 1, 3):
            self.assertEqual(P.transition_progress(0, 0, length, .42), 0)
            self.assertEqual(P.transition_progress(length, 0, length, .42), 0)
            self.assertAlmostEqual(P.transition_progress(length/2, 0, length, .42), 1)
            for t in np.linspace(0, length, 51):
                self.assertAlmostEqual(P.transition_progress(t, 0, length, .42),
                                       P.transition_progress(length-t, 0, length, .42))

    def test_one_doctor_component_through_entire_morph(self):
        W, H = 120, 240
        source = np.full((H, W, 3), (20, 80, 20), np.uint8)
        source[35:75, 45:75] = (240, 0, 0)  # one face, not two alpha-composited views
        layer = object.__new__(P.MotionBroll)
        layer.morph = True; layer.ctx = SimpleNamespace(W=W, H=H, k=1, anchor=(.5, .25))
        layer.start = 0; layer.end = 2; layer.morph_seconds = .42
        layer.bw = False; layer.dim = 0; layer.lower_gradient = {}
        layer.seam_color = (235,235,235)
        layer._content = lambda t: np.full((H//2, W, 3), (0, 0, 180), np.uint8)
        for t in np.linspace(0, 2, 121):
            frame = source.copy(); layer.draw(frame, float(t))
            red = ((frame[..., 0]>180)&(frame[..., 1]<30)&(frame[..., 2]<30)).astype(np.uint8)
            count, _ = cv2.connectedComponents(red)
            self.assertEqual(count-1, 1, msg=f'{t:.3f}s')
        frame = source.copy(); layer.draw(frame, 0)
        self.assertTrue(np.array_equal(frame, source))
        frame = source.copy(); layer.draw(frame, 2)
        self.assertTrue(np.array_equal(frame, source))

    def test_one_source_geometry_in_bounds_at_every_progress(self):
        for anchor in ((.1, .1), (.5, .5), (.9, .9)):
            for p in np.linspace(0, 1, 301):
                x, y, w, h, output_h = P.split_geometry(540, 960, anchor, float(p))
                self.assertTrue(0<=x<x+w<=540 and 0<=y<y+h<=960)
                self.assertTrue(480<=output_h<=960)

    def test_stage_morph_preserves_single_face_and_full_frame_endpoints(self):
        W, H = 120, 240
        source = np.full((H, W, 3), (20, 80, 20), np.uint8)
        source[35:75, 45:75] = (240, 0, 0)
        layer = object.__new__(P.MotionStage)
        layer.ctx = SimpleNamespace(W=W, H=H)
        layer.morph = True; layer.start = 0; layer.end = 2; layer.morph_seconds = .5
        layer.sx0 = 0; layer.sy0 = 20; layer.sx1 = W; layer.sy1 = 160
        layer.cw = 100; layer.ch = 116; layer.cx = 60; layer.cy = 78; layer.radius = 10
        layer.backdrop = SimpleNamespace(draw=lambda frame, t, boost: frame.__setitem__(slice(None), (0, 0, 180)))
        for t in np.linspace(0, 2, 121):
            frame = source.copy(); layer.draw(frame, float(t))
            red = ((frame[..., 0]>180)&(frame[..., 1]<30)&(frame[..., 2]<30)).astype(np.uint8)
            count, _ = cv2.connectedComponents(red)
            self.assertEqual(count-1, 1, msg=f'{t:.3f}s')
        for t in (0, 2):
            frame = source.copy(); layer.draw(frame, t)
            self.assertTrue(np.array_equal(frame, source))

    def test_rotation_alpha_premultiplication_and_cache(self):
        spr = M.Sprite(np.full((30, 40, 4), (100, 30, 20, 150), np.uint8), -20, -15)
        layer = object.__new__(P.MotionImage)
        layer.reader = None; layer.transform_cache = P.OrderedDict(); layer.cache_limit = 18000
        first = layer.transformed(spr, 8, 0)
        self.assertIs(first, layer.transformed(spr, 8, 0))
        for angle in range(0, 40, 2):
            rotated = layer.transformed(spr, angle, 1)
            self.assertTrue(np.all(rotated.pix[..., :3]<=rotated.pix[..., 3:4]))
        self.assertLessEqual(sum(s.pix.nbytes for s in layer.transform_cache.values()), layer.cache_limit)
        self.assertLessEqual(len(layer.transform_cache), 16)

    def test_video_frames_never_share_static_transform_cache(self):
        layer = object.__new__(P.MotionImage)
        layer.reader = object(); layer.transform_cache = P.OrderedDict(); layer.cache_limit = 18000
        spr = M.Sprite(np.full((20, 20, 4), (100, 30, 20, 255), np.uint8), -10, -10)
        layer.transformed(spr, 8, 1)
        self.assertEqual(len(layer.transform_cache), 0)

    def ctx(self):
        st=C.load_style();st['video'].update(width=180,height=320,fps=30)
        st['captions'].update(font='Inter',glow=None)
        return E.Ctx(st)

    def test_premultiplied_rgba_composition_equivalent_to_rgb(self):
        spr=M.Sprite(np.full((20,20,4),(80,40,10,120),np.uint8))
        rgba=np.zeros((40,40,4),np.uint8);rgb=np.full((40,40,3),100,np.uint8)
        M.blit(rgba,spr,5,5,.6);M.blit(rgb,spr,5,5,.6)
        combined=np.full((40,40,3),100,np.uint8);M.blit(combined,M.Sprite(rgba),0,0)
        np.testing.assert_array_equal(combined,rgb)
        self.assertTrue(np.all(rgba[...,:3]<=rgba[...,3:4]))

    def test_rotating_sprite_preserves_chosen_pivot(self):
        pixels=np.zeros((20,40,4),np.uint8);pixels[8:12,18:22]=[255,0,0,255]
        spr=M.Sprite(pixels,-20,-10)
        for angle in (-90,30,90):
            state=dict(P.IDENTITY,rotate=angle,scale=1.3)
            result=P.warp(spr,state)
            frame=np.zeros((80,80,4),np.uint8);M.blit(frame,result,40,40)
            yy,xx=np.nonzero(frame[...,0]>200)
            self.assertLess(abs(xx.mean()-40),2);self.assertLess(abs(yy.mean()-40),2)

    def test_six_materials_and_shapes_keep_alpha_and_text(self):
        ctx=self.ctx();signatures=set()
        for material in P.MATERIALS:
            for shape in ('rounded','diagonal','arch'):
                layer=E.build_elements(ctx,[dict(type='card',start=0,end=2,material=material,shape=shape,
                                                text='o‘g‘il',font_size=70,width=.7,height=.2,anim='none')],2)[0]
                im=np.zeros((320,180,4),np.uint8);layer.draw(im,1)
                self.assertTrue(im.any());self.assertTrue(np.all(im[...,:3]<=im[...,3:4]))
                signatures.add(im.tobytes())
        self.assertGreaterEqual(len(signatures),12)

    def test_card_active_state_and_timed_canvas_child(self):
        ctx=self.ctx();layer=E.build_elements(ctx,[dict(type='canvas',start=0,end=2,items=[
            dict(type='card',at=.5,end=1.8,text='1',height=.15,anim='none',active_at=1,active_color='#FF4400')])],2)[0]
        ims=[]
        for t in (.2,.8,1.2,1.9):
            im=np.zeros((320,180,3),np.uint8);layer.draw(im,t);ims.append(im)
        self.assertFalse(ims[0].any());self.assertFalse(ims[-1].any())
        self.assertTrue(ims[1].any());self.assertFalse(np.array_equal(ims[1],ims[2]))

    def test_canvas_and_card_alpha_export_reconstruct_over_any_background(self):
        import editor_export as EX
        ctx=self.ctx()
        for el in (dict(type='card',text='o‘g‘il',material='grid',y=.6,anim='none'),
                   dict(type='canvas',items=[dict(type='card',text='1',y=.4,anim='none')],
                        trajectory=[{'at':0},{'at':1,'rotate':5,'dx':.05}])):
            layer=E.build_elements(ctx,[dict(start=0,end=2,**el)],2)[0]
            straight=EX.alpha_frame(layer,1,(320,180,3))
            img=np.full((320,180,3),73,np.uint8);direct=img.copy();layer.draw(direct,1)
            premul=straight.astype(np.uint16);premul[...,:3]=(premul[...,:3]*premul[...,3:4]+127)//255
            M.blit(img,M.Sprite(premul.astype(np.uint8)),0,0)
            self.assertLessEqual(np.max(np.abs(img.astype(int)-direct.astype(int))),2)

    def test_canvas_camera_moves_all_children_together(self):
        ctx=self.ctx();el=dict(type='canvas',start=0,end=2,trajectory=[{'at':0},{'at':1,'dx':.1,'ease':'linear'}],
                             items=[dict(type='card',text='1',x=.3,y=.3,width=.15,height=.08,anim='none'),
                                    dict(type='card',text='2',x=.6,y=.6,width=.15,height=.08,anim='none')])
        layer=E.build_elements(ctx,[el],2)[0];ims=[]
        for t in (0,1):
            im=np.zeros((320,180,3),np.uint8);layer.draw(im,t);ims.append(im)
        np.testing.assert_array_equal(ims[0][:,:-18],ims[1][:,18:])

    def test_text_track_preserves_identity_pixels_and_uzbek_units(self):
        ctx=self.ctx();el=dict(type='text',start=0,end=2,text='o‘g‘il',anim='none',y=.6)
        plain=E.build_elements(ctx,[el],2)[0]
        tracked=E.build_elements(ctx,[dict(el,trajectory=[{'at':0},{'at':1}])],2)[0]
        a=np.zeros((320,180,3),np.uint8);b=a.copy();plain.draw(a,1);tracked.draw(b,1)
        np.testing.assert_array_equal(a,b);self.assertEqual(ML.clusters('o‘g‘'),['o‘','g‘'])

    def test_outline_has_transparent_interior_and_relief_extends_box(self):
        font=self.ctx().fonts.get('Inter',48,800)
        flat,adv=M.text_sprite('O',font,'#FFFFFF')
        relief,radv=M.text_sprite('O',font,'#FFFFFF',stroke={'depth':10,'depth_color':'#DD3300'})
        outline,_=M.text_sprite('O',font,'#FFFFFF',stroke={'width':2,'color':'#FFFFFF','outline_only':True})
        self.assertEqual(adv,radv);self.assertGreater(relief.w,flat.w)
        self.assertLess(np.count_nonzero(outline.pix[...,3]),np.count_nonzero(flat.pix[...,3]))
        self.assertTrue(np.all(relief.pix[...,:3]<=relief.pix[...,3:4]))

    def test_invalid_card_canvas_track_and_transition_fail_clearly(self):
        ctx=self.ctx()
        for el in (dict(type='card',material='fake'),dict(type='card',width=float('nan')),
                   dict(type='canvas',items=[dict(type='canvas')]),dict(type='canvas',items=[]),
                   dict(type='card',active_at=3),dict(type='text',transition='layout_morph'),
                   dict(type='icon',name='heart',trajectory=[{'at':0},{'at':1}])):
            with self.subTest(el=el),self.assertRaises(C.MontajError):
                E.build_elements(ctx,[dict(start=0,end=2,**el)],2)

    def test_recipe_preserves_explicit_override_and_text(self):
        ctx=self.ctx();ctx.style['motion_design']={'caption_recipes':{'key_point':{
            'enter':'typewriter','sub':'mask_up','emphasis':'box_wipe'}}}
        layer=E.CaptionLayer(ctx,[dict(start=0,end=2,text='o‘g‘il')],None,2)
        self.assertEqual(layer.items[0]['cfg']['anim_main'],'typewriter')
        fixed=E.CaptionLayer(ctx,[dict(start=0,end=2,text='{clean,anim=none} o‘g‘il')],None,2)
        self.assertEqual(fixed.items[0]['cfg']['anim_main'],'none')

    def test_card_and_canvas_sfx_share_density_and_lead(self):
        import sound_design as SD
        from unittest.mock import patch
        st=self.ctx().style;st['sfx'].update(enabled=True,max_per_10_sec=2,min_gap_sec=.1,event_map={'label':'pop'})
        els=[dict(type='canvas',start=0,end=5,items=[dict(type='card',at=1,active_at=2),dict(type='card',at=3)])]
        with patch.object(SD,'variants',return_value=[Path('safe.wav')]): events=SD.gather(st,els,[],[])
        self.assertEqual(len(events),2)
        self.assertTrue(all(e['lead_frames_actual']==3 for e in events))

    def test_group_selection_ambiguity_and_brand_precedence(self):
        import sample_groups as SG
        self.assertEqual(SG.select({'seated_explainer':True,'static_speaker':True})['selected'],'A_studio_explainer')
        self.assertIsNone(SG.select({})['selected'])
        self.assertIsNone(SG.select({'creator':True,'documents':True})['selected'])
        with self.assertRaises(C.MontajError):SG.select({'made_up':True})
        with self.assertRaises(C.MontajError):SG.apply('D_cinematic_commercial',self.ctx().style,'product')
        st=self.ctx().style;st['captions']['accent']='#112233';st['captions']['font']='Caveat'
        out=SG.apply('B2_kinetic_creator',st,'creator tutorial',brand_patch={'motion':{'durations_ms':{'title':777}}})
        self.assertEqual(out['captions']['accent'],'#112233');self.assertEqual(out['captions']['font'],'Caveat')
        self.assertEqual(out['motion']['durations_ms']['title'],777)
        self.assertNotIn('sample_group',st)

    def test_peer_review_canvas_rejection_registry_and_seam_config(self):
        ctx=self.ctx()
        with self.assertRaisesRegex(C.MontajError,'behind_person'):
            E.build_elements(ctx,[dict(type='canvas',start=0,end=2,items=[
                dict(type='text',text='o‘g‘il',behind_person=True)])],2)
        self.assertTrue(all(callable(v) for v in E.ELEMENT_TYPES.values()))
        self.assertIsInstance(E.ELEMENT_TYPES['card'](ctx,dict(type='card',start=0,end=2,text='1')),P.CardLayer)
        from unittest.mock import patch
        ctx.style['motion_design']['seam_color']='#123456'
        with patch.object(E.BrollLayer,'__init__',return_value=None):
            # BrollLayer normally sets mode; isolate the configuration without decoding media.
            with patch.object(P.MotionBroll,'mode','split',create=True):
                layer=P.MotionBroll(ctx,{'transition':'layout_morph'})
        self.assertEqual(layer.seam_color,(18,52,86))

    def test_invert_flash_holds_exact_requested_frames_and_legacy_unchanged(self):
        ctx=self.ctx();el=dict(type='flash',at=1,duration=3/30,mode='invert',amount=1)
        layer=E.build_elements(ctx,[el],2)[0];source=np.full((320,180,3),(10,80,190),np.uint8)
        for frame_no in (30,31,32):
            frame=source.copy();layer.draw(frame,frame_no/30)
            np.testing.assert_array_equal(frame,255-source)
        frame=source.copy();layer.draw(frame,33/30);np.testing.assert_array_equal(frame,source)
        legacy=E.build_elements(ctx,[dict(type='flash',at=1,duration=.3)],2)[0]
        explicit=E.build_elements(ctx,[dict(type='flash',at=1,duration=.3,mode='color')],2)[0]
        a=source.copy();b=a.copy();legacy.draw(a,1.1);explicit.draw(b,1.1);np.testing.assert_array_equal(a,b)
        with self.assertRaises(C.MontajError):E.build_elements(ctx,[dict(el,mode='fake')],2)

    def test_d_subtypes_do_not_force_promo_on_vlog_and_brand_still_wins(self):
        import sample_groups as SG
        ctx=self.ctx();ctx.style['captions']['preset']='clean'
        for subtype,preset in (('promo','promo'),('showcase','single'),('vlog','clean')):
            out=SG.apply('D_cinematic_commercial',ctx.style,'observed '+subtype,subtype)
            self.assertEqual(out['captions']['preset'],preset)
        out=SG.apply('D_cinematic_commercial',ctx.style,'vlog','vlog',{'captions':{'preset':'serif'}})
        self.assertEqual(out['captions']['preset'],'serif')


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MotionProTests))
    print(f'MOTION DESIGN NATIJA: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}')
    raise SystemExit(not result.wasSuccessful())
