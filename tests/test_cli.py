"""Exercise actual commands in subprocesses, including exit codes and disk effects."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = str(Path(self.temp.name) / "store")

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-m", "src.data", "--store", self.store, *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, expected, result.stderr)
        if expected == 0:
            self.assertTrue(result.stdout, "Successful CLI commands must produce their JSON response")
        return json.loads(result.stdout) if result.stdout else None

    def test_complete_terminal_workflow_and_decision(self):
        self.cli("init")
        self.cli("load", "examples/artificial/input", "--cutoff", "2025-02-10")
        repeated = self.cli("load", "examples/artificial/input", "--cutoff", "2025-02-10")
        self.assertEqual(repeated["status"], "already_loaded")
        case = self.cli("review")
        decision = self.cli("decide", case["case_id"], "reject", "--source", "SRC_DEMO", "--reason", "Different fictional journeys")
        self.assertTrue(decision.startswith("DEC_"))
        report = self.cli("report", "--cutoff", "2025-02-10")
        self.assertTrue(Path(report).exists())
        self.assertTrue(self.cli("issues"))

    def test_invalid_event_does_not_publish_revision(self):
        self.cli("init")
        pointer = Path(self.store) / "CURRENT"
        before = pointer.read_text()
        self.cli("outcome", "MISSING", "won", "--at", "2025-02-06", "--source", "MISSING", "--reason", "Unknown", "--event-id", "EVENT", expected=2)
        self.assertEqual(before, pointer.read_text())

    def test_empty_report_runs_from_terminal(self):
        path = self.cli("report", "--cutoff", "2025-02-10")
        self.assertIn("Sin datos", Path(path).read_text(encoding="utf-8"))
