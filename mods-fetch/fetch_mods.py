#!/usr/bin/env python3
"""
Kitsugi modpack updater: fetch the LATEST 1.21.1 NeoForge version of each mod
listed in modlist_raw.txt from Modrinth, verify integrity, and produce:
  - mods_out/<downloaded jars>
  - mods_out/manifest.json   (requested -> resolved mapping + hashes)
  - mods_out/summary.txt     (human readable result summary)
  - mods_out/GUNCELLEME_REHBERI.txt (Turkish old->new mapping guide)
Usage: fetch_mods.py <modlist> <outdir>
"""
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = "https://api.modrinth.com/v2"
UA = {"User-Agent": "KitsugiModpackUpdater/1.0 (github.com/gameras1010-afk/Kitsugi-Plugins; modpack update tool)"}

STOP = {
    "neoforge", "neo", "forge", "neoforged", "fabric", "quilt", "mc", "v", "jar", "all", "full",
    "universal", "updated", "update", "snapshot", "main", "b", "alpha", "beta", "re",
    "plus", "the", "and", "mod", "mods", "mc1", "patch", "j", "f", "s", "n", "t", "x",
}

# Manual slug overrides: key = filename stem (letters/digits only, lowercased)
OVERRIDES = {
    "tandt": "towns-and-towers",
    "mcwfurniture": "macaws-furniture",
    "mcwlights": "macaws-lights",
    "mcwpaintings": "macaws-paintings",
    "mcwroofs": "macaws-roofs",
    "mcwtrapdoors": "macaws-trapdoors",
    "yungsapi": "yungs-api",
    "yungsbetterdungeons": "yungs-better-dungeons",
    "yungsbetterendisland": "yungs-better-end-island",
    "yungsbetterjungletemples": "yungs-better-jungle-temples",
    "yungsbettermineshafts": "yungs-better-mineshafts",
    "yungsbetternetherfortresses": "yungs-better-nether-fortresses",
    "yungsbetteroceanmonuments": "yungs-better-ocean-monuments",
    "yungsbetterstrongholds": "yungs-better-strongholds",
    "yungsbetterwitchhuts": "yungs-better-witch-huts",
    "yungsbridges": "yungs-bridges",
    "yungsmenutweaks": "yungs-menu-tweaks",
    "repurposedstructures": "repurposed-structures",
    "c2me": "c2me-fabric",
    "connector": "sinytra-connector",
    "connectorextras": "connector-extras",
    "forgifiedfabricapi": "forgified-fabric-api",
    "twilightforest": "the-twilight-forest",
    "alexsmobs": "alexs-mobs",
    "mowziesmobs": "mowzies-mobs",
    "travellersbackpack": "travelers-backpack",
    "ironchest": "iron-chests",
    "storagenetwork": "simple-storage-network",
    "elevatorid": "elevator-id",
    "naturescompass": "natures-compass",
    "architectury": "architectury-api",
    "supermartijn642configlib": "supermartijn642s-config-lib",
    "resourcefulllib": "resourceful-lib",
    "resourcefulconfig": "resourceful-config",
    "uteamcore": "u-team-core",
    "distanthorizons": "distanthorizons",
    "inventoryprofilesnext": "inventory-profiles-next",
    "inventoryhud": "inventory-hud-forge",
    "mousetweaks": "mouse-tweaks",
    "justenoughresources": "just-enough-resources",
    "justenoughprofessions": "just-enough-professions",
    "journeymapwebmap": "journeymap-webmap",
    "betteradvancements": "better-advancements",
    "enchdesc": "enchantment-descriptions",
    "charmofundying": "charm-of-undying",
    "carryon": "carry-on",
    "ironfurnaces": "iron-furnaces",
    "farmersdelight": "farmers-delight",
    "farmersstructures": "farmers-structures",
    "domumornamentum": "domum-ornamentum",
    "everycomp": "every-compat",
    "bettervillage": "better-village",
    "villagesandpillages": "villages-and-pillages",
    "guardvillagers": "guard-villagers",
    "goblintraders": "goblin-traders",
    "betterend": "better-end",
    "betternether": "better-nether",
    "biomesoplenty": "biomes-o-plenty",
    "ohthebiomeswevegone": "oh-the-biomes-weve-gone",
    "ohthetreesyoullgrow": "oh-the-trees-youll-grow",
    "sereneseasons": "serene-seasons",
    "apothicattributes": "apothic-attributes",
    "apotichenchanting": "apothic-enchanting",
    "apothicspawners": "apothic-spawners",
    "dungeoncrawl": "dungeon-crawl",
    "dungeonsandtaverns": "dungeons-and-taverns",
    "treeharvester": "tree-harvester",
    "leavesbegone": "leaves-begone",
    "oreexcavation": "ore-excavation",
    "easyanvils": "easy-anvils",
    "easymagic": "easy-magic",
    "enchantinginfuser": "enchanting-infuser",
    "visualworkbench": "visual-workbench",
    "barteringstation": "bartering-station",
    "stylisheffects": "stylish-effects",
    "mindfuldarkness": "mindful-darkness",
    "resourcepackoverrides": "resource-pack-overrides",
    "configureddefaults": "configured-defaults",
    "deleteworldstotrash": "delete-worlds-to-trash",
    "skeletonairfix": "skeleton-ai-fix",
    "tradingpost": "trading-post",
    "overflowingbars": "overflowing-bars",
    "puzzleslib": "puzzles-lib",
    "bettermodsbutton": "better-mods-button",
    "fancymenu": "fancymenu",
    "distractionfreerecipes": "distraction-free-recipes",
    "longerchathistory": "longer-chat-history",
    "continuity": "continuity",
    "lambdynamiclights": "lambdynamiclights",
    "alternatecurrent": "alternate-current",
    "badoptimizations": "badoptimizations",
    "ferritecore": "ferritecore",
    "modernfix": "modernfix",
    "noisium": "noisium",
    "lithium": "lithium",
    "servercore": "servercore",
    "spark": "spark",
    "entityculling": "entityculling",
    "immediatelyfast": "immediatelyfast",
    "notenoughanimations": "not-enough-animations",
    "entitymodelfeatures": "entity-model-features",
    "entitytexturefeatures": "entity-texture-features",
    "skinlayers3d": "skin-layers-3d",
    "playeranimationlib": "player-animation-lib",
    "playeranimatorapi": "playeranimator",
    "geckolib": "geckolib",
    "citadel": "citadel",
    "balm": "balm",
    "bookshelf": "bookshelf",
    "clothconfig": "cloth-config",
    "corgilib": "corgilib",
    "craterlib": "craterlib",
    "creativecore": "creativecore",
    "curios": "curios",
    "cristellib": "cristel-lib",
    "athena": "athena",
    "glitchcore": "glitchcore",
    "kotlinforforge": "kotlin-for-forge",
    "owolib": "owo-lib",
    "midnightlib": "midnightlib",
    "searchables": "searchables",
    "neruina": "neruina",
    "skinrestorer": "skin-restorer",
    "highlighter": "highlighter",
    "handcrafted": "handcrafted",
    "chipped": "chipped",
    "waystones": "waystones",
    "gravestone": "gravestone",
    "levelhearts": "level-hearts",
    "polymorph": "polymorph",
    "comforts": "comforts",
    "iceberg": "iceberg",
    "controlling": "controlling",
    "jade": "jade",
    "jei": "jei",
    "journeymap": "journeymap",
    "appleskin": "appleskin",
    "eatinganimation": "eating-animation",
    "itemphysic": "itemphysic",
    "ambientsounds": "ambientsounds",
    "fpsreducer2": "fps-reducer",
    "soundphysicsremastered": "sound-physics-remastered",
    "pingwheel": "ping-wheel",
    "chatheads": "chat-heads",
    "bobby": "bobby",
    "iris": "iris",
    "reesessodiumoptions": "reeses-sodium-options",
    "sodiumextra": "sodium-extra",
    "sodium": "sodium",
    "aether": "aether",
    "deeperdarker": "deeper-darker",
    "naturalist": "naturalist",
    "terralith": "terralith",
    "terrablender": "terrablender",
    "quark": "quark",
    "zeta": "zeta",
    "apotheosis": "apotheosis",
    "placebo": "placebo",
    "lithostitched": "lithostitched",
    "lootr": "lootr",
    "chunky": "chunky",
    "reap": "reap-mod",
    "advancednetherite": "advanced-netherite",
    "aquaculture": "aquaculture",
    "supplementaries": "supplementaries",
    "amendments": "amendments",
    "moonlight": "moonlight",
    "cyclic": "cyclic",
    "usefulbackpacks": "useful-backpacks",
    "travelersbackpack": "travelers-backpack",
    "carryon": "carry-on",
    "explorify": "explorify",
    "elevatorid": "elevator-id",
    "skeletonairfix": "skeleton-ai-fix",
}


