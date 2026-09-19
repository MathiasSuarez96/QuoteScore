"""Prueba del flujo completo reproducible; segunda ejecución no duplica registros."""
import argparse
import json

from src.data.load_data import load_bundle
from src.data.quality_report import save_report
from src.data.reconcile_opportunities import propose_group
from src.data.review_cases import decide, update_outcome
from src.data.snapshots import save_snapshots
from src.data.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="local/demo")
    args = parser.parse_args()
    store = Store(args.store)
    first = load_bundle(store, "examples/artificial/input", "2025-02-10")
    repeated = load_bundle(store, "examples/artificial/input", "2025-02-10")
    before = save_snapshots(store, "Reconstrucción inicial artificial", "SRC_DEMO")
    update_outcome(store, "OP_DEMO_1", "won", "2025-02-06", "SRC_DEMO", "Venta parcial artificial confirmada", "EVENT_DEMO_WON", sold_scope="flight_only", sale_extent="partial", final_destination="Otro destino ficticio", final_sale_amount="500", final_sale_currency="USD")
    update_outcome(store, "OP_DEMO_3", "lost", "2025-02-04", "SRC_DEMO", "Pérdida artificial confirmada", "EVENT_DEMO_LOST")
    after = save_snapshots(store, "Comprobación posterior al desenlace", "SRC_DEMO")
    assert before == after, "El desenlace no debe modificar el snapshot"
    # Two invented records are deliberately proposed for review; no automatic merge.
    tables = store.read()
    existing = next((c for c in tables["review_queue"] if c["case_type"] == "group_opportunities" and c["entity_id"] == "OP_DEMO_4"), None)
    case_id = existing["case_id"] if existing else propose_group(store, "OP_DEMO_4", "OP_DEMO_1", "SRC_DEMO", "Hipótesis artificial: mismo viaje")
    case = next(c for c in store.read()["review_queue"] if c["case_id"] == case_id)
    if not case["last_decision_id"]:
        decide(store, case_id, "reject", "SRC_DEMO", "La evidencia artificial identifica viajes distintos")
    report = save_report(store, "2025-02-10", sampling="Muestra artificial diseñada para probar reglas, sin representatividad comercial")
    tables = store.read()
    from src.data.snapshots import build_snapshots
    print(json.dumps({"data_kind": "artificial; decisions scripted for demonstration", "first_load": first["status"],
        "repeated_load": repeated["status"], "snapshot_unchanged": before == after,
        "counts": {t: len(tables[t]) for t in ("opportunities", "quotes", "quote_options", "transactions", "quality_issues", "outcome_history")},
        "verified_snapshots": sum(s["snapshot_status"] == "verified" for s in build_snapshots(tables)),
        "report": str(report), "reviewed_case": case_id}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
