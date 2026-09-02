"""
ng_pages_b.py  —  GERIYE DÖNÜK UYUMLULUK SHIM
Gerçek kod: pages/ klasöründe.
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from pages import *  # noqa
from pages import (
    build_theme_page, build_settings, build_about,
    build_reports, build_datasources, build_notifications,
    build_api_keys, build_accounts,
)
