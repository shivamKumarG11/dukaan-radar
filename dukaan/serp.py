"""SerpApi client with a local SQLite cache.

The free plan has 250 searches a month, so every response is stored and reused: a search with the
same parameters is served from the cache until it is older than its time-to-live. Each report
counts how many searches were live and how many came from the cache, and shows it to the user.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DEMO_CACHE = ROOT / "demo" / "serpapi-demo.sqlite"
# Demo mode: no API key (or DUKAAN_DEMO=1) -> replay recorded searches, never call the API.
DEMO = os.environ.get("DUKAAN_DEMO") == "1" or (not os.environ.get("SERPAPI_API_KEY") and DEMO_CACHE.exists())
CACHE_PATH = Path(os.environ.get("DUKAAN_CACHE") or (DEMO_CACHE if DEMO else ROOT / "cache" / "serpapi.sqlite"))
_lock = threading.Lock()


class BudgetError(RuntimeError):
    """Raised instead of spending a search when live calls are switched off."""


def _db():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS searches (key TEXT PRIMARY KEY, params TEXT, response TEXT, fetched REAL)")
    return con


def scrub(text):
    """Remove the API key from text before it is stored. SerpApi puts it inside the pagination
    and link URLs of every response, and the cache is what the bundled demo data is made from."""
    key = os.environ.get("SERPAPI_API_KEY")
    return text.replace(key, "REDACTED") if key else text


def cache_key(params):
    clean = {k: v for k, v in sorted(params.items()) if k != "api_key"}
    return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()


def worker_for(params):
    """Which Research Room worker runs this search."""
    engine = params.get("engine", "")
    if engine in ("google_shopping", "google_maps"):
        return "price"
    if engine == "google_news":
        return "news"
    if engine == "google_trends" and params.get("data_type") == "TIMESERIES" and not str(params.get("date", "")).startswith("today"):
        return "historian"
    return "scout"


class Tally:
    """Counts live and cached searches for one report; `listener` hears each one start and finish."""

    def __init__(self, listener=None):
        self.live = 0
        self.cached = 0
        self.log = []
        self.listener = listener

    def emit(self, phase, label, **extra):
        if self.listener:
            self.listener(dict(type="search", phase=phase, worker=label.get("worker"), label=label, **extra))

    def record(self, label, source, age_h=None):
        if source == "live":
            self.live += 1
        else:
            self.cached += 1
        entry = dict(label, source=source)
        if age_h is not None:
            entry["age_h"] = age_h
        self.log.append(entry)
        self.emit("done", label, source=source)

    def as_dict(self):
        return dict(live=self.live, cached=self.cached, searches=self.log)


def search(params, ttl_hours=12, tally=None, allow_live=None):
    """Run a SerpApi search, or return the cached response if it is fresh enough.

    allow_live: None = live calls allowed when a key is present; False = cache only (demo/offline).
    """
    params = {k: v for k, v in params.items() if v is not None}
    key = cache_key(params)
    label = {k: params[k] for k in ("engine", "q", "geo", "data_type", "location", "date") if k in params}
    label["worker"] = worker_for(params)
    if tally:
        tally.emit("start", label)
    with _lock:
        con = _db()
        row = con.execute("SELECT response, fetched FROM searches WHERE key = ?", (key,)).fetchone()
        con.close()
    if row and (time.time() - row[1]) < ttl_hours * 3600:
        if tally:
            tally.record(label, "cache", round((time.time() - row[1]) / 3600, 1))
        return json.loads(row[0])
    api_key = os.environ.get("SERPAPI_API_KEY")
    if allow_live is False or not api_key or DEMO or os.environ.get("DUKAAN_OFFLINE") == "1":
        if row:  # stale but better than nothing in offline mode
            if tally:
                tally.record(label, "cache (stale)", round((time.time() - row[1]) / 3600, 1))
            return json.loads(row[0])
        raise BudgetError(f"no cached result for {label} and live searches are off")
    import serpapi

    client = serpapi.Client(api_key=api_key)
    data = dict(client.search(params))
    if "error" in data and not data.get("search_metadata"):
        raise RuntimeError(f"SerpApi error for {label}: {data['error']}")
    with _lock:
        con = _db()
        con.execute("INSERT OR REPLACE INTO searches VALUES (?, ?, ?, ?)",
                    (key, scrub(json.dumps({k: v for k, v in params.items() if k != "api_key"})), scrub(json.dumps(data)), time.time()))
        con.commit()
        con.close()
    if tally:
        tally.record(label, "live")
    return data


def account():
    """Searches left this month (the Account API does not use a search credit)."""
    import httpx
    r = httpx.get("https://serpapi.com/account.json", params={"api_key": os.environ.get("SERPAPI_API_KEY", "")}, timeout=20)
    r.raise_for_status()
    j = r.json()
    return dict(plan=j.get("plan_name"), used=j.get("this_month_usage"), left=j.get("plan_searches_left"),
                total=j.get("searches_per_month"))
