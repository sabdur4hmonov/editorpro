"""Motion polish regressions: lint, slow-motion review, sub-pixel, cuts, scrim, emphasis, motion blur,
templates, mask reveal, brand presets. Synthetic inputs only; legacy styles must stay untouched."""
from __future__ import annotations
import copy, json, subprocess, tempfile, unittest
from pathlib import Path
import numpy as np
import common as C
import compose
import elements as E
import motion as M
import motion_language as ML
import quality_gate as QG
import review_tools as RT


def style(**motion):
    st = C.load_style()
    st['video'].update(width=360, height=640, fps=30)
    st['motion']['choice'] = {'enter': 'slide_overshoot', 'sub': 'mask_up', 'emphasis': 'underline_draw'}
    st['motion'] = C.deep_merge(st['motion'], motion)
    st['captions'].update(preset='clean', font='Inter', accent='#FFD040', position_y=.6)
    return st


def row(f, layer, tag, x, y=100., w=50., op=1., sc=1.):
    return (f, layer, tag, x, y, w, 20., sc, op)


class LintTests(unittest.TestCase):
    def flags(self, rows, cuts=(), rng=None):
        return RT.lint_rows(rows, 30, 1.0, cuts, 2, rng)

    def test_linear_jump_short_flagged_eased_clean(self):
        rows = [row(f, 'a', 'lin', 100 + 6 * f) for f in range(12)] + [row(f, 'a', 'lin', 166) for f in range(12, 15)]
        rows += [row(f, 'b', 'jmp', 100 if f < 5 else 140) for f in range(10)]
        rows += [row(f, 'c', 'pop', 100, w=50 + (8 if f in (3, 4) else 0)) for f in range(10)]
        rows += [row(f, 'd', 'ease', 100 + 60 * (1 - (1 - min(1, f / 10)) ** 3), op=min(1, f / 3 + .2)) for f in range(16)]
        rep = self.flags(rows)
        by = {(fl['flag'], fl.get('track')) for fl in rep['flags']}
        self.assertIn(('linear', 'a/lin'), by)
        self.assertIn(('velocity_jump', 'b/jmp'), by)
        self.assertIn(('short', 'c/pop'), by)
        self.assertFalse([fl for fl in rep['flags'] if fl.get('track') == 'd/ease'])

    def test_at_once_and_cut_rules(self):
        rows = [row(f, 'x', f't{i}', 50 * i, op=min(1, (f - 10) / 4 + .1)) for i in range(6) for f in range(10, 20)]
        rows += [row(f, 'captions', 'c0:w0', 100, op=min(1, (f - 30) / 4 + .1)) for f in range(30, 40)]   # onset on cut 30
        rows += [row(f, 'captions', 'c1:w0', 200, op=min(1, (f - 62) / 4 + .1)) for f in range(62, 70)]  # 2 frames off cut 60
        rows += [row(f, 'sticker', 's', 300 if f < 60 else 312) for f in range(50, 70)]                   # jumps at cut
        rows += [row(f, 'captions', 'c2:w0', 100, 400 + (0 if f < 85 else 4 * (f - 84)), op=1 - max(0, f - 84) * .3) for f in range(80, 88)]
        rows += [row(f, 'captions', 'c3:w0', 100, 440 - 4 * min(5, f - 88), op=min(1, (f - 88) / 3 + .2)) for f in range(88, 96)]
        rep = self.flags(rows, cuts=(1.0, 2.0, 88 / 30))
        names = [fl['flag'] for fl in rep['flags']]
        self.assertIn('all_at_once', names)
        self.assertEqual([fl['frame'] for fl in rep['flags'] if fl['flag'] == 'caption_on_cut'], [30, 88])
        self.assertIn('jump_at_cut', names)
        self.assertIn('direction_mismatch', names)

    def test_drift_jitter_and_curves_png(self):
        steps = [row(f, 'captions', 'c0:w0', 100 + round(.3 * f)) for f in range(30)]
        smooth = [row(f, 'captions', 'c1:w0', 100 + .3 * f) for f in range(30)]
        a, b = self.flags(steps), self.flags(smooth)
        self.assertGreater(a['summary']['pixel_steps'] + (a['summary']['drift_jitter_px'] or 0), .5)
        self.assertLess(b['summary']['drift_jitter_px'], .02)
        with tempfile.TemporaryDirectory() as td:
            pngs = RT.lint_curves(steps, a, td)
            self.assertTrue(pngs and Path(pngs[0]).stat().st_size > 1000)


