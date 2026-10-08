"""Feedback fixes: fallback glyph pixels, bounded browser retry and real SFX preference."""
import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import common as C
import motion as M
import html_render as HR
import sound_design as SD
import sfx_library as SL

class Part0Tests(unittest.TestCase):
    def test_fallback_only_missing_character_and_real_pixels(self):
        fonts=M.Fonts([C.ROOT/'style/fonts'])
        f=fonts.get('Caveat',72,400)
        self.assertIs(f.character_font('o'), f.primary)
        self.assertEqual(f.character_font('ʻ').getname()[0], 'Inter')
        self.assertIs(f.character_font('g'), f.primary)
        spr,adv=M.text_sprite('ʻ', f, '#FFFFFF')
        expected,ea=M.text_sprite('ʻ',fonts.get('Inter',72,400),'#FFFFFF')
        # Extract occupied pixels, independent of differing baseline padding.
        def crop(s):
            y,x=np.nonzero(s.pix[:,:,3]); return s.pix[y.min():y.max()+1,x.min():x.max()+1]
        np.testing.assert_array_equal(crop(spr),crop(expected))
        self.assertEqual(adv,ea)
        self.assertGreater(M.text_sprite('oʻgʻil',f,'#FFFFFF',3)[1],0)

    def test_retry_logs_failure_and_success_and_new_profile(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            page=Path(td)/'page.html'; shot=Path(td)/'page.png'
            with patch.object(HR.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='',stdout='')) as run, \
                 patch.object(HR,'wait_for_shot',side_effect=[False,True]),patch.object(C,'warn') as warn:
                _,attempts=HR.browser_shot(['edge','--user-data-dir=old'],shot,page)
            self.assertEqual(attempts,2); warn.assert_called_once()
            self.assertNotEqual(run.call_args_list[0].args[0],run.call_args_list[1].args[0])
            rows=[json.loads(s) for s in (Path(td)/'browser_attempts.jsonl').read_text().splitlines()]
            self.assertEqual([r['ready'] for r in rows],[False,True])
            self.assertTrue(all(r['time_utc'] for r in rows))

    def test_retry_remains_bounded_clear_failure(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            with patch.object(HR.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='no PNG',stdout='')) as run, \
                 patch.object(HR,'wait_for_shot',return_value=False):
                with self.assertRaisesRegex(C.MontajError,'Brauzer rasm chiqarmadi'):
                    HR.browser_shot(['edge'],Path(td)/'x.png',Path(td)/'x.html')
            self.assertEqual(run.call_count,2)

    def test_real_preference_and_unverified_exclusion(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            root=Path(td); category=root/'assets/sfx/pop'; category.mkdir(parents=True)
            real=category/'real.wav'; synth=category/'synth.wav'; unknown=category/'unknown.wav'
            for path in (real,synth,unknown): path.write_bytes(b'test')
            for path,kind in ((real,'real'),(synth,'synthesized')):
                C.write_json(dict(source='https://example.test/source',license='fixture licence',kind=kind),path.with_suffix('.wav.credit.json'))
                path.with_suffix('.wav.LICENSE.txt').write_text('fixture licence')
            with patch.object(C,'ROOT',root):
                self.assertEqual(SD.variants('pop'),[real])
                real.with_suffix('.wav.LICENSE.txt').write_text('UNVERIFIED')
                self.assertEqual(SD.variants('pop'),[synth])
                self.assertFalse(SL.provenance(unknown)['usable'])

    def test_sticker_and_broll_not_starved_by_hero_captions(self):
        st=C.load_style(); st['sfx'].update(min_gap_sec=.1,max_per_10_sec=3)
        cues=[dict(start=i,end=i+.6,text='**so‘zi**') for i in (1,2,3,4)]
        events=SD.gather(st,[dict(type='image',start=5,end=7),dict(type='broll',start=8,end=11)],cues,None)
        self.assertEqual(len(events),3)
        self.assertIn('sticker',[e['kind'] for e in events])
        self.assertIn('broll_in',[e['kind'] for e in events])

if __name__=='__main__': unittest.main(verbosity=2)
