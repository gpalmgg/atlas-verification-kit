#!/usr/bin/env python3
"""Generate Murmurations organization profiles from the PUBLIC map slice.

DRAFT — prepared 2026-07-09 as a handoff to the atlas workstream.
Reads map/data/map.json (the consent-tiered public slice: gold-set only,
coords already rounded to ~1km, contact data already stripped) so nothing
leaves this script that isn't already public on communities-map.vercel.app.

Murmurations (murmurations.network): each org publishes a small JSON profile
at its own URL; a federated index lets any platform (incl. GEN's rebuild)
discover and pull all of them. Protocol schema: organizations_schema-v1.0.0.

Usage:
  python3 scripts/murmurations-profiles.py            # writes samples (10) to murmurations/samples/
  python3 scripts/murmurations-profiles.py --all      # writes all profiles to murmurations/profiles/

Before REGISTERING with the index (the step this script does NOT do):
  1. Decide the hosting base URL (proposal: https://communities-map.vercel.app/murmurations/)
  2. Deploy the profiles there (ship the murmurations/ dir with the map)
  3. Batch-register each profile URL: POST https://index.murmurations.network/v2/nodes
     {"profile_url": "<url>"}
  4. Validate a few against https://test-index.murmurations.network first.
Registration should be a deliberate, Gustaf-approved step — it makes the
dataset discoverable to every Murmurations consumer.
"""
import json, sys, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "map" / "data" / "map.json"
BASE_URL = "https://communities-map.vercel.app/murmurations/"  # proposal — atlas session confirms

def slugify(name, country):
    s = f"{name}-{country or ''}".lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "community"

def to_profile(c):
    p = {
        "linked_schemas": ["organizations_schema-v1.0.0"],
        "name": c["name"],
    }
    if c.get("url"): p["primary_url"] = c["url"]
    desc = c.get("what_it_is") or ""
    note = "Listed in the Living Atlas (communities-map.vercel.app); location approximate to ~1km to respect residential privacy."
    p["description"] = (desc + (" " if desc else "") + note).strip()
    if c.get("lat") is not None and c.get("lon") is not None:
        p["geolocation"] = {"lat": c["lat"], "lon": c["lon"]}
    if c.get("country"): p["country_name"] = c["country"]
    tags = ["intentional community"]
    if c.get("community_form"): tags.append(str(c["community_form"]))
    p["tags"] = tags
    return p

def main():
    data = json.loads(SRC.read_text())
    comms = data.get("communities", [])
    write_all = "--all" in sys.argv
    outdir = ROOT / "murmurations" / ("profiles" if write_all else "samples")
    outdir.mkdir(parents=True, exist_ok=True)
    seen, n = {}, 0
    for c in sorted(comms, key=lambda x: (x.get("name") or "", x.get("country") or "")):
        if not c.get("name"): continue
        slug = slugify(c["name"], c.get("country"))
        if slug in seen:
            seen[slug] += 1; slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 1
        (outdir / f"{slug}.json").write_text(json.dumps(to_profile(c), ensure_ascii=False, indent=1))
        n += 1
        if not write_all and n >= 10: break
    print(f"wrote {n} profiles to {outdir}  (base_url proposal: {BASE_URL})")

if __name__ == "__main__":
    main()
