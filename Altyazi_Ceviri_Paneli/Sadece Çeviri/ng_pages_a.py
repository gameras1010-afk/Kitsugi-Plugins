"""
ng_pages_a.py  —  GERIYE DÖNÜK UYUMLULUK SHIM
Gerçek kod: pages/ klasöründe.
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from pages import *  # noqa
from pages import (
    get_prefs, get_glossary, state, nbtn, refresh_status,
    build_dashboard, build_translate, build_glossary,
)
