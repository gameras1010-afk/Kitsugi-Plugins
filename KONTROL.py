#!/usr/bin/env python3
# ! GECICI SURUM v2 - Kitsugi modpack guncelleyici (Kontrol.yml uzerinden calisir)
# ! Bu dosya is bitince orijinal haliyle geri yuklenecektir.
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = "https://github.com/gameras1010-afk/Kitsugi-Plugins"
BRANCH = "mods-cache"
ZIP_NAME = "Kitsugi_Mods_1.21.1_NeoForge.zip"
CACHE = "/tmp/mods_cache"
MERGE = "/tmp/merge_dir"


def run(cmd, **kw):
    print("+ " + (" ".join(cmd) if isinstance(cmd, list) else cmd), flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=kw.pop("cwd", ROOT),
                          check=True, **kw)


def main():
    t0 = time.time()
    os.environ.setdefault("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
    os.environ["GIT_TERMINAL_PROMPT"] = "0"

    # 1) run1 zip'ini mods-cache branch'inden getir
    if os.path.isdir(CACHE):
        shutil.rmtree(CACHE)
    run(["git", "clone", "--depth", "1", "--branch", BRANCH, "--single-branch", REPO, CACHE])
    parts = sorted(p for p in os.listdir(os.path.join(CACHE, "parts")) if p.startswith("part_"))
    print("parts:", len(parts), flush=True)
    zip_path = os.path.join(ROOT, ZIP_NAME)
    with open(zip_path, "wb") as out:
        for p in parts:
            with open(os.path.join(CACHE, "parts", p), "rb") as pf:
                shutil.copyfileobj(pf, out, 1 << 20)
    got = subprocess.run(["sha256sum", zip_path], capture_output=True, text=True,
                         check=True).stdout.split()[0]
    exp = open(os.path.join(CACHE, "parts", "SHA256.txt")).read().split()[0]
    print("sha256 exp:", exp, flush=True)
    print("sha256 got:", got, flush=True)
    assert got == exp, "run1 zip SHA256 MISMATCH"

    # 2) run1 zip'ini ac
    if os.path.isdir(MERGE):
        shutil.rmtree(MERGE)
    os.makedirs(MERGE)
    run(f"unzip -q {zip_path} -d {MERGE}")
    run(f"ls {MERGE} | wc -l")

    # 3) fix listesini indir (modrinth + curseforge)
    run([sys.executable, "mods-fetch/fetch_mods.py", "mods-fetch/modlist_fix.txt", "mods_out2"])

    # 4) birlestir: run1 manifest + run2 manifest
    man1 = json.load(open(os.path.join(MERGE, "manifest.json")))
    man2 = json.load(open(os.path.join("mods_out2", "manifest.json")))
    res1 = man1["results"]
    res2 = man2["results"]
    replaced = {r["requested"] for r in res2}
    # eski (yanlis/secilememis) dosyalari sil
    for r in res1:
        if r["requested"] in replaced and r.get("file_name"):
            p = os.path.join(MERGE, r["file_name"])
            if os.path.exists(p):
                os.remove(p)
                print("silindi (eski):", r["file_name"], flush=True)
    # run2 jar'larini kopyala
    for r in res2:
        if r["status"] == "OK" and r.get("file_name"):
            src = os.path.join("mods_out2", r["file_name"])
            if os.path.exists(src):
                shutil.copy(src, os.path.join(MERGE, r["file_name"]))
    # manifest birlestir
    final_results = [r for r in res1 if r["requested"] not in replaced] + res2
    final_manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "game_version": "1.21.1", "loader": "neoforge",
        "total": len(final_results),
        "ok": len([r for r in final_results if r["status"] == "OK"]),
        "failed": len([r for r in final_results if r["status"] != "OK"]),
        "results": final_results,
    }
    with open(os.path.join(MERGE, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(final_manifest, f, indent=2, ensure_ascii=False)

    # rehber + ozet yaz
    guide = ["KITSUGI MODPACK - GUNCELLEME REHBERI (1.21.1 NeoForge)", "=" * 60,
             "Eski dosya adi -> Yeni (guncel) dosya adi", ""]
    for r in final_results:
        if r["status"] == "OK":
            note = f" [{r.get('source','')}]" if r.get("source") == "curseforge" else ""
            warn = f" [DIKKAT: {r.get('modid_warning')}]" if r.get("modid_warning") else ""
            guide.append(f"{r['requested']}\n    -> {r['file_name']}{note}{warn}")
        else:
            guide.append(f"{r['requested']}\n    -> [SORUN: {r['status']}] {r.get('error', '')}")
    with open(os.path.join(MERGE, "GUNCELLEME_REHBERI.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(guide))

    ok = [r for r in final_results if r["status"] == "OK"]
    bad = [r for r in final_results if r["status"] != "OK"]
    lines = ["KITSUGI MODPACK - GUNCELLEME SONUCU",
             f"Tarih: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
             f"Toplam mod: {len(final_results)} | Basarili: {len(ok)} | Sorunlu: {len(bad)}", ""]
    lines += ["=== SORUNLU ==="]
    for r in bad:
        lines.append(f"[{r['status']}] {r['requested']} {r.get('error', '')} {r.get('slug', '')}")
    with open(os.path.join(MERGE, "OZET.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines), flush=True)

    # 5) final zip + dogrulama
    if os.path.exists(zip_path):
        os.remove(zip_path)
    run(f"cd {MERGE} && zip -q -r -1 {zip_path} . && cd {ROOT}")
    run(f"unzip -t {ZIP_NAME} | tail -1")
    run(f"unzip -l {ZIP_NAME} | tail -1")
    sha = subprocess.run(["sha256sum", ZIP_NAME], capture_output=True, text=True,
                         check=True).stdout.split()[0]
    print("FINAL SHA256:", sha, flush=True)

    # 6) GitHub Release (kullanici indirme sayfasi)
    try:
        tag = "mods-1.21.1-" + time.strftime("%Y%m%d-%H%M%S")
        notes = open(os.path.join(MERGE, "OZET.txt"), encoding="utf-8").read()
        size = os.path.getsize(zip_path)
        if size < 1950000000:
            assets = [zip_path]
        else:
            os.makedirs("parts", exist_ok=True)
            run(f"split -b 90m -d -a 2 {ZIP_NAME} parts/part_")
            assets = [os.path.join("parts", p) for p in sorted(os.listdir("parts")) if p.startswith("part_")]
        assets += [os.path.join(MERGE, "manifest.json"), os.path.join(MERGE, "GUNCELLEME_REHBERI.txt")]
        run(["gh", "release", "create", tag] + assets +
            ["--title", "Kitsugi Mods 1.21.1 NeoForge (guncel)", "--notes", notes])
        print("RELEASE_TAG=" + tag, flush=True)
    except Exception as e:  # noqa: BLE001
        print("release olusturulamadi (onemsiz):", e, flush=True)

    # 7) parcalari mods-cache branch'ine push et
    os.makedirs("parts", exist_ok=True)
    run(f"split -b 90m -d -a 2 {ZIP_NAME} parts/part_")
    with open(os.path.join("parts", "SHA256.txt"), "w") as f:
        f.write(sha + "  " + ZIP_NAME + "\n")
    for extra in ("manifest.json", "GUNCELLEME_REHBERI.txt"):
        shutil.copy(os.path.join(MERGE, extra), os.path.join("parts", extra))
    shutil.copy(os.path.join(MERGE, "OZET.txt"), os.path.join("parts", "OZET.txt"))
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
    run(["git", "checkout", "--orphan", BRANCH])
    run("git rm -rf --quiet . || true")
    for name in sorted(os.listdir("parts")):
        run(f"git add parts/{name}")
    run(["git", "commit", "-m", f"mods cache {time.strftime('%Y%m%d-%H%M%S')}"])
    run(["git", "push", "origin", BRANCH, "--force"])
    ref = os.environ.get("GITHUB_REF_NAME", "")
    if ref:
        run(["git", "checkout", "-f", ref])
    run(f"rm -rf parts mods_out2 {ZIP_NAME}")

    print(f"DONE in {int(time.time() - t0)}s - mods-cache push edildi, SHA256={sha}", flush=True)


if __name__ == "__main__":
    main()
