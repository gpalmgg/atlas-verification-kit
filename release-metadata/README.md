# Atlas: a census of communal living

**Version 2026-07-30** · 6,246 communities · 137 countries · CC BY-SA 4.0

A global dataset of intentional communities: ecovillages, cohousing, monasteries, kibbutzim,
Camphill and L'Arche houses, squats and land occupations, co-living labs, Transition Towns, and
a large number of communities affiliated with no network at all.

Compiled from roughly forty published directories in nine languages, deduplicated, and verified
against public web evidence.

## Files

| File | What it is |
|---|---|
| `atlas-2026-07-30.csv` | One row per community, readable column names. Start here. |
| `atlas-2026-07-30.json` | The published slice exactly as the live map serves it. |
| `CITATION.cff` | Citation metadata. |
| `LICENSE.txt` | CC BY-SA 4.0. |

## What is in scope

This release is the **verified, mapped slice only**. Two other layers exist and are not included:

- **5,209 directory entries**: real leads that could not be confirmed.
- **3,360 rejected entries**: checked and found not to be intentional
  communities (businesses, umbrella organisations, scraper artifacts, duplicates), kept for
  provenance.

Both are available to researchers and communities on request: editor@heartofecovillages.org

## Verification

Every entry carries one of two stamps:

- **verified-active**: dated evidence belonging to that specific community, showing operation in
  the current or previous year. A copyright footer year does not count.
- **network-verified**: carried in a membership body's own curated directory and accepted on that
  network's discernment. The `vouching_network` column names it.

## Privacy

Coordinates are deliberately fuzzed to roughly 1.1 km. Contact details and street addresses are
never published. No community opted in; everything here derives from what a community or its
federation published openly. Removal on request is honoured.

## Limits, stated plainly

1. **Verification was done by language models against a written rubric, not by people.** Every
   verdict carries dated evidence and the method used, and any of them can be audited and
   reversed. It is a first-pass filter, not peer review.
2. **No validation study.** No double-coded sample, no inter-rater agreement statistic.
3. **No ground truth.** No entry has been confirmed by phone, survey or visit. A thriving offline
   community is indistinguishable from a dead one.
4. **Geography follows the sources.** Coverage reflects which national networks publish good
   directories. Africa, South and Southeast Asia and most of Latin America are thin for this
   reason, not because the communities are absent.
5. **The inclusion boundary is inherited** from the source directories and then hand-trimmed.
6. **Classification is uneven.** Some form values are inferred from a source directory's prior
   rather than read from the community. Corrections are wanted.

Full procedure: the Method page on the map.

## Corrections

There is a feedback control on every screen of the map at
[heartofecovillages.org/#atlas](https://heartofecovillages.org/#atlas). Corrections are read by a
person against public evidence; a single report never alters a listing on its own.

## Citation

> Heart of Ecovillages (2026). *Atlas: a census of communal living* (Version 2026-07-30)
> [Data set]. https://heartofecovillages.org/#atlas
