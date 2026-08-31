import subprocess
import os
import json
import shutil
import re
import hashlib

def calculate_sha256(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha.update(data)
    return f"sha256-{sha.hexdigest()}"


def parse_plugin_gradle(plugin_dir):
    gradle_path = os.path.join(plugin_dir, "build.gradle.kts")
    if not os.path.exists(gradle_path):
        return None
        
    with open(gradle_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extract version
    version_match = re.search(r'version\s*=\s*(\d+)', content)
    version = int(version_match.group(1)) if version_match else 1
    
    # Extract authors
    authors_match = re.search(r'authors\s*=\s*listOf\((.*?)\)', content)
    authors = []
    if authors_match:
        authors = [a.strip().strip('"').strip("'") for a in authors_match.group(1).split(",")]
        
    # Extract language
    lang_match = re.search(r'language\s*=\s*["\'](.*?)["\']', content)
    language = lang_match.group(1) if lang_match else "tr"
    
    # Extract description
    desc_match = re.search(r'description\s*=\s*["\'](.*?)["\']', content)
    description = desc_match.group(1) if desc_match else ""
    
    # Extract tvTypes
    tv_match = re.search(r'tvTypes\s*=\s*listOf\((.*?)\)', content)
    tv_types = []
    if tv_match:
        # Normalize tvTypes like TvType.Movie -> Movie
        raw_types = tv_match.group(1).split(",")
        for t in raw_types:
            clean_t = t.strip().strip('"').strip("'").split(".")[-1]
            if clean_t:
                tv_types.append(clean_t)
        
    # Extract iconUrl
    icon_match = re.search(r'iconUrl\s*=\s*["\'](.*?)["\']', content)
    icon_url = icon_match.group(1) if icon_match else ""
    
    return {
        "name": plugin_dir,
        "internalName": plugin_dir,
        "version": version,
        "description": description,
        "authors": authors,
        "language": language,
        "tvTypes": tv_types,
        "iconUrl": icon_url
    }


def get_changed_plugins():
    changed_files = set()
    try:
        output = subprocess.check_output(["git", "diff", "--name-only", "HEAD~1"], text=True, encoding="utf-8", errors="replace")
        changed_files.update(output.splitlines())
    except Exception as e:
        print(f"[build_changed] git diff HEAD~1 failed: {e}")
        try:
            output = subprocess.check_output(["git", "show", "--name-only", "--pretty=format:"], text=True, encoding="utf-8", errors="replace")
            changed_files.update(output.splitlines())
        except Exception as e2:
            print(f"[build_changed] git show failed: {e2}")
            try:
                output = subprocess.check_output(["git", "status", "--porcelain"], text=True, encoding="utf-8", errors="replace")
                for line in output.splitlines():
                    if len(line) >= 4:
                        changed_files.add(line[3:].strip().strip('"'))
            except Exception as e3:
                print(f"[build_changed] git status failed: {e3}")
                return None

    # We check all modified files. Since we use Python metadata parser, core files modification
    # only triggers full compilation if settings.gradle.kts or root build.gradle.kts was changed.
    core_files = {
        "settings.gradle.kts", 
        "build.gradle.kts", 
        "gradle.properties",
        "build_changed.py"
    }

    force_all = False
    for line in changed_files:
        line = line.strip().replace("\\", "/")
        if not line:
            continue
        if line in core_files or any(line.startswith(p) for p in ("gradle/",)):
            force_all = True
            print(f"[build_changed] Core build file modified ({line}). Forcing rebuild of all plugins.")
            break

    if force_all:
        return None

    changed_plugins = set()
    for line in changed_files:
        line = line.strip().replace("\\", "/")
        if not line:
            continue
        parts = line.split("/")
        plugin_dir = parts[0]
        skip_prefixes = (".", "_", "build", "gradle", "prebuilt")
        skip_files = {"KONTROL.py", "merge_plugins.py", "sync_prebuilt.py",
                      "sync_all_sources.py", "auto_bump.py", "github_push.bat",
                      "add_missing.py", "README.md", "LICENSE", "MiBox.md",
                      "settings.gradle.kts", "build.gradle.kts", "gradle.properties",
                      "local.properties", "gradlew", "gradlew.bat", "_config.yml"}
        
        if not any(plugin_dir.startswith(p) for p in skip_prefixes) and plugin_dir not in skip_files:
            if os.path.exists(os.path.join(plugin_dir, "build.gradle.kts")):
                changed_plugins.add(plugin_dir)

    return changed_plugins


def merge_and_save_metadata(builds_dir, changed_plugins, rebuilt_all=False):
    builds_json_path = os.path.join(builds_dir, "plugins.json")
    prebuilt_json_path = "prebuilt_plugins.json"
    
    # 1. Load existing builds/plugins.json if it exists
    combined = {}
    if os.path.exists(builds_json_path):
        try:
            with open(builds_json_path, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    name = p.get("internalName") or p.get("name")
                    if name:
                        combined[name] = p
        except Exception as e:
            print(f"[build_changed] Error loading builds/plugins.json: {e}")

    # 2. Update with newly compiled plugins metadata (parsed via Python)
    plugins_to_update = []
    if rebuilt_all:
        # Scan all directories containing build.gradle.kts
        for d in os.listdir("."):
            if os.path.isdir(d) and os.path.exists(os.path.join(d, "build.gradle.kts")):
                plugins_to_update.append(d)
    else:
        plugins_to_update = list(changed_plugins)

    for p in plugins_to_update:
        meta = parse_plugin_gradle(p)
        if meta:
            cs3_file = os.path.join(builds_dir, f"{p}.cs3")
            # If the binary exists in builds folder, compute size and hash
            if os.path.exists(cs3_file):
                size = os.path.getsize(cs3_file)
                hash_val = calculate_sha256(cs3_file)
                meta["fileSize"] = size
                meta["fileHash"] = hash_val
                meta["url"] = f"https://raw.githubusercontent.com/gameras1010-afk/Kitsugi-Plugins/builds/{p}.cs3"
                combined[p] = meta
                print(f"  [METADATA UPDATED] {p} (version={meta['version']}, size={size})")
            else:
                if not rebuilt_all:
                    print(f"  [WARNING] Could not find compiled binary to update metadata for {p}: {cs3_file}")

    # 3. Overwrite/update with prebuilt plugins
    if os.path.exists(prebuilt_json_path):
        try:
            with open(prebuilt_json_path, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    name = p.get("internalName") or p.get("name")
                    if name:
                        combined[name] = p
        except Exception as e:
            print(f"[build_changed] Error loading prebuilt plugins: {e}")

    # Write the updated combined JSON back
    try:
        os.makedirs(builds_dir, exist_ok=True)
        with open(builds_json_path, "w", encoding="utf-8") as f:
            json.dump(list(combined.values()), f, indent=4, ensure_ascii=False)
        print(f"[build_changed] Successfully wrote merged manifest to {builds_json_path}. Total: {len(combined)} plugins.")
    except Exception as e:
        print(f"[build_changed] Error writing merged manifest: {e}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    builds_dir = os.path.abspath(os.path.join("..", "builds"))
    if not os.path.exists(os.path.join(builds_dir, "plugins.json")) and os.path.exists("builds"):
        builds_dir = os.path.abspath("builds")
        print(f"[build_changed] Using local builds dir: {builds_dir}")
    else:
        print(f"[build_changed] Using builds dir: {builds_dir}")

    changed_plugins = get_changed_plugins()
    gradle_bin = "gradlew.bat" if os.name == 'nt' else "./gradlew"

    rebuilt_all = False

    if changed_plugins is None:
        print("[build_changed] Rebuilding ALL plugins...")
        rebuilt_all = True
        # Try full build make task
        try:
            subprocess.check_call([gradle_bin, "make"])
        except subprocess.CalledProcessError as e:
            print(f"[build_changed] Gradle build make failed: {e}")
            exit(1)

        # Copy all compiled .cs3 files
        os.makedirs(builds_dir, exist_ok=True)
        copied = 0
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("build", "gradle")]
            for f in files:
                if f.endswith(".cs3") and "build" in root:
                    shutil.copy2(os.path.join(root, f), os.path.join(builds_dir, f))
                    copied += 1
        print(f"[build_changed] Copied {copied} .cs3 plugin binaries to builds/.")

    else:
        if not changed_plugins:
            print("[build_changed] No plugin changes detected. Skipping gradle compile.")
        else:
            print(f"[build_changed] Building modified plugins: {', '.join(changed_plugins)}")
            # Construct build tasks for modified plugins only
            tasks = []
            for p in sorted(changed_plugins):
                tasks.append(f":{p}:make")

            try:
                subprocess.check_call([gradle_bin] + tasks)
            except subprocess.CalledProcessError as e:
                print(f"[build_changed] Gradle build failed for tasks {tasks}: {e}")
                exit(1)

            # Copy only the compiled binaries of changed plugins
            os.makedirs(builds_dir, exist_ok=True)
            copied = 0
            for p in changed_plugins:
                cs3_file = f"{p}/build/{p}.cs3"
                if os.path.exists(cs3_file):
                    shutil.copy2(cs3_file, os.path.join(builds_dir, f"{p}.cs3"))
                    print(f"  [COPIED] {cs3_file} -> {builds_dir}/{p}.cs3")
                    copied += 1
                else:
                    print(f"  [WARNING] Output binary not found: {cs3_file}")
            print(f"[build_changed] Copied {copied}/{len(changed_plugins)} compiled binaries.")

    # Copy prebuilt plugins to builds folder if any are present in local 'prebuilt' directory
    if os.path.exists("prebuilt"):
        os.makedirs(builds_dir, exist_ok=True)
        for f in os.listdir("prebuilt"):
            if f.endswith(".cs3"):
                shutil.copy2(os.path.join("prebuilt", f), os.path.join(builds_dir, f))

    # Merge and update metadata manifest
    merge_and_save_metadata(
        builds_dir=builds_dir,
        changed_plugins=changed_plugins if changed_plugins is not None else set(),
        rebuilt_all=rebuilt_all
    )

if __name__ == '__main__':
    main()
