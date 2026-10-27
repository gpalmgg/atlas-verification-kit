"""AC-1 tests for scripts/geo_core.py (atlas-coordinate-honesty, 2026-10-19).

Fixture responses only: geo_core._fetch is replaced, so nothing here touches the network. Every cache/lock
path is redirected into a temp dir; the real scripts/.geocode-cache*.json files are never written.
Run: python3 -m unittest scripts/tests/test_geo_core.py -v
"""
import hashlib, json, os, subprocess, sys, tempfile, textwrap, time, unittest, urllib.error
from unittest import mock

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SCRIPTS)
import geo_core as G  # noqa: E402

OLD_CACHE = os.path.join(SCRIPTS, ".geocode-cache.json")
DB = os.path.join(SCRIPTS, "..", "communities-database.json")


def rb(path):
    with open(path, "rb") as f:
        return f.read()


def rt(path):
    with open(path) as f:
        return f.read()


def sha(path):
    return hashlib.sha256(rb(path)).hexdigest()


def box(lat, lon, km):
    """boundingbox [s, n, w, e] strings whose corner distance from (lat, lon) is about `km`."""
    d = km / 111.0 / 1.4142
    return [str(lat - d), str(lat + d), str(lon - d), str(lon + d)]


def resp(rank, *, lat=40.0, lon=-100.0, km=3.0, addresstype="village", cc="us", state=None, name="Place",
         display=None, **extra):
    """A Nominatim `search` hit as the live API returns it (strings for lat/lon/boundingbox)."""
    addr = {"country_code": cc}
    if state:
        addr["state"] = state
    r = {"lat": str(lat), "lon": str(lon), "class": "place", "type": "village", "addresstype": addresstype,
         "place_rank": rank, "boundingbox": box(lat, lon, km), "display_name": display or f"{name}, {state or ''}",
         "address": addr}
    r.update(extra)
    return r


