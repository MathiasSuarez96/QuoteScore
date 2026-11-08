"""Pantalla local: revisar, evaluar y registrar una primera cotización."""
import base64
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import streamlit as st
from extraer_pdf import extraer_pdf
from modelo import cargar_modelo, evaluar, carpeta_privada
from src.data.app_store import guardar, listar, actualizar_resultado

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Predictor de Cotizaciones · TocToc', page_icon='✈️', layout='wide')
today = datetime.now(ZoneInfo('America/Montevideo')).date()
PDF_DEFAULTS=dict(destino='',producto='Paquete',fecha_viaje=None,fecha_regreso=None,pax=None,menores=None,monto=None,moneda='USD',alcance='unknown')
def image_data(name):
    return 'data:image/png;base64,' + base64.b64encode((ROOT/'assets'/name).read_bytes()).decode()

st.markdown('''<style>
.stApp {background:#f3f8ff;color:#172b4d}
.block-container{max-width:1180px;padding-top:2rem}
h1,h2,h3{letter-spacing:-.035em} h1{font-size:2.7rem!important}
[data-testid="stForm"]{background:white;border:1px solid #dfeaf6;border-radius:20px;padding:24px}
.hero{padding:30px 0 22px}.eyebrow{color:#0080ff;font-size:12px;font-weight:700;letter-spacing:2px}
.hero p{color:#60738c;font-size:17px;max-width:700px}.logos{display:flex;align-items:center;gap:30px;background:white;border-radius:18px;padding:18px 24px}
.logos img:first-child{width:138px}.logos img:last-child{width:190px;border-left:1px solid #e0e8f1;padding-left:26px}
.badge{display:inline-block;background:#fff0cc;border-radius:30px;color:#775000;padding:6px 12px;font-size:12px;font-weight:600}
.score{background:white;border:1px solid #dce8f6;border-radius:20px;padding:26px;margin:18px 0}.score h2{margin:8px 0}.score p{color:#60738c}
[data-testid="stMetric"]{background:white;border:1px solid #dfeaf6;border-radius:16px;padding:18px}
.stButton button,.stFormSubmitButton button{border-radius:12px;min-height:44px}
footer{visibility:hidden}
[data-testid="stAppDeployButton"]{display:none}
@media(max-width:600px){.logos{gap:14px;padding:16px}.logos img:first-child{width:110px}.logos img:last-child{width:150px;padding-left:14px}h1{font-size:2rem!important}.hero{padding-top:22px}}
</style>''', unsafe_allow_html=True)
font=ROOT/'assets'/'Poppins-Regular.ttf'
if font.exists():
    encoded=base64.b64encode(font.read_bytes()).decode()
    st.markdown(f'<style>@font-face{{font-family:Poppins;src:url(data:font/ttf;base64,{encoded})}}html,body,[class*="css"],.stApp,h1,h2,h3,p,button,label{{font-family:Poppins,sans-serif!important}}</style>',unsafe_allow_html=True)
