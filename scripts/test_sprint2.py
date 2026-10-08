"""Measured dynamics, conservative candidate approval and real native export checks."""
import copy, tempfile, unittest, subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import common as C
import energy_curve as EC
import broll_system as B
import editor_export as EX
import elements as E
import audio_mix as AM

class Sprint2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=C.TEMP_DIR,prefix='sprint2_test_'); self.work=Path(self.tmp.name)
        self.style=C.load_style(); self.style['video'].update(width=180,height=320,fps=30)
        self.style['dynamics'].update(enabled=True,smooth_seconds=1,hook_seconds=0)
    def tearDown(self): self.tmp.cleanup()
    def test_word_union_pauses_rate_rms_and_controls(self):
        data=np.concatenate([np.zeros(1000),np.full(1000,.2)])
        words=[dict(start=1,end=1.6),dict(start=1.3,end=1.9)]
        report=EC.analyze(data,1000,words,[],2,self.style)
        calm,peak=report['seconds']; self.assertEqual(calm['words_per_second'],0)
        self.assertEqual(peak['words_per_second'],2); self.assertAlmostEqual(peak['pause_fraction'],.1)
        self.assertAlmostEqual(peak['rms_dbfs'],-13.98,places=2)
        for key in ('zoom','caption_intensity','sfx_per_10s','background_speed'):
            self.assertGreater(peak['controls'][key],calm['controls'][key])
        self.assertLess(peak['controls']['element_gap_seconds'],calm['controls']['element_gap_seconds'])
    def test_structure_override_and_continuous_background(self):
        self.style['dynamics']['structure_overrides']=[dict(start=1,end=2,label='cta')]
        r=EC.analyze(np.zeros(2000),1000,[],[],2,self.style); self.assertEqual(r['seconds'][1]['structure'],'cta')
        st=dict(self.style,_energy=r); self.assertLess(abs(EC.clock(st,1)-EC.clock(st,1-1e-6)),1e-5)
    def test_automatic_element_density_preserves_explicit(self):
        el=[dict(type='icon',start=t,end=t+.5,automatic=True) for t in (0,1,7)]
        el.append(dict(type='image',start=1.1,end=2))
        r=EC.analyze(np.zeros(8000),1000,[],[],8,self.style,el)
        self.assertEqual(len(r['skipped_automatic_elements']),1)
        self.assertIn(el[-1],r['elements'])
    def test_no_speech_retime_and_visual_cut_spacing(self):
        cues=[dict(start=i,end=i+.6,text='qiyin holat') for i in range(10)]
        saved=copy.deepcopy(cues); r=EC.analyze(np.ones(10000)*.1,1000,[],cues,10,self.style)
        self.assertEqual(cues,saved); times=[e['start'] for e in r['events']]
        self.assertTrue(all(b-a>=2.8 for a,b in zip(times,times[1:])))
    def test_beat_onset_is_local_numpy_detection(self):
        sr=16000; data=np.zeros(sr*3)
        for t in (.5,1.5,2.5):
            i=int(t*sr); data[i:i+800]=np.sin(np.arange(800)*.5)*np.exp(-np.arange(800)/180)
        hits=EC.beats(data,sr,EC.config(self.style)['beat'])
        for t in (.5,1.5,2.5): self.assertTrue(any(abs(h-t)<.1 for h in hits),(t,hits))
    def test_query_rank_cannot_admit_unrelated_meat_or_diving(self):
        self.assertFalse(B.relevance({'title':'raw meat'},dict(query='hospital bed')))
        self.assertFalse(B.relevance({'title':'diving helmet'},dict(query='medical oxygen mask equipment')))
        self.assertTrue(B.relevance({'title':'Hospital Bed 2011'},dict(query='hospital bed')))
    def test_long_static_span_across_short_captions_is_ranked(self):
        cues=[dict(start=i,end=i+1,text='oddiy gap') for i in (0,4,8)]
        moments=B.moments(cues,self.style,[])
        self.assertEqual(len(moments),1);self.assertIn('long static',moments[0]['reasons'][0])
        self.assertEqual(moments[0]['query'],'')  # Ask for a meaningful visual, do not retrieve generic stock.
    def test_cover_middle_top_anchor_draws_missing_glyph(self):
        import motion as M
        from PIL import ImageDraw
        font=E.Ctx(self.style).fonts.get('Caveat',42,700)
        image=Image.new('RGB',(180,100)); M.draw_text(ImageDraw.Draw(image),(90,10),'oʻgʻil',font=font,fill='white',anchor='mt')
        bbox=image.getbbox(); self.assertIsNotNone(bbox); self.assertGreaterEqual(bbox[1],9)
        self.assertLessEqual(bbox[1],11); self.assertLess(bbox[0],90); self.assertGreater(bbox[2],90)
    def test_exact_crop_resolution_and_duration(self):
        path=self.work/'wide.jpg'; Image.new('RGB',(1600,900),'#CD9270').save(path)
        c,crop=B.inspect(dict(file=str(path),title='hospital bed',credit={'license':'cc0'}),
                         Image.new('RGB',(540,960),'#CD9270'),dict(query='hospital bed',start=0,end=3),self.style,self.work)
        self.assertAlmostEqual(c['checks']['crop_9_16']['retained_area'],.3164,places=4)
        self.assertFalse(c['checks']['resolution']['ok']); self.assertFalse(c['technical_ok'])
        self.assertEqual(c['checks']['text_watermark_logo']['status'],'human_review_required')
    def test_sticker_preview_preserves_whole_object(self):
        path=self.work/'oxygen.png'; Image.new('RGBA',(600,200),(255,50,50,150)).save(path)
        c,crop=B.inspect(dict(file=str(path),title='oxygen mask',credit={'license':'cc0'}),
                       Image.new('RGB',(540,960),'#FF3333'),dict(query='oxygen mask',start=0,end=3),self.style,self.work)
        self.assertTrue(c['alpha']); self.assertEqual(crop.size,(540,960))
        self.assertTrue(c['checks']['resolution']['ok'])
    def test_grey_sticker_background_cannot_fake_colour(self):
        path=self.work/'grey.png'; Image.new('RGBA',(600,200),(100,100,100,150)).save(path)
        c,_=B.inspect(dict(file=str(path),title='oxygen mask',credit={'license':'cc0'}),
                     Image.new('RGB',(540,960),'#FF3333'),dict(query='oxygen mask',start=0,end=3),self.style,self.work)
        self.assertEqual(c['checks']['colour']['mean_saturation'],0);self.assertFalse(c['technical_ok'])
    def test_mixed_search_requests_video_and_photo(self):
        video=self.video(); moment=dict(id='x',start=0,end=2.5,query='hospital bed',text='bed')
        with patch.object(C,'ffprobe_info',return_value={'duration':4}),patch.object(B,'preview',return_value=Image.new('RGB',(540,960),'red')),patch.object(B.images,'search',return_value={'candidates':[]}) as search:
            B.prepare(video,[],self.style,self.work/'broll',[],[moment],kind='mixed')
        self.assertEqual([call.args[3] for call in search.call_args_list],['video','photo'])
    def test_video_duration_and_three_sample_checks(self):
        file=self.work/'short.mp4'
        C.run([C.need_tool('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=c=orange:s=540x960:r=30:d=1','-c:v','libx264',str(file)])
        c,_=B.inspect(dict(file=str(file),title='hospital bed',credit={'license':'cc0'}),
            Image.new('RGB',(540,960),'orange'),dict(query='hospital bed',start=0,end=3),self.style,self.work)
        self.assertFalse(c['checks']['duration']['ok']);self.assertFalse(c['technical_ok'])
        self.assertEqual(len(c['checks']['text_watermark_logo']['sample_seconds']),3)
    def test_written_approval_and_visual_review_required(self):
        c=dict(id='a',number=1,technical_ok=True,rank=.9,visual_review=None,file='a.png',alpha=True)
        plan={'moments':[dict(moment=dict(id='m',start=0,end=3,text='oxygen'),candidates=[c])]}
        with self.assertRaises(C.MontajError): B.accept(plan,{'m':'auto'},'',self.style,{},self.work)
        output,_=B.accept(plan,{'m':'auto'},'auto',self.style,{},self.work); self.assertEqual(output,[])
        c['visual_review']='ok'; output,history=B.accept(plan,{'m':1},'1',self.style,{},self.work)
        self.assertEqual(len(output),1); self.assertEqual(history['entries'][0]['reason'],'1')
    def test_rejection_reason_changes_future_rank(self):
        c=dict(id='a',score=.8,title='adult patient',file='x',checks={'colour':{'mean_saturation':.5}})
        history=B.reject({},c,'adult instead of child'); self.assertLess(B.history_score(c,{'query':'child patient'},history),0)
        votes={'entries':[dict(asset_id='a',status='accepted',reason='yes')]*40+history['entries']}
        self.assertLess(B.history_score(c,{'query':'child patient'},votes),0)
        with self.assertRaises(C.MontajError): B.reject({},c,'')
    def test_source_cut_mapping_timecodes_and_unsupported_retime(self):
        cuts=EX.cut_list([[0,2],[3,4]],30,108000)
        self.assertEqual(cuts,EX.cut_list([{'start':0,'end':2},{'start':3,'end':4}],30,108000))
        self.assertEqual(cuts[1]['record_in'],60); self.assertEqual(cuts[1]['source_in_tc'],'01:00:03:00')
        self.assertEqual(cuts[1]['record_out'],90)
        with self.assertRaises(C.MontajError): EX.cut_list([[0,2]],29.97)
        with self.assertRaises(C.MontajError): EX.cut_list([[0,2]],30,speed=1.1)
        with self.assertRaises(C.MontajError): EX.cut_list([[3,4],[1,2]],30)
    def test_conform_24fps_source_preserves_seconds_and_original(self):
        source=self.work/'original24.mp4'
        C.run([C.need_tool('ffmpeg'),'-v','error','-y','-f','lavfi','-i','testsrc2=s=180x320:r=24:d=2','-c:v','libx264',str(source)])
        digest=B.asset_id(source); file,note=EX.conform_source(source,30,self.work)
        self.assertEqual(C.ffprobe_info(file)['fps'],30)
        self.assertAlmostEqual(C.ffprobe_info(file)['duration'],2,places=2)
        self.assertEqual(B.asset_id(source),digest); self.assertEqual(note['original_average_fps'],24)
    def video(self):
        path=self.work/'cut.mp4'
        C.run([C.need_tool('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=c=gray:s=180x320:r=30:d=1',
               '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1','-c:v','libx264','-c:a','aac','-shortest',str(path)])
        return path
    def test_real_xml_media_and_range_roundtrip(self):
        video=self.video(); clip=dict(file=str(video),record_in=0,record_out=30,source_in=0,source_out=30)
        EX.write_xml(self.work/'timeline.xml',[dict(kind='video',clips=[clip])],30,180,320,30,'x')
        loaded=EX.read_xml(self.work/'timeline.xml')[0]['clips'][0]
        self.assertEqual(loaded['record_out'],30); self.assertEqual(loaded['pathurl'],video.resolve().as_uri())
    def test_actual_prores_alpha_survives_encode_decode(self):
        st=copy.deepcopy(self.style); st['dynamics']['enabled']=False
        image=self.work/'opaque.png'; Image.new('RGBA',(100,100),(240,90,50,255)).save(image)
        layer=E.build_elements(E.Ctx(st),[dict(type='image',start=0,end=1,file=str(image),y=.4,width=.5,anim='none',radius=0)],1)[0]
        file=self.work/'alpha.mov'; EX.render_alpha(layer,file,0,1,st)
        self.assertTrue(C.ffprobe_info(file)['alpha'])
        result=subprocess.run([C.need_tool('ffmpeg'),'-v','error','-ss','0.5','-i',str(file),'-frames:v','1','-pix_fmt','rgba','-f','rawvideo','-'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace')); rgba=np.frombuffer(result.stdout,np.uint8).reshape(320,180,4)
        self.assertEqual(rgba[:,:,3].min(),0); self.assertGreater(rgba[:,:,3].max(),200)
    def test_real_stems_exist_and_speech_preserved_without_effects(self):
        video=self.video(); st=copy.deepcopy(self.style); st['audio']['export_stems']=True; st['sfx']['enabled']=False
        AM.build_audio(video,self.work/'mix.wav',st,1)
        for name in ('speech','sfx','music'):
            self.assertAlmostEqual(C.ffprobe_info(self.work/'stems'/(name+'.wav'))['duration'],1,places=2)
        import review_tools as RT
        mixed,_=RT.pcm(self.work/'mix.wav'); speech,_=RT.pcm(self.work/'stems/speech.wav')
        np.testing.assert_array_equal(mixed,speech)

    def test_complete_editor_package_and_validation_detects_corrupt_xml(self):
        video=self.video(); st=copy.deepcopy(self.style); st['dynamics']['enabled']=False
        st['zoom'].update(enabled=True,face_aware=False); st['sfx']['enabled']=False
        subs=self.work/'subs.srt'; C.write_srt([dict(start=0,end=.9,text="o‘g‘il **yaxshi**")],subs)
        image=self.work/'graphic.png'; Image.new('RGBA',(100,100),(220,80,30,200)).save(image)
        package=self.work/'editor'
        report=EX.export(video,video,{'keep':[[0,1]],'speed':1},st,subs,[],
              [dict(type='image',start=0,end=1,file=str(image),x=.5,y=.4,width=.5,anim='none')],package)
        self.assertTrue(report['ok']); self.assertEqual(report['graphics'],1)
        manifest=C.read_json(package/'manifest.json'); self.assertEqual(manifest['captions'][0]['text'],'o‘g‘il yaxshi')
        self.assertEqual(len([t for t in manifest['timeline_tracks'] if t['kind']=='audio']),6)
        xml=package/'timeline.xml'; text=xml.read_text(encoding='utf-8'); xml.write_text(text.replace('<end>30</end>','<end>29</end>',1),encoding='utf-8')
        with self.assertRaisesRegex(C.MontajError,'range mismatch'):EX.validate(package)

if __name__=='__main__': unittest.main(verbosity=2)
