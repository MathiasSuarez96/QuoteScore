"""Casos artificiales independientes; sin transcripciones comerciales."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.data.summary_import import import_summary, prepare_tables
from src.data.snapshots import build_snapshots
from src.data.store import Store


def artificial_summary():
    return {"mode": "artificial", "tables": {
        "sources": [{"source_id": "S_FICTION", "sanitized_reference": "Independent artificial summary"}],
        "opportunities": [
            {"opportunity_id": "O_FICTION_A", "status": "lost", "converted": "0", "outcome_source_id": "S_FICTION", "outcome_basis": "Artificial declared loss", "exclude_from_training": "0"},
            {"opportunity_id": "O_FICTION_B", "status": "won", "converted": "1", "outcome_source_id": "S_FICTION", "outcome_basis": "Artificial declared sale", "final_sale_amount": "72", "exclude_from_training": "1", "exclusion_reason": "Artificial administrative assignment"}],
        "quotes": [
            {"quote_id": "Q_FICTION_A", "opportunity_id": "O_FICTION_A", "sent_at": "2024-01-02", "source_id": "S_FICTION"},
            {"quote_id": "Q_FICTION_B", "opportunity_id": "O_FICTION_A", "sent_at": "2024-01-05", "source_id": "S_FICTION"}],
    }}


class SummaryImportTests(unittest.TestCase):
    def test_load_repeat_and_no_temporal_invention(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "summary.json"
            payload = artificial_summary()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            store = Store(root / "store")
            self.assertEqual(import_summary(store, manifest, "2024-02-01")["status"], "loaded")
            self.assertEqual(import_summary(store, manifest, "2024-02-01")["status"], "already_loaded")
            tables = store.read()
            self.assertEqual(len(tables["opportunities"]), 2)
            self.assertEqual(len(tables["quotes"]), 2)
            self.assertIsNone(tables["opportunities"][0]["outcome_at"])
            self.assertEqual(tables["quote_options"], [])
            self.assertTrue(all(s["features"] == {} and not s["training_eligible"] for s in build_snapshots(tables)))
            self.assertEqual(tables["opportunities"][1]["exclude_from_training"], "1")
            for rows in payload["tables"].values():
                rows.reverse()
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            import_summary(store, manifest, "2024-02-01")
            self.assertEqual(store.read()["opportunities"], tables["opportunities"])

    def test_summary_level_and_pending_evidence(self):
        payload = artificial_summary()
        payload["mode"] = "private"
        tables = prepare_tables(payload, "private")  # Artificial values only; no private store.
        self.assertEqual(tables["sources"][0]["evidence_level"], "supplied_summary")
        self.assertTrue(all(e["review_status"] == "pending" and e["known_at"] is None for e in tables["field_evidence"]))

    def test_scope_blocks_before_reading_input_or_writing_store(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = Store(root / "store", "private")
            scope = root / "scope.md"
            scope.write_text("Estado: pendiente", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Alcance pendiente"):
                import_summary(store, root / "does-not-exist.json", "2024-02-01", scope)
            self.assertFalse(store.root.exists())

    def test_reject_duplicate_ids_and_initial_confirmation(self):
        payload = artificial_summary()
        payload["tables"]["opportunities"].append(copy.deepcopy(payload["tables"]["opportunities"][0]))
        with self.assertRaises(ValueError):
            prepare_tables(payload, "artificial")
        payload = artificial_summary()
        payload["tables"]["quotes"][0]["first_priced_quote_status"] = "confirmed"
        with self.assertRaises(ValueError):
            prepare_tables(payload, "artificial")

    def test_confirmed_private_scope_preserves_summary_level(self):
        # Entirely artificial values exercise the private storage contract.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scope = root / "scope.md"
            scope.write_text("Estado: **confirmado para importación privada de resúmenes**", encoding="utf-8")
            payload = artificial_summary()
            payload["mode"] = "private"
            manifest = root / "summary.json"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            store = Store(root / "store", "private")
            self.assertEqual(import_summary(store, manifest, "2024-02-01", scope)["status"], "loaded")
            self.assertEqual(import_summary(store, manifest, "2024-02-01", scope)["status"], "already_loaded")
            self.assertEqual({r["evidence_level"] for r in store.read()["sources"]}, {"supplied_summary"})
            self.assertTrue(all(s["features"] == {} for s in build_snapshots(store.read())))


if __name__ == "__main__":
    unittest.main()
