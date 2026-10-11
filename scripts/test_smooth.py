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
                            '-f', 'lavfi', '-i', 'anoisesrc=a=0.02:c=pink:r=48000', '-t', '4', '-c:v', 'libx264', '-c:a', 'pcm_s16le',
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
            self.assertGreater(dips['crossfade'], -4)      # overlap: room tone continuous


if __name__ == '__main__':
    unittest.main(verbosity=1)
