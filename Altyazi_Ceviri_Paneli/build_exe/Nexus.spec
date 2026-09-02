# -*- mode: python ; coding: utf-8 -*-
"""
Nexus AI Subtitle Engine — PyInstaller Spec
Tek EXE: çift tıkla çalış, kendi penceresinde açılır.
"""

import os, sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# ── Yollar ───────────────────────────────────────────────────────────────────
ROOT       = Path(SPECPATH).parent                  # Altyazi_Ceviri_Paneli/
CEVIRI_DIR = ROOT / "Sadece Çeviri"
KODLAR_DIR = ROOT / "Python kodları"

# ── NiceGUI kaynak dosyaları (web UI) ────────────────────────────────────────
nicegui_datas, nicegui_binaries, nicegui_hiddenimports = collect_all('nicegui')

# ── Gizli import listesi ─────────────────────────────────────────────────────
hidden = [
    # NiceGUI + FastAPI
    'nicegui', 'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops',
    'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan',
    'uvicorn.lifespan.on', 'starlette', 'anyio', 'httpx',
    # Altyazı motoru
    'pysubs2', 'requests', 'colorama', 'tqdm',
    # Bizim alt paketlerimiz
    'processor', 'processor.pipeline', 'processor.pipeline.main',
    'processor.batch', 'processor.dedup', 'processor.imports',
    'processor.karaoke', 'processor.song_detect', 'processor.song_translate',
    'processor.style_detect', 'processor.tag_tools', 'processor.text_helpers',
    'glossary', 'glossary.builder', 'glossary.cache', 'glossary.characters',
    'glossary.fetcher', 'glossary.models', 'glossary.resolver',
    'glossary.slug', 'glossary.store', 'glossary.titles', 'glossary.wiki_api',
    'offline_db', 'offline_db.anime_db', 'offline_db.characters',
    'offline_db.constants', 'offline_db.franchise', 'offline_db.lookup',
    'offline_db.media_db', 'offline_db.tmdb_cast',
    'media_id', 'media_id.ai_tools', 'media_id.apis', 'media_id.constants',
    'media_id.episode', 'media_id.fetcher', 'media_id.quality',
    'translator_pkg', 'translator_pkg.key_manager',
    'translator_pkg.subtitle_translator',
    'detector', 'detector.classifier', 'detector.freq_tools',
    'termbase', 'termbase.manager', 'termbase.paths',
    'ass_reader', 'ass_reader.reader', 'ass_reader.pysubs_utils',
    'tag_library', 'tag_library.core', 'tag_library.color_time',
    'romaji', 'romaji.kana', 'romaji.filter', 'romaji.detector',
    'utils_pkg', 'utils_pkg.text', 'utils_pkg.file_io',
    'pages', 'pages.helpers', 'pages.dashboard', 'pages.translate',
    'pages.glossary_page', 'pages.theme', 'pages.settings', 'pages.about',
    'pages.reports', 'pages.datasources', 'pages.notifications',
    'pages.api_keys', 'pages.accounts',
    # Standart lib
    'xml.etree.ElementTree', 'unicodedata', 'difflib',
    'concurrent.futures', 'threading', 'multiprocessing',
    'json', 'gzip', 'hashlib', 'tempfile', 'shutil',
    # Windows native pencere
    'webview',
] + nicegui_hiddenimports

