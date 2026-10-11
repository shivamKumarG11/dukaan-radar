"""Snapshot the local search cache as the bundled demo data (no API key needed to run the demo).
    uv run python scripts/make_demo.py 2026-10-11"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
day = sys.argv[1]
src, dst = ROOT / "cache" / "serpapi.sqlite", ROOT / "demo" / "serpapi-demo.sqlite"
dst.parent.mkdir(exist_ok=True)
con = sqlite3.connect(src)
con.execute("PRAGMA wal_checkpoint(FULL)")
con.close()
shutil.copyfile(src, dst)
# scrub the API key from every stored row (SerpApi embeds it in pagination/link URLs)
sys.path.insert(0, str(ROOT))
from dukaan.serp import scrub  # noqa: E402
con = sqlite3.connect(dst)
rows = con.execute("SELECT key, params, response FROM searches").fetchall()
con.executemany("UPDATE searches SET params = ?, response = ? WHERE key = ?", [(scrub(p), scrub(r), k) for k, p, r in rows])
con.commit()
con.execute("VACUUM")
con.close()
(ROOT / "demo" / "demo.json").write_text(json.dumps({"day": day}))
n = sqlite3.connect(dst).execute("SELECT COUNT(*) FROM searches").fetchone()[0]
print(f"demo cache: {n} recorded searches, day {day}, {dst.stat().st_size // 1024} KB")
