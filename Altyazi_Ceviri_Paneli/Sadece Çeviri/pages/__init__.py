"""
pages/__init__.py
=================
NiceGUI sayfa modülleri paketi.
ng_pages_a.py + ng_pages_b.py → pages/ alt modülleri.
"""
from pages.helpers import get_prefs, get_glossary, state, nbtn, refresh_status
from pages.dashboard import build_dashboard
from pages.translate import build_translate
from pages.glossary_page import build_glossary
from pages.theme import build_theme_page
from pages.settings import build_settings
from pages.about import build_about
from pages.reports import build_reports
from pages.datasources import build_datasources
from pages.notifications import build_notifications
from pages.api_keys import build_api_keys
from pages.accounts import build_accounts

__all__ = [
    "get_prefs", "get_glossary", "state", "nbtn", "refresh_status",
    "build_dashboard", "build_translate", "build_glossary",
    "build_theme_page", "build_settings", "build_about",
    "build_reports", "build_datasources", "build_notifications",
    "build_api_keys", "build_accounts",
]
