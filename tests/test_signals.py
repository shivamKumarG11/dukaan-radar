from datetime import date, timedelta

from dukaan import signals
from dukaan.config import festival_near


def series(values, start=date(2026, 7, 1)):
    return [(start + timedelta(days=i), v, False) for i, v in enumerate(values)]


def test_momentum_compares_last_week_with_a_month_earlier():
    vals = [10] * 49 + [30] * 7          # 56 days: flat, then a 3x jump in the last week
    m, recent, base = signals.momentum(series(vals))
    assert recent == 30 and base == 10 and m == round(31 / 11, 2)
    assert signals.momentum(series([5] * 20)) == (None, None, None)  # too short to judge


def test_season_replay_finds_growth_left_and_peak_timing():
    diwali_ly = date(2025, 10, 20)
    pts = []
    for back in range(40, -4, -1):           # rises to 100 five days before the festival
        d = diwali_ly - timedelta(days=back)
        pts.append((d, 100 if back == 5 else (4 if back > 20 else 20), False))
    r = signals.season_replay(pts, diwali_ly, days_to_go=28)
    assert r["then"] == 4 and r["peak"] == 100 and r["peak_days_before"] == 5
    assert r["growth"] == round(101 / 5, 2)


def test_price_summary_uses_quartiles_and_google_bands():
    data = {"shopping_results": [{"extracted_price": p, "source": s} for p, s in
                                  [(100, "a"), (200, "b"), (300, "a"), (400, "c"), (1000, "d")]],
            "categorized_shopping_results": [{"title": "Under ₹250", "shopping_results": [1, 2]}]}
    s = signals.price_summary(data)
    assert s["median"] == 300 and s["listings"] == 5 and s["sellers"] == 4
    assert s["bands"] == [{"band": "Under ₹250", "listings": 2}]
    assert signals.price_summary({"shopping_results": []}) is None


def test_news_flags_keep_recent_headlines_naming_the_product():
    today = date(2026, 10, 11)
    data = {"news_results": [
        {"title": "Diya prices rise after clay shortage", "iso_date": "2026-10-05T07:00:00Z", "source": {"name": "X"}},
        {"title": "Diya makers struggle", "iso_date": "2025-10-11T07:00:00Z"},           # a year old
        {"title": "Cricket score", "iso_date": "2026-10-10T07:00:00Z"},                   # not about a product
    ]}
    f = signals.news_flags(data, ["diya", "rangoli"], today)
    assert [n["title"] for n in f["diya"]] == ["Diya prices rise after clay shortage"]
    assert "shortage" in f["diya"][0]["risk"] and f["rangoli"] == []


def test_trending_matches_whole_product_terms_only():
    data = {"trending_searches": [{"query": "indian idol", "categories": [{"name": "Entertainment"}]},
                                  {"query": "lakshmi ganesh idol price", "categories": []}]}
    hits = signals.trending_for_shop(data, ["lakshmi ganesh idol"])
    assert [h["query"] for h in hits] == ["lakshmi ganesh idol price"]


def test_festival_naming():
    assert festival_near(date(2026, 10, 16), exclude="Diwali")[0] == "Navratri"   # inside the span
    assert festival_near(date(2026, 11, 3), exclude="Diwali")[0] == "Dhanteras"   # 3 days before it
    assert festival_near(date(2026, 9, 1), exclude="Diwali") is None
