#!/usr/bin/env python3
"""Shared geocoding core (atlas-coordinate-honesty A1, 2026-10-19).

One place for what geocode.py, coord_audit.py, coord_qc_fix.py and the reclassify/site-address
passes all need, so they cannot drift apart:

  * BBOX / OVERSEAS / in_country  - whole-country boxes (secondary check; coordinates without a response)
  * ISO / iso_codes               - country name -> ISO codes for EVERY `country` value on a mappable
                                    row; an unknown name raises instead of passing (primary check)
  * candidates()                  - the query ladder as (query, rung); garbage first segments dropped
  * geocode_v2()                  - hardened Nominatim call: addressdetails=1, limit=3, countrycodes,
                                    in-country pick, full response cached in .geocode-cache-v2.json,
                                    never caches an HTTP error, one live call at a time (file lock)
  * level_of()                    - explicit place_rank table -> address/street/town/region/country

The OLD cache (.geocode-cache.json) is never written here: it has no place_rank, so it cannot
support level_of, and A2 needs it byte-identical as the "before" record.
No network at import time. Stdlib only.
"""
import contextlib, fcntl, html, json, math, os, re, tempfile, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_V2 = os.path.join(HERE, ".geocode-cache-v2.json")
LOCK_PATH = os.path.join(HERE, ".nominatim.lock")
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "communities-database-geocoder/1.0 (editor@heartofecovillages.org)"
MIN_INTERVAL = 1.1      # Nominatim usage policy: <=1 req/s, enforced across processes via LOCK_PATH
MIN_RADIUS_KM = 0.5     # DB floor (town_pin_radius.py MIN_KM); the exporter floors again at 1.1
RETRIES = 4             # live attempts per query on 429 / 5xx / network error
BACKOFF = (2.0, 4.0, 8.0)

