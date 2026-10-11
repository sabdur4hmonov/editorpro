"""Setup kengaytmalari: mustaqil qoidalar, real CLI va sintetik namuna-uslub render sinovi."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

import numpy as np
from PIL import Image
import common as C
import compose
import elements as E
import person_mask
import studio

WORK = C.TEMP_DIR / "studio_test"


def cli(name, *args, expected=0):
    run = subprocess.run([sys.executable, str(C.ROOT / "scripts" / name), *map(str, args)],
                         cwd=C.ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         stdin=subprocess.DEVNULL, timeout=600)
    if run.returncode != expected:
        raise AssertionError(f"{name}: {run.returncode}, expected {expected}\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}")
    return run


class Rules(unittest.TestCase):
    def test_draft_preserves_final_style(self):
        # F12: a draft keeps the source frame rate (25 in -> 25 out); only size/encode get cheaper
        original = C.resolve_fps(C.load_style(), meta={"fps": 25.0, "r_fps": 25.0})
        before = copy.deepcopy(original)
        draft = compose.draft_style(original)
        self.assertEqual(original, before)
        self.assertEqual((draft["video"]["width"], draft["video"]["height"], draft["video"]["fps"]), (360, 640, 25))
        legacy = dict(original, video=dict(original["video"], fps=30), preview=dict(original["preview"], fps=15))
        self.assertEqual(compose.draft_style(legacy)["video"]["fps"], 15)          # old per-video styles unchanged

    def test_preflight_finds_semantic_risks_and_structural_errors(self):
        style = C.load_style()
        cues = [{"start": 2, "end": 3, "text": "**raqam** va **natija**"}]
        report = studio.preflight(style, cues, [], 12, False)
        self.assertTrue(report["structural_ok"])
        codes = {warning["code"] for warning in report["warnings"]}
        self.assertTrue({"hook_missing", "rhythm_gap", "accent_density", "multiple_accents", "ending_missing"} <= codes)
        bad = studio.preflight(style, [{"start": -1, "end": 1, "text": "bad"}], [{"type": "follow", "end": "bad"}], 4, False)
        self.assertFalse(bad["structural_ok"])
        self.assertEqual(len(bad["errors"]), 2)
        clipped = studio.preflight(style, [], [{"type": "follow", "start": 3, "end": 10, "handle": "@test"}], 4, False)
        self.assertTrue(clipped["structural_ok"])
        actual_colors = studio.preflight(style, [{"start": .1, "end": 1, "text": "{caps}*SINOV*"}],
                                         [{"type": "stat", "start": .1, "value": 85}], 4, False)
        self.assertEqual(actual_colors["accent_cue_ratio"], 1)
        self.assertIn("accent_overlap", {row["code"] for row in actual_colors["warnings"]})
        default_item = studio.preflight(style, [], [{"type": "list", "items": [{"text": "Sinov"}]}], 4, False)
        self.assertTrue(default_item["structural_ok"])

    def test_follow_without_handle_draws_icon(self):
        style = C.load_style()
        style["video"].update(width=360, height=640)
        ctx = E.Ctx(style)
        layer = E.FollowLayer(ctx, {"type": "follow", "start": 0, "end": 3, "icon": "user-plus", "tap": 1})
        self.assertIsNone(layer.pill)
        frame = np.zeros((640, 360, 3), np.uint8)
        layer.draw(frame, 1.5)
        self.assertGreater(int(frame.max()), 0)
        with self.assertRaises(C.MontajError):
            E.FollowLayer(ctx, {"type": "follow", "start": 0, "end": 3, "icon": "yoq-belgi-nomi"})

    def test_mark2_big_lockup_and_image_wiggle(self):
        words = [{"start": i * .3, "end": i * .3 + .25, "word": w} for i, w in enumerate("bola ~~pnevmoniya~~ bo'lib qolgan".split())]
        self.assertGreater(len(C.words_to_cues(words, {"max_words_per_line": 2})), 1)
        self.assertEqual(len(C.words_to_cues(words, {"max_words_per_line": 2, "mark2_big": True})), 1)
        style = C.load_style()
        style["video"].update(width=360, height=640)
        style["captions"]["mark2_big"] = True
        ctx = E.Ctx(style)
        cfg = ctx.caption_cfg()
        block = E.RichBlock(ctx, "bola ~~pnevmoniya~~", cfg)
        self.assertTrue(any(w["emph"] and w["group"] is not None for w in block.words))
        WORK.mkdir(parents=True, exist_ok=True)
        png = WORK / "wiggle.png"
        Image.new("RGBA", (40, 30), (255, 0, 0, 255)).save(png)
        layer = E.ImageLayer(ctx, {"start": 0, "end": 2, "file": str(png), "width": 0.2, "wiggle": 3})
        self.assertEqual(len(layer.sprites), 9)
        frame = np.zeros((640, 360, 3), np.uint8)
        layer.draw(frame, 0.8)
        self.assertGreater(int(frame.max()), 0)

    def test_broll_bw_and_dim(self):
        style = C.load_style()
        style["video"].update(width=90, height=160)
        ctx = E.Ctx(style)
        WORK.mkdir(parents=True, exist_ok=True)
        png = WORK / "broll_red.png"
        Image.new("RGB", (90, 160), (200, 40, 40)).save(png)
        layer = E.BrollLayer(ctx, {"start": 0, "end": 1, "file": str(png), "mode": "full", "bw": True, "dim": 0.5})
        frame = np.zeros((160, 90, 3), np.uint8)
        layer.draw(frame, 0.5)
        r, g, b = (int(v) for v in frame[80, 45])
        self.assertEqual((r, r), (g, b))                 # oq-qora
        self.assertLess(r, 60)                          # qoraytirilgan (kulrang ~ 83 * 0.5)

    def test_promo_presets_justify_and_tag_glow(self):
        style = C.load_style()
        style["video"].update(width=540, height=960)
        ctx = E.Ctx(style)
        self.assertIn("promo", E.CAPTION_PRESETS)
        self.assertIsNone(E.CAPTION_PRESETS["vo"]["glow"])
        cfg = ctx.caption_cfg({"preset": "promo"})
        block = E.RichBlock(ctx, "**5 kishilik** set so'rashdi", cfg)
        hero = [w for w in block.words if w["emph"]]
        sub = [w for w in block.words if not w["emph"]]
        hero_l, hero_r = hero[0]["x"], hero[-1]["x"] + hero[-1]["w"]
        self.assertAlmostEqual(sub[0]["x"], hero_l, delta=2)               # "set" chap chetda
        self.assertAlmostEqual(sub[-1]["x"] + sub[-1]["w"], hero_r, delta=2)  # "so'rashdi" o'ng chetda
        price = E.RichBlock(ctx, "5 kishilik setlarimiz narxi !!990,000!! so'm", cfg)
        self.assertEqual(len({w["line"] for w in price.words}), 3)
        num = [w for w in price.words if w["emph"]][0]
        unit = price.words[-1]
        self.assertAlmostEqual(unit["x"] + unit["w"], num["x"] + num["w"], delta=2)  # "so'm" o'ngga
        style["captions"]["glow"] = {"blur": 0, "opacity": 0}
        layer = E.CaptionLayer(E.Ctx(style), [{"start": 0, "end": 1, "text": "{caps}*sinov*"}], None, 1)
        self.assertEqual(layer.items[0]["cfg"]["glow"], {"blur": 0, "opacity": 0})

    def test_label_and_aside_elements(self):
        style = C.load_style()
        style["video"].update(width=540, height=960)
        ctx = E.Ctx(style)
        WORK.mkdir(parents=True, exist_ok=True)
        png = WORK / "label_thumb.png"
        Image.new("RGBA", (60, 40), (200, 120, 40, 255)).save(png)
        label = E.LabelLayer(ctx, {"start": 0, "end": 3, "items": [
            {"at": 0, "kicker": "1-set", "name": "Mol qovurg'asi", "image": str(png)},
            {"at": 1.5, "kicker": "2-set", "name": "Qo'yning qo'li"}]})
        self.assertEqual([round(i["end"], 2) for i in label.items], [1.5, 3.0])
        frame = np.zeros((960, 540, 3), np.uint8)
        label.draw(frame, 0.6)
        self.assertGreater(int(frame.max()), 0)
        with self.assertRaises(C.MontajError):
            E.LabelLayer(ctx, {"start": 0, "end": 1, "items": [{"at": 0, "name": ""}]})
        ctx.anchor = (0.5, 0.35)
        aside = E.AsideLayer(ctx, {"start": 0, "end": 2, "items": [
            {"at": 0, "text": "juda\nham", "side": "left"}, {"at": 0.3, "text": "ko'pchilik bizdan", "side": "right"}]})
        left, right = aside.parts
        self.assertLess(left.cx + left.block.width / 2, 0.5 * 540)
        self.assertGreater(right.cx - right.block.width / 2, 0.5 * 540)
        self.assertLessEqual(right.cx + right.block.width / 2, 540 * 0.95 + 1)    # kadr ichida
        frame = np.zeros((960, 540, 3), np.uint8)
        aside.draw(frame, 1.0)
        self.assertGreater(int(frame.max()), 0)
        with self.assertRaises(C.MontajError):
            E.AsideLayer(ctx, {"start": 0, "end": 1, "items": [{"text": "x", "side": "top"}]})

    def test_assemble_clips_and_protect_products(self):
        import assemble as A
        import auto_cut
        self.assertEqual(auto_cut.subtract_ranges([{"start": 0, "end": 10, "reason": "jim"}], [(2, 4)]),
                         [{"start": 0, "end": 2, "reason": "jim"}, {"start": 4, "end": 10, "reason": "jim"}])
        clips = WORK / "assemble_src"
        clips.mkdir(parents=True, exist_ok=True)
        ff = C.need_tool("ffmpeg")
        C.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x568:r=60:d=2", "-f", "lavfi", "-i",
               "sine=f=440:d=2", "-c:v", "libx264", "-c:a", "aac", "-shortest", clips / "01_speech.mp4"])
        C.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=568x320:r=25:d=1.5", "-c:v", "libx264",
               clips / "02_product.mp4"])
        C.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=330:d=1.2", "-c:a", "aac", clips / "03_vo.m4a"])
        manifest = WORK / "assemble_clips.json"
        C.write_json({"name": "studio_assemble_test", "clips": [
            {"file": str(clips / "01_speech.mp4"), "role": "speech"},
            {"file": str(clips / "02_product.mp4"), "role": "product"},
            {"file": str(clips / "03_vo.m4a"), "role": "voiceover", "cover": [{"file": str(clips / "02_product.mp4"), "out": 0.5}]}]},
            manifest)
        style = C.load_style()
        style["video"].update(width=180, height=320, fps=15)
        built = A.build(manifest, style)
        meta = C.ffprobe_info(built["video"])
        self.assertEqual((meta["width"], meta["height"]), (180, 320))
        self.assertAlmostEqual(meta["duration"], 4.7, delta=0.25)
        self.assertEqual([s["role"] for s in built["segments"]], ["speech", "product", "voiceover"])
        self.assertEqual(len(built["protect"]), 1)
        ps, pe = built["protect"][0]
        plan = auto_cut.build_plan(built["video"], style, [], protect=built["protect"])
        for r in plan["removed"]:
            self.assertFalse(r["start"] < pe - 0.01 and ps + 0.01 < r["end"], f"mahsulot kesildi: {r}")
        again = A.build(manifest, style)                       # o'zgarmagan ro'yxat qayta yig'ilmaydi
        self.assertEqual(Path(again["video"]).stat().st_mtime, Path(built["video"]).stat().st_mtime)

    def test_promo_looks_valid_palette_and_no_repeat(self):
        import promo_looks as PL
        import assemble as A
        looks = PL.load_looks()
        self.assertGreaterEqual(len(looks), 4)
        WORK.mkdir(parents=True, exist_ok=True)
        allowed = {"label": {"glass", "x", "y", "width", "size", "image_size", "color", "kicker_color", "font", "preset"},
                   "aside": {"spread", "dy", "size", "font", "color", "weight", "stagger", "margin", "preset", "glow"},
                   "handnote": {"font", "size", "x", "y", "color"}}
        old_hist = PL.HISTORY_PATH
        PL.HISTORY_PATH = WORK / "promo_history_test.json"
        try:
            C.write_json({"history": []}, PL.HISTORY_PATH)
            for name, look in looks.items():
                self.assertIn(look["style"]["captions"].get("preset", "clean"), E.CAPTION_PRESETS, name)
                self.assertIn(look["style"]["look"]["preset"], compose.LOOK_PRESETS, name)
                for kind, fields in look.get("elements", {}).items():
                    self.assertTrue(set(fields) <= allowed[kind], f"{name}.{kind}: {set(fields) - allowed[kind]}")
                path = WORK / f"look_{name}.json"
                C.write_json(C.load_style(), path)
                PL.apply(name, path)
                style = C.load_style(path)
                style["video"].update(width=360, height=640)
                ctx = E.Ctx(style)
                for role, tag in look["tags"].items():
                    preset, _, _ = E.split_cue_tag(tag + "sinov")
                    self.assertTrue(preset is None or preset in E.CAPTION_PRESETS, f"{name}.{role}: {tag}")
                    layer = E.CaptionLayer(ctx, [{"start": 0, "end": 1, "text": f"{tag}**990,000** so'm"}], None, 1)
                    self.assertTrue(layer.items)
            PL.record("bold_caps", "sinov_job", "#ff5a1f")
            with self.assertRaises(C.MontajError):
                PL.apply("bold_caps", WORK / "look_bold_caps.json")          # oldingi promo yo'nalishi takrorlanmaydi
            PL.apply("bold_caps", WORK / "look_bold_caps.json", allow_repeat=True)
        finally:
            PL.HISTORY_PATH = old_hist
        clip = WORK / "palette_red.mp4"
        C.run([C.need_tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xC81E1E:s=180x320:r=10:d=1",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", clip])
        pal = PL.palette(clip, n_frames=2, k=2)
        r, g, b = (int(pal["accent_food"][i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(r, 200)
        self.assertLess(max(g, b), 120)
        rows = A.report([{"start": 0, "end": 2, "role": "speech", "file": "a.mp4"},
                         {"start": 2, "end": 4, "role": "product", "file": "b.mp4"}],
                        [{"start": 2.5, "end": 2.8, "word": "salom"}])
        self.assertEqual([r["words"] for r in rows], [0, 1])
        self.assertTrue(rows[0]["hint"] and rows[1]["hint"])

    def test_emphasis_suggestions_keep_timings(self):
        import apply_corrections as AC
        words = [{"start": i*.3, "end": i*.3+.2, "word": word, "prob": .9}
                 for i, word in enumerate("3 oyda natija olasiz. sifat muhim.".split())]
        proposal = studio.suggestions(words, ["sifat"])
        WORK.mkdir(parents=True, exist_ok=True)
        path = WORK / "proposals.json"
        C.write_json({"corrections": proposal["corrections"]}, path)
        applied, _ = AC.apply(words, AC.read_corrections(path, len(words)))
        self.assertEqual([(row["start"], row["end"]) for row in applied], [(row["start"], row["end"]) for row in words])
        self.assertTrue(applied[0]["word"].startswith("*3"))
        self.assertEqual(words[0]["word"], "3")
        words[0]["needs_review"] = True
        self.assertFalse(any(row["index"] == 1 for row in studio.suggestions(words, [])["corrections"]))

    def test_person_compositing_and_offline_model(self):
        original = np.zeros((2, 2, 3), np.uint8)
        original[:] = [0, 0, 255]
        painted = np.full((2, 2, 3), 255, np.uint8)
        person_mask.restore_person(painted, original, np.array([[1, 0], [.5, 1]], np.float32))
        self.assertEqual(painted[0, 0].tolist(), [0, 0, 255])
        self.assertEqual(painted[0, 1].tolist(), [255, 255, 255])
        self.assertEqual(painted[1, 0].tolist(), [128, 128, 255])
        model = person_mask.PersonMask()
        alpha = model.infer(np.zeros((480, 270, 3), np.uint8))
        self.assertEqual(alpha.shape, (480, 270))
        self.assertTrue(np.isfinite(alpha).all())
        self.assertTrue(((alpha >= 0) & (alpha <= 1)).all())

    def test_output_protection(self):
        for target in (C.INPUT_DIR / "bad.json", C.SAMPLES_DIR / "bad.png", C.ROOT / ".env"):
            with self.assertRaises(C.MontajError):
                studio.destination(target)
        for box in ("0,0,2,1", "0,0,NaN,1", "1,1,0,0"):
            with self.assertRaises(C.MontajError):
                studio.parse_box(box)
        with self.assertRaises(C.MontajError):
            studio.destination(WORK / "source.png", [WORK / "source.png", WORK / "other.mp4"])
        with self.assertRaises(C.MontajError):
            studio.metrics(Image.new("RGB", (10, 10)), [0, 0, .001, .001])


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        cls.video = WORK / "studio_fixture.mp4"
        C.run([C.need_tool("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", "testsrc=size=480x854:rate=30:duration=4",
               "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", cls.video])
        cls.hash = hashlib.sha256(cls.video.read_bytes()).hexdigest()
        style = C.load_style()
        style["zoom"]["face_aware"] = False
        style["sfx"]["enabled"] = False
        style["endcard"]["enabled"] = False
        cls.style = WORK / "test_style.json"
        C.write_json(style, cls.style)
        cls.srt = WORK / "demo.srt"
        C.write_srt([{"start": .1, "end": 1.1, "text": "{caps,y=0.2}*SINOV*"},
                     {"start": 1.15, "end": 2.2, "text": "*3 oyda* natija"},
                     {"start": 2.25, "end": 3.6, "text": "**sifat** muhim"}], cls.srt)
        cls.elements = WORK / "elements.json"
        C.write_json({"elements": [
            {"type": "handnote", "start": .1, "end": 1.2, "text": "Sinov izohi", "x": .32, "y": .36, "size": .8},
            {"type": "arrow", "start": .1, "end": 1.2, "points": [[.2,.27],[.6,.26],[.7,.4]]},
            {"type": "phone", "start": 1.2, "end": 2.3, "width": .25, "y": .29, "name": "Sinov", "handle": "@sinov", "bio": "Demo"},
            {"type": "stat", "start": 2.3, "end": 3.2, "value": 85, "ring": True, "size": .45, "y": .30},
            {"type": "follow", "start": 3.2, "end": 4, "handle": "@sinov", "name": "Sinov", "size": .18, "y": .32, "tap": .3},
        ]}, cls.elements)

    def test_01_stills_and_new_elements(self):
        cli("compose.py", self.video, "--style", self.style, "--subs", self.srt, "--elements", self.elements,
            "--stills", ".8,1.8,2.8,3.8", "--stills-out", WORK / "new_elements.jpg")
        with Image.open(WORK / "new_elements.jpg") as image:
            self.assertGreater(image.width, 1000)
        # Full scene is genuinely rendered later, not just stills.

    def test_02_approval_required_for_draft(self):
        out = WORK / "unapproved_draft.mp4"
        before = out.stat().st_mtime_ns if out.exists() else None
        cli("compose.py", self.video, "--style", self.style, "--subs", self.srt, "--draft", "-o", out, expected=3)
        self.assertEqual(out.stat().st_mtime_ns if out.exists() else None, before)

    def test_03_full_and_draft_benchmark(self):
        times = {}
        for name, flags in (("full", []), ("draft", ["--draft"])):
            start = time.perf_counter()
            out = WORK / (name+".mp4")
            cli("compose.py", self.video, "--style", self.style, "--subs", self.srt, "--elements", self.elements,
                "--approved", "-o", out, *flags)
            times[name] = round(time.perf_counter()-start, 3)
            meta = C.ffprobe_info(out)
            self.assertTrue(meta["has_audio"])
            self.assertAlmostEqual(meta["duration"], 4, delta=.15)
            self.assertEqual((meta["width"], meta["height"]), (1080, 1920) if name == "full" else (360, 640))
        times["speedup"] = round(times["full"]/times["draft"], 2)
        C.write_json(times, WORK / "benchmark.json")
        print(f"DRAFT BENCHMARK: {times}")

    def test_04_compare_cover_and_source_integrity(self):
        cli("studio.py", "compare", self.video, WORK / "draft.mp4", "--at", ".8,1.8", "--reference-at", ".8,1.8",
            "--box", ".1,.1,.8,.7", "--out", WORK / "comparison/report.json")
        report = C.read_json(WORK / "comparison/report.json")
        self.assertEqual(len(report["frames"]), 2)
        self.assertTrue((WORK / "comparison/compare.html").is_file())
        cli("studio.py", "cover", self.video, "--style", self.style, "--title", "Sinov muqovasi", "--at", ".8", "--out", WORK / "cover.png")
        with Image.open(WORK / "cover.png") as image:
            self.assertEqual(image.size, (1080, 1920))
        self.assertEqual(hashlib.sha256(self.video.read_bytes()).hexdigest(), self.hash)
        # A generated contact sheet must never overwrite a comparison input.
        collision = WORK / "collision"
        collision.mkdir(exist_ok=True)
        source = collision / "sheet_001.jpg"
        Image.new("RGB", (100, 100), "red").save(source)
        before = source.read_bytes()
        cli("studio.py", "compare", source, WORK / "draft.mp4", "--n", "1", "--out", collision / "report.json", expected=1)
        self.assertEqual(source.read_bytes(), before)
        cli("studio.py", "preflight", self.video, "--elements", self.elements, "--out", self.elements, expected=1)
        self.assertEqual(len(C.read_json(self.elements)["elements"]), 5)

    def test_05_prepare_only_never_renders_and_batch_resume(self):
        folder = WORK / "queue"
        folder.mkdir(exist_ok=True)
        rows = []
        for n in range(2):
            video = folder / f"studio_queue_{n}.mp4"
            video.write_bytes(self.video.read_bytes())
            words = WORK / f"queue_words_{n}.json"
            data = {"words": [{"start": i*.5, "end": i*.5+.4, "word": word, "prob": .99}
                              for i, word in enumerate("Bu faqat sinov matni".split())]}
            C.write_json(data, words)
            cli("pipeline.py", video, "--words", words, "--no-cut", "--prepare-only", "--style", self.style,
                "--approve-subs", expected=3)  # even this flag cannot make prepare-only render
            work = C.job_dir(video)
            C.write_json(data, work / "orig.words.json")
            rows.append(video)
        report = WORK / "queue-report.json"
        cli("studio.py", "batch", folder, "--no-cut", "--style", self.style, "--out", report)
        manifest = C.read_json(report)
        self.assertEqual([item["status"] for item in manifest["jobs"]], ["need_approval", "need_approval"])
        self.assertFalse(manifest["rendered"])
        mtimes = [(C.job_dir(video)/"subs.srt").stat().st_mtime_ns for video in rows]
        cli("studio.py", "batch", folder, "--no-cut", "--style", self.style, "--out", report, "--resume")
        self.assertEqual(mtimes, [(C.job_dir(video)/"subs.srt").stat().st_mtime_ns for video in rows])
        for video in rows:
            self.assertFalse((C.OUTPUT_DIR/(video.stem+"_final.mp4")).exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-only", action="store_true", help="Render qilmasdan qoidalarni sinash")
    args = parser.parse_args()
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Rules))
    if not args.unit_only:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Integration))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"STUDIO NATIJA: {result.testsRun-len(result.failures)-len(result.errors)}/{result.testsRun}")
    raise SystemExit(not result.wasSuccessful())
