# Reporte de calidad — QuoteScore

Modo: **artificial**. Demostración ficticia, sin interpretación comercial.
Generado: 2026-09-19T01:52:43.925315+00:00. Fecha de corte: 2025-02-10.
Revisión: f8aa5b9362214a48818b330d39e04e26. Esquema: 1.0.0; reglas: 1.1.0.
Muestreo: Muestra artificial diseñada para probar reglas, sin representatividad comercial.
El corte excluye oportunidades, propuestas y transacciones con fecha posterior; fechas desconocidas se conservan como cobertura incierta. Las correcciones documentales se aplican según la revisión seleccionada. La auditoría de errores y cargas describe la revisión completa.

## Inventario y denominadores

Oportunidades según conciliación actual: 4; registros originales de oportunidades: 4. La unicidad definitiva depende de resolver las sospechas de duplicado.
- ganada: 1 / 4 oportunidades.
- perdida: 1 / 4 oportunidades.
- abierta/dudosa: 2 / 4 oportunidades.
- dudosa: 0 / 4 oportunidades.
- desenlace sin fecha: 0 / 4 oportunidades.
- sources: 1 registros.
- opportunities: 4 registros.
- quotes: 3 registros.
- quote_options: 3 registros.
- quote_components: 1 registros.
- transactions: 1 registros.
- field_evidence: 95 registros.
- Oportunidades sin fecha de creación (inclusión temporal incierta): 0.
- Registros de oportunidades recibidos en la revisión completa: 4.
- Registros de tipo venta recibidos: 1; ventas declaradas: no configurado. No equivalen necesariamente a oportunidades.
- Fuentes por nivel de evidencia: {'artificial': 1}.
- Exclusiones explícitas: 0 / 4.
- Snapshots verificados (tiempo e identidad): 1 / 4.
Elegibilidad de entrenamiento: pendiente de política de confirmación, cancelaciones, horizonte y representatividad. No se genera training_quotescore_v1.csv en esta entrega.

## Completitud de campos

Presentes, desconocidos y no aplicables documentados; denominador: filas de la tabla. No mide veracidad ni elegibilidad temporal.

| Tabla | Campo | Presentes | Desconocidos | No aplicables | Denominador |
|---|---|---:|---:|---:|---:|
| quotes | sent_at | 3 | 0 | 0 | 3 |
| quotes | lead_source_at_quote | 3 | 0 | 0 | 3 |
| quote_options | departure_date | 3 | 0 | 0 | 3 |
| quote_options | return_date | 3 | 0 | 0 | 3 |
| quote_options | passengers | 2 | 1 | 0 | 3 |
| quote_options | product_scope | 3 | 0 | 0 | 3 |
| quote_options | currency | 3 | 0 | 0 | 3 |
| quote_options | price_scope | 2 | 1 | 0 | 3 |
| quote_options | net_price | 2 | 1 | 0 | 3 |
| quote_options | points_available | 3 | 0 | 0 | 3 |
| quote_options | points_proposed | 3 | 0 | 0 | 3 |

Procedencia por oportunidad conciliada (denominador: oportunidades):
- artificial: 3 / 4.
- sin fuentes: 1 / 4.
Primera cotización declarada confirmada: 3 / 4; la verificación temporal se informa por separado.

## Cobertura por resultado, período y tipo de fuente

Denominador: opciones en cada grupo; no oportunidades ni tasa comercial.

| Resultado / mes / fuente | Opciones | Precio conocido | Pasajeros | Puntos disponibles |
|---|---:|---:|---:|---:|
| abierta/dudosa / 2025-02 / artificial | 1 | 0 | 0 | 1 |
| ganada / 2025-02 / artificial | 1 | 1 | 1 | 1 |
| perdida / 2025-02 / artificial | 1 | 1 | 1 | 1 |

Proveedor aéreo: 0 / 0 componentes de vuelo. Otros tipos: no aplicable, fuera del denominador.
Un vacío es desconocido salvo campo estructuralmente no aplicable; field_evidence.review_status=not_applicable documenta otros casos.

## Incidencias y pendientes

Errores bloqueantes actuales: 0.
Advertencias actuales: 1. No se exige cero NULL.
Incidencias históricas conservadas: 4; el historial puede incluir problemas ya corregidos.
Estado de incidencias históricas: {'pending': 4}. Un valor normalizado a NULL no demuestra que su incidencia esté resuelta.
Casos pendientes: 2. Decisiones registradas: 1.
Duplicados sospechosos históricos: 2.
- price_scope_unknown: 1.

## Límites

Período de cotizaciones recuperado: 2025-02-03 a 2025-02-03.
No se infiere pérdida por silencio ni antigüedad. La fecha de corte no acredita seguimiento suficiente. Fuentes distintas según desenlace pueden introducir selección documental. No hay probabilidad validada ni efecto causal demostrado del seguimiento.
No se suman ventas con desgloses, alternativas, monedas o alcances incompatibles. No se calcula conversión de toda la actividad a partir de una muestra seleccionada.

## Trazabilidad

- RUN_02e3cda178d84a0bf47d22b5; entrada BATCH_ee99d984beba5961d9ccbb33; corte de carga 2025-02-10; entradas {"field_evidence":95,"opportunities":4,"quote_components":1,"quote_options":3,"quotes":3,"sources":1,"transactions":1}; salidas {"field_evidence":95,"opportunities":4,"quote_components":1,"quote_options":3,"quotes":3,"sources":1,"transactions":1}.