class RenderTests(unittest.TestCase):
    def test_adjacent_caption_scrims_have_distinct_trace_identity(self):
        st=style(scrim={'enabled':True,'max_alpha':.9})
        ctx=E.Ctx(st)
        cap=E.CaptionLayer(ctx,[{'start':0,'end':1,'text':'bir'},
                              {'start':1,'end':2,'text':'uzunroq ikkinchi gap'}],None,2)
        M.TRACE=M.Trace()
        for f,t in ((15,.5),(45,1.5)):
            M.TRACE.begin_frame(f);M.TRACE.begin_layer('captions')
            cap.draw(np.full((640,360,3),220,np.uint8),t)
        tags={r[2] for r in M.TRACE.rows if r[2].endswith('scrim')}
        self.assertEqual(tags,{'c0:scrim','c1:scrim'})
        cap.close()

    def tearDown(self):
        M.SUBPIXEL, M.TRACE = False, None

    def centroid(self, frame):
        g = frame[..., 0].astype(np.float64)
        return float((g.sum(0) * np.arange(g.shape[1])).sum() / g.sum())

    def test_subpixel_drift_has_no_integer_stairs(self):
        spr = M.rounded_rect_sprite(20, 20, 4, (255, 255, 255, 255))
        out = {}
        for mode in (False, True):
            M.SUBPIXEL = mode
            M.TRACE = M.Trace() if mode else None
            xs = []
            for f in range(20):
                if M.TRACE: M.TRACE.begin_frame(f); M.TRACE.begin_layer('t')
                fr = np.zeros((60, 120, 3), np.uint8)
                M.blit(fr, spr, 30 + .3 * f, 20, tag='s')
                xs.append(self.centroid(fr))
            out[mode] = np.diff(xs)
        self.assertTrue(set(np.round(out[False], 3)) <= {0.0, 1.0})
        self.assertLess(float(np.abs(out[True] - .3).max()), .03)

    def test_subpixel_resting_sprite_stays_sharp(self):
        M.SUBPIXEL, M.TRACE = True, M.Trace()
        spr = M.Sprite(np.full((10, 10, 4), 255, np.uint8))
        for f in range(3):
            M.TRACE.begin_frame(f); M.TRACE.begin_layer('t')
            fr = np.zeros((30, 30, 3), np.uint8)
            M.blit(fr, spr, 10.4, 10, tag='s')
        self.assertEqual(int(fr[..., 0].max()), 255)
        self.assertEqual(sorted(set(np.unique(fr[..., 0]).tolist())), [0, 255])

    def test_fractional_rest_opt_out_does_not_snap_after_motion_or_during_fade(self):
        M.SUBPIXEL, M.TRACE = True, M.Trace(resting_snap=False)
        spr=M.Sprite(np.full((10,10,4),255,np.uint8))
        for f,x in enumerate((10.1,10.25,10.4,10.4,10.4)):
            M.TRACE.begin_frame(f);M.TRACE.begin_layer('t')
            M.blit(np.zeros((30,30,3),np.uint8),spr,x,10.2,opacity=1-f*.1,tag='s')
        centres=[r[3] for r in M.TRACE.rows]
        self.assertEqual(centres[-3:],[15.4,15.4,15.4])
        self.assertTrue(ML.config(style())['resting_snap'])

    def test_motion_blur_smears_fast_moves_only(self):
        spr = M.rounded_rect_sprite(10, 30, 0, (255, 255, 255, 255))
        def run(blur, dx):
            M.TRACE = M.Trace({'samples': 6, 'min_px': 6, 'shutter': .5} if blur else None)
            for f, x in enumerate((20, 20 + dx)):
                M.TRACE.begin_frame(f); M.TRACE.begin_layer('t')
                fr = np.zeros((40, 120, 3), np.uint8)
                M.blit(fr, spr, x, 5, tag='s')
            return int((fr[..., 0].max(0) > 8).sum())
        self.assertGreater(run(True, 24), run(False, 24) + 6)
        self.assertEqual(run(True, 2), run(False, 2))        # slow move: below min_px, untouched

    def test_cut_sync_direction_and_zoom_ease(self):
        st = style(cuts={'enabled': True, 'offset_frames': 3})
        ctx = E.Ctx(st); ctx.cut_times = [1.0]
        cues = [{'start': .2, 'end': 1.0, 'text': 'birinchi gap'}, {'start': 1.0, 'end': 2.2, 'text': 'ikkinchi gap'}]
        cap = E.CaptionLayer(ctx, cues, None, 3.0)
        self.assertAlmostEqual(cap.items[1]['start'], 1.1, places=6)
        self.assertAlmostEqual(cap.items[0]['start'], .2)
        self.assertEqual(cap.items[0]['cfg'].get('exit_vec'), (-1.0, 0.0))   # leaves the way the next enters
        plan = [(0., 2., 1., 1.1)]
        lin, eas = compose.zoom_at(plan, [], .2, (.5, .5))[0], compose.zoom_at(plan, [], .2, (.5, .5), True)[0]
        self.assertLess(eas, lin)
        self.assertAlmostEqual(compose.zoom_at(plan, [], 1., (.5, .5), True)[0], 1.05, places=6)
        off = E.CaptionLayer(E.Ctx(style()), cues, None, 3.0)
        self.assertAlmostEqual(off.items[1]['start'], 1.0)                   # switch off: legacy timing

    def test_adaptive_scrim_follows_background(self):
        st = style(scrim={'enabled': True, 'style': 'soft'})
        ctx = E.Ctx(st)
        cues = [{'start': 0, 'end': 2, 'text': 'oq fonda matn'}]
        res = {}
        for name, value in (('dark', 10), ('bright', 235)):
            cap = E.CaptionLayer(ctx, cues, None, 2.0)
            fr = np.full((640, 360, 3), value, np.uint8)
            cap.draw(fr, 1.0)
            res[name] = cap.contrast[0]
        self.assertEqual(res['dark'][3], 0.0)
        self.assertGreater(res['bright'][3], .3)
        self.assertGreater(res['bright'][2], res['bright'][1])

    def test_emphasis_set_renders_and_settles(self):
        for effect in ('pop_overshoot', 'colour_flash', 'shake', 'underline_draw', 'box_wipe'):
            st = style(choice={'enter': 'slide_overshoot', 'sub': 'mask_up', 'emphasis': effect})
            ctx = E.Ctx(st)
            cap = E.CaptionLayer(ctx, [{'start': 0, 'end': 2, 'text': 'bu **muhim** gap'}], None, 2.0)
            mid, late = (np.zeros((640, 360, 3), np.uint8) for _ in range(2))
            cap.draw(mid, .12); cap.draw(late, 1.5)
            self.assertGreater(int(np.abs(mid.astype(int) - late.astype(int)).sum()), 0, effect)
        with self.assertRaises(C.MontajError):
            ML.config(style(choice={'emphasis': 'wobble'}))


