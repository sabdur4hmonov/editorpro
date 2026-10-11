"""Regression tests for approval timing, fixed layout, brand settings and QA failure detection."""
import copy, unittest, tempfile, wave
from pathlib import Path
from unittest.mock import patch
import common as C,remotion_engine as R

class RemotionTests(unittest.TestCase):
    def test_config_rejects_unsafe_resource_settings(self):
        for cfg in ({'fps':25},{'concurrency':8},{'enter_sec':.05},{'qa_attempts':9},{'blur':{'intensity':10}}):
            with self.assertRaises(C.MontajError):R.settings({'remotion':cfg})
    def test_unknown_animation_rejected(self):
        with self.assertRaises(C.MontajError):R.settings({'remotion':{'animation_cycle':['linear']}})
    def test_brand_overrides(self):
        cfg=R.settings({'remotion':{'preset':'bouncy','blur':{'enabled':True}}})
        self.assertEqual(cfg['preset'],'bouncy');self.assertEqual(cfg['blur']['intensity'],2)
    def test_uzbek_word_cluster_timing_and_stable_layout(self):
        style=C.load_style();style['captions']['font']='Inter'
        words=[dict(word='o‘g‘il',start=.123,end=.5),dict(word='to‘g‘ri',start=.6,end=.9)]
        a,_,_=R.caption_plan([dict(start=0,end=1,text='o‘g‘il *to‘g‘ri*')],words,style,540,960,30,R.settings(style))
        self.assertEqual(len(a[0]['words']),2);self.assertEqual(a[0]['words'][0]['frame'],4)
        self.assertEqual(a[0]['words'][0]['text'],'o‘g‘il');self.assertGreater(a[0]['words'][1]['x'],a[0]['words'][0]['x'])
    def test_mismatch_never_guesses_word_time(self):
        with self.assertRaisesRegex(C.MontajError,'alignment'):
            R.caption_plan([dict(start=0,end=1,text='other')],[dict(word='o‘g‘il',start=0,end=1)],C.load_style(),540,960,30,R.settings({}))
    def props(self):
        return dict(width=100,height=100,safe=dict(left=.1,right=.1,top=.1,bottom=.1),durationInFrames=2,
                    motion=dict(distance=30),captions=[dict(words=[dict(id='w',frame=0)])])
    def traces(self):
        return [dict(frame=i,boxes=[dict(id='w',role='caption',phase='hold',x=20,y=20,w=20,h=20,opacity=1)]) for i in range(2)]
    def test_good_measured_trace(self):self.assertFalse(R.dom_qa(self.props(),self.traces())['errors'])
    def test_missing_measurement_is_failure(self):self.assertTrue(R.dom_qa(self.props(),[])['errors'])
    def test_bounds_violation_detected(self):
        tr=self.traces();tr[0]['boxes'][0]['x']=89
        self.assertIn('safe_area',{e['kind'] for e in R.dom_qa(self.props(),tr)['errors']})
    def test_hold_jump_detected(self):
        tr=self.traces();tr[1]['boxes'][0]['x']=25
        self.assertIn('hold_jitter',{e['kind'] for e in R.dom_qa(self.props(),tr)['errors']})
    def test_unknown_legacy_graphic_not_silently_dropped(self):
        with self.assertRaisesRegex(C.MontajError,'does not support'):
            R.elements_plan([dict(type='unknown',start=0,end=1)],{},C.TEMP_DIR,540,960,30,R.settings({}))
    def test_nonfinite_geometry_fails(self):
        tr=self.traces();tr[0]['boxes'][0]['x']=None
        self.assertIn('invalid_geometry',{e['kind'] for e in R.dom_qa(self.props(),tr)['errors']})
    def test_text_graphic_safe_area(self):
        tr=self.traces();tr[0]['boxes'].append(dict(id='title',role='graphic',safeRequired=True,phase='enter',x=90,y=20,w=20,h=20,opacity=1))
        self.assertIn('safe_area',{e['kind'] for e in R.dom_qa(self.props(),tr)['errors']})
    def test_audio_grid_repair_preserves_original_samples(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as tmp:
            wav=Path(tmp)/'short.wav';samples=b'\x10\x00'*4800
            with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000);f.writeframes(samples)
            fixed=R.exact_audio(wav,.133333333,tmp,{'audio':{'room_tone':False}})
            with wave.open(str(fixed)) as f:
                data=f.readframes(f.getnframes());self.assertEqual(f.getnframes(),6400);self.assertEqual(data[:len(samples)],samples)
    def test_cache_protects_active_and_prunes_old(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as tmp:
            folder=Path(tmp)/'segments';folder.mkdir();a=folder/'a.mov';b=folder/'b.mov'
            a.write_bytes(b'1234');b.write_bytes(b'5678');a.with_suffix('.trace.json').write_text('[]')
            result=R.prune_cache(tmp,[b],4)
            self.assertFalse(a.exists());self.assertFalse(a.with_suffix('.trace.json').exists());self.assertTrue(b.exists());self.assertEqual(result['bytes'],4)
    def test_real_missing_uzbek_glyph_uses_present_font(self):
        import motion,glyph_audit
        fonts=motion.Fonts([C.ROOT/'style/fonts']);font=fonts.get('Caveat',50,700)
        self.assertIn('ʻ',glyph_audit.missing(font.primary.path))
        fallback=font.character_font('ʻ');self.assertNotEqual(str(font.primary.path),str(fallback.path))
        self.assertEqual(glyph_audit.missing(fallback.path,'ʻ'),[])
    def test_scratch_cleanup_preserves_active_and_manual_files(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as tmp:
            root=Path(tmp)/'remotion';folder=root/'public/assets';folder.mkdir(parents=True)
            active=folder/('a'*64+'.png');old=folder/('b'*64+'.png');manual=folder/'manual.png'
            for p in (active,old,manual):p.write_bytes(b'1234')
            R.clean_scratch(root,dict(elements=[dict(file='assets/'+active.name)]))
            self.assertTrue(active.exists());self.assertFalse(old.exists());self.assertTrue(manual.exists())
            with self.assertRaises(C.MontajError):R.clean_scratch(Path(tmp),{})
    def test_conservative_face_geometry(self):
        import remotion_qa
        self.assertEqual(remotion_qa.face_rect_cover((0,0,100,100),[dict(x=150,y=0,w=10,h=10)]),0)
        self.assertEqual(remotion_qa.face_rect_cover((0,0,100,100),[dict(x=50,y=0,w=100,h=100)]),.5)
    def test_quality_gate_uses_measured_browser_caption(self):
        import quality_gate
        result=dict(caption_metrics=dict(font_sizes_pct_h=[5],centres_y=[.99],centres_x=[.5],method='Measured DOM'),
                    face_safety=dict(verification='measured',max_cover=0),checks=[('export','ok','')],audio=dict(additions=False),fps=60,remotion_enter_frames=20)
        gate=quality_gate.evaluate(C.load_style(),[],[dict(type='broll',start=1,end=2)],2,dict(quality_targets=dict(caption_size_pct_h=[3,8],caption_position_y=[.5,.8],entrance_frames_30fps=[9,11])),result,[])
        rows={r['key']:r for r in gate['measurements']}
        self.assertEqual(rows['caption_size_pct_h']['status'],'pass');self.assertEqual(rows['caption_position_y']['status'],'fail')
        self.assertEqual(rows['entrance_frames_30fps']['value'],10);self.assertEqual(rows['entrance_frames_30fps']['status'],'pass')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RemotionTests))
    print(f'REMOTION NATIJA: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}')
    raise SystemExit(not result.wasSuccessful())