# ── Veri dosyaları ────────────────────────────────────────────────────────────
datas = nicegui_datas + [
    # "Sadece Çeviri/" içindeki Python paketleri
    (str(CEVIRI_DIR / "pages"),    "pages"),
    (str(CEVIRI_DIR / "ng_config.py"),  "."),
    (str(CEVIRI_DIR / "ng_styles.py"),  "."),
    (str(CEVIRI_DIR / "ng_app.py"),     "."),
    # "Python kodları/" içindeki paketler ve JSON dosyaları
    (str(KODLAR_DIR / "processor"),     "processor"),
    (str(KODLAR_DIR / "glossary"),      "glossary"),
    (str(KODLAR_DIR / "offline_db"),    "offline_db"),
    (str(KODLAR_DIR / "media_id"),      "media_id"),
    (str(KODLAR_DIR / "translator_pkg"),"translator_pkg"),
    (str(KODLAR_DIR / "detector"),      "detector"),
    (str(KODLAR_DIR / "termbase"),      "termbase"),
    (str(KODLAR_DIR / "ass_reader"),    "ass_reader"),
    (str(KODLAR_DIR / "tag_library"),   "tag_library"),
    (str(KODLAR_DIR / "romaji"),        "romaji"),
    (str(KODLAR_DIR / "utils_pkg"),     "utils_pkg"),
    (str(KODLAR_DIR / "_vendor"),       "_vendor"),
    # Tek dosya .py modülleri
    (str(KODLAR_DIR / "settings.py"),                  "."),
    (str(KODLAR_DIR / "utils.py"),                     "."),
    (str(KODLAR_DIR / "ass_tag_extractor.py"),         "."),
    (str(KODLAR_DIR / "ass_tags_database.py"),         "."),
    (str(KODLAR_DIR / "ass_tag_library.py"),           "."),
    (str(KODLAR_DIR / "ass_file_reader.py"),           "."),
    (str(KODLAR_DIR / "ass_line_filter.py"),           "."),
    (str(KODLAR_DIR / "ass_style_conventions.py"),     "."),
    (str(KODLAR_DIR / "ass_content_classifier.py"),    "."),
    (str(KODLAR_DIR / "ass_qa_checker.py"),            "."),
    (str(KODLAR_DIR / "ass_skip_learner.py"),          "."),
    (str(KODLAR_DIR / "ass_tag_reference.py"),         "."),
    (str(KODLAR_DIR / "ass_vendor_setup.py"),          "."),
    (str(KODLAR_DIR / "content_detector.py"),          "."),
    (str(KODLAR_DIR / "episode_context.py"),           "."),
    (str(KODLAR_DIR / "fandom_glossary.py"),           "."),
    (str(KODLAR_DIR / "glossary_prescanner.py"),       "."),
    (str(KODLAR_DIR / "idiom_scanner.py"),             "."),
    (str(KODLAR_DIR / "media_identifier.py"),          "."),
    (str(KODLAR_DIR / "notif_bus.py"),                 "."),
    (str(KODLAR_DIR / "offline_db_manager.py"),        "."),
    (str(KODLAR_DIR / "romaji_detector.py"),           "."),
    (str(KODLAR_DIR / "romaji_filter.py"),             "."),
    (str(KODLAR_DIR / "subtitle_processor.py"),        "."),
    (str(KODLAR_DIR / "subtitle_tracks.py"),           "."),
    (str(KODLAR_DIR / "subtitle_validator.py"),        "."),
    (str(KODLAR_DIR / "subtitle_position_helpers.py"), "."),
    (str(KODLAR_DIR / "termbase_manager.py"),          "."),
    (str(KODLAR_DIR / "tr_lang_detector.py"),          "."),
    (str(KODLAR_DIR / "translation_report.py"),        "."),
    (str(KODLAR_DIR / "translation_verifier.py"),      "."),
    (str(KODLAR_DIR / "translator.py"),                "."),
    (str(KODLAR_DIR / "subtitle_position_helpers.py"), "."),
    (str(KODLAR_DIR / "_no_window.py"),                "."),
    # Sadece Çeviri'deki ek dosyalar
    (str(CEVIRI_DIR / "translator_gui.py"),        "."),
    (str(CEVIRI_DIR / "manual_gui.py"),            "."),
    (str(CEVIRI_DIR / "manual_translator.py"),     "."),
    # JSON veri dosyaları
    (str(KODLAR_DIR / "prompt_template.json"),         "."),
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(CEVIRI_DIR / "ng_app.py")],
    pathex=[str(CEVIRI_DIR), str(KODLAR_DIR)],
    binaries=nicegui_binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['../build_exe/hook_portable.py'],  # Portable mod desteği
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2',
              'tensorflow', 'torch', 'sklearn', 'pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name            = "Nexus",
    debug           = False,
    bootloader_ignore_signals = False,
    strip           = False,
    upx             = False,           # UPX antivirüs tetikleyebilir
    upx_exclude     = [],
    runtime_tmpdir  = None,
    console         = False,           # Siyah konsol penceresi YOK
    disable_windowed_traceback = False,
    argv_emulation  = False,
    target_arch     = None,
    codesign_identity = None,
    entitlements_file = None,
    icon            = None,            # icon.ico eklenince buraya
    onefile         = True,            # TEK dosya EXE
)
