#!/usr/bin/env python3
"""
Predictor de cotizaciones perdidas (Viajes Soy Santander / TocToc).

Qué hace
--------
1. Lee una planilla (Excel o CSV) con una fila por cotización.
2. Se queda con las filas Ganada o Perdida. Las "Cotizada" viejas (sin novedades
   hace más de N días, o con el viaje ya pasado) se cuentan como Perdida por
   silencio. Las "Cotizada" recientes no se usan para entrenar: se puntúan al final.
3. Usa variables de cotización. ATENCIÓN: el fallback a último contacto cuando
   falta la fecha inicial puede introducir información posterior; no garantiza
   ausencia de filtración temporal ni validez comercial.
4. Entrena regresión logística (línea de base) y un árbol poco profundo.
5. Valida con validación cruzada estratificada y mide la clase Perdida.
6. Guarda un CSV con la probabilidad de pérdida de las cotizaciones abiertas.

Uso
---
    pip install pandas scikit-learn openpyxl
    python entrenar_modelo_cotizaciones.py --archivo cotizaciones_privadas.xlsx
    python entrenar_modelo_cotizaciones.py --archivo datos.csv --dias 45

Columnas esperadas (los alias entre paréntesis también sirven)
--------------------------------------------------------------
    id, resultado (estado), fecha_cotizacion (1er contacto),
    fecha_ultimo_contacto (ficha actualizada), fecha_viaje (inicio viaje),
    canal (canal de entrada), producto, destino, pax, menores,
    monto (monto (usd)), puntos (puntos santander)

Reglas de datos
---------------
* "monto" debe ser el monto COTIZADO en todas las filas. Si en las ganadas pones
  el monto vendido y en las perdidas el cotizado, el modelo aprende esa diferencia
  y no sirve.
* No uses columnas que se conocen después del cierre (etapa, motivo de pérdida,
  notas, evidencia). Este script las ignora a propósito.
* Los nombres de clientes nunca se leen ni se imprimen. Solo se usa el id.
"""
import argparse
import re
import sys
import unicodedata
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

SEMILLA = 42

ALIAS = {
    "id": ["id"],
    "resultado": ["resultado", "estado"],
    "fecha_cotizacion": ["fecha_cotizacion", "1er contacto", "fecha 1er contacto"],
    "fecha_ultimo_contacto": ["fecha_ultimo_contacto", "ficha actualizada", "ultimo contacto", "último contacto"],
    "fecha_viaje": ["fecha_viaje", "inicio viaje", "inicio"],
    "canal": ["canal", "canal de entrada"],
    "producto": ["producto"],
    "destino": ["destino"],
    "pax": ["pax"],
    "menores": ["menores"],
    "monto": ["monto", "monto (usd)", "monto cotizado"],
    "puntos": ["puntos", "puntos santander"],
}

RESULTADOS = {
    "ganada": "Ganada", "vendida": "Ganada",
    "perdida": "Perdida",
    "cotizada": "Cotizada", "en curso": "Cotizada", "por confirmar": "Cotizada",
}


