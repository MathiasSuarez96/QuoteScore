"""Projection of event history: corrections replace assertions, transitions keep history."""
import json
from datetime import datetime


def event_kind(event):
    payload = json.loads(event["details_json"] or "{}")
    if "event_kind" in payload:
        return payload["event_kind"]
    # Compatibility with 1.0: direct CLI payloads had status; review corrections had a row.
    return "correction" if event["supersedes_event_id"] and "opportunity_id" in payload else "transition"


def outcome_at_cutoff(tables, member_ids, cutoff):
    events = [r for r in tables["outcome_history"] if r["opportunity_id"] in member_ids]
    replaced = {r["supersedes_event_id"] for r in events if event_kind(r) == "correction"}
    active = [r for r in events if r["outcome_event_id"] not in replaced]
    sources = {r["source_id"] for r in tables["sources"]}
    if any(not r["outcome_at"] for r in active):
        return "desenlace sin fecha"
    active = [r for r in active if r["outcome_at"][:10] <= cutoff]
    if not active:
        return "abierta/dudosa"
    # Intraday order is not invented: contradictory events on the same day require review.
    latest_day = max(r["outcome_at"][:10] for r in active)
    latest = [r for r in active if r["outcome_at"][:10] == latest_day]
    if all("T" in r["outcome_at"] and datetime.fromisoformat(r["outcome_at"]).tzinfo is not None for r in active):
        last_time = max(datetime.fromisoformat(r["outcome_at"]) for r in active)
        latest = [r for r in active if datetime.fromisoformat(r["outcome_at"]) == last_time]
    if any(r["source_id"] not in sources or not r["reason"] for r in latest):
        return "dudosa"
    if any((r["new_status"] == "won" and r["converted"] != "1") or (r["new_status"] == "lost" and r["converted"] != "0") or (r["new_status"] == "open" and r["converted"] is not None) for r in latest):
        return "dudosa"
    labels = {r["converted"] for r in latest}
    if len(labels) != 1:
        return "dudosa"
    return {"1": "ganada", "0": "perdida", None: "abierta/dudosa"}.get(next(iter(labels)), "dudosa")


def view_at_cutoff(tables, cutoff):
    """Exclude dated future records; retain unknown dates explicitly in report."""
    result = {t: list(rows) for t, rows in tables.items()}
    result["opportunities"] = [r for r in tables["opportunities"] if not r["created_at"] or r["created_at"][:10] <= cutoff]
    ids = {r["opportunity_id"] for r in result["opportunities"]}
    result["opportunity_links"] = [r for r in tables["opportunity_links"] if r["alias_opportunity_id"] in ids and r["canonical_opportunity_id"] in ids]
    result["quotes"] = [r for r in tables["quotes"] if r["opportunity_id"] in ids and (not r["sent_at"] or r["sent_at"][:10] <= cutoff)]
    qids = {r["quote_id"] for r in result["quotes"]}
    result["quote_options"] = [r for r in tables["quote_options"] if r["quote_id"] in qids]
    oids = {r["option_id"] for r in result["quote_options"]}
    result["quote_components"] = [r for r in tables["quote_components"] if r["option_id"] in oids]
    result["transactions"] = [r for r in tables["transactions"] if r["opportunity_id"] in ids and (not r["transaction_date"] or r["transaction_date"][:10] <= cutoff)]
    from .schema import KEYS, INPUT_TABLES
    entity_ids = {t: {r[KEYS[t]] for r in result[t]} for t in INPUT_TABLES}
    result["field_evidence"] = [r for r in tables["field_evidence"] if r["entity_id"] in entity_ids.get(r["entity_type"], set())]
    return result
