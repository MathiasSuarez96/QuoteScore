# Importación de resúmenes suministrados

El importador recibe una transcripción revisada en JSON, no interpreta automáticamente
Markdown, PDFs ni chats. Los manifiestos comerciales, sus correspondencias y reportes
permanecen fuera del proyecto. Consultar el registro de alcance para el uso local
confirmado; los resultados de cargas privadas se conservan junto al almacén externo.

Contrato: objeto con `mode` (`artificial` o `private`) y `tables`, cuyas claves son las
siete tablas de entrada del diccionario. Cada valor es una lista de objetos con columnas
del contrato V1. Se admiten campos ausentes como NULL; se rechazan columnas desconocidas
e IDs repetidos. IDs opacos persistentes se asignan durante la transcripción, nunca por
alias, destino, posición actual de una fila ni similitud textual.

| Antecedente | Destino y tratamiento |
|---|---|
| Documento resumen e inventario | `sources`: tipo summary, evidence_level supplied_summary (resumen suministrado), referencias opacas distintas. No afirmar originales verificados. |
| Resultado declarado | `opportunities`: converted y status, outcome_source_id y outcome_basis; review_status pending. Fecha de desenlace solamente si está explícita. |
| Referencia aún sin identidad conciliada | Registro provisional de oportunidad, sin afirmar unicidad comercial. Revisión y conciliación mediante CLI existente. |
| Fecha de cotización | `quotes.sent_at`, precisión day; first_priced_quote_status candidate o unknown. No completa outcome_at ni created_at. |
| Varias versiones explícitas del mismo viaje | Distintos quote_id bajo un mismo opportunity_id. No inventar números de versión. |
| Descripción complementaria de una referencia | Enriquece la misma transcripción; no genera otra oportunidad. Si abarca varias referencias sin atribución precisa, mantener pendiente en la fuente privada. |
| Alternativas comprables documentadas | `quote_options`; separar versiones y opciones. Si no puede atribuirse a una propuesta, mantener pendiente antes de transcribir. |
| Servicios de una opción | `quote_components`; no repetir el total del paquete ni convertir cada componente en alternativa. |
| Venta y adicional explícitos | `transactions`, misma oportunidad cuando esté acreditado. No crear transacción por cada resumen repetido ni sumar un total resumen con su desglose. |
| Importe o destino final | Campos finales de `opportunities` o transacción respaldada; nunca rellenan quote_options. No inferir moneda. |
| Exclusión explícita | exclude_from_training=1 y exclusion_reason; conservar resultado e historial. |
| Evidencia por campo | `field_evidence`, pending; known_at desconocido salvo evidencia explícita. El importador no verifica temporalidad. |
| Ambigüedades | NULL en el campo afectado y `quality_issues`/cola de revisión existente; conservar discrepancia en fuente privada. |
| Total comercial declarado | Parámetro del reporte; no genera filas, no acredita registros recibidos ni permite calcular conversión de una muestra. |

Los detalles no representables sin pérdida permanecen en la fuente privada hasta revisar
su correspondencia. No se fuerza un mapeo genérico de puntos pagados a puntos propuestos,
ni primer contacto a primera cotización. Una fecha compartida por venta y cotización no
prueba orden intradiario. La carga crea historial de resultados y registra versiones de
entrada; las correcciones posteriores pasan por la cola existente.

Ejecutar pruebas con datos artificiales independientes:

```powershell
python -m unittest discover -s tests -v
```

Ejemplo de contrato artificial mínimo:

```json
{"mode":"artificial","tables":{"sources":[{"source_id":"S_EXAMPLE","sanitized_reference":"Independent artificial example"}],"opportunities":[{"opportunity_id":"O_EXAMPLE","status":"open","exclude_from_training":"0","outcome_source_id":"S_EXAMPLE"}]}}
```

Guardar ese ejemplo en un JSON y ejecutar:

```powershell
python -m src.data.summary_import example.json --store local/summary-demo --cutoff 2024-02-01
```

Para datos reales se registra primero la instrucción y el alcance aplicable en
`docs/data_use_scope.md`: quién lo confirma, fecha, categorías de datos,
entorno local, finalidad, restricciones y referencia privada al respaldo. No atribuir
la confirmación del usuario a terceros. Solo entonces
cambiar el estado a `Estado: **confirmado para importación privada de resúmenes**`.
Esta marca es un control operativo, no valida una autorización ni reemplaza su revisión.
El comando admite `--mode private` y exige manifiesto y almacén externos al proyecto.
No habilitarlo solo por haber recibido los resúmenes. Los comandos CSV anteriores siguen
existiendo; tampoco deben usarse para eludir el alcance pendiente.

Limitaciones: la transcripción humana debe resolver referencias complementarias y señalar
ambigüedades; el importador no descubre identidades, no concilia automáticamente y no
garantiza que un texto libre esté sanitizado. No genera una tabla de entrenamiento.
