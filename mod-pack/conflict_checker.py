#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÇAKIŞMA TARAYICI — mods/ klasöründeki jar'ları analiz eder
===========================================================
Neleri kontrol eder:
  1) DUPLICATE MOD ID  -> iki jar ayni modId sagliyor (ciddi cakisma)
  2) EKSIK ZORUNLU DEP  -> bir mod, klasorde olmayan required dependency istiyor
  3) BILINEN CAKISMA CIFTLERI  -> ayni isi yapan / birbirini bozan modlar (uyari)
  4) SURUM UYUSMAZLIGI (basit) -> modun istedigi minimum dep surumu vs kurulu

KULLANIM:
  python3 conflict_checker.py /opt/mc/mods
  python3 conflict_checker.py /opt/mc/mods --json    # makine-okur cikti

CIKTI: OK / UYARI / SORUN satirlari. SORUN gorursen log'a da bak (asagida).
"""
import sys
import os
import re
import glob
import zipfile
import json

# ---------------- bilinen cakisma ciftleri (modId seviyesinde) ----------------
# (a, b, aciklama, seviye)  seviye: "sorun" | "uyari"
KNOWN_PAIRS = [
    ("lithium", "radium", "Lithium ve Radium AYNI isi yapar (ikisi birden olmaz).", "sorun"),
    ("lithium", "canary", "Lithium ve Canary AYNI isi yapar.", "sorun"),
    ("sodium", "xenon", "Sodium ve Xenon AYNI render isi yapar.", "sorun"),
    ("sodium", "rubidium", "Sodium ve Rubidium AYNI isi yapar.", "sorun"),
    ("iris", "oculus", "Iris ve Oculus AYNI shader isi yapar.", "sorun"),
    ("ferritecore", "ferritecore-fabric", "FerriteCore cift yuklenmis.", "sorun"),
    ("c2me-opts-accel-opencl", "noisium", "C2ME OpenCL + Noisium MIXIN CAKISMASI yapar (noisium'u cikar).", "sorun"),
    ("c2me", "noisium", "C2ME CPU + Noisium genelde uyumlu (cakisma yok) — ama OpenCL moduluyle birlikteyse yukaridaki gecerli.", "uyari"),
    ("modernfix", "performant", "ModernFix + Performant cakisa bilir.", "uyari"),
    ("embeddium", "sodium", "Embeddium ve Sodium AYNI isi yapar.", "sorun"),
    ("jei", "rei", "JEI ve REI birlikte cakisa bilir (birini sec).", "uyari"),
    ("jei", "emi", "JEI ve EMI birlikte cakisa bilir (birini sec).", "uyari"),
    ("entityculling", "entity_culling", "EntityCulling cift yuklenmis.", "sorun"),
    ("oreexcavation", "veinmining", "Ore Excavation ve Vein Mining AYNI isi yapar.", "uyari"),
    ("carryon", "carry-on", "Carry On cift yuklenmis.", "sorun"),
]


def parse_mod_ids_and_deps(jar_path):
    """jar icinden modId listesi + dependency'leri cikar. (neoforge.mods.toml + fabric.mod.json)"""
    mod_ids, deps = [], []  # deps: (depModId, type, versionRange)
    try:
        with zipfile.ZipFile(jar_path) as z:
            names = z.namelist()
            if "META-INF/neoforge.mods.toml" in names:
                txt = z.read("META-INF/neoforge.mods.toml").decode("utf-8", "replace")
                mod_ids += re.findall(r'^\s*modId\s*=\s*"([^"]+)"', txt, re.M)
                # [[dependencies.<modid>]] bloklari
                for m in re.finditer(
                    r'\[\[dependencies\.([^\]]+)\]\]\s*\{([^}]*)\}', txt):
                    dep_mod = m.group(1)
                    block = m.group(2)
                    d_type = re.search(r'type\s*=\s*"([^"]+)"', block)
                    v_range = re.search(r'versionRange\s*=\s*"([^"]+)"', block)
                    deps.append((dep_mod, d_type.group(1) if d_type else "required",
                                 v_range.group(1) if v_range else ""))
            if "fabric.mod.json" in names:
                fj = json.loads(z.read("fabric.mod.json").decode("utf-8", "replace"))
                mid = fj.get("id")
                if mid:
                    mod_ids.append(mid)
                for dep in fj.get("depends", {}):
                    deps.append((dep, "required", ""))
    except Exception:
        pass
    return mod_ids, deps


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if not a.startswith("--")]
    folder = args[0] if args else "mods"
    if not os.path.isdir(folder):
        print(f"❌ Klasor bulunamadi: {folder}")
        sys.exit(1)

    jars = sorted(glob.glob(os.path.join(folder, "*.jar")))
    if not jars:
        print(f"❌ {folder} icinde jar yok.")
        sys.exit(1)

    # her jar -> (modIds, deps)
    info = {}
    for j in jars:
        ids, deps = parse_mod_ids_and_deps(j)
        info[j] = (ids, deps)

    issues = []  # (seviye, mesaj)
    modid_to_jar = {}
    for j, (ids, _) in info.items():
        for mid in ids:
            modid_to_jar.setdefault(mid, []).append(j)

    # 1) duplicate mod id
    for mid, jar_list in modid_to_jar.items():
        if len(jar_list) > 1:
            issues.append(("SORUN",
                f"AYNI MOD ID '{mid}' birden fazla jar'da: {[os.path.basename(x) for x in jar_list]}"))

    # 2) eksik zorunlu dep (klasor icinde hicbir jar saglamiyorsa)
    provided = set(modid_to_jar.keys())
    for j, (ids, deps) in info.items():
        for dep_mod, d_type, v_range in deps:
            if d_type == "required" and dep_mod not in provided:
                issues.append(("SORUN",
                    f"{os.path.basename(j)} zorunlu dep istiyor: '{dep_mod}' — ama mods/ icinde YOK."))

    # 3) bilinen cakisma ciftleri
    present_ids = set(provided)
    for a, b, desc, sev in KNOWN_PAIRS:
        if a in present_ids and b in present_ids:
            issues.append((sev.upper(), f"{a} + {b}: {desc}"))

    # 4) surum uyari (ilk 50 dep icin basit: "x" min sürüm cikar)
    #    (tam surum karsilastirmasi karmasik — sadece bos olmayan range'leri raporla)
    for j, (ids, deps) in info.items():
        for dep_mod, d_type, v_range in deps:
            if v_range and d_type == "required" and dep_mod in provided:
                issues.append(("UYARI",
                    f"{os.path.basename(j)}: dep '{dep_mod}' icin istenen aralik '{v_range}' — "
                    f"kurulu jar '{os.path.basename(modid_to_jar[dep_mod][0])}' bu araliga uygun mu kontrol et."))

    if as_json:
        print(json.dumps({"jar_count": len(jars), "issues": issues}, ensure_ascii=False, indent=2))
        return

    print(f"🔍 Taranan jar: {len(jars)}")
    print("=" * 66)
    if not issues:
        print("✅ SORUN BULUNMADI — paket temiz gorunuyor.")
    for sev, msg in issues:
        icon = "❌" if sev == "SORUN" else "⚠️"
        print(f"{icon} [{sev}] {msg}")
    print("=" * 66)
    if any(s == "SORUN" for s, _ in issues):
        print("📌 SORUN varsa: ilgili jar'i mods/'dan cikar (veya dep'i indir), sonra tekrar calistir.")
    else:
        print("📌 Yine de ilk acilista log'a bak: grep -iE 'mixin.*fail|conflict|incompatible|Exception' logs/latest.log")


if __name__ == "__main__":
    main()
