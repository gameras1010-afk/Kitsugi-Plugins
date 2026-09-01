"""translator.py — GERIYE DÖNÜK UYUMLULUK SHIM"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path: sys.path.insert(0, _HERE)
from translator_pkg import KeyManager, SubtitleTranslator  # noqa
