"""La demo pública no toca datos privados y aísla sus sesiones."""
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class PublicDemoTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'cloud'/'streamlit_app.py'),default_timeout=30)
    def test_full_flow_and_session_isolation(self):
        with patch('modelo.cargar_modelo',side_effect=AssertionError('Acceso privado')),patch('modelo.carpeta_privada',side_effect=AssertionError('Ruta privada')):
            a=self.app().run()
            self.assertFalse(a.exception)
            next(b for b in a.button if b.label=='Leer PDF de ejemplo').click().run()
            self.assertFalse(a.exception)
            self.assertEqual(a.number_input(key='f_pax').value,3)
            self.assertEqual(a.number_input(key='f_menores').value,1)
            a.checkbox(key='f_confirmed').check()
            next(b for b in a.button if b.label=='Evaluar y guardar').click().run()
            self.assertFalse(a.exception)
            self.assertFalse(a.error)
            a.run()
            self.assertEqual(len(a.session_state['demo_records']),1)
            next(b for b in a.button if b.label=='Guardar resultado').click().run()
            self.assertFalse(a.exception)
            records=a.session_state['demo_records']
            self.assertEqual(next(iter(records.values()))['resultado'],'Ganada')
            b=self.app().run()
            self.assertFalse(b.exception)
            self.assertNotIn('demo_records',b.session_state)
            self.assertFalse(b.get('file_uploader'))
    def test_three_pdf_examples(self):
        from demo_publica import ejemplos
        from extraer_pdf import extraer_pdf
        from datetime import date
        samples=ejemplos(date(2026,11,8))
        self.assertEqual(len(samples),3)
        for content,kids in zip(samples.values(),(1,0,2)):
            fields=extraer_pdf(content).campos
            self.assertEqual(fields['menores'],kids)
            for key in ('destino','producto','fecha_viaje','fecha_regreso','pax','menores','monto'):
                self.assertIn(key,fields)
