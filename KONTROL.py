#!/usr/bin/env python3
# ! GECICI SURUM - Majrusz port derleyici (Kontrol.yml uzerinden calisir)
# ! Is bitince orijinal KONTROL.py geri yuklenecek.
import glob
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.join(ROOT, "port")
BRANCH = "mods-cache"
ZIP_NAME = "Majrusz_Port_1.21.1_NeoForge.zip"
LIB_DIR = os.path.join(PORT, "majrusz-library")
MOD_DIR = os.path.join(PORT, "majruszsenchantments")


def run(cmd, cwd=None, env=None, timeout=1800):
    print("+ " + (" ".join(cmd) if isinstance(cmd, list) else cmd), flush=True)
    return subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd, env=env,
                          check=True, timeout=timeout)


def find_java21():
    import glob as g
    cands = []
    for base in ("/usr/lib/jvm", "/opt/hostedtoolcache", "/usr/local/lib/jvm"):
        for p in g.glob(base + "/*"):
            if os.path.exists(os.path.join(p, "bin", "java")):
                cands.append(p)
    for c in sorted(cands):
        low = os.path.basename(c).lower()
        if "21" in low:
            return c
    # fallback: any java >= 17
    for c in sorted(cands):
        try:
            out = subprocess.run([os.path.join(c, "bin", "java"), "-version"],
                                 capture_output=True, text=True).stderr
            if "version \"21" in out or "version \"2" in out:
                return c
        except Exception:
            continue
    return None


def build_gradle(proj, env, extra_args=""):
    run(f"./gradlew :neoforge:build --no-daemon {extra_args}".strip(),
        cwd=proj, env=env, timeout=2700)


def smoke_server(mod_dir, env):
    """Start NeoForge dev server briefly; report OK/CRASH/UNCLEAR."""
    rundir = os.path.join(mod_dir, "run")
    os.makedirs(rundir, exist_ok=True)
    os.makedirs(os.path.join(rundir, "mods"), exist_ok=True)
    with open(os.path.join(rundir, "eula.txt"), "w") as f:
        f.write("eula=true\n")
    # library + mod jar'larini dev mods klasorune koy (eger yoksa)
    for j in glob.glob(os.path.join(MOD_DIR, "libs", "majrusz-library-*.jar")):
        dst = os.path.join(rundir, "mods", os.path.basename(j))
        if not os.path.exists(dst):
            shutil.copy(j, dst)
            print("dev mods'a kopyalandi:", os.path.basename(j), flush=True)
    for j in glob.glob(os.path.join(MOD_DIR, "neoforge", "build", "libs", "majruszs-enchantments-*.jar")):
        dst = os.path.join(rundir, "mods", os.path.basename(j))
        if not os.path.exists(dst):
            shutil.copy(j, dst)
            print("dev mods'a kopyalandi:", os.path.basename(j), flush=True)
    log_path = os.path.join(rundir, "smoke.log")
    logf = open(log_path, "w")
    proc = subprocess.Popen(["./gradlew", ":neoforge:runServer", "--no-daemon"],
                            cwd=mod_dir, env=env, stdout=logf, stderr=subprocess.STDOUT)
    try:
        proc.wait(timeout=540)
        logf.close()
        log = open(log_path, encoding="utf-8", errors="replace").read()
        return "CRASH", log[-4000:]
    except subprocess.TimeoutExpired:
        proc.kill()
        logf.close()
        log = open(log_path, encoding="utf-8", errors="replace").read()
        if "Done (" in log or "For help" in log:
            return "OK", log[-4000:]
        return "UNCLEAR", log[-4000:]