# ── country boxes (moved from coord_audit.py; BBOX/OVERSEAS verbatim, aliases added 2026-10-19) ──
# (lat_min, lat_max, lon_min, lon_max) - generous whole-country boxes.
BBOX = {
    "United States": (18.0, 71.5, -180.0, -66.0), "France": (41.0, 51.5, -5.5, 9.8),
    "Denmark": (54.5, 57.9, 8.0, 15.3), "United Kingdom": (49.8, 61.0, -8.7, 2.0),
    "Canada": (41.6, 83.2, -141.1, -52.6), "Germany": (47.2, 55.1, 5.8, 15.1),
    "Russia": (41.1, 82.1, 19.6, 191.0), "Israel": (29.4, 33.4, 34.2, 35.9),
    "Switzerland": (45.8, 47.9, 5.9, 10.6), "Netherlands": (50.7, 53.7, 3.3, 7.3),
    "Brazil": (-33.8, 5.3, -74.0, -34.8), "Spain": (35.9, 43.9, -9.4, 4.4),
    "Italy": (36.6, 47.1, 6.6, 18.6), "Namibia": (-29.0, -16.9, 11.7, 25.3),
    "Australia": (-43.7, -10.0, 112.9, 153.7), "India": (6.5, 35.6, 68.1, 97.4),
    "Portugal": (32.4, 42.2, -31.3, -6.2), "Mexico": (14.5, 32.8, -118.5, -86.7),
    "Belgium": (49.5, 51.5, 2.5, 6.4), "Uruguay": (-35.0, -30.0, -58.5, -53.0),
    "Tanzania": (-11.8, -0.9, 29.3, 40.5), "Colombia": (-4.3, 13.4, -79.1, -66.8),
    "Ukraine": (44.3, 52.4, 22.1, 40.2), "Lithuania": (53.9, 56.5, 20.9, 26.9),
    "Argentina": (-55.1, -21.8, -73.6, -53.6), "Costa Rica": (8.0, 11.2, -85.9, -82.5),
    "Kenya": (-4.7, 5.0, 33.9, 41.9), "New Zealand": (-47.3, -34.4, 166.4, 178.6),
    "Japan": (24.0, 45.6, 122.9, 145.8), "Sweden": (55.3, 69.1, 11.1, 24.2),
    "South Africa": (-34.9, -22.1, 16.5, 32.9), "Austria": (46.4, 49.0, 9.5, 17.2),
    "Thailand": (5.6, 20.5, 97.3, 105.6), "Democratic Republic of the Congo": (-13.5, 5.4, 12.2, 31.3),
    "Ecuador": (-5.0, 1.7, -81.1, -75.2), "Chile": (-56.0, -17.5, -75.7, -66.4),
    "China": (18.2, 53.6, 73.5, 134.8), "Norway": (57.9, 71.4, 4.6, 31.1),
    "Poland": (49.0, 54.9, 14.1, 24.2), "Ireland": (51.4, 55.4, -10.6, -5.9),
    "Philippines": (4.6, 21.1, 116.9, 126.6), "Peru": (-18.4, -0.0, -81.4, -68.7),
    "Indonesia": (-11.0, 6.1, 95.0, 141.0), "Hungary": (45.7, 48.6, 16.1, 22.9),
    "South Korea": (33.1, 38.6, 125.9, 129.6), "Greece": (34.8, 41.8, 19.4, 28.3),
    "Nigeria": (4.3, 13.9, 2.7, 14.7), "Finland": (59.8, 70.1, 20.6, 31.6),
    "Madagascar": (-25.6, -11.9, 43.2, 50.5), "Czech Republic": (48.6, 51.1, 12.1, 18.9),
    "Turkey": (35.8, 42.1, 26.0, 44.8), "Romania": (43.6, 48.3, 20.3, 29.7),
    "Nepal": (26.3, 30.4, 80.1, 88.2), "Uganda": (-1.5, 4.2, 29.6, 35.0),
    "Senegal": (12.3, 16.7, -17.5, -11.4), "Paraguay": (-27.6, -19.3, -62.6, -54.3),
    "Togo": (6.1, 11.1, -0.1, 1.8), "Ethiopia": (3.4, 14.9, 33.0, 48.0),
    "Bulgaria": (41.2, 44.2, 22.4, 28.6), "Scotland, UK": (54.6, 61.0, -8.7, -0.7),
    "Vietnam": (8.4, 23.5, 102.1, 109.6), "Malaysia": (0.8, 7.5, 99.6, 119.4),
    "Cambodia": (9.9, 14.7, 102.3, 107.7), "Laos": (13.9, 22.6, 100.0, 107.8),
    "Myanmar": (9.5, 28.6, 92.1, 101.2), "Taiwan": (21.8, 25.4, 119.9, 122.1),
    "Hong Kong": (22.1, 22.6, 113.8, 114.5),
}
# overseas territories legitimately outside the mainland box (not errors)
OVERSEAS = {
    "Spain": [(27.5, 29.5, -18.3, -13.3)],          # Canary Islands
    "Portugal": [(36.9, 39.8, -25.8, -24.9), (32.4, 33.2, -17.3, -16.2)],  # Azores, Madeira
    "France": [(14.3, 16.6, -61.9, -60.7), (-21.5, -20.8, 55.2, 55.9),      # Martinique/Guadeloupe, Réunion
               (3.9, 5.9, -54.7, -51.5)],                                    # French Guiana
    "United States": [(18.9, 22.3, -160.3, -154.7), (17.9, 18.6, -67.3, -65.2)],  # Hawaii, Puerto Rico
}
# 2026-10-19: names that used to fall through to "no bbox" or to the wrong box.
BBOX_ALIAS = {
    "czechia": "Czech Republic", "česko": "Czech Republic",
    "scotland": "Scotland, UK", "scotland, uk": "Scotland, UK",
    "uk": "United Kingdom", "great britain": "United Kingdom",
    "england": "United Kingdom", "wales": "United Kingdom",
    "canary islands": "Spain", "islas canarias": "Spain",
    "usa": "United States", "us": "United States",
    "türkiye": "Turkey", "turkiye": "Turkey", "viet nam": "Vietnam",
    "democratic republic of congo": "Democratic Republic of the Congo",
    "congo kinshasa": "Democratic Republic of the Congo",
    "tanzania, united republic of": "Tanzania",
}
_BBOX_FOLD = {k.casefold(): k for k in BBOX}


def bbox_name(country):
    """Canonical BBOX key for a country string (aliases applied), or None if there is no box."""
    if not country:
        return None
    k = html.unescape(str(country)).strip().casefold()
    if k in _BBOX_FOLD:
        return _BBOX_FOLD[k]
    return BBOX_ALIAS.get(k)


def bbox_for(country):
    n = bbox_name(country)
    return BBOX.get(n) if n else None


def in_overseas(country, lat, lon):
    n = bbox_name(country)
    return any(a <= lat <= b and d <= lon <= e for (a, b, d, e) in OVERSEAS.get(n, []))


