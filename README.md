# QuoteScore

Iniciativa personal de práctica y portfolio para organizar oportunidades de viaje y estudiar, más adelante, su conversión en ventas. **Entrega 1: base local funcionando con datos artificiales. Todavía no existe un score validado.** No es un encargo ni una entrega académica de una institución o empresa.

La unidad de trabajo es una necesidad concreta de viaje. Una oportunidad puede tener varias propuestas, alternativas, componentes y transacciones. Comprar una parte cuenta como conversión; cambiar destino manteniendo el mismo viaje conserva la oportunidad. La reconstrucción inicial usa únicamente información acreditada al enviar la primera cotización con precio.

## Empezar en Windows

Desde la carpeta del proyecto, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m tools.run_demo
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Python 3.11 o superior; se verificó con 3.14.7. No requiere instalar paquetes, activar PowerShell ni configurar servicios. `requirements.txt` deja explícito que esta etapa usa la biblioteca estándar. Si `.venv` ya existe, ejecutar directamente su Python.

La demo carga cuatro oportunidades **inventadas desde cero**, registra una venta parcial y una pérdida confirmada, revisa una propuesta de agrupación y genera un informe. Incluye pasajeros contradictorios y precio de alcance desconocido para probar cómo quedan registradas las incidencias. Ejecutarla nuevamente no duplica registros, decisiones ni desenlaces. Cada informe se conserva por separado.

Las salidas de la demo quedan en `local/demo/`, excluido de Git. El comando imprime la ruta del reporte. Esos conteos solo describen la demostración.

Las decisiones de la demo están programadas con evidencia ficticia: muestran cómo registrar una decisión humana, no un sistema que descubre por sí solo si hubo venta o si dos consultas son el mismo viaje. La carga, los CSV, el historial, las comprobaciones y el reporte sí se ejecutan realmente. Quedan dos sospechas pendientes a propósito; por eso solo un snapshot supera conjuntamente tiempo e identidad.

La revisión crítica posterior y sus correcciones están en [docs/audit_delivery1.md](docs/audit_delivery1.md).

## Qué está implementado

- Siete tablas de entrada CSV y siete tablas auxiliares, con esquemas, claves y plantillas consistentes.
- Carga idempotente con IDs persistentes, normalización conservadora, incidencias acumulables y huella de cada lote.
- Cola de revisión por CLI: correcciones documentales, sospechas de duplicados y agrupaciones explícitas; decisiones reversibles con historial.
- Registro de desenlaces con evidencia y fecha, sin completar retrospectivamente la cotización inicial.
- Snapshots de auditoría versionados con una lista explícita de campos iniciales y evidencia temporal por campo.
- Reportes de calidad para datos vacíos o cargados, con denominadores y fecha de corte.

Los datos se guardan como CSV en revisiones completas. `CURRENT` señala la revisión vigente; las anteriores se conservan. No hay servidor de base de datos. No se interpretan automáticamente PDFs o chats.

## Flujo manual reproducible

```powershell
python -m src.data --store local/practica init
python -m src.data --store local/practica load examples/artificial/input --cutoff 2025-02-10
python -m src.data --store local/practica validate
python -m src.data --store local/practica review
python -m src.data --store local/practica issues
python -m src.data --store local/practica snapshot --reason "Reconstruccion artificial inicial" --source SRC_DEMO
python -m src.data --store local/practica outcome OP_DEMO_1 won --at 2025-02-06 --source SRC_DEMO --reason "Venta parcial artificial confirmada" --event-id EVENT_PRACTICA_1 --sold-scope flight_only --sale-extent partial
python -m src.data --store local/practica report --cutoff 2025-02-10 --sampling "Demostracion artificial"
```

`validate` devuelve 1 si hay errores actuales; `load` conserva incidencias y devuelve 0 cuando el lote pudo registrarse. Un error de uso/esquema devuelve 2. La demo incluye errores de entrada históricos normalizados a NULL y advertencias tolerables. Consultar el reporte y `quality_issues.csv`, no solo el código de salida.

Para revisar una agrupación:

```powershell
python -m src.data --store local/practica propose-group OP_DEMO_4 OP_DEMO_1 --source SRC_DEMO --reason "Hipotesis ficticia de mismo viaje"
python -m src.data --store local/practica review
```

Copiar el `case_id` que devuelve el primer comando. Las siguientes son formas de uso; sustituir los identificadores entre `<...>`:

```powershell
python -m src.data --store local/practica decide "<case_id>" confirm --source SRC_DEMO --reason "Evidencia revisada"
python -m src.data --store local/practica decide "<case_id>" pending --source SRC_DEMO --reason "Reabrir por nueva evidencia" --supersedes "<decision_id>"
```

También se admite `reject`. Rechazar un caso no marca una oportunidad como perdida. `review` muestra un caso sin modificarlo; una respuesta omitida nunca confirma. Para una corrección del CSV, reimportar la fila completa con la misma ID y revisar la propuesta generada. Las tablas gestionadas por la CLI no se editan a mano.

## Documentación y entrada de datos

- [Guía de operación e interfaz de entrada](docs/operations.md).
- [Diccionario de datos](docs/data_dictionary.md) y [plantillas de entrada](templates/input/).
- [Reglas de conciliación](docs/reconciliation_rules.md) y [decisiones técnicas](docs/decisions.md).
- [Alcance de uso de datos](docs/data_use_scope.md).
- [Reporte de la entrega](docs/data_quality_report.md), [verificación](docs/verification.md) y [resumen ejecutivo](docs/executive_summary.md).
- [Reporte ficticio generado](docs/demo_report.md): resultado legible de una ejecución real, sin datos comerciales.

Los originales, datos comerciales reales, tablas de identidad, reportes privados y el contexto maestro quedan **fuera del árbol del proyecto**. El modo `private` requiere rutas externas y un alcance de uso previamente aclarado. `.gitignore` es una barrera adicional; no anonimiza contenidos ni elimina historial. No hay remoto, publicación o envío a terceros configurados por este proyecto.

## Próximas entregas

Entrega 2: reconstruir fuentes permitidas, conciliar oportunidades y emitir el reporte real. Entrega 3: análisis descriptivo y decisión de viabilidad de un modelo. Posteriormente: Power BI como dashboard y app local propuesta en Streamlit con formulario/listado. El modelo, si la evidencia alcanza, se evaluará antes de mostrar probabilidades. No se han construido interfaz web, dashboard ni entrenamiento.

El tiempo de revisión manual se estimará al conocer las fuentes; no hay fechas ni dedicación semanal asumidas.
