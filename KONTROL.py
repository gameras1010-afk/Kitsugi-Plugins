#!/usr/bin/env python3
# ! GECICI SURUM - Kitsugi modpack guncelleyici (Kontrol.yml uzerinden calisir)
# ! Bu dosya is bitince orijinal haliyle geri yuklenecektir.
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BRANCH = "mods-cache"
ZIP_NAME = "Kitsugi_Mods_1.21.1_NeoForge.zip"


def run(cmd, **kw):
    print("+ " + (" ".join(cmd) if isinstance(cmd, list) else cmd), flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=kw.pop("cwd", ROOT),
                          check=True, **kw)


def main():
    t0 = time.time()
    os.environ.setdefault("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
    os.environ["GIT_TERMINAL_PROMPT"] = "0"

    # 1) modlari indir
    run([sys.executable, "mods-fetch/fetch_mods.py", "mods-fetch/modlist_raw.txt", "mods_out"])

    # 2) zip + dogrulama
    zip_path = os.path.join(ROOT, ZIP_NAME)
    run(f"cd mods_out && zip -q -r -1 {zip_path} . && cd {ROOT}")
    run(f"unzip -t {ZIP_NAME} | tail -1")
    run(f"unzip -l {ZIP_NAME} | tail -1")

    # 3) parcalara bol (her parca < 100MB -> GitHub dosya limiti)
    sha = subprocess.run(["sha256sum", ZIP_NAME], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout.split()[0]
    print("SHA256:", sha, flush=True)
    parts_dir = os.path.join(ROOT, "parts")
    os.makedirs(parts_dir, exist_ok=True)
    run(f"split -b 90m -d -a 2 {ZIP_NAME} {parts_dir}/part_")
    with open(os.path.join(parts_dir, "SHA256.txt"), "w") as f:
        f.write(sha + "  " + ZIP_NAME + "\n")
    for extra in ("manifest.json", "GUNCELLEME_REHBERI.txt"):
        src = os.path.join(ROOT, "mods_out", extra)
        if os.path.exists(src):
            run(f"cp {src} {parts_dir}/")
    run(f"ls -la {parts_dir} | head -60")

    # 4) GitHub Release olusturmayi dene (kullanici icin guzel indirme sayfasi)
    try:
        tag = "mods-1.21.1-" + time.strftime("%Y%m%d-%H%M%S")
        notes = subprocess.run(["cat", "mods_out/summary.txt"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout
        size = os.path.getsize(zip_path)
        if size < 1950000000:
            assets = [zip_path]
        else:
            assets = [os.path.join(parts_dir, p) for p in sorted(os.listdir(parts_dir))
                      if p.startswith("part_")]
        assets += ["mods_out/manifest.json", "mods_out/GUNCELLEME_REHBERI.txt"]
        run(["gh", "release", "create", tag] + assets +
            ["--title", "Kitsugi Mods 1.21.1 NeoForge (guncel)", "--notes", notes])
        print("RELEASE_TAG=" + tag, flush=True)
    except Exception as e:  # noqa: BLE001
        print("release olusturulamadi (onemsiz):", e, flush=True)

    # 5) parcalari mods-cache branch'ine push et (sandbox'a tasima kanali)
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
    run(["git", "checkout", "--orphan", BRANCH])
    run(["git", "rm", "-rf", "--quiet", "."])
    for name in sorted(os.listdir(parts_dir)):
        run(f"git add parts/{name}")
    run(["git", "commit", "-m", f"mods cache {time.strftime('%Y%m%d-%H%M%S')}"])
    run(["git", "push", "origin", BRANCH, "--force"])
    # isci dizinini temizle
    run(["git", "checkout", "-f", os.environ["GITHUB_REF_NAME"]])
    run(f"rm -rf {parts_dir} mods_out {ZIP_NAME}")

    print(f"DONE in {int(time.time() - t0)}s - mods-cache branch push edildi, SHA256={sha}", flush=True)


if __name__ == "__main__":
    main()
