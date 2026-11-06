"""Cached, rate-limited bulk fetcher for the Microburbs rent task.

Wraps any client with `.get(path, **params) -> data|None` (by default the
python-quickstart `Microburbs` client, which already retries 429/5xx and unwraps
the {"data": ...} envelope) and adds:

- a shared rate limiter (default 8 req/s; the API allows about 10);
- a SQLite response cache, so a crashed or restarted run resumes for free
  (cached `None` answers count too: "no data" is a normal, stable reply);
- paging over the suburb bulk endpoints (`limit` up to 1000 + `offset`);
- a leakage guard: nothing dated after CUTOFF (31 Jul 2026) is ever returned.

CLI (needs MICROBURBS_API_KEY; outputs go to rents/data/, which is gitignored):

    python rents/fetcher.py adverts                  # past adverts, all 29 suburbs
    python rents/fetcher.py properties               # every address, all suburbs
    python rents/fetcher.py flats ids.txt            # per-flat rent history (gap fill)
    python rents/fetcher.py adverts --suburbs "Glebe (NSW)" Pyrmont
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

CUTOFF = "2026-07-31"  # last allowed date for anything we use (task rule)

# Exact SAL names from the API docs (state suffixes matter).
SUBURBS = [
    "Alexandria", "Barangaroo", "Beaconsfield (NSW)", "Camperdown (NSW)",
    "Centennial Park (NSW)", "Chippendale", "Darlinghurst",
    "Darlington (Sydney - NSW)", "Dawes Point", "Elizabeth Bay", "Erskineville",
    "Eveleigh", "Forest Lodge", "Glebe (NSW)", "Haymarket", "Millers Point",
    "Moore Park", "Potts Point", "Pyrmont", "Redfern", "Rosebery (NSW)",
    "Rushcutters Bay", "Surry Hills", "Sydney", "The Rocks (Sydney - NSW)",
    "Ultimo", "Waterloo (NSW)", "Woolloomooloo", "Zetland",
]

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CACHE_PATH = ROOT / "cache" / "responses.sqlite"


class LeakageError(ValueError):
    """Raised when a request could return information dated after CUTOFF."""


class RateLimiter:
    """Thread-safe: spaces calls at least 1/rate seconds apart."""

    def __init__(self, rate: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.interval = 1.0 / rate
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + self.interval
            delay = start - now
        if delay > 0:
            self._sleep(delay)


class DiskCache:
    """key -> JSON value in SQLite. A stored `None` is a hit, not a miss."""

    _MISS = object()

    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("CREATE TABLE IF NOT EXISTS r (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
            self._db.commit()

    def get(self, key: str) -> Any:
        with self._lock:
            row = self._db.execute("SELECT v FROM r WHERE k = ?", (key,)).fetchone()
        return self._MISS if row is None else json.loads(row[0])

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO r (k, v) VALUES (?, ?)", (key, json.dumps(value)))
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()


def _check_not_after_cutoff(label: str, value: str | None) -> None:
    if value is None:
        raise LeakageError(f"{label} must be set (default would include dates after {CUTOFF})")
    if value > CUTOFF:  # ISO dates compare correctly as strings
        raise LeakageError(f"{label}={value} is after the cutoff {CUTOFF}")


class Fetcher:
    def __init__(self, client: Any, cache: DiskCache | None = None, rate: float = 8.0,
                 limiter: RateLimiter | None = None):
        self.client = client
        self.cache = cache if cache is not None else DiskCache(CACHE_PATH)
        self.limiter = limiter or RateLimiter(rate)
        self.stats = {"api_calls": 0, "cache_hits": 0, "dropped_after_cutoff": 0}

    # -- single cached call -------------------------------------------------
    def get(self, path: str, **params: Any) -> Any:
        key = json.dumps([path, sorted(params.items())], default=str)
        hit = self.cache.get(key)
        if hit is not DiskCache._MISS:
            self.stats["cache_hits"] += 1
            return hit
        self.limiter.wait()
        value = self.client.get(path, **params)
        self.stats["api_calls"] += 1
        self.cache.put(key, value)
        return value

    # -- paging -------------------------------------------------------------
    def paged(self, path: str, limit: int = 1000, **params: Any) -> Iterator[dict]:
        """Yield every row of a `{results, meta}` endpoint, page by page."""
        offset = 0
        while True:
            data = self.get(path, limit=limit, offset=offset, **params)
            if not data:  # None (no data) or empty
                return
            rows = data.get("results") or []
            yield from rows
            total = (data.get("meta") or {}).get("total")
            offset += len(rows)
            if not rows or (total is not None and offset >= total):
                return

    # -- task-specific bulk calls ------------------------------------------
    def rent_adverts(self, suburb: str, from_date: str | None = None,
                     to_date: str | None = CUTOFF) -> list[dict]:
        """Past rent adverts for a suburb, dated <= to_date (never after CUTOFF)."""
        _check_not_after_cutoff("to_date", to_date)
        params: dict[str, Any] = {"to_date": to_date}
        if from_date:
            params["from_date"] = from_date
        out = []
        for row in self.paged(f"/v1/suburbs/{suburb}/listings/rent-history", **params):
            d = row.get("listing_date")
            if d is None or d > CUTOFF:  # defence in depth: server filter should prevent this
                self.stats["dropped_after_cutoff"] += 1
                continue
            out.append(row)
        return out

    def properties(self, suburb: str) -> list[dict]:
        """Every address in the suburb (beds, baths, car spaces, floor, building size)."""
        return list(self.paged(f"/v1/suburbs/{suburb}/properties"))

    def flat_rent_history(self, gnaf_id: str) -> list[dict]:
        """One flat's For Rent records dated <= CUTOFF. `[]` when the API has none."""
        data = self.get(f"/v1/properties/{gnaf_id}/rent-history")
        out = []
        for rec in data or []:
            d = rec.get("date")
            if d is None or d > CUTOFF:
                self.stats["dropped_after_cutoff"] += 1
                continue
            out.append(rec)
        return out

    def flat_rent_histories(self, gnaf_ids: Iterable[str], workers: int = 8,
                            progress: Callable[[int], None] | None = None) -> dict[str, list[dict]]:
        ids = list(dict.fromkeys(gnaf_ids))  # de-dupe, keep order
        result: dict[str, list[dict]] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, (gid, recs) in enumerate(zip(ids, pool.map(self.flat_rent_history, ids)), 1):
                result[gid] = recs
                if progress and i % 500 == 0:
                    progress(i)
        return result


