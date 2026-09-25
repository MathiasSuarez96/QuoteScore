"""Entradas: un directorio de CSV sanitizados con IDs opacos persistentes."""
import hashlib
import re
from pathlib import Path

from .normalize import normalize
from .schema import INPUT_TABLES, KEYS, VERSION, RULES_VERSION, fields
from .store import json_text, now, read_csv, stable_id
from .validate_data import add_issues, issue, validate


def queue_change(tables, table, entity_id, current, proposed, source, reason="source_correction"):
    case_id = stable_id("CASE", table, entity_id, current, proposed)
    if not any(c["case_id"] == case_id for c in tables["review_queue"]):
        tables["review_queue"].append({"case_id": case_id, "case_type": "record_correction", "entity_type": table,
            "entity_id": entity_id, "proposed_opportunity_id": proposed.get("opportunity_id"),
            "evidence_source_id": source, "reason": reason, "current_json": json_text(current),
            "proposed_json": json_text(proposed), "status": "pending", "last_decision_id": None})
    return case_id


def load_bundle(store, directory, cutoff):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError("Directorio de entrada inexistente")
    if store.mode == "private" and directory.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Las entradas privadas deben permanecer fuera del proyecto")
    entries, fingerprints = {}, []
    for path in sorted(directory.glob("*.csv")):
        table = path.stem
        if table not in INPUT_TABLES:
            raise ValueError("Tabla de entrada no permitida; usar las siete plantillas de entrada")
        columns, rows = read_csv(path)
        if columns != list(fields(table)):
            raise ValueError(f"Encabezado incompatible en {table}; usar plantilla V1")
        entries[table] = rows
        fingerprints.append((table, hashlib.sha256(path.read_bytes()).hexdigest()))
    if not entries:
        raise ValueError("No se encontraron CSV de entrada")
    fingerprint = stable_id("BATCH", VERSION, RULES_VERSION, fingerprints)
    with store.locked():
        tables = store.read()
        if any(r["input_fingerprint"] == fingerprint for r in tables["load_runs"]):
            return {"status": "already_loaded", "fingerprint": fingerprint}
        pending_issues = []
        for table in INPUT_TABLES:
            index = {r[KEYS[table]]: r for r in tables[table]}
            for position, raw in enumerate(entries.get(table, []), 2):
                entity = raw.get(KEYS[table])
                if not entity or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", entity):
                    pending_issues.append(issue(table, stable_id("ROW", fingerprint, table, position), KEYS[table], "invalid_or_missing_id"))
                    continue
                row = {}
                for name, spec in fields(table).items():
                    try:
                        row[name] = normalize(raw.get(name), spec)
                    except ValueError as exc:
                        row[name] = None
                        pending_issues.append(issue(table, entity, name, str(exc), source=raw.get("source_id")))
                if table == "sources" and store.mode == "artificial" and row.get("evidence_level") != "artificial":
                    raise ValueError("El modo artificial solo admite fuentes etiquetadas artificial")
                if table == "quote_options":
                    p, a, c = (row.get(k) for k in ("passengers", "adults", "children"))
                    if all(v is not None for v in (p, a, c)) and int(p) != int(a) + int(c):
                        pending_issues.append(issue(table, entity, "passengers", "passenger_count_inconsistent", source=row.get("source_id")))
                        row["passengers"] = None
                    if row.get("price_scope") in (None, "unknown"):
                        # An explicit per-person quote has its own scope; other amounts do not.
                        for name in ("gross_price", "discount_amount", "net_price", "points_value_quoted", "quoted_cash_balance"):
                            row[name] = None
                if table == "quote_components" and row.get("price_scope") in (None, "unknown"):
                    if row.get("amount") is not None:
                        pending_issues.append(issue(table, entity, "price_scope", "price_scope_unknown", "warning", row.get("source_id")))
                        row["amount"] = None
                content_fingerprint = stable_id("CONTENT", VERSION, table, entity, row)
                if any(r["content_fingerprint"] == content_fingerprint for r in tables["import_records"]):
                    # Compare against imported content, not the current commercial outcome.
                    continue
                tables["import_records"].append({"record_version_id": stable_id("REC", content_fingerprint),
                    "entity_type": table, "entity_id": entity, "content_fingerprint": content_fingerprint,
                    "run_id": stable_id("RUN", fingerprint), "recorded_at": now(), "normalized_json": json_text(row)})
                if entity in index:
                    if index[entity] != row:
                        queue_change(tables, table, entity, index[entity], row, row.get("source_id") or row.get("outcome_source_id") or (entity if table == "sources" else None))
                        pending_issues.append(issue(table, entity, KEYS[table], "source_correction_pending", "warning"))
                    continue
                tables[table].append(row)
                index[entity] = row
                if table == "opportunities" and row.get("converted") is not None:
                    tables["outcome_history"].append({"outcome_event_id": stable_id("OUT", fingerprint, entity),
                        "opportunity_id": entity, "previous_status": None, "new_status": row.get("status"),
                        "converted": row.get("converted"), "outcome_at": row.get("outcome_at"), "recorded_at": now(),
                        "source_id": row.get("outcome_source_id"), "reason": row.get("outcome_basis"),
                        "supersedes_event_id": None, "details_json": json_text(row)})
        findings = validate(tables)
        add_issues(tables, pending_issues + findings)
        # Same content under distinct IDs is only a suspicion; never discard either row.
        for table in ("opportunities", "quotes", "transactions"):
            seen = {}
            key = KEYS[table]
            for row in tables[table]:
                content = {k: v for k, v in row.items() if k != key}
                if not any(v is not None for k, v in content.items() if k not in ("status", "review_status", "exclude_from_training")):
                    continue
                signature = json_text(content)
                if signature in seen:
                    add_issues(tables, [issue(table, row[key], key, "suspected_duplicate", "warning")])
                    case_id = stable_id("DUP", table, row[key], seen[signature])
                    if not any(c["case_id"] == case_id for c in tables["review_queue"]):
                        tables["review_queue"].append({"case_id": case_id, "case_type": "duplicate_check", "entity_type": table,
                            "entity_id": row[key], "proposed_opportunity_id": None, "evidence_source_id": row.get("source_id"),
                            "reason": "Equal content under different IDs; review identity; no automatic deletion",
                            "current_json": json_text({"record_id": row[key]}), "proposed_json": json_text({"possible_duplicate_of": seen[signature]}),
                            "status": "pending", "last_decision_id": None})
                else:
                    seen[signature] = row[key]
        run = {"run_id": stable_id("RUN", fingerprint), "schema_version": VERSION, "rules_version": RULES_VERSION,
               "input_fingerprint": fingerprint, "generated_at": now(), "cutoff": cutoff,
               "input_counts": json_text({t: len(r) for t, r in entries.items()}),
               "output_counts": json_text({t: len(tables[t]) for t in INPUT_TABLES})}
        tables["load_runs"].append(run)
        revision = store.commit(tables)
        return {"status": "loaded", "revision": revision, "run_id": run["run_id"], "issues": len(tables["quality_issues"]), "pending_cases": sum(c["status"] == "pending" for c in tables["review_queue"])}
