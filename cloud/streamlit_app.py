"""Único punto de entrada de la demo pública; nunca activa el modelo privado."""
import runpy
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
if str(root) not in sys.path:sys.path.insert(0,str(root))
runpy.run_path(str(root/'app.py'),init_globals={'QUOTESCORE_DEMO':True},run_name='__main__')
