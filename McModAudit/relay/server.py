#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarayıcı-tabanlı mod tarama aracı için küçük sunucu.

Neden: Bu sandbox'tan Modrinth/CurseForge erişimi kapalı (egress allowlist),
ama kullanıcının tarayıcısı erişebiliyor. Sayfa, tarayıcıda tüm mod listesini
Modrinth API üzerinden tarar ve sonuçları buraya POST eder.

Çalıştırma: python3 McModAudit/relay/server.py  (0.0.0.0:8123)
"""
import ast
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(AUDIT_DIR)
OUT = os.path.join(AUDIT_DIR, "out")
os.makedirs(OUT, exist_ok=True)

CONFIG = os.path.join(HERE, "config.json")
RESULTS = os.path.join(OUT, "relay_results.json")
PORT = int(os.environ.get("PORT", "8123"))


def build_config():
    """audit_runner.py içindeki OVERRIDES/TARGETS sözlüklerini ast ile çek."""
    src = open(os.path.join(AUDIT_DIR, "audit_runner.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    overrides, targets = {}, []
    roots = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "OVERRIDES":
                overrides = ast.literal_eval(node.value)
            elif name == "ROOT_OVERRIDES":
                roots = ast.literal_eval(node.value)
            elif name == "TARGETS":
                targets = ast.literal_eval(node.value)
    overrides.update(roots)
    return overrides, targets


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return [l.strip() for l in fh if l.strip()]


def nkey(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def load_config():
    overrides, targets = build_config()
    server = read_lines(os.path.join(AUDIT_DIR, "server_mods.txt"))
    client = read_lines(os.path.join(AUDIT_DIR, "client_mods.txt"))
    mods67 = set(read_lines(os.path.join(AUDIT_DIR, "mods67.txt")))
    order, sides = [], {}
    for jar in server + client:
        if jar not in sides:
            sides[jar] = []
            order.append(jar)
        side = "S" if jar in server else "C"
        if side not in sides[jar]:
            sides[jar].append(side)
    return {
        "targets": targets,
        "overrides": {nkey(k): v for k, v in overrides.items()},
        "jars": [{"jar": j, "sides": "+".join(sides[j]), "in67": j in mods67} for j in order],
        "counts": {"server": len(server), "client": len(client), "unique": len(order)},
    }


def load_results():
    if not os.path.exists(RESULTS):
        return {}
    try:
        with open(RESULTS, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def save_results(store):
    with open(RESULTS, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # sessiz log
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif path == "/mods.json":
            self._send(200, json.dumps(load_config(), ensure_ascii=False))
        elif path == "/status":
            store = load_results()
            self._send(200, json.dumps({
                "collected": len(store),
                "jars": {k: {"slug": v.get("slug"), "title": v.get("title"),
                             "match": v.get("match"), "error": v.get("error")}
                         for k, v in list(store.items())[:2000]},
            }, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):  # noqa: N802
        if self.path.split("?")[0] == "/reset":
            save_results({})
            with open(os.path.join(OUT, "relay_log.txt"), "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%H:%M:%S')} RESET\n")
            self._send(200, json.dumps({"ok": True, "total": 0}))
            return
        if self.path.split("?")[0] != "/collect":
            self._send(404, json.dumps({"error": "not found"}))
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._send(400, json.dumps({"error": str(exc)}))
            return
        store = load_results()
        added = 0
        for rec in payload.get("results") or []:
            jar = rec.get("jar")
            if not jar:
                continue
            store[jar] = rec
            added += 1
        save_results(store)
        with open(os.path.join(OUT, "relay_log.txt"), "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} +{added} (toplam {len(store)})\n")
        self._send(200, json.dumps({"ok": True, "received": added, "total": len(store)}))


def main():
    cfg = load_config()
    print(f"Mod listesi: {cfg['counts']} — kayıtlı sonuç: {len(load_results())}", flush=True)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Sunucu hazır: http://0.0.0.0:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
