# Reglas de conciliación

1. Una oportunidad representa el mismo viaje del cliente/grupo, aunque cambie destino. Viajes distintos siguen separados aunque se repita un alias. No se infieren identidades por nombre.
2. Una versión es una propuesta enviada; una opción es una alternativa comprable. Componentes del paquete se compran juntos. No sumar opciones como componentes.
3. La venta de una parte convierte la oportunidad. Cross-sell del mismo viaje se registra como transacción adicional; no otra oportunidad. Cambio de destino no demuestra venta parcial.
4. Un documento, captura o transacción no determina por sí solo una oportunidad. El operador asigna y conserva IDs fuente; las agrupaciones quedan propuestas hasta revisión explícita.
5. Coincidencias de contenido generan sospecha, nunca eliminación. Fecha e importe no son una clave de identidad. Se diferencian archivos repetidos de operaciones legítimamente iguales.
6. Cambios de pasajeros requieren revisión. Los importes de alcance desconocido no generan precios por persona. Se preservan otros campos fiables y todas las incidencias.
7. Confirmar una agrupación conserva los registros originales mediante aliases opacos y una ID canónica. No se permiten ciclos ni escoger entre targets confirmados contradictorios. Dos primeras cotizaciones confirmadas en un grupo suspenden su snapshot hasta resolverlas.
8. Cada decisión conserva motivo, fecha, fuente y valores anterior/propuesto. Se corrige con otra decisión que referencia la vigente; nunca se borra la anterior. Rechazar o dejar pendiente una propuesta no implica pérdida comercial.
9. converted es 1 para venta confirmada, 0 para pérdida confirmada y NULL para abierta/dudosa. Un día de diferencia entre cotización y pérdida no invalida por sí solo el resultado. Silencio o ausencia de una venta encontrada nunca confirma pérdida.
10. Resultado y revisión son independientes. Puede existir un target confirmado con precio pendiente. Un resultado nuevo no modifica los campos iniciales.

La conciliación es conservadora y asistida: no hay fuzzy matching, extractor de PDFs o búsqueda automática en chats. Confirmar la pertenencia al mismo viaje sigue requiriendo evidencia humana. El alcance es suficiente para operar los conflictos V1, no pretende automatizar la reconstrucción histórica.
