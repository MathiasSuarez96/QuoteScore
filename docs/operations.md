# Operación local e interfaz de entrada

## Preparar un lote

Un lote es un directorio con una o más de las siete tablas de `templates/input/`. Copiar sus encabezados exactos; mantener columnas aunque sus valores sean desconocidos. UTF-8, coma, comillas CSV estándar, un registro por fila. Los importes usan punto decimal y nunca separador de miles. Cada fila es un registro completo, no un parche parcial: celda vacía significa NULL, no “conservar el valor anterior”.

Asignar IDs opacas estables antes de cargar: letras, números, guion y guion bajo, inicio alfabético, hasta 80 caracteres. Conservar el mapeo de registro fuente a ID en el área privada. No formar claves con nombres, teléfono, fecha+importe ni posición de fila. Cada archivo/registro fuente puede representar varios hechos o varias propuestas. El cargador no decide esa granularidad por sí solo.

La entrada es una transcripción sanitizada; el sistema no extrae documentos originales. Una fuente documental se registra en sources y se referencia mediante source_id. field_evidence identifica campo, entidad, página/mensaje opacos y cuándo era conocido. `evidence_level=original_verified` debe significar revisión humana real, no simple importación. El modo artificial exige fuentes `artificial`.

Un importe que existía pero es ambiguo queda vacío. Si price_scope es desconocido, la carga deja vacíos los importes que dependen de ese alcance; quoted_price_per_person conserva su alcance explícito por persona. `first_priced_quote_status=confirmed` significa que se confirmó el carácter de primera propuesta con precio, aunque el importe no sea recuperable. No usar un resumen de cierre para declarar ese estado. Se requieren evidencias de sent_at y first_priced_quote_status para verificar temporalmente el snapshot.

## Datos privados

Antes de usar datos comerciales, completar [data_use_scope.md](data_use_scope.md) con el alcance aplicable. Cuando esté confirmado, elegir una carpeta privada local **externa** al proyecto. Separar originales, transcripciones sanitizadas y almacén de salida; las correspondencias de identidad se mantienen aparte. Ninguna ruta personal real debe quedar en documentación pública.

Forma del comando, usando rutas externas previamente elegidas:

```powershell
python -m src.data --store "<carpeta-privada-externa>/almacen" --mode private load "<carpeta-privada-externa>/entrada" --cutoff YYYY-MM-DD
python -m src.data --store "<carpeta-privada-externa>/almacen" --mode private report --cutoff YYYY-MM-DD --declared-sales <cantidad-declarada> --sampling "Criterio de inclusion y omisiones"
```

No cambiar de modo para un almacén existente. El programa impide colocar almacenes/entradas privados dentro del proyecto. No puede comprobar automáticamente que todo texto libre esté sanitizado: revisar notas, referencias y contenido antes de importar. Nunca colocar originales o notas sensibles en el modo artificial.

## Cargas y errores

La huella del lote incluye contenido de archivos y versión de reglas. Un lote idéntico es un no-op, incluso después de actualizar sus desenlaces. Reordenar filas conserva los registros mediante sus IDs, aunque registra una nueva ejecución con distinta huella. import_records conserva las versiones normalizadas recibidas: reimportar contenido ya visto no revierte desenlaces ni vuelve a proponer cambios rechazados. Una corrección nueva con la misma ID crea un caso de revisión; la versión anterior sigue vigente hasta confirmar. Para reconsiderar una versión ya recibida, reabrir explícitamente su caso con nueva evidencia.

Un encabezado incorrecto, filas mal formadas, modo incompatible o archivo desconocido aborta el lote antes de publicarlo. Errores de celdas se registran por campo; valores no interpretables pasan a NULL, y IDs inválidas impiden incorporar esa fila. Las claves foráneas rotas se conservan como incidencias bloqueantes para corregir la fuente. La CLI no imprime valores originales inválidos.

Pasajeros contradictorios entre total y adultos+niños dejan `passengers` vacío y conservan una incidencia. No se completa el total por suma ni por datos de cierre. Variantes de servicios por pasajero no deben aplanarse; dejar ambiguos los campos afectados y documentar la incidencia mediante una fuente sanitizada.

Las revisiones completas de CSV se escriben en `revisions/<id>/`; un reemplazo atómico de `CURRENT` las publica. La escritura usa bloqueo exclusivo: no hay escrituras concurrentes. Si un proceso se interrumpe, comprobar que terminó antes de retirar un `.write.lock` residual. No editar ni borrar revisiones utilizadas en análisis. Las revisiones incompletas no apuntadas por CURRENT no son vigentes.

## Revisión y desenlaces

`review` muestra el primer pendiente con IDs, valores en conflicto y fuente; `review --case ID` permite inspeccionar uno resuelto. `decide` exige una decisión explícita, motivo y fuente existente. Reabrir o revertir referencia la última decisión con `--supersedes`. Una decisión obsoleta se rechaza si el registro cambió desde la propuesta.

