# Revisión crítica de la Entrega 1

Revisión contra el contexto maestro privado, versión 2.3. El contexto y su anexo no se copiaron al proyecto. Esquema CSV: 1.0.0; reglas corregidas: 1.1.0. Las revisiones y los reportes anteriores se conservaron.

## Conclusión

La base ejecutaba un flujo real, pero las 20 pruebas originales no justificaban afirmar que todas las reglas estaban bien cubiertas. Se encontraron y corrigieron errores de temporalidad, conciliación, reportes, contratos y operación. La nueva suite contiene 37 pruebas, incluidas ejecuciones reales de la CLI en procesos separados.

## Hallazgos y correcciones

| Hallazgo | Consecuencia anterior | Corrección y comprobación |
|---|---|---|
| Corregir un campo reutilizaba su evidencia anterior | Un dato cambiado podía parecer conocido desde la primera cotización | La evidencia del campo pasa a pendiente; una nueva evidencia debe acreditar el valor y su known_at. Prueba con dato posterior bloqueado. |
| Sospechas de duplicado no bloqueaban ambos lados | El reporte mostraba snapshots verificados con identidad incierta | Se bloquean ambos registros hasta rechazar la sospecha o resolver la agrupación. Confirmar una sospecha sin agrupar tampoco despeja identidad. |
| La demo informaba 3/4 snapshots verificados | Mezclaba recuperación de cotización con verificación de identidad | Conserva tres primeras propuestas, pero informa 1/4 snapshots verificados conjuntamente. |
| Corte aplicado solo a desenlaces | Inventario podía incluir registros futuros | Se filtran creación de oportunidad, envío de propuesta y fecha de transacción; fechas desconocidas se explicitan. |
| Corrección de una fecha se trataba como transición comercial | Una venta con fecha corregida seguía figurando en el corte anterior | Se separan transition y correction; se conserva el historial y se sustituye la afirmación corregida al proyectar. |
| Desenlace confirmado sin fecha quedaba entre abiertas | Se perdía la incertidumbre sobre fecha del resultado | Categoría específica “desenlace sin fecha”; no se inventa fecha. |
| Corrección parcial bloqueada por cualquier error restante | No se podía arreglar un campo hasta resolver todos | Se rechazan errores nuevos, permitiendo arreglos independientes y reversión auditable. |
| Incidencias solo se podían inspeccionar en CSV | Faltaba una operación para documentar aceptación/resolución | Comandos issues e issue, con propuestas y decisiones reversibles. Aceptar no significa completar el dato. |
| Decimal.normalize podía redondear números extensos | Alteración silenciosa de un valor de entrada | Normalización textual exacta y prueba con más de 28 cifras. |
| Un CSV alterado con un número inválido podía romper validate | Fallaba la herramienta antes de informar el problema | Validación trabaja sobre copia y evita aritmética sobre celdas inválidas. |
| Esquema de status de review_queue usaba estados comerciales | Los datos de auditoría no coincidían con su esquema | Catálogo propio pending/confirmed/rejected; pruebas sobre filas de auditoría. |
| Faltaban comprobaciones de moneda de cierre y tipo de cambio | Posibles importes sin moneda o conversión inválida | Validaciones adicionales; siguen sin sumarse importes incompatibles. |
| Reportes archivados sin comando de reproducción por revisión | Había que manipular CURRENT para analizar otra revisión | report --revision consulta el archivo histórico sin modificar CURRENT. |
| Acentos en salida de CLI mediante pipes Windows | Lectura JSON podía fallar aunque el comando terminara bien | Salida UTF-8 explícita; pruebas de subprocesos exigen una respuesta real. |
| Conteo llamado “único” con duplicados pendientes | Afirmación excesiva de conciliación terminada | Se presenta como conciliación actual y se advierte que la unicidad depende de los pendientes. |

## Contraste con el documento maestro

