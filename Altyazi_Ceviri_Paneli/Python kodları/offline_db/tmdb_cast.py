"""
offline_db/tmdb_cast.py
=======================
TMDB oyuncu kadrosu çekme.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

def _fetch_potterdb(verbose: bool = False) -> dict:
    """PotterDB API — Harry Potter karakterler, buyuler, iksirler."""
    BASE = "https://api.potterdb.com/v1"
    HDR  = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}
    result = {"characters": [], "skills": [], "items": []}

    # Karakterler
    try:
        chars = []
        page = 1
        while page <= 5:  # max 5 sayfa
            r = requests.get(f"{BASE}/characters?page[number]={page}&page[size]=100",
                             timeout=15, headers=HDR)
            if r.status_code != 200:
                break
            data = r.json().get("data", [])
            if not data:
                break
            for item in data:
                    name = item.get("attributes", {}).get("name", "").strip()
                    attrs = item.get("attributes", {})
                    # Filtrele: rakamla baslayanlar, cok uzunlar, aciklamali olanlar
                    if not name or len(name) > 50:
                        continue
                    if name[0].isdigit():
                        continue
                    skip_kw = ('spectator','match','tournament','ceremony',
                               'student','class','member','crowd','mourner',
                               'attendee','unnamed','unknown','various')
                    if any(kw in name.lower() for kw in skip_kw):
                        continue
                    chars.append(name)
            if len(data) < 100:
                break
            page += 1
            time.sleep(0.5)
        # Bilinen onemliler one: en az 2 kelimeli gercek isimler once
        full_names  = [c for c in chars if ' ' in c and len(c) <= 30]
        short_names = [c for c in chars if ' ' not in c and len(c) <= 20]
        result["characters"] = (full_names + short_names)[:200]
        if verbose:
            print(f"[PotterDB] Karakterler: {len(chars)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Karakter hatasi: {e}")

    # Buyuler (skills olarak)
    try:
        spells = []
        r = requests.get(f"{BASE}/spells?page[size]=200", timeout=15, headers=HDR)
        if r.status_code == 200:
            for item in r.json().get("data", []):
                name = item.get("attributes", {}).get("name", "").strip()
                if name:
                    spells.append(name)
        result["skills"] = spells
        if verbose:
            print(f"[PotterDB] Buyuler: {len(spells)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Buyu hatasi: {e}")

    # Iksirler (items olarak)
    try:
        potions = []
        r = requests.get(f"{BASE}/potions?page[size]=200", timeout=15, headers=HDR)
        if r.status_code == 200:
            for item in r.json().get("data", []):
                name = item.get("attributes", {}).get("name", "").strip()
                if name:
                    potions.append(name)
        result["items"] = potions
        if verbose:
            print(f"[PotterDB] Iksirler: {len(potions)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Iksir hatasi: {e}")

    return result


def _fetch_swapi(verbose: bool = False) -> dict:
    """SWAPI — Star Wars karakterler, gezegenler, gemiler, turler."""
    MIRRORS = [
        "https://swapi.info/api",
        "https://swapi.tech/api",
        "https://swapi.dev/api",
    ]
    BASE = None
    for mirror in MIRRORS:
        try:
            r = requests.get(f"{mirror}/people/", timeout=8,
                             headers={"User-Agent": "AnimeSubtitleTranslator/3.0"})
            if r.status_code == 200:
                BASE = mirror
                break
        except Exception:
            continue

    if not BASE:
        if verbose:
            print("[SWAPI] Hicbir mirror erisilebilir degil.")
        return {}

    if verbose:
        print(f"[SWAPI] Mirror: {BASE}")

    HDR  = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}
    result = {"characters": [], "locations": [], "items": [], "terminology": []}

    ENDPOINTS = [
        ("people",    "characters"),
        ("planets",   "locations"),
        ("starships", "items"),
        ("species",   "terminology"),
    ]
    for endpoint, key in ENDPOINTS:
        collected = []
        url = f"{BASE}/{endpoint}/"
        while url and len(collected) < 500:
            try:
                r = requests.get(url, timeout=15, headers=HDR)
                if r.status_code != 200:
                    break
                data = r.json()
                # swapi.info direkt array; swapi.dev/swapi.tech {results:[...]} doner
                if isinstance(data, list):
                    items_list = data
                    url = None
                else:
                    items_list = data.get("results", [])
                    url = data.get("next")
                for item in items_list:
                    name = (item.get("name") or "").strip()
                    if name and name.lower() not in ("unknown", "n/a", ""):
                        collected.append(name)
                time.sleep(0.3)
            except Exception as e:
                if verbose:
                    print(f"[SWAPI] {endpoint} hata: {e}")
                break
        result[key] = collected
        if verbose:
            print(f"[SWAPI] {endpoint}: {len(collected)}")

    return result


# ─────────────────────────────────────────────────────────────────────────────

# BÖLÜM 5: GÜNCELLEME YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────────────────────

