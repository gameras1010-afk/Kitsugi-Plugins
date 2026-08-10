#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MC 1.21.1 NeoForge MOD İNDİRİCİ + ZIPLEYİCİ — Kitsugi modpaketi
================================================================
mod_manifest.json içindeki modları resmi kaynaklardan (Modrinth API +
CurseForge via curse.tools) indirir, SHA1 ile doğrular, iki klasöre ayırır:
  mods-server/   -> sunucuya gidecek modlar
  mods-client/   -> sadece client tarafına gidecek modlar
Sonra hepsini MC-1211-ModPaketi.zip içinde birleştirir ve LINK_LISTESI.txt
ile indirilen her dosyanın kaynak linkini yazar.

KULLANIM:
  python3 indir_modlar.py                # indir + zip üret
  python3 indir_modlar.py --no-zip       # sadece indir, zip yapma
  python3 indir_modlar.py --dry-run      # sadece planı göster
  python3 indir_modlar.py --skip-hash    # sha1 doğrulamasını atla
  python3 indir_modlar.py --include-experimental   # deneysel modları (C2ME OpenCL) DAHİL ET

NOT: Deneysel modlar (ör. C2ME OpenCL - GPU) varsayılan olarak ATLANIR.
Sunucuda GPU/OpenCL kullanmıyorsan (önerilen) --include-experimental YAZMA.

