"""Build one stock-plan report for a city and shop type.

Searches per fresh report (cached afterwards; the cache lifetime is set per kind of data):
  Google Trends, this season, 2 calls (5 products each)          12 h
  Google Trends, last season around the festival, 2 calls        30 days (history does not change)
  Google Trends, interest by state for the top pick, 1 call      24 h
  Google Trends, rising searches for the shop's seed term, 1    24 h
  Google Trends Trending Now (India), 1 call                     6 h, shared by every shop
  Google Shopping in the shop's city, top 4 picks               24 h
  Google News, top picks, 1 call                                12 h
"""
import math
from datetime import date, timedelta

from . import serp, signals
from .config import ANCHOR, CITIES, FESTIVALS, SHOP_TYPES, SPANS, festival_near, next_festival

TOP_PICKS = 4
HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def hi_date(d):
    return f"{d.day} {HI_MONTHS[d.month - 1]}"


def _chunks(xs, n=5):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def _score(m, replay, recent):
    """Higher = order now. Last season's remaining growth matters most; current momentum confirms it."""
    if m is None and replay is None:
        return None
    s = 0.0
    if replay:
        s += math.log(max(replay["growth"], 0.2))
    if m:
        s += 0.5 * math.log(max(m, 0.2))
    if (recent or 0) < 2 and (replay or {}).get("peak", 0) < 10:
        s -= 1.0  # too little search volume to trust
    return round(s, 3)


def _action(p, fest, today):
    """Pick an action and phrase it in English and Hindi."""
    r, m = p["replay"], p["momentum"]
    name, hi = p["name"], p["hi"]
    days_left = (fest[0] - today).days
    until_peak = days_left - r["peak_days_before"] if r else None
    if r and r["growth"] >= 1.5:
        peak_day = fest[0] - timedelta(days=r["peak_days_before"])
        g = f"{r['growth']:.0f}" if r["growth"] >= 10 else f"{r['growth']:.1f}"
        other = festival_near(peak_day, exclude=ANCHOR)
        if r["peak_days_before"] <= 0:
            when_en, when_hi = f"on {ANCHOR} itself", f"{fest[2]} के दिन"
        elif other and other[0] in SPANS:
            when_en, when_hi = f"during {other[0]}", f"{other[1]} के दौरान"
        elif other:
            when_en, when_hi = f"around {other[0]}", f"{other[1]} के आसपास"
        else:
            when_en, when_hi = f"{r['peak_days_before']} days before {ANCHOR}", f"{fest[2]} से {r['peak_days_before']} दिन पहले"
        if until_peak > 7:
            kind = "stock_now"
            en = (f"Order {name.lower()} now. Last season, searches grew {g}× from this point and peaked {when_en} "
                  f"(this year about {peak_day.day} {peak_day:%b}, {until_peak} days away).")
            hn = (f"{hi} अभी मंगाएँ। पिछले साल इस समय से खोज {g} गुना बढ़ी और {when_hi} सबसे ज़्यादा थी "
                  f"(इस साल लगभग {hi_date(peak_day)}, {until_peak} दिन बाद)।")
        else:
            kind = "last_call"
            en = (f"Peak is close: last season {name.lower()} searches peaked {when_en}, about {max(until_peak, 0)} days from now. "
                  f"Top up fast sellers only; do not over-order.")
            hn = (f"मांग का चरम पास है: पिछले साल खोज {when_hi} सबसे ज़्यादा थी, यानी लगभग {max(until_peak, 0)} दिन में। "
                  f"तेज़ बिकने वाला माल ही भरें, ज़्यादा ऑर्डर न दें।")
    elif m and m >= 1.3 and (not r or r["growth"] < 1.5):
        kind = "at_peak"
        en = f"{name} demand is already high (searches up {m:.1f}× in a month). Keep stock on the shelf; avoid a big new order."
        hn = f"{hi} की मांग पहले से ऊँची है (एक महीने में खोज {m:.1f} गुना)। स्टॉक रखें, पर बड़ा नया ऑर्डर न दें।"
    elif m is not None and m < 0.75 and (not r or r["growth"] < 1.0):
        kind = "cooling"
        en = f"{name} searches are falling ({m:.1f}× of a month ago). Clear remaining stock with a bundle offer."
        hn = f"{hi} की खोज घट रही है। बचा हुआ माल कॉम्बो ऑफ़र से निकालें।"
    else:
        kind = "watch"
        en = f"No strong signal for {name.lower()} yet. Check again in a few days."
        hn = f"{hi} के लिए अभी कोई साफ़ संकेत नहीं। कुछ दिन बाद फिर देखें।"
    return kind, en, hn


def _price_line(price):
    if not price:
        return None, None
    rupee = [b for b in price["bands"] if "₹" in (b["band"] or "")]
    band = max(rupee, key=lambda b: b["listings"])["band"] if rupee else None
    en = f"Online median ₹{price['median']:,} (middle half ₹{price['p25']:,}–₹{price['p75']:,}, {price['listings']} listings from {price['sellers']} sellers)."
    hn = f"ऑनलाइन औसत दाम ₹{price['median']:,} ({price['listings']} लिस्टिंग, {price['sellers']} विक्रेता)।"
    if band:
        en += f" Google groups the most listings in {band}."
    return en, hn


