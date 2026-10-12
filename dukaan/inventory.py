"""The supermarket's stock, in SQLite (data/store.sqlite, created from store_seed on first run).
Used by the web page and by the stock agent's tools."""
import os
import re
import sqlite3
import threading
from pathlib import Path

from .store_seed import ITEMS, STORE

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("DUKAAN_DATA") or ROOT / "data")  # tests point this at a temp folder
DB = DATA / "store.sqlite"
IMAGES = Path(__file__).resolve().parent / "static" / "items"
_lock = threading.Lock()
FIELDS = ("name", "hindi", "category", "unit", "qty", "reorder", "cost", "price", "term", "image")
CATEGORIES = ["Staples", "Oils & ghee", "Dairy & bakery", "Fruits & veg", "Snacks & sweets", "Beverages", "Household", "Festive & pooja"]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _image_for(name):
    for ext in (".jpg", ".png"):
        if (IMAGES / f"{slug(name)}{ext}").exists():
            return f"/static/items/{slug(name)}{ext}"
    return None


def _con():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT UNIQUE, hindi TEXT, category TEXT,
                   unit TEXT, qty INTEGER, reorder INTEGER, cost REAL, price REAL, term TEXT, image TEXT)""")
    return con


def reset():
    """Restore the 50 starting items."""
    with _lock:
        con = _con()
        con.execute("DELETE FROM items")
        con.executemany(f"INSERT INTO items ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
                        [(n, h, c, u, q, r, co, p, t, _image_for(n)) for n, h, c, u, q, r, co, p, t, _ in ITEMS])
        con.commit()
        con.close()


def ensure():
    with _lock:
        con = _con()
        n = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        con.close()
    if n == 0:
        reset()


def items():
    ensure()
    con = _con()
    rows = [dict(r) for r in con.execute("SELECT * FROM items ORDER BY id")]
    con.close()
    return rows


def find(name_or_id):
    """By id, exact name, or the closest name containing the words (for the agent)."""
    rows = items()
    if str(name_or_id).isdigit():
        return next((r for r in rows if r["id"] == int(name_or_id)), None)
    q = str(name_or_id).strip().lower()
    exact = [r for r in rows if r["name"].lower() == q or r["hindi"] == name_or_id]
    if exact:
        return exact[0]
    words = q.split()
    part = [r for r in rows if all(w in (r["name"] + " " + r["term"]).lower() for w in words)]
    return part[0] if part else None


def add(name, category, unit, qty, reorder=None, cost=0, price=0, term=None, hindi=""):
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    if find(name) and find(name)["name"].lower() == name.lower():
        raise ValueError(f"{name} is already in stock")
    with _lock:
        con = _con()
        cur = con.execute(f"INSERT INTO items ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
                          (name, hindi, category if category in CATEGORIES else "Staples", unit or "unit", int(qty),
                           int(reorder if reorder is not None else max(int(qty), 1)), float(cost), float(price),
                           (term or name).lower(), _image_for(name)))
        con.commit()
        new_id = cur.lastrowid
        con.close()
    return find(new_id)


def update(item_id, **changes):
    allowed = {k: v for k, v in changes.items() if k in ("name", "hindi", "category", "unit", "qty", "reorder", "cost", "price", "term") and v is not None}
    if "qty" in allowed:
        allowed["qty"] = max(0, int(allowed["qty"]))
    if not allowed:
        return find(item_id)
    with _lock:
        con = _con()
        con.execute(f"UPDATE items SET {', '.join(f'{k} = ?' for k in allowed)} WHERE id = ?", (*allowed.values(), int(item_id)))
        con.commit()
        con.close()
    return find(item_id)


def remove(item_id):
    with _lock:
        con = _con()
        con.execute("DELETE FROM items WHERE id = ?", (int(item_id),))
        con.commit()
        con.close()


def is_low(r):
    """At half of the normal stock or below."""
    return r["qty"] <= 0.5 * r["reorder"]


def summary():
    rows = items()
    return dict(store=STORE, count=len(rows), value=round(sum(r["qty"] * r["cost"] for r in rows)),
                low=[r["name"] for r in rows if is_low(r)], categories=CATEGORIES)