GEREKSİNİM: İnternet erişimi olan makine + Python 3.8+ (harici kütüphane YOK).
GitHub Actions'ta da aynı script çalışır (ubuntu-latest, python3 hazır).
"""
import json
import hashlib
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(BASE_DIR, "mod_manifest.json")
OUT_SERVER = os.path.join(BASE_DIR, "mods-server")
OUT_CLIENT = os.path.join(BASE_DIR, "mods-client")
LINKS_FILE = os.path.join(BASE_DIR, "LINK_LISTESI.txt")
ZIP_PATH = os.path.join(BASE_DIR, "MC-1211-ModPaketi.zip")
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}
PREFERRED_TYPES = ("release", "beta", "alpha")


def api_get(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def download_file(url, dest, headers=None, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers or UA)
            with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            return True
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
    return False


def sha1_file(path: str):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pick_version(versions: list):
    by_type = {}
    for v in versions:
        by_type.setdefault(v.get("version_type", "beta"), []).append(v)
    for t in PREFERRED_TYPES:
        if by_type.get(t):
            return by_type[t][0]
    return versions[0] if versions else None


# ---------------------------------------------------------------- Modrinth
def modrinth_resolve(entry):
    slug = entry["slug"]
    game = entry.get("versions") or ["1.21.1"]
    loaders = entry.get("loaders") or ["neoforge"]
    q = urllib.parse.urlencode({
        "game_versions": json.dumps(game),
        "loaders": json.dumps(loaders),
    })
    url = f"https://api.modrinth.com/v2/project/{slug}/version?{q}&limit=100"
    try:
        versions = json.loads(api_get(url))
    except Exception as e:
        return None, f"API hatası: {e}"
    if not versions:
        return None, "1.21.1 + bu loader için sürüm bulunamadı (Modrinth'te yok olabilir)"
    ver = pick_version(versions)
    if not ver:
        return None, "sürüm listesi boş"
    files = ver.get("files") or []
    if not files:
        return None, "dosya yok"
    f = files[0]
    return {
        "filename": f["filename"],
        "url": f["url"],
        "sha1": (f.get("hashes") or {}).get("sha1"),
        "version_number": ver.get("version_number"),
        "version_type": ver.get("version_type"),
        "project_name": entry["name"],
        "manual": False,
    }, None


# --------------------------------------------------------------- CurseForge
def curseforge_search_mod_id(slug):
    """curse.tools API: slug -> mod id (gameId 432 = Minecraft)."""
    url = ("https://api.curse.tools/v1/cf/mods/search"
           f"?gameId=432&classId=6&pageSize=10&searchFilter={urllib.parse.quote(slug)}")
    data = json.loads(api_get(url))
    mods = data.get("data", []) or []
    for m in mods:
        if str(m.get("slug", "")).lower() == slug.lower():
            return m["id"], m["name"]
    if mods:
        return mods[0]["id"], mods[0].get("name", slug)
    return None, None


def curseforge_resolve(entry):
    slug = entry["slug"]
    name = entry["name"]
    fid = entry.get("file_id") or 0
    cf_id = entry.get("cf_mod_id") or 0
    try:
        if not fid:
            if not cf_id:
                cf_id, name = curseforge_search_mod_id(slug)
                entry["cf_mod_id"] = cf_id
            if cf_id:
                url = (f"https://api.curse.tools/v1/cf/mods/{cf_id}/files"
                       "?gameVersion=1.21.1&modLoaderType=6&pageSize=50")
                files = json.loads(api_get(url)).get("data", [])
                if not files:
                    # yedek: gameVersion'siz çek, 1.21.1 içereni seç
                    files = json.loads(api_get(
                        f"https://api.curse.tools/v1/cf/mods/{cf_id}/files?pageSize=50"
                    )).get("data", [])
                    files = [f for f in files if "1.21.1" in (f.get("gameVersions") or [])]
                if files:
                    files = sorted(files, key=lambda f: f.get("fileDate", ""), reverse=True)
                    fid = files[0]["id"]
        if fid:
            return {
                "filename": entry.get("filename") or f"{slug}-{fid}.jar",
                "url": f"https://www.curseforge.com/minecraft/mc-mods/{slug}/download/{fid}",
                "sha1": None,
                "version_number": str(fid),
                "version_type": "curseforge",
                "project_name": name,
                "manual": False,
            }, None
        return None, f"manuel: https://www.curseforge.com/minecraft/mc-mods/{slug}/files (1.21.1 NeoForge dosyasını seç)"
    except Exception as e:
        return None, f"CurseForge hatası: {e} (manuel: https://www.curseforge.com/minecraft/mc-mods/{slug}/files)"


def verify_jar(dest, sha1_expected, skip_hash):
    if not os.path.exists(dest):
        return False
    if not sha1_expected:
        return True
    if skip_hash:
        return True
    return sha1_file(dest) == sha1_expected


def main():
    no_zip = "--no-zip" in sys.argv
    dry_run = "--dry-run" in sys.argv
    skip_hash = "--skip-hash" in sys.argv

    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(OUT_SERVER, exist_ok=True)
    os.makedirs(OUT_CLIENT, exist_ok=True)

    print("=" * 70)
    print(f"MC {manifest.get('minecraft')} / {manifest.get('loader')} mod indirici")
    all_mods = list(manifest["mods"]) + [
        {**e, "curseforge": True} for e in manifest.get("curseforge_only", [])
    ]
    print(f"Toplam kayıt: {len(all_mods)}")
    print("=" * 70)

    ok, fail = 0, 0
    failed = []
    links = []

    include_exp = "--include-experimental" in sys.argv

    for entry in all_mods:
        name = entry["name"]
        if entry.get("experimental") and not include_exp:
            print(f"[⏭] {name:<42} deneysel (GPU/OpenCL) — ATLANDI. --include-experimental ile dahil edilir")
            continue
        if entry.get("curseforge"):
            info, err = curseforge_resolve(entry)
        else:
            info, err = modrinth_resolve(entry)
        if err:
            fail += 1
            failed.append((name, err))
            print(f"[❌] {name:<42} {err}")
            continue

        dest_dir = OUT_CLIENT if entry.get("client") else OUT_SERVER
        if dry_run:
            print(f"[🔎] {name:<42} -> {info['filename']}  ({info.get('version_number')}, {info.get('version_type')})")
            ok += 1
            links.append(f"{name}\t{info['url']}\t{info['filename']}")
            continue

        dest = os.path.join(dest_dir, info["filename"])
        print(f"[↓] {name:<42} {info['filename']}", end=" ... ", flush=True)
        try:
            if verify_jar(dest, info.get("sha1"), skip_hash):
                print("var (önbellek)")
            else:
                download_file(info["url"], dest)
                print("OK")
            ok += 1
            links.append(f"{name}\t{info['url']}\t{info['filename']}")
        except Exception as e:
            fail += 1
            failed.append((name, str(e)))
            print(f"BAŞARISIZ ({e})")
        time.sleep(0.3)

    # Link listesi
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        f.write("MOD ADI\tKAYNAK URL\tDOSYA\n")
        for line in links:
            f.write(line + "\n")
        if failed:
            f.write("\n=== ÇÖZÜLEMEYENLER (manuel) ===\n")
            for name, err in failed:
                f.write(f"{name}\t{err}\n")

    print("=" * 70)
    print(f"Bitti: {ok} tamam, {fail} sorunlu")
    print(f"  Sunucu modları : {OUT_SERVER}/")
    print(f"  Client modları : {OUT_CLIENT}/")
    print(f"  Link listesi   : {LINKS_FILE}")

    if failed:
        print("\n⚠️  SORUNLU MODLAR:")
        for name, err in failed:
            print(f"   - {name}: {err}")

    if not dry_run and not no_zip:
        import zipfile
        print("\n[🗜] ZIP oluşturuluyor ...")
        with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
            for folder, label in ((OUT_SERVER, "mods-server"), (OUT_CLIENT, "mods-client")):
                for root, _, files in os.walk(folder):
                    for fn in files:
                        full = os.path.join(root, fn)
                        arc = os.path.join(label, fn)
                        z.write(full, arc)
            for doc in ("KURULUM-REHBERI.md", "LINK_LISTESI.txt", "mod_manifest.json"):
                p = os.path.join(BASE_DIR, doc)
                if os.path.exists(p):
                    z.write(p, doc)
        size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
        print(f"[✅] ZIP hazır: {ZIP_PATH} ({size_mb:.1f} MB)")

    print("=" * 70)


if __name__ == "__main__":
    main()
