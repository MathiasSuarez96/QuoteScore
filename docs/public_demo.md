# QuoteScore en la web

[Abrir la app](https://quotescore-ecewfmkqdzuqi8xxzq9g5a.streamlit.app/).

Entrada: `cloud/streamlit_app.py`; Python 3.14; dependencias: `cloud/requirements.txt`.

## Dos modos explícitos

- Con `quotescore_model_b64` y `quotescore_model_sha256` en Streamlit Secrets: carga un artefacto saneado del modelo histórico; permite subir PDF sin datos personales y evaluar con la regresión logística existente.
- Sin modelo configurado: demo sintética con tres PDF ficticios. Se identifica como datos inventados; nunca sustituye silenciosamente un modelo configurado que falle.

Los secretos son configuración administrativa: nunca aceptar artefactos joblib/pickle de visitantes. El hash verifica integridad, no confianza en la procedencia. Usar únicamente el archivo preparado y verificado por el propietario. No incluir Secrets ni modelos en Git. La versión de scikit-learn debe coincidir.

## Privacidad y límites

Antes de habilitar el cargador, el visitante confirma que retiró los datos personales y acepta procesar el PDF en Streamlit. Esto no anonimiza automáticamente un documento. La extracción ocurre en memoria del servidor; la app no escribe el PDF a disco, no lo incorpora a entrenamiento ni lo envía a un servicio de IA. No hay OCR.

Los campos y resultados se mantienen en `st.session_state`, aislados por visitante. Recargar o perder la sesión puede borrarlos. La app no ofrece persistencia comercial. El modelo queda en el servidor y no se entrega al navegador; los CSV de entrenamiento no se despliegan.

Las categorías de canales están generalizadas; seleccionar solo la que corresponda, o dejar Sin dato. La copia de despliegue conserva parámetros, preprocesamiento y referencia. No constituye un nuevo entrenamiento ni una mejora de precisión.

El semáforo expresa posición relativa frente a una referencia histórica, no probabilidades calibradas. Persisten sesgos, etiquetas inferidas y limitaciones de fechas históricas. No se presentan porcentajes como chances comprobadas de venta.

## Ejecutar

```sh
python -m pip install -r cloud/requirements.txt
python -m streamlit run cloud/streamlit_app.py
python -m unittest discover -s tests -v
```

Para probar el modo histórico localmente, configurar los dos secretos en `.streamlit/secrets.toml` (ignorado por Git). La app privada original sigue usando `iniciar_app.cmd` y su almacén local; no se migran ni reescriben datos privados.

Las fuentes web del esquema usan `website`. Revisar importaciones antiguas; la columna de puntos admite `puntos` o `puntos del programa`.