def in_country(lat, lon, country):
    """Secondary check, for coordinates that arrive without a Nominatim response (hand-fixes).
    No box for the country -> True (coverage gap tracked by coord_audit, not a verdict)."""
    box = bbox_for(country)
    if not box:
        return True
    if in_overseas(country, lat, lon):
        return True
    a, b, c, d = box
    return a <= lat <= b and c <= lon <= d


# ── ISO map: every `country` value on a row with lat/lon or geo_status pinned ───────────────────
# Generated 2026-10-19 from the DB (181 distinct values, incl. None). () = not a single country
# (no countrycodes filter, no in-country check). Unknown names raise: a silent pass is how
# "Maryland, Netherlands" got into a US row.
ISO = {
    "Albania": ("al",), "Algeria": ("dz",), "Angola": ("ao",), "Argentina": ("ar",), "Armenia": ("am",),
    "Australia": ("au",), "Austria": ("at",), "Bangladesh": ("bd",), "Belarus": ("by",), "Belgium": ("be",),
    "Belize": ("bz",), "Benin": ("bj",), "Bhutan": ("bt",), "Bolivia": ("bo",),
    "Bosnia and Herzegovina": ("ba",), "Botswana": ("bw",), "Brazil": ("br",), "Bulgaria": ("bg",),
    "Burkina Faso": ("bf",), "Burundi": ("bi",), "Cabo Verde": ("cv",), "Cambodia": ("kh",),
    "Cameroon": ("cm",), "Canada": ("ca",), "Central African Republic": ("cf",), "Chad": ("td",),
    "Chile": ("cl",), "China": ("cn",), "Colombia": ("co",), "Congo Kinshasa": ("cd",),
    "Costa Rica": ("cr",), "Cote d'Ivoire": ("ci",), "Côte d'Ivoire": ("ci",), "Ivory Coast": ("ci",),
    "Croatia": ("hr",), "Cuba": ("cu",), "Curaçao": ("cw", "nl"), "Cyprus": ("cy",),
    "Czech Republic": ("cz",), "Czechia": ("cz",), "Česko": ("cz",),
    "Democratic Republic of Congo": ("cd",), "Democratic Republic of the Congo": ("cd",),
    "Denmark": ("dk",), "Dominica": ("dm",), "Dominican Republic": ("do",), "Ecuador": ("ec",),
    "Egypt": ("eg",), "Eritrea": ("er",), "Estonia": ("ee",), "Ethiopia": ("et",), "Fiji": ("fj",),
    "Finland": ("fi",), "France": ("fr",), "Gambia": ("gm",), "The Gambia": ("gm",), "Georgia": ("ge",),
    "Germany": ("de",), "Ghana": ("gh",), "Greece": ("gr",), "Guatemala": ("gt",), "Guinea": ("gn",),
    "Guyana": ("gy",), "Haiti": ("ht",), "Honduras": ("hn",), "Hong Kong": ("hk", "cn"), "Hungary": ("hu",),
    "Iceland": ("is",), "India": ("in",), "Indonesia": ("id",), "Iran": ("ir",), "Iraq": ("iq",),
    "Ireland": ("ie",), "Israel": ("il",), "Italy": ("it",), "Jamaica": ("jm",), "Japan": ("jp",),
    "Jordan": ("jo",), "Kazakhstan": ("kz",), "Kenya": ("ke",), "Laos": ("la",), "Latvia": ("lv",), "Lebanon": ("lb",),
    "Liberia": ("lr",), "Liechtenstein": ("li",), "Lithuania": ("lt",), "Luxembourg": ("lu",),
    "Macedonia": ("mk",), "Madagascar": ("mg",), "Malawi": ("mw",), "Malaysia": ("my",), "Mali": ("ml",),
    "Mauritania": ("mr",), "Mauritius": ("mu",), "Mexico": ("mx",), "Moldova": ("md",),
    "Montenegro": ("me",), "Morocco": ("ma",), "Mozambique": ("mz",), "Myanmar": ("mm",),
    "Namibia": ("na",), "Nepal": ("np",), "Netherlands": ("nl",), "New Zealand": ("nz",),
    "Nicaragua": ("ni",), "Nigeria": ("ng",), "Norway": ("no",), "Pakistan": ("pk",),
    "Palestine": ("ps",), "Panama": ("pa",), "Papua New Guinea": ("pg",), "Paraguay": ("py",),
    "Peru": ("pe",), "Philippines": ("ph",), "Poland": ("pl",), "Portugal": ("pt",), "Romania": ("ro",),
    "Russia": ("ru",), "Rwanda": ("rw",), "Saint Lucia": ("lc",), "Senegal": ("sn",), "Serbia": ("rs",),
    "Sierra Leone": ("sl",), "Singapore": ("sg",), "Sint Maarten": ("sx", "nl"), "Slovakia": ("sk",),
    "Slovenia": ("si",), "Solomon Islands": ("sb",), "South Africa": ("za",), "South Korea": ("kr",),
    "Spain": ("es",), "Sri Lanka": ("lk",), "Suriname": ("sr",), "Sweden": ("se",),
    "Switzerland": ("ch",), "Syria": ("sy",), "Taiwan": ("tw",), "Tanzania": ("tz",),
    "Tanzania, United Republic of": ("tz",), "Thailand": ("th",), "Togo": ("tg",),
    "Trinidad and Tobago": ("tt",), "Tunisia": ("tn",), "Turkey": ("tr",), "Türkiye": ("tr",),
    "Uganda": ("ug",), "Ukraine": ("ua",), "United Kingdom": ("gb",), "United States": ("us",),
    "Uruguay": ("uy",), "Vanuatu": ("vu",), "Venezuela": ("ve",), "Vietnam": ("vn",), "Viet Nam": ("vn",),
    "Zambia": ("zm",), "Zimbabwe": ("zw",),
    # UK nations / regions are filed as countries on some rows; Nominatim says country_code "gb"
    "Scotland": ("gb",), "Scotland, UK": ("gb",), "England": ("gb",), "Wales": ("gb",),
    "England: London & SE": ("gb",), "England: Midlands": ("gb",), "England: The North": ("gb",),
    "Wales & Borders": ("gb",), "UK": ("gb",), "USA": ("us",),
    # territories: Nominatim reports their own code, so accept the parent as well
    "Canary Islands": ("es",), "France (Réunion)": ("re", "fr"), "Reunion": ("re", "fr"),
    "New Caledonia (France)": ("nc", "fr"),
    "Ukraine (Crimea)": ("ua", "ru"), "Ukraine (de facto Russian-controlled)": ("ua", "ru"),
    "Serbia And Montenegro": ("rs", "me"),
    "Norway / Sweden / Finland / Russia (Sápmi)": ("no", "se", "fi", "ru"),
    # two-letter ISO codes stored verbatim on a few rows
    "CM": ("cm",), "CU": ("cu",), "DO": ("do",), "ET": ("et",), "GH": ("gh",), "GM": ("gm",),
    "JM": ("jm",), "PS": ("ps",), "UG": ("ug",),
    # not a single country: no filter, no in-country check
    "International": (), "Unknown": (), "Southeast Europe": (), "Western European Countries": (),
}
_ISO_FOLD = {html.unescape(k).casefold(): v for k, v in ISO.items()}


