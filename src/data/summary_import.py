"""Importación conservadora de tablas transcritas de resúmenes, no extractor de texto."""
import argparse
import json
import tempfile
from pathlib import Path

from .load_data import load_bundle
from .schema import INPUT_TABLES, KEYS, fields
from .store import Store, stable_id, write_csv

PROJECT = Path(__file__).resolve().parents[2]


def prepare_tables(payload, mode):
    """IDs opacos asignados en la transcripción; nunca deducir identidad de alias."""
    if set(payload) != {"mode", "tables"} or payload["mode"] != mode:
        raise ValueError("Declarar mode y tables; no mezclar datos privados y artificiales")
    tables = {t: [] for t in INPUT_TABLES}
    if set(payload["tables"]) - set(INPUT_TABLES):
        raise ValueError("Tabla no admitida")
    for table, rows in payload["tables"].items():
        seen = set()
        for raw in rows:
            if set(raw) - set(fields(table)):
                raise ValueError("Campo no admitido en " + table)
            row = {k: raw.get(k) for k in fields(table)}
            key = row[KEYS[table]]
            if not key or key in seen:
                raise ValueError("IDs ausentes o repetidos en " + table)
            seen.add(key)
            tables[table].append(row)
    for source in tables["sources"]:
        source.update(source_type="summary" if mode == "private" else "artificial",
                      evidence_level="supplied_summary" if mode == "private" else "artificial")
    source_ids = {s["source_id"] for s in tables["sources"]}
    for table in INPUT_TABLES[1:-1]:
        for row in tables[table]:
            source = row.get("source_id") or row.get("outcome_source_id")
            if source not in source_ids:
                raise ValueError("Cada registro necesita una fuente del resumen")
            if table == "opportunities":
                row["review_status"] = "pending"
                if row["exclude_from_training"] not in ("0", "1"):
                    raise ValueError("Declarar exclusión como 0 o 1")
                if row["exclude_from_training"] == "1" and not row["exclusion_reason"]:
                    raise ValueError("La exclusión necesita motivo")
            if table == "quotes":
                if row["first_priced_quote_status"] == "confirmed":
                    raise ValueError("Un resumen no confirma la primera cotización")
                row["first_priced_quote_status"] = row["first_priced_quote_status"] or "unknown"
                row["date_precision"] = row["date_precision"] or ("day" if row["sent_at"] else "unknown")
            # Conservar procedencia por campo sin atribuir conocimiento inicial.
            for name, value in row.items():
                if value is not None and name != KEYS[table]:
                    evidence_id = stable_id("E", table, row[KEYS[table]], name, source)
                    if not any(e["evidence_id"] == evidence_id for e in tables["field_evidence"]):
                        tables["field_evidence"].append(dict(evidence_id=evidence_id,
                            entity_type=table, entity_id=row[KEYS[table]], field_name=name,
                            source_id=source, locator="structured_summary/" + row[KEYS[table]],
                            known_at=None, time_precision="unknown", review_status="pending"))
    for evidence in tables["field_evidence"]:
        evidence["review_status"] = "pending"
    return tables


def import_summary(store, manifest, cutoff, scope_file=PROJECT / "docs/data_use_scope.md"):
    manifest = Path(manifest).resolve()
    if store.mode == "private":
        # This workflow stays closed until the project's scope record is completed.
        scope = Path(scope_file).read_text(encoding="utf-8")
        if "Estado: **confirmado para importación privada de resúmenes**" not in scope:
            raise ValueError("Alcance pendiente: registrar autorización aplicable en docs/data_use_scope.md")
        if manifest.is_relative_to(PROJECT):
            raise ValueError("El manifiesto privado debe permanecer fuera del proyecto")
    payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    tables = prepare_tables(payload, store.mode)
    # Temporary files stay outside the repository, including private bundles.
    with tempfile.TemporaryDirectory(prefix="quotescore-summary-") as temporary:
        for table, rows in tables.items():
            write_csv(Path(temporary) / (table + ".csv"), fields(table), rows)
        return load_bundle(store, temporary, cutoff)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--store", required=True)
    parser.add_argument("--mode", choices=("artificial", "private"), default="artificial")
    parser.add_argument("--cutoff", required=True)
    args = parser.parse_args()
    try:
        from datetime import date
        date.fromisoformat(args.cutoff)
        result = import_summary(Store(args.store, args.mode), args.manifest, args.cutoff)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError):
        print("Importación rechazada: revisar alcance, modo, rutas y contrato del resumen.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
