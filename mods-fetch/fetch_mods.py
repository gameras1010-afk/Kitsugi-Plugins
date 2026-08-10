#!/usr/bin/env python3
"""
Kitsugi modpack updater v2: fetch the LATEST 1.21.1 NeoForge version of each mod.
Sources: Modrinth API (primary), CurseForge (fallback for CF-only mods).
Produces: <outdir>/jars + manifest.json + summary.txt + GUNCELLEME_REHBERI.txt
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
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 KitsugiModpackUpdater/1.0"}

STOP = {
    "neoforge", "neo", "forge", "neoforged", "fabric", "quilt", "mc", "v", "jar", "all", "full",
    "universal", "updated", "update", "snapshot", "main", "b", "alpha", "beta", "re",
    "plus", "the", "and", "mod", "mods", "mc1", "patch", "j", "f", "s", "n", "x",
}

# key = filename stem (letters/digits, lowercased) -> Modrinth slug
OVERRIDES = {
    "tandt": "towns-and-towers",
    "advancementplaques": "advancement-plaques",
    "betterend": "betterend-neoforge",
    "betternether": "betternether-neoforge",
    "bookshelf": "bookshelf-lib",
    "ferritecore": "ferrite-core",
    "repurposedstructures": "repurposed-structures-forge",
    "elevatorid": "elevatormod",
    "gravestone": "gravestone-mod",
    "deeperdarker": "deeperdarker",
    "skinlayers3d": "3dskinlayers",
    "skinrestorer": "skinrestorer",
    "dungeoncrawl": "dungeoncrawl",
    "inventoryhud": "inventoryhudplus",
    "justenoughprofessions": "just-enough-professions-jep",
    "justenoughresources": "just-enough-resources-jer",
    "leavesbegone": "leaves-be-gone",
    "skeletonairfix": "skeleton-ai-fix",
    "skeletonaifix": "skeleton-ai-fix",
    "mcwlights": "macaws-lights-and-lamps",
    "playeranimationlib": "player-animation-library",
    "travelersbackpack": "travelersbackpack",
    "entitytexturefeatures": "entitytexturefeatures",
    "fpsreducer": "fps-reducer",
    "drippyloadingscreen": "drippy-loading-screen",
    "drippyloadingscreenmc": "drippy-loading-screen",
    "fancyenchantments": "fancy-enchantments",
    "konkrete": "konkrete",
    "elitekonkrete": "konkrete",
    "elitekonkretemc": "konkrete",
    "libraryferret": "library-ferret",
    "luna": "luna",
    "lunaminecraft": "luna",
    "morevanillashields": "more-vanilla-shields",
    "particleeffects": "particle-effects",
    "kotlinforforge": "kotlin-for-forge",
    "kotlinforall": "kotlin-for-forge",
    "kotlinfor": "kotlin-for-forge",
    "inventoryessentials": "inventory-essentials",
    "bettercompatabilitychecker": "better-compatibility-checker",
    "betterworldloading": "better-world-loading",
    "apotichenchanting": "apothic-enchanting",
    "athena": "athena-ctm",
    "moreandmorearmor": "morearmor",
    "mcwfurniture": "macaws-furniture",
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
    "c2me": "c2me-fabric",
    "connector": "sinytra-connector",
    "connectorextras": "connector-extras",
    "forgifiedfabricapi": "forgified-fabric-api",
    "twilightforest": "CF:the-twilight-forest",
    "alexsmobs": "CF:alexs-mobs",
    "mowziesmobs": "mowzies-mobs",
    "ironchest": "CF:iron-chests",
    "storagenetwork": "simple-storage-network",
    "naturescompass": "natures-compass",
    "architectury": "architectury-api",
    "supermartijn642configlib": "supermartijn642s-config-lib",
    "resourcefulllib": "resourceful-lib",
    "resourcefulconfig": "resourceful-config",
    "uteamcore": "u-team-core",
    "distanthorizons": "distanthorizons",
    "inventoryprofilesnext": "inventory-profiles-next",
    "mousetweaks": "mouse-tweaks",
    "journeymapwebmap": "CF:journeymap-webmap",
    "betteradvancements": "better-advancements",
    "enchdesc": "enchantment-descriptions",
    "charmofundying": "charm-of-undying",
    "carryon": "carry-on",
    "ironfurnaces": "iron-furnaces",
    "farmersdelight": "farmers-delight",
    "farmersstructures": "CF:farmers-structures",
    "domumornamentum": "CF:domum-ornamentum",
    "everycomp": "every-compat",
    "bettervillage": "better-village",
    "villagesandpillages": "villages-and-pillages",
    "guardvillagers": "guard-villagers",
    "goblintraders": "CF:goblin-traders",
    "biomesoplenty": "biomes-o-plenty",
    "ohthebiomeswevegone": "oh-the-biomes-weve-gone",
    "ohthetreesyoullgrow": "oh-the-trees-youll-grow",
    "sereneseasons": "serene-seasons",
    "apothicattributes": "apothic-attributes",
    "apothicspawners": "apothic-spawners",
    "apothicenchanting": "apothic-enchanting",
    "dungeonsandtaverns": "dungeons-and-taverns",
    "awesomedungeonocean": "CF:awesome-dungeon-ocean",
    "structureessentials": "CF:structure-essentials",
    "structurelayoutoptimizer": "structure-layout-optimizer",
    "ftbquests": "CF:ftb-quests-forge",
    "ftblibrary": "CF:ftb-library-forge",
    "ftbteams": "CF:ftb-teams-forge",
    "treeharvester": "tree-harvester",
    "oreexcavation": "CF:ore-excavation",
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
    "modernfix": "modernfix",
    "noisium": "noisium",
    "lithium": "lithium",
    "servercore": "servercore",
    "spark": "spark",
    "entityculling": "entityculling",
    "immediatelyfast": "immediatelyfast",
    "notenoughanimations": "not-enough-animations",
    "entitymodelfeatures": "entity-model-features",
    "playeranimatorapi": "playeranimator",
    "geckolib": "geckolib",
    "citadel": "citadel",
    "balm": "balm",
    "clothconfig": "cloth-config",
    "corgilib": "corgilib",
    "craterlib": "craterlib",
    "creativecore": "creativecore",
    "curios": "curios",
    "cristellib": "cristel-lib",
    "glitchcore": "glitchcore",
    "owolib": "owo-lib",
    "midnightlib": "midnightlib",
    "searchables": "searchables",
    "neruina": "neruina",
    "highlighter": "CF:item-highlighter",
    "handcrafted": "handcrafted",
    "chipped": "chipped",
    "waystones": "waystones",
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
    "soundphysicsremastered": "sound-physics-remastered",
    "pingwheel": "ping-wheel",
    "chatheads": "chat-heads",
    "bobby": "bobby",
    "iris": "iris",
    "reesessodiumoptions": "reeses-sodium-options",
    "sodiumextra": "sodium-extra",
    "sodium": "sodium",
    "aether": "aether",
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
    "explorify": "explorify",
    "morearmor": "CF:more-armor-new-armors-tools-ores",
    "lavatrident": "CF:lavatrident",
    "logbegone": "CF:logbegone",
    "lootintegrations": "CF:loot-integrations",
    "lootintegrationsyungs": "CF:loot-integrations-yungs",
    "simplerpc": "simple-discord-rpc",
    "zetafix": "CF:zetafix",
    "cupboard": "CF:cupboard",
    "gml": "CF:gml",
    "acedium": "CF:acedium",
    "framework": "CF:framework",
    "extragolemsreborn": "CF:extra-golems-reborn",
    "twilightforestuniversal": "CF:the-twilight-forest",
    "domumornamentumsnapshotmain": "CF:domum-ornamentum",
}

# CF slugs where my primary guess may be wrong: stem -> list of candidate CF slugs
CF_CANDIDATES = {
    "structureessentials": ["structure-essentials-forge-fabric", "structure-essentials", "structureessentials"],
    "lootintegrationsyungs": ["yung-structures-addon-for-loot-integrations", "loot-integrations-yungs", "lootintegrations-yungs"],
    "acedium": ["acedium-sodiumized", "acedium"],
    "awesomedungeonocean": ["awesome-dungeon-edition-ocean-neoforge", "awesome-dungeon-ocean", "awesome-dungeon"],
    "journeymapwebmap": ["journeymap-web-map", "journeymap-webmap"],
    "logbegone": ["log-begone", "logbegone", "log-be-gone"],
    "ironchest": ["iron-chests", "ironchest"],
    "ftblibrary": ["ftb-library-forge", "ftb-library"],
    "ftbteams": ["ftb-teams-forge", "ftb-teams"],
    "highlighter": ["item-highlighter"],
    "twilightforest": ["the-twilight-forest"],
    "alexsmobs": ["alexs-mobs"],
    "farmersstructures": ["farmers-structures"],
    "domumornamentum": ["domum-ornamentum"],
    "goblintraders": ["goblin-traders"],
    "oreexcavation": ["ore-excavation"],
    "lavatrident": ["lavatrident", "lava-trident"],
    "lootintegrations": ["loot-integrations", "lootintegrations"],
    "morearmor": ["more-armor-new-armors-tools-ores", "more-armor"],
    "zetafix": ["zetafix"],
    "cupboard": ["cupboard"],
    "gml": ["gml", "groovymodloader"],
    "framework": ["framework"],
    "extragolemsreborn": ["extra-golems-reborn", "extra-golems"],
    "ftbquests": ["ftb-quests-forge", "ftb-quests"],
}

# stem -> expected modid (warning only; mismatch recorded but file kept)
EXPECTED_MODID = {
    "betterend": "betterend", "betternether": "betternether", "bookshelf": "bookshelf",
    "ferritecore": "ferritecore", "repurposedstructures": "repurposed_structures",
    "elevatorid": "elevatorid", "gravestone": "gravestone", "deeperdarker": "deeperdarker",
    "skinlayers3d": "skinlayers3d", "skinrestorer": "skinrestorer",
    "dungeoncrawl": "dungeoncrawl", "justenoughprofessions": "jep",
    "justenoughresources": "jeresources", "leavesbegone": "leavesbegone",
    "skeletonairfix": "skeletonfix", "mcwlights": "mcwlights",
    "playeranimationlib": "player_animation_lib", "travelersbackpack": "travelersbackpack",
    "entitytexturefeatures": "entitytexturefeatures", "fpsreducer": "fpsreducer",
    "drippyloadingscreen": "drippyloadingscreen", "fancyenchantments": "fancyenchantments",
    "elitekonkrete": "konkrete", "libraryferret": "libraryferret", "luna": "luna",
    "morevanillashields": "morevanillashields", "particleeffects": "particleeffects",
    "kotlinforforge": "kotlinforforge", "inventoryessentials": "inventoryessentials",
    "bettercompatabilitychecker": "bettercompatibilitychecker",
    "betterworldloading": "betterworldloading", "athena": "athena",
    "moreandmorearmor": "morearmor", "advancementplaques": "advancementplaques",
    "apotichenchanting": "apothic_enchanting",
}

CF_HEADERS = {"User-Agent": UA["User-Agent"], "Accept-Language": "en-US,en;q=0.9"}


def http_get(url, headers=None, tries=5, timeout=60):
    last = None
    hdrs = dict(UA)
    if headers:
        hdrs.update(headers)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
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


def get_json(url, tries=5):
    return json.loads(http_get(url, tries=tries).decode("utf-8", "replace"))


def clean_token(t):
    t = re.sub(r"^mc\d[\d.]*", "", t)
    t = re.sub(r"^(?:v)?\d+(?:\.\d+)*", "", t)
    t = re.sub(r"(?:neoforged|neoforge|forge|fabric|quilt)(?:\d+)?(?:update|updated)?$", "", t)
    t = re.sub(r"(?:nf|nfo|neo)\d+$", "", t)
    t = re.sub(r"\d+$", "", t)
    return t


def stem_and_query(name):
    s = name.lower().replace(".jar", "")
    s = s.replace("[", " ").replace("]", " ")
    toks = re.split(r"[-_.+() ]+", s)
    stem_keep = {"and", "the", "for", "mod", "mods"}
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
        if len(t) >= 2 and (t not in STOP or t in stem_keep):
            all_tokens.append(t)
        elif len(t) == 1 and t.isalpha():
            all_tokens.append(t)
        if len(t) >= 2 and (t in stem_keep or t not in STOP):
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
    qjoin = "".join(query_tokens)
    if qjoin and qjoin in (hit.get("slug") or "").replace("-", ""):
        score = max(score, 0.9)
    return score


def search_modrinth(query):
    params = urllib.parse.urlencode({
        "query": query, "limit": 8,
        "facets": json.dumps([["versions:1.21.1"], ["categories:neoforge"]]),
    })
    return get_json(f"{API}/search?{params}").get("hits", [])


def resolve_project(name):
    """Return ('modrinth', slug) or ('curseforge', slug_list) or None."""
    stem, query = stem_and_query(name)
    if stem in OVERRIDES:
        v = OVERRIDES[stem]
        if v.startswith("CF:"):
            slugs = CF_CANDIDATES.get(stem, [v[3:]])
            return ("curseforge", slugs)
        return ("modrinth", v)
    try:
        hits = search_modrinth(query)
    except Exception:  # noqa: BLE001
        hits = []
    if hits:
        qt = query.split()
        best, best_s = None, 0.0
        for h in hits:
            s = hit_score(qt, h)
            if s > best_s:
                best, best_s = h, s
        if best and best_s >= 0.6:
            return ("modrinth", best["slug"])
    return None


def modrinth_latest(slug):
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


# Hardcoded CF project IDs (fallback when cfwidget/legacy fail) - keyed by CF slug
CF_PIDS = {
    "ftb-quests-forge": 289412, "ftb-library-forge": 404465, "ftb-teams-forge": 404468,
    "the-twilight-forest": 227639, "iron-chests": 228756,
    "more-armor-new-armors-tools-ores": 1431856, "goblin-traders": 363703,
    "structure-essentials-forge-fabric": 832882, "acedium-sodiumized": 1577618,
    "awesome-dungeon-edition-ocean-neoforge": 533528,
    "yung-structures-addon-for-loot-integrations": 1012211,
}


def has_exact_version(values, target="1.21.1"):
    """Exact game-version match: '1.21.1' must appear as its own token."""
    if isinstance(values, list):
        return target in [str(v) for v in values]
    return target in set(re.findall(r"\d+(?:\.\d+)+", str(values)))


def cf_parse_legacy_page(html):
    """Parse a legacy.curseforge.com files/all page -> list of (fileId, display, gamever)."""
    rows = []
    for m in re.finditer(r'<tr[^>]*>(.*?)</tr>', html, re.S):
        row = m.group(1)
        fm = re.search(r'/files/(\d+)', row)
        if not fm:
            continue
        texts = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        cells = [re.sub(r'<[^>]+>', ' ', c).strip() for c in texts]
        rows.append({"file_id": int(fm.group(1)), "cells": cells})
    return rows


def cf_api_pick(pid, diag, tag="1.21.1", loader="neoforge"):
    """Query www CF API for files; return first exact-match release file."""
    lt = {"neoforge": 6, "forge": 1}.get(loader, 6)
    for page in range(3):
        try:
            api = get_json(f"https://www.curseforge.com/api/v1/mods/{pid}/files"
                           f"?gameVersion={tag}&modLoaderType={lt}&pageSize=50&index={page * 50}", tries=2)
        except Exception as e:  # noqa: BLE001
            diag.append(f"api {pid} p{page}: {e}")
            return None
        files = api.get("data") or []
        if not files:
            break
        exact = [f for f in files if has_exact_version(f.get("gameVersions") or [], tag)]
        if exact:
            rel = [f for f in exact if f.get("releaseType") == 1]
            return (rel or exact)[0]
    return None


def cf_find_file(slug_candidates, diag):
    """Find newest 1.21.1 NeoForge file of a CF project.
    Chain: legacy files page (paginated) -> cfwidget+API -> hardcoded pid + API."""
    # --- attempt 1: legacy files page (no pid needed) ---
    for slug in slug_candidates:
        found_page = False
        for page in range(1, 6):
            try:
                html = http_get(f"https://legacy.curseforge.com/minecraft/mc-mods/{slug}/files/all?page={page}&pageSize=50",
                                headers=CF_HEADERS, timeout=90).decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                diag.append(f"legacy {slug} p{page}: {e}")
                break
            if "File Details" not in html and "/files/" not in html:
                if page == 1:
                    diag.append(f"legacy {slug}: not found")
                break
            found_page = True
            for row in cf_parse_legacy_page(html):
                cells = row["cells"]
                if len(cells) < 5 or not has_exact_version(cells[4]):
                    continue
                try:
                    fhtml = http_get(f"https://legacy.curseforge.com/minecraft/mc-mods/{slug}/files/{row['file_id']}",
                                     headers=CF_HEADERS, timeout=90).decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    continue
                fname = re.search(r"Filename\s*[:]?\s*(?:</?[^>]+>\s*)*([^<>\s]+\.jar)", fhtml)
                if not fname or "NeoForge" not in fhtml:
                    continue
                return {"file_id": row["file_id"], "file_name": fname.group(1).strip(),
                        "slug": slug, "cf_id": CF_PIDS.get(slug), "source": "legacy"}
        if not found_page:
            continue
        diag.append(f"legacy {slug}: no exact 1.21.1 NeoForge file")
    # --- attempt 2: cfwidget -> pid, then www API ---
    for slug in slug_candidates:
        try:
            data = get_json(f"https://api.cfwidget.com/minecraft/mc-mods/{slug}", tries=2)
            pid = data.get("id")
        except Exception as e:  # noqa: BLE001
            diag.append(f"cfwidget {slug}: {e}")
            continue
        if not pid:
            diag.append(f"cfwidget {slug}: empty")
            continue
        f = cf_api_pick(pid, diag)
        if f:
            return {"file_id": f["id"], "file_name": f.get("fileName"),
                    "slug": slug, "cf_id": pid, "source": "api"}
        f = cf_api_pick(pid, diag, tag="1.21", loader="neoforge")
        if f:
            return {"file_id": f["id"], "file_name": f.get("fileName"),
                    "slug": slug, "cf_id": pid, "source": "api", "note": "1.21 build (1.21.1 yok)"}
        diag.append(f"api {pid}: no exact 1.21.1 file")
    # --- attempt 3: hardcoded pid + www API ---
    for slug in slug_candidates:
        pid = CF_PIDS.get(slug)
        if not pid:
            continue
        f = cf_api_pick(pid, diag)
        if f:
            return {"file_id": f["id"], "file_name": f.get("fileName"),
                    "slug": slug, "cf_id": pid, "source": "api"}
        f = cf_api_pick(pid, diag, tag="1.21", loader="neoforge")
        if f:
            return {"file_id": f["id"], "file_name": f.get("fileName"),
                    "slug": slug, "cf_id": pid, "source": "api", "note": "1.21 build (1.21.1 yok)"}
        diag.append(f"hardcoded {slug} ({pid}): no exact 1.21.1 file")
    return None


def cf_download(cfg, outdir):
    diag = []
    info = cf_find_file(cfg["slugs"], diag)
    if info is None:
        return None, "CF bulunamadi | " + " | ".join(diag[-6:])
    fid = info["file_id"]
    fname = info["file_name"]
    dest = os.path.join(outdir, fname)
    urls = [
        ("edge.forgecdn.net", f"https://edge.forgecdn.net/files/{fid // 1000}/{fid % 1000}/" + urllib.parse.quote(fname, safe='')),
        ("media.forgecdn.net", f"https://media.forgecdn.net/files/{fid // 1000}/{fid % 1000}/" + urllib.parse.quote(fname, safe='')),
        ("cursemaven", f"https://cursemaven.com/curse/maven/{info.get('slug','mod')}-{info.get('cf_id') or 0}/{fid}/{info.get('slug','mod')}-{info.get('cf_id') or 0}-{fid}.jar"),
    ]
    hdrs = dict(CF_HEADERS)
    hdrs["Referer"] = "https://www.curseforge.com/"
    for label, u in urls:
        try:
            data = http_get(u, headers=hdrs, timeout=300)
            if len(data) < 1000:
                continue
            with open(dest, "wb") as f:
                f.write(data)
            return {"file_name": fname, "file_id": fid,
                    "project_id": info.get("cf_id"), "cf_slug": info.get("slug"),
                    "download_host": label, "note": info.get("note", "")}, None
        except Exception as e:  # noqa: BLE001
            diag.append(f"{label}: {e}")
    return None, "indirme basarisiz | " + " | ".join(diag[-6:])


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

    for idx, name in enumerate(names, 1):
        stem, _ = stem_and_query(name)
        rec = {"requested": name, "stem": stem}
        resolved = resolve_project(name)
        if resolved is None:
            rec["status"] = "NOT_FOUND"
            results.append(rec)
            print(f"[{idx:03d}/{len(names)}] NOT_FOUND: {name}", flush=True)
            continue
        source, target = resolved
        try:
            if source == "modrinth":
                ver, loaders = modrinth_latest(target)
                if ver is None:
                    rec["status"] = "NO_1_21_1_VERSION"
                    rec["slug"] = target
                    results.append(rec)
                    print(f"[{idx:03d}/{len(names)}] NO 1.21.1: {name} -> {target}", flush=True)
                    continue
                f0 = ver["files"][0]
                dest = os.path.join(outdir, f0["filename"])
                data = http_get(f0["url"], timeout=300)
                if (f0.get("hashes") or {}).get("sha1"):
                    h = hashlib.sha1(data).hexdigest()
                    if h != f0["hashes"]["sha1"]:
                        rec["status"] = "SHA1_MISMATCH"
                        results.append(rec)
                        print(f"[{idx:03d}/{len(names)}] SHA1 MISMATCH: {name}", flush=True)
                        continue
                with open(dest, "wb") as f:
                    f.write(data)
                rec.update({
                    "status": "OK", "source": "modrinth", "slug": target,
                    "modrinth_url": f"https://modrinth.com/project/{target}",
                    "title": ver.get("name") or target,
                    "version_number": ver.get("version_number", ""),
                    "version_type": ver.get("version_type", ""),
                    "loaders_used": loaders or ver.get("loaders", []),
                    "file_name": f0["filename"], "file_size": f0.get("size"),
                })
            else:  # curseforge
                info, err = cf_download({"slugs": target}, outdir)
                if info is None:
                    rec["status"] = "CF_FAILED"
                    rec["error"] = err
                    rec["cf_slugs"] = target
                    results.append(rec)
                    print(f"[{idx:03d}/{len(names)}] CF FAILED: {name} ({err})", flush=True)
                    continue
                rec.update({
                    "status": "OK", "source": "curseforge", "slug": info.get("project_id"),
                    "cf_slugs": target, "cf_page": info.get("page_url"),
                    "title": info.get("display") or name, "version_number": "",
                    "version_type": "release", "loaders_used": ["neoforge"],
                    "file_name": info["file_name"], "file_id": info["file_id"],
                    "cf_note": info.get("note", ""),
                })
        except Exception as e:  # noqa: BLE001
            rec["status"] = "ERROR"
            rec["error"] = str(e)
            results.append(rec)
            print(f"[{idx:03d}/{len(names)}] ERROR: {name} ({e})", flush=True)
            continue

        # verify jar
        dest2 = os.path.join(outdir, rec.get("file_name", ""))
        if rec["status"] == "OK":
            if not os.path.exists(dest2) or not zipfile.is_zipfile(dest2):
                rec["status"] = "NOT_A_JAR"
                print(f"[{idx:03d}/{len(names)}] NOT_A_JAR: {name}", flush=True)
                continue
            mid, mf = detect_modid(dest2)
            rec["detected_modid"], rec["detected_meta"] = mid, mf
            # loader jars (kotlinforforge etc.) may lack mod metadata - accept by filename
            no_meta_ok = any(k in name.lower() for k in ("kotlinforforge", "connector", "essential"))
            if mid is None and not no_meta_ok:
                rec["status"] = "NO_MOD_METADATA"
                print(f"[{idx:03d}/{len(names)}] NO_MOD_METADATA: {name}", flush=True)
                continue
            if stem in EXPECTED_MODID and mid != EXPECTED_MODID[stem]:
                rec["modid_warning"] = f"expected {EXPECTED_MODID[stem]}, got {mid}"
        results.append(rec)
        print(f"[{idx:03d}/{len(names)}] OK: {name} -> {rec.get('file_name')} ({rec.get('detected_modid')}) [{rec.get('source')}]", flush=True)
        time.sleep(0.2)

    # outputs
    ok_count = len([r for r in results if r["status"] == "OK"])
    manifest_path = os.path.join(outdir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                   "game_version": "1.21.1", "loader": "neoforge",
                   "total": len(names), "ok": ok_count,
                   "results": results}, f, indent=2, ensure_ascii=False)

    lines = ["KITSUGI - FIX LISTESI SONUCLARI",
             f"Tarih: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
             f"Toplam: {len(names)} | OK: {ok_count} | Sorunlu: {len(results) - ok_count}", ""]
    for r in results:
        if r["status"] == "OK":
            extra = f" [modid uyari: {r.get('modid_warning')}]" if r.get("modid_warning") else ""
            lines.append(f"[OK] {r['requested']} -> {r['file_name']} ({r.get('detected_modid')}) src={r.get('source')}{extra}")
        else:
            lines.append(f"[{r['status']}] {r['requested']} {r.get('error', '')} {r.get('slug', '')} {r.get('cf_slugs', '')}")
    with open(os.path.join(outdir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n=========== FIX RESULTS ===========")
    print(f"Total: {len(names)}  OK: {ok_count}  Failed: {len(results) - ok_count}")
    for r in results:
        if r["status"] != "OK":
            print(f"  FAIL: [{r['status']}] {r['requested']} {r.get('error', '')}")
        elif r.get("modid_warning"):
            print(f"  WARN: {r['requested']} {r['modid_warning']}")


if __name__ == "__main__":
    main()
