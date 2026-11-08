"""Carga el pipeline local y compara su score con una referencia congelada."""
import argparse
import hashlib
import json
import os
import platform
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from tools.entrenar_modelo_cotizaciones import leer, preparar, armar_preprocesador, SEMILLA

ROOT = Path(__file__).resolve().parent


def carpeta_privada():
    base = Path(os.environ.get('QUOTESCORE_APP_PRIVATE', Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'QuoteScorePrivate' / 'app-v1')).resolve()
    if base.is_relative_to(ROOT):
        raise ValueError('La carpeta de datos debe estar fuera del proyecto.')
    return base


def archivos_modelo():
    folder = carpeta_privada() / 'modelo'
    return folder / 'logistica.joblib', folder / 'metadata.json'


def preparar_modelo(archivo, corte):
    """Paso explícito de preparación; nunca reentrena al evaluar o cambiar un resultado."""
    data = preparar(leer(str(archivo), None), pd.Timestamp(corte), 30, True)
    train = data[data.resultado.isin(['Ganada', 'Perdida'])].copy()
    abiertas = data[data.resultado.eq('Cotizada')].copy()
    y = train.resultado.eq('Perdida').astype(int)
    if y.nunique() != 2 or y.value_counts().min() < 2 or abiertas.empty:
        raise ValueError('Se necesitan ambas clases y cotizaciones abiertas de referencia.')
    # El precio se recopila para el futuro, pero no se incorpora a este experimento.
    for frame in (train, abiertas):
        frame['log_monto'] = np.nan
        frame['monto_por_pax'] = np.nan
    pre, columns = armar_preprocesador(train)
    pipe = Pipeline([('pre', pre), ('m', LogisticRegression(class_weight='balanced', max_iter=2000, random_state=SEMILLA))])
    pipe.fit(train[columns], y)
    reference = pipe.predict_proba(abiertas[columns])[:, 1].tolist()
    source_hash = hashlib.sha256(Path(archivo).read_bytes()).hexdigest()
    metadata = dict(schema=1, model_version='logistica-' + source_hash[:10] + '-' + corte,
                    created_at=datetime.now(timezone.utc).isoformat(), cutoff=corte,
                    sklearn=sklearn.__version__, pandas=pd.__version__, python=platform.python_version(),
                    training_rows=len(train), wins=int((1-y).sum()), losses=int(y.sum()),
                    inferred_losses=int(train.origen_perdida.eq('silencio').sum()),
                    missing_initial_date=int(train.fecha_cotizacion.isna().sum()),
                    reference_count=len(reference), source_sha256=source_hash,
                    features=columns, price_used=False,
                    limitations=['Muestra sesgada por producto', 'Etiquetas de pérdida inferidas por silencio o viaje pasado',
                                 'Anticipación histórica usa último contacto si falta fecha inicial',
                                 'Ranking y semáforo no validados comercialmente'])
    model_path, meta_path = archivos_modelo()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if model_path.exists() or meta_path.exists():
        raise ValueError('Ya existe un modelo. Conservá esta versión y usá otra carpeta privada para reentrenar.')
    bundle = dict(pipeline=pipe, columns=columns, reference=reference,
                  known_destinations=sorted(train.destino_norm.dropna().unique().tolist()),
                  known_channels=sorted(train.canal.dropna().unique().tolist()), metadata=metadata)
    temporary = model_path.with_suffix('.tmp')
    joblib.dump(bundle, temporary)
    metadata['artifact_sha256'] = hashlib.sha256(temporary.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(model_path)
    return metadata


def cargar_modelo():
    model_path, meta_path = archivos_modelo()
    if not model_path.exists() or not meta_path.exists():
        raise ValueError('Todavía no hay un modelo local preparado. Consultá las instrucciones de inicio.')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta['sklearn'] != sklearn.__version__:
        raise ValueError('La versión de scikit-learn no coincide con la del modelo guardado.')
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != meta['artifact_sha256']:
        raise ValueError('El archivo del modelo cambió. No se cargará.')
    # joblib solo se usa con este artefacto local generado por preparar_modelo, nunca con uploads.
    return joblib.load(model_path)


def validar_entrada(datos, hoy=None):
    hoy = hoy or date.today()
    if not datos.get('fecha_cotizacion'):
        raise ValueError('Indicá la fecha real de envío de la primera cotización.')
    fecha = date.fromisoformat(str(datos['fecha_cotizacion']))
    if fecha > hoy:
        raise ValueError('La fecha de envío no puede estar en el futuro.')
    if not datos.get('primera_confirmada'):
        raise ValueError('Confirmá que los datos corresponden a la primera propuesta con precio.')
    if not str(datos.get('destino', '')).strip() or not datos.get('producto'):
        raise ValueError('Completá destino y producto.')
    if len(str(datos['destino'])) > 120 or any(c in str(datos['destino']) for c in '\n\r@'):
        raise ValueError('Ingresá solo el destino, sin datos personales.')
    for key in ('pax', 'menores'):
        v = datos.get(key)
        if v is not None and (not float(v).is_integer() or v < (1 if key == 'pax' else 0) or v > 999):
            raise ValueError('Revisá la cantidad de pasajeros y menores.')
    if datos.get('menores') is not None and datos.get('pax') is not None and datos['menores'] > datos['pax']:
        raise ValueError('Los menores no pueden superar el total de pasajeros.')
    if datos.get('fecha_viaje') and date.fromisoformat(str(datos['fecha_viaje'])) < fecha:
        raise ValueError('El viaje no puede empezar antes de la primera cotización.')
    if datos.get('fecha_regreso') and datos.get('fecha_viaje') and str(datos['fecha_regreso']) < str(datos['fecha_viaje']):
        raise ValueError('El regreso es anterior a la salida.')
    if datos.get('monto') is not None and (not np.isfinite(datos['monto']) or datos['monto'] <= 0):
        raise ValueError('El monto debe ser positivo o quedar vacío.')


def evaluar(datos, bundle):
    validar_entrada(datos)
    row = {k: datos.get(k, np.nan) for k in ('canal','producto','destino','pax','menores','puntos')}
    # Fechas DD/MM/YYYY para coincidir con el parser original dayfirst=True.
    for key in ('fecha_cotizacion','fecha_viaje'):
        row[key] = date.fromisoformat(str(datos[key])).strftime('%d/%m/%Y') if datos.get(key) else np.nan
    row.update(id='NUEVA', resultado='Cotizada', fecha_ultimo_contacto=np.nan, monto=np.nan)
    frame = preparar(pd.DataFrame([row]), pd.Timestamp.today().normalize(), 30, False)
    p = float(bundle['pipeline'].predict_proba(frame[bundle['columns']])[0, 1])
    reference = np.asarray(bundle['reference'])
    below = int((reference < p).sum())
    percentile = 100 * below / len(reference)
    level = 'Alto' if percentile >= 2*100/3 else 'Medio' if percentile >= 100/3 else 'Bajo'
    warnings = []
    dest = frame.iloc[0]['destino_norm']
    if dest not in bundle['known_destinations']:
        warnings.append('Este destino no aparece en el entrenamiento; la comparación tiene mayor incertidumbre.')
    if datos.get('producto') == 'Hotel' and not bundle['metadata'].get('synthetic',False):
        warnings.append('El entrenamiento no contiene hoteles perdidos. Un score bajo puede reflejar ese sesgo.')
    if datos.get('canal') and str(datos['canal']).strip().lower() not in bundle['known_channels']:
        warnings.append('Este canal no aparece con la misma etiqueta en el entrenamiento.')
    faltan = [k for k in ('pax','menores','fecha_viaje','canal','puntos') if datos.get(k) is None]
    if faltan:
        warnings.append('Datos desconocidos: ' + ', '.join(faltan) + '. El pipeline usa su tratamiento de faltantes.')
    return dict(raw_score=p, percentile=percentile, below=below, total=len(reference), level=level,
                model_version=bundle['metadata']['model_version'], reference_cutoff=bundle['metadata']['cutoff'], warnings=warnings)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('accion', choices=['preparar'])
    parser.add_argument('--archivo', required=True)
    parser.add_argument('--fecha-corte', required=True)
    args = parser.parse_args()
    date.fromisoformat(args.fecha_corte)
    print(json.dumps(preparar_modelo(args.archivo, args.fecha_corte), ensure_ascii=False, indent=2))
