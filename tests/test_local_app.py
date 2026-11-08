"""Fixtures artificiales; ninguna cotización o PDF real en el repositorio."""
import copy
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from extraer_pdf import extraer_pdf
from modelo import validar_entrada
from src.data.app_store import guardar,listar,actualizar_resultado
from src.data.store import Store
from src.data.validate_data import validate

def pdf(text=''):
    writer=PdfWriter(); page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content=DecodedStreamObject();content.set_data(('BT /F1 12 Tf 30 750 Td '+ ' '.join('('+line+') Tj 0 -20 Td' for line in text.splitlines())+' ET').encode('latin1'))
    page[NameObject('/Contents')]=writer._add_object(content)
    stream=BytesIO();writer.write(stream);return stream.getvalue()

class LocalAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'store'
        self.d=dict(destino='Aruba',producto='Paquete',fecha_cotizacion='2026-01-01',fecha_viaje='2026-12-01',fecha_regreso=None,pax=2,menores=0,canal='whatsapp toctoc',puntos='No',monto=None,moneda='USD',alcance='unknown',primera_confirmada=True)
    def tearDown(self):self.tmp.cleanup()
    def test_pdf_one_option(self):
        e=extraer_pdf(pdf('Paquete Aruba\nPasajeros: 2\nMenores: 0\nSalida: 01/12/2026\nPrecio total: USD 1.500,50'))
        self.assertEqual(e.campos['destino'],'Aruba');self.assertEqual(e.campos['pax'],2);self.assertEqual(e.campos['monto'],1500.5)
        self.assertNotIn('canal',e.campos);self.assertNotIn('fecha_cotizacion',e.campos)
    def test_pdf_multiple_options(self):
        e=extraer_pdf(pdf('Opcion 1 Paquete Aruba\nPrecio total: USD 1500\nOpcion 2 Paquete Cancun\nPrecio total: USD 1600'))
        self.assertNotIn('monto',e.campos);self.assertNotIn('destino',e.campos)
    def test_pdf_no_text(self):
        e=extraer_pdf(pdf());self.assertFalse(e.campos);self.assertTrue(e.avisos)
    def test_bad_file(self):
        with self.assertRaises(ValueError):extraer_pdf(b'not a PDF')
    def test_confirm_first(self):
        with self.assertRaises(ValueError):validar_entrada(dict(self.d,primera_confirmada=False))
    def test_save_idempotent_snapshot_and_outcomes(self):
        oid,created=guardar(self.root,self.d,{'level':'Medio'},'fixture1');self.assertTrue(created)
        self.assertFalse(guardar(self.root,self.d,{'level':'Medio'},'fixture1')[1])
        with self.assertRaises(ValueError):guardar(self.root,dict(self.d,pax=3),{},'fixture1')
        before=Store(self.root,'private').read()
        errors=[r for r in validate(before) if r['severity']=='error']
        self.assertEqual(errors,[])
        actualizar_resultado(self.root,oid,'Ganada','2026-02-01','Venta confirmada')
        actualizar_resultado(self.root,oid,'Abierta','2026-02-02','Reactivación confirmada')
        after=Store(self.root,'private').read()
        self.assertEqual(before['quotes'],after['quotes']);self.assertEqual(before['quote_options'],after['quote_options'])
        self.assertEqual(len(after['outcome_history']),2);self.assertEqual(listar(self.root)[0]['resultado'],'Abierta')
    def test_outcome_before_quote(self):
        oid,_=guardar(self.root,self.d,{},'fixture2')
        with self.assertRaises(ValueError):actualizar_resultado(self.root,oid,'Perdida','2025-01-01','No compra')

if __name__=='__main__':unittest.main()
