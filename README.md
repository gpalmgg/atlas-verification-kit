# Atlas Verification Kit

Open method, schema and scripts that Heart of Ecovillages uses to check, one by one, whether the intentional communities and ecovillages on its Living Atlas exist and are active.

Heart of Ecovillages is an association (France, loi 1901, registered October 2026) with several projects for the ecovillage and intentional-community movement. The Living Atlas maps about 15,500 gathered places across Europe and beyond, of which about 6,600 are mapped after checking.

## What is here

| Path | What it is |
|---|---|
| `docs/METHODOLOGY.md` | How places are gathered, deduplicated and checked, and what we measured about which checks work |
| `docs/VERIFICATION-PROTOCOL.md` | The step-by-step verification protocol |
| `docs/SCHEMA.md` | The record schema, with what each field means |
| `scripts/` | Deterministic helper scripts (geocoding core, link checks, dead-link marking, Murmurations profiles) with tests |
| `murmurations/` | Notes on publishing profiles to the Murmurations network |
| `release-metadata/` | Citation and licence notes for data releases |

No community data rows are included. Data releases follow separately, with a source and licence per value, and never include rows whose use is governed by agreements with other networks.

## Status

Work in progress. This repository was published in October 2026 as the base for a proposed verification kit. Most existing code and documents here were written with AI assistance (Claude, Anthropic), and the commit history in the source project shows it. Any future funded work on this kit will be written by people, with any read-only AI review recorded in `GENAI.md`.

## Licences

- Code: GNU Affero General Public License v3.0 or later (`LICENSE`, `LICENSES/AGPL-3.0-or-later.txt`).
- Documentation and Heart-made data: Creative Commons Attribution-ShareAlike 4.0 (`LICENSES/CC-BY-SA-4.0.txt`).

## Contact

editor@heartofecovillages.org
