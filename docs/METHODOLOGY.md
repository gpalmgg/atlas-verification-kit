# The Living Atlas: methodology

**Version 1.0, 2026-08-07.** Written in response to a request made on the IERI call of
2026-08-06, where two researchers independently asked that the procedure behind the Atlas be
documented step by step so that it can be evaluated, criticised, and if useful, cited.

> **Superseded in part, 2026-09-18.** The figures in this version are from 2026-08-07 and the
> map has moved twice since: the federation-roster removal and Transition layer of 2026-09-08,
> and the September rebuild that took it to **6,727 mapped of 15,637, 150 countries**. The
> method described here still holds; the counts do not. Current numbers and the full September
> account: `map/ONE-MAP.md`. A version 1.1 draft exists at
> `heart-of-ecovillages/editorial/strategy/atlas-successors/atlas-method-v1.1.md` (not adopted,
> and itself now carrying pre-09-18 counts).

Data as of 2026-08-07. The map: atlas.regencommunity.tools.
Maintained by Gustaf Palm for Heart of Ecovillages and Regen Community Tools.

This document describes what was actually done, including the parts that are weak. It is not a
justification. Where a step was a judgement call, it says so and names the call.

---

## 1. What the Atlas is trying to be

Research on intentional communities has no sampling frame. Studies either draw on one
federation's membership directory, which answers *who has joined us* rather than *what exists*,
or they snowball from personal contacts. Neither supports a claim about the population.

The Atlas is an attempt at a frame: a documented inclusion rule, per-entry provenance, an
auditable rejection set, and an evidence verdict attached to every row. It is not a membership
directory and does not aspire to become one.

**Inclusion boundary.** Deliberately wider than any single federation's remit. It holds
ecovillages, cohousing, monastic and other faith-rooted communal traditions, kibbutzim, care
communities, anarchist and autonomous projects, co-living and residency labs, Transition Towns,
and communities affiliated with no network at all. This width is the reason the project exists
separately from GEN and FIC, whose boundaries are properly set by membership.

**The boundary is inherited, and that is the weakest definitional fact about the project.** In
practice, inclusion means: something one of roughly 130 source directories treated as an
intentional community, minus what we checked and rejected. We did not derive the boundary from
first principles. The working definition in the background, credited to Daniel Greenberg, is
communities of people trying to live high quality, low impact lives.

## 2. Pipeline overview

    harvest  ->  dedup  ->  verify  ->  geocode  ->  publish (two tiers, fuzzed, allowlisted)
      16,400     merged     verdict    10,602        6,246 public
      leads      + flagged  per row    placeable     4,979 independent + 1,267 federation-listed

Each stage is described below with its counts, its rules, and its known failure modes.

## 3. Stage 1: harvest

**Sources.** About 130 published directories, all already public. Categories:

- Federation directories: GEN and its national bodies, FIC, and regional networks
- National cohousing and co-housing registers: Switzerland, Netherlands, Denmark, Germany,
  United Kingdom, United States, Canada, Australia, New Zealand, Spain
- Movement-specific directories: Camphill, L'Arche, Emmaus, Catholic Worker, Bruderhof,
  Anabaptist communal, the kibbutz movement, Auroville's internal community directory
- Regional networks: Colibris and Réseau Oasis (France), RIE (Iberia and Latin America),
  RIVE (Italy), Diggers and Dreamers and Radical Routes (UK), Wohnprojekte and Syndikat
  (Germany)
- Language-specific portals, including Russian (anastasia.ru, poselenia.ru), Japanese, and
  Indian (Vikalp Sangam)
- A Wikipedia canon pass, and a deliberate audit for well-known communities the directories
  missed

**Record.** Every ingest is logged in `INGESTION-LOG.md` with source, date, raw count,
duplicates removed, and a separate count of borderline matches (see stage 2).

**Known bias, stated plainly.** Harvesting from federation directories imports each
federation's definition of what counts, and imports each country's directory-publishing
culture. The result is visible in the data: France carries 1,620 entries and Italy 120. That
ratio is a fact about Colibris and RIVE, not about Europe. Africa, South and Southeast Asia,
and most of Latin America outside Brazil and Argentina are thin for the same reason.

## 4. Stage 2: deduplication

Entries were matched across sources on name, country and location. Three outcomes were
recorded rather than two:

- **merged**, where the matcher was confident two rows were the same community
- **borderline**, where it was not, logged as a separate count per source and left unmerged
- **distinct**

Borderline counts are large in some sources and are published rather than hidden. Examples:
`habitat-participatif-france`, 323 raw, 9 duplicates, 89 borderline. `cohousing-us`, 265 raw,
104 duplicates, 159 borderline. Alternate names absorbed during a merge are preserved in an
`also_listed_as` field rather than discarded.

