import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.data.__main__ import main
from src.data.load_data import load_bundle
from src.data.normalize import normalize, on_or_before
from src.data.quality_report import render_report, save_report
from src.data.reconcile_opportunities import canonical_id, propose_group
from src.data.review_cases import decide, update_outcome
from src.data.schema import INPUT_TABLES, KEYS, TABLE_COLUMNS, empty_tables, fields
from src.data.snapshots import build_snapshots, save_snapshots
from src.data.store import Store, read_csv, write_csv
from src.data.validate_data import validate
from tools.build_demo import demo_tables


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root / "store")
        self.data = demo_tables()
        self.write_bundle()

    def write_bundle(self, data=None, folder="input"):
        directory = self.root / folder
        for table, rows in (data or self.data).items():
            write_csv(directory / (table + ".csv"), fields(table), rows)
        return directory

    def load(self):
        return load_bundle(self.store, self.root / "input", "2025-02-10")

    def test_idempotence_including_reordered_rows(self):
        self.load()
        before = self.store.read()
        self.assertEqual(self.load()["status"], "already_loaded")
        for rows in self.data.values():
            rows.reverse()
        self.write_bundle()
        self.load()
        after = self.store.read()
        for table in INPUT_TABLES + ("quality_issues", "reconciliation_log", "review_queue"):
            self.assertEqual(before[table], after[table], table)
        self.assertEqual(len(after["load_runs"]), 2)

    def test_partial_sale_destination_change_preserves_snapshot(self):
        self.load()
        path = save_snapshots(self.store, "Initial", "SRC_DEMO")
        initial = path.read_bytes()
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-06", "SRC_DEMO", "Artificial partial sale", "OUT_TEST", sold_scope="flight_only", sale_extent="partial", final_destination="Distinct fictional destination")
        again = save_snapshots(self.store, "After outcome", "SRC_DEMO")
        self.assertEqual(path, again)
        self.assertEqual(initial, again.read_bytes())
        row = self.store.read()["opportunities"][0]
        self.assertEqual(row["converted"], "1")
        self.assertEqual(len(self.store.read()["opportunities"]), 4)

    def test_reordered_old_bundle_does_not_revert_new_outcome(self):
        self.load()
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-06", "SRC_DEMO", "Confirmed", "EV_NEW")
        before = self.store.read()
        for rows in self.data.values():
            rows.reverse()
        self.write_bundle()
        self.load()
        after = self.store.read()
        self.assertEqual(before["opportunities"], after["opportunities"])
        self.assertEqual(before["review_queue"], after["review_queue"])
        self.assertEqual(before["import_records"], after["import_records"])

    def test_invalid_evidence_precision_cannot_verify_initial(self):
        self.load()
        tables = self.store.read()
        for e in tables["field_evidence"]:
            if e["entity_id"] == "Q_DEMO_1" and e["field_name"] == "sent_at":
                e["time_precision"] = "timestamp"
        self.assertEqual(build_snapshots(tables)[0]["snapshot_status"], "pending")

    def test_outcome_idempotence_and_reactivation_audit(self):
        self.load()
        args = (self.store, "OP_DEMO_1", "lost", "2025-02-04", "SRC_DEMO", "Confirmed", "EV_1")
        update_outcome(*args)
        update_outcome(*args)
        self.assertEqual(len(self.store.read()["outcome_history"]), 1)
        with self.assertRaises(ValueError):
            update_outcome(self.store, "OP_DEMO_1", "open", "2025-02-05", "SRC_DEMO", "Same journey reactivated", "EV_2")
        update_outcome(self.store, "OP_DEMO_1", "open", "2025-02-05", "SRC_DEMO", "Same journey reactivated", "EV_2", "EV_1")
        self.assertIsNone(self.store.read()["opportunities"][0]["converted"])
        self.assertEqual(self.store.read()["outcome_history"][-1]["supersedes_event_id"], "EV_1")

    def test_unknown_passengers_price_and_multiple_issues(self):
        self.load()
        tables = self.store.read()
        codes = {i["issue_code"] for i in tables["quality_issues"] if i["entity_id"] == "OPT_DEMO_2"}
        self.assertTrue({"passenger_count_inconsistent", "price_scope_unknown"} <= codes)
        snap = next(s for s in build_snapshots(tables) if s["opportunity_id"] == "OP_DEMO_2")
        option = snap["features"]["options"][0]
        self.assertIsNone(option["passengers"])
        self.assertIsNone(option["gross_price"])
        self.assertIsNone(option["net_price_per_person"])
        self.assertEqual(option["destination_summary"], "Destino ficticio 2")

    def test_no_final_fields_or_future_information(self):
        self.load()
        tables = self.store.read()
        q = tables["quotes"][0]
        q["channel_at_quote"] = "phone"
        for e in tables["field_evidence"]:
            if e["entity_id"] == q["quote_id"] and e["field_name"] == "channel_at_quote":
                e["known_at"] = "2025-02-04"
        tables["opportunities"][0].update(final_sale_amount="999999", final_destination="SECRET_FINAL")
        snapshot = build_snapshots(tables)[0]
        self.assertIsNone(snapshot["features"]["channel_at_quote"])
        self.assertNotIn("SECRET_FINAL", json.dumps(snapshot))
        self.assertNotIn("final_sale_amount", snapshot["features"])

    def test_final_quote_not_substitute_for_missing_initial(self):
        self.load()
        tables = self.store.read()
        tables["quotes"][0]["first_priced_quote_status"] = "candidate"
        snap = build_snapshots(tables)[0]
        self.assertEqual(snap["snapshot_status"], "pending")
        self.assertEqual(snap["features"], {})

    def test_source_correction_review_and_reversal(self):
        self.load()
        original = copy.deepcopy(self.store.read()["quotes"][0])
        self.data["quotes"][0]["channel_at_quote"] = "phone"
        self.write_bundle()
        self.load()
        self.assertEqual(original, self.store.read()["quotes"][0])
        case = next(c for c in self.store.read()["review_queue"] if c["case_type"] == "record_correction")
        first = decide(self.store, case["case_id"], "confirm", "SRC_DEMO", "Verified correction")
        self.assertEqual(self.store.read()["quotes"][0]["channel_at_quote"], "phone")
        with self.assertRaises(ValueError):
            decide(self.store, case["case_id"], "reject", "SRC_DEMO", "Revert")
        second = decide(self.store, case["case_id"], "reject", "SRC_DEMO", "Revert", first)
        self.assertEqual(original, self.store.read()["quotes"][0])
        log = self.store.read()["reconciliation_log"]
        self.assertEqual(len(log), 2)
        self.assertEqual(log[-1]["supersedes_decision_id"], first)
        self.assertNotEqual(first, second)

    def test_corrected_snapshot_version_retains_previous(self):
        self.load()
        original = save_snapshots(self.store, "First", "SRC_DEMO")
        self.data["quotes"][0]["channel_at_quote"] = "phone"
        self.write_bundle()
        self.load()
        case = next(c for c in self.store.read()["review_queue"] if c["case_type"] == "record_correction")
        decide(self.store, case["case_id"], "confirm", "SRC_DEMO", "Documented initial correction")
        with self.assertRaises(ValueError):
            save_snapshots(self.store, "Missing source")
        corrected = save_snapshots(self.store, "Documented initial correction", "SRC_DEMO")
        self.assertNotEqual(original, corrected)
        self.assertTrue(original.exists())

    def test_group_and_revert_preserve_original_ids(self):
        self.load()
        case_id = propose_group(self.store, "OP_DEMO_4", "OP_DEMO_1", "SRC_DEMO", "Same trip evidence")
        decision = decide(self.store, case_id, "confirm", "SRC_DEMO", "Confirmed same trip")
        self.assertEqual(canonical_id(self.store.read(), "OP_DEMO_4"), "OP_DEMO_1")
        self.assertEqual(len(build_snapshots(self.store.read())), 3)
        decide(self.store, case_id, "pending", "SRC_DEMO", "Reopen with new evidence", decision)
        self.assertEqual(canonical_id(self.store.read(), "OP_DEMO_4"), "OP_DEMO_4")
        self.assertEqual(len(self.store.read()["opportunities"]), 4)

    def test_duplicate_suspicion_never_deletes(self):
        duplicate = dict(self.data["transactions"][0], transaction_id="TX_DISTINCT")
        self.data["transactions"].append(duplicate)
        self.write_bundle()
        self.load()
        tables = self.store.read()
        self.assertEqual(len(tables["transactions"]), 2)
        self.assertTrue(any(c["case_type"] == "duplicate_check" for c in tables["review_queue"]))
        self.assertTrue(any(i["issue_code"] == "suspected_duplicate" for i in tables["quality_issues"]))

    def test_invalid_cells_null_and_no_crash(self):
        self.data["quote_options"][0].update(passengers="two", net_price="1,200.50", departure_date="12/05/2025")
        self.write_bundle()
        self.load()
        row = self.store.read()["quote_options"][0]
        self.assertIsNone(row["passengers"])
        self.assertIsNone(row["net_price"])
        self.assertIsNone(row["departure_date"])
        self.assertTrue(save_report(self.store, "2025-02-10").exists())

    def test_foreign_key_error_recorded(self):
        self.data["quotes"][0]["opportunity_id"] = "OP_MISSING"
        self.write_bundle()
        self.load()
        self.assertTrue(any(i["issue_code"] == "missing_foreign_key" for i in self.store.read()["quality_issues"]))

    def test_empty_report_and_templates(self):
        report = render_report(empty_tables(), "2025-02-10", "artificial", "empty")
        self.assertIn("Sin datos", report)
        self.assertNotIn("28 %", report)
        for table in TABLE_COLUMNS:
            folder = "input" if table in INPUT_TABLES else "audit"
            columns, rows = read_csv(Path("templates") / folder / (table + ".csv"))
            self.assertEqual(columns, list(fields(table)))
            self.assertEqual(rows, [])

    def test_null_zero_and_date_precision(self):
        spec = fields("quotes")["repeat_customer_at_quote"]
        self.assertIsNone(normalize("", spec))
        self.assertEqual(normalize("0", spec), "0")
        self.assertFalse(on_or_before("2025-02-03", "2025-02-03T12:00:00+00:00"))
        self.assertTrue(on_or_before("2025-02-02", "2025-02-03T12:00:00+00:00"))
        self.assertFalse(on_or_before("2025-02-03T14:00:00", "2025-02-03T15:00:00"))

    def test_report_cutoff_and_reproducible_archive(self):
        self.load()
        update_outcome(self.store, "OP_DEMO_1", "won", "2025-02-06", "SRC_DEMO", "Confirmed", "EV")
        early = render_report(self.store.read(), "2025-02-05", "artificial", "test")
        later = render_report(self.store.read(), "2025-02-06", "artificial", "test")
        self.assertIn("ganada: 0 / 4", early)
        self.assertIn("ganada: 1 / 4", later)
        a = save_report(self.store, "2025-02-06")
        b = save_report(self.store, "2025-02-06")
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists())

    def test_private_data_cannot_live_in_repo(self):
        with self.assertRaises(ValueError):
            Store("local/private", "private")

    def test_sources_mode_and_schema_rejected_atomically(self):
        self.data["sources"][0]["evidence_level"] = "original_verified"
        self.write_bundle()
        with self.assertRaises(ValueError):
            self.load()
        self.assertFalse((self.store.root / "CURRENT").exists())

    def test_sale_summary_does_not_confirm_outcome(self):
        self.load()
        self.assertIsNone(self.store.read()["opportunities"][0]["converted"])


if __name__ == "__main__":
    unittest.main()
