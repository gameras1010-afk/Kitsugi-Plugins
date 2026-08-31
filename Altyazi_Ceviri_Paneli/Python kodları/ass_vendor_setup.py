"""
ass_vendor_setup.py
===================
Projeye gömülü kütüphaneleri aktif eder.

Her modülün EN BAŞINDA (tüm import'lardan önce) şu satırı ekle:

    import ass_vendor_setup  # noqa

Bu dosya:
  1. _vendor/ dizinini sys.path'e ekler
  2. Sistem kurulumunda pysubs2/pyonfx/ass_tag_parser yoksa _vendor'dan kullanır
  3. Varsa sistem kurulumunu tercih eder (pip paketi güncel olabilir)

Versiyon Bilgisi:
  pysubs2       : 1.8.1  — https://github.com/tkarabela/pysubs2
  PyonFX        : 0.11.0 — https://github.com/CoffeeStraw/PyonFX
  ass_tag_parser: 2.4.1  — https://github.com/bubblesub/ass_tag_parser
"""
import sys
import os

# Bu dosyanın bulunduğu dizin = Python kodları klasörü
_BASE = os.path.dirname(os.path.abspath(__file__))
_VENDOR = os.path.join(_BASE, '_vendor')

def _ensure_vendor():
    """_vendor/ dizinini sys.path'e ekle (zaten ekli değilse)."""
    if _VENDOR not in sys.path:
        sys.path.insert(0, _VENDOR)

def _check_and_report():
    """Kütüphane durumunu kontrol et."""
    _ensure_vendor()
    status = {}
    for lib in ('pysubs2', 'pyonfx', 'ass_tag_parser'):
        try:
            mod = __import__(lib)
            ver = getattr(mod, '__version__', '?')
            loc = getattr(mod, '__file__', '?')
            is_vendor = _VENDOR in (loc or '')
            status[lib] = {'ok': True, 'version': ver, 'vendored': is_vendor}
        except ImportError as e:
            status[lib] = {'ok': False, 'error': str(e)}
    return status

# Çalıştırıldığında otomatik aktif et
_ensure_vendor()

# Direkt çalıştırılırsa rapor ver
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("=== Vendor Kütüphane Durumu ===")
    for lib, info in _check_and_report().items():
        if info['ok']:
            src = 'VENDOR' if info['vendored'] else 'SYSTEM'
            print(f"  {lib:20s} v{info['version']:10s} [{src}]")
        else:
            print(f"  {lib:20s} HATA: {info['error']}")
