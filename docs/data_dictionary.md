# Diccionario de datos V1

Generado desde `src/data/schema.py` con `python -m tools.build_contract`.

## Convenciones

CSV UTF-8, separador coma, encabezado exacto; vacío = NULL. Texto literal NULL no es un nulo. Booleanos 1/0/vacío. Importes decimales con punto, sin separadores de miles. Monedas ISO de tres letras, solo si constan en fuente. No se convierte moneda automáticamente.
IDs opacos persistentes asignados antes de importar: no derivarlos de nombres ni de fecha/importe. Una misma ID conserva identidad al reordenar CSV. Una ID nueva con contenido similar solo genera sospecha.
Fechas ISO YYYY-MM-DD y timestamps ISO; conservar zona conocida. Una fecha sin hora no permite ordenar hechos intradiarios. No inventar zona en itinerarios.
`initial_requires_evidence`: candidato inicial condicionado a evidencia conocida a score_at. La etiqueta no habilita todos los campos como features; la lista explícita está en snapshots.py. `descriptive_or_outcome_not_feature`: descripción/resultado, fuera de X. `audit`: identificación y trazabilidad, fuera de X.
Celda vacía = desconocido, salvo campos ajenos al tipo de componente (p. ej. equipaje en hotel): no aplicable. Para otras excepciones documentar field_evidence con review_status=not_applicable; no escribir cero.
`sent_at`, `transaction_date`, `outcome_at` son tiempos del evento; `known_at` acredita disponibilidad comercial; `imported_at`, `recorded_at`, `generated_at` registran incorporación/generación. Ninguno sustituye a otro.

## Alcances y fórmulas

opportunities: una necesidad de viaje; quotes: propuesta enviada; quote_options: alternativa comprable; quote_components: servicio dentro de una alternativa; transactions: evento económico de la oportunidad. Los componentes no son alternativas y las transacciones no son automáticamente oportunidades.
net_price = gross_price - discount_amount solo cuando la fuente acredita igual moneda/alcance. El cargador no rellena el neto automáticamente. Puntos como pago y crédito no son descuentos comerciales; quoted_cash_balance nunca sustituye net_price.
net_price_per_person = net_price / passengers únicamente para precio group, pasajeros positivos confiables e igual moneda; para per_person conserva net_price. En cualquier otro caso NULL.
points_coverage_ratio = points_value_quoted / net_price, net_price > 0; ambos deben documentarse en la misma moneda y alcance de la opción. Si la fuente no permite esa correspondencia, dejar points_value_quoted vacío. No equivale a puntos efectivamente usados al cierre.
amount_usd = amount × exchange_rate, donde exchange_rate es USD por unidad de currency, con exchange_rate_date y evidencia. Tolerancia aritmética 0.01. Sin conversión documentada, no sumar monedas.
Transactions: sale/add_on ≥ 0; refund ≤ 0; cancellation = 0 como evento no financiero; adjustment admite ambos signos. Reembolso económico va en refund. No registrar simultáneamente una venta resumen y sus partes como ventas sumables. Mantener originales privados para contrastar; related_transaction_id enlaza ajustes/reembolsos.
quote_options: todos los importes excepto quoted_price_per_person comparten moneda y price_scope de la fila. Si no comparten alcance, dejar el valor ambiguo vacío y registrar incidencia. quoted_price_per_person es explícitamente por persona.
No se agregan rangos de precios ni servicios en V1: sin prueba de exhaustividad no se confunde opciones recuperadas con todas las alternativas enviadas. Componentes permanecen en CSV y fuera de los snapshots V1.

## Catálogos y evidencia

