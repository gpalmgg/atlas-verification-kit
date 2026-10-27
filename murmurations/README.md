# Murmurations federation — handoff (prepared 2026-07-09)

**What this is:** everything needed to publish the Living Atlas's 4,311 verified communities as [Murmurations](https://murmurations.network) profiles — the open protocol (120k+ nodes) that lets any platform, including GEN's 2025–26 map/directory rebuild, discover and pull this data with zero bilateral integration. This is the "federate unconditionally" move from the 2026-07-04 atlas research, and it strengthens the GEN data-partnership posture ("pull our data via the index — no burden on your one developer").

**What's here:**
- `scripts/murmurations-profiles.py` — generator, reads ONLY the consent-tiered public slice (`map/data/map.json`), so no non-public data can leak. `--all` writes all ~4,311 profiles.
- `samples/` — 10 generated examples for review.

**What's deliberately NOT done (atlas-session decisions):**
1. **Hosting** — proposal: ship `murmurations/profiles/` with the map deploy → profiles live at `communities-map.vercel.app/murmurations/<slug>.json`. Self-hosted profiles survive even if Murmurations-the-org folds.
2. **Schema check** — validate a few samples against the live schema (`test-index.murmurations.network`) before bulk registration; field names were written from the 2026-07-04 research and may need touching up against organizations_schema-v1.0.0 current.
3. **Index registration** — `POST https://index.murmurations.network/v2/nodes {"profile_url": ...}` per profile. This is the step that makes everything publicly discoverable — **Gustaf approves before it runs.**
4. Optional positioning move from the research: propose a dedicated `communities` schema to the Murmurations Library by PR — author the standard rather than fill someone else's.
