"""One-off probe of the six engine calls Dukaan Radar needs; prints the response shapes."""
import json
from dukaan import serp

t = serp.Tally()
calls = {
    "ts": dict(engine="google_trends", q="diya,rangoli,dandiya,led lights,dry fruits", geo="IN-MH", date="today 3-m", data_type="TIMESERIES"),
    "geo": dict(engine="google_trends", q="diya,rangoli,dandiya,led lights,dry fruits", geo="IN", region="REGION", date="today 1-m", data_type="GEO_MAP"),
    "rel": dict(engine="google_trends", q="diwali gift", geo="IN", date="today 1-m", data_type="RELATED_QUERIES"),
    "now": dict(engine="google_trends_trending_now", geo="IN", hours="24"),
    "shop": dict(engine="google_shopping", q="clay diya", location="Pune, Maharashtra, India", gl="in", hl="en"),
    "news": dict(engine="google_news", q="diya prices shortage", gl="in", hl="en"),
}
out = {}
for name, p in calls.items():
    try:
        d = serp.search(p, ttl_hours=24 * 30, tally=t)
        out[name] = d
        print(f"== {name}: keys {list(d.keys())}")
    except Exception as e:
        print(f"!! {name}: {e}")
print(t.as_dict())
json.dump(out, open("scripts/probe_out.json", "w", encoding="utf-8"), ensure_ascii=False)
