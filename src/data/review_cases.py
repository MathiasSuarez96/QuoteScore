"""Decisiones anexables con control de versiones y reversión explícita."""
import json
from uuid import uuid4

from .reconcile_opportunities import canonical_id
from .schema import KEYS
from .store import json_text, now, stable_id
from .validate_data import add_issues, validate


def require_source(tables, source, reason):
    if source not in {r["source_id"] for r in tables["sources"]}:
        raise ValueError("Fuente de evidencia inexistente")
    if not reason or not reason.strip():
        raise ValueError("Se requiere un motivo sanitizado")


def record_outcome(tables, before, after, source, reason, supersedes=None):
    tables["outcome_history"].append({"outcome_event_id": "OUT_" + uuid4().hex,
        "opportunity_id": after["opportunity_id"], "previous_status": before.get("status"),
        "new_status": after.get("status"), "converted": after.get("converted"),
        "outcome_at": after.get("outcome_at"), "recorded_at": now(), "source_id": source,
        "reason": reason, "supersedes_event_id": supersedes, "details_json": json_text({"event_kind": "correction", "record": after})})


def decide(store, case_id, action, source, reason, supersedes=None):
    if action not in ("confirm", "reject", "pending"):
        raise ValueError("Decisión inválida")
    with store.locked():
        tables = store.read()
        require_source(tables, source, reason)
        case = next((r for r in tables["review_queue"] if r["case_id"] == case_id), None)
        if case is None:
            raise ValueError("Caso inexistente")
        previous = case.get("last_decision_id")
        if previous and supersedes != previous:
            raise ValueError("Para corregir o reabrir, referenciar la última decisión con --supersedes")
        if supersedes and supersedes != previous:
            raise ValueError("La decisión referenciada no es la vigente del caso")
        decision_id = "DEC_" + uuid4().hex
        before, after = json.loads(case["current_json"]), json.loads(case["proposed_json"])
        old_action = case["status"]
        if case["case_type"] == "record_correction":
            table = case["entity_type"]
            row = next((r for r in tables[table] if r[KEYS[table]] == case["entity_id"]), None)
            expected = after if old_action == "confirmed" else before
            if row != expected:
                raise ValueError("El registro cambió; crear una nueva propuesta antes de decidir")
            replacement = after if action == "confirm" else before
            if row != replacement:
                existing_errors = {i["issue_id"] for i in validate(tables) if i["severity"] == "error"}
                old_row = dict(row)
                row.clear()
                row.update(replacement)
                # Don't accept structural errors; missing noncritical values remain reviewable.
                blockers = [i for i in validate(tables) if i["severity"] == "error" and i["issue_id"] not in existing_errors]
                if blockers and action == "confirm":
                    raise ValueError("La propuesta tiene errores bloqueantes; corregir la fuente")
                # Evidence of a previous value does not attest its replacement, even on reversal.
                changed_fields = {k for k in row if row[k] != old_row.get(k)}
                for evidence in tables["field_evidence"]:
                    if evidence["entity_type"] == table and evidence["entity_id"] == case["entity_id"] and evidence["field_name"] in changed_fields:
                        evidence["review_status"] = "pending"
                if table == "opportunities" and any(old_row.get(k) != row.get(k) for k in ("status", "converted", "outcome_at", "outcome_source_id", "outcome_basis")):
                    prior = next((r["outcome_event_id"] for r in reversed(tables["outcome_history"]) if r["opportunity_id"] == row["opportunity_id"]), None)
                    record_outcome(tables, old_row, row, source, reason, prior)
        elif case["case_type"] == "group_opportunities":
            alias, canonical = case["entity_id"], case["proposed_opportunity_id"]
            link = next((r for r in tables["opportunity_links"] if r["alias_opportunity_id"] == alias), None)
            if old_action == "confirmed":
                if not link or link["decision_id"] != previous:
                    raise ValueError("La agrupación cambió; revisar dependencias")
                tables["opportunity_links"].remove(link)
            elif link:
                raise ValueError("La oportunidad ya tiene otra agrupación")
            if action == "confirm":
                if canonical_id(tables, canonical) == alias:
                    raise ValueError("La agrupación crearía un ciclo")
                # A merge cannot choose between contradictory known outcomes.
                members = [r for r in tables["opportunities"] if canonical_id(tables, r["opportunity_id"]) in (alias, canonical_id(tables, canonical))]
                if len({r["converted"] for r in members if r["converted"] is not None}) > 1:
                    raise ValueError("Desenlaces contradictorios: resolver antes de agrupar")
                tables["opportunity_links"].append({"link_id": stable_id("LINK", alias), "alias_opportunity_id": alias,
                    "canonical_opportunity_id": canonical, "decision_id": decision_id})
        elif case["case_type"] == "duplicate_check":
            # Acknowledges the finding only. Grouping requires a separate explicit proposal.
            pass
        elif case["case_type"] == "quality_issue":
            row = next((r for r in tables["quality_issues"] if r["issue_id"] == case["entity_id"]), None)
            expected = after if old_action == "confirmed" else before
            if row != expected:
                raise ValueError("La incidencia cambió; revisar su decisión vigente")
            row.update(after if action == "confirm" else before)
        else:
            raise ValueError("Tipo de caso no soportado")
        case["status"] = {"confirm": "confirmed", "reject": "rejected", "pending": "pending"}[action]
        case["last_decision_id"] = decision_id
        tables["reconciliation_log"].append({"decision_id": decision_id, "source_record_id": case["entity_id"],
            "opportunity_id": case["proposed_opportunity_id"] or (case["entity_id"] if case["entity_type"] == "opportunities" else None),
            "decision_type": action, "rationale": reason, "evidence_source_id": source, "decided_at": now(),
            "case_id": case_id, "supersedes_decision_id": supersedes, "before_json": json_text(before), "after_json": json_text(after)})
        add_issues(tables, validate(tables))
        store.commit(tables)
        return decision_id


