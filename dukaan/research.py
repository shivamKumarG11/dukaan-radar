"""Demand research for the supermarket: the key festive-season items (FOCUS) are checked against live
search data; every other item gets the plain stock rule (restock when down to half of normal).

Searches for a fresh run, about 10 (cached afterwards):
  Google Trends, Maharashtra, this season      1 call per 5 focus items    12 h
  Google Trends, Maharashtra, last season      1 call per 5 focus items    30 days
  Google Shopping, Mumbai                      top movers (PRICE_CHECKS)   24 h
  Google News                                  1 call for the top movers   12 h
  Google Maps, supermarkets near the store     1 call                      7 days

Reorder rule, kept deliberately simple and explainable: an item's reorder level is its normal stock
for a week. Expected demand for the next weeks = normal x a demand factor taken from search data
(growth still ahead last season, else this month's momentum), halved towards 1 to stay cautious
and capped per category: a festival spike in "rangoli" searches is real extra demand, a spike in
"salt" searches is not people eating three times the salt. Order = what it takes to reach that target.
"""
import math
import threading
from datetime import date, timedelta

from . import inventory, serp, signals
from .config import ANCHOR, FESTIVALS, next_festival
from .report import TOP_PICKS, _action, _price_line, _score, hi_date
from .store_seed import STORE

PRICE_CHECKS = 4
# the items worth searching for in the run-up to Diwali: festive, sweets, a staple, a slow mover
RUNNING = threading.Lock()  # one research run at a time
GO = threading.Event()      # cleared = paused between searches
GO.set()
FOCUS = ["Diyas", "Rangoli colours", "Kaju katli", "Ghee", "Sugar", "Cold drink"]
# how far search signals may raise demand above normal, by category
CAPS = {"Staples": 1.3, "Oils & ghee": 1.3, "Dairy & bakery": 1.2, "Fruits & veg": 1.3, "Beverages": 1.3,
        "Household": 1.3, "Snacks & sweets": 2.5, "Festive & pooja": 3.0}
STOCK_LABELS = {
    "stock_up": ("Stock up", "स्टॉक बढ़ाएँ"), "restock": ("Restock", "फिर से भरें"),
    "slow": ("Slow down", "कम मंगाएँ"), "ok": ("OK", "ठीक है"),
}


def _demand_factor(m, replay, until_peak, weak, cap=3.0):
    if weak:
        return 1.0
    if replay and replay["growth"] >= 1.2 and until_peak is not None and until_peak > 0:
        raw = replay["growth"]
    elif m:
        raw = m
    else:
        return 1.0
    return round(min(cap, max(0.6, 1 + (raw - 1) * 0.5)), 2)


