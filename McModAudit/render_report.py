#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relay_results.json -> Markdown + CSV rapor (Turkce)."""

import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "relay_results.json")
DST = os.path.join(HERE, "out", "RAPOR.md")
CSV = os.path.join(HERE, "out", "RAPOR.csv")

K263 = "26.3"
K262 = "26.2/26.1.x"
K1211 = "1.21.11 ve alti"
K1211ONCE = "1.21.1 ve oncesi"
KYOK = "yok"

GROUPS = [K263, K262, K1211, K1211ONCE, KYOK]


def load():
    with open(SRC, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "results" in data:
        return list(data["results"])
    if isinstance(data, dict):
        return [v for v in data.values() if isinstance(v, dict)]
    return data


def jar_versions(jar):
    b = re.sub(r"\.(jar|zip|bak)$", "", jar, flags=re.I)
    return [t for t in re.findall(r"\d+(?:\.\d+)+[a-z]?", b) if len(t) >= 3]


def up_to_date(rec):
    v = (rec.get("v1211") or {}).get("version") or ""
    if not v:
        return "?"
    toks = [t for t in jar_versions(rec.get("jar", "")) if t not in ("1.21.1", "1.21", "1.20.1")]
    if any(t in v for t in toks):
        return "guncel"
    if toks:
        return "yeni surum var"
    return "?"


def bucket(rec):
    nm = rec.get("newest_mc") or {}
    mc = nm.get("mc")
    if not mc:
        return KYOK
    if mc == "26.3":
        return K263
    if mc in ("26.2", "26.1.2", "26.1.1", "26.1"):
        return K262
    if mc in ("1.21.11", "1.21.10", "1.21.9"):
        return K1211
    return K1211ONCE


def row(rec):
    nm = rec.get("newest_mc") or {}
    v1 = rec.get("v1211") or {}
    name = rec.get("title") or rec.get("name") or "?"
    link = rec.get("url") or ""
    src = rec.get("source") or "-"
    if nm:
        newest = "{} . {} ({})".format(nm.get("mc"), nm.get("version"), nm.get("date", ""))
        ld = "/".join((nm.get("loaders") or [])[:3])
    else:
        newest, ld = "-", ""
    l1211 = "{} ({})".format(v1.get("version"), v1.get("date", "")) if v1 else "-"
    in67 = "E" if rec.get("in67") else ""
    return "| {} | {} | {} | {} | {} | {} | {} | {} | [link]({}) |".format(
        name, rec.get("sides", "?"), in67, src, newest, ld, l1211, up_to_date(rec), link)


HEADER = ("| Mod | S/C | 67 | Kaynak | En yuksek MC (build) | Loader | 1.21.1 en yeni | 1.21.1 durumu | Link |\n"
          "|---|---|---|---|---|---|---|---|---|")


def main():
    recs = load()
    recs.sort(key=lambda r: (r.get("name") or ""))
    groups = {k: [] for k in GROUPS}
    for r in recs:
        groups[bucket(r)].append(r)

    matched = [r for r in recs if r.get("slug")]
    in67 = [r for r in recs if r.get("in67")]
    outdated = [r for r in recs if up_to_date(r) == "yeni surum var"]

    out = []
    out.append("# Kitsugi - Modlarin en son Minecraft surumu uyumluluk raporu")
    out.append("")
    out.append("- **Olusturma:** {}".format(time.strftime("%d.%m.%Y %H:%M")))
    out.append("- **Veri kaynagi:** Modrinth API (+ CurseForge/cfwidget)")
    out.append("- **En son Minecraft:** `26.3` (15 Eylul 2026) - **NeoForge:** `26.3.0.6-beta`")
    out.append("- **Taranan:** {} benzersiz jar (sunucu 212 + istemci 234)".format(len(recs)))
    out.append("- **Eşleşen:** {}/{} - 67'lik listeden: {}".format(len(matched), len(recs), len(in67)))
    out.append("")
    out.append("## Ozet")
    out.append("")
    out.append("| En yuksek desteklenen MC | Mod sayisi |")
    out.append("|---|---|")
    for k in GROUPS:
        out.append("| {} | {} |".format(k, len(groups[k])))
    out.append("| 1.21.1 icin yeni build var (sende eski) | {} |".format(len(outdated)))
    out.append("")

    titles = {
        K263: "A) 26.3 destekleyenler (en guncel surum)",
        K262: "B) 26.2 / 26.1.x'e kadar olanlar (26.3 yok)",
        K1211: "C) 1.21.11 / 1.21.10 / 1.21.9'a kadar olanlar",
        K1211ONCE: "D) 26.x hic yok - 1.21.1 ve oncesinde kalanlar",
    }
    for k in (K263, K262, K1211, K1211ONCE):
        out.append("## {}".format(titles[k]))
        out.append("")
        out.append(HEADER if k != KYOK else "")
        out.extend(row(r) for r in groups[k])
        out.append("")

    out.append("## E) Eşleşmeyenler / veri yok")
    out.append("")
    out.append("| Jar | Not |")
    out.append("|---|---|")
    for r in groups[KYOK]:
        note = r.get("error") or r.get("note") or "Modrinth + CF eslesmesi bulunamadi"
        out.append("| {} | {} |".format(r.get("jar"), note))
    out.append("")

    out.append("## F) 67'lik esya/silah/yemek modu listesi")
    out.append("")
    out.append(HEADER)
    out.extend(row(r) for r in in67)
    out.append("")

    out.append("## G) 1.21.1'de guncel olmayan jar'lar")
    out.append("")
    out.append("| Mod | Sende (jar) | 1.21.1 en yeni | Link |")
    out.append("|---|---|---|---|")
    for r in outdated:
        v1 = (r.get("v1211") or {}).get("version", "")
        out.append("| {} | `{}` | {} | [link]({}) |".format(
            r.get("title") or r.get("name"), r.get("jar"), v1, r.get("url", "")))
    out.append("")
    out.append("---")
    out.append("")
    out.append("> Not: '1.21.1 durumu' kolonu, jar adindaki surum ile API'daki 1.21.1 build "
               "surumunun metinsel karsilastirmasina dayanir. Eslesen proje adi yanlissa "
               "(benzer isimli mod) satiri elle dogrula.")

    with open(DST, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))

    with open(CSV, "w", encoding="utf-8") as fh:
        fh.write("jar;mod;taraf;esya67;kaynak;slug;en_yuksek_mc;build;tarih;loader;1.21.1_en_yeni;1.21.1_durumu;link\n")
        for r in recs:
            nm = r.get("newest_mc") or {}
            v1 = r.get("v1211") or {}
            fh.write(";".join([
                r.get("jar", ""),
                (r.get("title") or r.get("name") or "").replace(";", ","),
                r.get("sides", ""),
                "1" if r.get("in67") else "",
                r.get("source", ""),
                r.get("slug", ""),
                nm.get("mc", ""),
                str(nm.get("version", "")),
                nm.get("date", ""),
                "/".join(nm.get("loaders") or []),
                str(v1.get("version", "")),
                up_to_date(r),
                r.get("url", ""),
            ]) + "\n")

    print("Rapor: {}".format(DST))
    print("CSV: {}".format(CSV))
    print("Toplam {} | 26.3: {} | 26.2/26.1.x: {} | 1.21.11: {} | 1.21.1: {} | yok: {} | guncel degil: {}".format(
        len(recs), len(groups[K263]), len(groups[K262]), len(groups[K1211]),
        len(groups[K1211ONCE]), len(groups[KYOK]), len(outdated)))


if __name__ == "__main__":
    main()