def normalizar(texto):
    """Minúsculas, sin tildes y con guiones bajos como espacios."""
    t = unicodedata.normalize("NFKD", str(texto).strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return t.replace("_", " ")


def leer(archivo, hoja):
    """Lee Excel o CSV y busca solo la fila de encabezados."""
    if archivo.lower().endswith((".csv", ".txt")):
        crudo = pd.read_csv(archivo, header=None, dtype=object)
    else:
        xls = pd.ExcelFile(archivo)
        if hoja is None:
            hoja = next((h for h in ("Entrenamiento", "Fichas") if h in xls.sheet_names),
                        xls.sheet_names[0])
        print(f"Hoja usada: {hoja}")
        crudo = pd.read_excel(archivo, sheet_name=hoja, header=None, dtype=object)

    conocidos = {normalizar(a) for lista in ALIAS.values() for a in lista}
    fila = None
    for i in range(min(15, len(crudo))):
        celdas = {normalizar(c) for c in crudo.iloc[i].tolist() if pd.notna(c)}
        if len(celdas & conocidos) >= 4:
            fila = i
            break
    if fila is None:
        sys.exit("No encontré la fila de encabezados. Revisá los nombres de las columnas.")

    df = crudo.iloc[fila + 1:].copy()
    df.columns = [normalizar(c) if pd.notna(c) else f"_col{j}" for j, c in enumerate(crudo.iloc[fila])]
    df = df.dropna(how="all")

    salida = pd.DataFrame(index=df.index)
    for canonica, alias in ALIAS.items():
        columna = next((normalizar(a) for a in alias if normalizar(a) in df.columns), None)
        salida[canonica] = df[columna] if columna else np.nan
    return salida.reset_index(drop=True)


def preparar(df, hoy, dias, usar_silencio):
    df = df.copy()
    df["resultado"] = df["resultado"].map(lambda x: RESULTADOS.get(normalizar(x)) if pd.notna(x) else None)
    df = df[df["resultado"].notna()].copy()

    for c in ("fecha_cotizacion", "fecha_ultimo_contacto", "fecha_viaje"):
        df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
    for c in ("pax", "menores", "monto"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Cotizadas viejas: pérdida por silencio
    sin_novedad = (hoy - df["fecha_ultimo_contacto"]).dt.days > dias
    viaje_pasado = df["fecha_viaje"] < hoy
    silencio = (df["resultado"] == "Cotizada") & (sin_novedad | viaje_pasado)
    df["origen_perdida"] = np.where(silencio, "silencio", "")
    if usar_silencio:
        df.loc[silencio, "resultado"] = "Perdida"

    # Variables conocidas al cotizar
    referencia = df["fecha_cotizacion"].fillna(df["fecha_ultimo_contacto"])
    df["dias_hasta_viaje"] = (df["fecha_viaje"] - referencia).dt.days
    df["mes_viaje"] = df["fecha_viaje"].dt.month.map(lambda m: f"{int(m):02d}" if pd.notna(m) else np.nan)
    df["con_menores"] = np.where(df["menores"].isna(), np.nan, (df["menores"] > 0).astype(float))
    df["log_monto"] = np.log1p(df["monto"])
    df["monto_por_pax"] = df["monto"] / df["pax"].replace(0, np.nan)
    df["producto_tipo"] = (df["producto"].astype(str)
                           .str.extract(r"^([A-Za-zÁÉÍÓÚáéíóúñÑ]+)", expand=False)
                           .str.lower())
    df["destino_norm"] = (df["destino"].astype(str).str.lower()
                          .str.replace(r"\(.*?\)", "", regex=True).str.strip())
    df["canal"] = df["canal"].astype(str).str.strip().str.lower()
    df["puntos"] = df["puntos"].astype(str).str.strip().str.lower()
    for c in ("canal", "producto_tipo", "destino_norm", "puntos"):
        df[c] = df[c].replace({"nan": np.nan, "none": np.nan, "": np.nan})
    return df


NUMERICAS = ["pax", "con_menores", "log_monto", "monto_por_pax", "dias_hasta_viaje"]
CATEGORICAS = ["canal", "producto_tipo", "destino_norm", "puntos", "mes_viaje"]


def armar_preprocesador(df):
    num = [c for c in NUMERICAS if df[c].notna().any()]
    cat = [c for c in CATEGORICAS if df[c].notna().any()]
    return ColumnTransformer([
        ("num", Pipeline([
            ("imp", SimpleImputer(strategy="median", add_indicator=True)),
            ("esc", StandardScaler())]), num),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="constant", fill_value="sin dato")),
            ("ohe", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=3))]), cat),
    ]), num + cat