def build(today=None, allow_live=None, listener=None):
    today = today or date.today()
    tally = serp.Tally(listener)
    errors = []

    def S(params, ttl):
        GO.wait(timeout=600)  # paused from the Research Room (a forgotten pause ends after 10 min)
        try:
            return serp.search(params, ttl_hours=ttl, tally=tally, allow_live=allow_live)
        except Exception as e:
            errors.append(str(e))
            return {}

    rows = inventory.items()
    geo, location = STORE["state"], STORE["location"]
    anchor_now, anchor_ly, anchor_hi = FESTIVALS[ANCHOR]
    days_to_anchor = (anchor_now - today).days
    fest = next_festival(today)
    start = anchor_ly - timedelta(days=max(days_to_anchor, 0) + 21)
    end = anchor_ly + timedelta(days=3)

    focus = {r["id"] for r in rows if r["name"] in FOCUS}
    terms = list(dict.fromkeys(r["term"] for r in rows if r["id"] in focus))
    now_series, ly_series = {}, {}
    for i in range(0, len(terms), 5):
        q = ",".join(terms[i:i + 5])
        now_series.update(signals.timeseries(S(dict(engine="google_trends", q=q, geo=geo, date="today 3-m", data_type="TIMESERIES"), 12)))
        if days_to_anchor >= 0:
            ly_series.update(signals.timeseries(S(dict(engine="google_trends", q=q, geo=geo, date=f"{start:%Y-%m-%d} {end:%Y-%m-%d}", data_type="TIMESERIES"), 24 * 30)))

    recs = []
    for r in rows:
        m, recent, base = signals.momentum(now_series.get(r["term"], []))
        replay = signals.season_replay(ly_series.get(r["term"], []), anchor_ly, days_to_anchor) if r["term"] in ly_series else None
        researched = r["id"] in focus
        weak = researched and (recent or 0) < 2 and (replay or {}).get("peak", 0) < 10
        until_peak = days_to_anchor - replay["peak_days_before"] if replay else None
        f = _demand_factor(m, replay, until_peak, weak, CAPS.get(r["category"], 1.3))
        target = math.ceil(r["reorder"] * f)
        p = dict(id=r["id"], name=r["name"], hi=r["hindi"], term=r["term"], category=r["category"], unit=r["unit"],
                 qty=r["qty"], reorder=r["reorder"], price_ours=r["price"], image=r["image"],
                 researched=researched, momentum=m, recent=recent, replay=replay, score=_score(m, replay, recent), weak=weak, demand=f, target=target,
                 spark=[v for _, v, _ in now_series.get(r["term"], [])][-63:])
        p["action"], p["action_en"], p["action_hi"] = _action(p, (anchor_now, ANCHOR, anchor_hi), today)
        if f >= 1.25 and target > r["qty"]:
            p["stock"], p["order"] = "stock_up", target - r["qty"]
        elif inventory.is_low(r):
            p["stock"], p["order"] = "restock", r["reorder"] - r["qty"]
            p["action_en"] = f"Down to half of normal stock or less ({r['qty']} of {r['reorder']} {r['unit']}). Restock to the normal level."
            p["action_hi"] = f"सामान्य स्टॉक का आधा या कम ({r['qty']}/{r['reorder']})। सामान्य स्तर तक भरें।"
        elif f <= 0.8 and r["qty"] > r["reorder"]:
            p["stock"], p["order"] = "slow", 0
        else:
            p["stock"], p["order"] = "ok", 0
            if not researched:
                p["action_en"] = "Not in this research. Stock is above half of normal, so nothing to do."
                p["action_hi"] = "इस रिसर्च में नहीं। स्टॉक सामान्य के आधे से ज़्यादा है, कुछ करने की ज़रूरत नहीं।"
            elif weak:
                p["action_en"] = "Too few searches in Maharashtra to read demand. Keep the normal stock."
                p["action_hi"] = "महाराष्ट्र में खोजें बहुत कम हैं, मांग का अंदाज़ा नहीं। सामान्य स्टॉक रखें।"
            elif f >= 1.25:
                p["action_en"] = f"Demand is rising (about {f}x normal), and the stock you have already covers it."
                p["action_hi"] = f"मांग बढ़ रही है (सामान्य से करीब {f} गुना), पर मौजूदा स्टॉक काफ़ी है।"
            elif p["action"] in ("watch", "stock_now", "last_call"):
                p["action_en"] = "Demand looks steady. Keep the normal stock."
                p["action_hi"] = "मांग स्थिर है। सामान्य स्टॉक रखें।"
        p["stock_en"], p["stock_hi"] = STOCK_LABELS[p["stock"]]
        recs.append(p)

    movers = sorted([p for p in recs if p["stock"] == "stock_up"], key=lambda p: -(p["score"] or 0))
    picks = movers[:TOP_PICKS]

    # prices in Mumbai for the biggest movers, news for the picks, nearby supermarkets
    for p in movers[:PRICE_CHECKS]:
        p["price"] = signals.price_summary(S(dict(engine="google_shopping", q=p["term"], location=location, gl="in", hl="en"), 24))
        p["price_en"], p["price_hi"] = _price_line(p["price"])
    news = S(dict(engine="google_news", q=" OR ".join(f'"{p["term"]}"' for p in picks) + " price", gl="in", hl="en"), 12) if picks else {}
    flags = signals.news_flags(news, [p["term"] for p in picks], today)
    for p in recs:
        p.setdefault("price", None)
        p["news"] = flags.get(p["term"], [])[:2]
        p["sources"] = ["Google Trends · " + geo] + (["Google Trends · last season"] if p["replay"] else []) + \
                       (["Google Shopping · Mumbai"] if p["price"] else []) + (["Google News"] if p["news"] else [])
    maps = S(dict(engine="google_maps", q="supermarket", ll=f"@{STORE['lat']},{STORE['lng']},15z", type="search", hl="en"), 24 * 7)
    competitors = [dict(name=x.get("title"), rating=x.get("rating"), reviews=x.get("reviews"), address=x.get("address"),
                        type=x.get("type"), lat=(x.get("gps_coordinates") or {}).get("latitude"),
                        lng=(x.get("gps_coordinates") or {}).get("longitude"))
                   for x in maps.get("local_results", [])[:8]]

    return dict(
        store=STORE, date=today.isoformat(), city="Mumbai", city_key="mumbai", state=geo,
        shop="store", shop_label=STORE["name"], shop_hi="सुपरमार्केट",
        festival=dict(name=fest[1], hi=fest[2], date=fest[0].isoformat(), days=(fest[0] - today).days) if fest else None,
        anchor=dict(name=ANCHOR, hi=anchor_hi, date=anchor_now.isoformat(), days=days_to_anchor,
                    label_en=f"{anchor_now.day} {anchor_now:%b}", label_hi=hi_date(anchor_now)),
        recs=recs, picks=picks, competitors=competitors,
        totals=dict(stock_up=len(movers), restock=sum(p["stock"] == "restock" for p in recs),
                    slow=sum(p["stock"] == "slow" for p in recs), units=sum(p["order"] for p in recs),
                    spend=round(sum(p["order"] * next(r["cost"] for r in rows if r["id"] == p["id"]) for p in recs))),
        budget=tally.as_dict(), errors=errors,
    )