**Why this is published.** Most datasets pick a similarity threshold and report a single clean
number. The borderline count is the honest measure of how much of the deduplication is
uncertain.

## 5. Stage 3: verification

This is the stage that most needs scrutiny, so it is described in full.

### 5.1 The rubric

Every verdict is made against this rubric and carries one line of dated evidence
(`verification_note`), the method used (`verification_method`) and a date (`verified_date`).

| Verdict | Criterion |
|---|---|
| `verified-active` | Evidence belongs to **this** community, name and place matching, **and** shows operation in the current or previous year: dated content, upcoming events, active recruitment. A copyright footer year is explicitly **not** evidence. |
| `uncertain` | Matches but undatable, or identity unclear, or bot-blocked. A 403 or captcha is recorded as *not* a dead site. |
| `verified-but-inactive` | Explicit closure, dissolution, or sale. |
| `no-web-presence` | A real search found nothing. Recorded as different information from `uncertain`. |
| `network-verified` | Carried in a federation's own directory and accepted on that network's discernment, with no independent check by us. |

Standing rule: never guess, never invent. A wrong pin is worse than no pin.

### 5.2 Who made the verdicts

**Large language models, working to the rubric above, with the web retrieval done in ordinary
code rather than by the model.** A script performs the page fetch and search API call; the
model judges the returned snippet against the rubric. This is stated plainly because it is the
single most important limitation of the dataset.

The July 2026 campaign produced 7,373 verdicts. An earlier approach, in which agents performed
their own retrieval, cost roughly 3,200 tokens per community for the same verdicts; the
code-fetch plus snippet-judge design costs roughly 450. The standing rule since is that a
community is verified at the moment it is discovered, not in a later bulk campaign.

### 5.3 What this method cannot do

- **It cannot distinguish a thriving offline community from a dead one.** 1,203 entries are
  marked `no-web-presence`, which is precisely the population where the method stops working.
- **It is biased toward communities with a web presence in a major language.** Minority-language
  and deliberately unlisted communities are systematically under-detected.
- **There is no validation study.** No double-coded sample, no human-adjudicated gold standard
  beyond the rubric text, no inter-rater agreement statistic. This is the most serious
  methodological gap in the project and it is not one we can close alone.
- **No entry has been confirmed by contact with the community.** Nobody has phoned, surveyed or
  visited.

The rejection set is preserved specifically so that any verdict can be audited and reversed. It
has been reversed before: an early pass rejected Swiss housing cooperatives as generic housing,
and a later review recovered 200 of them as genuine cohousing. The door swings both ways, on
evidence.

### 5.4 Current verdict distribution

Across all 16,400 entries:

| Verdict | Count |
|---|---|
| verified-active | 5,098 |
| uncertain | 2,847 |
| network-verified | 1,932 |
| no-web-presence | 1,203 |
| verified-but-inactive | 852 |
| dead-link | 237 |
| recovered-cohousing | 200 |
| **no verdict yet** | **4,031** |

## 6. Stage 4: geocoding and placement

| `geo_status` | Count | Meaning |
|---|---|---|
| pinned | 10,602 | Has coordinates good enough to place |
| rejected | 3,360 | Checked and found not to be an intentional community |
| staged | 853 | Harvested, not yet processed |
| unlocated | 560 | Real community, geocoding failed |
| out-of-scope | 460 | Outside the inclusion boundary |
| verified-unlocatable | 327 | Confirmed real, location not resolvable |
| non-geographic | 236 | Networks and federations with no single point |

Unlocated and verified-unlocatable rows are retained and reported rather than dropped. Each
pinned entry records how precise its coordinate is. Until 2026-10 that was a single
`geocode_precision` flag set at geocode time, which turned out to overstate precision (see
"Location precision" below). The public precision class now comes from `geocode_level`, the level
the geocoder actually returned.

### 6.1 Location precision (2026-10)

On 2026-10-19 a ground-truth audit of 40 pins found that the map labelled 5,377 pins "Exact
place" when most were town or region centroids reached through a silent fallback (a failed street
query falling back to the town, then the region, still recorded as `place`). The fix is a
mechanical rule, not a re-judgement of each row. The public map now has four classes:

| Public class | Meaning | Derived from |
|---|---|---|
| Address-level (shown to ~1 km) | The geocoder matched a street address or a building | `geocode_level` `address` |
| Placed by source or hand | The coordinate was supplied, not geocoded | provenance: source coordinates, hand placement, or community-supplied |
| Town centre (site nearby) | The pin is the centre of the named town; the site is within `unc` km | `geocode_level` `street` or `town` |
| Approximate (region or country) | Region or country centroid, or a box wider than 60 km | `geocode_level` `region` or `country`; any box over 60 km |

