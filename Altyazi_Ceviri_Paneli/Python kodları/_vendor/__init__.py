"""
_vendor/__init__.py
===================
Projeye gömülü (vendored) kütüphane paketi.

İçerik:
  _vendor/pysubs2/         — pysubs2 v1.8.1  (tkarabela/pysubs2)
  _vendor/pyonfx/          — PyonFX v0.11.0  (CoffeeStraw/PyonFX)
  _vendor/ass_tag_parser/  — ass_tag_parser v2.4.1 (bubblesub/ass_tag_parser)

Bu __init__.py import edilmeden ÖNCE _vendor dizini sys.path'e eklenir.
Bunun için ass_vendor_setup.py'yi en başta import edin:

    import ass_vendor_setup  # en üst satırda bir kez

Veya doğrudan:
    from _vendor import pysubs2, pyonfx, ass_tag_parser
"""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)

# _vendor dizinini path'e ekle (pip install olmaksızın erişmek için)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
