"""Motion/SFX/evidence regression checks; GPU paths are mocked, never run on this CPU PC."""
from __future__ import annotations
import copy, json, math, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import numpy as np
import common as C
import elements as E
import motion as M
import motion_language as ML
import sound_design as SD
import hardware as H
import glyph_audit as G
import review_tools as RT
import audio_mix

class MotionTests(unittest.TestCase):
    def style(self):
        st=C.load_style(); st['video'].update(width=360,height=640,fps=30)
        st['motion']['choice']={'enter':'slide_overshoot','sub':'mask_up','emphasis':'underline_draw'}
        st['captions'].update(preset='clean',font='Inter',accent='#FFD040',position_y=.6)
        return st

    def test_uzbek_units_and_tracking(self):
        for text in ("o‘g‘il","o'g'il","oʻgʻil","ma’no"):
            units=ML.clusters(text)
            self.assertEqual(''.join(units),text)
            self.assertFalse(any(u in "'‘’ʻ" for u in units))
        ctx=E.Ctx(self.style()); cfg=ctx.caption_cfg({'animation':'letter_cascade'})
        block=E.RichBlock(ctx,'**o‘g‘il**',cfg)
        self.assertEqual(len(block.words[0]['letters']),4)
        font=ctx.fonts.get('Inter',32,700)
        self.assertAlmostEqual(M.text_advance(font,'o‘g‘',3),font.getlength('o‘g‘')+3)

    def test_font_glyph_warning_detects_real_gap(self):
        self.assertEqual(G.missing(C.ROOT/'style/fonts/Inter.ttf'),[])
        self.assertIn('ʻ',G.missing(C.ROOT/'style/fonts/Caveat.ttf'))

    def test_six_entrances_settle_and_exit_cleanly(self):
        settled=[]
        for mode in ML.ENTRANCES:
            st=self.style(); st['motion']['choice'].update(enter=mode,sub=mode,emphasis='scale_punch')
            ctx=E.Ctx(st); cfg=ctx.caption_cfg(); block=E.RichBlock(ctx,'**o‘g‘il** yaxshi',cfg)
            images=[]
            for t in (-.01,.08,.9,2.01):
                im=np.zeros((640,360,3),np.uint8); block.draw(im,180,380,t,None,cfg,0,2); images.append(im)
            self.assertFalse(images[0].any(),mode)
            self.assertTrue(images[1].any(),mode)
            self.assertTrue(images[2].any(),mode)
            self.assertFalse(images[3].any(),mode)
            settled.append(images[2])
        for im in settled[1:]: np.testing.assert_array_equal(im,settled[0])

    def test_emphasis_changes_pixels_without_text_or_time_changes(self):
        frames=[]
        for effect in ML.EMPHASIS:
            st=self.style(); st['motion']['choice']['emphasis']=effect
            ctx=E.Ctx(st); cfg=ctx.caption_cfg(); block=E.RichBlock(ctx,'**87%**',cfg)
            im=np.zeros((640,360,3),np.uint8); block.draw(im,180,380,.18,[0],cfg,0,2)
            self.assertEqual(block.plain_words,['87%']); self.assertTrue(im.any()); frames.append(im)
        self.assertEqual(len({im.tobytes() for im in frames}),4)

    def test_colour_sweep_handles_different_glow_padding(self):
        st=self.style(); st['motion']['choice']['emphasis']='colour_sweep'
        st['captions'].update(glow={'blur':36,'opacity':.8},shadow={'blur':16,'dy':4,'opacity':.35})
        ctx=E.Ctx(st); cfg=ctx.caption_cfg(); block=E.RichBlock(ctx,'**o‘g‘il**',cfg)
        self.assertNotEqual(block.words[0]['spr'].h,block.words[0]['sweep'].h)
        for t in (.1,.3,.6):
            frame=np.zeros((640,360,3),np.uint8); block.draw(frame,180,380,t,[0],cfg,0,2)
            self.assertTrue(frame.any())
        for mode in ('letter_cascade','typewriter'):
            lc=ctx.caption_cfg({'animation':mode}); letters=E.RichBlock(ctx,'**o‘g‘il**',lc)
            self.assertIn('sweep_letters',letters.words[0])
            for t in (.1,.3,.6):
                frame=np.zeros((640,360,3),np.uint8); letters.draw(frame,180,380,t,[0],lc,0,2)
                self.assertTrue(frame.any())

    def test_config_override_legacy_and_invalid(self):
        st=self.style(); ctx=E.Ctx(st)
        self.assertEqual(ctx.caption_cfg({'animation':'none'})['anim_main'],'none')
        cue=E.CaptionLayer(ctx,[dict(start=0,end=2,text='{caps} **SO‘Z**')],None,2).items[0]
        self.assertEqual(cue['cfg']['anim_main'],'slide_overshoot')
        self.assertEqual(cue['cfg']['anim_ms'],260)
        legacy=copy.deepcopy(st); legacy.pop('motion'); ctx=E.Ctx(legacy)
        self.assertNotIn('_motion',ctx.caption_cfg())
        layer=E.Layer(0,2); layer.ctx=ctx
        self.assertEqual(layer.appear(.1,0,2),E.appear(.1,0,2))
        cfg=ML.config(st); fast=C.deep_merge(st,{'motion':{'speed':'fast'}})
        self.assertEqual(ML.config(C.deep_merge(st,{'motion_override':{'speed':'slow'}}))['speed'],'slow')
        self.assertLess(ML.duration(ML.config(fast),'caption'),ML.duration(cfg,'caption'))
        for over in ({'durations_ms':{'caption':float('nan')}},{'stagger':{'word_ms':-1}}, {'choice':{'sub':'bad'}}):
            with self.assertRaises(C.MontajError): ML.config(C.deep_merge(st,{'motion':over}))

    def test_choice_persists_and_next_job_differs(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR,prefix='motion-test-') as td:
            st=self.style(); st['motion']['choice']={}
            with patch.object(C,'TEMP_DIR',Path(td)):
                a=ML.choose(st,Path(td)/'video1'); b=ML.choose(st,Path(td)/'video2')
                again=ML.choose(st,Path(td)/'video1')
            self.assertEqual(a['motion']['choice'],again['motion']['choice'])
            self.assertNotEqual(a['motion']['choice'],b['motion']['choice'])

    def test_parallel_choice_only_writes_own_folder(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR,prefix='motion-test-') as td:
            st=self.style(); st['motion']['choice']={}; root=Path(td)
            with patch.object(C,'TEMP_DIR',root),patch('handoff.unfinished_notes',return_value=[{'note':str(root/'other'/'HOLAT.md')} ]):
                ML.choose(st,root/'mine')
            self.assertTrue(C.read_json(root/'mine'/'motion_choice.json')['history_deferred'])
            self.assertFalse((root/'.motion_history').exists())
            self.assertFalse((root/'other').exists())

    def test_sfx_lead_density_variants_and_manual(self):
        st=self.style(); st['sfx'].update(min_gap_sec=.1,max_per_10_sec=3,lead_frames=3)
        els=[dict(type='image',start=t,end=t+1) for t in (1,2,3,4,11.3,12.3)]
        els.append(dict(type='sfx',at=20,name='tick',volume_db=-18))
        ev=SD.gather(st,els,[],None)
        auto=[e for e in ev if e['kind']!='manual']
        self.assertEqual(len(auto),5)
        for e in auto: self.assertAlmostEqual(e['visual_at']-e['at'],.1)
        for a,b in zip(auto,auto[1:]): self.assertNotEqual(a['name'],b['name'])
        for e in auto: self.assertLessEqual(sum(e['at']-10<o['at']<=e['at'] for o in ev),3)
        strong=C.deep_merge(st,{'sfx':{'profile':'stronger'}}); other=SD.gather(strong,els,[],None)
        self.assertEqual([(e['at'],e['name']) for e in ev],[(e['at'],e['name']) for e in other])
        self.assertTrue(all(b['volume_db']-a['volume_db']==16 for a,b in zip(ev,other)))

    def test_sfx_all_visual_event_routes(self):
        st=self.style(); st['sfx'].update(min_gap_sec=0,max_per_10_sec=50)
        els=[dict(type=t,start=2+i,end=15,items=[{'at':2+i}],tap=.5) for i,t in enumerate(('image','broll','label','stat','follow','title'))]
        ev=SD.gather(st,els,[dict(start=.5,end=1,text='**87%**')],None)
        self.assertEqual({e['kind'] for e in ev},{'hero','sticker','broll_in','label','number','follow_tap','title'})

    def test_evidence_range_validation(self):
        ts=RT.timepoints(1,2,12,3); self.assertEqual(len(ts),12)
        self.assertEqual(ts[0],1); self.assertEqual(ts[-1],2)
        for vals in ((2,1,12,3),(0,4,12,3),(0,2,1,3)):
            with self.assertRaises(C.MontajError): RT.timepoints(*vals)

    def test_real_audio_cue_stems_music_and_mix_difference(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR,prefix='cue-test-') as td:
            root=Path(td); video=root/'voice.wav'; music=root/'music.wav'; ff=C.need_tool('ffmpeg')
            C.run([ff,'-hide_banner','-nostdin','-v','error','-y','-f','lavfi','-i','sine=frequency=240:duration=2',
                   '-c:a','pcm_s16le',str(video)])
            C.run([ff,'-hide_banner','-nostdin','-v','error','-y','-f','lavfi','-i','sine=frequency=520:duration=2',
                   '-c:a','pcm_s16le',str(music)])
            # Keep this fixture above the existing meter's -70dB overlap gate.
            st=self.style(); st['audio'].update(voice='off',voice_margin_db=10,music_volume_db=-26)
            reports=[]
            for profile in ('subtle','stronger'):
                gain=SD.mix_gain(dict(st['sfx'],profile=profile))
                events=[{'at':.9,'name':'pop','kind':'hero','visual_at':1,'lead_frames_actual':3,'volume_db':-14+gain}]
                folder=root/profile
                audio_mix.build_audio(video,folder/'mix.wav',st,2,music,events)
                report=C.read_json(folder/'audio_cues.json'); reports.append(report)
                self.assertEqual([e['kind'] for e in report['events']],['hero','music'])
                self.assertEqual(report['events'][0]['lead_frames_actual'],3)
                self.assertTrue(all(math.isfinite(e['sample_peak_dbfs']) for e in report['events']))
                self.assertTrue((folder/'audio_waveform.png').is_file())
                self.assertGreaterEqual(report['final_bus_margin_percentile_db'],9.5)
            self.assertGreater(reports[1]['events'][0]['sample_peak_dbfs'],reports[0]['events'][0]['sample_peak_dbfs']+5)
            self.assertEqual(reports[0]['voice'],reports[1]['voice'])

    def test_hardware_cpu_detection_and_cuda_init_fallback(self):
        with patch.object(H,'cuda_count',return_value=0):
            self.assertFalse(H.encoder(self.style()))
            self.assertEqual(H.whisper_device({'device':'auto','compute_type':'auto'}),('cpu','int8'))
            self.assertEqual(H.onnx_providers(),['CPUExecutionProvider'])
        import transcribe as T
        model=MagicMock(side_effect=[RuntimeError('CUDA library missing'),SimpleNamespace(model=SimpleNamespace(device='cpu'))])
        with patch.object(T,'_fw_import',return_value=model),patch.object(T,'ensure_model',return_value={'path':'cached','bytes':0}),patch.object(C,'memory_status',return_value=None):
            T.load_model({'model':'cached','device':'cuda','compute_type':'float16'})
        self.assertEqual(model.call_args_list[0].kwargs['device'],'cuda')
        self.assertEqual(model.call_args_list[1].kwargs['device'],'cpu')
        self.assertEqual(model.call_args_list[1].kwargs['compute_type'],'int8')

    def test_cuda_generator_failure_retries_entire_transcript(self):
        import transcribe as T
        gpu=SimpleNamespace(model=SimpleNamespace(device='cuda'),transcribe=MagicMock(side_effect=RuntimeError('CUDA error')))
        cpu=SimpleNamespace(model=SimpleNamespace(device='cpu'),transcribe=lambda *a,**kw:(iter([]),SimpleNamespace(language='uz',language_probability=1,duration=1)))
        with patch.object(T,'load_model',return_value=cpu) as load:
            result=T.transcribe_audio(Path('unused.wav'),{'model':'cached','device':'cuda'},gpu)
        self.assertEqual(result['words'],[])
        self.assertEqual(load.call_args.args[0]['device'],'cpu')
        self.assertFalse(load.call_args.kwargs['allow_download'])

    def test_onnx_inference_falls_back_to_cpu(self):
        import person_mask as P
        seg=P.PersonMask.__new__(P.PersonMask)
        seg.net=MagicMock(); seg.net.forward.return_value=np.ones((1,2,192,192),np.float32)
        seg.ort_session=MagicMock(); seg.ort_session.run.side_effect=RuntimeError('CUDA error')
        alpha=seg.infer(np.zeros((80,60,3),np.uint8))
        self.assertIsNone(seg.ort_session); self.assertEqual(alpha.shape,(80,60))
        seg.net.forward.assert_called_once()

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MotionTests))
    print(f'MOTION NATIJA: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}')
    raise SystemExit(not result.wasSuccessful())
