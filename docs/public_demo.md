# Demo pública de QuoteScore

**Demo publicada:** https://quotescore-ecewfmkqdzuqi8xxzq9g5a.streamlit.app/

Entrada para hosting: `cloud/streamlit_app.py`. La entrada `app.py` sigue siendo la versión de trabajo privada y no debe desplegarse directamente.

## Contenido público

- Mismo diseño, identidad personal y firma GitHub.
- Tres PDF ficticios generados en memoria; no admite subir documentos reales.
- Regresión logística entrenada en memoria sobre 200 filas completamente sintéticas y 40 ejemplos sintéticos de referencia. El generador, su semilla y su regla artificial son públicos en `demo_publica.py`.
- No usa el modelo ni los CSV comerciales locales. No requiere secretos ni credenciales de datos.
- Guardado y cambios de estado solo en `st.session_state`, independientes entre visitantes. No hay base de datos compartida ni persistencia de oportunidades. Recargar o perder sesión puede borrar los ejemplos.
- Se procesa en el servidor, no exclusivamente en la computadora del visitante. No ingresar información personal en los campos editables.
- Los colores ilustran el flujo técnico; no demuestran precisión comercial.

## Ejecutar y probar

```powershell
.\.venv\Scripts\python.exe -m pip install -r cloud/requirements.txt
.\.venv\Scripts\python.exe -m streamlit run cloud/streamlit_app.py --server.address 127.0.0.1 --server.port 8502
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La app local se inicia con `iniciar_app.cmd`, que conserva el enlace exclusivo a 127.0.0.1. La configuración compartida omite una dirección fija para que el hosting pueda asignar su interfaz.

## Streamlit Community Cloud

Repositorio: `MathiasSuarez96/QuoteScore`; rama: `main`; archivo: `cloud/streamlit_app.py`. Seleccionar Python 3.14 si está disponible (versión verificada localmente 3.14.7). Las dependencias se toman de `cloud/requirements.txt`. No configurar rutas privadas ni subir el modelo entrenado con clientes.

Una vez desplegada, verificar carga inicial, lectura de los tres ejemplos, evaluación, guardado, cambio de estado e independencia entre dos sesiones. No presentar el despliegue como finalizado hasta confirmar la URL pública operativa.

## Texto para compartir

Desarrollé QuoteScore, un proyecto personal en Python que convierte cotizaciones PDF en datos estructurados y permite explorar un modelo experimental de clasificación. Incluye revisión de campos, evaluación y seguimiento de resultados. Esta demo pública utiliza datos ficticios y muestra el flujo técnico; no predice ventas reales. La validación con datos confirmados sigue en desarrollo.

## Compatibilidad de importación

Las fuentes web usan ahora la categoría genérica `website`. En copias de trabajo antiguas, revisar los valores de `lead_source_at_quote` antes de importar; no se migran almacenes privados automáticamente. La columna de puntos puede llamarse `puntos` o `puntos del programa`.
