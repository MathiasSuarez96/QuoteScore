# Registro de decisiones técnicas

Fecha de implementación inicial: 2026-09-18. Contrato: 1.0.0. Reglas tras revisión crítica: 1.1.0; compatible con las tablas anteriores. Revisiones y reportes originales conservados.

| Decisión | Motivo y efecto |
|---|---|
| Python y biblioteca estándar | CSV, JSON, Decimal, argparse y unittest cubren esta etapa sin paquetes innecesarios. |
| Tablas CSV vinculadas | Se conserva la granularidad oportunidad → propuesta → opción → componente; transacciones por oportunidad. |
| IDs explícitas opacas | El operador fija identidad en transcripciones sanitizadas; no se deduce identidad desde nombres/fechas/importes. |
| evidence_id adicional | field_evidence necesita clave estable para cargas repetibles. |
| review_queue y opportunity_links | Cola operable y agrupaciones reversibles sin destruir IDs ni filas originales. |
| outcome_history | Desenlaces y reactivaciones anexables, separados del contenido inicial. |
| load_runs | Esquema, reglas, huella, corte y conteos de cada entrada; no son features. |
| import_records | Conserva cada versión normalizada de entrada; reimportar un registro ya recibido no propone revertir un desenlace posterior. |
| Revisiones CSV completas y CURRENT | Publicación atómica simple sin servidor; historial accesible para auditoría. Costo: espacio adicional por revisión. |
| Cantidades decimales exactas | Evita errores binarios en comprobaciones monetarias. No se adivinan monedas ni conversiones. |
| Contradicción de pasajeros → NULL | Conserva la incidencia y evita elegir por intuición o completar desde el cierre. |
| Fuente corregida → propuesta | Requiere decisión y evidencia; no sobrescribe silenciosamente. |
| Snapshot separado del target | Una actualización de resultado no cambia el contenido inicial; correcciones documentales emiten otra versión. |
| Lista explícita de features | Campos de resultados, identidad y extracción no se copian a X. Componentes aún sin agregados iniciales. |
| Opciones individuales | No se asume exhaustividad ni compatibilidad para rangos de precios o agregados de servicios. |
| Reporte con corte de inventario y desenlaces | Excluye fechas conocidas posteriores al corte, explicita fechas desconocidas y permite elegir revisión archivada; auditoría completa separada. |
| Demo independiente | Casos ficticios creados para reglas, sin reutilizar ejemplos comerciales privados. |

Pendientes para datos reales: alcance permitido de uso, fuentes sanitizadas, criterios de inclusión, comprobante de venta, política de cancelaciones/reembolsos, horizonte de conversión y tratamiento de abiertas. Esos puntos no bloquean la demostración de Entrega 1.

No se agregaron infraestructura web, servidor SQL, notebooks vacíos ni modelo. Power BI está previsto como visualización; la app local futura registrará/evaluará cotizaciones y actualizará oportunidades usando las mismas reglas.

La revisión crítica agregó separación entre transición y corrección de desenlace, invalidación de evidencia al corregir valores, bloqueo por duplicados pendientes, gestión auditable de incidencias, validación numérica tolerante a errores y salida de CLI en UTF-8. Detalle en audit_delivery1.md.