**How each row's class is derived.**

1. **The level is what Nominatim returned, not what we asked for.** `geo_core.level_of` reads
   `place_rank` from the cached response: 28 and above is `address`, 26-27 `street`, 13-25 `town`,
   5-12 `region`, below 5 `country`. A building-type result counts as `address` only if its
   bounding box has a radius of 1 km or less. A missing `place_rank` is an error, never a guess. If
   the row's `city_region` names a state and the response says another state, the level is capped
   at `region`.
2. **An address comes only from a street-level query.** A query with no house number, street word
   or postcode-plus-street (`is_street_query`) is sent to Nominatim as a settlement search
   (`featureType=settlement`) and can never return `address` or `street`. The first dry run had 211
   false address upgrades from queries such as "Rural California".
3. **Wide boxes are approximate.** A hit whose bounding-box radius exceeds 60 km is demoted to
   `country` class and marked `geocode_unbounded`, whatever its place rank.
4. **Provenance wins.** A coordinate that came from the source directory, was placed by hand, or
   was supplied by the community (`geocode_precision: given`, or a `community-*` `location_source`)
   is "Placed by source or hand" and is never overwritten by a geocode. Only a pin that has no
   precision recorded and a community-report source is read as `given` by default.
5. **Moves are rare.** A pin moves only if it lies outside its own country (15 rows). Otherwise
   the current pin is kept and only the level, radius and cache key are recorded. A pin that sits
   outside the honest hit's tolerance (inside the hit's box, or within the larger of its radius
   and 2 km) is *not* moved. It is labelled approximate and listed for review. 499 such
   "unexplained" pins exist. When no in-country result exists the row stays pinned at the country
   centroid with a `coord_note`.
6. **Town pins carry an uncertainty radius.** `unc` is the box radius in km, floored at 1.1 so
   nothing claims to be tighter than the publication rounding, rounded half-up. The map draws it as
   a true-scale circle on a selected pin.
7. **Website addresses.** For rows with a community website, a harvester reads the contact, find-us,
   home and about pages for a postal address and geocodes it. Impressum and legal pages are
   excluded: a spot-check of that class failed, because it names natural persons. A pilot gate
   (yield, accuracy, no private-home exposure) was signed by Gustaf before the full run. Address text
   is never stored, only the resulting coordinate and the page URL and date (`site_address_src`).
   An accepted address upgrades the pin to `address` level; anything over 50 km from the old
   pin, or out of country, goes to a review list instead. 450 upgrades were applied; 236 were then reverted, so the net is 214 upgraded pins. Lesson: the first targeting wrongly included 47 hand- or source-placed `given` rows and 189 source-coords rows, and the pass overwrote them. They were restored from the pre-apply backup. Website addresses never override source-supplied or hand-placed coordinates; `is_given` in `site_address_harvest.py` and `apply_site_addresses.py` enforces it.
8. **Publication rounding is unchanged.** Every published coordinate is still rounded to two
   decimals (about 1.1 km), with no jitter. "Address-level" therefore means the geocode matched an
   address, not that the map shows one. Rows with `pin_suppressed` are never fetched by the website
   harvest and never mapped.

**Result on the live map (2026-10-20).** Town centre 2,454; Approximate 2,138; Address-level
1,442; Placed by source or hand 622. Before: 5,377 "Exact place".

**Measured.** In the 40-pin ground-truth sample (27 verified pins), the number labelled more
precisely than they really are fell from 8 of 27 to 0 of 27
(`scripts/ground_truth_check.py`). Read this with care: two sample pins (`verein-wohnnetz`,
`bon-homme-hutterite-colony-2`) were corrected by hand from the same audit, so the sample no longer
measures the automated pipeline cleanly. Part of the sample was also chosen by the signals the fix
uses. It shows honesty on the sample, not accuracy across the map. A fresh held-out sample has not
been drawn yet and is needed before any claim about the whole map.

**Known weaknesses.** The 499 unexplained pins are labelled approximate but are not resolved. The
"town centre" class can sit several km from the site. Label honesty is verified; coordinate accuracy
is not.

## 7. Stage 5: the public slice

The published map is deliberately narrower than the database. `map/atlas/export-atlas-data.py`
derives it under three rules.

