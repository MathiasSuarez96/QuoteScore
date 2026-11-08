"""Demo reproducible: datos inventados y registros solo en la sesión del visitante."""
from copy import deepcopy
from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from tools.entrenar_modelo_cotizaciones import preparar, armar_preprocesador
from modelo import validar_entrada


@st.cache_resource
def cargar_demo():
    # No lee archivos, datasets, modelos ni variables de la instalación privada.
    rng=np.random.default_rng(4217)
    rows=[]
    for i in range(240):
        lead=int(rng.integers(5,180));pax=int(rng.integers(1,7))
        product=str(rng.choice(['Paquete','Pasaje','Hotel']))
        channel=str(rng.choice(['web','whatsapp','referido']))
        # Regla deliberadamente artificial, con ruido, únicamente para mostrar el flujo.
        latent=-.6+.6*(product=='Paquete')+.35*(channel=='web')-.008*(lead-60)+.12*(pax-2)
        lost=rng.random()<1/(1+np.exp(-latent))
        quoted=date(2025,1,1)+timedelta(days=int(rng.integers(0,300)))
        rows.append(dict(id=f'DEMO{i}',resultado='Perdida' if lost else 'Ganada',
            fecha_cotizacion=quoted.strftime('%d/%m/%Y'),fecha_ultimo_contacto=np.nan,
            fecha_viaje=(quoted+timedelta(days=lead)).strftime('%d/%m/%Y'),
            canal=channel,producto=product,destino=str(rng.choice(['Aruba','Punta Cana','Río de Janeiro'])),
            pax=pax,menores=int(rng.integers(0,min(pax,3))),monto=np.nan,
            puntos=str(rng.choice(['Sí','No']))))
    frame=preparar(pd.DataFrame(rows),pd.Timestamp('2026-01-01'),30,False)
    train=frame.iloc[:200];reference=frame.iloc[200:]
    pre,columns=armar_preprocesador(train)
    pipe=Pipeline([('pre',pre),('m',LogisticRegression(class_weight='balanced',max_iter=2000,random_state=42))])
    pipe.fit(train[columns],train.resultado.eq('Perdida').astype(int))
    return dict(pipeline=pipe,columns=columns,reference=pipe.predict_proba(reference[columns])[:,1].tolist(),
        known_destinations=sorted(train.destino_norm.unique().tolist()),known_channels=['web','whatsapp','referido'],
        metadata=dict(model_version='demo-sintetica-v1',synthetic=True,training_rows=200,reference_count=40,cutoff='2026-01-01',
            limitations=['Datos y resultados completamente inventados.',
                        'El semáforo demuestra el funcionamiento técnico, no estima ventas reales.',
                        'No se publican métricas de precisión comercial.']))


def ejemplos(hoy):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    choices=[('Escapada a Río','Río de Janeiro',3,1,30,2100),
             ('Vacaciones en Aruba','Aruba',2,0,90,3200),
             ('Familia en Punta Cana','Punta Cana',4,2,120,4600)]
    result={}
    for label,destination,pax,kids,lead,amount in choices:
        start=hoy+timedelta(days=lead);end=start+timedelta(days=7)
        buffer=BytesIO();canvas=Canvas(buffer,pagesize=(595,842))
        canvas.setTitle('QuoteScore - ejemplo ficticio')
        for index,line in enumerate(['QUOTESCORE · DEMO FICTICIA',destination,'Paquete: aéreo + hotel',
            f'Salida: {start:%d/%m/%Y}',f'Regreso: {end:%d/%m/%Y}',f'Pasajeros: {pax}',f'Menores: {kids}',
            f'Precio total: USD {amount}', 'Sin datos de clientes. No es una oferta comercial.']):
            canvas.drawString(40,790-index*28,line)
        canvas.save();result[label]=buffer.getvalue()
    return result


def guardar_demo(_root,datos,prediccion,token):
    validar_entrada(datos)
    records=st.session_state.setdefault('demo_records',{})
    if token in records:
        if records[token]['input']!=datos:raise ValueError('Ya guardaste esta propuesta. Usá Nueva cotización para crear otra.')
        return token,False
    if len(records)>=50:raise ValueError('Límite de 50 ejemplos por sesión. Reiniciá la demo para comenzar otra prueba.')
    records[token]=dict(input=deepcopy(datos),prediction=deepcopy(prediccion),resultado='Abierta',fecha_resultado=None,historial=[])
    return token,True


def listar_demo(_root):
    return [dict(id=token,fecha_cotizacion=r['input']['fecha_cotizacion'],destino=r['input']['destino'],
        producto=r['input']['producto'],pasajeros=r['input'].get('pax'),resultado=r['resultado'],
        fecha_resultado=r['fecha_resultado'],nivel=r['prediction']['level'],modelo='demo-sintetica-v1')
        for token,r in reversed(list(st.session_state.get('demo_records',{}).items()))]


def actualizar_demo(_root,oid,estado,fecha,motivo):
    r=st.session_state.get('demo_records',{}).get(oid)
    if r is None:raise ValueError('El ejemplo ya no está en esta sesión.')
    if estado not in ('Ganada','Perdida','Abierta'):raise ValueError('Estado inválido.')
    when=date.fromisoformat(fecha)
    if fecha<r['input']['fecha_cotizacion'] or when>date.today():raise ValueError('Revisá la fecha del resultado.')
    if r['fecha_resultado'] and fecha<r['fecha_resultado']:raise ValueError('La fecha no puede preceder al último resultado.')
    r['historial'].append(dict(estado=estado,fecha=fecha,motivo=motivo))
    r.update(resultado=estado,fecha_resultado=fecha)