def get_json(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                last = e
                time.sleep(3 * (i + 1))
                continue
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise last


def clean_token(t):
    t = re.sub(r"^mc\d[\d.]*", "", t)          # mc1.21.1neoforge -> neoforge
    t = re.sub(r"^(?:v)?\d+(?:\.\d+)*", "", t)  # 1.21.1neoforge -> neoforge
    t = re.sub(r"(?:neoforged|neoforge|forge|fabric|quilt)(?:\d+)?(?:update|updated)?$", "", t)  # neoforge1211update
    t = re.sub(r"(?:nf|nfo|neo)\d+$", "", t)    # betterworldloadingnf21 -> betterworldloading
    t = re.sub(r"\d+$", "", t)                  # skinlayers3d -> skinlayers
    return t


def stem_and_query(name):
    s = name.lower().replace(".jar", "")
    s = s.replace("[", " ").replace("]", " ")
    toks = re.split(r"[-_.+() ]+", s)
    all_tokens, query_tokens = [], []
    for t in toks:
        t = t.strip()
        if not t:
            continue
        if re.fullmatch(r"v?\d+(\.\d+)*([a-z0-9]+)?", t) and re.search(r"\d", t):
            t2 = clean_token(t)
            if not t2:
                continue
            t = t2
        else:
            t = clean_token(t)
        t = t.strip("-_")
        if len(t) < 2 and not (len(t) == 1 and t.isalpha()):
            continue
        all_tokens.append(t)
        if len(t) >= 2 and t not in STOP:
            query_tokens.append(t)
    return "".join(all_tokens), " ".join(query_tokens)


def hit_score(query_tokens, hit):
    title_tokens = set()
    for w in re.split(r"[^a-z0-9]+", (hit.get("title") or "").lower()):
        if len(w) >= 2:
            title_tokens.add(w)
    for w in (hit.get("slug") or "").replace("-", " ").split():
        if len(w) >= 2:
            title_tokens.add(w)
    q = set(query_tokens)
    inter = q & title_tokens
    if not inter:
        return 0.0
    recall = len(inter) / max(1, len(q))
    precision = len(inter) / max(1, len(title_tokens))
    score = 0.6 * recall + 0.4 * precision
    # slug bonus
    qjoin = "".join(query_tokens)
    if qjoin and qjoin in (hit.get("slug") or "").replace("-", ""):
        score = max(score, 0.9)
    return score


def resolve_project(name):
    """Return (slug, title, source) where source in {'override','search'}."""
    stem, query = stem_and_query(name)
    if stem in OVERRIDES:
        return OVERRIDES[stem], query, "override"
    params = urllib.parse.urlencode({
        "query": query,
        "limit": 10,
        "facets": json.dumps([["versions:1.21.1"], ["categories:neoforge"]]),
    })
    hits = get_json(f"{API}/search?{params}").get("hits", [])
    if not hits:
        return None, query, "search"
    qt = query.split()
    best, best_s = None, 0.0
    for h in hits:
        s = hit_score(qt, h)
        if s > best_s:
            best, best_s = h, s
    if best is None or best_s < 0.55:
        return None, query, "search"
    return best["slug"], query, "search"


def latest_version(slug):
    """Return (version_dict, loader_list_used) for 1.21.1, or (None,None)."""
    for loaders in (["neoforge"], ["forge"], None):
        url = f"{API}/project/{slug}/version?game_versions=" + urllib.parse.quote(json.dumps(["1.21.1"]))
        if loaders is not None:
            url += "&loaders=" + urllib.parse.quote(json.dumps(loaders))
        try:
            vs = get_json(url)
        except Exception:  # noqa: BLE001
            vs = []
        if not vs:
            continue
        vs.sort(key=lambda v: v.get("date_published", ""), reverse=True)
        for typ in ("release", "beta"):
            for v in vs:
                if v.get("version_type") == typ:
                    return v, loaders
        return vs[0], loaders
    return None, None


def download_file(url, dest, sha1_expected, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                h = hashlib.sha1()
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
                    f.write(chunk)
            if sha1_expected and h.hexdigest() != sha1_expected:
                raise ValueError(f"sha1 mismatch: {h.hexdigest()} != {sha1_expected}")
            return True
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    return False


def detect_modid(jar_path):
    try:
        with zipfile.ZipFile(jar_path) as z:
            for cand in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml", "fabric.mod.json", "quilt.mod.json"):
                try:
                    data = z.read(cand).decode("utf-8", "replace")
                except KeyError:
                    continue
                if cand.endswith(".toml"):
                    m = re.search(r"^\s*modId\s*=\s*[\"']([^\"']+)[\"']", data, re.M)
                    if m:
                        return m.group(1), cand
                else:
                    m = re.search(r"\"id\"\s*:\s*\"([^\"]+)\"", data)
                    if m:
                        return m.group(1), cand
    except Exception:  # noqa: BLE001
        pass
    return None, None


def main():
    modlist_path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    names = [ln.strip() for ln in open(modlist_path, encoding="utf-8") if ln.strip().endswith(".jar")]
    results = []
    failures = []

    for idx, name in enumerate(names, 1):
        slug, query, src = resolve_project(name)
        rec = {"requested": name, "stem_query": query, "resolve_source": src, "slug": slug}
        if slug is None:
            rec["status"] = "NOT_FOUND_ON_MODRINTH"
            failures.append(rec)
            results.append(rec)
            print(f"[{idx:03d}/{len(names)}] NOT FOUND: {name} (query='{query}')", flush=True)
            continue
        ver, loaders = latest_version(slug)
        if ver is None:
            rec["status"] = "NO_1_21_1_VERSION"
            failures.append(rec)
            results.append(rec)
            print(f"[{idx:03d}/{len(names)}] NO 1.21.1 VER: {name} -> {slug}", flush=True)
            continue
        f0 = ver["files"][0]
        rec.update({
            "status": "OK",
            "modrinth_url": f"https://modrinth.com/project/{slug}",
            "title": ver.get("name") or slug,
            "version_id": ver["id"],
            "version_number": ver.get("version_number", ""),
            "version_type": ver.get("version_type", ""),
            "loaders_used": loaders or ver.get("loaders", []),
            "file_name": f0["filename"],
            "file_url": f0["url"],
            "file_size": f0.get("size"),
            "sha1": (f0.get("hashes") or {}).get("sha1", ""),
            "sha512": (f0.get("hashes") or {}).get("sha512", ""),
        })
        results.append(rec)
        print(f"[{idx:03d}/{len(names)}] OK: {name}\n      -> {rec['title']} v{rec['version_number']} [{ver.get('version_type')}] loader={loaders} file={f0['filename']}", flush=True)
        time.sleep(0.25)

    # ---- download phase (parallel) ----
    ok_recs = [r for r in results if r["status"] == "OK"]

    def work(rec):
        dest = os.path.join(outdir, rec["file_name"])
        try:
            ok = download_file(rec["file_url"], dest, rec.get("sha1"))
            if not ok:
                return rec, False, "download failed"
            if not zipfile.is_zipfile(dest):
                return rec, False, "not a valid zip/jar"
            mid, mf = detect_modid(dest)
            rec["detected_modid"], rec["detected_meta"] = mid, mf
            return rec, True, ""
        except Exception as e:  # noqa: BLE001
            return rec, False, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(work, r): r for r in ok_recs}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            rec, ok, err = fut.result()
            done += 1
            if not ok:
                rec["status"] = "DOWNLOAD_FAILED"
                rec["error"] = err
                failures.append(rec)
                print(f"[dl {done}/{len(ok_recs)}] FAILED: {rec['file_name']} ({err})", flush=True)
            else:
                print(f"[dl {done}/{len(ok_recs)}] OK: {rec['file_name']} ({rec['detected_modid']})", flush=True)

    # ---- outputs ----
    manifest_path = os.path.join(outdir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                   "game_version": "1.21.1", "loader": "neoforge",
                   "total": len(names), "ok": len([r for r in results if r["status"] == "OK"]),
                   "failed": len(failures), "results": results}, f, indent=2, ensure_ascii=False)

    ok_count = len([r for r in results if r["status"] == "OK"])
    lines = [
        "KITSUGI MODPACK - MOD GUNCELLEME SONUCU",
        f"Tarih: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"Toplam mod: {len(names)} | Basarili: {ok_count} | Sorunlu: {len(failures)}",
        "",
        "=== BASARILI (en guncel 1.21.1 NeoForge) ===",
    ]
    for r in results:
        if r["status"] == "OK":
            lines.append(f"[OK] {r['requested']}")
            lines.append(f"     -> {r['title']} v{r['version_number']} ({r['version_type']}) loader={r['loaders_used']}")
            lines.append(f"     -> dosya: {r['file_name']} (modid: {r.get('detected_modid')})")
    lines.append("")
    lines.append("=== SORUNLU / INCELEME GEREKEN ===")
    for r in failures:
        lines.append(f"[{r['status']}] {r['requested']} (slug={r.get('slug')} query='{r.get('stem_query')}' err={r.get('error', '')})")
    with open(os.path.join(outdir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    guide = [
        "KITSUGI MODPACK - GUNCELLEME REHBERI (1.21.1 NeoForge)",
        "=" * 60,
        "Eski dosya adi -> Yeni (guncel) dosya adi",
        "",
    ]
    for r in results:
        if r["status"] == "OK":
            guide.append(f"{r['requested']}\n    -> {r['file_name']}   [{r['title']} v{r['version_number']}]")
        else:
            guide.append(f"{r['requested']}\n    -> [SORUN: {r['status']}] {r.get('error', '')}")
    with open(os.path.join(outdir, "GUNCELLEME_REHBERI.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(guide))

    print("\n================ RESULT ================")
    print(f"Total: {len(names)}  OK: {ok_count}  Failed: {len(failures)}")
    for r in failures:
        print(f"  FAIL: [{r['status']}] {r['requested']} -> {r.get('slug')} {r.get('error', '')}")
    print("manifest: ", manifest_path)


if __name__ == "__main__":
    main()