source_type indica formato; evidence_level distingue resumen, original verificado, confirmación del usuario o artificial. Importar no implica verificar el original. locator es referencia opaca (página/mensaje), nunca texto sensible.
Canal, origen, solicitud, recurrencia y reactivación son independientes. Vocabulario desconocido se deja vacío con incidencia; conservar el mapeo original/normalizado fuera del repositorio. No inferir origen desde el formato de archivo.
needs_review puede conservar un converted confirmado. sale_extent compara alcance solicitado y vendido: cambiar destino no demuestra venta parcial. exclude_from_training conserva el histórico y requiere motivo.
Las tablas auxiliares son gestionadas por la CLI; no se importan como datos comerciales. field_evidence agrega evidence_id para idempotencia. opportunity_links preserva IDs originales al agrupar. before_json/after_json guardan valores sanitizados; el historial nunca se borra.

## sources

Clave: `source_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| source_id | text | no | audit | — |
| source_type | text | no | audit | summary, pdf, chat, sale_record, user_confirmation, artificial, other |
| sanitized_reference | text | no | audit | — |
| document_date | date | sí | audit | — |
| imported_at | time | sí | audit | — |
| evidence_level | text | no | audit | supplied_summary, original_verified, user_confirmation, artificial |

## opportunities

Clave: `opportunity_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| opportunity_id | text | no | descriptive_or_outcome_not_feature | — |
| created_at | time | sí | descriptive_or_outcome_not_feature | — |
| status | text | no | descriptive_or_outcome_not_feature | open, won, lost, needs_review |
| converted | bool | sí | descriptive_or_outcome_not_feature | — |
| outcome_at | time | sí | descriptive_or_outcome_not_feature | — |
| outcome_source_id | text | sí | descriptive_or_outcome_not_feature | — |
| outcome_basis | text | sí | descriptive_or_outcome_not_feature | — |
| initial_destination | text | sí | descriptive_or_outcome_not_feature | — |
| final_destination | text | sí | descriptive_or_outcome_not_feature | — |
| requested_scope_initial | text | sí | descriptive_or_outcome_not_feature | — |
| sold_scope | text | sí | descriptive_or_outcome_not_feature | — |
| sale_extent | text | sí | descriptive_or_outcome_not_feature | full, partial, unknown |
| final_sale_amount | decimal | sí | descriptive_or_outcome_not_feature | — |
| final_sale_currency | text | sí | descriptive_or_outcome_not_feature | — |
| exclude_from_training | bool | no | descriptive_or_outcome_not_feature | — |
| exclusion_reason | text | sí | descriptive_or_outcome_not_feature | — |
| review_status | text | no | descriptive_or_outcome_not_feature | pending, verified, not_applicable |

## quotes

Clave: `quote_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| quote_id | text | no | initial_requires_evidence | — |
| opportunity_id | text | no | initial_requires_evidence | — |
| sent_at | time | sí | initial_requires_evidence | — |
| date_precision | text | no | initial_requires_evidence | day, timestamp, unknown |
| version_number | integer | sí | initial_requires_evidence | — |
| first_priced_quote_status | text | no | initial_requires_evidence | confirmed, candidate, unknown |
| channel_at_quote | text | sí | initial_requires_evidence | web, whatsapp, branch, phone, other |
| lead_source_at_quote | text | sí | initial_requires_evidence | santander_web, referral, other |
| request_type_at_quote | text | sí | initial_requires_evidence | quote_request, purchase_error, other |
| preselected_product_at_quote | bool | sí | initial_requires_evidence | — |
| repeat_customer_at_quote | bool | sí | initial_requires_evidence | — |
| reactivated_lead_at_quote | bool | sí | initial_requires_evidence | — |
| date_flexibility_at_quote | bool | sí | initial_requires_evidence | — |
| credit_available_at_quote | bool | sí | initial_requires_evidence | — |
| financing_available_at_quote | bool | sí | initial_requires_evidence | — |
| source_id | text | no | initial_requires_evidence | — |

## quote_options

Clave: `option_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| option_id | text | no | initial_requires_evidence | — |
| quote_id | text | no | initial_requires_evidence | — |
| option_order | integer | sí | initial_requires_evidence | — |
| product_scope | text | sí | initial_requires_evidence | — |
| origin | text | sí | initial_requires_evidence | — |
| destination_summary | text | sí | initial_requires_evidence | — |
| destination_count | integer | sí | initial_requires_evidence | — |
| departure_date | date | sí | initial_requires_evidence | — |
| return_date | date | sí | initial_requires_evidence | — |
| nights | integer | sí | initial_requires_evidence | — |
| passengers | integer | sí | initial_requires_evidence | — |
| adults | integer | sí | initial_requires_evidence | — |
| children | integer | sí | initial_requires_evidence | — |
| currency | text | sí | initial_requires_evidence | — |
| price_scope | text | no | initial_requires_evidence | group, per_person, component, unknown |
| gross_price | decimal | sí | initial_requires_evidence | — |
| discount_amount | decimal | sí | initial_requires_evidence | — |
| net_price | decimal | sí | initial_requires_evidence | — |
| quoted_price_per_person | decimal | sí | initial_requires_evidence | — |
| points_available | integer | sí | initial_requires_evidence | — |
| points_proposed | integer | sí | initial_requires_evidence | — |
| points_value_quoted | decimal | sí | initial_requires_evidence | — |
| quoted_cash_balance | decimal | sí | initial_requires_evidence | — |
| source_id | text | no | initial_requires_evidence | — |

