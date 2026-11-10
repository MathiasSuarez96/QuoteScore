"""Entrada pública: modelo privado configurado o demo sintética explícita."""
import runpy
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if str(root) not in sys.path:sys.path.insert(0,str(root))
from cloud_model import cloud_configurado
real=cloud_configurado()
runpy.run_path(str(root/'app.py'),init_globals={'QUOTESCORE_DEMO':not real,'QUOTESCORE_CLOUD':real},run_name='__main__')
