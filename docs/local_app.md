# Predictor de Cotizaciones

Prototipo Streamlit local. Ejecutar `iniciar_app.cmd` o, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Abrir http://127.0.0.1:8501. No desplegar esta app privada en un servidor público.

## Cómo está separado

- `extraer_pdf.py`: recibe bytes en memoria, busca campos explícitos y devuelve sugerencias. No guarda PDF, nombres ni texto completo. Varias alternativas, destinos ambiguos, documentos escaneados y campos sin etiquetas requieren revisión manual.
- `modelo.py`: carga una regresión logística local, aplica las mismas transformaciones del experimento y compara el score con una referencia congelada. El precio se guarda, pero no se usa para predecir.
- `app.py`: formulario, logos y fuente local, resultados, guardado y seguimiento.
- `src/data/app_store.py`: reutiliza los CSV versionados del proyecto para preservar la primera propuesta y registrar el historial de resultados.

## Preparar el modelo una sola vez

```powershell
.\.venv\Scripts\python.exe modelo.py preparar --archivo "RUTA_PRIVADA\entrenamiento.csv" --fecha-corte AAAA-MM-DD
```

Elegir explícitamente la fecha del experimento; cambia la regla histórica de silencio. El comando no sobrescribe un modelo existente. Para una futura versión, usar otra carpeta externa mediante `QUOTESCORE_APP_PRIVATE` y validar antes de usarla.

Los datos y artefactos quedan por defecto en `%LOCALAPPDATA%\QuoteScorePrivate\app-v1`, fuera del repositorio. La app no modifica el almacén histórico. Los PDF se mantienen solo durante el procesamiento en memoria; ningún servicio externo recibe el archivo. La fuente Poppins también se sirve localmente (licencia en assets/OFL.txt).

La fecha de envío viene en hoy, pero es editable: un PDF viejo debe conservar su fecha real. Se guarda una opción por oportunidad, con resultado vacío (estado abierta), no todo un conjunto de alternativas. El botón Nueva cotización inicia otro registro; no usarlo para duplicar alternativas de un mismo viaje. Guardar dos veces el mismo formulario no duplica filas. Los cambios posteriores al guardado no sobrescriben la propuesta inicial. Ganada/Perdida exige confirmación; la app no convierte silencio en pérdida automáticamente.

## Límites del experimento

La muestra histórica está sesgada por producto. El pipeline heredado infiere pérdidas y usa último contacto como referencia cuando falta la fecha inicial: esto puede filtrar información posterior. No demuestra utilidad comercial. El ranking tampoco está validado. Bajo/Medio/Alto son tercios de posición relativa frente a las abiertas congeladas, no probabilidades ni recomendaciones de seguimiento. Cambiar el supuesto de tasa real mediante la corrección del prior mantiene el orden, pero no lo valida. Guardar resultados no reentrena automáticamente.

La importación de CSV originales y los modelos son privados. No agregar a Git datos reales, PDF ni artefactos. `.gitignore` excluye PDF, joblib, pkl y carpetas privadas; revisar siempre el diff antes de publicar.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas automatizadas usan contenido artificial: una opción clara, múltiples alternativas, documentos sin texto y formatos de las plantillas. También se verificaron cuatro PDF reales localmente sin incorporarlos al repositorio. Se reconocen rangos de fechas, destino principal frente a aeropuertos, composición de pasajeros, totales brutos y puntos personalizados. Si hay varios precios, el usuario selecciona una alternativa. Canal, fecha de envío y datos ausentes requieren confirmación. Esto no garantiza compatibilidad con cualquier PDF.
