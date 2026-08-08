#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2ME-OCL LWJGL sign-extension YAMA SCRIPTİ
===========================================
LWJGL, CL_DEVICE_TYPE_ALL filtresini -1L (0xFFFFFFFFFFFFFFFF) olarak gönderir.
Mesa Rusticl bu değeri reddeder -> CL_INVALID_DEVICE_TYPE [-31].
Yama: C2ME-OCL jar'ının içindeki nested lwjgl-opencl jar'ının CL.class
bytecode'undaki Long(-1) sabitini Long(4294967295) ile değiştirir.

KULLANIM:
  python3 patch_lwjgl.py                    # mods/ klasöründeki c2me...jar'ı otomatik bulur
  python3 patch_lwjgl.py /yol/c2me.jar      # belirli jar'ı yamalar
  python3 patch_lwjgl.py --check            # yama uygulanmış mı diye kontrol eder (değiştirmez)
  python3 patch_lwjgl.py --revert           # yamayı geri alır (eski hale döndürür)

ÖNEMLİ: Her C2ME güncellemesinden SONRA bu scripti tekrar çalıştır.
"""
import os
import sys
import glob
import shutil
import tempfile
import zipfile

OLD = b"\x05\xff\xff\xff\xff\xff\xff\xff\xff"  # Long tag 0x05, deger -1
NEW = b"\x05\x00\x00\x00\x00\xff\xff\xff\xff"  # Long tag 0x05, deger 4294967295


def find_c2me_jar():
    candidates = []
    for base in (os.getcwd(), "mods", "mods-server", "mods-client"):
        if os.path.isdir(base):
            candidates += glob.glob(os.path.join(base, "c2me-neoforge-opts-accel-opencl-*.jar"))
            candidates += glob.glob(os.path.join(base, "c2me-*-accel-opencl-*.jar"))
    # benzersizleştir
    seen, out = set(), []
    for c in candidates:
        c = os.path.abspath(c)
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def patch_nested(path, apply: bool, revert: bool):
    """nested lwjgl-opencl jar'ini bul, CL.class'i yamala. degisti mi don."""
    target = OLD if apply else NEW
    repl = NEW if apply else OLD
    changed = False
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if "lwjgl-opencl" in item.filename and item.filename.endswith(".jar"):
                nested_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jar")
                nested_tmp.write(data)
                nested_tmp.close()
                n_tmp = nested_tmp.name + ".tmp"
                n_changed = False
                with zipfile.ZipFile(nested_tmp.name) as nz, zipfile.ZipFile(n_tmp, "w", zipfile.ZIP_DEFLATED) as nzout:
                    for ni in nz.infolist():
                        nd = nz.read(ni.filename)
                        if ni.filename.endswith("org/lwjgl/opencl/CL.class"):
                            if target in nd:
                                nd = nd.replace(target, repl)
                                n_changed = True
                                changed = True
                        nzout.writestr(ni, nd)
                if n_changed:
                    with open(n_tmp, "rb") as f:
                        data = f.read()
                os.unlink(nested_tmp.name)
                os.unlink(n_tmp)
            zout.writestr(item, data)
    if changed:
        shutil.move(tmp, path)
    else:
        os.unlink(tmp)
    return changed


def check_patch(path):
    with zipfile.ZipFile(path) as zin:
        for item in zin.infolist():
            if "lwjgl-opencl" in item.filename and item.filename.endswith(".jar"):
                data = zin.read(item.filename)
                import io
                with zipfile.ZipFile(io.BytesIO(data)) as nz:
                    for ni in nz.infolist():
                        if ni.filename.endswith("org/lwjgl/opencl/CL.class"):
                            nd = nz.read(ni.filename)
                            if NEW in nd:
                                return "YAMALI (4294967295L)"
                            if OLD in nd:
                                return "YAMASIZ (-1L)"
                            return "BULUNAMADI (farkli bytecode?)"
    return "lwjgl-opencl nested jar bulunamadi"


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    revert = "--revert" in args
    explicit = [a for a in args if not a.startswith("--")]

    jars = [os.path.abspath(e) for e in explicit] if explicit else find_c2me_jar()
    if not jars:
        print("❌ c2me accel-opencl jar bulunamadi. Yolu ver: python3 patch_lwjgl.py /yol/c2me.jar")
        sys.exit(1)

    for jar in jars:
        if not os.path.exists(jar):
            print(f"❌ Dosya yok: {jar}")
            continue
        if check_only:
            print(f"{jar}\n   -> {check_patch(jar)}")
            continue
        ok = patch_nested(jar, apply=True, revert=revert)
        if ok:
            print(f"✅ YAMA UYGULANDI: {os.path.basename(jar)}")
        else:
            state = check_patch(jar)
            print(f"⚠️  Degisiklik yapilmadi: {os.path.basename(jar)} -> {state}")


if __name__ == "__main__":
    main()
