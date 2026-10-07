"""Skill sinxronlash va MCP chegaralarini haqiqiy stdio orqali tekshiradi."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import sync_skills
from test_parallel import ParallelTests


class SetupTests(unittest.TestCase):
    def test_sync_preserves_source_and_instructions(self):
        with tempfile.TemporaryDirectory(prefix="agent-setup-") as directory:
            root = Path(directory)
            source = '---\nname: demo\ndescription: Demo\nargument-hint: "<video>"\n---\nArguments: `$ARGUMENTS`\nKeep every instruction.\n'
            for name in sync_skills.NAMES:
                path = root / "docs/claude_skills" / name / "SKILL.md"
                path.parent.mkdir(parents=True)
                path.write_text(source, encoding="utf-8")
            self.assertEqual(len(sync_skills.sync(root)), 8)
            self.assertFalse((root / ".agents").exists())  # --check never writes
            sync_skills.sync(root, apply=True)
            self.assertEqual(sync_skills.sync(root), [])
            self.assertEqual((root / "docs/claude_skills/montaj/SKILL.md").read_text(), source)
            self.assertEqual((root / ".claude/skills/montaj/SKILL.md").read_text(), source)
            codex = (root / ".agents/skills/montaj/SKILL.md").read_text()
            self.assertIn("Keep every instruction.\n", codex)
            self.assertNotIn("argument-hint:", codex)
            self.assertIn("<arguments supplied in the user prompt>", codex)
            (root / "docs/claude_skills/montaj/SKILL.md").write_text(source + "New instruction.\n")
            self.assertEqual(len(sync_skills.sync(root)), 2)
            sync_skills.sync(root, apply=True)
            self.assertIn("New instruction.", (root / ".agents/skills/montaj/SKILL.md").read_text())

    def test_missing_source_does_not_write_copies(self):
        with tempfile.TemporaryDirectory(prefix="agent-setup-") as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                sync_skills.sync(root, apply=True)
            self.assertFalse((root / ".agents").exists())

    def test_stdio_protocol_and_tools(self):
        def req(identity, method, params=None):
            return {"jsonrpc": "2.0", "id": identity, "method": method, "params": params or {}}
        messages = [
            req(1, "tools/list"),
            req(2, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                   "clientInfo": {"name": "test", "version": "1"}}),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            req(3, "tools/list"), req(4, "ping"),
            req(5, "tools/call", {"name": "read_guide", "arguments": {"guide": "memory"}}),
            req(6, "tools/call", {"name": "read_guide", "arguments": {"guide": "../../.env"}}),
            req(7, "tools/call", {"name": "project_state", "arguments": {"command": "anything"}}),
            req(8, "tools/call", {"name": "skills_status"}),
            req(9, "tools/call", {"name": "render"}),
            req(10, "tools/call", {"name": "project_state"}),
            req(11, "server/discover"),
            req(12, "initialize", {"protocolVersion": "unsupported-version"}),
        ]
        wire = "\n".join(json.dumps(message) for message in messages) + "\n{broken\n"
        run = subprocess.run([sys.executable, str(sync_skills.ROOT / "scripts/project_mcp.py")],
                             input=wire, capture_output=True, text=True, encoding="utf-8", timeout=90)
        self.assertEqual(run.returncode, 0, run.stderr)
        replies = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(replies), 13)  # notification has no response, malformed JSON has one
        by_id = {reply["id"]: reply for reply in replies}
        self.assertEqual(by_id[1]["error"]["code"], -32000)
        self.assertEqual(by_id[2]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(len(by_id[3]["result"]["tools"]), 3)
        self.assertEqual(by_id[4]["result"], {})
        self.assertIn("Claude va Codex", by_id[5]["result"]["content"][0]["text"])
        for identity in (6, 7):
            self.assertTrue(by_id[identity]["result"]["isError"])
        self.assertEqual(by_id[9]["error"]["code"], -32602)
        self.assertFalse(by_id[8]["result"]["isError"])
        self.assertIn("Navbat almashish", by_id[10]["result"]["content"][0]["text"])
        self.assertEqual(by_id[11]["error"]["code"], -32601)
        self.assertEqual(by_id[12]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(by_id[None]["error"]["code"], -32700)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
