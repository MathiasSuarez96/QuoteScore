"""Captura de la app sobre el Store versionado existente; CSV e historial atómicos."""
import json
from datetime import date

from .store import Store, now, stable_id, json_text
from .schema import fields

PRODUCTOS = {'Pasaje':'flight_only', 'Hotel':'hotel_only', 'Paquete':'package',
             'Mixto':'mixed', 'Crucero':'cruise', 'Servicio':'other'}


def row(tabla, **values):
    return {key: values.get(key) for key in fields(tabla)}


def guardar(root, datos, prediccion, token):
    from modelo import validar_entrada
    validar_entrada(datos)
    store = Store(root, 'private')
    oid, qid, optid, sid = [stable_id(prefix, token) for prefix in ('O_APP','Q_APP','OPT_APP','S_APP')]
    timestamp = now()
    with store.locked():
        tables = store.read()
        existing = next((r for r in tables['reconciliation_log'] if r['decision_id'] == stable_id('SAVE', token)), None)
        if existing:
            if json.loads(existing['after_json'])['input'] != datos:
                raise ValueError('Esta oportunidad ya está guardada. Usá Nueva cotización para otro registro; no se sobrescribió la propuesta inicial.')
            return oid, False
        tables['sources'].append(row('sources',source_id=sid,source_type='user_confirmation',sanitized_reference='app/formulario-revisado',document_date=timestamp[:10],imported_at=timestamp,evidence_level='user_confirmation'))
        tables['opportunities'].append(row('opportunities',opportunity_id=oid,created_at=datos['fecha_cotizacion'],status='open',converted=None,initial_destination=datos['destino'],requested_scope_initial=PRODUCTOS[datos['producto']],exclude_from_training='0',review_status='pending'))
        original_canal=(datos.get('canal') or '').lower()
        canal = 'whatsapp' if 'whatsapp' in original_canal else 'web' if 'web' in original_canal else 'other' if original_canal else None
        tables['quotes'].append(row('quotes',quote_id=qid,opportunity_id=oid,sent_at=datos['fecha_cotizacion'],date_precision='day',version_number='1',first_priced_quote_status='confirmed',channel_at_quote=canal,source_id=sid))
        tables['quote_options'].append(row('quote_options',option_id=optid,quote_id=qid,option_order='1',product_scope=PRODUCTOS[datos['producto']],destination_summary=datos['destino'],departure_date=datos.get('fecha_viaje'),return_date=datos.get('fecha_regreso'),passengers=str(datos['pax']) if datos.get('pax') is not None else None,children=str(datos['menores']) if datos.get('menores') is not None else None,currency=datos.get('moneda'),price_scope=datos.get('alcance','unknown'),gross_price=str(datos['monto']) if datos.get('monto') is not None else None,source_id=sid))
        # Solo los valores aportados tienen evidencia; no convertir faltantes en ceros.
        for tabla, entity, key in [('quotes',tables['quotes'][-1],'quote_id'),('quote_options',tables['quote_options'][-1],'option_id')]:
            for name, value in entity.items():
                if value is not None and name not in (key,'source_id','quote_id','opportunity_id'):
                    tables['field_evidence'].append(row('field_evidence',evidence_id=stable_id('E',token,tabla,name),entity_type=tabla,entity_id=entity[key],field_name=name,source_id=sid,locator='app/campos-revisados',known_at=datos['fecha_cotizacion'],time_precision='day',review_status='verified'))
        tables['reconciliation_log'].append(row('reconciliation_log',decision_id=stable_id('SAVE',token),source_record_id=qid,opportunity_id=oid,decision_type='app_capture',rationale='Primera propuesta confirmada por el usuario; opción evaluada, no todas las alternativas del viaje',evidence_source_id=sid,decided_at=timestamp,after_json=json_text({'input':datos,'evaluation':prediccion,'recorded_at':timestamp})))
        store.commit(tables)
    return oid, True


def listar(root):
    tables = Store(root, 'private').read()
    captures = {r['opportunity_id']:json.loads(r['after_json']) for r in tables['reconciliation_log'] if r['decision_type']=='app_capture'}
    result=[]
    for opportunity in tables['opportunities']:
        oid=opportunity['opportunity_id']
        if oid not in captures:
            continue
        cap=captures[oid]
        datos=cap['input']
        result.append(dict(id=oid,fecha_cotizacion=datos['fecha_cotizacion'],destino=datos['destino'],producto=datos['producto'],pasajeros=datos.get('pax'),resultado={'open':'Abierta','won':'Ganada','lost':'Perdida'}[opportunity['status']],fecha_resultado=opportunity.get('outcome_at'),nivel=(cap.get('evaluation') or {}).get('level','Sin evaluar'),modelo=(cap.get('evaluation') or {}).get('model_version','')))
    return list(reversed(result))


def actualizar_resultado(root, oid, estado, fecha, motivo):
    if estado not in ('Ganada','Perdida','Abierta') or not motivo:
        raise ValueError('Elegí un resultado y su fundamento.')
    event_date=date.fromisoformat(fecha)
    if event_date>date.today():
        raise ValueError('El resultado no puede tener fecha futura.')
    from .review_cases import update_outcome
    store=Store(root,'private')
    tables=store.read()
    op=next((r for r in tables['opportunities'] if r['opportunity_id']==oid),None)
    if op is None:
        raise ValueError('No se encontró la oportunidad.')
    first=next(q for q in tables['quotes'] if q['opportunity_id']==oid)
    if fecha<first['sent_at'][:10]:
        raise ValueError('El resultado no puede ser anterior a la cotización.')
    status={'Ganada':'won','Perdida':'lost','Abierta':'open'}[estado]
    if op['status']==status and (op.get('outcome_at') or '')==fecha:
        return False
    # ID por revisión evita duplicación de doble clic, pero permite reactivación posterior.
    revision=(store.root/'CURRENT').read_text().strip()
    prior=next((r for r in reversed(tables['outcome_history']) if r['opportunity_id']==oid),None)
    update_outcome(store,oid,status,fecha,first['source_id'],motivo,
                   stable_id('APP_OUTCOME',oid,status,fecha,revision),
                   supersedes=prior['outcome_event_id'] if prior else None)
    return True