class UnknownCountry(ValueError):
    """A `country` value with no ISO entry. Add it to ISO deliberately; never pass it silently."""


def iso_codes(country):
    """ISO codes acceptable for `country`, as a tuple; () means not a single country (no filter).
    None / '' -> (). Unknown name raises UnknownCountry."""
    if country is None or not str(country).strip():
        return ()
    k = html.unescape(str(country)).strip().casefold()
    if k not in _ISO_FOLD:
        raise UnknownCountry(f"no ISO entry for country {country!r}; add it to geo_core.ISO")
    return _ISO_FOLD[k]


# ── shared JSON cache IO ────────────────────────────────────────────────────────────────────────
def load_json(path, default=None):
    """Load a JSON cache; a missing file gives `default`. A corrupt file RAISES: treating it as empty
    would let the next write replace a damaged-but-recoverable cache with nothing."""
    if not os.path.exists(path):
        return {} if default is None else default
    with open(path) as f:
        return json.load(f)


def atomic_write_json(path, obj, **dump_kw):
    """Write temp file in the same directory, fsync, os.replace. An interrupted write leaves the old
    file intact and parseable; the temp file is removed on failure."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, **dump_kw)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)          # mkstemp is 0600; caches are plain shared files
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


# ── query ladder (moved from geocode.py; garbage-first-segment drop added 2026-10-19) ───────────
NON_GEO = {"global", "worldwide", "eu", "eu-west", "eu-east", "eu-north", "eu-south", "europe",
           "international", "various", "multiple", "online", "virtual", "na", "n/a", ""}
DIRECTION = re.compile(r"^(south|north|east|west|central|southern|northern|eastern|western|"
                       r"se|sw|ne|nw|s|n|e|w)\s+", re.I)
ALIAS = {
    "deutschland": "Germany", "österreich": "Austria", "schweiz": "Switzerland", "suisse": "Switzerland",
    "svizzera": "Switzerland", "españa": "Spain", "italia": "Italy", "belgië": "Belgium", "belgique": "Belgium",
    "nederland": "Netherlands", "the netherlands": "Netherlands", "holland": "Netherlands", "sverige": "Sweden",
    "norge": "Norway", "danmark": "Denmark", "suomi": "Finland", "éire": "Ireland", "brasil": "Brazil",
    "méxico": "Mexico", "台灣": "Taiwan", "česko": "Czechia", "czech republic": "Czechia", "uk": "United Kingdom",
    "u.k.": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom",
    "usa": "United States", "u.s.a.": "United States", "u.s.": "United States", "us": "United States",
}


def clean_country(raw):
    """'Brazil (Vale do Itamboatá)' -> 'Brazil'; 'southern Poland' -> 'Poland'; 'global' -> None."""
    if not raw:
        return None
    s = str(raw).split(";")[0].split("(")[0].strip().strip(",").strip()
    s = DIRECTION.sub("", s).strip()
    low = s.lower()
    if low in NON_GEO:
        return None
    if low in ALIAS:
        return ALIAS[low]
    return s or None


def clean_place(raw):
    """Trim prose lead-ins from city_region: 'Headquarters in Lahel, Podor Region' -> 'Lahel, Podor Region'."""
    if not raw:
        return None
    s = str(raw).strip()
    s = re.sub(r"^(secretariat|headquarters?|hq|located|based|situated|set)\s+(in|at|near)\s+", "", s, flags=re.I)
    s = re.sub(r"^(in|at|near)\s+", "", s, flags=re.I)
    return s.strip().strip(",") or None


def strip_parens(s):
    return re.sub(r"\s*\([^)]*\)", "", s).strip().strip(",").strip()


_POSTCODE_ONLY = re.compile(r"^\d[\d\s\-]*$|^[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}$")
_POSTCODE_TAIL = re.compile(r"^(.*\D)\s+\d{4,6}$")


def _is_garbage(seg):
    """A segment that must not START a query: <=3 chars (state codes, 'NY', stray letters), or a bare
    postcode. 'Odisha 767062, India' geocoded to the wrong state (Shikha). 3-letter segments survive
    only when they read as a name ('Ayr', 'Ely', 'Rye'): alphabetic and not ALL-CAPS ('USA', 'UAE')."""
    s = seg.strip()
    if len(s) <= 2:
        return True
    if _POSTCODE_ONLY.match(s):
        return True
    if len(s) == 3:
        return not (s.isalpha() and not s.isupper())
    return False


def ladder(place, country, name=""):
    """Ordered specific->coarse as (query, rung, kind); kind is 'place' or 'country'. `rung` is the
    index in the UNFILTERED ladder, so a dropped garbage rung leaves a gap and rung > 0 still means
    'silent fallback' (A5). The country-centroid rung comes last, at rung len(place segments)."""
    out = []
    n_seg = 0
    if place:
        segs = [ALIAS.get(strip_parens(s).lower(), strip_parens(s)) for s in place.split(",")]
        # 'Odisha 767062' -> 'Odisha': a trailing postcode on a name is noise (bare ones stay, to be dropped)
        segs = [(_POSTCODE_TAIL.sub(r"\1", s) if _POSTCODE_TAIL.match(s) else s) for s in segs]
        segs = [s for s in segs if s]
        if country and segs and segs[-1].lower() == country.lower():
            segs = segs[:-1]
        n_seg = len(segs)
        for i in range(n_seg):
            if _is_garbage(segs[i]):
                continue
            sub = ", ".join(segs[i:])
            q = f"{sub}, {country}" if country and country.lower() not in sub.lower() else sub
            out.append((q, i, "place"))
    if country:
        out.append((country, n_seg, "country"))
    if not out:                                    # Stage 3: no location text, infer country from the name
        guess = country_from_name(name or "")
        if guess:
            out.append((guess, 0, "country"))
    return out


def candidates(place, country, name=""):
    """The ladder as (query, rung_index) pairs."""
    return [(q, rung) for q, rung, _ in ladder(place, country, name)]


COUNTRIES = ["Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia", "Austria", "Bangladesh",
 "Belgium", "Bhutan", "Bolivia", "Bosnia", "Botswana", "Brazil", "Bulgaria", "Cambodia", "Cameroon", "Canada",
 "Chile", "China", "Colombia", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czechia", "Denmark", "Ecuador", "Egypt",
 "Estonia", "Ethiopia", "Finland", "France", "Georgia", "Germany", "Ghana", "Greece", "Guatemala", "Hungary",
 "Iceland", "India", "Indonesia", "Iran", "Ireland", "Israel", "Italy", "Japan", "Kenya", "Latvia", "Lithuania",
 "Luxembourg", "Malaysia", "Mexico", "Moldova", "Mongolia", "Morocco", "Nepal", "Netherlands", "New Zealand",
 "Nicaragua", "Nigeria", "Norway", "Pakistan", "Peru", "Philippines", "Poland", "Portugal", "Romania", "Russia",
 "Scotland", "Senegal", "Serbia", "Singapore", "Slovakia", "Slovenia", "South Africa", "South Korea", "Spain",
 "Sri Lanka", "Sweden", "Switzerland", "Taiwan", "Tanzania", "Thailand", "Turkey", "Uganda", "Ukraine",
 "United Kingdom", "United States", "Uruguay", "Venezuela", "Vietnam", "Zambia", "Zimbabwe"]
NAME_HINTS = {c.lower(): c for c in COUNTRIES}
NAME_HINTS.update(ALIAS)
NAME_HINTS.update({"england": "United Kingdom", "wales": "United Kingdom", "britain": "United Kingdom"})
# longest keys first so "United Kingdom" wins over "Kingdom", "South Africa" over "Africa"
HINT_KEYS = sorted(NAME_HINTS, key=len, reverse=True)


def country_from_name(name):
    low = f" {name.lower()} "
    for key in HINT_KEYS:
        if re.search(rf"\b{re.escape(key)}\b", low):
            return NAME_HINTS[key]
    return None


# ── level_of: explicit place_rank table (stress-test blocker 1; A13/A14/A15) ───────────────────
# A query is "street-level" when it names a street or a house number. Only those may legitimately come back
# as street/address; "Global, Denmark" or "Rural California, United States" matching a same-named shop is
# the false-address bug of 2026-10-20. Segments are checked one by one; a bare postcode never counts.
_STREET_WORD = re.compile(
    r"(?i)(?<![\w])(?:str(?:eet|aße|asse|aat|\.)?|road|rd\.?|lane|ln\.?|avenue|ave\.?|av\.|drive|dr\.|"
    r"boulevard|blvd|vej|gade|gaden|alle|allé|all\u00e9e|weg|laan|plein|platz|"
    r"gasse|gata|gatan|v\u00e4gen|v\u00e4g|katu|ulica|ul\.|ulitsa|\u0443\u043b\.?|\u0443\u043b\u0438\u0446\u0430|"
    r"\u043f\u0440\.|\u043f\u0435\u0440\.|rue|chemin|impasse|cours|quai|via|viale|piazza|strada|"
    r"calle|carrer|camino|carretera|avenida|rua|estrada|travessa|stra\u00dfe)(?![\w])")


def is_street_query(q):
    """True when `q` (comma-separated, last segment usually the country) names a street or house number."""
    segs = [x.strip() for x in str(q or "").split(",") if x.strip()]
    for seg in segs:
        if _POSTCODE_ONLY.match(seg):
            continue
        if _STREET_WORD.search(seg):
            return True
        # 'Kirkebakken 80', '12 Mill Lane': a short number attached to a word (not a 4-6 digit postcode)
        if re.search(r"[^\W\d_]{3,}\.?\s+\d{1,3}\s?[a-zA-Z]?$|^\d{1,3}\s?[a-zA-Z]?\s+[^\W\d_]{3,}", seg):
            return True
    return False


def feature_for(q, country):
    """featureType for a query: None (street-level, unrestricted), 'country' (the bare country),
    'settlement' (any other place text: answer must be a town/region, never a POI)."""
    if is_street_query(q):
        return None
    if str(q).strip().casefold() == str(country or "").strip().casefold():
        return "country"
    return "settlement"


SITE_TYPES = {"house", "building", "amenity", "tourism", "leisure", "office"}
LEVELS = ("country", "region", "town", "street", "address")   # coarse -> fine
_STATE_KEYS = ("state", "province", "region", "state_district", "county")


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def radius_km(resp):
    """Greatest distance from the result point to any corner of its bounding box (an upper bound,
    as in town_pin_radius.py). None when the response has no usable box."""
    bb = resp.get("boundingbox")
    try:
        s, n, w, e = (float(x) for x in bb)
        lat, lon = float(resp["lat"]), float(resp["lon"])
    except (TypeError, ValueError, KeyError):
        return None
    return max(haversine_km(lat, lon, cy, cx) for cy in (s, n) for cx in (w, e))


def _fold(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", html.unescape(str(s))).casefold()
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def state_mismatch(resp, city_region):
    """True when city_region ends in a named state/province/county that the response does not contain
    (same-name town in the wrong region: Shikha at Odisha vs elsewhere). Needs >=2 comma segments, the
    last non-country one is the claim. It must appear in a state-level address field, or at least in
    display_name; otherwise it is a mismatch. No claim, or no address in the response -> False."""
    if not city_region:
        return False
    segs = [_fold(strip_parens(s)) for s in str(city_region).split(",")]
    segs = [s for s in segs if s]
    # UK nations are real state-level claims ('Edinburgh, Scotland'), so they stay in
    country_names = ({_fold(k) for k in ISO} | {_fold(k) for k in ALIAS}) - {"scotland", "england", "wales"}
    segs = [s for s in segs if s not in country_names and not _POSTCODE_ONLY.match(s)]
    if len(segs) < 2:
        return False
    claim = segs[-1]
    addr = resp.get("address") or {}
    if not addr:
        return False
    states = [_fold(addr[k]) for k in _STATE_KEYS if addr.get(k)]
    if any(claim == s or claim in s or s in claim for s in states):
        return False
    return claim not in _fold(resp.get("display_name") or "")


def level_of(resp, city_region=None):
    """address / street / town / region / country for one cached response.

    place_rank first: >=28 address; 26-27 street; 13-25 town (hamlet 20, dwelling 22); 5-12 region;
    <5 country. A SITE_TYPES addresstype is `address` only when its bbox radius is <= 1 km (a
    `tourism` park with a 30 km box is not an address). Missing place_rank raises: guessing a level
    is exactly the silent-`place` bug. A state/county in city_region that the response contradicts
    caps the level at `region`."""
    pr = resp.get("place_rank")
    if pr is None or pr == "":
        raise ValueError(f"missing place_rank in response {resp.get('display_name')!r}")
    pr = int(pr)
    r = radius_km(resp)
    if pr >= 28:
        lvl = "address"
    elif resp.get("addresstype") in SITE_TYPES and r is not None and r <= 1.0:
        lvl = "address"
    elif pr >= 26:
        lvl = "street"
    elif pr >= 13:
        lvl = "town"
    elif pr >= 5:
        lvl = "region"
    else:
        lvl = "country"
    if LEVELS.index(lvl) > LEVELS.index("region") and state_mismatch(resp, city_region):
        lvl = "region"
    return lvl


# ── cross-process rate limit ────────────────────────────────────────────────────────────────────
class LockTimeout(RuntimeError):
    pass


class GeocodeError(RuntimeError):
    """Live call failed after retries (429, 5xx, network). Nothing was cached."""


class CacheMiss(KeyError):
    """live=False and the query is not in cache-v2."""


def _sleep(s):          # indirection so tests can skip backoff without touching time.sleep globally
    time.sleep(s)


class _Gate:
    def __init__(self, f):
        self.f = f

    def _last(self):
        self.f.seek(0)
        try:
            return float(self.f.read().strip() or 0)
        except ValueError:
            return 0.0

    def wait(self):
        """Block until MIN_INTERVAL has passed since the last live call by ANY process."""
        gap = self._last() + MIN_INTERVAL - time.time()
        if gap > 0:
            _sleep(gap)

    def stamp(self):
        self.f.seek(0)
        self.f.truncate()
        self.f.write(repr(time.time()))
        self.f.flush()


@contextlib.contextmanager
def nominatim_gate(lock_timeout=None):
    """Exclusive file lock on LOCK_PATH: one live Nominatim caller at a time, machine-wide. The lock
    file also carries the timestamp of the last call. lock_timeout=None blocks; a number raises
    LockTimeout after that many seconds."""
    f = open(LOCK_PATH, "a+")
    try:
        if lock_timeout is None:
            fcntl.flock(f, fcntl.LOCK_EX)
        else:
            end = time.time() + lock_timeout
            while True:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.time() >= end:
                        raise LockTimeout(f"{LOCK_PATH} held by another process")
                    time.sleep(0.05)
        yield _Gate(f)
    finally:
        f.close()       # closing releases the flock


# ── geocode_v2 ──────────────────────────────────────────────────────────────────────────────────
_mem = {"sig": None, "data": None}


def _load_cache():
    """cache-v2 as a dict, re-read only when the file changed (another process may have written)."""
    try:
        st = os.stat(CACHE_V2)
        sig = (CACHE_V2, st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        sig = (CACHE_V2, None, None)
    if _mem["sig"] != sig:
        _mem["data"] = load_json(CACHE_V2)
        _mem["sig"] = sig
    return _mem["data"]


def _fetch(url):
    """One HTTP GET -> parsed JSON list. Raises urllib.error.* / OSError / ValueError."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _query_live(gate, q, codes, feature=None):
    params = {"q": q, "format": "json", "limit": 3, "addressdetails": 1}
    if feature:
        params["featureType"] = feature
    if codes:
        params["countrycodes"] = ",".join(codes)
    url = f"{NOMINATIM}?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(RETRIES):
        gate.wait()
        try:
            data = _fetch(url)
            gate.stamp()
            if not isinstance(data, list):
                raise ValueError(f"unexpected response type {type(data).__name__}")
            return data
        except urllib.error.HTTPError as e:
            gate.stamp()
            last = f"HTTP {e.code}"
            ra = e.headers.get("Retry-After") if e.headers else None
            extra = min(float(ra), 60.0) if ra and ra.isdigit() else 0.0
        except (urllib.error.URLError, OSError, ValueError) as e:
            gate.stamp()
            last = f"{type(e).__name__}: {e}"
            extra = 0.0
        if attempt < RETRIES - 1:
            _sleep(max(BACKOFF[min(attempt, len(BACKOFF) - 1)], extra))
    raise GeocodeError(f"{q!r}: {last} after {RETRIES} attempts (not cached)")


