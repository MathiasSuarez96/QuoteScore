# Verificación de Entrega 1

Entorno comprobado el 2026-09-18: Windows, Python 3.14.7, Git 2.55.0. Se detectó el ejecutable local de Power BI Desktop; no se ejecutó ni se verificaron edición, licencia o distribución. Entorno virtual `.venv` creado. Sin dependencias externas instaladas.

Comandos ejecutados desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m tools.build_contract
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tools.run_demo
.\.venv\Scripts\python.exe -m tools.run_demo
.\.venv\Scripts\python.exe -m src.data --store local/empty report --cutoff 2025-02-10
.\.venv\Scripts\python.exe -m src.data --store local/demo review
```

Después de la revisión crítica pasaron **37 pruebas automatizadas**, sin excepciones de subprocesos. Cubren idempotencia por lote y por registro, reordenación después de un desenlace, nulos/ceros, claves foráneas, alcance monetario ambiguo, múltiples incidencias, venta parcial, cambio de destino, duplicados sin eliminación, correcciones y reversión, agrupación reversible, reactivación auditable, fuentes artificiales separadas, reporte vacío y con fecha de corte, plantillas y bloqueo de datos finales/posteriores en snapshots. También prueban precisión temporal incompatible, invalidación de evidencia antigua, exclusiones explícitas, corrección de fechas de cierre, cifras decimales extensas, gestión de incidencias y CLI real con salida UTF-8.

La demo completa terminó y su segunda ejecución no duplicó registros. El contenido inicial permaneció estable tras incorporar los desenlaces. El reporte vacío se generó correctamente. No se ejecutaron pruebas con originales comerciales, extractor de PDF/chat, interfaz web, Power BI o modelos porque no forman parte de esta entrega.

Se probó una demo nueva en `local/audit-demo` y la compatibilidad con `local/demo` ya existente. Reglas actuales: 1.1.0; esquema CSV compatible: 1.0.0. Una primera ejecución con reglas nuevas puede registrar una nueva carga; conserva las filas y eventos ya recibidos. Ver [audit_delivery1.md](audit_delivery1.md) para hallazgos y límites.

Las pruebas son evidencia del flujo artificial V1, no de cobertura de todos los formatos históricos. La conciliación sigue requiriendo revisión humana y la política analítica previa al entrenamiento permanece pendiente.
