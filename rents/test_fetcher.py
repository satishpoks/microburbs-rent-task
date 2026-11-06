"""Tests for fetcher.py using a fake client: no network, no API key."""

import pytest

import fetcher
from fetcher import CUTOFF, DiskCache, Fetcher, LeakageError, RateLimiter


class FakeClient:
    """Serves canned data; records every call."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def get(self, path, **params):
        self.calls.append((path, params))
        return self.handler(path, params)


def advert(i, date="2026-05-01"):
    return {"gnaf_pid": f"G{i}", "weekly_rent": 500 + i, "listing_date": date,
            "bedrooms": 1, "bathrooms": 1, "car_spaces": 0, "leased": True}


def paged_handler(rows):
    def h(path, p):
        o, l = p["offset"], p["limit"]
        page = rows[o:o + l]
        return {"area_name": "X", "meta": {"limit": l, "offset": o, "returned": len(page),
                                           "total": len(rows)}, "results": page}
    return h


@pytest.fixture
def make():
    def _make(handler, **kw):
        fake = FakeClient(handler)
        kw.setdefault("limiter", RateLimiter(1000, sleep=lambda s: None))
        return Fetcher(fake, cache=DiskCache(":memory:"), **kw), fake
    return _make


def test_paging_collects_all_rows_across_pages(make):
    rows = [advert(i) for i in range(25)]
    fx, fake = make(paged_handler(rows))
    out = list(fx.paged("/v1/x", limit=10))
    assert [r["gnaf_pid"] for r in out] == [f"G{i}" for i in range(25)]
    assert [c[1]["offset"] for c in fake.calls] == [0, 10, 20]


def test_paging_stops_on_exact_multiple_without_extra_call(make):
    fx, fake = make(paged_handler([advert(i) for i in range(20)]))
    assert len(list(fx.paged("/v1/x", limit=10))) == 20
    assert len(fake.calls) == 2


def test_paging_handles_no_data_and_empty(make):
    fx, _ = make(lambda p, q: None)
    assert list(fx.paged("/v1/x")) == []
    fx2, _ = make(paged_handler([]))
    assert list(fx2.paged("/v1/x")) == []


def test_paging_stops_if_server_returns_empty_page_despite_total(make):
    fx, fake = make(lambda p, q: {"meta": {"total": 99}, "results": []})
    assert list(fx.paged("/v1/x")) == []
    assert len(fake.calls) == 1


def test_cache_prevents_repeat_calls_including_none(make):
    fx, fake = make(lambda p, q: None)
    assert fx.get("/v1/a", k=1) is None
    assert fx.get("/v1/a", k=1) is None
    assert len(fake.calls) == 1
    assert fx.stats == {"api_calls": 1, "cache_hits": 1, "dropped_after_cutoff": 0}
    fx.get("/v1/a", k=2)  # different params -> new call
    assert len(fake.calls) == 2


def test_cache_persists_across_fetchers(tmp_path):
    db = tmp_path / "c.sqlite"
    f1 = FakeClient(lambda p, q: {"v": 1})
    Fetcher(f1, cache=DiskCache(db), limiter=RateLimiter(1000, sleep=lambda s: None)).get("/v1/a")
    f2 = FakeClient(lambda p, q: pytest.fail("should have been cached"))
    assert Fetcher(f2, cache=DiskCache(db), limiter=RateLimiter(1000, sleep=lambda s: None)).get("/v1/a") == {"v": 1}


def test_rent_adverts_sends_cutoff_and_url_with_suburb_name(make):
    fx, fake = make(paged_handler([advert(1)]))
    fx.rent_adverts("Glebe (NSW)", from_date="2026-01-01")
    path, params = fake.calls[0]
    assert path == "/v1/suburbs/Glebe (NSW)/listings/rent-history"
    assert params["to_date"] == CUTOFF and params["from_date"] == "2026-01-01"
    assert params["limit"] == 1000


@pytest.mark.parametrize("bad", ["2026-08-01", "2026-10-28", None])
def test_rent_adverts_refuses_dates_after_cutoff(make, bad):
    fx, fake = make(paged_handler([]))
    with pytest.raises(LeakageError):
        fx.rent_adverts("Glebe (NSW)", to_date=bad)
    assert fake.calls == []


def test_rent_adverts_drops_rows_after_cutoff_or_undated(make):
    rows = [advert(1, "2026-07-31"), advert(2, "2026-08-01"), advert(3, "2026-10-28"),
            {**advert(4), "listing_date": None}]
    fx, _ = make(paged_handler(rows))
    out = fx.rent_adverts("Glebe (NSW)")
    assert [r["gnaf_pid"] for r in out] == ["G1"]
    assert fx.stats["dropped_after_cutoff"] == 3


def test_properties_pages_through_suburb(make):
    rows = [{"gnaf_pid": f"G{i}", "bedrooms": 2} for i in range(1500)]
    fx, fake = make(paged_handler(rows))
    assert len(fx.properties("Pyrmont")) == 1500
    assert [c[1]["offset"] for c in fake.calls] == [0, 1000]


def test_flat_rent_history_filters_dates_and_handles_none(make):
    recs = [{"date": "2025-07-24", "price": 750, "type": "For Rent"},
            {"date": "2026-09-01", "price": 900, "type": "For Rent"},
            {"price": 800, "type": "For Rent"},
            {"date": "2022-10-10", "type": "For Rent"}]  # no price is legitimate
    fx, _ = make(lambda p, q: recs)
    assert [r["date"] for r in fx.flat_rent_history("G1")] == ["2025-07-24", "2022-10-10"]
    assert fx.stats["dropped_after_cutoff"] == 2
    fx2, _ = make(lambda p, q: None)
    assert fx2.flat_rent_history("G2") == []


def test_flat_rent_histories_dedupes_and_runs_concurrently(make):
    fx, fake = make(lambda p, q: [{"date": "2025-01-01", "price": 1}])
    res = fx.flat_rent_histories(["A", "B", "A", "C"], workers=4)
    assert list(res) == ["A", "B", "C"]
    assert len(fake.calls) == 3


def test_rate_limiter_spaces_calls():
    now = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s

    rl = RateLimiter(10, clock=lambda: now[0], sleep=sleep)
    for _ in range(4):
        rl.wait()
    assert slept == pytest.approx([0.1, 0.1, 0.1])  # first call is free, then 10/s


def test_get_waits_on_limiter_only_for_real_calls(make):
    waits = []
    rl = RateLimiter(1000, sleep=lambda s: None)
    rl.wait = lambda: waits.append(1)
    fx, _ = make(lambda p, q: {"x": 1}, limiter=rl)
    fx.get("/a"), fx.get("/a"), fx.get("/b")
    assert len(waits) == 2


def test_client_error_is_not_cached(make):
    state = {"n": 0}

    def h(p, q):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    fx, _ = make(h)
    with pytest.raises(RuntimeError):
        fx.get("/a")
    assert fx.get("/a") == {"ok": True}


def test_slug_and_write_jsonl(tmp_path):
    assert fetcher.slug("The Rocks (Sydney - NSW)") == "the_rocks_sydney_nsw"
    p = tmp_path / "o" / "x.jsonl"
    assert fetcher.write_jsonl(p, [{"a": 1}, {"a": "é"}]) == 2
    assert p.read_text(encoding="utf-8").splitlines() == ['{"a": 1}', '{"a": "é"}']


def test_suburb_list_has_29_unique_names():
    assert len(fetcher.SUBURBS) == 29 == len(set(fetcher.SUBURBS))
