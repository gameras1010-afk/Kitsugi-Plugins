#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository Sahip Tasima Araci — "gameras1010-afk" sahibi atiflarinin tamamini
yeni hesaba yazar. Hem Kitsugi-Plugins hem de Kitsugi-Beta deposu icin
ayni script kullanilir (--dir ile hedef klasoru belirtirsiniz).

KULLANIM
--------
    # Bu deponun (mevcut klasorun) main branch'ini tasima:
    python3 migrate_urls.py yeni-hesabim

    # Baska bir deponu (orn. app reposu) tasima:
    python3 migrate_urls.py yeni-hesabim --dir ../Kitsugi-Beta

    # Repo adlari da degisecekse:
    python3 migrate_urls.py yeni-hesabim Kitsugi-Plugins=yeni-eklentiler

    # Once ne degisecekse gormek icin (dosyalara dokunmaz):
    python3 migrate_urls.py yeni-hesabim --dry-run

builds BRANCH ICI (yalnizca Kitsugi-Plugins)
-------------------------------------------
    git checkout builds
    python3 migrate_urls.py yeni-hesabim
    git checkout main

NOTLAR
------
* .cs3, .zip, .pyc, .dex, resim vb. IKIL dosyalara DOKUNMAZ.
  (cs3 icine URL gomulu degildir; manifest JSON'larda degistirilir.)
* Calistirdiktan sonra `git diff` ile kontrol edin, onaylarsaniz commit edin.
* main branch'teki .pyc / zip gibi ikil kalintilar yeni ortamda kendiliginden
  yeniden uretilecegi icin bilincli olarak degistirilmez.
"""

import os
import sys

OLD_OWNER = "gameras1010-afk"

# Ikil (degistirilmeyecek) uzantilar
SKIP_EXTS = {
    ".pyc", ".cs3", ".zip", ".dex", ".jar", ".so", ".aar", ".apk",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".bmp",
    ".7z", ".rar", ".sqlite", ".db", ".keystore", ".jks", ".bin",
    ".ttf", ".otf", ".wav", ".mp3", ".pdf",
}

# Bu scriptin kendisi hicbir zaman degistirilmez
SELF_PATH = os.path.normpath(os.path.abspath(__file__))


def is_text_file(path, max_bytes=8192):
    """Dosya okunabilir metin mi? (null bayt iceren dosya ikildir)"""
    try:
        with open(path, "rb") as f:
            chunk = f.read(max_bytes)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def parse_args(argv):
    dry_run = False
    target_dir = "."
    repo_pairs = []
    new_owner = None

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry-run":
            dry_run = True
        elif a == "--dir":
            i += 1
            if i < len(argv):
                target_dir = argv[i]
        elif a.startswith("--dir="):
            target_dir = a.split("=", 1)[1]
        elif "=" in a and new_owner is not None:
            old_repo, new_repo = a.split("=", 1)
            repo_pairs.append((old_repo, new_repo))
        elif new_owner is None:
            new_owner = a
        else:
            print(f"HATA: beklenmeyen argument: {a}")
            sys.exit(1)
        i += 1

    return new_owner, repo_pairs, target_dir, dry_run


def main():
    argv = sys.argv[1:]
    new_owner, repo_pairs, target_dir, dry_run = parse_args(argv)

    if not new_owner:
        print(__doc__)
        sys.exit(1)
    if new_owner == OLD_OWNER:
        print("HATA: yeni sahip eski sahip ile ayni.")
        sys.exit(1)
    if not os.path.isdir(target_dir):
        print(f"HATA: hedef dizin bulunamadi: {target_dir}")
        sys.exit(1)

    changed = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "build", ".gradle",
                                                "node_modules", ".idea")]
        for fn in files:
            path = os.path.join(root, fn)
            abs_path = os.path.normpath(os.path.abspath(path))
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXTS:
                continue
            if abs_path == SELF_PATH:
                continue
            if not is_text_file(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            if OLD_OWNER not in content:
                continue

            new_content = content
            # 1) EskiSahip/EskiRepo -> YeniSahip/YeniRepo  (URL ciftleri)
            for old_repo, new_repo in repo_pairs:
                new_content = new_content.replace(
                    f"{OLD_OWNER}/{old_repo}", f"{new_owner}/{new_repo}"
                )
            # 2) Kalan yalizin atiflari: EskiSahip -> YeniSahip
            #    (repoOwner = "..." , User-Agent, MY_REPO = "sahip/repo" vb.)
            new_content = new_content.replace(OLD_OWNER, new_owner)

            if new_content != content:
                changed.append(path)
                if not dry_run:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)

    print(f"HEDEF DIZIN: {target_dir}")
    print(f"YENI SAHIB : {new_owner}")
    if repo_pairs:
        print(f"REPO ESI   : {repo_pairs}")
    print(f"{'[DRY-RUN] ' if dry_run else ''}Degisen dosya sayisi: {len(changed)}")
    for p in changed:
        print(f"  - {p}")
    if dry_run and changed:
        print("\n--dry-run modu: dosyalara dokunulmadi.")


if __name__ == "__main__":
    main()