def ajustar_prior(p, tasa_real):
    """Corrige la probabilidad a la tasa real de pérdida.
    Sirve para la regresión logística con class_weight='balanced' (que entrena como si
    hubiera 50% de cada clase). Si la tasa real de pérdida es r, se suma log(r / (1 - r))
    al logit."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p)) + np.log(tasa_real / (1 - tasa_real))
    return 1 / (1 + np.exp(-z))


def evaluar(nombre, modelo, X, y, cv):
    proba = cross_val_predict(modelo, X, y, cv=cv, method="predict_proba")[:, 1]
    pred = (proba >= 0.5).astype(int)
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=[1], zero_division=0)
    print(f"\n=== {nombre} ===")
    print(f"Perdida  precisión {p[0]:.2f} | recall {r[0]:.2f} | F1 {f[0]:.2f}")
    if len(set(y)) == 2:
        print(f"AUC {roc_auc_score(y, proba):.2f} | PR-AUC {average_precision_score(y, proba):.2f} "
              f"(azar = {y.mean():.2f})")
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    print(f"Matriz: ganadas bien {tn} | ganadas marcadas perdida {fp} | "
          f"perdidas no detectadas {fn} | perdidas detectadas {tp}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--hoja", default=None)
    ap.add_argument("--dias", type=int, default=30, help="Días sin novedades para contar una cotizada como perdida")
    ap.add_argument("--sin-silencio", action="store_true", help="No contar las cotizadas viejas como perdidas")
    ap.add_argument("--hoy", default=None, help="Fecha de referencia AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--salida", default="cotizadas_riesgo.csv")
    ap.add_argument("--tasa-perdida-real", type=float, default=None,
                    help="Tasa real de pérdida (0 a 1) para ajustar las probabilidades. "
                         "Ej.: 0.19 si solo cuentan las perdidas etiquetadas, 0.50 si todas las cotizadas sin cerrar se perdieron")
    args = ap.parse_args()

    warnings.filterwarnings("ignore")
    hoy = pd.Timestamp(args.hoy) if args.hoy else pd.Timestamp.today().normalize()

    df = preparar(leer(args.archivo, args.hoja), hoy, args.dias, not args.sin_silencio)
    train = df[df["resultado"].isin(["Ganada", "Perdida"])].copy()
    abiertas = df[df["resultado"] == "Cotizada"].copy()

    y = (train["resultado"] == "Perdida").astype(int).to_numpy()
    n_perd, n_gan = int(y.sum()), int((1 - y).sum())
    por_silencio = int((train["origen_perdida"] == "silencio").sum())
    print(f"Casos para entrenar: {len(train)} | Ganadas {n_gan} | Perdidas {n_perd} "
          f"(de ellas por silencio: {por_silencio}) | Abiertas: {len(abiertas)}")
    if min(n_perd, n_gan) < 2:
        sys.exit("Hacen falta al menos 2 casos de cada clase para validar.")
    if n_perd < 30:
        print(f"AVISO: con {n_perd} perdidas los resultados son muy inestables. Usalo como prueba.")

    pre, columnas = armar_preprocesador(train)
    X = train[columnas]
    cv = StratifiedKFold(n_splits=min(5, n_perd, n_gan), shuffle=True, random_state=SEMILLA)

    modelos = {
        "Referencia (siempre la clase más común)": DummyClassifier(strategy="most_frequent"),
        "Regresión logística": Pipeline([("pre", pre), ("m", LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=SEMILLA))]),
        "Árbol (profundidad 3)": Pipeline([("pre", pre), ("m", DecisionTreeClassifier(
            max_depth=3, min_samples_leaf=5, class_weight="balanced", random_state=SEMILLA))]),
    }
    for nombre, modelo in modelos.items():
        if nombre.startswith("Referencia"):
            pred = cross_val_predict(modelo, X, y, cv=cv)
            print(f"\n=== {nombre} ===\nAccuracy {np.mean(pred == y):.2f} (si esto se parece a tus "
                  f"modelos, no aprendieron nada útil)")
        else:
            evaluar(nombre, modelo, X, y, cv)

    # Ajuste final con todos los datos para interpretar y puntuar
    logistica = modelos["Regresión logística"].fit(X, y)
    nombres = logistica.named_steps["pre"].get_feature_names_out()
    coef = pd.Series(logistica.named_steps["m"].coef_[0], index=nombres).sort_values()
    print("\nVariables que más empujan hacia PERDIDA:")
    print(coef.tail(8).iloc[::-1].round(2).to_string())
    print("\nVariables que más empujan hacia GANADA:")
    print(coef.head(8).round(2).to_string())

    arbol = modelos["Árbol (profundidad 3)"].fit(X, y)
    print("\nReglas del árbol:")
    print(export_text(arbol.named_steps["m"],
                      feature_names=list(arbol.named_steps["pre"].get_feature_names_out())))

    if len(abiertas):
        abiertas["prob_perdida"] = logistica.predict_proba(abiertas[columnas])[:, 1]
        columnas_salida = ["id", "prob_perdida"]
        if args.tasa_perdida_real is not None:
            if not 0 < args.tasa_perdida_real < 1:
                sys.exit("--tasa-perdida-real tiene que estar entre 0 y 1.")
            abiertas["prob_perdida_ajustada"] = ajustar_prior(abiertas["prob_perdida"], args.tasa_perdida_real)
            columnas_salida.append("prob_perdida_ajustada")
        salida = abiertas[columnas_salida].sort_values(columnas_salida[-1], ascending=False)
        salida.to_csv(args.salida, index=False)
        print(f"\nGuardé {len(salida)} cotizaciones abiertas con su riesgo en {args.salida}")


if __name__ == "__main__":
    main()
