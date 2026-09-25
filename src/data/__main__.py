"""Ejecutar: python -m src.data --help."""
import argparse
import json
import sys
from datetime import date

from .load_data import load_bundle
from .quality_report import save_report
from .reconcile_opportunities import propose_group
from .review_cases import decide, update_outcome, propose_issue_resolution
from .snapshots import save_snapshots
from .store import Store
from .validate_data import add_issues, validate


def main(argv=None):
    # Pipes on Windows otherwise use the system code page, corrupting JSON with accents.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="QuoteScore — Entrega 1, datos locales auditables")
    parser.add_argument("--store", required=True, help="Directorio local de salida; privado fuera del proyecto")
    parser.add_argument("--mode", choices=("artificial", "private"), default="artificial")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Inicializar tablas vacías")
    load = sub.add_parser("load", help="Cargar CSV sanitizados con IDs estables")
    load.add_argument("directory")
    load.add_argument("--cutoff", required=True)
    sub.add_parser("validate", help="Registrar incidencias; devuelve 1 con errores actuales")
    sub.add_parser("issues", help="Listar incidencias históricas y sus estados sin editar CSV")
    review = sub.add_parser("review", help="Ver un caso pendiente sin decidir automáticamente")
    review.add_argument("--case")
    decision = sub.add_parser("decide", help="Confirmar, rechazar o dejar pendiente; permite revertir")
    decision.add_argument("case_id")
    decision.add_argument("action", choices=("confirm", "reject", "pending"))
    decision.add_argument("--source", required=True)
    decision.add_argument("--reason", required=True)
    decision.add_argument("--supersedes")
    group = sub.add_parser("propose-group", help="Proponer que dos registros representan el mismo viaje")
    group.add_argument("alias")
    group.add_argument("canonical")
    group.add_argument("--source", required=True)
    group.add_argument("--reason", required=True)
    outcome = sub.add_parser("outcome", help="Registrar desenlace con historial; nunca modifica cotización")
    outcome.add_argument("opportunity_id")
    outcome.add_argument("status", choices=("won", "lost", "open"))
    outcome.add_argument("--at", required=True)
    outcome.add_argument("--source", required=True)
    outcome.add_argument("--reason", required=True)
    outcome.add_argument("--event-id", required=True)
    outcome.add_argument("--supersedes")
    outcome.add_argument("--kind", choices=("transition", "correction"), default="transition")
    issue = sub.add_parser("issue", help="Proponer aceptar/resolver/reabrir una incidencia")
    issue.add_argument("issue_id")
    issue.add_argument("status", choices=("accepted", "resolved", "pending"))
    issue.add_argument("--source", required=True)
    issue.add_argument("--reason", required=True)
    for name in ("sold-scope", "sale-extent", "final-destination", "final-sale-amount", "final-sale-currency"):
        outcome.add_argument("--" + name)
    snapshot = sub.add_parser("snapshot", help="Guardar versión de reconstrucción inicial; no entrenar")
    snapshot.add_argument("--reason", required=True)
    snapshot.add_argument("--source")
    report = sub.add_parser("report", help="Generar informe versionado con corte explícito")
    report.add_argument("--cutoff", required=True)
    report.add_argument("--declared-sales", type=int)
    report.add_argument("--sampling", default="No definido; inventario parcial")
    report.add_argument("--revision", help="Reproducir una revisión archivada sin cambiar CURRENT")
    args = parser.parse_args(argv)
    try:
        if hasattr(args, "cutoff"):
            date.fromisoformat(args.cutoff)
        if getattr(args, "declared_sales", None) is not None and args.declared_sales < 0:
            raise ValueError("Ventas declaradas debe ser no negativo")
        store = Store(args.store, args.mode)
        command = args.command
        if command == "init":
            with store.locked():
                tables = store.read()
                if not (store.root / "CURRENT").exists():
                    store.commit(tables)
            result = "Almacén listo"
        elif command == "load":
            result = load_bundle(store, args.directory, args.cutoff)
        elif command == "validate":
            with store.locked():
                tables = store.read()
                issues = validate(tables)
                before = len(tables["quality_issues"])
                add_issues(tables, issues)
                if len(tables["quality_issues"]) != before:
                    store.commit(tables)
            print(json.dumps(issues, ensure_ascii=False, indent=2))
            return int(any(i["severity"] == "error" for i in issues))
        elif command == "review":
            tables = store.read()
            case = next((c for c in tables["review_queue"] if (c["case_id"] == args.case if args.case else c["status"] == "pending")), None)
            if args.case and case is None:
                raise ValueError("Caso inexistente")
            result = case or "No hay casos pendientes"
        elif command == "issues":
            result = store.read()["quality_issues"]
        elif command == "decide":
            result = decide(store, args.case_id, args.action, args.source, args.reason, args.supersedes)
        elif command == "propose-group":
            result = propose_group(store, args.alias, args.canonical, args.source, args.reason)
        elif command == "outcome":
            details = {k: getattr(args, k) for k in ("sold_scope", "sale_extent", "final_destination", "final_sale_amount", "final_sale_currency") if getattr(args, k) is not None}
            result = update_outcome(store, args.opportunity_id, args.status, args.at, args.source, args.reason, args.event_id, args.supersedes, event_kind=args.kind, **details)
        elif command == "issue":
            result = propose_issue_resolution(store, args.issue_id, args.status, args.source, args.reason)
        elif command == "snapshot":
            result = str(save_snapshots(store, args.reason, args.source))
        else:
            result = str(save_report(store, args.cutoff, args.declared_sales, args.sampling, args.revision))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        # OS exceptions may contain personal paths: keep filesystem errors generic.
        message = "Error de acceso a archivos; revisar rutas y permisos" if isinstance(exc, OSError) else str(exc)
        print("Error: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
