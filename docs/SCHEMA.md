# Communities Database — Schema

`{ "meta": {...}, "entries": [ { …entry… }, … ] }`. Every field is optional — **missing = `null`/absent,
never guessed.** Entries are heterogeneous (different sources fill different fields); consumers should
degrade gracefully and surface confidence.

## Identity & contact
| Field | Type | Notes |
|---|---|---|
| `id` | string | slug |
| `name` | string | the community/network name (some long ones cleaned from blurbs — flagged `name_cleaned`) |
| `url` | string | official website |
| `country` / `region` | string | `region` may be a clean country OR a region-code (`eu-west`, `global`) |
| `city_region` | string | city / area / location line |
| `lat` / `lon` | number | present on ~1,556 only |
| `who_runs_it` | string | founders/stewards (sparse) |
| `contact` | string | public email (sparse; URL is the usual contact path) |

## Classification (the matching vocabulary — added Phase 1)
| Field | Values |
|---|---|
| `kind` | `destination` (a place) · `doorway` (a network/federation that leads to places) |
| `entry_type` | `community` · `federation` · `platform` · `creator` · `brand` · `virtual` · `hub` |
| `joinable` | bool — could a person actually go live/stay there. **Filter on this for "find me a community."** |
| `community_form` | `intentional-settlement` · `transformed-village` · `co-living-lab` · `popup` · `doorway` · `traditional-communal` · `care-residential` · `non-community` · `unclassified`. The *form* axis — what kind of thing it physically is. `community_form_inferred:true` = derived from directory-source prior, lower confidence. |
| `spectrum_category` | int 1–10 (the intentional-communities *spectrum*): 1 federation · 2 legacy-land-based · 3 utopian-scale · 4 contemplative-faith · 5 cohousing · 6 care · 7 anarchist-autonomous · 8 extitutional · 9 distributed-regen · 10 historical |
| `tags_canon` | string[] — **harmonized** controlled tags (ecovillage, cohousing, coliving, permaculture, commune, spiritual, anarchist, cooperative, care, transition, education, web3, art). Prefer over raw `tags`. |
| `tags` | string[] — raw source tags (mixed vocabularies; kept for provenance) |
| `identity_norm` | `LGBTQ+` · `Indigenous-led` · `Black/Afro` · `Women` · `Student/Youth` · `Faith-tradition` · `Other` (normalized from `identity_focus` free-text) |
| `identity_focus` | string — raw identity descriptor (free-text, wave3) |

## Status, scale, confidence
| Field | Notes |
|---|---|
| `status` | `active` · `forming` · `unclear` · `aspirational` |
| `research_confidence` | `high` · `medium` · `low` (research-sourced rows) |
| `is_adjacent` / `adjacent_label` | `true` = community-adjacent (eco-resort, refuge, peer network), not a core intentional community |
| `audience_scale` · `size` · `members_current` · `members_capacity` · `founded` | scale/age where known |
| `access_model` | `Short-term` · `Membership` · `Co-op Share` · `Event-based` · `Property` (sparse) |

## Provenance & verification
| Field | Notes |
|---|---|
| `source` | which harvest/list produced it (gen-europe-directory, ic-org, gen, kimi-global-sweep, kimi-wave2-networks, kimi-wave3-demographic, cohousing-us, …) |
| `source_url` · `source_dimension` · `logged_date` | trace back to origin |
| `verified_2026_06_11` | bool — hand-verified in the Kimi quality pass |
| `verification_note` · `needs_verification` · `verification_flags` · `editorial_sensitivity` | from the editorial/network master |
| `editorial_sensitivity` | bool — **delicate for the MAGAZINE to cover** (Rabhi lineage, Sámi bodies, Eisenstein). Not a safety signal. Do not conflate with `safeguarding_status`. |
| `safeguarding_status` | `documented` · `under-review` · `checked-clear` · `contested` · absent(default). Documented harm by the community to people inside it, per an external adjudicating body. **`under-review` and `contested` are internal only — never render per-community.** See `SAFEGUARDING.md`. |
| `country_inferred` · `community_form_inferred` · `name_cleaned` | flags marking derived (lower-confidence) values |
| `also_listed_as` | string[] — alternate names absorbed during dedup |
| `ext_links` | `[{label, url}]` — link-backs rendered on the card as outlined buttons next to "Visit site" (exported as `links`). Filled for FIC / GEN rows by `scripts/populate_fic_gen_ext_links.py` with labels `Listing on FIC` · `Listing on GEN` · `Listing on GEN Europe`; hand-added for peer documentation (ToGather). Never remove a hand-added link when re-running the script: it only appends, deduped by listing identity. |
| `external_ids` | `{ic: <ic.org directory slug>, gen: <ecovillage.org slug>}` — join keys to the federation directories, derived from `source_url` by `scripts/crosswalk_fic_gen.py`. GEN Europe national-network pages are **not** ids (they identify the network, not the community). See `docs/fic-gen-interop.md`. |