class TemplateTests(unittest.TestCase):
    def draw(self, el, t, base=40):
        ctx = E.Ctx(style())
        layer = E.build_elements(ctx, [el], 4.0)[0]
        fr = np.full((640, 360, 3), base, np.uint8)
        layer.draw(fr, t)
        return fr

    def test_templates_draw(self):
        logo = str(C.ROOT / 'brands/demo/logo.png')
        for el in ({'type': 'calendar', 'start': 0, 'end': 3, 'month': 'Mart', 'day': 8, 'label': '8-mart'},
                   {'type': 'panel', 'start': 0, 'end': 3, 'title': 'Belgilar', 'lines': ['isitma', 'yo‘tal']},
                   {'type': 'logo_sting', 'start': 0, 'end': 2, 'file': logo},
                   {'type': 'image', 'start': 0, 'end': 3, 'file': logo, 'push': .08}):
            fr = self.draw(el, 1.0)
            self.assertGreater(int(np.abs(fr.astype(int) - 40).sum()), 1000, el['type'])

    def test_mask_reveal_opens_whole_frame(self):
        el = {'type': 'mask_reveal', 'start': 0, 'end': 1.0, 'text': 'SALOM', 'color': '#FF3366'}
        first, last = self.draw(el, .05), self.draw(el, .999)
        self.assertGreater(float((first == np.array([255, 51, 102], np.uint8)).all(-1).mean()), .5)
        self.assertLess(int(np.abs(last.astype(int) - 40).max()), 3)