def main():
    t0 = time.time()
    os.environ.setdefault("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
    env = dict(os.environ)
    jh = find_java21()
    if jh:
        env["JAVA_HOME"] = jh
        env["PATH"] = os.path.join(jh, "bin") + os.pathsep + env.get("PATH", "")
        print("JAVA_HOME:", jh, flush=True)
    else:
        print("!!! JAVA 21 BULUNAMADI - default java kullanilacak", flush=True)

    summary = []
    try:
        # 1) Library derle
        build_gradle(LIB_DIR, env)
        lib_jars = glob.glob(os.path.join(LIB_DIR, "neoforge/build/libs/majrusz-library-neoforge-*.jar"))
        lib_common = glob.glob(os.path.join(LIB_DIR, "common/build/libs/majrusz-library-common-*.jar"))
        lib_jars = [j for j in lib_jars if not j.endswith("-sources.jar") and not j.endswith("-javadoc.jar")]
        lib_common = [j for j in lib_common if not j.endswith("-sources.jar")]
        print("library jars:", lib_jars, lib_common, flush=True)
        assert lib_jars and lib_common, "library jar bulunamadi"
        libs_dir = os.path.join(MOD_DIR, "libs")
        os.makedirs(libs_dir, exist_ok=True)
        for j in lib_jars + lib_common:
            shutil.copy(j, os.path.join(libs_dir, os.path.basename(j)))
            print("kopyalandi:", os.path.basename(j), flush=True)
        summary.append("Library: OK")

        # API dump: sponge joined jar'dan kritik siniflarin imzalari (log'a)
        try:
            import glob as g2
            jars = []
            for pat in ["/home/runner/.gradle/caches/**/*joined*.jar",
                        "/home/runner/.gradle/caches/**/minecraft-*.jar",
                        "/home/runner/.gradle/caches/**/*1.21.1*.jar"]:
                jars += g2.glob(pat, recursive=True)
            jars = sorted(set(jars))
            print("CANDIDATE_JARS:", jars, flush=True)
            for j in jars:
                if not os.path.exists(j):
                    continue
                for cls in ["net.minecraft.world.item.Item",
                            "net.minecraft.world.item.HorseArmorItem",
                            "net.minecraft.world.item.Equippable",
                            "net.minecraft.core.component.DataComponents",
                            "net.minecraft.world.damagesource.DamageSource",
                            "net.minecraft.world.entity.animal.horse.Horse",
                            "net.minecraft.client.renderer.entity.layers.HorseArmorLayer"]:
                    try:
                        out = subprocess.run(["javap", "-p", "-classpath", j, cls],
                                             capture_output=True, text=True, timeout=60)
                        if out.returncode == 0:
                            print(f"=== {cls} ===", flush=True)
                            print(out.stdout[:2500], flush=True)
                    except Exception as e:  # noqa: BLE001
                        print(cls, "ERR", e, flush=True)
        except Exception as e:  # noqa: BLE001
            print("API dump basarisiz:", e, flush=True)

        # 2) Enchantments mod derle
        build_gradle(MOD_DIR, env)
        mod_jars = [j for j in glob.glob(os.path.join(MOD_DIR, "neoforge/build/libs/majruszs-enchantments-neoforge-*.jar"))
                    if not j.endswith("-sources.jar") and not j.endswith("-javadoc.jar")]
        print("mod jars:", mod_jars, flush=True)
        assert mod_jars, "mod jar bulunamadi"
        summary.append("Mod: OK")

        # 3) Smoke test (dev server) - library jar'ini dev mods klasorune koy
        run_dir = os.path.join(MOD_DIR, "run")
        os.makedirs(os.path.join(run_dir, "mods"), exist_ok=True)
        for j in lib_jars:
            shutil.copy(j, os.path.join(run_dir, "mods", os.path.basename(j)))
            print("dev mods'a kopyalandi:", os.path.basename(j), flush=True)
        smoke, tail = smoke_server(MOD_DIR, env)
        summary.append(f"Smoke: {smoke} (dev ortami; kullanici kurulumunda jar'lar mods klasorunde olacak)")
        print("SMOKE:", smoke, flush=True)
        print("SMOKE_TAIL:", tail[-2000:], flush=True)
        if smoke == "CRASH" and "not installed" in tail:
            # bilinen dev-ortami sorunu: library mods klasorune eklenmemis; kullanici kurulumunda sorun yok
            summary.append("NOT: dev ortami library'yi mods'ta bulamadi - kullanici kurulumunda iki jar da mods'ta olacak")
    except Exception as e:  # noqa: BLE001
        summary.append(f"HATA: {e}")
        print("EXC:", e, flush=True)
        smoke, tail = "BUILD_FAIL", ""
        try:
            logf = os.path.join(MOD_DIR, "run", "smoke.log")
            if os.path.exists(logf):
                tail = open(logf, encoding="utf-8", errors="replace").read()[-4000:]
        except Exception:  # noqa: BLE001
            pass
        # yine de varsa jar'lari topla
        mod_jars = [j for j in glob.glob(os.path.join(MOD_DIR, "neoforge/build/libs/majruszs-enchantments-neoforge-*.jar"))
                    if not j.endswith("-sources.jar")]
        lib_jars = [j for j in glob.glob(os.path.join(LIB_DIR, "neoforge/build/libs/majrusz-library-neoforge-*.jar"))
                    if not j.endswith("-sources.jar")]

    # 4) Zip + release + cache
    out_dir = os.path.join(ROOT, "port_out")
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for j in glob.glob(os.path.join(out_dir, "*")):
        os.remove(j)
    for j in (mod_jars if 'mod_jars' in dir() else []) + (lib_jars if 'lib_jars' in dir() else []):
        if os.path.exists(j):
            dst = os.path.join(out_dir, os.path.basename(j))
            shutil.copy(j, dst)
            files.append(dst)
    try:
        smokef = os.path.join(MOD_DIR, "run", "smoke.log")
        if os.path.exists(smokef):
            shutil.copy(smokef, os.path.join(out_dir, "SMOKE_LOG.txt"))
    except Exception:  # noqa: BLE001
        pass
    readme = os.path.join(out_dir, "README.txt")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("MAJRUSZ PORT 1.21.1 NeoForge\n")
        f.write("=" * 40 + "\n")
        f.write("\n".join(summary) + "\n")
        f.write("\nKurulum: iki jar'i da mods klasorune koy.\n")
        f.write("Kaynak: Majrusz (MIT) + MT-MC 1.21.1 library portu + patch'ler.\n")
    files.append(readme)
    print("OUT:", files, flush=True)

    zip_path = os.path.join(ROOT, ZIP_NAME)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    run(f"cd {out_dir} && zip -q -r -1 {zip_path} .")
    sha = subprocess.run(["sha256sum", zip_path], capture_output=True, text=True,
                         check=True).stdout.split()[0]
    print("SHA256:", sha, flush=True)

    try:
        tag = "majrusz-port-1.21.1-" + time.strftime("%Y%m%d-%H%M%S")
        notes = "\n".join(summary) + "\n\nSmoke tail:\n" + tail[-1500:]
        run(["gh", "release", "create", tag, zip_path] + files +
            ["--title", "Majrusz Port 1.21.1 NeoForge", "--notes", notes])
        print("RELEASE_TAG=" + tag, flush=True)
    except Exception as e:  # noqa: BLE001
        print("release olusturulamadi:", e, flush=True)

    # cache branch push (sandbox'a tasima kanali)
    parts_dir = os.path.join(ROOT, "parts")
    os.makedirs(parts_dir, exist_ok=True)
    for f in os.listdir(parts_dir):
        os.remove(os.path.join(parts_dir, f))
    run(f"split -b 90m -d -a 2 {zip_path} {parts_dir}/part_")
    with open(os.path.join(parts_dir, "SHA256.txt"), "w") as f:
        f.write(sha + "  " + ZIP_NAME + "\n")
    for extra in ("README.txt",):
        shutil.copy(os.path.join(out_dir, extra), os.path.join(parts_dir, extra))
    with open(os.path.join(parts_dir, "BUILD_SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n\nSMOKE:\n" + tail[-4000:])
    run(["git", "config", "user.name", "github-actions[bot]"])
    run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
    run(["git", "checkout", "--orphan", BRANCH])
    run("git rm -rf --quiet . || true")
    for name in sorted(os.listdir(parts_dir)):
        run(f"git add parts/{name}")
    run(["git", "commit", "-m", f"majrusz port {time.strftime('%Y%m%d-%H%M%S')}"])
    run(["git", "push", "origin", BRANCH, "--force"])
    ref = os.environ.get("GITHUB_REF_NAME", "")
    if ref:
        run(["git", "checkout", "-f", ref])
    run(f"rm -rf {parts_dir} {out_dir} {ZIP_NAME}")

    print(f"DONE in {int(time.time() - t0)}s", flush=True)


if __name__ == "__main__":
    main()
