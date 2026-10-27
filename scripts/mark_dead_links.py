#!/usr/bin/env python3
"""Flag entries whose URL is confirmed-dead with url_status='broken' (keeps the url for the record,
so the map can show 'website offline' instead of linking to a 404). Confirmed set comes from the
two-pass link check (research/dead-confirmed.json)."""
import json, os
ROOT = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(ROOT, "communities-database.json")
dead = set(json.load(open(os.path.join(ROOT,"research","dead-confirmed.json")))["confirmed"].keys())
db = json.load(open(DB)); rows = db["entries"]
n = 0
for r in rows:
    u = (r.get("url") or "").strip()
    if u and u in dead:
        if r.get("url_status") != "broken":
            r["url_status"] = "broken"; n += 1
    elif r.get("url_status") == "broken":          # recovered since last run -> clear stale flag
        r.pop("url_status", None)
json.dump(db, open(DB,"w"), ensure_ascii=False, separators=(",",":"))
print(f"flagged {n} entries url_status=broken (of {len(dead)} confirmed-dead urls)")