Confirmar un `duplicate_check` confirma la observación, **no elimina registros**. Si representan el mismo viaje, crear además `propose-group` y confirmar esa propuesta con evidencia. La agrupación usa opportunity_links: preserva filas originales y permite revertir. Las cotizaciones/transacciones originales siguen vinculadas a su ID; los reportes y snapshots resuelven el grupo canónico. Si quedan dos primeras cotizaciones confirmadas, el snapshot queda pendiente hasta revisar documentalmente sus estados.

`outcome` requiere ID de evento estable, oportunidad, estado, fecha, fuente y motivo. Repetir el mismo evento es idempotente; reutilizar su ID con contenido distinto falla. Una corrección o reactivación exige `--supersedes` al último evento. La CLI conserva el evento anterior; revisar que la reactivación corresponde al mismo viaje. Una venta parcial usa `won`, `sold_scope` y `sale_extent=partial`. Una transacción cargada por sí sola no confirma el target.

La política final de comprobante de venta y cancelaciones está pendiente. La herramienta registra afirmaciones explícitas documentadas; no certifica por sí sola que un comprobante sea suficiente. Refund/cancellation son transacciones separadas y no revierten converted automáticamente.

Para corregir una fecha o un resultado mal transcrito, usar `outcome ... --kind correction --supersedes EVENTO_ANTERIOR`. Para un cambio comercial real (por ejemplo, reactivación del mismo viaje), usar `--kind transition`, que es el valor por defecto. La corrección reemplaza la afirmación anterior al reconstruir el corte; la transición conserva su vigencia histórica. Un desenlace confirmado sin fecha aparece como “desenlace sin fecha”, no como abierta. Eventos contradictorios del mismo día sin hora suficiente quedan dudosos.

Después de confirmar o revertir una corrección de campos, la evidencia del valor anterior pasa a pendiente. Incorporar una nueva fila de field_evidence, con evidence_id nueva, fuente y known_at que acrediten el valor corregido. Reimportar el mismo respaldo viejo no lo verifica otra vez. Confirmar la corrección de un valor no demuestra por sí solo que se conocía al cotizar.

Para gestionar incidencias sin editar CSV:

```powershell
python -m src.data --store local/practica issues
python -m src.data --store local/practica issue "<issue_id>" accepted --source SRC_DEMO --reason "Dato desconocido; limitacion aceptada"
python -m src.data --store local/practica decide "<case_id_devuelto>" confirm --source SRC_DEMO --reason "Revision documentada"
```

Estados: `accepted` reconoce una limitación; `resolved` exige que la regla ya no falle; `pending` solicita reabrir. La propuesta también se puede rechazar o revertir con `decide --supersedes`. Aceptar una limitación no rellena el dato ni elimina su historial. Los errores todavía presentes continúan apareciendo en validate.

## Snapshots y reportes

`snapshot` conserva una reconstrucción inmutable por contenido. El mismo contenido devuelve la misma versión. Una nueva versión requiere fuente y motivo, y conserva la anterior. Una venta posterior no modifica features iniciales. No se emite el futuro `training_quotescore_v1.csv`: `training_eligible=0` hasta resolver política analítica y representatividad.

Solo fields con evidencia verificada y known_at compatible con score_at llegan a features. Una transcripción retrospectiva es válida si acredita que se sabía entonces. Una hora sin zona no permite comparar instantes; mezcla de día y hora del mismo día no permite ordenar. Una opción necesita evidencia del vínculo a la propuesta inicial; no se incorporan alternativas posteriores. Opciones recuperadas se conservan individualmente, sin elegir la comprada ni asumir exhaustividad. Servicios de componentes quedan disponibles en CSV, sin features agregadas V1.

`report` genera un archivo nuevo por ejecución, registra revisión, reglas, huellas y fecha de generación. El corte excluye oportunidades creadas, cotizaciones enviadas y transacciones fechadas después de ese día; conserva fechas desconocidas como cobertura incierta. Las fechas de viaje pueden ser posteriores al corte porque ya estaban cotizadas. Los errores y ejecuciones se auditan sobre la revisión completa. Las fuentes retrospectivas siguen disponibles para acreditar hechos anteriores.

`report --revision ID --cutoff YYYY-MM-DD` consulta una revisión archivada sin cambiar CURRENT. El corte se interpreta por la fecha de calendario registrada, sin inventar zona horaria. Las agrupaciones y correcciones son las de la revisión elegida; no se simula qué sabía un operador antes de cargar una fuente. No se ha implementado una base bitemporal ni una tabla de entrenamiento.

Revisar abiertas/pendientes aproximadamente mensualmente o al recibir nuevas fuentes, bajo demanda. No hay monitor ni tarea programada. Generar otro reporte tras cada actualización relevante.