def update_outcome(store, opportunity_id, status, outcome_at, source, reason, event_id, supersedes=None, event_kind="transition", **details):
    from .normalize import normalize
    from .schema import fields
    if status not in ("open", "won", "lost"):
        raise ValueError("Estado de desenlace inválido")
    import re
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", event_id):
        raise ValueError("ID de evento inválida")
    if event_kind not in ("transition", "correction"):
        raise ValueError("Tipo de evento inválido")
    outcome_at = normalize(outcome_at, fields("opportunities")["outcome_at"])
    if not outcome_at:
        raise ValueError("Indicar fecha del evento")
    with store.locked():
        tables = store.read()
        require_source(tables, source, reason)
        row = next((r for r in tables["opportunities"] if r["opportunity_id"] == opportunity_id), None)
        if row is None:
            raise ValueError("Oportunidad inexistente")
        existing = next((r for r in tables["outcome_history"] if r["outcome_event_id"] == event_id), None)
        payload = {"status": status, "outcome_at": outcome_at, "source": source, "reason": reason, "details": details, "supersedes": supersedes, "event_kind": event_kind}
        if existing:
            old_payload = json.loads(existing["details_json"])
            old_payload.setdefault("event_kind", "transition")
            if old_payload == payload and existing["opportunity_id"] == opportunity_id:
                return event_id
            raise ValueError("ID de evento reutilizado con contenido diferente")
        prior = next((r for r in reversed(tables["outcome_history"]) if r["opportunity_id"] == opportunity_id), None)
        if prior and supersedes != prior["outcome_event_id"]:
            raise ValueError("Referenciar el último evento con --supersedes para corregir o reactivar")
        if supersedes and (not prior or supersedes != prior["outcome_event_id"]):
            raise ValueError("Evento previo inválido")
        if event_kind == "correction" and not prior:
            raise ValueError("Una corrección requiere un evento anterior")
        if event_kind == "transition" and prior and prior["outcome_at"] and outcome_at[:10] < prior["outcome_at"][:10]:
            raise ValueError("Una transición no puede preceder al evento anterior; usar corrección documental")
        previous_status = row["status"]
        row.update(status=status, converted={"open": None, "won": "1", "lost": "0"}[status],
                   outcome_at=outcome_at, outcome_source_id=source, outcome_basis=reason)
        allowed = {"sold_scope", "sale_extent", "final_destination", "final_sale_amount", "final_sale_currency"}
        if set(details) - allowed:
            raise ValueError("Campo no permitido en desenlace")
        for name, value in details.items():
            row[name] = normalize(value, fields("opportunities")[name])
        if any(i["severity"] == "error" and i["entity_type"] == "opportunities" and i["entity_id"] == opportunity_id for i in validate(tables)):
            raise ValueError("El desenlace produce errores de validación")
        tables["outcome_history"].append({"outcome_event_id": event_id, "opportunity_id": opportunity_id,
            "previous_status": previous_status, "new_status": status, "converted": row["converted"],
            "outcome_at": outcome_at, "recorded_at": now(), "source_id": source, "reason": reason,
            "supersedes_event_id": supersedes, "details_json": json_text(payload)})
        add_issues(tables, validate(tables))
        store.commit(tables)
        return event_id


def propose_issue_resolution(store, issue_id, status, source, reason):
    """Reuse the decision queue so quality annotations also have reversible history."""
    if status not in ("accepted", "resolved", "pending"):
        raise ValueError("Estado de incidencia inválido")
    with store.locked():
        tables = store.read()
        require_source(tables, source, reason)
        row = next((r for r in tables["quality_issues"] if r["issue_id"] == issue_id), None)
        if row is None:
            raise ValueError("Incidencia inexistente")
        if status == "resolved" and any(i["issue_id"] == issue_id for i in validate(tables)):
            raise ValueError("La regla todavía falla; corregir los datos o aceptar la limitación")
        proposed = dict(row, resolution_status=status, resolution_note=reason, evidence_source_id=source)
        case_id = stable_id("QUALITY", row, proposed)
        if not any(c["case_id"] == case_id for c in tables["review_queue"]):
            tables["review_queue"].append({"case_id": case_id, "case_type": "quality_issue", "entity_type": "quality_issues",
                "entity_id": issue_id, "proposed_opportunity_id": None, "evidence_source_id": source, "reason": reason,
                "current_json": json_text(row), "proposed_json": json_text(proposed), "status": "pending", "last_decision_id": None})
            store.commit(tables)
        return case_id
