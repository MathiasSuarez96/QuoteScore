"""Agrupaciones explícitas y reversibles; nunca se infiere identidad por nombre."""
from .store import json_text, stable_id


def canonical_id(tables, opportunity_id):
    links = {r["alias_opportunity_id"]: r["canonical_opportunity_id"] for r in tables["opportunity_links"]}
    seen = set()
    while opportunity_id in links:
        if opportunity_id in seen:
            raise ValueError("Ciclo en agrupaciones")
        seen.add(opportunity_id)
        opportunity_id = links[opportunity_id]
    return opportunity_id


def propose_group(store, alias, canonical, source, reason):
    if not reason.strip():
        raise ValueError("Se requiere motivo sanitizado")
    with store.locked():
        tables = store.read()
        ids = {r["opportunity_id"] for r in tables["opportunities"]}
        if alias not in ids or canonical not in ids or alias == canonical:
            raise ValueError("IDs de oportunidades inválidos")
        if source not in {r["source_id"] for r in tables["sources"]}:
            raise ValueError("Fuente inexistente")
        if canonical_id(tables, alias) == canonical_id(tables, canonical):
            raise ValueError("Las oportunidades ya están agrupadas")
        case_id = stable_id("GROUP", alias, canonical, source, reason)
        if not any(r["case_id"] == case_id for r in tables["review_queue"]):
            tables["review_queue"].append({"case_id": case_id, "case_type": "group_opportunities",
                "entity_type": "opportunities", "entity_id": alias, "proposed_opportunity_id": canonical,
                "evidence_source_id": source, "reason": reason, "current_json": json_text(None),
                "proposed_json": json_text({"alias_opportunity_id": alias, "canonical_opportunity_id": canonical}),
                "status": "pending", "last_decision_id": None})
            store.commit(tables)
        return case_id