## quote_components

Clave: `component_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| component_id | text | no | initial_requires_evidence | — |
| option_id | text | no | initial_requires_evidence | — |
| component_order | integer | sí | initial_requires_evidence | — |
| component_type | text | no | initial_requires_evidence | flight, hotel, transfer, insurance, excursion, event_ticket, other |
| origin | text | sí | initial_requires_evidence | — |
| destination | text | sí | initial_requires_evidence | — |
| start_date | date | sí | initial_requires_evidence | — |
| end_date | date | sí | initial_requires_evidence | — |
| nights | integer | sí | initial_requires_evidence | — |
| provider | text | sí | initial_requires_evidence | — |
| hotel_category | text | sí | initial_requires_evidence | — |
| room_type | text | sí | initial_requires_evidence | — |
| meal_plan | text | sí | initial_requires_evidence | — |
| passengers_covered | integer | sí | initial_requires_evidence | — |
| flight_direction | text | sí | initial_requires_evidence | outbound, inbound, other |
| number_of_connections | integer | sí | initial_requires_evidence | — |
| max_connection_minutes | integer | sí | initial_requires_evidence | — |
| overnight_connection | bool | sí | initial_requires_evidence | — |
| personal_item | bool | sí | initial_requires_evidence | — |
| carry_on | bool | sí | initial_requires_evidence | — |
| checked_bag | bool | sí | initial_requires_evidence | — |
| amount | decimal | sí | initial_requires_evidence | — |
| currency | text | sí | initial_requires_evidence | — |
| price_scope | text | sí | initial_requires_evidence | group, per_person, component, unknown |
| source_id | text | no | initial_requires_evidence | — |

## transactions

Clave: `transaction_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| transaction_id | text | no | descriptive_or_outcome_not_feature | — |
| opportunity_id | text | no | descriptive_or_outcome_not_feature | — |
| transaction_date | time | sí | descriptive_or_outcome_not_feature | — |
| transaction_type | text | no | descriptive_or_outcome_not_feature | sale, add_on, refund, cancellation, adjustment |
| product_type | text | sí | descriptive_or_outcome_not_feature | — |
| amount | decimal | sí | descriptive_or_outcome_not_feature | — |
| currency | text | sí | descriptive_or_outcome_not_feature | — |
| amount_usd | decimal | sí | descriptive_or_outcome_not_feature | — |
| exchange_rate | decimal | sí | descriptive_or_outcome_not_feature | — |
| exchange_rate_date | date | sí | descriptive_or_outcome_not_feature | — |
| related_transaction_id | text | sí | descriptive_or_outcome_not_feature | — |
| source_id | text | no | descriptive_or_outcome_not_feature | — |

## field_evidence

