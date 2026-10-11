"""Smoothness regressions (findings F1-F13 + variety): synthetic inputs, legacy styles untouched."""
from __future__ import annotations
import copy, json, math, subprocess, tempfile, unittest
from pathlib import Path
import numpy as np
import common as C
import auto_cut


class FrameRateTests(unittest.TestCase):
    def test_source_rate_rules(self):
        self.assertEqual(C.source_fps({'fps': 25.0, 'r_fps': 25.0}), (25.0, 'source'))
        self.assertEqual(C.source_fps({'fps': 29.47, 'r_fps': 30.0})[0], 30.0)            # VFR phone clip
        self.assertEqual(C.source_fps({'fps': 29.47, 'r_fps': 30.0})[1], 'vfr->nearest')
        self.assertEqual(C.source_fps({'fps': 26.0, 'r_fps': 26.0}), (25.0, 'odd->nearest'))
        self.assertEqual(C.fps_expr(30000 / 1001), '30000/1001')
        self.assertEqual(C.fps_expr(25.0), '25')

    def test_numeric_styles_pass_through_and_drafts_follow_source(self):
        legacy = {'video': {'fps': 30}, 'preview': {'fps': 15}}
        self.assertIs(C.resolve_fps(legacy, meta={'fps': 25.0}), legacy)
        new = C.resolve_fps({'video': {'fps': 'source'}, 'preview': {'fps': 'source'}}, meta={'fps': 25.0, 'r_fps': 25.0})
        self.assertEqual((new['video']['fps'], new['preview']['fps']), (25.0, 25.0))
        self.assertEqual(C.fps_of({'video': {'fps': 'source'}}), 30.0)

    def test_cut_frames_never_drift(self):
        keep = [{'start': i * 1.7, 'end': i * 1.7 + 1.0 + (i % 3) / 30} for i in range(40)]   # 30 fps grid plan
        fr = auto_cut.segment_frames(keep, 25.0)
        total = sum(k['end'] - k['start'] for k in keep)
        self.assertEqual(sum(n for _, n in fr), round(total * 25))
        acc = 0.0; frames = 0
        for k, (_, n) in zip(keep, fr):
            acc += k['end'] - k['start']; frames += n
            self.assertLessEqual(abs(frames / 25 - acc), .5 / 25 + 1e-9)
        same = auto_cut.segment_frames([{'start': .4, 'end': 1.2}, {'start': 2.0, 'end': 3.0}], 25.0)
        self.assertEqual(same, [(10, 20), (50, 25)])                                           # on-grid: exact