| Requisito | Estado real después de la revisión |
|---|---|
| Unidad viaje, propuestas, alternativas, componentes y transacciones separados (§4, §6) | Tablas vinculadas e IDs persistentes; no se suman alternativas ni se fuerzan vínculos de transacción a opción. |
| Venta parcial y cambio de destino del mismo viaje (§2) | Implementados y probados; no crean automáticamente otra oportunidad. |
| Primera propuesta con precio y ausencia de información futura (§5, §8) | Lista explícita de campos, prueba de evidencia temporal, versiones de snapshot y bloqueo de correcciones sin evidencia nueva. |
| Datos ambiguos, nulos y múltiples incidencias (§6, §7) | Carga conservadora y calidad por campo; arreglos parciales permitidos. |
| Conciliación conservadora y revisión reversible (§7, §12.3) | Cola, agrupaciones explícitas, sospechas sin borrado, motivo/fuente/fecha e historial. No inferencia automática de identidad. |
| Carga repetible y actualizaciones (§12.2, §12.4) | Huellas por lote/registro, revisión publicada atómicamente y eventos de desenlace; pruebas de reordenación tras cierre. |
| Reporte vacío, cobertura y denominadores (§9) | Ejecutable; incluye cortes, fuentes, completitud, pendientes, exclusiones y límites. La comparación con volumen declarado se configura, no se rellena. |
| Exclusión administrativa sin borrar historia (§2, §7) | exclude_from_training, motivo y bloqueo explícito; probado con un caso completamente artificial. |
| Privacidad y alcance de uso (§11, §13.5) | Fuentes reales externas, ejemplos independientes, modo privado fuera del proyecto y registro del alcance pendiente. |
| Documentación, resumen ejecutivo y aprendizaje (§12, §13.6) | README, diccionario, guía operativa, decisiones, resumen y pruebas reproducibles. |
| No adelantar modelos, web, dashboard o servidor (§1, §10, §13) | Respetado. No hay entrenamiento, app visual, servicio SQL ni dashboard implementados. |

## Qué está simulado y qué no

La demo inventa cuatro oportunidades y sus evidencias. También programa qué decisión comercial se registra, como sustituto de una persona que ya revisó documentación: el código **no descubrió una venta en un chat ni confirmó una identidad real**.

La carga, normalización, archivos CSV, decisiones, historial, snapshots y reportes son operaciones reales. Se comprobaron tanto en funciones como desde la terminal. Los conteos de la demo se leen del almacén, no son números decorativos.

`training_eligible=0` es un bloqueo deliberado hasta definir política analítica y representatividad. No es una evaluación estadística ni un modelo oculto. Un snapshot verificado acredita las reglas declaradas y evidencia ingresada; no certifica automáticamente la verdad de una fuente.

## Limitaciones que permanecen

- No se recibieron fuentes comerciales originales. No se cargó el historial completo ni se inspeccionaron documentos reales.
- No hay extractor de PDFs/chats, detector general de datos personales ni conciliación semántica. La transcripción, asignación de IDs, sanitización y verificación documental requieren intervención humana.
- La detección automática de duplicados es exacta y conservadora. Similitudes más complejas se proponen explícitamente; no hay fuzzy matching.
- Componentes se conservan en CSV; sus agregados, rangos de opciones exhaustivas y entrenamiento se dejan para cuando existan fuentes conciliadas. No se elige retrospectivamente la opción comprada.
- El reporte usa las correcciones y agrupaciones de la revisión seleccionada. No reconstruye por sí solo qué información estaba disponible al operador en cada fecha de carga; las fechas desconocidas permanecen inciertas.
- El sistema conserva revisiones locales, pero no sustituye respaldos externos. No se inicializó Git ni se creó remoto; .gitignore está preparado, sin historial de commits que auditar.
- El alcance para usar datos comerciales, comprobante de venta, cancelaciones, horizonte y representatividad siguen pendientes antes de entrenar. La herramienta no decide esas políticas por su cuenta.

## Reproducir

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tools.run_demo
.\.venv\Scripts\python.exe -m tools.run_demo
```

Resultado verificado: 37 pruebas aprobadas; demo nueva y repetida sin duplicaciones, con cuatro oportunidades, tres propuestas, tres opciones, una transacción, cuatro incidencias y dos eventos de desenlace. Quedan dos sospechas pendientes y un snapshot verificado. Las demás reconstrucciones conservan sus limitaciones.
