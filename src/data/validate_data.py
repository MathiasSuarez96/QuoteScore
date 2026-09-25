"""Incidencias acumulables por campo; ningún error corrige datos por intuición."""
from decimal import Decimal
import re
from copy import deepcopy

from .normalize import normalize
from .schema import FOREIGN_KEYS, KEYS, INPUT_TABLES, fields
from .store import stable_id


def issue(table, entity_id, field, code, severity="error", source=None):
    return {"issue_id": stable_id("ISS", table, entity_id, field, code),
            "entity_type": table, "entity_id": entity_id, "field_name": field,
            "issue_code": code, "severity": severity, "resolution_status": "pending",
            "resolution_note": None, "evidence_source_id": source}


def add_issues(tables, issues):
    existing = {r["issue_id"] for r in tables["quality_issues"]}
    for item in issues:
        if item["issue_id"] not in existing:
            tables["quality_issues"].append(item)
            existing.add(item["issue_id"])


def validate(tables):
    # Validation must also handle edited/corrupt CSV without crashing in arithmetic below.
    tables = deepcopy(tables)
    findings = []
    indices = {t: {r[KEYS[t]]: r for r in tables[t]} for t in INPUT_TABLES}
    for table in INPUT_TABLES:
        seen = set()
        for row in tables[table]:
            entity = row[KEYS[table]]

            def flag(field, code, severity="error"):
                findings.append(issue(table, entity, field, code, severity, row.get("source_id")))

            if entity in seen:
                flag(KEYS[table], "duplicate_primary_key")
            seen.add(entity)
            for name, spec in fields(table).items():
                value = row.get(name)
                if value is None and spec.required:
                    flag(name, "required_value_missing")
                if value is not None:
                    try:
                        normalize(value, spec)
                    except ValueError as exc:
                        flag(name, str(exc))
                        row[name] = None
                if name.endswith("currency") and value and not re.fullmatch(r"[A-Z]{3}", value):
                    flag(name, "invalid_currency")
            for name, target in FOREIGN_KEYS.get(table, {}).items():
                if row.get(name) and row[name] not in indices[target]:
                    flag(name, "missing_foreign_key")
            if table == "opportunities":
                status, converted = row.get("status"), row.get("converted")
                if (status == "won" and converted != "1") or (status == "lost" and converted != "0") or (status == "open" and converted is not None):
                    flag("converted", "status_target_conflict")
                if converted is not None and not (row.get("outcome_source_id") and row.get("outcome_basis")):
                    flag("converted", "outcome_evidence_missing")
                if converted is not None and not row.get("outcome_at"):
                    flag("outcome_at", "outcome_date_unknown", "warning")
                if row.get("exclude_from_training") == "1" and not row.get("exclusion_reason"):
                    flag("exclusion_reason", "exclusion_reason_missing")
                if row.get("final_sale_amount") is not None:
                    if not row.get("final_sale_currency"):
                        flag("final_sale_currency", "currency_missing")
                    if Decimal(row["final_sale_amount"]) < 0:
                        flag("final_sale_amount", "negative_sale_amount")
            if table == "quotes":
                sent, precision = row.get("sent_at"), row.get("date_precision")
                if sent and ((precision == "day" and "T" in sent) or (precision == "timestamp" and "T" not in sent) or precision == "unknown"):
                    flag("date_precision", "precision_conflict")
                if row.get("first_priced_quote_status") == "confirmed" and not sent:
                    flag("sent_at", "first_quote_date_missing")
            if table in ("quote_options", "quote_components"):
                start = row.get("departure_date") or row.get("start_date")
                end = row.get("return_date") or row.get("end_date")
                if start and end and end < start:
                    flag("return_date" if table == "quote_options" else "end_date", "date_order_requires_review", "warning")
                if row.get("price_scope") == "unknown":
                    flag("price_scope", "price_scope_unknown", "warning")
                amounts = ("gross_price", "discount_amount", "net_price", "quoted_price_per_person", "points_value_quoted", "quoted_cash_balance", "amount")
                for name in amounts:
                    if row.get(name):
                        if not row.get("currency"):
                            flag(name, "currency_missing")
                        if Decimal(row[name]) < 0:
                            flag(name, "negative_quoted_amount")
                if table == "quote_options":
                    p, a, c = (row.get(k) for k in ("passengers", "adults", "children"))
                    if p == "0":
                        flag("passengers", "nonpositive_passengers")
                    if all(v is not None for v in (p, a, c)) and int(p) != int(a) + int(c):
                        flag("passengers", "passenger_count_inconsistent")
                    if all(row.get(k) is not None for k in ("gross_price", "discount_amount", "net_price")):
                        if Decimal(row["gross_price"]) - Decimal(row["discount_amount"]) != Decimal(row["net_price"]):
                            flag("net_price", "price_arithmetic_requires_review", "warning")
            if table == "transactions":
                amount = row.get("amount")
                if amount is not None:
                    if not row.get("currency"):
                        flag("currency", "currency_missing")
                    if row["transaction_type"] in ("sale", "add_on") and Decimal(amount) < 0:
                        flag("amount", "transaction_sign_conflict")
                    if row["transaction_type"] == "refund" and Decimal(amount) > 0:
                        flag("amount", "transaction_sign_conflict")
                    if row["transaction_type"] == "cancellation" and Decimal(amount) != 0:
                        flag("amount", "cancellation_is_nonfinancial_event")
                if row.get("amount_usd") is not None and row.get("currency") != "USD":
                    if not all(row.get(k) for k in ("exchange_rate", "exchange_rate_date", "amount")):
                        flag("amount_usd", "exchange_evidence_missing")
                    elif abs(Decimal(row["amount"]) * Decimal(row["exchange_rate"]) - Decimal(row["amount_usd"])) > Decimal("0.01"):
                        flag("amount_usd", "exchange_arithmetic_conflict")
                if row.get("related_transaction_id") == entity:
                    flag("related_transaction_id", "self_reference")
                if row.get("exchange_rate") is not None and Decimal(row["exchange_rate"]) <= 0:
                    flag("exchange_rate", "nonpositive_exchange_rate")
                if row.get("currency") == "USD" and row.get("amount") is not None and row.get("amount_usd") is not None and Decimal(row["amount"]) != Decimal(row["amount_usd"]):
                    flag("amount_usd", "exchange_arithmetic_conflict")
            if table == "field_evidence":
                target = row.get("entity_type")
                if target not in INPUT_TABLES or row.get("entity_id") not in indices.get(target, {}):
                    flag("entity_id", "missing_evidence_entity")
                elif row.get("field_name") not in fields(target):
                    flag("field_name", "unknown_evidence_field")
                if row.get("known_at") and ((row.get("time_precision") == "day" and "T" in row["known_at"]) or (row.get("time_precision") == "timestamp" and "T" not in row["known_at"])):
                    flag("time_precision", "precision_conflict")
    firsts = {}
    for q in tables["quotes"]:
        if q.get("first_priced_quote_status") == "confirmed":
            firsts.setdefault(q["opportunity_id"], []).append(q)
    for opp, quotes in firsts.items():
        if len(quotes) > 1:
            findings.append(issue("opportunities", opp, "score_at", "multiple_first_quotes"))
    return findings