def _audio(path):
    raw = subprocess.run([C.need_tool('ffmpeg'), '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '48000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def _db(x):
    return 20 * math.log10(max(1e-7, float(np.sqrt(np.mean(x * x)))))


class CutAudioTests(unittest.TestCase):
    def test_crossfade_keeps_room_tone_and_sync(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            src = Path(td) / 'src.mp4'
            subprocess.run([C.need_tool('ffmpeg'), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=size=160x284:rate=25',
                            '-f', 'lavfi', '-i', 'anoisesrc=a=0.02:c=pink:r=48000:seed=7', '-t', '4', '-c:v', 'libx264', '-c:a', 'pcm_s16le',
                            '-pix_fmt', 'yuv420p', str(src.with_suffix('.mov'))], check=True)
            plan = {'fps': 25.0, 'speed': 1.0, 'settings': {'fade_ms': 15}, 'keep': [{'start': .2, 'end': 1.2}, {'start': 2.0, 'end': 3.0}]}
            dips = {}
            for name, xf in (('legacy', None), ('crossfade', 20)):
                st = C.load_style(); st['video']['fps'] = 25
                st['cut'].pop('crossfade_ms', None)
                if xf: st['cut']['crossfade_ms'] = xf
                out = Path(td) / f'{name}.mp4'
                auto_cut.apply_plan(src.with_suffix('.mov'), plan, out, st)
                a = _audio(out); n = 48000
                room = _db(a[int(.6 * n):int(.95 * n)])
                dips[name] = min(_db(a[i:i + 240]) for i in range(n - 960, n + 960, 120)) - room
                m = C.ffprobe_info(out)
                self.assertAlmostEqual(len(a) / 48000, 2.0, delta=.03)
                self.assertAlmostEqual(m['duration'], 2.0, delta=.05)
            self.assertLess(dips['legacy'], -12)           # fade to zero: a hole
            self.assertGreater(dips['crossfade'], -8)      # overlap: room tone continuous (5 ms noise varies ~3-5 dB)


def _vstyle(seed=7):
    import motion_language as ML
    st = C.load_style(); st['video'].update(width=360, height=640, fps=25)
    st['motion']['choice'] = {'enter': 'slide_overshoot', 'sub': 'mask_up', 'emphasis': 'underline_draw'}
    st['_variety'] = {'signature': 'slide_overshoot', 'others': ['mask_up', 'spring_pop', 'scale_blur'], 'sticker': 'spring',
                      'sticker_others': ['slide_left', 'fade_drift', 'pop'], 'transition': 'push', 'transition_others': ['cut', 'mask'],
                      'emphasis': 'underline_draw', 'seed': seed}
    return st


class VarietyTests(unittest.TestCase):
    CUES = ['bu **muhim** gap', 'oddiy gap', 'yana **asosiy** ibora', '!!90%!! bemorlar', 'nega shunday?', 'oddiy davom',
            'yana *katta* so‘z', 'tinch gap', '**natija** ko‘rinadi', 'oxirgi *urg‘u*', 'birinchi qadam', 'ikkinchi qadam']

    def plan(self, seed=7):
        import motion_language as ML
        return ML.caption_plan(_vstyle(seed), [{'text': t, 'start': 2 + i * 1.5} for i, t in enumerate(self.CUES)], 25)

    def test_caption_plan_is_varied_bounded_and_reproducible(self):
        import motion_language as ML
        a, b = self.plan(), self.plan()
        self.assertEqual(a, b)                                            # same video re-renders identically
        rep = ML.variety_report([p['enter'] for p in a])
        self.assertLessEqual(rep['longest_run'], 3)
        self.assertLessEqual(rep['max_share'], .6)
        self.assertGreaterEqual(len(rep['counts']), 3)
        num = a[3]
        self.assertEqual((num['role'], num['enter'] in ML.STRONG, num['emphasis']), ('number', True, 'pop_overshoot'))
        self.assertTrue(all(abs(p['jitter_ms']) <= 2 * 1000 / 25 + 1e-6 and abs(p['ease_k'] - 1) <= .03 for p in a))

    def test_legacy_styles_have_no_plan(self):
        import motion_language as ML
        st = C.load_style(); st['motion'].pop('variety_plan', None)
        self.assertIsNone(ML.caption_plan(st, [{'text': 'a', 'start': 0}], 25))
        els = [{'type': 'image', 'start': 0, 'end': 2, 'file': 'x.png'}]
        self.assertEqual(ML.element_plan(st, els), (els, []))

    def test_elements_moves_alternate_and_respect_explicit(self):
        import motion_language as ML
        els = [{'type': 'image', 'start': i, 'end': i + .8, 'file': 'x.png'} for i in range(9)]
        els += [{'type': 'broll', 'start': 10 + 2 * i, 'end': 11 + 2 * i, 'file': 'b.mp4'} for i in range(6)]
        els.append({'type': 'broll', 'start': 30, 'end': 31, 'file': 'b.mp4', 'fade': 0})
        out, moves = ML.element_plan(_vstyle(), els)
        st = [m for _, k, m in moves if k == 'image']
        self.assertLessEqual(ML.variety_report(st)['longest_run'], 3)
        slides = [m for m in st if m.startswith('slide')]
        self.assertTrue(all(x != y for x, y in zip(slides, slides[1:])))
        self.assertNotIn('transition', out[-1])
        self.assertGreaterEqual(len({m for _, k, m in moves if k == 'broll'}), 2)

    def test_zoom_variety_eased_varied_some_none(self):
        import motion_language as ML
        bounds = [(i * 2.0, i * 2.0 + 2.0) for i in range(12)]
        plan, moves = ML.zoom_variety(_vstyle(), bounds, 1.12, .03, .8)
        kinds = [m for _, _, m in moves]
        self.assertIn('none', kinds)
        levels = [z1 for t0, t1, z0, z1 in plan if z0 == 1.0 and z1 > 1.0]
        self.assertTrue(levels and all(1.04 <= z <= 1.10 for z in levels) and len(set(levels)) > 1)
        self.assertLessEqual(ML.variety_report(['in' if k != 'none' else k for k in kinds])['longest_run'], 3)

    def test_caption_layer_applies_per_cue_plan_and_gate_warns(self):
        import elements as E, quality_gate as QG
        ctx = E.Ctx(_vstyle())
        cap = E.CaptionLayer(ctx, [{'start': 2 + i * 1.5, 'end': 3.2 + i * 1.5, 'text': t} for i, t in enumerate(self.CUES)], None, 30)
        self.assertGreaterEqual(len({it['cfg']['anim_main'] for it in cap.items}), 3)
        bad = {'captions': {'n': 10, 'counts': {'a': 10}, 'longest_run': 10, 'max_share': 1.0},
               'motion': {'n': 4, 'counts': {'a': 2, 'b': 2}, 'longest_run': 1, 'max_share': .5}}
        rows = {r['key']: r['status'] for r in QG.evaluate(C.load_style(), [], [], 10, {}, {'checks': [], 'variety': bad})['measurements']}
        self.assertEqual((rows['captions_variety_run'], rows['captions_variety_share'], rows['motion_variety_run']), ('fail', 'fail', 'pass'))

    def test_broll_transitions_draw(self):
        import elements as E
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            img = Path(td) / 'b.png'
            import cv2; cv2.imwrite(str(img), np.full((640, 360, 3), 200, np.uint8))
            ctx = E.Ctx(_vstyle())
            for tr in ('push', 'mask', 'flash'):
                layer = E.build_elements(ctx, [{'type': 'broll', 'start': 0, 'end': 2, 'file': str(img), 'transition': tr}], 3)[0]
                early, late = (np.zeros((640, 360, 3), np.uint8) for _ in range(2))
                layer.draw(early, .08); layer.draw(late, 1.0)
                self.assertGreater(int(np.abs(late.astype(int) - early.astype(int)).sum()), 1000, tr)


class ExitTests(unittest.TestCase):
    def exit_frames(self, min_exit):
        import elements as E, motion as M, review_tools as RT
        st = _vstyle(); st.pop('_variety')
        st['motion'].pop('min_exit_frames', None)
        if min_exit: st['motion']['min_exit_frames'] = min_exit
        ctx = E.Ctx(st)
        cap = E.CaptionLayer(ctx, [{'start': 1.0, 'end': 1.5, 'text': 'qisqa gap'}], None, 3)
        M.TRACE = M.Trace()
        try:
            for f in range(20, 45):
                M.TRACE.begin_frame(f); M.TRACE.begin_layer('captions')
                cap.draw(np.zeros((640, 360, 3), np.uint8), f / 25)
            rows = [r for r in M.TRACE.rows if r[2].endswith('w0')]
        finally:
            M.TRACE = None
        last = max(r[0] for r in rows)
        fading = [r for r in rows if r[0] > last - 10 and r[8] < .98 and r[0] > 30]
        return len(fading)

    def test_exit_never_two_frames(self):
        self.assertLessEqual(self.exit_frames(None), 3)       # legacy behaviour kept when the key is absent
        self.assertGreaterEqual(self.exit_frames(5), 4)


class CutSyncTests(unittest.TestCase):
    def test_cues_land_off_the_cut_on_both_sides(self):
        import elements as E
        st = _vstyle(); st.pop('_variety'); st['motion']['cuts'] = {'enabled': True, 'offset_frames': 3}
        ctx = E.Ctx(st); ctx.cut_times = [2.0]
        cues = [{'start': 1.92, 'end': 2.8, 'text': 'oldin'}, {'start': 4.0, 'end': 5.0, 'text': 'uzoq'}]
        cap = E.CaptionLayer(ctx, cues, None, 6)
        self.assertAlmostEqual(cap.items[0]['start'], 2.0 + 3 / 25)
        self.assertAlmostEqual(cap.items[1]['start'], 4.0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
