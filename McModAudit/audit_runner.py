#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kitsugi-Plugins — Minecraft mod güncelleme denetimi (GitHub Actions üzerinden çalışır).

Sunucu (212) + istemci (236) listesindeki her jar için:
  * Modrinth / CurseForge (cfwidget) eşleşmesi
  * En yüksek desteklenen Minecraft release sürümü + o sürümdeki build
  * 1.21.1 için en yeni build (versiyon + tarih + loader)
  * Hedef MC sürümleri (26.3 ... 1.21.8) destek durumu
Çıktı: McModAudit/out/audit.json  (+ stdout log)
"""

import json
import os
import re
import sys
import time
import difflib
import subprocess

try:
    import requests
except ImportError:  # pragma: no cover
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, "out")
UA = {"User-Agent": "kitsugi-mod-audit/1.0 (+https://github.com/gameras1010-afk/Kitsugi-Plugins)"}
MR = "https://api.modrinth.com/v2"
CF = "https://api.cfwidget.com/minecraft/mc-mods/"

TARGETS = ["26.3", "26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9", "1.21.8", "1.21.1"]

OVERRIDES = {
    "t and t": "towns-and-towers",
    "mcw doors": "macaws-doors",
    "mcw lights": "macaws-lights-and-lamps",
    "mcw mcwwindows": "macaws-windows",
    "mcw paintings": "macaws-paintings",
    "mcw roofs": "macaws-roofs",
    "mcw trapdoors": "macaws-trapdoors",
    "skinlayers3d": "3dskinlayers",
    "skinlayers3d neoforge 1 11 2 mc1 21 1": "3dskinlayers",
    "l enders cataclysm": "lenders-cataclysm",
    "everycomp": "every-compat",
    "holdmyitems 1 21 1 neoforge 1 0 4": "cf:hold-my-items-refoxed",
    "hold my items refoxed": "cf:hold-my-items-refoxed",
    "eating animation 1 21 1 9 72": "eating-animation",
    "eating animation neoforge 6 0 1": "cf:eating-animation-forge",
    "firstperson forge 2 7 2 mc1 21 1": "first-person-model",
    "yungsmenutweaks 1 21 1 neoforge 2 1 2": "yungs-menu-tweaks",
    "villager news addon port 1 3 4": "cf:villager-news",
    "audio improvements v1 1 neoforge 1 21 1 21 3": "cf:audio-improvements",
    "iris shader folder 1 4 1 neoforge": "cf:iris-shader-folder",
    "epicterrain 0 1 4": "cf:epic-terrain",
    "betterworldloadingnf21 1 0": "cf:better-world-loading",
    "fancyenchantments 1 21 1 1 0": "cf:fancy-enchantments",
    "enchantments encore 1 8": "cf:enchantments-encore",
    "modpack update checker 1 21 1 neoforge 0 15 6": "cf:modpack-update-checker",
    "more mobs v1 5 11 mc1 14 26 3 9 mod": "cf:more-mobs",
    "more mobs v1 5 10 mc1 14 26 2 9 mod": "cf:more-mobs",
    "annuus neoforge 1 0 16 fix2": "annuus",
    "netherportalfix neoforge 1 21 1 21 1 1": "netherportalfix",
    "zetafix 1 0 0": "cf:zeta-fix",
    "playerlistheads 2 0 1 21 1 21 8 neoforge": "cf:playerlistheads",
    "gml 6 0 2": "cf:gml",
    "luna minecraft neoforge 5 3 1": "cf:luna",
    "doubledoors 1 21 1 7 2": "doubledoors",
    "tablist neoforge 1 21 1 1 5": "cf:tablist",
    "trek b0 6 2": "trek",
    "orb neoforge 1 21 1 0 3 0": "orb",
    "letmedespawn 1 21 x neoforge 1 5 0": "letmedespawn",
    "unloadedactivity v0 6 7 1 21 1 21 1": "unloaded-activity",
    "void totem 3": "voidtotem",
    "blossom blade 1 3": "cf:blossom-blade",
    "crashexploitfixer neoforge 2 0 0 1 21 4": "cf:crash-exploit-fixer",
    "chunksending 1 21 3 9": "cf:chunk-sending",
    "chunksending 1 21 3 7": "cf:chunk-sending",
    "structure layout optimizer neoforge 1 0 12": "cf:structure-layout-optimizer",
    "dungeons arise 1 21 1 2 1 68 release": "when-dungeons-arise",
    "adorabuild structures 2 11 0 neoforge 1 21 3": "adorabuild",
    "daisy neoforge 1 0 2 test": "cf:daisy",
    "discordintegration 1 21 1 4 0 1": "cf:discord-integration",
    "easydisenchanting neoforge 1 0 0 1 21 1": "easy-disenchanting",
    "formationsnether 1 0 5b mc1 21": "cf:formations-nether",
    "formationsoverworld 1 0 5c mc1 21": "cf:formations-overworld",
    "formations 1 0 4 neoforge mc1 21": "cf:formations",
    "better compatability checker neoforge 21 1 8": "better-compatibility-checker",
    "displaythat 1 21 1 1 0 0": "display-that",
    "lootintegrations yungs 1 6": "loot-integrations-yungs",
    "lootintegrations yungs 1 5": "loot-integrations-yungs",
    "lootintegrations 1 21 1 4 7": "loot-integrations",
    "structureessentials 1 21 1 5 0": "structure-essentials",
    "villagesandpillages neoforge mc1 21 1 1 0 3": "villages-and-pillages",
    "guardvillagers 2 4 12 1 21 1": "guard-villagers",
    "guardvillagers 2 4 10 1 21 1": "guard-villagers",
    "gravestone neoforge 1 21 1 1 0 40": "gravestone-mod",
    "goblintraders neoforge 1 21 1 1 11 2": "goblin-traders",
    "moreandmorearmorneoforge1211update": "cf:more-armor",
    "more armor 1 0 5 neoforge 1 21 1": "cf:more-armor",
    "domum ornamentum 1 0 231 main": "domum-ornamentum",
    "domum ornamentum 1 0 234 snapshot main": "domum-ornamentum",
    "ironchest 1 21 neoforge 16 0 7": "iron-chests",
    "ironfurnaces neoforge 1 21 1 4 3 2": "iron-furnaces",
    "smarterfarmers 1 21 2 2 4 neoforge": "cf:smarter-farmers",
    "supermartijn642configlib 1 1 8 neoforge mc1 21": "supermartijn642s-config-lib",
    "melody neoforge 1 0 10 mc 1 21": "cf:melody",
    "konkrete neoforge 1 9 9 mc 1 21": "cf:konkrete",
    "fancymenu neoforge 3 9 12 mc 1 21 1": "cf:fancymenu",
    "drippyloadingscreen neoforge 3 1 5 mc 1 21 1": "cf:drippy-loading-screen",
    "mcef neoforge 2 2 0 1 21 1": "cf:mcef",
    "longerchathistory neoforge 1 7": "cf:longer-chat-history",
    "fpsreducer2 neoforge 1 21 2 10": "cf:fps-reducer",
    "c2me neoforge mc1 21 1 0 4 0 alpha 0 116": "cf:c2me",
    "connector 2 0 0 beta 16 1 21 1 full": "cf:connector",
    "connector extras 1 12 1 1 21 1": "cf:connector-extras",
    "forgified fabric api 0 116 15 2 3 5 1 21 1": "cf:forgified-fabric-api",
    "forgified fabric api 0 116 15 2 3 1 1 21 1": "cf:forgified-fabric-api",
    "inventoryhud neoforged 1 21 1 3 4 28": "cf:inventory-hud",
    "inventoryessentials neoforge 1 21 1 21 1 18": "inventoryessentials",
    "inventoryessentials neoforge 1 21 1 21 1 17": "inventoryessentials",
    "logbegone neoforge 1 21 1 1 0 3": "cf:log-begone",
    "highlighter 1 21 neoforge 1 1 11": "cf:highlighter",
    "ambientsounds neoforge v6 3 8 mc1 21 1": "cf:ambientsounds",
    "distanthorizons 3 3 1 1 21 1 fabric neoforge": "distanthorizons",
    "distanthorizons 3 2 0 b 1 21 1 fabric neoforge": "distanthorizons",
    "fwa 1 21 1 neoforge 1 2 31": "fancy-world-animations",
    "eating animation 1 21 1 9 72": "eating-animation",
    "entity model features 3 3 5 1 21 neoforge": "entity-model-features",
    "entity texture features 7 2 1 1 21 neoforge": "entitytexturefeatures",
    "punchy 2 8a forge 1 21 1": "punchy",
    "notenoughanimations neoforge 1 12 4 mc1 21 1": "not-enough-animations",
    "waterframes neoforge mc1 21 1 v2 1 23": "waterframes",
    "watermedia youtube plugin 2 1 2": "cf:watermedia-youtube-plugin",
    "watermedia 2 1 37": "cf:watermedia",
    "webdisplays 2 6 0 1 21 1": "cf:webdisplays",
    "fape compat 0 5": "cf:fresh-animations-player-extension",
    "emf compat not enough animations 1 21 1 1 2 0": "cf:emf-compat-not-enough-animations",
    "essential 1 4 1 1 neoforge 1 21 1": "cf:essential",
    "zfastnoise 1 0 13 1 21 1 neoforge": "cf:zeta-fastnoise",
    "scalablelux neoforge 0 3 0 alpha 0 6 all": "cf:scalablelux",
    "annuus": "annuus",
    "acedium 0 4 1 mc1 21 1": "acedium",
    "aquaculture 1 21 1 2 7 21": "aquaculture",
    "betterend 21 0 35": "betterend",
    "betterend 21 0 34": "betterend",
    "bethernet 21 0 26": "bethernet",
    "bclib 21 0 26": "bclib",
    "wunderlib 21 0 10": "wunderlib",
    "worldweaver 21 0 25": "worldweaver",
    "patchouli 1 21 1 93 neoforge": "patchouli",
    "quark 4 1 485": "quark",
    "quark 4 1 482": "quark",
    "framedblocks 10 6 1": "framedblocks",
    "aquamirae neoforge 1 21 1 7 2 7": "aquamirae",
    "aquaculturedelight 1 2 0 neoforge 1 21 1": "aquaculture-delight",
    "farmersdelight 1 21 1 1 3 4": "farmers-delight",
    "farmersdelight 1 21 1 1 3 2": "farmers-delight",
    "cyclic 1 21 1 1 14 2": "cyclic",
    "cyclic 1 21 1 1 14 1": "cyclic",
    "advancednetherite neoforge 2 3 1 1 21 1": "advanced-netherite",
    "morevanillashields 1 0 2 1 21 1": "more-vanilla-shields",
    "handcrafted neoforge 1 21 1 4 0 3": "handcrafted",
    "another furniture neoforge 4 0 2": "another-furniture",
    "chipped neoforge 1 21 1 4 0 2": "chipped",
    "betterarcheology neoforge 1 21 1 1 3 8": "better-archeology",
    "dungeons and taverns v4 4 4": "dungeons-and-taverns",
    "twilightforest 1 21 1 4 8 3345 universal": "twilight-forest",
    "mowziesmobs 1 21 1 1 8 2": "mowzies-mobs",
    "naturalist 2 0 3 neoforge 1 21 1": "naturalist",
    "naturalist 2 0 2 neoforge 1 21 1": "naturalist",
    "born in chaos neoforge 1 21 1 1 7 6": "born-in-chaos",
    "environmental 1 21 1 5 0 1": "environmental",
    "deeperdarker neoforge 1 21 1 1 4 1": "deeper-and-darker",
    "citadel 2 7 1 1 21 1": "citadel",
    "aether 1 21 1 1 5 10 neoforge": "aether",
    "alexsmobs 2 2 1 neoforge 1 21 1": "alexs-mobs",
    "alexsmobs 2 0 8 neoforge 1 21 1": "alexs-mobs",
    "supplementaries 1 21 1 3 9 9 neoforge": "supplementaries",
    "supplementaries 1 21 1 3 8 9 neoforge": "supplementaries",
    "amendments 1 21 2 1 10 neoforge": "amendments",
    "amendments neoforge 1 21 2 1 7": "amendments",
    "moonlight 1 21 1 3 6 5 neoforge": "moonlight",
    "moonlight 1 21 1 3 3 3 neoforge": "moonlight",
    "blueprint 1 21 1 8 2 0": "blueprint",
    "comforts neoforge 9 0 5 1 21 1": "comforts",
    "sereneseasons neoforge 1 21 1 10 1 0 3": "serene-seasons",
    "raided 1 21 1 0 1 6": "raided",
    "moogsendstructures universal 1 21 2 1 1": "moogs-end-structures",
    "moogsglowup neoforge 1 21 1 1 2 2": "moogs-glow-up",
    "moogsstructurelib neoforge 1 21 1 3 3 1": "moogs-structure-lib",
    "moogsvoyagerstructures universal 1 21 5 1 2": "moogs-voyager-structures",
    "appleskin neoforge mc1 21 3 0 9": "appleskin",
    "explorify v1 6 5 mod": "explorify",
    "terralith 1 21 1 v2 6 2 neoforge": "terralith",
    "biomesoplenty neoforge 1 21 1 21 1 0 14": "biomes-o-plenty",
    "oh the biomes weve gone neoforge 2 6 0": "oh-the-biomes-weve-gone",
    "oh the trees youll grow neoforge 1 21 1 5 3 2": "oh-the-trees-youll-grow",
    "naturescompass 1 21 1 3 4 0 neoforge": "natures-compass",
    "explorerscompass 1 21 1 3 4 0 neoforge": "explorers-compass",
    "lithium neoforge 0 15 4 mc1 21 1": "lithium",
    "ferritecore 7 0 3 neoforge": "ferritecore",
    "spark 1 10 124 neoforge": "spark",
    "chunky neoforge 1 4 23": "chunky",
    "clumps neoforge 1 21 1 19 0 0 1": "clumps",
    "modernfix neoforge 5 27 24 mc1 21 1": "modernfix",
    "modernfix neoforge 5 27 20 mc1 21 1": "modernfix",
    "lootr neoforge 1 21 1 1 11 38 125": "lootr",
    "lootr neoforge 1 21 1 1 11 38 123": "lootr",
    "jei 1 21 1 neoforge 19 54 0 427": "jei",
    "jei 1 21 1 neoforge 19 44 0 401": "jei",
    "curios neoforge 9 5 1 1 21 1": "curios",
    "geckolib neoforge 1 21 1 4 9 3": "geckolib",
    "geckolib neoforge 1 21 1 4 9 2": "geckolib",
    "architectury 13 0 11 neoforge": "architectury-api",
    "cloth config 15 0 140 neoforge": "cloth-config",
    "collective 1 21 1 8 39": "collective",
    "balm neoforge 1 21 1 21 0 65": "balm",
    "balm neoforge 1 21 1 21 0 64": "balm",
    "bookshelf neoforge 1 21 1 21 1 81": "bookshelf-lib",
    "iceberg 1 21 1 neoforge 1 3 2": "iceberg",
    "jade 1 21 1 neoforge 15 10 6": "jade",
    "journeymap neoforge 1 21 1 6 0 8": "journeymap",
    "journeymap neoforge 1 21 1 6 0 4": "journeymap",
    "kotlinforforge 5 12 0 all": "kotlin-for-forge",
    "midnightlib neoforge 1 9 3 1 21 1": "midnightlib",
    "owo lib neoforge 0 12 15 5 beta 1 1 21": "owo-lib",
    "polymorph neoforge 1 2 0 1 21 1": "polymorph",
    "polymorph neoforge 1 1 0 1 21 1": "polymorph",
    "resourcefulconfig neoforge 1 21 3 0 11": "resourceful-config",
    "resourcefullib neoforge 1 21 3 0 12": "resourceful-lib",
    "repurposed structures 7 5 22 1 21 1 neoforge": "repurposed-structures",
    "repurposed structures 7 5 21 1 21 1 neoforge": "repurposed-structures",
    "servercore neoforge 1 5 19 1 21 1": "servercore",
    "skinrestorer 2 11 0 1 21 neoforge": "skin-restorer",
    "skinrestorer 2 10 0 1 21 neoforge": "skin-restorer",
    "voicechat neoforge 1 21 1 2 6 22": "simple-voice-chat",
    "yungsapi 1 21 1 neoforge 5 1 9": "yungs-api",
    "yungsapi 1 21 1 neoforge 5 1 6": "yungs-api",
    "create": "create",
    "cerbon": "cf:cerbons-api",
    "trek": "trek",
    "flib 1 21 1 0 2 9": "flib",
    "yet another config lib v3 3 8 2 1 21 1 neoforge": "yacl",
    "coroutil neoforge 1 21 0 1 3 8": "coroutil",
    "cit": "cf:cit-resewn",
}



# --- Kök ad (root) override'ları: 1. turda aramada bulunamayan modlar ---
ROOT_OVERRIDES = {
    "yungsapi": "yungs-api",
    "yungsbetterdeserttemples": "yungs-better-desert-temples",
    "yungsbetterdungeons": "yungs-better-dungeons",
    "yungsbetterendisland": "yungs-better-end-island",
    "yungsbetterjungletemples": "yungs-better-jungle-temples",
    "yungsbettermineshafts": "yungs-better-mineshafts",
    "yungsbetternetherfortresses": "yungs-better-nether-fortresses",
    "yungsbetteroceanmonuments": "yungs-better-ocean-monuments",
    "yungsbetterstrongholds": "yungs-better-strongholds",
    "yungsbetterwitchhuts": "yungs-better-witch-huts",
    "yungsbridges": "yungs-bridges",
    "yungsextras": "yungs-extras",
    "yungsmenutweaks": "yungs-menu-tweaks",
    "twilightforest": "twilight-forest",
    "alexsmobs": "alexs-mobs",
    "mowziesmobs": "mowzies-mobs",
    "voicechat": "simple-voice-chat",
    "appleskin": "appleskin",
    "advancednetherite": "advanced-netherite",
    "aquaculturedelight": "aquaculture-delight",
    "betterarcheology": "better-archeology",
    "better compatability checker": "better-compatibility-checker",
    "notenoughanimations": "not-enough-animations",
    "mcef": "cf:mcef",
    "ironchest": "iron-chests",
    "ironfurnaces": "iron-furnaces",
    "everycomp": "every-compat",
    "morevanillashields": "more-vanilla-shields",
    "domum ornamentum": "domum-ornamentum",
    "easyanvils": "easy-anvils",
    "easymagic": "easy-magic",
    "enchantinginfuser": "enchanting-infuser",
    "barteringstation": "bartering-station",
    "tradingpost": "trading-post",
    "visualworkbench": "visual-workbench",
    "skeleton a i fix": "skeleton-ai-fix",
    "skeletonaifix": "skeleton-ai-fix",
    "puzzleslib": "puzzles-lib",
    "sereneseasons": "serene-seasons",
    "explorerscompass": "explorers-compass",
    "naturescompass": "natures-compass",
    "biomesoplenty": "biomes-o-plenty",
    "farmer s delight": "farmers-delight",
    "farmersdelight": "farmers-delight",
    "farmersstructures": "farmers-structures",
    "justenoughresources": "just-enough-resources-jer",
    "justenoughprofessions": "just-enough-professions",
    "extra golems reborn": "extra-golems",
    "extra golems": "extra-golems",
    "advancementplaques": "advancement-plaques",
    "connector extras": "connector-extras",
    "decorativeblocks reborn": "decorative-blocks-reborn",
    "discordintegration": "discord-integration",
    "dungeons arise": "when-dungeons-arise",
    "moogsendstructures": "moogs-end-structures",
    "moogsglowup": "moogs-glow-up",
    "moogsstructurelib": "moogs-structure-lib",
    "moogsvoyagerstructures": "moogs-voyager-structures",
    "villager news addon port": "cf:villager-news",
    "alternate current": "alternate-current",
    "charmofundying": "charm-of-undying",
    "cristellib": "cristellib",
    "cupboard": "cupboard",
    "displaythat": "display-that",
    "doubledoors": "doubledoors",
    "easydisenchanting": "easy-disenchanting",
    "elevatorid": "elevatorid",
    "inventoryessentials": "inventory-essentials",
    "kotlinforforge": "kotlin-for-forge",
    "letmedespawn": "letmedespawn",
    "libraryferret": "library-ferret",
    "lootintegrations": "loot-integrations",
    "lootintegrations yungs": "loot-integrations-yungs",
    "resourcefulconfig": "resourceful-config",
    "resourcefullib": "resourceful-lib",
    "smarterfarmers": "smarter-farmers",
    "structureessentials": "structure-essentials",
    "supermartijn642configlib": "supermartijn642s-config-lib",
    "unloadedactivity": "unloaded-activity",
    "villagesandpillages": "villages-and-pillages",
    "waterframes": "waterframes",
    "carryon": "carry-on",
    "apothicattributes": "apothic-attributes",
    "apothicenchanting": "apothic-enchanting",
    "apothicspawners": "apothic-spawners",
    "betteradvancements": "better-advancements",
    "bettermosbutton": "better-mods-button",
    "better mods button": "better-mods-button",
    "configureddefaults": "configured-defaults",
    "deleteworldstotrash": "delete-worlds-to-trash",
    "fpsreducer2": "fps-reducer",
    "inventoryinteractions": "inventory-interactions",
    "inventoryprofilesnext": "inventory-profiles-next",
    "leavesbegone": "leaves-be-gone",
    "longerchathistory": "cf:longer-chat-history",
    "mindfuldarkness": "mindful-darkness",
    "mousetweaks": "mouse-tweaks",
    "overflowingbars": "overflowing-bars",
    "particleeffects": "particle-effects",
    "resourcepackoverrides": "resource-pack-overrides",
    "simplediscordrichpresence": "simple-discord-rich-presence",
    "stylisheffects": "stylish-effects",
    "betterworldloadingnf21": "cf:better-world-loading",
    "drippyloadingscreen": "cf:drippy-loading-screen",
    "enchdesc": "enchantment-descriptions",
    "fancyenchantments": "cf:fancy-enchantments",
    "fape compat": "cf:fresh-animations-player-extension",
    "holdmyitems": "cf:hold-my-items-refoxed",
    "inventoryhud neoforged": "cf:inventory-hud",
    "logbegone": "cf:log-begone",
    "tia": "tia",
    "watermedia youtube plugin": "cf:watermedia-youtube-plugin",
    "watermedia": "cf:watermedia",
    "formati": "cf:formations",
    "formations": "cf:formations",
    "formationsnether": "cf:formations-nether",
    "formationsoverworld": "cf:formations-overworld",
    "framework": "framework",
    "ftb library": "ftb-library",
    "ftb library neoforge": "ftb-library",
    "lionfishapi": "lionfish-api",
    "luna minecraft": "cf:luna",
    "moreandmorearmorneoforge1211update": "cf:more-armor",
    "more armor": "cf:more-armor",
    "orb": "orb",
    "trek": "trek",
    "zetafix": "cf:zeta-fix",
    "fastrecipesearch": "fast-recipe-search",
    "chunksending": "cf:chunk-sending",
    "c2me": "cf:c2me",
    "awesomedungeonocean": "awesome-dungeon-ocean",
    "treeharvester": "tree-harvester",
    "playeranimationlib": "playeranimator",
    "playeranimationlibneoforge": "playeranimator",
    "jagmkiwis": "jagmkiwis",
    "acedium": "acedium",
    "apotheosis": "apotheosis",
    "aquaculture": "aquaculture",
    "quark": "quark",
    "patchouli": "patchouli",
    "supplementaries": "supplementaries",
    "amendments": "amendments",
    "moonlight": "moonlight",
    "blueprint": "blueprint",
    "bclib": "bclib",
    "betterend": "betterend",
    "bethernet": "bethernet",
    "wunderlib": "wunderlib",
    "worldweaver": "worldweaver",
    "citadel": "citadel",
    "aether": "aether",
    "naturalist": "naturalist",
    "born in chaos": "born-in-chaos",
    "aquamirae": "aquamirae",
    "environmental": "environmental",
    "deeperdarker": "deeper-and-darker",
    "chipped": "chipped",
    "handcrafted": "handcrafted",
    "another furniture": "another-furniture",
    "framedblocks": "framedblocks",
    "dungeons and taverns": "dungeons-and-taverns",
    "comforts": "comforts",
    "gravestone": "gravestone-mod",
    "goblintraders": "goblin-traders",
    "guardvillagers": "guard-villagers",
    "netherportalfix": "netherportalfix",
    "skinrestorer": "skin-restorer",
    "geckolib": "geckolib",
    "architectury": "architectury-api",
    "cloth config": "cloth-config",
    "collective": "collective",
    "balm": "balm",
    "bookshelf": "bookshelf-lib",
    "iceberg": "iceberg",
    "jade": "jade",
    "journeymap": "journeymap",
    "midnightlib": "midnightlib",
    "owo lib": "owo-lib",
    "polymorph": "polymorph",
    "repurposed structures": "repurposed-structures",
    "servercore": "servercore",
    "spark": "spark",
    "chunky": "chunky",
    "clumps": "clumps",
    "modernfix": "modernfix",
    "lootr": "lootr",
    "jei": "jei",
    "curios": "curios",
    "terralith": "terralith",
    "explorify": "explorify",
    "lithium": "lithium",
    "ferritecore": "ferritecore",
    "yacl": "yacl",
    "yet another config lib v3": "yacl",
    "coroutil": "coroutil",
    "terrabender": "terrablender",
    "glitchcore": "glitchcore",
    "corgilib": "corgilib",
    "athena": "athena",
    "placebo": "placebo",
    "prickle": "prickle",
    "sodium": "sodium",
    "iris": "iris",
    "bobby": "bobby",
    "entityculling": "entityculling",
    "moreculling": "moreculling",
    "immediatelyfast": "immediatelyfast",
    "badoptimizations": "badoptimizations",
    "threadtweak": "threadtweak",
    "sound physics remastered": "sound-physics-remastered",
    "distanthorizons": "distanthorizons",
    "fwa": "fancy-world-animations",
    "entity model features": "entity-model-features",
    "entity texture features": "entitytexturefeatures",
    "eating animation": "cf:eating-animation-forge",
    "firstperson forge": "first-person-model",
    "skinlayers3d": "3dskinlayers",
    "inventory profiles next": "inventory-profiles-next",
    "colorwheel": "colorwheel",
    "libipn": "libipn",
    "chat heads": "chat-heads",
    "melody": "cf:melody",
    "konkrete": "cf:konkrete",
    "fancymenu": "cf:fancymenu",
    "continuity": "continuity",
    "lambdynamiclights": "lambdynamiclights",
    "reeses sodium options": "reeses-sodium-options",
    "sodium extra": "sodium-extra",
    "entity culling": "entityculling",
    "essential 1 4 1 1 neoforge 1 21 1": "cf:essential",
    "scalablelux": "cf:scalablelux",
    "zfastnoise": "cf:zeta-fastnoise",
    "modpack update checker": "cf:modpack-update-checker",
    "more mobs": "cf:more-mobs",
    "gml": "cf:gml",
    "tablist": "cf:tablist",
    "annuus": "annuus",
    "daisy": "cf:daisy",
    "connectorextras": "connector-extras",
    "stylisheffects v21": "stylish-effects",
    "distraction free recipes": "distraction-free-recipes",
    "highlighter": "cf:highlighter",
    "void totem": "voidtotem",
    "xercamod": "cf:xercamod",
}
OVERRIDES.update(ROOT_OVERRIDES)

OV = {nkey(k): v for k, v in OVERRIDES.items()}


def http_get(url, timeout=45):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 429:
                time.sleep(4 + attempt * 3)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                return {"__error__": str(exc)}
            time.sleep(1.5 * (attempt + 1))
    return None


def nkey(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def jar_root(jar):
    b = re.sub(r"\.(jar|zip|bak|disabled)$", "", jar, flags=re.I)
    b = re.sub(r"[\[\]\(\)]", " ", b)
    b = b.replace("_", " ").replace("-", " ").replace("+", " ").replace(".", " ")
    toks = b.split()
    keep = []
    for t in toks:
        if re.match(r"^v?\d", t) and keep:
            break
        keep.append(t)
    words = " ".join(keep).strip().split()
    tails = {"neoforge", "forge", "fabric", "quilt", "universal", "mod", "all", "update", "test"}
    while words and words[-1].lower() in tails:
        words.pop()
    return " ".join(words) or b


MC_IN_NAME = re.compile(r"(?:mc)?(1\.21\.\d+|26\.\d+(?:\.\d+)?|1\.20\.\d+)")


def mcs_from_name(name):
    return MC_IN_NAME.findall(name or "")


def cf_lookup(slug):
    data = http_get(CF + slug)
    if not isinstance(data, dict) or "__error__" in data or not data.get("files"):
        return None
    rows = []
    for f in data["files"]:
        fname = str(f.get("name") or "")
        mcs = f.get("versions") or mcs_from_name(fname)
        rows.append({
            "version": fname or str(f.get("version") or ""),
            "date": (f.get("uploaded_at") or "")[:10],
            "mcs": mcs,
            "loaders": f.get("loaders") or [],
            "type": f.get("type"),
        })
    return {
        "slug": data.get("slug") or slug,
        "title": data.get("title") or slug,
        "url": f"https://www.curseforge.com/minecraft/mc-mods/{data.get('slug') or slug}",
        "score": 1.0,
        "source": "curseforge",
        "files": rows,
        "downloads": data.get("downloads"),
        "loaders": [],
        "updated": "",
    }


def mr_match(jar, name):
    for cand in (nkey(name), nkey(jar)):
        hit = OV.get(cand)
        if hit:
            if hit.startswith("cf:"):
                got = cf_lookup(hit[3:])
                if got:
                    return got
            else:
                proj = http_get(f"{MR}/project/{hit}")
                if isinstance(proj, dict) and "slug" in proj:
                    out = dict(proj)
                    out["score"] = 1.0
                    out["source"] = "modrinth"
                    return out
    hits = http_get(
        f"{MR}/search?query={requests.utils.quote(name)}&limit=6"
        "&facets=%5B%5B%22project_type%3Amod%22%5D%5D"
    )
    if not isinstance(hits, dict) or "hits" not in hits:
        return None
    key = nkey(name)
    best, best_score = None, 0.0
    for h in hits["hits"]:
        tkey, skey = nkey(h.get("title")), nkey(h.get("slug"))
        s = max(difflib.SequenceMatcher(None, key, tkey).ratio(),
                difflib.SequenceMatcher(None, key, skey).ratio())
        if key and (key in tkey or tkey in key or key.replace(" ", "") in skey):
            s = max(s, 0.9)
        if s > best_score:
            best, best_score = h, s
    if not best or best_score < 0.55:
        return None
    proj = http_get(f"{MR}/project/{best['slug']}")
    if not isinstance(proj, dict) or "slug" not in proj:
        return None
    out = dict(proj)
    out["score"] = round(best_score, 3)
    out["source"] = "modrinth"
    return out


def mr_versions(slug, mc=None, limit=100):
    url = f"{MR}/project/{slug}/version?limit={limit}"
    if mc:
        url += f"&game_versions=%5B%22{mc}%22%5D"
    data = http_get(url)
    if not isinstance(data, list):
        return []
    return [{
        "version": v.get("version_number"),
        "date": (v.get("date_published") or "")[:10],
        "mcs": v.get("game_versions") or [],
        "loaders": v.get("loaders") or [],
        "type": v.get("version_type"),
    } for v in data]


def pick_latest(files, mc=None):
    pool = [f for f in files if (mc in (f.get("mcs") or []))] if mc else list(files)
    if not pool:
        return None
    return sorted(pool, key=lambda f: f.get("date") or "", reverse=True)[0]


def audit_one(jar, sides, in67):
    name = jar_root(jar)
    rec = {"jar": jar, "name": name, "sides": sides, "in67": in67}
    proj = mr_match(jar, name)
    if not proj:
        rec["match"] = None
        return rec
    source = proj.get("source")
    rec["source"] = source
    rec["slug"] = proj.get("slug")
    rec["title"] = proj.get("title")
    rec["url"] = (f"https://modrinth.com/mod/{proj.get('slug')}" if source == "modrinth"
                  else proj.get("url"))
    rec["match"] = proj.get("score")
    rec["downloads"] = proj.get("downloads")
    rec["loaders"] = proj.get("loaders") or []
    rec["updated"] = (proj.get("updated") or "")[:10]

    if source == "modrinth":
        gv = set(proj.get("game_versions") or [])
        rec["supports"] = {t: (t in gv) for t in TARGETS}
        latest = pick_latest(mr_versions(proj["slug"], limit=1))
        v1211 = pick_latest(mr_versions(proj["slug"], "1.21.1", limit=60))
    else:
        files = proj.get("files") or []
        gv = set()
        for f in files:
            gv |= set(f.get("mcs") or [])
        rec["supports"] = {t: (t in gv) for t in TARGETS}
        latest = pick_latest(files)
        v1211 = pick_latest(files, "1.21.1")

    rec["all_game_versions"] = sorted(gv)
    if latest:
        rec["latest"] = {"version": latest["version"], "date": latest["date"],
                         "mcs": latest["mcs"][:10], "loaders": latest["loaders"]}
    if v1211:
        rec["v1211"] = {"version": v1211["version"], "date": v1211["date"],
                        "mcs": v1211["mcs"], "loaders": v1211["loaders"]}
    for t in TARGETS:
        if rec["supports"].get(t):
            if source == "modrinth":
                f = pick_latest(mr_versions(proj["slug"], t, limit=30))
            else:
                f = pick_latest(proj.get("files") or [], t)
            if f:
                rec["newest_mc"] = {"mc": t, "version": f["version"], "date": f["date"],
                                    "loaders": f["loaders"]}
                break
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    server = [l.strip() for l in open(os.path.join(ROOT, "server_mods.txt"), encoding="utf-8") if l.strip()]
    client = [l.strip() for l in open(os.path.join(ROOT, "client_mods.txt"), encoding="utf-8") if l.strip()]
    mods67 = {l.strip() for l in open(os.path.join(ROOT, "mods67.txt"), encoding="utf-8") if l.strip()}

    order, sides = [], {}
    for jar in server + client:
        if jar not in sides:
            sides[jar] = []
            order.append(jar)
        tag = "S" if jar in server else "C"
        if tag not in sides[jar]:
            sides[jar].append(tag)
    print(f"Toplam benzersiz jar: {len(order)} (sunucu {len(server)}, istemci {len(client)})", flush=True)

    results = []
    for i, jar in enumerate(order, 1):
        try:
            rec = audit_one(jar, "+".join(sides[jar]), jar in mods67)
        except Exception as exc:  # noqa: BLE001
            rec = {"jar": jar, "name": jar_root(jar), "sides": "+".join(sides[jar]),
                   "in67": jar in mods67, "error": str(exc), "match": None}
        results.append(rec)
        newest = rec.get("newest_mc") or {}
        v1211 = rec.get("v1211") or {}
        print(
            f"[{i}/{len(order)}] {jar} -> {rec.get('slug','?')} ({rec.get('source','-')},"
            f"{rec.get('match')}) | maxMC={newest.get('mc','-')}:{newest.get('version','-')}"
            f" | 1.21.1={v1211.get('version','-')} ({v1211.get('date','-')})",
            flush=True,
        )
        time.sleep(0.2)

    matched = [r for r in results if r.get("slug")]
    unmatched = [r["jar"] for r in results if not r.get("slug")]
    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "latest_minecraft": "26.3",
        "targets": TARGETS,
        "total": len(results),
        "matched": len(matched),
        "unmatched": unmatched,
        "results": results,
    }
    with open(os.path.join(OUT, "audit.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"\nEşleşen: {len(matched)}/{len(results)}", flush=True)
    print("Eşleşmeyenler: " + (", ".join(unmatched) if unmatched else "-"), flush=True)

    try:
        subprocess.run(["git", "add", "-A", "McModAudit"], cwd=REPO, check=False)
        subprocess.run(
            ["git", "-c", "user.email=actions@github.com", "-c", "user.name=mod-audit",
             "commit", "-m", "audit: mod güncelleme taraması sonuçları"],
            cwd=REPO, check=False,
        )
        subprocess.run(["git", "push", "origin", "HEAD:arena/01a0b5c1-kitsugi-plugins"], cwd=REPO, check=False)
        print("Push denemesi tamam.", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Push hatası: {exc}", flush=True)


if __name__ == "__main__":
    main()