def build(city="pune", shop="gifts", today=None, allow_live=None, listener=None):
    """listener(event) hears every search start/finish (the Research Room animates from it)."""
    today = today or date.today()
    tally = serp.Tally(listener)
    cname, geo, location = CITIES[city]
    st = SHOP_TYPES[shop]
    products = st["products"]
    fest = next_festival(today)
    anchor_now, anchor_ly, anchor_hi = FESTIVALS[ANCHOR]
    days_to_anchor = (anchor_now - today).days
    errors = []

    def S(params, ttl):
        try:
            return serp.search(params, ttl_hours=ttl, tally=tally, allow_live=allow_live)
        except Exception as e:  # keep building with what we have
            errors.append(str(e))
            return {}

    # 1. this season and last season, per state, 5 terms per Trends call
    terms = [p[0] for p in products]
    now_series, ly_series = {}, {}
    start = anchor_ly - timedelta(days=max(days_to_anchor, 0) + 21)
    end = anchor_ly + timedelta(days=3)
    for chunk in _chunks(terms):
        q = ",".join(chunk)
        now_series.update(signals.timeseries(S(dict(engine="google_trends", q=q, geo=geo, date="today 3-m", data_type="TIMESERIES"), 12)))
        if days_to_anchor >= 0:
            ly_series.update(signals.timeseries(S(dict(engine="google_trends", q=q, geo=geo, date=f"{start:%Y-%m-%d} {end:%Y-%m-%d}", data_type="TIMESERIES"), 24 * 30)))

    rows = []
    for term, name, hi in products:
        m, recent, base = signals.momentum(now_series.get(term, []))
        replay = signals.season_replay(ly_series.get(term, []), anchor_ly, days_to_anchor) if term in ly_series else None
        series = [v for _, v, _ in now_series.get(term, [])][-63:]
        rows.append(dict(term=term, name=name, hi=hi, momentum=m, recent=recent, base=base, replay=replay,
                         score=_score(m, replay, recent), spark=series))
    scored = sorted([r for r in rows if r["score"] is not None], key=lambda r: -r["score"])
    picks = scored[:TOP_PICKS]
    pick_terms = {p["term"] for p in picks}
    cooling = [r for r in scored if r["term"] not in pick_terms and r["momentum"] is not None and r["momentum"] < 0.75][:3]

    # 2. evidence for the picks: prices in the city, news
    news = S(dict(engine="google_news", q=" OR ".join(f'"{p["term"]}"' for p in picks) + " price", gl="in", hl="en"), 12) if picks else {}
    flags = signals.news_flags(news, [p["term"] for p in picks], today)
    for p in picks:
        shop_data = S(dict(engine="google_shopping", q=p["term"], location=location, gl="in", hl="en"), 24)
        p["price"] = signals.price_summary(shop_data)
        p["price_en"], p["price_hi"] = _price_line(p["price"])
        p["news"] = flags.get(p["term"], [])[:2]
        p["action"], p["action_en"], p["action_hi"] = _action(p, (anchor_now, ANCHOR, anchor_hi), today)
        p["sources"] = ["Google Trends · " + geo, "Google Trends · last season"] + (["Google Shopping · " + cname] if p["price"] else []) + (["Google News"] if p["news"] else [])
    for c in cooling:
        c["action"], c["action_en"], c["action_hi"] = _action(c, (anchor_now, ANCHOR, anchor_hi), today)

    # 3. context: where the top pick is hottest, rising searches, trending today
    states = signals.region_ranking(S(dict(engine="google_trends", q=picks[0]["term"], geo="IN", region="REGION", date="today 1-m", data_type="GEO_MAP_0"), 24)) if picks else []
    rising = signals.rising_queries(S(dict(engine="google_trends", q=st["seed"], geo=geo, date="today 1-m", data_type="RELATED_QUERIES"), 24))
    trending = signals.trending_for_shop(S(dict(engine="google_trends_trending_now", geo="IN", hours="24"), 6), terms)

    return dict(
        city=cname, city_key=city, state=geo, shop=shop, shop_label=st["label"], shop_hi=st["hi"], date=today.isoformat(),
        festival=dict(name=fest[1], hi=fest[2], date=fest[0].isoformat(), days=(fest[0] - today).days) if fest else None,
        anchor=dict(name=ANCHOR, hi=anchor_hi, date=anchor_now.isoformat(), days=days_to_anchor, last_year=anchor_ly.isoformat(),
                    label_en=f"{anchor_now.day} {anchor_now:%b}", label_hi=hi_date(anchor_now)),
        picks=picks, cooling=cooling, all=rows, states=states, top_term=picks[0]["name"] if picks else None,
        rising=rising, trending=trending, budget=tally.as_dict(), errors=errors,
    )
