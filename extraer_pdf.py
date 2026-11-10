"""Sugerencias conservadoras desde un PDF de texto. No guarda bytes ni texto crudo."""
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
import re
import unicodedata

from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 15
DESTINOS = ('Arraial do Cabo', 'Porto de Galinhas', 'Playa del Carmen', 'Punta del Este', 'Puerto Plata',
            'Río de Janeiro', 'Rio de Janeiro', 'Buenos Aires', 'Ciudad de México',
            'Nueva York', 'New York', 'Punta Cana', 'Bayahibe', 'Florianópolis',
            'Porto Alegre', 'Porto Seguro', 'Praia do Forte', 'Ilha Grande',
            'Hong Kong', 'Chengdu', 'Cartagena', 'Cancún', 'Curazao', 'Aruba',
            'Miami', 'Naples', 'Madrid', 'Panamá', 'Mendoza', 'Salta', 'Natal',
            'Salvador', 'Maceió', 'Maragogi', 'Jericoacoara', 'San Andrés', 'Recife',
            'Orlando', 'Barcelona', 'Santiago', 'Puerto Varas', 'Ushuaia', 'Córdoba')


@dataclass
class Extraccion:
    campos: dict = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    paginas: int = 0
    texto_disponible: bool = False
    opciones_precio: list[dict] = field(default_factory=list)


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c))


def importe(texto):
    s = texto.replace(' ', '')
    if ',' in s and '.' in s:
        decimal = ',' if s.rfind(',') > s.rfind('.') else '.'
        s = s.replace('.' if decimal == ',' else ',', '').replace(decimal, '.')
    elif ',' in s or '.' in s:
        sep = ',' if ',' in s else '.'
        s = s.replace(sep, '' if len(s.split(sep)[-1]) == 3 else '.')
    return float(s)