class PresetTests(unittest.TestCase):
    def test_presets_frames_and_explicit_override(self):
        cfg = ML.config({'motion': {'preset': 'punchy', 'speed': 'medium'}, 'video': {'fps': 30}})
        self.assertEqual((cfg['speed'], cfg['choice']['emphasis'], cfg['motion_blur']['enabled'], cfg['zoom_strength']),
                         ('medium', 'pop_overshoot', True, 1.2))
        self.assertEqual(ML.config({'motion': {'durations_frames': {'caption': 9}}, 'video': {'fps': 30}})['durations_ms']['caption'], 300)
        self.assertEqual(ML.frames(cfg, 'caption', 30), round(ML.duration(cfg, 'caption') * 30))
        with self.assertRaises(C.MontajError):
            ML.config({'motion': {'preset': 'wild'}})
        st = C.load_style(); st['zoom'].update(enabled=True, punch_in=1.2, slow_push=.04)
        st['motion']['preset'] = 'calm'
        plan = compose.zoom_plan(st, {'keep': [{'start': 0, 'end': 2}, {'start': 3, 'end': 5}]}, 4.0)
        self.assertAlmostEqual(plan[1][2], 1.12, places=6)

    def test_legacy_untouched(self):
        old = {k: v for k, v in ML.DEFAULTS.items() if k not in ML.NEW_KEYS}
        cfg = ML.config({})
        self.assertFalse(cfg['subpixel'] or cfg['motion_blur']['enabled'] or cfg['cuts']['enabled'] or cfg['scrim']['enabled'])
        self.assertIsNone(cfg['zoom_strength'])
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            st = style(); st['motion']['choice'] = {}
            a = ML.choose(st, Path(td))['motion']['choice']
            st2 = copy.deepcopy(st); st2['motion']['subpixel'] = True; st2['motion']['scrim'] = {'enabled': True}
            self.assertEqual(ML.choose(st2, Path(td))['motion']['choice'], a)   # quality switches never re-roll
        self.assertTrue(set(old) < set(ML.DEFAULTS))
        rep = QG.evaluate(C.load_style(), [], [], 10, {}, {'checks': []})
        self.assertFalse({'motion_lint_flags_per_min', 'drift_jitter_px'} & {r['key'] for r in rep['measurements']})
        rep = QG.evaluate(C.load_style(), [], [], 10, {}, {'checks': [], 'motion_lint': {'flags': 0, 'drift_jitter_px': .05}})
        self.assertEqual({r['key']: r['status'] for r in rep['measurements']}['drift_jitter_px'], 'pass')


class SlowmoTests(unittest.TestCase):
    def test_quarter_speed_clip_and_12_frame_strip(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            src = Path(td) / 'src.mp4'
            subprocess.run([C.need_tool('ffmpeg'), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=size=180x320:rate=30',
                            '-t', '2', '-pix_fmt', 'yuv420p', str(src)], check=True)
            made = RT.slowmo(src, [20], Path(td) / 'out')
            self.assertEqual(C.read_json(Path(made[0]['strip']).with_suffix('.json'))['count'], 12)
            self.assertAlmostEqual(C.ffprobe_info(made[0]['clip'])['duration'], 12 / 30 * 4, delta=.1)


if __name__ == '__main__':
    unittest.main(verbosity=1)