def _pick(results, codes):
    """First result whose address.country_code is acceptable. No codes (non-country row): first."""
    for r in results:
        if not codes:
            return r
        cc = ((r.get("address") or {}).get("country_code") or "").lower()
        if cc in codes:
            return r
    return None


def _slim(r):
    pr = r.get("place_rank")
    return {
        "lat": float(r["lat"]), "lon": float(r["lon"]),
        "class": r.get("class") or r.get("category"), "type": r.get("type"),
        "addresstype": r.get("addresstype"),
        "place_rank": int(pr) if pr not in (None, "") else None,
        "boundingbox": [float(x) for x in r["boundingbox"]] if r.get("boundingbox") else None,
        "display_name": r.get("display_name"),
        "address": r.get("address") or {},
    }


def cache_key(q, country, feature=None):
    """feature=None keeps the pre-2026-10-20 key format, so old entries stay valid for old callers."""
    base = f"{q}|{','.join(iso_codes(country))}"
    return f"{base}|ft={feature}" if feature else base


def _derive(entry, key, city_region):
    """Cached entry + level and floored radius, as a new dict (the cache stays context-free)."""
    out = dict(entry)
    out["cache_key"] = key
    out["level"] = level_of(entry, city_region)
    r = radius_km(entry)
    out["radius_km"] = None if r is None else round(max(r, MIN_RADIUS_KM), 2)
    return out


