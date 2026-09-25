"""Snapshots de auditoría, sin exportar una tabla de entrenamiento prematura."""
import json
from decimal import Decimal

from .normalize import on_or_before
from .reconcile_opportunities import canonical_id
from .schema import VERSION, RULES_VERSION
from .store import json_text, now, stable_id
from .validate_data import validate

QUOTE_FEATURES = ("channel_at_quote", "lead_source_at_quote", "request_type_at_quote", "preselected_product_at_quote", "repeat_customer_at_quote", "reactivated_lead_at_quote", "date_flexibility_at_quote", "credit_available_at_quote", "financing_available_at_quote")
OPTION_FEATURES = ("product_scope", "origin", "destination_summary", "destination_count", "departure_date", "return_date", "nights", "passengers", "adults", "children", "currency", "price_scope", "gross_price", "discount_amount", "net_price", "quoted_price_per_person", "points_available", "points_proposed", "points_value_quoted", "quoted_cash_balance")


def build_snapshots(tables):
    issues = validate(tables)
    sources = {r["source_id"]: r for r in tables["sources"]}
    verified_levels = {"original_verified", "user_confirmation", "artificial"}

    def proven(table, row, field, at):
        key = {"quotes": "quote_id", "quote_options": "option_id"}[table]
        if any(i["entity_type"] == table and i["entity_id"] == row[key] and i["field_name"] == field for i in issues):
            return False
        return any(e["entity_type"] == table and e["entity_id"] == row[key] and e["field_name"] == field
                   and e["review_status"] == "verified" and e["locator"] and e["time_precision"] in ("day", "timestamp")
                   and not any(i["entity_type"] == "field_evidence" and i["entity_id"] == e["evidence_id"] for i in issues)
                   and sources.get(e["source_id"], {}).get("evidence_level") in verified_levels
                   and on_or_before(e["known_at"], at) for e in tables["field_evidence"])

    snapshots = []
    groups = {}
    for row in tables["opportunities"]:
        groups.setdefault(canonical_id(tables, row["opportunity_id"]), []).append(row)
    for opportunity, members in sorted(groups.items()):
        member_ids = {r["opportunity_id"] for r in members}
        firsts = [q for q in tables["quotes"] if q["opportunity_id"] in member_ids and q["first_priced_quote_status"] == "confirmed"]
        reasons, metadata, features = [], {}, {}
        if len(firsts) != 1:
            reasons.append("first_quote_missing_or_ambiguous")
            quote = None
        else:
            quote = firsts[0]
            at = quote["sent_at"]
            quote_errors = any(i["entity_type"] == "quotes" and i["entity_id"] == quote["quote_id"] and i["severity"] == "error" and i["field_name"] in ("sent_at", "date_precision", "source_id", "opportunity_id", "first_priced_quote_status") for i in issues)
            if quote_errors or not at or not proven("quotes", quote, "sent_at", at) or not proven("quotes", quote, "first_priced_quote_status", at):
                reasons.append("first_quote_time_unverified")
            if not reasons:
                for field in QUOTE_FEATURES:
                    features[field] = quote[field] if proven("quotes", quote, field, at) else None
                alternatives = []
                for option in sorted((o for o in tables["quote_options"] if o["quote_id"] == quote["quote_id"]), key=lambda o: o["option_id"]):
                    # Membership itself needs evidence; later alternatives cannot leak in.
                    if not proven("quote_options", option, "quote_id", at):
                        continue
                    values = {f: option[f] if proven("quote_options", option, f, at) else None for f in OPTION_FEATURES}
                    p, price = values["passengers"], values["net_price"]
                    values["net_price_per_person"] = None
                    if values["currency"] and price is not None:
                        if values["price_scope"] == "per_person":
                            values["net_price_per_person"] = price
                        elif values["price_scope"] == "group" and p and int(p) > 0:
                            values["net_price_per_person"] = format(Decimal(price) / Decimal(p), "f")
                    # Points value must have exactly the option's documented currency/scope.
                    values["points_coverage_ratio"] = None
                    if values["price_scope"] in ("group", "per_person") and values["currency"] and price and Decimal(price) > 0 and values["points_value_quoted"] is not None:
                        values["points_coverage_ratio"] = format(Decimal(values["points_value_quoted"]) / Decimal(price), "f")
                    alternatives.append(values)
                features["options"] = alternatives
                # No assumption that recovered options exhaust the original proposal.
                metadata["verified_options_recovered"] = len(alternatives)
                if not alternatives:
                    metadata["option_coverage"] = "not_verified"
        def affects_identity(case):
            if case["case_type"] == "duplicate_check" and case["entity_type"] == "opportunities" and case["status"] != "rejected":
                other = json.loads(case["proposed_json"]).get("possible_duplicate_of")
                if canonical_id(tables, case["entity_id"]) == canonical_id(tables, other):
                    return False
                return case["entity_id"] in member_ids or other in member_ids
            if case["status"] != "pending":
                return False
            if case["case_type"] == "group_opportunities":
                return case["entity_id"] in member_ids or case["proposed_opportunity_id"] in member_ids
            if case["case_type"] == "record_correction" and case["entity_type"] == "quotes":
                old, new = json.loads(case["current_json"]), json.loads(case["proposed_json"])
                if old["opportunity_id"] in member_ids or new["opportunity_id"] in member_ids:
                    return any(old.get(k) != new.get(k) for k in ("opportunity_id", "sent_at", "first_priced_quote_status", "date_precision"))
            return False
        if any(affects_identity(c) for c in tables["review_queue"]):
            reasons.append("identity_review_pending")
        snapshots.append({"opportunity_id": opportunity, "quote_id": quote["quote_id"] if quote else None,
            "score_at": quote["sent_at"] if quote else None, "date_precision": quote["date_precision"] if quote else None,
            "snapshot_status": "pending" if reasons else "verified", "temporal_reasons": reasons,
            "training_eligible": 0, "ineligibility_reason": "modeling_policy_and_representativeness_pending" + (";explicit_exclusion" if any(r["exclude_from_training"] == "1" for r in members) else ""),
            "features": features, "audit": metadata})
    return snapshots


def save_snapshots(store, reason, source=None):
    if not reason.strip():
        raise ValueError("Indicar motivo de generación/corrección")
    with store.locked():
        tables = store.read()
        if source and source not in {s["source_id"] for s in tables["sources"]}:
            raise ValueError("Fuente inexistente")
        snapshots = build_snapshots(tables)
        version = stable_id("SNAP", RULES_VERSION, snapshots)
        folder = store.root / "snapshots"
        folder.mkdir(exist_ok=True)
        path = folder / (version + ".json")
        if not path.exists():
            if any(folder.glob("*.json")) and not source:
                raise ValueError("Una nueva versión documental requiere --source y motivo; se conserva la anterior")
            pointer = store.root / "CURRENT"
            revision = pointer.read_text(encoding="utf-8") if pointer.exists() else "empty"
            path.write_text(json_text({"snapshot_version": version, "schema_version": VERSION, "rules_version": RULES_VERSION,
                "data_revision": revision, "generated_at": now(), "reason": reason,
                "source_id": source, "snapshots": snapshots}), encoding="utf-8")
        return path