**Rule 1: two tiers only.** An entry reaches the map if `geo_status` is `pinned` **and**
`verification_status` is one of `verified-active`, `recovered-cohousing` (together, the
independently verified tier, 4,979) or `network-verified` (the federation-listed tier, 1,267).
Nothing else is published. Because the filter is an allowlist of statuses, the tier label
shown on any pin is true by construction rather than by editorial diligence.

Each published row carries an explicit `evidence` field, `independent` or `federation-listed`.
Consumers should read that field rather than infer from the internal status vocabulary.

**Rule 2: coordinates are fuzzed.** Every published coordinate is rounded to two decimal places,
roughly 800 metres to 1.1 km. These are residential addresses and the rounding is a deliberate
privacy floor, not a data limitation.

**Rule 3: fields are allowlisted, not blocklisted.** The generator enumerates the permitted
columns. Contact details, street and town, internal scores and source URLs are never emitted.
A newly added private column in the database cannot leak by omission, because omission is the
default.

## 8. Classification, and why parts of it should not be cited

The database carries several classification axes. They are not equally trustworthy and are
listed here in descending order of reliability.

| Axis | State |
|---|---|
| `community_form` (9 values, physical form) | Populated on all entries. **1,762 values are inferred** from the source directory's prior rather than read from the community, and are flagged `community_form_inferred`. |
| `entry_type` | Reliable. Distinguishes community from network, platform, creator. |
| `verification_status` / `evidence` | Reliable, as described in section 5. |
| `status` (active/forming/unclear) | **86% empty.** 14,074 of 16,400 have no value. Do not cite. |
| `spectrum_category` (10 editorial forms) | **Bulk-defaulted on import.** The great majority of classified rows sit in one category as an artifact. **Do not cite as a distribution.** This axis is an editorial commissioning tool, not a measurement. |
| `identity_norm` (who a community is for) | About 250 rows of 16,400. Essentially unsurveyed. |
| `access_model` | About 45 rows. Effectively unpopulated. |

**The open problem.** On the 2026-08-06 call, a researcher working in Latin America identified
communities labelled traditional that are intentional and the reverse. Two participants proposed
removing self-assigned labels entirely in favour of showing only which source maps a community
appears on. A third proposed keeping labels but always attaching their provenance and allowing
a community to disagree, and framed multi-perspective definition as a research question in its
own right.

**Adopted position, 2026-08-07:** labels are retained, provenance is always shown alongside
them, and a correction path is provided. Two of the three components already existed in the
interface (a verification filter and a source-map toggle) and were under-surfaced. The
disagreement mechanism is not built yet.

Note also that two taxonomies are in play at once, `community_form` and `spectrum_category`,
which doubles the exposure of any typology-alignment work with FIC or GEN.

## 9. Corrections and feedback

A feedback control was added to the map on 2026-08-07 in direct response to the call. Any
visitor can report an error from the map itself or from any community's page. Reports reach a
person, who checks them against public evidence; a single report never alters a listing on its
own.

Removal on request is honoured. No community opted in to being listed; every entry derives from
what a community or its federation published openly. There is no opt-in consent process, and
there should be. A proposed mechanism, writing to each listed community with the entry held and
inviting confirmation, correction or removal, would create a third and stronger evidence tier.
It is not built.

## 10. Reproducibility and citation

- Database: `communities-database.json`, schema in `SCHEMA.md`
- Ingest ledger: `INGESTION-LOG.md`
- Verification rubric: `VERIFICATION-PROTOCOL.md`
- Public slice generator: `map/atlas/export-atlas-data.py`
- Known data debt: `DATA-QUALITY-DEBT.md`

**Not yet available and needed before citation.** There is currently no versioned, immutable
snapshot with a persistent identifier. A citable release (for example via Zenodo, with a DOI per
version) is planned. Input on what such a release must contain to satisfy peer review is
actively wanted.

**Federation.** A Murmurations profile generator exists and reads only the consent-tiered public
slice. Registering with the Murmurations index would make every published entry discoverable
through an open protocol with no bilateral integration required of any partner. It has not been
fired, pending agreement with FIC and GEN.

## 11. Summary of limitations

1. No validation study of the classifier: no double-coded sample, no inter-rater agreement.
2. Verification is web-evidence only; no community has been contacted, surveyed or visited.
3. 4,031 entries carry no verdict, and 1,267 published entries rest on a federation's word.
4. Geography reflects directory-publishing culture, not the distribution of communities.
5. The inclusion boundary is inherited from source directories and hand-trimmed.
6. `spectrum_category` and `status` are not fit to be cited.
7. Two social axes, who a community is for and how it can be accessed, are unsurveyed.
8. No opt-in consent process exists.
9. No versioned citable snapshot exists yet.
