"""Download one freely licensed picture per item from Wikipedia (Wikimedia Commons) and record
where it came from (dukaan/static/items/credits.json).   uv run python scripts/fetch_images.py"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dukaan.store_seed import ITEMS  # noqa: E402

OUT = ROOT / "dukaan" / "static" / "items"
UA = {"User-Agent": "DukaanRadar/0.2 (SerpApi India Hackathon demo; github.com/shivamKumarG11/dukaan-radar)"}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


credits = {}
with httpx.Client(headers=UA, timeout=30, follow_redirects=True) as c:
    for name, _, _, _, _, _, _, _, _, wiki in ITEMS:
        r = c.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(wiki.replace(' ', '_'))}")
        if r.status_code != 200 or "thumbnail" not in r.json():
            print("no image:", name, wiki, r.status_code)
            continue
        j = r.json()
        src = j["thumbnail"]["source"]
        src = re.sub(r"/(\d+)px-", "/400px-", src)  # a 400 px thumbnail is plenty for a card
        img = c.get(src)
        if img.status_code != 200:
            img = c.get(j["thumbnail"]["source"])
        ext = ".png" if src.lower().endswith(".png") else ".jpg"
        (OUT / f"{slug(name)}{ext}").write_bytes(img.content)
        credits[slug(name)] = dict(file=f"{slug(name)}{ext}", article=j.get("title"),
                                   page=j.get("content_urls", {}).get("desktop", {}).get("page"), image=src)
        print("ok", name, "->", f"{slug(name)}{ext}", len(img.content) // 1024, "KB")
        time.sleep(0.3)
(OUT / "credits.json").write_text(json.dumps(credits, indent=1, ensure_ascii=False))
print(len(credits), "images")