## Consent (pin suppression) — separate from verification
| Field | Notes |
|---|---|
| `pin_suppressed` | bool — **the row is never pinned on the map, whatever its `verification_status`.** It still appears in the Directory with "location withheld at the community's request". A permission fact, not an evidence fact: do not fold it into `verification_status` or `geo_status`. Set by `scripts/apply_pin_suppression.py` (a list from FIC / GEN or a direct request) or `scripts/sync_fic_gen.py --apply` (listing gone from the source). The exporter (`map/atlas/export-atlas-data.py`) enforces it as a gate before the verification gate. |
| `pin_suppressed_reason` | `source-hidden-location` (the home directory hides the location) · `community-request` · `source-removed` (listing deleted at FIC / GEN) · `other` |
| `pin_suppressed_at` | YYYY-MM-DD |

## Location precision (2026-10)
How precise a pin really is, and where it came from. The public class is derived mechanically from these fields by `map/atlas/export-atlas-data.py` (`prec_of`, `unc_of`); see METHODOLOGY §6.1. Provenance (`geocode_precision: given`, or a `community-*` `location_source`) wins over `geocode_level`. None of the fields below except the derived class and `unc` is published.

| Field | Type / values | Meaning | Written by |
|---|---|---|---|
| `geocode_level` | `address` · `street` · `town` · `region` · `country` | The level the geocoder actually returned, from `place_rank` of the cached response (`geo_core.level_of`). Exports as: address → "Address-level"; street, town → "Town centre"; region, country → "Approximate". `address` can only come from a street-level query. | `scripts/reclassify_precision.py`; `scripts/apply_site_addresses.py` (sets `address`) |
| `geocode_radius_km` | number, km (floor 0.5) | Upper bound on the pin's distance from the site: the greatest distance from the result point to a corner of the response's bounding box. Exported as `unc` for town pins, floored at 1.1 and rounded half-up. | `reclassify_precision.py`; `apply_site_addresses.py` |
| `geocode_unbounded` | bool | The hit's box exceeded 60 km, so the row exports as Approximate whatever its level. Paired with `geocode_unbounded_km`. | `reclassify_precision.py` |
| `geocode_cache_key` | string | Key of the Nominatim response in `cache-v2` that the level and radius were derived from. Internal; never exported. | `reclassify_precision.py` |
| `geocode_reclass` | `"2026-10"` | Marks a row as reclassified in this pass; makes `--apply` idempotent. | `reclassify_precision.py` |
| `coord_prev` | `{lat, lon, date}` | The coordinate before the first automated move of more than 1 km. First write wins; never overwritten. Internal; never exported. | `reclassify_precision.py`; `apply_site_addresses.py`; `fix_reported_2026_10.py` |
| `coord_note` | string | Why a pin is approximate or was changed, for example "pin not explained by its place text; approximate", "place text not found in country", "pinned at the country centroid". Semicolon-joined. | `reclassify_precision.py`; hand fixes |
| `site_address_src` | `{url, date}` | The community web page (contact, find-us, home or about; never impressum or legal) that an accepted address came from. Set together with `location_source: site-address-2026-10`. The address text itself is not stored. Never exported. | `scripts/apply_site_addresses.py` |

## Merges and archives (2026-10)
| Field | Notes |
|---|---|
| `merged_from` | string[] — ids of duplicate rows absorbed by this survivor. The absorbed rows are kept, with `geo_status: duplicate`, `duplicate_of`, `duplicate_reason`. Written by `scripts/fix_reported_2026_10.py` and `scripts/archive_occupied.py`. |
| `meta.occupied_archive` | `{file, count, date, rule}` — set when `scripts/archive_occupied.py --apply` has moved rows (13 on 2026-10-19) to the named file under `archive/`. Rows are restorable with `--restore`. Internal; the rule has no public note. Applying twice is refused while this is set. |

## meta
`entry_count`, snapshot/merge stamps (`last_*_merge`, `phase1_classified`, `phase2_pruned`), source list.
