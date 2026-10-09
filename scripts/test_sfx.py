"""SFX v2: numpy synthesis (determinism, level match, variety), pack import (zip safety, trim, normalise,
categories, licence note, index), git-ignore of purchased audio, real > synthesized and newest synth version."""
import json, subprocess, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

import common as C
import sfx_import as SI
import sfx_library as SL
import sfx_synth as S
import sound_design as SD


def tone(sec, f=440.0, lead=0.3, tail=0.4, amp=0.2):
    n, a, b = int(S.SR * sec), int(S.SR * lead), int(S.SR * tail)
    x = amp * np.sin(2 * np.pi * f * np.arange(n) / S.SR)
    return np.concatenate([np.zeros(a), x, np.zeros(b)])


class SynthTests(unittest.TestCase):
    def test_deterministic_and_variants_differ(self):
        for cat in S.RECIPES:
            a, b, c = S.make(cat, 1), S.make(cat, 1), S.make(cat, 2)
            np.testing.assert_array_equal(a, b)
            self.assertFalse(a.shape == c.shape and np.allclose(a, c), cat)

    def test_level_match_and_peak_ceiling(self):
        for cat in S.RECIPES:
            for k in (1, 2, 3):
                x = S.make(cat, k)
                self.assertLessEqual(S.peak_db(x), S.PEAK_DB + 0.01, cat)
                # transient sounds may stay below the RMS target because the peak ceiling wins; never above it
                self.assertLessEqual(abs(S.loudest_rms_db(x) - S.TARGET_RMS_DB), 3.5, cat)
                self.assertLessEqual(S.loudest_rms_db(x), S.TARGET_RMS_DB + 0.05, cat)
                self.assertEqual(x.shape[1], 2)

    def test_shapes_measured_not_assumed(self):
        # whoosh rises then falls; riser keeps rising to its end; impact has a low-end body
        w = S.make("whoosh", 1).mean(axis=1)
        q = len(w) // 10
        e = [float(np.sqrt(np.mean(w[i * q:(i + 1) * q] ** 2))) for i in range(10)]
        self.assertGreater(max(e[3:8]), 3 * e[0])
        self.assertGreater(max(e[3:8]), 3 * e[9])
        r = S.make("riser", 1).mean(axis=1)
        h = len(r) // 2
        self.assertGreater(np.sqrt(np.mean(r[h:] ** 2)), 3 * np.sqrt(np.mean(r[:h] ** 2)))
        im = S.make("impact", 1).mean(axis=1)
        spec = np.abs(np.fft.rfft(im)) ** 2
        f = np.fft.rfftfreq(len(im), 1 / S.SR)
        self.assertGreater(spec[f < 200].sum() / spec.sum(), 0.5)

    def test_build_writes_provenance_and_preview(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            rows = S.build(Path(td), ["pop", "ding"], variants=2)
            self.assertEqual(len(rows), 4)
            for r in rows:
                meta = SL.provenance(Path(r["file"]))
                self.assertEqual((meta["kind"], meta["usable"], meta["synth_version"]), ("synthesized", True, S.VERSION))
            for cat in ("pop", "ding"):
                self.assertTrue((Path(td) / "_preview" / f"{cat}.wav").is_file())
            idx = SL.index(Path(td))
            self.assertFalse(any("_preview" in r["file"] for r in idx))


class ImportTests(unittest.TestCase):
    def test_categorise_names_and_ties(self):
        self.assertEqual(SI.categorise("Whooshes/fast_swoosh_03.wav")[0], "whoosh")
        self.assertEqual(SI.categorise("UI/Button Click 2.mp3")[0], "click")
        self.assertEqual(SI.categorise("Cinematic/Boom Impact Deep.wav")[0], "impact")
        self.assertEqual(SI.categorise("misc/thing_01.wav")[0], None)
        self.assertEqual(SI.categorise("pop click.wav")[0], None)                       # tie -> _unsorted
        self.assertEqual(SI.categorise("guide/build_up_riser.wav")[0], "riser")
        self.assertIsNone(SI.categorise("fruit.wav")[0])                                 # "ui" is not a word in fruit

    def test_zip_import_trim_normalise_sort_licence_index(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            root = Path(td)
            src = root / "src"
            src.mkdir()
            S.write_wav(src / "whoosh_fast.wav", np.stack([tone(0.4, 900)] * 2, axis=1))
            S.write_wav(src / "Button Click.wav", np.stack([tone(0.05, 3000, amp=0.05)] * 2, axis=1))
            S.write_wav(src / "mystery.wav", np.stack([tone(0.3, 300)] * 2, axis=1))
            S.write_wav(src / "silent.wav", np.zeros((4800, 2)))
            zpath = root / "inbox" / "Cool Pack.zip"
            zpath.parent.mkdir()
            with zipfile.ZipFile(zpath, "w") as z:
                for f in src.iterdir():
                    z.write(f, f"Cool Pack/{f.name}")
                z.writestr("../evil.wav", b"x")                                         # path traversal is skipped
                z.writestr("readme.txt", "not audio")
            lib = root / "lib"
            res = SI.import_pack(zpath, "Test Shop", "Fixture licence v1", "cool-pack", lib)
            cats = {Path(r["source"]).name: r.get("category", r.get("status")) for r in res["rows"]}
            self.assertEqual(cats["whoosh_fast.wav"], "whoosh")
            self.assertEqual(cats["Button Click.wav"], "click")
            self.assertEqual(cats["mystery.wav"], "_unsorted")
            self.assertTrue(cats["silent.wav"].startswith("skipped"))
            self.assertFalse((root / "evil.wav").exists())
            out = next(r for r in res["rows"] if r.get("category") == "whoosh")
            x = S.read_wav(C.ROOT / out["file"])
            self.assertAlmostEqual(len(x) / S.SR, 0.4 + 2 * 0.008, delta=0.01)          # silence trimmed
            self.assertAlmostEqual(S.loudest_rms_db(x), S.TARGET_RMS_DB, delta=0.3)
            meta = SL.provenance(C.ROOT / out["file"])
            self.assertEqual((meta["kind"], meta["usable"]), ("real", True))
            note = (lib / "_licenses" / "cool-pack.md").read_text(encoding="utf-8")
            self.assertIn("Fixture licence v1", note)
            self.assertIn("Test Shop", note)
            idx = SL.index(lib)
            self.assertFalse(any("_unsorted" in r["file"] for r in idx))
            self.assertTrue(any(r["kind"] == "real" and r["usable"] for r in idx))

    def test_cli_refuses_empty_licence(self):
        p = subprocess.run([str(C.ROOT / ".venv/Scripts/python.exe"), str(C.ROOT / "scripts/sfx_import.py"), "--shop", "X",
                            "--license", " ", "--inbox", "temp/sfx_import_none"], cwd=C.ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("litsenziya", (p.stdout + p.stderr).lower())

    def test_purchased_audio_is_git_ignored_index_tracked(self):
        def ignored(path):
            return subprocess.run(["git", "check-ignore", "-q", path], cwd=C.ROOT).returncode == 0
        self.assertTrue(ignored("assets/sfx/whoosh/real__pack__x.wav"))
        self.assertTrue(ignored("assets/sfx/whoosh/real__pack__x.wav.credit.json"))
        self.assertTrue(ignored("assets/sfx/_inbox/pack.zip"))
        self.assertTrue(ignored("assets/sfx/_unsorted/real__pack__y.wav"))
        self.assertFalse(ignored("assets/sfx/index.json"))
        self.assertFalse(ignored("assets/sfx/_licenses/pack.md"))
        self.assertFalse(ignored("assets/sfx/whoosh/synth_v2_01.wav"))


class SelectionTests(unittest.TestCase):
    def test_real_wins_then_newest_synth(self):
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            root = Path(td)
            cat = root / "assets/sfx/whoosh"
            cat.mkdir(parents=True)
            old, new = cat / "synth_01.wav", cat / "synth_v2_01.wav"
            for p, v in ((old, None), (new, 2)):
                p.write_bytes(b"x")
                meta = {"source": "scripts/make_sfx.py", "license": "project", "kind": "synthesized"}
                if v:
                    meta["synth_version"] = v
                C.write_json(meta, p.with_suffix(".wav.credit.json"))
                p.with_suffix(".wav.LICENSE.txt").write_text("project")
            with patch.object(C, "ROOT", root):
                self.assertEqual(SD.variants("whoosh"), [new])
                real = cat / "real__shop__a.wav"
                real.write_bytes(b"x")
                C.write_json({"source": "Shop", "license": "L", "kind": "real"}, real.with_suffix(".wav.credit.json"))
                real.with_suffix(".wav.LICENSE.txt").write_text("L")
                self.assertEqual(SD.variants("whoosh"), [real])


if __name__ == "__main__":
    r = unittest.main(verbosity=1, exit=False).result
    n = r.testsRun
    print(f"SFX NATIJA: {n - len(r.failures) - len(r.errors)}/{n}")
    raise SystemExit(0 if r.wasSuccessful() else 1)
