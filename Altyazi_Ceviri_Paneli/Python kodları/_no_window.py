"""
_no_window.py — Console Suppressor
===================================
Bu modülü import etmek, Python'daki subprocess.Popen ve subprocess.run
çağrılarını otomatik olarak CREATE_NO_WINDOW ile yapar.

Kullanım (dosyanın en başına ekle):
    import _no_window  # noqa

Nasıl çalışır:
    Windows'ta creationflags parametresi belirtilmemişse otomatik olarak
    CREATE_NO_WINDOW (0x08000000) eklenir. Zaten belirtilmişse dokunmaz.
    Linux/Mac'ta hiçbir şey değişmez.
"""
import os
import subprocess as _sp

if os.name == 'nt':
    _CNW  = getattr(_sp, 'CREATE_NO_WINDOW', 0x08000000)
    _ORIG_POPEN = _sp.Popen

    class _PopenNW(_ORIG_POPEN):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = _CNW
            else:
                # Mevcut flag'lere OR ile ekle (varolan ayarları bozmaz)
                kwargs['creationflags'] |= _CNW
            super().__init__(*args, **kwargs)

    _sp.Popen = _PopenNW

    # subprocess.run da Popen'ı kullandığı için otomatik etkilenir.
    # Ama güvenlik için run'ı da wrap edelim:
    _ORIG_RUN = _sp.run
    def _run_nw(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = _CNW
        else:
            kwargs['creationflags'] |= _CNW
        return _ORIG_RUN(*args, **kwargs)
    _sp.run = _run_nw

    # subprocess.call da (varsa)
    _ORIG_CALL = _sp.call
    def _call_nw(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = _CNW
        else:
            kwargs['creationflags'] |= _CNW
        return _ORIG_CALL(*args, **kwargs)
    _sp.call = _call_nw