def extraer_texto(texto: str) -> Extraccion:
    """Solo devuelve campos comerciales acotados, nunca nombres, notas o localizadores."""
    resultado = Extraccion(texto_disponible=bool(texto.strip()))
    if len(texto.strip()) < 25:
        resultado.avisos.append('No se encontró texto suficiente. Puede ser un PDF escaneado: completá el formulario manualmente.')
        return resultado
    normal = normalizar(texto)
    # El encabezado identifica el destino del viaje; el cuerpo puede mencionar aeropuertos y escalas.
    cabecera = normal[:600].split('¿por que')[0]
    # No elegir una alternativa automáticamente cuando el PDF contiene varias.
    multiples = len(re.findall(r'\b(?:opcion|alternativa)\s*(?:\d+|[a-d])\b', normal)) > 1
    if multiples:
        resultado.avisos.append('Hay varias alternativas. Elegí una propuesta inicial para esta prueba; no se seleccionaron precios, pasajeros ni fechas automáticamente.')
    encontrados = []
    for destino in DESTINOS:
        if re.search(r'(?<!\w)' + re.escape(normalizar(destino)) + r'(?!\w)', normal):
            if normalizar(destino) not in [normalizar(d) for d in encontrados]:
                encontrados.append(destino)
    encabezado = [d for d in encontrados if normalizar(d) in cabecera]
    if len(encabezado) == 1:
        resultado.campos['destino'] = encabezado[0]
    elif len(encontrados) == 1:
        resultado.campos['destino'] = encontrados[0]
    elif encontrados:
        resultado.avisos.append('Se mencionan varios destinos: ' + ', '.join(encontrados) + '. Confirmá cuál corresponde; puede haber escalas.')
    else:
        resultado.avisos.append('No se reconoció un destino del catálogo. Ingresalo manualmente.')
    for patron, producto in ((r'\bpaquete\b', 'Paquete'), (r'\bsolo (?:aereo|vuelo|pasaje)\b', 'Pasaje'),
                              (r'\bsolo (?:hotel|alojamiento)\b', 'Hotel'), (r'\bcrucero\b', 'Crucero')):
        if re.search(patron, normal):
            resultado.campos['producto'] = producto
            break
    if not multiples:
        for key, patron in [('pax', r'\b(?:pasajeros|pax)\s*[:=]?\s*(\d{1,3})\b'),
                            ('menores', r'\b(?:menores|ninos)\s*[:=]?\s*(\d{1,2})\b')]:
            matches = {int(v) for v in re.findall(patron, normal)}
            if not matches:
                word = 'pasajeros|pax' if key == 'pax' else 'menores|ninos'
                matches = {int(v) for v in re.findall(r'\b(\d{1,3})\s*(?:' + word + r')\b', normal)}
            if len(matches) == 1:
                resultado.campos[key] = matches.pop()
        adultos = {int(v) for v in re.findall(r'\b(\d{1,3})\s*adultos\b', normal)}
        if len(adultos) == 1 and 'menores' in resultado.campos and 'pax' not in resultado.campos:
            resultado.campos['pax'] = adultos.pop() + resultado.campos['menores']
        # No adivinar años, ni usar fechas de emisión/contacto como fecha de envío.
        for key, etiqueta in [('fecha_viaje', r'salida|fecha de viaje|inicio del viaje|check[ -]?in'),
                               ('fecha_regreso', r'regreso|retorno|check[ -]?out')]:
            vals = re.findall(r'\b(?:' + etiqueta + r')\s*[:=]?\s*(\d{1,2}/\d{1,2}/\d{4})', normal)
            if len(set(vals)) == 1:
                try:
                    resultado.campos[key] = datetime.strptime(vals[0], '%d/%m/%Y').date()
                except ValueError:
                    resultado.avisos.append('Una fecha no es válida; revisala manualmente.')
        prices = re.findall(r'\b(?:precio|importe|monto)\s+(total|por persona)\s*[:=]?\s*(USD|EUR|UYU)\s*([\d][\d., ]*)', texto, re.I)
        if len(prices) == 1:
            scope, currency, value = prices[0]
            try:
                resultado.campos.update(monto=importe(value.strip()), moneda=currency.upper(),
                                        alcance='group' if scope.lower() == 'total' else 'per_person')
            except ValueError:
                resultado.avisos.append('El precio no se pudo interpretar; completalo manualmente.')
        elif len(prices) > 1:
            resultado.avisos.append('Hay varios precios explícitos. No se eligió uno automáticamente.')
    if resultado.campos.get('pax') == 0:
        resultado.campos.pop('pax')
        resultado.avisos.append('La cantidad de pasajeros necesita revisión.')
    enriquecer_plantilla(texto, resultado)
    resultado.avisos.append('Revisá las sugerencias. Canal y fecha de primera cotización no se deducen del contacto del asesor ni de la fecha del archivo.')
    return resultado