class TmpEnv(unittest.TestCase):
    """Redirect cache-v2 + lock into a temp dir and fake the network."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = os.path.join(self.tmp.name, "cache-v2.json")
        self.lock = os.path.join(self.tmp.name, ".nominatim.lock")
        for name, val in (("CACHE_V2", self.cache), ("LOCK_PATH", self.lock), ("MIN_INTERVAL", 0.0)):
            p = mock.patch.object(G, name, val)
            p.start()
            self.addCleanup(p.stop)
        G._mem.update(sig=None, data=None)
        p = mock.patch.object(G, "_sleep", lambda s: None)   # no real backoff/rate sleeps unless a test opts in
        p.start()
        self.addCleanup(p.stop)
        self.urls = []
        self.queue = []

    def fake(self, *items):
        """Queue fetch outcomes: a list (JSON body) or an Exception instance to raise."""
        self.queue = list(items)
        outer = self

        def _fetch(url):
            outer.urls.append(url)
            item = outer.queue.pop(0) if len(outer.queue) > 1 else outer.queue[0]
            if isinstance(item, Exception):
                raise item
            return item
        p = mock.patch.object(G, "_fetch", _fetch)
        p.start()
        self.addCleanup(p.stop)

    def disk(self):
        return json.loads(rt(self.cache)) if os.path.exists(self.cache) else {}


def http(code):
    return urllib.error.HTTPError("http://x", code, "err", {}, None)


class LevelOf(unittest.TestCase):
    def lvl(self, rank, **kw):
        return G.level_of(resp(rank, **kw))

    def test_rank_boundary_27_28(self):
        self.assertEqual(self.lvl(28, km=5), "address")
        self.assertEqual(self.lvl(27, km=5), "street")

    def test_rank_boundary_25_26(self):
        self.assertEqual(self.lvl(26), "street")
        self.assertEqual(self.lvl(25), "town")

    def test_rank_boundary_12_13(self):
        self.assertEqual(self.lvl(13), "town")
        self.assertEqual(self.lvl(12), "region")

    def test_rank_boundary_4_5(self):
        self.assertEqual(self.lvl(5), "region")
        self.assertEqual(self.lvl(4), "country")

    def test_hamlet_is_town_and_street_is_street(self):
        self.assertEqual(self.lvl(20, addresstype="hamlet"), "town")
        self.assertEqual(self.lvl(26, addresstype="road"), "street")

    def test_site_type_is_address_only_within_1km(self):
        self.assertEqual(self.lvl(26, addresstype="tourism", km=0.4), "address")
        self.assertEqual(self.lvl(26, addresstype="tourism", km=5), "street")
        self.assertEqual(self.lvl(18, addresstype="amenity", km=1.5), "town")

    def test_tourism_rank10_30km_box_is_region(self):
        self.assertEqual(self.lvl(10, addresstype="tourism", km=30), "region")

    def test_missing_place_rank_raises(self):
        r = resp(20)
        del r["place_rank"]
        with self.assertRaises(ValueError):
            G.level_of(r)
        r["place_rank"] = None
        with self.assertRaises(ValueError):
            G.level_of(r)

    def test_state_mismatch_caps_at_region_shikha(self):
        # Shikha Ecovillage: city_region 'Binika, Odisha'; the wrong-state hit is still a rank-20 hamlet
        wrong = resp(20, cc="in", state="Uttar Pradesh", display="Binika, Kanpur, Uttar Pradesh, India")
        right = resp(20, cc="in", state="Odisha", display="Binika, Subarnapur, Odisha, India")
        self.assertEqual(G.level_of(wrong, "Binika, Odisha"), "region")
        self.assertEqual(G.level_of(right, "Binika, Odisha"), "town")
        self.assertEqual(G.level_of(wrong), "town")                     # no city_region -> no claim
        self.assertEqual(G.level_of(wrong, "Binika"), "town")           # one segment names no state

    def test_state_mismatch_caps_address_too(self):
        wrong = resp(30, cc="us", state="Maryland", display="1 Main St, Maryland, United States")
        self.assertEqual(G.level_of(wrong, "Mesa, Colorado"), "region")

    def test_state_match_via_county_in_display_name(self):
        r = resp(20, cc="gb", state="Scotland", display="Findhorn, Moray, Scotland, United Kingdom")
        self.assertEqual(G.level_of(r, "Findhorn, Moray"), "town")


class Candidates(unittest.TestCase):
    def test_odisha_postcode_rung_dropped(self):
        for place in ("767062, Odisha", "Odisha 767062", "Binika, 767062, Odisha"):
            qs = G.candidates(place, "India", "")
            self.assertTrue(qs, place)
            for q, _ in qs:
                first = q.split(",")[0].strip()
                self.assertFalse(first.isdigit(), (place, q))
        self.assertEqual(G.candidates("767062, Odisha", "India"), [("Odisha, India", 1), ("India", 2)])

    def test_garbage_first_segments(self):
        qs = [q for q, _ in G.candidates("X, NY, Springfield, Illinois", "United States")]
        self.assertEqual(qs, ["Springfield, Illinois, United States", "Illinois, United States", "United States"])
        self.assertEqual([q for q, _ in G.candidates("AB, 12345, Lyon", "France")], ["Lyon, France", "France"])

    def test_three_letter_names_survive(self):
        self.assertEqual(G.candidates("Ayr", "United Kingdom")[0], ("Ayr, United Kingdom", 0))

    def test_rung_is_index_in_unfiltered_ladder(self):
        self.assertEqual([r for _, r in G.candidates("Binika, Odisha", "India")], [0, 1, 2])
        self.assertEqual(G.candidates("", "France"), [("France", 0)])

    def test_stage3_name_guess(self):
        self.assertEqual(G.candidates(None, None, "GEN Belgium"), [("Belgium", 0)])


class Countries(unittest.TestCase):
    def test_czechia_and_czech_republic_alias(self):
        self.assertEqual(G.iso_codes("Czechia"), ("cz",))
        self.assertEqual(G.iso_codes("Czech Republic"), ("cz",))
        self.assertEqual(G.bbox_for("Czechia"), G.bbox_for("Czech Republic"))
        self.assertIsNotNone(G.bbox_for("Czechia"))
        self.assertTrue(G.in_country(50.08, 14.43, "Czechia"))        # Prague
        self.assertFalse(G.in_country(52.5, 13.4, "Czechia"))         # Berlin

    def test_canary_islands_are_spain(self):
        self.assertEqual(G.iso_codes("Canary Islands"), ("es",))
        self.assertTrue(G.in_country(28.1, -15.4, "Spain"))           # Las Palmas, outside the mainland box
        self.assertTrue(G.in_country(28.1, -15.4, "Canary Islands"))
        self.assertFalse(G.in_country(28.1, -15.4, "Portugal"))

    def test_scotland_and_uk(self):
        self.assertEqual(G.iso_codes("Scotland"), ("gb",))
        self.assertEqual(G.bbox_for("Scotland"), G.BBOX["Scotland, UK"])
        self.assertTrue(G.in_country(55.95, -3.19, "United Kingdom"))

    def test_html_entities_and_codes(self):
        self.assertEqual(G.iso_codes("Wales &amp; Borders"), ("gb",))
        self.assertEqual(G.iso_codes("England: London &amp; SE"), ("gb",))
        self.assertEqual(G.iso_codes("PS"), ("ps",))
        self.assertEqual(G.iso_codes(None), ())
        self.assertEqual(G.iso_codes("International"), ())

    def test_unknown_country_raises(self):
        with self.assertRaises(G.UnknownCountry):
            G.iso_codes("Atlantis")
        with self.assertRaises(G.UnknownCountry):
            G.geocode_v2("Paradise, Atlantis", "Atlantis", live=False)

    @unittest.skipUnless(os.path.exists(DB), "DB not present")
    def test_every_country_on_a_mappable_row_resolves(self):
        entries = json.loads(rt(DB))["entries"]
        missing = set()
        n = 0
        for r in entries:
            if (r.get("lat") is not None and r.get("lon") is not None) or r.get("geo_status") == "pinned":
                n += 1
                try:
                    G.iso_codes(r.get("country"))
                except G.UnknownCountry:
                    missing.add(r.get("country"))
        self.assertGreater(n, 10000)
        self.assertEqual(missing, set())

    def test_every_bbox_country_has_iso(self):
        for name in G.BBOX:
            self.assertTrue(G.iso_codes(name), name)


class GeocodeV2(TmpEnv):
    def test_request_params_and_user_agent(self):
        self.fake([resp(20, cc="us", state="Colorado")])
        out = G.geocode_v2("Mesa, Colorado, United States", "United States")
        q = self.urls[0]
        for frag in ("addressdetails=1", "limit=3", "countrycodes=us", "format=json"):
            self.assertIn(frag, q)
        self.assertEqual(out["level"], "town")
        self.assertIn("editor@heartofecovillages.org", G.UA)

    def test_cache_record_has_all_fields(self):
        self.fake([resp(20, cc="us", state="Colorado")])
        out = G.geocode_v2("Mesa, United States", "United States")
        rec = self.disk()[out["cache_key"]]
        for k in ("lat", "lon", "class", "type", "addresstype", "place_rank", "boundingbox", "display_name", "address"):
            self.assertIn(k, rec)
        self.assertIsInstance(rec["lat"], float)
        self.assertEqual(rec["place_rank"], 20)
        self.assertGreaterEqual(out["radius_km"], G.MIN_RADIUS_KM)

    def test_second_call_is_a_cache_hit(self):
        self.fake([resp(20)])
        G.geocode_v2("A, United States", "United States")
        G.geocode_v2("A, United States", "United States")
        self.assertEqual(len(self.urls), 1)
        with self.assertRaises(G.CacheMiss):
            G.geocode_v2("B, United States", "United States", live=False)

    def test_maryland_netherlands_rejected_for_us_row(self):
        nl = resp(16, cc="nl", state="Limburg", display="Maryland, Limburg, Netherlands")
        self.fake([nl])
        self.assertIsNone(G.geocode_v2("Maryland, Netherlands", "United States"))
        self.assertIn("countrycodes=us", self.urls[0])

    def test_limit3_in_country_result_beats_higher_ranked_foreign(self):
        foreign = resp(16, cc="de", display="Springfield, Germany")
        home = resp(14, cc="us", state="Illinois", display="Springfield, Illinois, United States")
        self.fake([foreign, home])
        out = G.geocode_v2("Springfield", "United States")
        self.assertIn("limit=3", self.urls[0])
        self.assertEqual(out["address"]["country_code"], "us")
        self.assertIn("Illinois", out["display_name"])

    def test_empty_result_is_cached_as_null(self):
        self.fake([])
        self.assertIsNone(G.geocode_v2("Nowhere, France", "France"))
        self.assertIsNone(G.geocode_v2("Nowhere, France", "France"))
        self.assertEqual(len(self.urls), 1)
        self.assertEqual(list(self.disk().values()), [None])

    def test_429_is_not_cached(self):
        self.fake(http(429))
        with self.assertRaises(G.GeocodeError):
            G.geocode_v2("Mesa, United States", "United States")
        self.assertEqual(len(self.urls), G.RETRIES)             # retried with backoff
        self.assertEqual(self.disk(), {})
        self.assertFalse(any(v is None for v in self.disk().values()))

    def test_5xx_and_network_errors_are_not_cached(self):
        for exc in (http(503), urllib.error.URLError("down"), TimeoutError("slow")):
            self.fake(exc)
            with self.assertRaises(G.GeocodeError):
                G.geocode_v2("Q, United States", "United States")
        self.assertEqual(self.disk(), {})

    def test_429_then_success_caches_the_success(self):
        self.fake(http(429), http(429), [resp(20)])
        out = G.geocode_v2("Mesa, United States", "United States")
        self.assertEqual(out["level"], "town")
        self.assertEqual(len(self.urls), 3)
        self.assertIsNotNone(self.disk()[out["cache_key"]])

    def test_non_list_body_is_an_error_not_a_null(self):
        self.fake({"error": "rate limited"})
        with self.assertRaises(G.GeocodeError):
            G.geocode_v2("Q, France", "France")
        self.assertEqual(self.disk(), {})

    def test_level_uses_city_region_but_cache_does_not(self):
        self.fake([resp(20, cc="in", state="Uttar Pradesh", display="Binika, Uttar Pradesh, India")])
        a = G.geocode_v2("Binika, India", "India", city_region="Binika, Odisha")
        b = G.geocode_v2("Binika, India", "India")
        self.assertEqual((a["level"], b["level"]), ("region", "town"))
        self.assertEqual(len(self.urls), 1)


class CacheSafety(TmpEnv):
    def test_interrupted_write_leaves_old_cache_readable(self):
        self.fake([resp(20)])
        G.geocode_v2("First, United States", "United States")
        before = rb(self.cache)
        # (a) crash while the temp file is being written

        def half_dump(obj, f, **kw):
            f.write('{"half": ')
            raise KeyboardInterrupt
        with mock.patch.object(G.json, "dump", half_dump):
            with self.assertRaises(KeyboardInterrupt):
                G.atomic_write_json(self.cache, {"new": 1})
        self.assertEqual(rb(self.cache), before)
        # (b) crash at the rename
        with mock.patch.object(G.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                G.atomic_write_json(self.cache, {"new": 2})
        self.assertEqual(rb(self.cache), before)
        self.assertEqual(len(json.loads(rt(self.cache))), 1)
        self.assertEqual([f for f in os.listdir(self.tmp.name) if f.endswith(".tmp")], [])   # no stray temp files
        # (c) and geocode_v2 itself survives a failed write: old cache intact, query not recorded
        self.fake([resp(20)])
        with mock.patch.object(G.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                G.geocode_v2("Second, United States", "United States")
        self.assertEqual(rb(self.cache), before)

    def test_corrupt_cache_raises_instead_of_being_overwritten(self):
        with open(self.cache, "w") as f:
            f.write('{"truncated": ')
        with self.assertRaises(ValueError):
            G.geocode_v2("Q, France", "France", live=False)
        self.fake([resp(20, cc="fr")])
        with self.assertRaises(ValueError):
            G.geocode_v2("Q, France", "France")
        self.assertEqual(rt(self.cache), '{"truncated": ')

    def test_old_cache_is_byte_identical(self):
        self.assertNotEqual(os.path.abspath(G.CACHE_V2), OLD_CACHE)
        before = sha(OLD_CACHE) if os.path.exists(OLD_CACHE) else None
        self.fake([resp(20), []])
        G.geocode_v2("A, United States", "United States")
        G.geocode_v2("B, United States", "United States")
        self.assertEqual(sha(OLD_CACHE) if os.path.exists(OLD_CACHE) else None, before)

    def test_default_cache_path_is_v2_file(self):
        src = rt(os.path.join(SCRIPTS, "geo_core.py"))
        self.assertIn('".geocode-cache-v2.json"', src)
        self.assertNotIn('".geocode-cache.json"', src)

    def test_atomic_write_roundtrip(self):
        G.atomic_write_json(self.cache, {"ä": [1, 2]}, ensure_ascii=False)
        self.assertEqual(G.load_json(self.cache), {"ä": [1, 2]})


class LockAcrossProcesses(TmpEnv):
    HOLDER = textwrap.dedent("""
        import fcntl, sys, time
        f = open(sys.argv[1], "a+")
        fcntl.flock(f, fcntl.LOCK_EX)
        print("locked", flush=True)
        time.sleep(float(sys.argv[2]))
    """)

    def start_holder(self, secs):
        p = subprocess.Popen([sys.executable, "-I", "-c", self.HOLDER, self.lock, str(secs)],
                             stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.stdout.close)
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)
        self.assertEqual(p.stdout.readline().strip(), "locked")
        return p

    def test_second_process_holding_lock_blocks_live_call(self):
        self.fake([resp(20)])
        p = self.start_holder(1.5)
        t0 = time.time()
        with self.assertRaises(G.LockTimeout):
            G.geocode_v2("Q, United States", "United States", lock_timeout=0.3)
        self.assertEqual(self.urls, [])                          # nothing went out while locked
        out = G.geocode_v2("Q, United States", "United States")  # blocks until the holder exits
        self.assertGreaterEqual(time.time() - t0, 1.2)
        self.assertEqual(out["level"], "town")
        self.assertEqual(len(self.urls), 1)
        p.wait()

    def test_cache_hits_do_not_need_the_lock(self):
        self.fake([resp(20)])
        G.geocode_v2("Q, United States", "United States")
        self.start_holder(1.0)
        t0 = time.time()
        G.geocode_v2("Q, United States", "United States", lock_timeout=0.1)
        self.assertLess(time.time() - t0, 0.5)

    def test_min_interval_between_live_calls(self):
        stamps = []
        self.fake([resp(20)])
        real = G._fetch
        G._fetch = lambda url: (stamps.append(time.time()), real(url))[1]
        self.addCleanup(setattr, G, "_fetch", real)
        with mock.patch.object(G, "MIN_INTERVAL", 1.1), mock.patch.object(G, "_sleep", time.sleep):
            G.geocode_v2("A, United States", "United States")
            G.geocode_v2("B, United States", "United States")
        self.assertGreaterEqual(stamps[1] - stamps[0], 1.1)

    def _legacy_blocks(self, call):
        """A legacy script's live geocode must wait for a foreign lock holder before touching the network."""
        calls = []

        class Resp:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s, *a): return b"[]"

        def urlopen(req, timeout=0):
            calls.append(time.time())
            return Resp()
        p = self.start_holder(1.5)
        t0 = time.time()
        with mock.patch("urllib.request.urlopen", urlopen):
            call()
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(calls[0] - t0, 1.2)
        p.wait()

    def test_geocode_py_live_call_takes_the_lock(self):
        import geocode as legacy
        with mock.patch.dict(legacy.cache, clear=False):
            self._legacy_blocks(lambda: legacy.geocode("zz-lock-test-query"))
            legacy.cache.pop("zz-lock-test-query", None)

    def test_coord_qc_fix_live_call_takes_the_lock(self):
        import coord_qc_fix as qc
        with mock.patch.object(qc, "CACHE", os.path.join(self.tmp.name, "qc.json")), \
                mock.patch.dict(qc.cache, clear=False):
            self._legacy_blocks(lambda: qc.geocode("zz-lock-test-query"))
            qc.cache.pop("zz-lock-test-query", None)

    def test_module_default_interval_is_at_least_1_1s(self):
        src = rt(os.path.join(SCRIPTS, "geo_core.py"))
        self.assertIn("MIN_INTERVAL = 1.1", src)



class StreetQueryAndFeatureType(unittest.TestCase):
    def test_street_detection(self):
        for q in ("Kirkebakken 80, Denmark", "12 Mill Lane, Ayr, United Kingdom", "Hauptstraße 5, Germany"):
            self.assertTrue(G.is_street_query(q), q)
        for q in ("Global, Denmark", "Rural California, United States", "Тверской обл, Russia",
                  "Czechia, Czech Republic", "Odisha 767062, India", "Karmitz, Germany", "St. Gallen, Switzerland"):
            self.assertFalse(G.is_street_query(q), q)

    def test_feature_for(self):
        self.assertIsNone(G.feature_for("Kirkebakken 80, Denmark", "Denmark"))
        self.assertEqual(G.feature_for("Denmark", "Denmark"), "country")
        self.assertEqual(G.feature_for("Global, Denmark", "Denmark"), "settlement")

    def test_cache_key_includes_feature_only_when_given(self):
        self.assertEqual(G.cache_key("Karmitz, Germany", "Germany"), "Karmitz, Germany|de")
        self.assertEqual(G.cache_key("Karmitz, Germany", "Germany", "settlement"), "Karmitz, Germany|de|ft=settlement")


if __name__ == "__main__":
    unittest.main()