st.markdown(f'<div class="logos"><img src="{image_data("toctoc-logo.png")}" alt="TocToc Viajes"><img src="{image_data("santander-logo.png")}" alt="Viajes Soy Santander"></div>',unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="eyebrow">TUS COTIZACIONES, MÁS CLARAS</div><h1>Predictor de Cotizaciones</h1><p>Del PDF al seguimiento. Revisá una propuesta, explorá su posición y guardá lo que sabés desde el primer día.</p><span class="badge">MODELO EXPERIMENTAL · USO LOCAL</span></div>',unsafe_allow_html=True)
try:
    bundle=cargar_modelo()
except (ValueError, OSError) as exc:
    st.error(str(exc)); st.info('Prepará el modelo siguiendo docs/local_app.md.'); st.stop()
root=carpeta_privada()/'store'
if 'token' not in st.session_state:
    st.session_state.token=str(uuid4())
if 'upload_generation' not in st.session_state:
    st.session_state.upload_generation=0

tab,history,about=st.tabs(['✦  Evaluar cotización','↗  Mis oportunidades','ⓘ  Sobre el modelo'])
with tab:
    left,right=st.columns([1.1,1.9],gap='large')
    with left:
        st.subheader('01 · Cargá tu propuesta')
        st.write('Un PDF de texto alcanza para empezar. Vos confirmás los datos antes de evaluar.')
        uploaded=st.file_uploader('PDF de cotización',type=['pdf'],key=f'pdf_{st.session_state.upload_generation}')
        if st.button('Leer PDF',disabled=uploaded is None,use_container_width=True):
            try:
                with st.spinner('Leyendo el PDF en esta computadora…'):
                    extracted=extraer_pdf(uploaded.getvalue())
                for key,value in PDF_DEFAULTS.items():
                    st.session_state['f_'+key]=value
                st.session_state.f_confirmed=False
                st.session_state.f_puntos=None
                for key,value in extracted.campos.items():
                    st.session_state['f_'+key]=value
                st.session_state.pdf_warnings=extracted.avisos
                st.session_state.pdf_fields=list(extracted.campos)
                # Compatibilidad con objetos creados antes de una recarga del módulo.
                st.session_state.pdf_prices=getattr(extracted,'opciones_precio',[])
                st.session_state.pop('pdf_price_choice',None)
                st.session_state.upload_generation+=1
                st.session_state.pop('prediction',None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        st.caption('El PDF se procesa en memoria. No se guarda ni se envía a servicios externos. No hay OCR para capturas o escaneos.')
        if 'pdf_fields' in st.session_state:
            labels=dict(destino='destino',producto='producto',fecha_viaje='salida',fecha_regreso='regreso',pax='pasajeros',menores='menores',monto='monto',moneda='moneda',alcance='alcance del precio',puntos='puntos')
            detected=st.session_state.pdf_fields
            if detected:
                st.success('PDF leído. Datos cargados: '+', '.join(labels.get(k,k) for k in detected)+'.')
            else:
                st.warning('PDF procesado, pero no se reconocieron campos. Completá el formulario manualmente.')
            missing=[labels[k] for k in ('destino','producto','fecha_viaje','pax','menores','monto') if k not in detected]
            if missing:st.caption('No se pudo leer: '+', '.join(missing)+'.')
            st.info('Ahora revisá los datos completados, agregá los pendientes, confirmá la primera propuesta y pulsá Evaluar. Leer PDF no ejecuta el modelo.')
            st.caption('El archivo se retiró del cargador después de leerlo. Para leer otro, usá Upload.')
        for warning in st.session_state.get('pdf_warnings',[]):
            st.info(warning)
        prices=st.session_state.get('pdf_prices',[])
        if prices:
            choice=st.selectbox('Elegí el total de la alternativa',list(range(len(prices))),index=None,format_func=lambda i:f'Opción {i+1}: {prices[i]["moneda"]} {prices[i]["monto"]:,.2f}',key='pdf_price_choice')
            if st.button('Usar este precio',disabled=choice is None):
                for key,value in prices[choice].items():st.session_state['f_'+key]=value
                st.success('Precio cargado en el formulario.')
        if st.button('Nueva cotización',use_container_width=True):
            defaults=dict(PDF_DEFAULTS,fecha_cotizacion=today,canal=None,puntos=None,confirmed=False)
            for key,value in defaults.items():st.session_state['f_'+key]=value
            for key in ('prediction','pdf_warnings','pdf_fields','pdf_prices','pdf_price_choice','saved'):st.session_state.pop(key,None)
            st.session_state.token=str(uuid4());st.session_state.upload_generation+=1;st.rerun()
        st.caption('Una evaluación representa una opción de la primera propuesta. No ingreses nombres, teléfonos ni localizadores.')
    with right:
        st.subheader('02 · Revisá los datos')
        with st.form('quote'):
            dest=st.text_input('Destino',key='f_destino',placeholder='Ej. Punta Cana',max_chars=120)
            a,b=st.columns(2)
            prod=a.selectbox('Producto',['Paquete','Pasaje','Hotel','Crucero','Mixto','Servicio'],key='f_producto')
            sent=b.date_input('Primera cotización enviada',value=today,max_value=today,key='f_fecha_cotizacion',format='DD/MM/YYYY')
            st.caption('Hoy viene seleccionado. Si cargás una propuesta anterior, indicá su fecha real de envío.')
            a,b=st.columns(2)
            departure=a.date_input('Salida (opcional)',value=None,key='f_fecha_viaje',format='DD/MM/YYYY')
            returning=b.date_input('Regreso (opcional)',value=None,key='f_fecha_regreso',format='DD/MM/YYYY')
            a,b=st.columns(2)
            pax=a.number_input('Pasajeros totales',min_value=1,max_value=999,value=None,step=1,key='f_pax')
            minors=b.number_input('Menores incluidos',min_value=0,max_value=999,value=None,step=1,key='f_menores')
            a,b=st.columns(2)
            channel=a.selectbox('Canal · completar manualmente',[None]+bundle['known_channels'],format_func=lambda v:v.capitalize() if v else 'Sin dato',key='f_canal')
            points=b.selectbox('¿Usa puntos? · revisar sugerencia',[None,'Sí','No','Pocos'],format_func=lambda v:v or 'Sin dato',key='f_puntos')
            with st.expander('Precio inicial · solo para el registro'):
                amount=st.number_input('Monto cotizado (opcional)',value=None,min_value=0.01,key='f_monto')
                currency=st.selectbox('Moneda',['USD','EUR','UYU'],key='f_moneda')
                scope=st.selectbox('Alcance',['unknown','group','per_person'],format_func=lambda v:{'unknown':'Sin confirmar','group':'Total del grupo','per_person':'Por persona'}[v],key='f_alcance')
                st.caption('Este modelo no usa el monto. Nunca reemplaces el precio inicial por el de venta.')
            confirmed=st.checkbox('Confirmo que son datos de la primera propuesta con precio.',key='f_confirmed')
            a,b=st.columns(2)
            run=a.form_submit_button('Evaluar',use_container_width=True)
            save=b.form_submit_button('Evaluar y guardar',type='primary',use_container_width=True)
        if run or save:
            datos=dict(destino=dest.strip(),producto=prod,fecha_cotizacion=sent.isoformat(),fecha_viaje=departure.isoformat() if departure else None,fecha_regreso=returning.isoformat() if returning else None,pax=pax,menores=minors,canal=channel,puntos=points,monto=amount,moneda=currency,alcance=scope,primera_confirmada=confirmed)
            try:
                prediction=evaluar(datos,bundle)
                st.session_state.prediction=prediction
                if save:
                    oid,created=guardar(root,datos,prediction,st.session_state.token)
                    st.success('Cotización guardada como abierta.' if created else 'Esta cotización ya estaba guardada; no se duplicó.')
            except (ValueError,OSError) as exc:
                st.session_state.pop('prediction',None);st.error(str(exc))
    if st.session_state.get('prediction'):
        p=st.session_state.prediction
        color={'Bajo':'#16845a','Medio':'#ad7100','Alto':'#cd4343'}[p['level']]
        titulo,explicacion,sugerencia={
            'Alto':('Riesgo alto de no concretarse','El modelo ubica esta propuesta entre las de mayor riesgo de no terminar en venta. No significa que esté perdida.','Preguntale al cliente qué necesita para avanzar y acordá cuándo volver a hablar. No descartes la oportunidad por este color.'),
            'Medio':('Riesgo intermedio de no concretarse','El modelo ubica esta propuesta en una posición intermedia: no da una señal clara a favor ni en contra de la venta.','Confirmá si la propuesta se ajusta a lo que busca el cliente y acordá un próximo paso.'),
            'Bajo':('Riesgo bajo de no concretarse','Es la señal más favorable del semáforo: el modelo ve menos riesgo que en otras propuestas. No significa que la venta esté asegurada.','Mantené el seguimiento y consultá si necesita algo para decidir. No la marques como ganada hasta que la venta esté confirmada.')
        }[p['level']]
        st.markdown(f'<div class="score"><div class="eyebrow">¿QUÉ SIGNIFICA PARA VOS?</div><h2 style="color:{color}">● {titulo}</h2><p>{explicacion}</p><h3>Cómo seguir la conversación</h3><p>{sugerencia}</p></div>',unsafe_allow_html=True)
        st.caption('Las sugerencias son pautas generales de atención; el modelo no identifica por qué un cliente compraría o dejaría de comprar.')
        st.warning('Herramienta en prueba: el color es orientativo, no garantiza una venta ni una pérdida. Usá también lo que te cuenta el cliente. Si cambiás los datos, volvé a evaluar.')
        with st.expander('Ver cómo se calculó el color'):
            st.write(f'El riesgo calculado supera al de {p["below"]} de las {p["total"]} cotizaciones de referencia ({p["percentile"]:.0f}%). No es un porcentaje de probabilidad de pérdida. Referencia al {p["reference_cutoff"]}.')
            st.caption('Bajo, medio y alto representan tres tramos de posición relativa. Todavía no están validados para decisiones comerciales.')
        for warning in p['warnings']:st.info(warning)
with history:
    st.subheader('El seguimiento empieza acá')
    rows=listar(root)
    a,b,c=st.columns(3)
    a.metric('Abiertas',sum(r['resultado']=='Abierta' for r in rows));b.metric('Ganadas',sum(r['resultado']=='Ganada' for r in rows));c.metric('Perdidas',sum(r['resultado']=='Perdida' for r in rows))
    if not rows:
        st.info('Todavía no guardaste cotizaciones en esta app. Tus registros históricos se conservan por separado.')
    else:
        st.dataframe(rows,use_container_width=True,hide_index=True)
        with st.form('outcome'):
            selected=st.selectbox('Oportunidad',rows,format_func=lambda r:f'{r["fecha_cotizacion"]} · {r["destino"]} · {r["id"][-6:]}')
            a,b=st.columns(2)
            state=a.selectbox('Resultado',['Ganada','Perdida','Abierta'])
            when=b.date_input('Fecha del resultado',value=today,max_value=today)
            reason=st.selectbox('Confirmación',['Venta confirmada','Cliente confirmó que no compra','Reactivación confirmada'])
            if st.form_submit_button('Guardar resultado',type='primary'):
                try:
                    expected={'Ganada':'Venta confirmada','Perdida':'Cliente confirmó que no compra','Abierta':'Reactivación confirmada'}[state]
                    if reason!=expected:raise ValueError('Elegí la confirmación correspondiente al resultado.')
                    actualizar_resultado(root,selected['id'],state,when.isoformat(),reason)
                    st.rerun()
                except (ValueError,OSError) as exc:st.error(str(exc))
        st.caption('El resultado conserva su historial y no modifica los datos de la primera cotización. El silencio no marca automáticamente una pérdida en esta app.')
with about:
    meta=bundle['metadata']
    st.subheader('Una prueba para aprender')
    st.write(f'Regresión logística · {meta["training_rows"]} casos históricos · {meta["reference_count"]} abiertas de referencia.')
    st.write('El semáforo divide la posición relativa en tres tramos: bajo (menos de 33⅓), medio y alto (desde 66⅔). No son umbrales comerciales.')
    for limitation in meta['limitations']:st.write('• '+limitation)
    st.write('Guardar nuevas oportunidades no reentrena el modelo. Primero habrá que revisar sus resultados y validar una nueva versión.')
    st.caption('Código: app.py = pantalla; extraer_pdf.py = sugerencias del PDF; modelo.py = carga y evaluación. Los CSV y el modelo quedan fuera del repositorio.')
st.caption('TocToc Viajes · Prototipo local de QuoteScore · Tus datos permanecen en esta computadora')