def enriquecer_plantilla(texto, resultado):
    """Campos globales del encabezado y precios explícitos, sin usar información personal."""
    normal=normalizar(texto)
    header=normal[:650].split('¿por que')[0]
    campos=resultado.campos
    meses={m:i+1 for i,m in enumerate(('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'))}
    ranges=[]
    for m in re.finditer(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+al\s+(\d{1,2})/(\d{1,2})/(\d{4})\b',header):
        d1,mo1,y1,d2,mo2,y2=m.groups()
        year1=int(y1) if y1 else int(y2)-(int(mo1)>int(mo2))
        ranges.append((year1,int(mo1),int(d1),int(y2),int(mo2),int(d2)))
    for m in re.finditer(r'\b(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+('+'|'.join(meses)+r')(?:\s+de)?\s*(\d{4})?',header):
        d1,d2,month,year=m.groups()
        # Año omitido en rango: solo el año único del encabezado, nunca el reloj actual.
        years=set(re.findall(r'\b20\d{2}\b',header))
        year=year or (next(iter(years)) if len(years)==1 else None)
        if year:ranges.append((int(year),meses[month],int(d1),int(year),meses[month],int(d2)))
    if len(set(ranges))==1:
        try:
            y,m,d,yy,mm,dd=ranges[0]
            start,end=datetime(y,m,d).date(),datetime(yy,mm,dd).date()
            if end>=start:campos.update(fecha_viaje=start,fecha_regreso=end)
        except ValueError:resultado.avisos.append('El rango de fechas requiere revisión.')
    elif len(set(ranges))>1:
        campos.pop('fecha_viaje',None);campos.pop('fecha_regreso',None)
        resultado.avisos.append('Hay varios rangos de viaje: confirmá las fechas.')
    totals={int(x) for x in re.findall(r'\b(\d{1,3})[ \t]+pasajeros\b',header)}
    adults={int(x) for x in re.findall(r'\b(\d{1,3})[ \t]+adultos?\b',header)}
    children={int(x) for x in re.findall(r'\b(\d{1,2})[ \t]+(?:menores?|ninos?|ninas?)\b',header)}
    if len(totals)==1:campos['pax']=next(iter(totals))
    if len(children)==1:campos['menores']=next(iter(children))
    if len(adults)==1:
        adult=next(iter(adults))
        if len(children)==1:campos['pax']=adult+next(iter(children))
        elif not totals or totals=={adult}:
            campos.update(pax=adult,menores=0)
    # Beneficio genérico no prueba que este cliente use puntos.
    if re.search(r'\b(?:con\s+)?tus\s+[\d.,]+\s+puntos\b',normal):
        campos['puntos']='Sí'
        resultado.avisos.append('Se detectó una propuesta con puntos del cliente; confirmá si usará ese beneficio.')
    elif re.search(r'\b(?:sin puntos|no usa puntos)\b',header):campos['puntos']='No'
    if 'paquete' in normal and re.search(r'\b(?:incluye|incluido|inversion|costo)\b',normal):campos['producto']='Paquete'
    # Priorizar total bruto del paquete. No confundir saldo con puntos, extras o cuota con precio inicial.
    pattern=r'(?m)^\s*(?:costo\s+)?total(?:\s+del\s+paquete)?(?:\s*[·:]\s*\d+\s+pasajeros|\s+para\s+los\s+\d+)?\s*\n\s*(USD|EUR|UYU)\s*([\d][\d.,]*)'
    matches=list(re.finditer(pattern,texto,re.I))
    prices=[]
    for match in matches:
        value=importe(match.group(2));currency=match.group(1).upper()
        if value<=0:continue
        item={'monto':value,'moneda':currency,'alcance':'group'}
        if item not in prices:prices.append(item)
    if len(prices)==1:campos.update(prices[0])
    elif len(prices)>1:
        for key in ('monto','moneda','alcance'):campos.pop(key,None)
        resultado.opciones_precio=prices
        resultado.avisos.append('Hay varios precios totales. Elegí el de la alternativa que querés evaluar.')
    if prices and re.search(r'saldo a pagar|total a abonar|con puntos(?:[^:\n]*)?:',normal):
        resultado.avisos.append('El precio sugerido es el total antes del descuento por puntos; el saldo a abonar no lo reemplaza.')
    if 'fecha_regreso' in campos:
        resultado.avisos.append('Regreso usa el final del rango de viaje del encabezado; la llegada a origen puede ser al día siguiente.')


def extraer_pdf(contenido: bytes) -> Extraccion:
    if len(contenido) > MAX_BYTES:
        raise ValueError('El PDF supera el límite de 10 MB.')
    if not contenido.startswith(b'%PDF-'):
        raise ValueError('El archivo no tiene una cabecera PDF válida.')
    try:
        reader = PdfReader(BytesIO(contenido))
        if reader.is_encrypted:
            raise ValueError('El PDF está protegido. Usá una copia sin contraseña o completá los datos manualmente.')
        if len(reader.pages) > MAX_PAGES:
            raise ValueError('Usá un PDF de hasta 15 páginas.')
        partes = []
        for page in reader.pages:
            stream = page.get_contents()
            if stream and len(stream.get_data()) > 8 * 1024 * 1024:
                raise ValueError('Una página es demasiado compleja para esta extracción local.')
            partes.append(page.extract_text() or '')
        result = extraer_texto('\n'.join(partes))
        result.paginas = len(reader.pages)
        return result
    except ValueError:
        raise
    except Exception as exc:
        # No mostrar texto del documento ni detalles internos que puedan contener PII.
        raise ValueError('No se pudo leer este PDF. Probá otro archivo o cargá los datos manualmente.') from exc
