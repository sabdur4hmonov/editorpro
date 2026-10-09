"""Formats: formats.json schema and evidence rule, detection on the measured reference set, split/card detectors,
history learning, plan + approval lines."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import common as C
import formats as F

REF = C.ROOT / "docs" / "formats" / "sample_features.json"
LABELS = {"f_Birinchi_yuzdan": "birinchi_yuzdan", "f_Interview": "interview", "f_Kadr_rakursli": "kadr_rakursli",
          "f_Obrazli": "obrazli", "f_Savol_javob": "savol_javob", "f_Syudjetli": "syudjetli",
          "f_Talking_head": "talking_head", "f_Tepa-past": "tepa_past"}
AGENT_EXTRAS = {"mic_or_headphones", "interviewer_voice", "staged_scenes", "props", "costume", "theatre_light",
                "question_given", "broll_available"}


class SchemaTests(unittest.TestCase):
    def test_every_format_complete_and_rules_use_known_features(self):
        fm = F.formats()
        self.assertEqual(set(fm), set(LABELS.values()))
        known = set(F.FEATURE_KEYS) | AGENT_EXTRAS
        for key, f in fm.items():
            for field in ("name", "summary", "evidence_class", "labelled_example", "matching_samples", "recognise",
                          "detect", "structure", "edit", "quality_targets", "graphics", "style_groups", "group_reason"):
                self.assertIn(field, f, key)
            for r in f["detect"]["rules"]:
                self.assertIn(r["feature"], known, key)
            q = f["quality_targets"]
            for k in ("cuts_per_min", "graphics_per_min", "min_gap_s", "calm_stretch_s", "caption_size_pct_h",
                      "hook_text_s", "max_face_cover"):
                self.assertIn(k, q, key)
            self.assertTrue(f["labelled_example"]["evidence"], key)

    def test_pattern_needs_three_videos_otherwise_observation(self):
        for key, f in F.formats().items():
            videos = {m["video"] for m in f["matching_samples"] if m["confidence"] in ("high", "medium")}
            if f["evidence_class"] == "pattern":
                self.assertGreaterEqual(len(videos) + 1, 3, key)       # +1 = the labelled example
            else:
                self.assertEqual(f["evidence_class"], "observation", key)

    def test_style_groups_exist(self):
        import sample_groups as SG
        for key, f in F.formats().items():
            for g in f["style_groups"]:
                self.assertIn(g, SG.FAMILIES, key)


class DetectTests(unittest.TestCase):
    def test_reference_examples_ranked_first(self):
        ref = C.read_json(REF)["features"]
        hits = sum(F.detect(ref[k])["ranked"][0]["format"] == v for k, v in LABELS.items())
        self.assertGreaterEqual(hits, 7)        # Obrazli needs the agent's 'costume' observation
        det = F.detect(ref["f_Obrazli"], {"costume": True})
        self.assertEqual(det["selected"], "obrazli")

    def test_unclear_is_reported_not_guessed(self):
        det = F.detect({"face_ratio": .5, "setups": 3})
        self.assertTrue(det["needs_editor_judgement"])
        self.assertIsNone(det["selected"])

    def test_split_and_card_detectors(self):
        n, h, w = 6, 320, 180
        split = np.full((n, h, w, 3), 120, np.uint8)
        split[:, 150:] = 20                                   # persistent seam at ~0.47 H
        self.assertGreaterEqual(F._split_line(split), 0.9)
        noisy = np.random.default_rng(1).integers(0, 255, (n, h, w, 3), dtype=np.uint8)
        self.assertLess(F._split_line(noisy), 0.9)
        card = np.full((n, h, w, 3), 60, np.uint8)
        card[:, 20:40, 30:150] = 250                          # question sticker, not touching the top
        self.assertTrue(F._top_card(card))
        lamp = np.full((n, h, w, 3), 60, np.uint8)
        lamp[:, 0:30, 40:140] = 250                           # bright area touching the top edge
        self.assertFalse(F._top_card(lamp))


class LearningTests(unittest.TestCase):
    def test_record_shifts_similar_footage_only(self):
        ref = C.read_json(REF)["features"]
        with tempfile.TemporaryDirectory(dir=C.TEMP_DIR) as td:
            hist = Path(td) / "choice_history.json"
            with patch.object(F, "HISTORY_FILE", hist):
                base = F.detect(ref["f_Obrazli"])
                F.record(Path("x.mp4"), "obrazli", "D_cinematic_commercial", "approved", "user: obrazli", ref["f_Obrazli"])
                after = F.detect(ref["f_Obrazli"])
                score = lambda d, k: next(r["score"] for r in d["ranked"] + [{"format": k, "score": None}] if r["format"] == k)
                self.assertGreater(score(after, "obrazli"), score(base, "obrazli"))
                self.assertIn("history", " ".join(next(r for r in after["ranked"] if r["format"] == "obrazli")["reasons"]))
                far = F.detect(ref["f_Birinchi_yuzdan"])
                self.assertFalse(any("history" in " ".join(r["reasons"]) for r in far["ranked"]))
                F.record(Path("y.mp4"), "kadr_rakursli", None, "rejected", "user: not multi-angle", ref["f_Obrazli"])
                self.assertLess(F.history_bonus(ref["f_Obrazli"]).get("kadr_rakursli", 0), 0)


class PlanTests(unittest.TestCase):
    def test_plan_combines_format_and_group_with_reasons(self):
        ref = C.read_json(REF)["features"]
        det = F.detect(ref["f_Interview"])
        p = F.plan(Path("v.mp4"), det["selected"], None, det, None)
        self.assertEqual((p["format"], p["style_group"]), ("interview", "C_interview_testimonial"))
        lines = F.approval_lines(p)
        self.assertTrue(lines[0].startswith("FORMAT: Interview"))
        self.assertIn("gaze_off", lines[0])
        self.assertTrue(lines[1].startswith("USLUB: C_interview_testimonial"))
        self.assertIn("quality_targets", p)
        with self.assertRaises(C.MontajError):
            F.plan(Path("v.mp4"), "nope", None, det, None)
        p2 = F.plan(Path("v.mp4"), "obrazli", "D_cinematic_commercial", det, "agent: costume seen 2.9 s")
        self.assertEqual(p2["subtype"], "promo")
        self.assertIn("costume", F.approval_lines(p2)[0])

    def test_guide_is_generated_from_json(self):
        text = F.guide()
        for f in F.formats().values():
            self.assertIn(f["name"], text)
        self.assertEqual(text, (C.ROOT / "docs" / "FORMATS.md").read_text(encoding="utf-8"),
                         "docs/FORMATS.md eskirgan: scripts/formats.py guide")


if __name__ == "__main__":
    r = unittest.main(verbosity=1, exit=False).result
    print(f"FORMATS NATIJA: {r.testsRun - len(r.failures) - len(r.errors)}/{r.testsRun}")
    raise SystemExit(0 if r.wasSuccessful() else 1)
