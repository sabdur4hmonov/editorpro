"""Ikki video eslatmasi va haqiqiy jarayonlar orqali FIFO CPU qulfi sinovlari."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import common as C
import handoff

BOOT = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import common as C
import handoff as H
C.setup_console()
C.TEMP_DIR = Path(sys.argv[2])
C.BUSY_FILE = C.TEMP_DIR / '.busy.json'
H.FILE = C.TEMP_DIR / 'PROJECT.md'
"""


class ParallelTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory(prefix="montaj-parallel-")
        self.root = Path(self.fixture.name)
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)
        # Edge delegates to child processes; profile DB handles can close after PNG completion.
        # Require full cleanup, retry only this transient Windows sharing violation.
        start = time.monotonic()
        deadline = start + 30
        while True:
            try:
                self.fixture.cleanup()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.2)
        if time.monotonic()-start > .5:
            print(f"TEST CLEANUP: Edge profili {time.monotonic()-start:.2f}s da bo'shadi")

    def start(self, code, *args, agent="test"):
        process = subprocess.Popen([sys.executable, "-u", "-c", BOOT + code, str(C.ROOT / "scripts"),
                                    str(self.root), *map(str, args)], cwd=C.ROOT,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   text=True, encoding="utf-8", env={**os.environ, "MONTAJ_AGENT": agent})
        self.processes.append(process)
        return process

    def finished(self, process, expected=0):
        out, err = process.communicate(timeout=12)
        self.assertEqual(process.returncode, expected, out + err)
        return out, err

    def wait_for(self, predicate):
        deadline = time.monotonic()+8
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail("Jarayon tayyor bo'lishini 8s kutdik")
            time.sleep(.02)

    def holder(self, seconds=1.2):
        process = self.start("C.busy_acquire('first', timeout=5); print('FIRST_RUN'); time.sleep(float(sys.argv[3]))",
                             seconds, agent="claude")
        self.wait_for(lambda: (self.root / ".busy.json").is_file())
        return process

    def test_two_video_notes_and_project_are_independent(self):
        project = self.root / "PROJECT.md"
        project.write_text("Loyiha ruxsatlari saqlanadi", encoding="utf-8")
        first = self.start("H.write_video_note('input/parallel_a.mp4', 'Matn A tasdiq kutilmoqda', 'claude')")
        second = self.start("H.write_video_note('input/parallel_b.mp4', 'Matn B tasdiqlangan: ha', 'codex')")
        self.finished(first); self.finished(second)
        a, b = self.root / "parallel_a/HOLAT.md", self.root / "parallel_b/HOLAT.md"
        original = a.read_bytes()
        self.assertIn("Matn B", b.read_text(encoding="utf-8"))
        update = self.start("H.write_video_note('input/parallel_b.mp4', 'Faqat B yangilandi', 'codex')")
        self.finished(update)
        self.assertEqual(a.read_bytes(), original)
        out, _ = self.finished(self.start("H.show()"))
        self.assertIn("Egasi: claude", out); self.assertIn("Egasi: codex", out)
        self.assertIn("parallel_a.mp4", out); self.assertIn("parallel_b.mp4", out)
        self.assertEqual(project.read_text(encoding="utf-8"), "Loyiha ruxsatlari saqlanadi")
        before = b.read_bytes()
        rejected = self.start("C.run_main(lambda: H.write_video_note('input/parallel_b.mp4', 'bad', 'claude'))")
        _, err = self.finished(rejected, 1)
        self.assertIn("tegishli", err)
        self.assertEqual(b.read_bytes(), before)
        self.finished(self.start("H.write_video_note('input/parallel_b.mp4', None, 'codex', done=True)"))
        out, _ = self.finished(self.start("H.show()"))
        self.assertNotIn("Egasi: codex", out)
        self.assertIn("Faqat B yangilandi", b.read_text(encoding="utf-8"))

    def test_second_heavy_job_waits_then_runs(self):
        first = self.holder(1.3)
        second = self.start("C.busy_acquire('second', timeout=5); print('SECOND_RUN')", agent="codex")
        self.wait_for(lambda: len(list((self.root / ".busy.queue").glob("*.json"))) == 1)
        self.assertIsNone(second.poll())
        self.assertEqual(C._lock_record(self.root / ".busy.json")["agent"], "claude")
        self.finished(first)
        out, _ = self.finished(second)
        self.assertIn("[NAVBAT]", out); self.assertIn("claude", out); self.assertIn("SECOND_RUN", out)
        self.assertFalse((self.root / ".busy.json").exists())
        self.assertFalse(list((self.root / ".busy.queue").glob("*.json")))

    def test_wait_timeout_does_not_start_or_steal_lock(self):
        first = self.holder(2)
        start = time.monotonic()
        second = self.start("C.run_main(lambda: (C.busy_acquire('second', timeout=.35), print('SHOULD_NOT_RUN')))", agent="codex")
        out, err = self.finished(second, 1)
        self.assertGreaterEqual(time.monotonic()-start, .35)
        self.assertIn("Kutish limiti", err); self.assertIn("claude", err)
        self.assertNotIn("SHOULD_NOT_RUN", out)
        self.assertEqual(C._lock_record(self.root / ".busy.json")["agent"], "claude")
        self.assertFalse(list((self.root / ".busy.queue").glob("*.json")))
        self.finished(first)

    def test_selftest_refuses_other_unfinished_video(self):
        self.finished(self.start("H.write_video_note('input/parallel_busy.mp4', 'Matn kutilmoqda', 'claude')"))
        code = "import selftest; sys.argv=['selftest', '--no-whisper']; C.run_main(selftest.main)"
        _, err = self.finished(self.start(code, agent="codex"), 1)
        self.assertIn("selftest ishlatilmaydi", err)
        self.assertIn("claude", err)

    def test_stale_holder_and_waiter_do_not_block(self):
        stale = {"pid": 1, "agent": "stale", "what": "dead", "queued_at": 0, "alive_at": 0}
        (self.root / ".busy.json").write_text(json.dumps(stale))
        queue = self.root / ".busy.queue"
        queue.mkdir()
        (queue / "stale.json").write_text(json.dumps(stale))
        out, _ = self.finished(self.start("C.busy_acquire('fresh', timeout=.5); print('FRESH_RUN')"))
        self.assertIn("FRESH_RUN", out)
        self.assertFalse((self.root / ".busy.json").exists())
        self.assertFalse(list(queue.glob("*.json")))

    def test_fresh_partial_lock_is_not_stolen(self):
        lock = self.root / ".busy.json"
        lock.write_text("{")
        code = "C.run_main(lambda: (C.busy_acquire('new', timeout=.2), print('SHOULD_NOT_RUN')))"
        out, err = self.finished(self.start(code), 1)
        self.assertIn("Kutish limiti", err)
        self.assertNotIn("SHOULD_NOT_RUN", out)
        self.assertEqual(lock.read_text(), "{")

    def test_two_html_renders_use_independent_video_profiles(self):
        from PIL import Image
        processes = []
        for name, color in (("graphic_a", "#FF0000"), ("graphic_b", "#0000FF")):
            folder = self.root / name
            (folder / "gfx").mkdir(parents=True)
            html = folder / "gfx/card.html"
            html.write_text(f'<div style="width:64px;height:64px;background:{color}"></div>', encoding="utf-8")
            code = "import html_render; html_render.render(Path(sys.argv[3]), Path(sys.argv[4]), size=(64,64), transparent=False)"
            processes.append(self.start(code, html, folder / "result.png"))
        for process in processes:
            out, err = process.communicate(timeout=60)
            self.assertEqual(process.returncode, 0, out+err)
        for name, rgb in (("graphic_a", (255,0,0)), ("graphic_b", (0,0,255))):
            folder = self.root / name
            with Image.open(folder / "result.png") as image:
                self.assertEqual(image.convert("RGB").getpixel((32,32)), rgb)
            self.assertTrue((folder / ".html_render/profile").is_dir())
        self.assertFalse((self.root / ".html_render").exists())

    def test_fifo_and_same_process_nested_acquire(self):
        first = self.holder(2)
        code = """
C.busy_acquire(sys.argv[3], timeout=6)
C.busy_acquire('nested', timeout=0)
events = C.TEMP_DIR / 'events.json'
C.write_json((C.read_json(events) if events.exists() else []) + [sys.argv[3]], events)
print('RUN')
time.sleep(.3)
"""
        second = self.start(code, "second", agent="codex")
        self.wait_for(lambda: len(list((self.root / ".busy.queue").glob("*.json"))) == 1)
        third = self.start(code, "third", agent="claude")
        self.wait_for(lambda: len(list((self.root / ".busy.queue").glob("*.json"))) == 2)
        self.finished(first)
        second_out, _ = self.finished(second)
        third_out, _ = self.finished(third)
        self.assertIn("RUN", second_out); self.assertIn("RUN", third_out)
        self.assertEqual(json.loads((self.root / "events.json").read_text()), ["second", "third"])
        self.assertFalse((self.root / ".busy.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
