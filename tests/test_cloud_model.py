import base64
import hashlib
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch
import joblib
import sklearn
from streamlit.testing.v1 import AppTest
from demo_publica import cargar_demo
from cloud_model import cargar_cloud

class CloudTests(unittest.TestCase):
    def app(self):
        import copy
        bundle=copy.deepcopy(cargar_demo())
        bundle['metadata'].update(deployment='cloud-sanitized-v1',sklearn=sklearn.__version__,synthetic=False)
        buf=BytesIO();joblib.dump(bundle,buf);raw=buf.getvalue()
        a=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'cloud/streamlit_app.py'),default_timeout=30)
        a.secrets['quotescore_model_b64']=base64.b64encode(raw).decode()
        a.secrets['quotescore_model_sha256']=hashlib.sha256(raw).hexdigest()
        return a

    def test_real_mode_session_isolated_and_upload_requires_consent(self):
        cargar_cloud.clear()
        with patch('modelo.cargar_modelo',side_effect=AssertionError('Local model access')),patch('modelo.carpeta_privada',side_effect=AssertionError('Local store access')):
            a=self.app().run()
            self.assertFalse(a.exception)
            self.assertTrue(a.get('file_uploader')[0].proto.disabled)
            a.checkbox(key='pdf_consent').check().run()
            self.assertFalse(a.get('file_uploader')[0].proto.disabled)
            a.text_input(key='f_destino').set_value('Aruba')
            a.checkbox(key='f_confirmed').check()
            next(b for b in a.button if b.label=='Evaluar y guardar').click().run()
            self.assertFalse(a.exception)
            self.assertFalse(a.error)
            self.assertEqual(len(a.session_state['demo_records']),1)
            b=self.app().run()
            self.assertNotIn('demo_records',b.session_state)
        cargar_cloud.clear()

    def test_bad_hash_stops_without_loading_artifact(self):
        cargar_cloud.clear()
        a=self.app();a.secrets['quotescore_model_sha256']='wrong'
        with patch('cloud_model.joblib.load',side_effect=AssertionError('Must not deserialize')):
            a.run()
        self.assertFalse(a.exception)
        self.assertTrue(a.error)
        cargar_cloud.clear()
