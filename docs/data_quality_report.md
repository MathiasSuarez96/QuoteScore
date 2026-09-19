# Calidad de la Entrega 1

La entrega se verifica con una muestra completamente artificial. No se recibieron ni cargaron originales comerciales; no hay conteos conciliados ni métricas de conversión de la actividad real. El volumen declarado del historial privado no se reproduce en datos públicos ni se transforma en filas de relleno.

## Demostración comprobada

| Concepto | Conteo artificial |
|---|---:|
| Registros de oportunidad / grupos de conciliación provisionales | 4 / 4 |
| Ganadas / perdidas / abiertas | 1 / 1 / 2 |
| Cotizaciones / opciones / componentes | 3 / 3 / 1 |
| Transacciones | 1 |
| Fuentes artificiales / originales comerciales verificados | 1 / 0 |
| Primeras cotizaciones declaradas confirmadas | 3 / 4 |
| Snapshots verificados en tiempo e identidad | 1 / 4 |
| Incidencias de pasajeros contradictorios | 1 |
| Incidencias de alcance de precio desconocido | 1 |
| Sospechas de duplicado preservadas para revisión | 2 |
| Hipótesis de agrupación rechazada con registro | 1 |

Denominador de resultados y cobertura temporal: cuatro oportunidades ficticias. La venta parcial conserva la oportunidad aunque cambie de destino. La pérdida fue confirmada al día siguiente de cotizar y no se invalida por esa proximidad. Las dos oportunidades restantes no se convierten en pérdidas por falta de cierre.

Corrección tras revisión crítica: el informe anterior mostraba 3/4 snapshots verificados pese a sospechas de identidad pendientes. Ahora las sospechas afectan ambos lados del posible duplicado. Las tres primeras cotizaciones siguen recuperadas; solo una oportunidad supera también la revisión de identidad. La unicidad definitiva de los cuatro registros no está demostrada mientras existan pendientes.

La contradicción de pasajeros deja el total normalizado vacío, conserva su incidencia y bloquea el precio derivado por persona. El alcance de precio desconocido no se completa por intuición. Otros campos iniciales con evidencia siguen disponibles.

El flujo se ejecutó dos veces: la segunda carga devolvió `already_loaded`, sin duplicar oportunidades, decisiones ni eventos. La versión de snapshot fue idéntica antes y después de los desenlaces. También se emitió un reporte vacío con “Sin datos”, sin tasas inventadas.

## Obtener el informe detallado

```powershell
python -m tools.run_demo
python -m src.data --store local/demo report --cutoff 2025-02-10 --sampling "Muestra artificial de prueba"
```

El comando imprime la ruta de un Markdown versionado dentro del almacén. Incluye generación/corte, revisión, reglas, huellas de carga, conteos, completitud, procedencia por resultado/período/tipo de fuente, no aplicables y limitaciones. Las incidencias históricas se distinguen de los errores de las filas vigentes: normalizar un valor inválido a NULL no elimina su incidencia histórica.

## Pendiente para la Entrega 2

Registrar el alcance de uso permitido, recibir el inventario de ventas y muestras sanitizadas de primeras propuestas/desenlaces, y contrastar agrupaciones con evidencia. Medir entonces registros recibidos frente al volumen declarado, oportunidades únicas, cobertura inicial, exclusiones y sesgos de selección. La ingeniería sobre fuentes reales no se declara completada por tener esta base funcional.
