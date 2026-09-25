"""Informe de calidad de la revisión actual, con corte y procedencia explícitos."""
from collections import Counter
from datetime import date
from pathlib import Path

from .reconcile_opportunities import canonical_id
from .schema import INPUT_TABLES, KEYS, VERSION, RULES_VERSION
from .outcomes import outcome_at_cutoff, view_at_cutoff
from .snapshots import build_snapshots
from .store import json_text, now, stable_id
from .validate_data import validate


def render_report(tables, cutoff, mode, revision, declared_sales=None, sampling="No definido; inventario parcial"):
    date.fromisoformat(cutoff)
    complete_tables = tables
    current_issues = validate(complete_tables)
    tables = view_at_cutoff(tables, cutoff)
    snapshots = build_snapshots(tables)
    groups = {}
    for r in tables["opportunities"]:
        groups.setdefault(canonical_id(tables, r["opportunity_id"]), []).append(r)
    counts = Counter()
    group_result = {}
    for key, members in groups.items():
        label = outcome_at_cutoff(tables, {r["opportunity_id"] for r in members}, cutoff)
        counts[label] += 1
        group_result[key] = label
    total = len(groups)
    lines = ["# Reporte de calidad — QuoteScore", "", f"Modo: **{mode}**. " + ("Demostración ficticia, sin interpretación comercial." if mode == "artificial" else "Uso privado; no publicar."),
        f"Generado: {now()}. Fecha de corte: {cutoff}.", f"Revisión: {revision}. Esquema: {VERSION}; reglas: {RULES_VERSION}.",
        f"Muestreo: {sampling}.", "El corte excluye oportunidades, propuestas y transacciones con fecha posterior; fechas desconocidas se conservan como cobertura incierta. Las correcciones documentales se aplican según la revisión seleccionada. La auditoría de errores y cargas describe la revisión completa.", "",
        "## Inventario y denominadores", "", "Sin datos." if not total else f"Oportunidades según conciliación actual: {total}; registros originales de oportunidades: {len(tables['opportunities'])}. La unicidad definitiva depende de resolver las sospechas de duplicado."]
    for label in ("ganada", "perdida", "abierta/dudosa", "dudosa", "desenlace sin fecha"):
        lines.append(f"- {label}: {counts[label]} / {total} oportunidades.")
    for table in INPUT_TABLES:
        lines.append(f"- {table}: {len(tables[table])} registros.")
    lines.append(f"- Oportunidades sin fecha de creación (inclusión temporal incierta): {sum(r['created_at'] is None for r in tables['opportunities'])}.")
    lines.append(f"- Registros de oportunidades recibidos en la revisión completa: {len(complete_tables['opportunities'])}.")
    sales = sum(r["transaction_type"] == "sale" for r in tables["transactions"])
    lines += [f"- Registros de tipo venta recibidos: {sales}; ventas declaradas: {declared_sales if declared_sales is not None else 'no configurado'}. No equivalen necesariamente a oportunidades.",
              f"- Fuentes por nivel de evidencia: {dict(Counter(r['evidence_level'] for r in tables['sources'])) or 'sin datos'}.",
              f"- Exclusiones explícitas: {sum(any(r['exclude_from_training'] == '1' for r in members) for members in groups.values())} / {total}.",
              f"- Snapshots verificados (tiempo e identidad): {sum(s['snapshot_status'] == 'verified' for s in snapshots)} / {total}.",
              "Elegibilidad de entrenamiento: pendiente de política de confirmación, cancelaciones, horizonte y representatividad. No se genera training_quotescore_v1.csv en esta entrega.",
              "", "## Completitud de campos", "", "Presentes, desconocidos y no aplicables documentados; denominador: filas de la tabla. No mide veracidad ni elegibilidad temporal.", "", "| Tabla | Campo | Presentes | Desconocidos | No aplicables | Denominador |", "|---|---|---:|---:|---:|---:|"]
    coverage = {"quotes": ("sent_at", "lead_source_at_quote"), "quote_options": ("departure_date", "return_date", "passengers", "product_scope", "currency", "price_scope", "net_price", "points_available", "points_proposed")}
    for table, columns in coverage.items():
        for field in columns:
            present = sum(r[field] is not None and r[field] != "unknown" for r in tables[table])
            na_ids = {e["entity_id"] for e in tables["field_evidence"] if e["entity_type"] == table and e["field_name"] == field and e["review_status"] == "not_applicable" and e["source_id"] in {s["source_id"] for s in tables["sources"]}}
            not_applicable = sum(r[KEYS[table]] in na_ids and r[field] is None for r in tables[table])
            missing = len(tables[table]) - present - not_applicable
            lines.append(f"| {table} | {field} | {present} | {missing} | {not_applicable} | {len(tables[table])} |")
    sources = {s["source_id"]: s for s in tables["sources"]}
    quotes = {q["quote_id"]: q for q in tables["quotes"]}
    origin_coverage = Counter()
    for members in groups.values():
        member_ids = {r["opportunity_id"] for r in members}
        source_ids = {q["source_id"] for q in tables["quotes"] if q["opportunity_id"] in member_ids}
        source_ids.update(r["outcome_source_id"] for r in members if r["outcome_source_id"])
        source_ids.update(t["source_id"] for t in tables["transactions"] if t["opportunity_id"] in member_ids)
        levels = {sources[s]["evidence_level"] for s in source_ids if s in sources}
        category = "original verificado disponible" if "original_verified" in levels else "solo resúmenes" if levels == {"supplied_summary"} else "artificial" if levels == {"artificial"} else "sin fuentes" if not levels else "confirmaciones/mezcla sin original verificado"
        origin_coverage[category] += 1
    lines += ["", "Procedencia por oportunidad conciliada (denominador: oportunidades):"]
    for category, count in sorted(origin_coverage.items()):
        lines.append(f"- {category}: {count} / {total}.")
    recovered = sum(any(q["opportunity_id"] in {r["opportunity_id"] for r in members} and q["first_priced_quote_status"] == "confirmed" for q in tables["quotes"]) for members in groups.values())
    lines.append(f"Primera cotización declarada confirmada: {recovered} / {total}; la verificación temporal se informa por separado.")
    strata = {}
    for option in tables["quote_options"]:
        q = quotes.get(option["quote_id"], {})
        opp = canonical_id(tables, q.get("opportunity_id"))
        key = (group_result.get(opp, "sin vínculo"), (q.get("sent_at") or "desconocido")[:7], sources.get(option["source_id"], {}).get("source_type", "desconocida"))
        strata.setdefault(key, []).append(option)
    lines += ["", "## Cobertura por resultado, período y tipo de fuente", "", "Denominador: opciones en cada grupo; no oportunidades ni tasa comercial.", "", "| Resultado / mes / fuente | Opciones | Precio conocido | Pasajeros | Puntos disponibles |", "|---|---:|---:|---:|---:|"]
    for key, rows in sorted(strata.items()):
        lines.append(f"| {' / '.join(key)} | {len(rows)} | {sum(r['net_price'] is not None for r in rows)} | {sum(r['passengers'] is not None for r in rows)} | {sum(r['points_available'] is not None for r in rows)} |")
    flight = [r for r in tables["quote_components"] if r["component_type"] == "flight"]
    lines += ["", f"Proveedor aéreo: {sum(r['provider'] is not None for r in flight)} / {len(flight)} componentes de vuelo. Otros tipos: no aplicable, fuera del denominador.",
        "Un vacío es desconocido salvo campo estructuralmente no aplicable; field_evidence.review_status=not_applicable documenta otros casos.",
        "", "## Incidencias y pendientes", "", f"Errores bloqueantes actuales: {sum(i['severity'] == 'error' for i in current_issues)}.",
        f"Advertencias actuales: {sum(i['severity'] == 'warning' for i in current_issues)}. No se exige cero NULL.",
        f"Incidencias históricas conservadas: {len(tables['quality_issues'])}; el historial puede incluir problemas ya corregidos.",
        f"Estado de incidencias históricas: {dict(Counter(i['resolution_status'] for i in tables['quality_issues'])) or 'sin datos'}. Un valor normalizado a NULL no demuestra que su incidencia esté resuelta.",
        f"Casos pendientes: {sum(c['status'] == 'pending' for c in tables['review_queue'])}. Decisiones registradas: {len(tables['reconciliation_log'])}.",
        f"Duplicados sospechosos históricos: {sum(i['issue_code'] == 'suspected_duplicate' for i in tables['quality_issues'])}."]
    for code, count in sorted(Counter(i["issue_code"] for i in current_issues).items()):
        lines.append(f"- {code}: {count}.")
    dates = [q["sent_at"][:10] for q in tables["quotes"] if q["sent_at"]]
    lines += ["", "## Límites", "", f"Período de cotizaciones recuperado: {min(dates) + ' a ' + max(dates) if dates else 'sin datos'}.",
        "No se infiere pérdida por silencio ni antigüedad. La fecha de corte no acredita seguimiento suficiente. Fuentes distintas según desenlace pueden introducir selección documental. No hay probabilidad validada ni efecto causal demostrado del seguimiento.",
        "No se suman ventas con desgloses, alternativas, monedas o alcances incompatibles. No se calcula conversión de toda la actividad a partir de una muestra seleccionada.",
        "", "## Trazabilidad", ""]
    for run in tables["load_runs"]:
        lines.append(f"- {run['run_id']}; entrada {run['input_fingerprint']}; corte de carga {run['cutoff']}; entradas {run['input_counts']}; salidas {run['output_counts']}.")
    return "\n".join(lines) + "\n"


def save_report(store, cutoff, declared_sales=None, sampling="No definido; inventario parcial", revision=None):
    with store.locked():
        tables = store.read(revision)
        pointer = store.root / "CURRENT"
        revision = revision or (pointer.read_text(encoding="utf-8") if pointer.exists() else "empty")
        report = render_report(tables, cutoff, store.mode, revision, declared_sales, sampling)
        folder = store.root / "reports"
        folder.mkdir(exist_ok=True)
        path = folder / (stable_id("REPORT", revision, cutoff, declared_sales, sampling, now()) + ".md")
        path.write_text(report, encoding="utf-8")
        return path
