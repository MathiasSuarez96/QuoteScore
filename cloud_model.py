"""Carga únicamente el artefacto configurado por el propietario en Secrets.

Nunca carga pickle/joblib de archivos subidos por visitantes.
"""
import base64
import hashlib
from io import BytesIO
import joblib
import sklearn
import streamlit as st

def cloud_configurado():
    try:
        return bool(st.secrets.get('quotescore_model_b64'))
    except FileNotFoundError:
        return False

@st.cache_resource
def cargar_cloud():
    try:
        data=base64.b64decode(st.secrets['quotescore_model_b64'],validate=True)
        expected=st.secrets['quotescore_model_sha256']
        if len(data)>2_000_000 or hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError('Artefacto inválido')
        # Secrets es configuración administrativa, nunca entrada del visitante.
        bundle=joblib.load(BytesIO(data))
        if bundle['metadata']['sklearn']!=sklearn.__version__:
            raise ValueError('Versión incompatible')
        if bundle['metadata'].get('deployment')!='cloud-sanitized-v1':
            raise ValueError('Modelo no preparado para publicación')
        return bundle
    except Exception:
        raise ValueError('Revisá el modelo configurado en Secrets.') from None
