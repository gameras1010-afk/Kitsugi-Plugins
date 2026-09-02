"""
hook_portable.py — PyInstaller runtime hook
EXE başlarken çalışır. Portable mod için veri dizinini ayarlar.
"""
import os, sys

# EXE'nin yanındaki 'data' klasörünü kullanıcı verisi olarak ayarla
_exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
           else os.path.dirname(os.path.abspath(__file__))

_data_dir = os.path.join(_exe_dir, 'data')
os.makedirs(_data_dir, exist_ok=True)

# Ortam değişkeni yoksa ayarla
if not os.environ.get('NEXUS_USER_DIR'):
    os.environ['NEXUS_USER_DIR'] = _data_dir
    os.environ['NEXUS_DATA_DIR'] = _data_dir