# -- output ---------------------------------------------------------------
def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def make_client() -> Any:
    """The python-quickstart client (reads MICROBURBS_API_KEY / MICROBURBS_API_BASE)."""
    sys.path.insert(0, str(ROOT.parent / "python-quickstart"))
    from microburbs_client import Microburbs  # noqa: PLC0415

    try:  # pick up .env if python-dotenv is installed; plain env vars work too
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(ROOT.parent / ".env")
    except ImportError:
        pass
    return Microburbs()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["adverts", "properties", "flats"])
    ap.add_argument("ids_file", nargs="?", help="flats: file with one gnaf_id per line")
    ap.add_argument("--suburbs", nargs="+", default=SUBURBS)
    ap.add_argument("--from-date", default=None)
    ap.add_argument("--rate", type=float, default=8.0)
    args = ap.parse_args(argv)

    fx = Fetcher(make_client(), rate=args.rate)
    if args.what == "flats":
        if not args.ids_file:
            ap.error("flats needs an ids file")
        ids = [l.strip() for l in Path(args.ids_file).read_text().splitlines() if l.strip()]
        res = fx.flat_rent_histories(ids, progress=lambda n: print(f"  {n}/{len(ids)} flats", flush=True))
        n = write_jsonl(DATA_DIR / "flat_rent_history.jsonl",
                        ({"gnaf_id": g, "records": r} for g, r in res.items()))
        print(f"flat_rent_history.jsonl: {n} flats")
    else:
        for sub in args.suburbs:
            rows = (fx.rent_adverts(sub, from_date=args.from_date) if args.what == "adverts"
                    else fx.properties(sub))
            n = write_jsonl(DATA_DIR / f"{args.what}_{slug(sub)}.jsonl", rows)
            print(f"{sub}: {n} rows", flush=True)
    print("stats:", fx.stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
