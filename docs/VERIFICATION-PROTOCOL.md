# Verification Protocol — verify on discovery, never in bulk again

**Standing rule (Gustaf, 2026-07-27):** the July 2026 bulk-verification campaign
(7,373 verdicts, five workflows, three days, two burned rate-limit windows) is not to be
repeated. From now on, **a community is verified at the moment it is found.** Verification
is part of research, not a debt paid later.

## What "verified on the spot" means for any new row

Every harvester, research prompt, and manual addition must deliver, per community:

1. **A verdict** — `verified-active` / `uncertain` / `verified-but-inactive` /
   `no-web-presence` — judged at ingestion time, not defaulted.
2. **One line of dated evidence** (`verification_note`) — "events calendar lists Aug 2026
   workshop", not "seems active". If the evidence is only a directory listing, say so.
3. **Method + date** (`verification_method`, `verified_date`).

Rows arriving without these fields land as `verification_status: null` and are **invisible
everywhere** (map and directory both show them as "not yet checked") — the pipeline
tolerates them but the protocol's point is that they should not be created.

## The standing rubric (from the 2026-07 campaign — reuse verbatim)

- **verified-active**: evidence belongs to THIS community (name/place match) AND shows
  operation in the current or previous year — dated content, upcoming events, active
  recruitment. A © footer year alone is NOT evidence.
- **uncertain**: matches but undatable, or identity unclear, or bot-blocked (403/captcha
  is not a dead site).
- **verified-but-inactive**: explicit closure/dissolution/for-sale.
- **no-web-presence**: a real search found nothing. (Different information than uncertain.)
- Never guess. Never invent. A wrong pin is worse than no pin.

## Cost discipline (learned the expensive way)

Do the web plumbing in **code**, judge with the **cheapest capable model**:
`scripts/econ_harvest.py` (page fetch + Brave API search, zero tokens) feeding a Haiku
snippet-judge. ~450 tokens/community. Never again 452 Opus agents doing their own fetching
(~3,200 tokens/community for the same verdicts).

## Where things go

- **IN** (`verified-active`/`recovered-cohousing`, pinned) → the map. Nothing else pins.
- **OUT** with evidence → the public Directory page (`/directory`) — accessible, labeled,
  never mixed with the verified layer.
- Removed listings → `EXCLUSIONS.json` (with reasons), enforced at ingest.

## Re-verification

Communities die quietly. A yearly re-check of the gold tier (same econ pipeline, ~$5-grade
job) keeps the map honest. Any OUT row that produces new evidence moves IN — the door
swings both ways, on evidence only.