def geocode_v2(q, country, city_region=None, live=True, lock_timeout=None, feature=None):
    """Geocode `q` inside `country` (a DB country string). Returns the cached response fields plus
    cache_key, level and radius_km, or None when there is genuinely no in-country result.

    - countrycodes from ISO (unknown country raises UnknownCountry), limit=3, addressdetails=1; the
      first result whose address.country_code matches wins, so a higher-ranked foreign hit cannot.
    - null is cached only for a real answer with nothing usable (empty, or all hits foreign). HTTP
      errors / 429 / timeouts are retried with backoff and then raise GeocodeError: never cached.
    - live=False raises CacheMiss instead of calling out.
    - One live call at a time machine-wide (nominatim_gate); cache writes are atomic."""
    codes = iso_codes(country)
    key = cache_key(q, country, feature)
    cache = _load_cache()
    if key in cache:
        hit = cache[key]
        return None if hit is None else _derive(hit, key, city_region)
    if not live:
        raise CacheMiss(key)
    with nominatim_gate(lock_timeout) as gate:
        disk = load_json(CACHE_V2)                  # another process may have just fetched it
        if key in disk:
            _mem["sig"] = None
            hit = disk[key]
            return None if hit is None else _derive(hit, key, city_region)
        results = _query_live(gate, q, codes, feature)
        pick = _pick(results, codes)
        entry = _slim(pick) if pick else None
        disk[key] = entry
        atomic_write_json(CACHE_V2, disk, ensure_ascii=False)
        _mem["sig"] = None
    return None if entry is None else _derive(entry, key, city_region)