Clave: `evidence_id`. Entrada admitida.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| evidence_id | text | no | audit | — |
| entity_type | text | no | audit | — |
| entity_id | text | no | audit | — |
| field_name | text | no | audit | — |
| source_id | text | no | audit | — |
| locator | text | sí | audit | — |
| known_at | time | sí | audit | — |
| time_precision | text | no | audit | day, timestamp, unknown |
| review_status | text | no | audit | pending, verified, not_applicable |

## quality_issues

Clave: `issue_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| issue_id | text | no | audit | — |
| entity_type | text | sí | audit | — |
| entity_id | text | sí | audit | — |
| field_name | text | sí | audit | — |
| issue_code | text | sí | audit | — |
| severity | text | sí | audit | error, warning |
| resolution_status | text | sí | audit | pending, resolved, accepted |
| resolution_note | text | sí | audit | — |
| evidence_source_id | text | sí | audit | — |

## reconciliation_log

Clave: `decision_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| decision_id | text | no | audit | — |
| source_record_id | text | sí | audit | — |
| opportunity_id | text | sí | audit | — |
| decision_type | text | sí | audit | — |
| rationale | text | sí | audit | — |
| evidence_source_id | text | sí | audit | — |
| decided_at | time | sí | audit | — |
| case_id | text | sí | audit | — |
| supersedes_decision_id | text | sí | audit | — |
| before_json | text | sí | audit | — |
| after_json | text | sí | audit | — |

## review_queue

Clave: `case_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| case_id | text | no | audit | — |
| case_type | text | sí | audit | — |
| entity_type | text | sí | audit | — |
| entity_id | text | sí | audit | — |
| proposed_opportunity_id | text | sí | audit | — |
| evidence_source_id | text | sí | audit | — |
| reason | text | sí | audit | — |
| current_json | text | sí | audit | — |
| proposed_json | text | sí | audit | — |
| status | text | sí | audit | pending, confirmed, rejected |
| last_decision_id | text | sí | audit | — |

## outcome_history

Clave: `outcome_event_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| outcome_event_id | text | no | descriptive_or_outcome_not_feature | — |
| opportunity_id | text | sí | descriptive_or_outcome_not_feature | — |
| previous_status | text | sí | descriptive_or_outcome_not_feature | — |
| new_status | text | sí | descriptive_or_outcome_not_feature | — |
| converted | bool | sí | descriptive_or_outcome_not_feature | — |
| outcome_at | time | sí | descriptive_or_outcome_not_feature | — |
| recorded_at | time | sí | descriptive_or_outcome_not_feature | — |
| source_id | text | sí | descriptive_or_outcome_not_feature | — |
| reason | text | sí | descriptive_or_outcome_not_feature | — |
| supersedes_event_id | text | sí | descriptive_or_outcome_not_feature | — |
| details_json | text | sí | descriptive_or_outcome_not_feature | — |

## load_runs

Clave: `run_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| run_id | text | no | audit | — |
| schema_version | text | sí | audit | — |
| rules_version | text | sí | audit | — |
| input_fingerprint | text | sí | audit | — |
| generated_at | time | sí | audit | — |
| cutoff | date | sí | audit | — |
| input_counts | text | sí | audit | — |
| output_counts | text | sí | audit | — |

## opportunity_links

Clave: `link_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| link_id | text | no | audit | — |
| alias_opportunity_id | text | sí | audit | — |
| canonical_opportunity_id | text | sí | audit | — |
| decision_id | text | sí | audit | — |

## import_records

Clave: `record_version_id`. Gestionada por CLI, no importar.

| Campo | Tipo | NULL | Alcance temporal | Valores |
|---|---|---|---|---|
| record_version_id | text | no | audit | — |
| entity_type | text | sí | audit | — |
| entity_id | text | sí | audit | — |
| content_fingerprint | text | sí | audit | — |
| run_id | text | sí | audit | — |
| recorded_at | time | sí | audit | — |
| normalized_json | text | sí | audit | — |
