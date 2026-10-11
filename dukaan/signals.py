"""Turn raw SerpApi responses into signals. Pure functions: no network, easy to test."""
import re
import statistics
from datetime import date, datetime, timedelta, timezone

from .config import NEWS_RISK_WORDS


# ---------- Google Trends ----------
def timeseries(data):
    """interest_over_time -> {query: [(date, value, partial)]}"""
    out = {}
    for pt in data.get("interest_over_time", {}).get("timeline_data", []):
        d = datetime.fromtimestamp(int(pt["timestamp"]), tz=timezone.utc).date()
        for v in pt.get("values", []):
            out.setdefault(v["query"], []).append((d, int(v.get("extracted_value") or 0), bool(pt.get("partial_data"))))
    return out


def momentum(series):
    """Last 7 complete days vs the same span four to eight weeks earlier (+1 smoothing)."""
    full = [v for _, v, partial in series if not partial]
    if len(full) < 56:
        return None, None, None
    recent = statistics.mean(full[-7:])
    base = statistics.mean(full[-56:-28])
    return round((recent + 1) / (base + 1), 2), round(recent, 1), round(base, 1)


def season_replay(series, festival_last_year, days_to_go):
    """Replay last season: at the same number of days before the festival, how much did search
    interest still grow, and how many days before the festival did it peak?"""
    pts = {d: v for d, v, _ in series}
    same = festival_last_year - timedelta(days=days_to_go)
    near = [pts[d] for d in pts if abs((d - same).days) <= 3]
    window = [(d, v) for d, v in pts.items() if same <= d <= festival_last_year + timedelta(days=1)]
    if not near or not window:
        return None
    now_ly = statistics.mean(near)
    peak_d, peak_v = max(window, key=lambda x: (x[1], -x[0].toordinal()))
    return dict(growth=round((peak_v + 1) / (now_ly + 1), 2), then=round(now_ly, 1), peak=peak_v,
                peak_days_before=(festival_last_year - peak_d).days)


def region_ranking(data, top=8):
    rows = []
    for r in data.get("interest_by_region", []) or []:
        v = r.get("extracted_value")
        if v is None:
            v = int(re.sub(r"\D", "", str(r.get("value", "0"))) or 0)
        rows.append(dict(state=r.get("location"), geo=r.get("geo"), value=int(v)))
    rows.sort(key=lambda x: -x["value"])
    return rows[:top]


def rising_queries(data, top=8):
    rel = data.get("related_queries", {})
    return [dict(query=x["query"], growth=x.get("extracted_value"), label=x.get("value"))
            for x in rel.get("rising", [])[:top]]


def trending_for_shop(data, terms, top=5):
    """Trending searches in India today that touch this shop (by product word or shopping category)."""
    terms = [t.lower() for t in terms]
    shopping = {"Shopping"}
    hits = []
    for x in data.get("trending_searches", []):
        q = x.get("query", "")
        cats = {c["name"] for c in x.get("categories", [])}
        if any(t in q.lower() for t in terms) or cats & shopping:
            hits.append(dict(query=q, volume=x.get("search_volume"), increase=x.get("increase_percentage"),
                             category=", ".join(sorted(cats)) or "Other"))
    hits.sort(key=lambda h: -(h["volume"] or 0))
    return hits[:top]


# ---------- Google Shopping ----------
def price_summary(data):
    items = [x for x in data.get("shopping_results", []) if x.get("extracted_price")]
    if not items:
        return None
    prices = sorted(float(x["extracted_price"]) for x in items)
    q = statistics.quantiles(prices, n=4) if len(prices) >= 4 else [prices[0], statistics.median(prices), prices[-1]]
    bands = [dict(band=c.get("title"), listings=len(c.get("shopping_results", [])))
             for c in data.get("categorized_shopping_results", []) if c.get("title")]
    sellers = sorted({x.get("source", "?") for x in items})
    examples = [dict(title=x.get("title"), price=x.get("extracted_price"), seller=x.get("source"))
                for x in items[:3]]
    return dict(median=round(statistics.median(prices)), p25=round(q[0]), p75=round(q[-1]), listings=len(prices),
                sellers=len(sellers), seller_names=sellers[:6], bands=bands, examples=examples)


# ---------- Google News ----------
def news_flags(data, product_terms, today, max_age_days=45):
    """Recent headlines that name a product; risk words mark supply or price warnings."""
    out = {t: [] for t in product_terms}
    for n in data.get("news_results", []):
        title = n.get("title", "")
        iso = n.get("iso_date")
        try:
            d = datetime.fromisoformat(iso.replace("Z", "+00:00")).date() if iso else None
        except ValueError:
            d = None
        if d is None or (today - d).days > max_age_days:
            continue
        low = title.lower()
        for t in product_terms:
            if t.lower() in low:
                risk = [w for w in NEWS_RISK_WORDS if w in low]
                out[t].append(dict(title=title, date=d.isoformat(), link=n.get("link"),
                                   source=(n.get("source") or {}).get("name"), risk=risk))
    return out
