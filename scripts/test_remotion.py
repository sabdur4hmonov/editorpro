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

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RemotionTests))
    print(f'REMOTION NATIJA: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}')
    raise SystemExit(not result.wasSuccessful())
