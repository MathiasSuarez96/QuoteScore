"""Regenerar artefactos públicos del contrato. Ejecutar desde la raíz."""
import json
from pathlib import Path

from src.data.schema import TABLE_COLUMNS, INPUT_TABLES, KEYS, VERSION, FOREIGN_KEYS, fields
from src.data.store import write_csv


def build(root=Path(".")):
    lines = ["# Diccionario de datos V1", "", "Generado desde `src/data/schema.py` con `python -m tools.build_contract`.",
        "", "## Convenciones", "", "CSV UTF-8, separador coma, encabezado exacto; vacío = NULL. Texto literal NULL no es un nulo. Booleanos 1/0/vacío. Importes decimales con punto, sin separadores de miles. Monedas ISO de tres letras, solo si constan en fuente. No se convierte moneda automáticamente.",
        "IDs opacos persistentes asignados antes de importar: no derivarlos de nombres ni de fecha/importe. Una misma ID conserva identidad al reordenar CSV. Una ID nueva con contenido similar solo genera sospecha.",
        "Fechas ISO YYYY-MM-DD y timestamps ISO; conservar zona conocida. Una fecha sin hora no permite ordenar hechos intradiarios. No inventar zona en itinerarios.",
        "`initial_requires_evidence`: candidato inicial condicionado a evidencia conocida a score_at. La etiqueta no habilita todos los campos como features; la lista explícita está en snapshots.py. `descriptive_or_outcome_not_feature`: descripción/resultado, fuera de X. `audit`: identificación y trazabilidad, fuera de X.",
        "Celda vacía = desconocido, salvo campos ajenos al tipo de componente (p. ej. equipaje en hotel): no aplicable. Para otras excepciones documentar field_evidence con review_status=not_applicable; no escribir cero.",
        "`sent_at`, `transaction_date`, `outcome_at` son tiempos del evento; `known_at` acredita disponibilidad comercial; `imported_at`, `recorded_at`, `generated_at` registran incorporación/generación. Ninguno sustituye a otro.",
        "", "## Alcances y fórmulas", "", "opportunities: una necesidad de viaje; quotes: propuesta enviada; quote_options: alternativa comprable; quote_components: servicio dentro de una alternativa; transactions: evento económico de la oportunidad. Los componentes no son alternativas y las transacciones no son automáticamente oportunidades.",
        "net_price = gross_price - discount_amount solo cuando la fuente acredita igual moneda/alcance. El cargador no rellena el neto automáticamente. Puntos como pago y crédito no son descuentos comerciales; quoted_cash_balance nunca sustituye net_price.",
        "net_price_per_person = net_price / passengers únicamente para precio group, pasajeros positivos confiables e igual moneda; para per_person conserva net_price. En cualquier otro caso NULL.",
        "points_coverage_ratio = points_value_quoted / net_price, net_price > 0; ambos deben documentarse en la misma moneda y alcance de la opción. Si la fuente no permite esa correspondencia, dejar points_value_quoted vacío. No equivale a puntos efectivamente usados al cierre.",
        "amount_usd = amount × exchange_rate, donde exchange_rate es USD por unidad de currency, con exchange_rate_date y evidencia. Tolerancia aritmética 0.01. Sin conversión documentada, no sumar monedas.",
        "Transactions: sale/add_on ≥ 0; refund ≤ 0; cancellation = 0 como evento no financiero; adjustment admite ambos signos. Reembolso económico va en refund. No registrar simultáneamente una venta resumen y sus partes como ventas sumables. Mantener originales privados para contrastar; related_transaction_id enlaza ajustes/reembolsos.",
        "quote_options: todos los importes excepto quoted_price_per_person comparten moneda y price_scope de la fila. Si no comparten alcance, dejar el valor ambiguo vacío y registrar incidencia. quoted_price_per_person es explícitamente por persona.",
        "No se agregan rangos de precios ni servicios en V1: sin prueba de exhaustividad no se confunde opciones recuperadas con todas las alternativas enviadas. Componentes permanecen en CSV y fuera de los snapshots V1.",
        "", "## Catálogos y evidencia", "", "source_type indica formato; evidence_level distingue resumen, original verificado, confirmación del usuario o artificial. Importar no implica verificar el original. locator es referencia opaca (página/mensaje), nunca texto sensible.",
        "Canal, origen, solicitud, recurrencia y reactivación son independientes. Vocabulario desconocido se deja vacío con incidencia; conservar el mapeo original/normalizado fuera del repositorio. No inferir origen desde el formato de archivo.",
        "needs_review puede conservar un converted confirmado. sale_extent compara alcance solicitado y vendido: cambiar destino no demuestra venta parcial. exclude_from_training conserva el histórico y requiere motivo.",
        "Las tablas auxiliares son gestionadas por la CLI; no se importan como datos comerciales. field_evidence agrega evidence_id para idempotencia. opportunity_links preserva IDs originales al agrupar. before_json/after_json guardan valores sanitizados; el historial nunca se borra.", ""]
    for table in TABLE_COLUMNS:
        spec = fields(table)
        schema = {"schema_version": VERSION, "table": table, "primary_key": KEYS[table], "foreign_keys": FOREIGN_KEYS.get(table, {}), "input_allowed": table in INPUT_TABLES,
                  "fields": {name: {"type": f.kind, "nullable": not f.required, "enum": list(f.choices), "temporal_scope": f.temporal} for name, f in spec.items()}}
        path = root / "schemas" / (table + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(root / "templates" / ("input" if table in INPUT_TABLES else "audit") / (table + ".csv"), spec, [])
        lines += [f"## {table}", "", f"Clave: `{KEYS[table]}`. " + ("Entrada admitida." if table in INPUT_TABLES else "Gestionada por CLI, no importar."), "", "| Campo | Tipo | NULL | Alcance temporal | Valores |", "|---|---|---|---|---|"]
        for name, f in spec.items():
            lines.append(f"| {name} | {f.kind} | {'no' if f.required else 'sí'} | {f.temporal} | {', '.join(f.choices) or '—'} |")
        lines.append("")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "data_dictionary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
