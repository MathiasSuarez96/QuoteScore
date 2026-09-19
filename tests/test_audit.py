"""Regression cases discovered during the critical review of delivery 1."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.build_demo import demo_tables
from src.data.store import Store, write_csv
from src.data.schema import fields, TABLE_COLUMNS
from src.data.load_data import load_bundle
from src.data.review_cases import decide, update_outcome, propose_issue_resolution
from src.data.quality_report import render_report, save_report
from src.data.snapshots import build_snapshots
from src.data.normalize import normalize
from src.data.validate_data import validate


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "store")
        self.data = demo_tables()

    def load(self):
        for table, rows in self.data.items():
            write_csv(self.root / "input" / (table + ".csv"), fields(table), rows)
        return load_bundle(self.store, self.root / "input", "2025-02-10")

    def test_changed_value_does_not_reuse_old_evidence(self):
        self.load()
        self.data["quotes"][0]["channel_at_quote"] = "phone"
        self.load()
        case = next(c for c in self.store.read()["review_queue"] if c["case_type"] == "record_correction")
        decide(self.store, case["case_id"], "confirm", "SRC_DEMO", "Documentary correction")
        snap = build_snapshots(self.store.read())[0]
        self.assertIsNone(snap["features"]["channel_at_quote"])
        old = next(e for e in self.data["field_evidence"] if e["entity_id"] == "Q_DEMO_1" and e["field_name"] == "channel_at_quote")
        self.data["field_evidence"].append(dict(old, evidence_id="E_NEW_CHANNEL", known_at="2025-02-04"))
        self.load()
        self.assertIsNone(build_snapshots(self.store.read())[0]["features"]["channel_at_quote"])

    def test_pending_duplicate_blocks_both_sides(self):
        self.load()
        snaps = {s["opportunity_id"]: s for s in build_snapshots(self.store.read())}
        for identifier in ("OP_DEMO_2", "OP_DEMO_3", "OP_DEMO_4"):
            self.assertIn("identity_review_pending", snaps[identifier]["temporal_reasons"])

    def test_confirming_duplicate_without_grouping_does_not_clear_identity(self):
        self.load()
        case = next(c for c in self.store.read()["review_queue"] if c["case_type"] == "duplicate_check")
        decide(self.store, case["case_id"], "confirm", "SRC_DEMO", "Duplicate finding confirmed; grouping pending")
        snap = next(s for s in build_snapshots(self.store.read()) if s["opportunity_id"] == case["entity_id"])
        self.assertIn("identity_review_pending", snap["temporal_reasons"])

    def test_explicit_exclusion_preserves_history_and_is_visible(self):
        self.data["opportunities"][0].update(exclude_from_training="1", exclusion_reason="Artificial administrative allocation")
        self.load()
        snap = build_snapshots(self.store.read())[0]
        self.assertIn("explicit_exclusion", snap["ineligibility_reason"])
        self.assertEqual(len(self.store.read()["opportunities"]), 4)

    def test_undated_won_is_not_reported_as_open(self):
        self.data["opportunities"][0].update(status="won", converted="1", outcome_source_id="SRC_DEMO", outcome_basis="Confirmed without date")
        self.load()
        report = render_report(self.store.read(), "2025-02-10", "artificial", "test")
        self.assertIn("desenlace sin fecha: 1 / 4", report)
        self.assertIn("abierta/dudosa: 3 / 4", report)

    def test_correction_of_close_date_removes_old_assertion(self):
        self.load()
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-04", "SRC_DEMO", "Initial assertion", "EV_OLD")
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-08", "SRC_DEMO", "Correct close date", "EV_NEW", "EV_OLD", event_kind="correction")
        report = render_report(self.store.read(), "2025-02-06", "artificial", "test")
        self.assertIn("ganada: 0 / 4", report)

    def test_reactivation_preserves_earlier_loss(self):
        self.load()
        update_outcome(self.store, "OP_DEMO_1", "lost", "2025-02-04", "SRC_DEMO", "Loss", "EV_OLD")
        update_outcome(self.store, "OP_DEMO_1", "open", "2025-02-08", "SRC_DEMO", "Same trip", "EV_NEW", "EV_OLD")
        report = render_report(self.store.read(), "2025-02-06", "artificial", "test")
        self.assertIn("perdida: 1 / 4", report)

    def test_cutoff_excludes_future_inventory(self):
        self.data["opportunities"][-1]["created_at"] = "2025-03-01"
        self.data["transactions"][0]["transaction_date"] = "2025-03-01"
        self.load()
        report = render_report(self.store.read(), "2025-02-10", "artificial", "test")
        self.assertIn("Oportunidades según conciliación actual: 3", report)
        self.assertIn("transactions: 0 registros", report)

    def test_partial_correction_with_other_existing_errors(self):
        self.data["quote_options"][0].update(passengers="0", currency=None)
        self.load()
        self.data["quote_options"][0]["currency"] = "USD"
        self.load()
        case = next(c for c in self.store.read()["review_queue"] if c["case_type"] == "record_correction")
        decide(self.store, case["case_id"], "confirm", "SRC_DEMO", "Resolve currency independently")
        self.assertEqual(self.store.read()["quote_options"][0]["currency"], "USD")

    def test_validator_does_not_crash_on_bad_numeric_cell(self):
        self.load()
        tables = self.store.read()
        tables["quote_options"][0]["gross_price"] = "invalid"
        self.assertTrue(any(i["issue_code"] == "invalid_decimal" for i in validate(tables)))

    def test_decimal_normalization_never_rounds_input(self):
        value = "123456789012345678901234567890.12"
        self.assertEqual(normalize(value, fields("quote_options")["gross_price"]), value)

    def test_quality_resolution_has_reversible_history(self):
        self.load()
        item = next(i for i in self.store.read()["quality_issues"] if i["issue_code"] == "price_scope_unknown")
        with self.assertRaises(ValueError):
            propose_issue_resolution(self.store, item["issue_id"], "resolved", "SRC_DEMO", "Still unknown")
        case = propose_issue_resolution(self.store, item["issue_id"], "accepted", "SRC_DEMO", "Tolerated missing value")
        decision = decide(self.store, case, "confirm", "SRC_DEMO", "Accept limitation")
        result = next(i for i in self.store.read()["quality_issues"] if i["issue_id"] == item["issue_id"])
        self.assertEqual(result["resolution_status"], "accepted")
        decide(self.store, case, "pending", "SRC_DEMO", "Reopen", decision)
        result = next(i for i in self.store.read()["quality_issues"] if i["issue_id"] == item["issue_id"])
        self.assertEqual(result["resolution_status"], "pending")

    def test_audit_rows_match_their_declared_schema(self):
        self.load()
        for table, rows in self.store.read().items():
            for row in rows:
                for name, spec in fields(table).items():
                    normalize(row[name], spec)

    def test_archived_revision_report_does_not_move_current(self):
        self.load()
        old = (self.store.root / "CURRENT").read_text()
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-04", "SRC_DEMO", "Won", "EV")
        current = (self.store.root / "CURRENT").read_text()
        report = save_report(self.store, "2025-02-10", revision=old).read_text(encoding="utf-8")
        self.assertIn("ganada: 0 / 4", report)
        self.assertEqual(current, (self.store.root / "CURRENT").read_text())
