"""Shop types, cities and the festival calendar.

Product search terms are what people actually type into Google in India; Hindi names are shown to
shop owners. Festival dates: verified against published 2026 calendars on 2026-10-11 (Diwali sources
disagree slightly; the UI says "verify"). Each festival has last year's date so Dukaan Radar can
replay last season's search curve.
"""
from datetime import date

SHOP_TYPES = {
    "gifts": {
        "label": "Gifts & pooja items", "hi": "गिफ्ट और पूजा सामग्री", "seed": "diwali gift",
        "products": [
            ("diya", "Diyas", "दीये"), ("rangoli", "Rangoli supplies", "रंगोली सामग्री"),
            ("toran", "Torans", "तोरण"), ("pooja thali", "Pooja thalis", "पूजा थाली"),
            ("diwali lights", "Diwali lights", "दिवाली लाइट"), ("dry fruits", "Dry fruits", "सूखे मेवे"),
            ("gift hamper", "Gift hampers", "गिफ्ट हैम्पर"), ("dandiya", "Dandiya sticks", "डांडिया"),
            ("akash kandil", "Lanterns (kandil)", "आकाश कंदील"), ("lakshmi ganesh idol", "Lakshmi-Ganesh idols", "लक्ष्मी-गणेश मूर्ति"),
        ],
    },
    "apparel": {
        "label": "Apparel", "hi": "कपड़े", "seed": "diwali dress",
        "products": [
            ("kurta", "Kurtas", "कुर्ते"), ("saree", "Sarees", "साड़ियाँ"), ("lehenga", "Lehengas", "लहंगे"),
            ("sherwani", "Sherwanis", "शेरवानी"), ("chaniya choli", "Chaniya cholis", "चनिया चोली"),
            ("kurti", "Kurtis", "कुर्तियाँ"), ("silk saree", "Silk sarees", "सिल्क साड़ी"),
            ("nehru jacket", "Nehru jackets", "नेहरू जैकेट"), ("kids ethnic wear", "Kids' ethnic wear", "बच्चों के पारंपरिक कपड़े"),
            ("dhoti kurta", "Dhoti-kurta sets", "धोती-कुर्ता"),
        ],
    },
    "electronics": {
        "label": "Electronics & appliances", "hi": "इलेक्ट्रॉनिक्स", "seed": "diwali offer",
        "products": [
            ("air fryer", "Air fryers", "एयर फ्रायर"), ("smart watch", "Smart watches", "स्मार्ट वॉच"),
            ("earbuds", "Earbuds", "ईयरबड्स"), ("led bulb", "LED bulbs", "LED बल्ब"),
            ("mixer grinder", "Mixer grinders", "मिक्सर ग्राइंडर"), ("room heater", "Room heaters", "रूम हीटर"),
            ("bluetooth speaker", "Bluetooth speakers", "ब्लूटूथ स्पीकर"), ("power bank", "Power banks", "पावर बैंक"),
            ("induction cooktop", "Induction cooktops", "इंडक्शन चूल्हा"), ("geyser", "Geysers", "गीज़र"),
        ],
    },
    "sweets": {
        "label": "Sweets & kirana", "hi": "मिठाई और किराना", "seed": "diwali sweets",
        "products": [
            ("kaju katli", "Kaju katli", "काजू कतली"), ("soan papdi", "Soan papdi", "सोन पापड़ी"),
            ("ghee", "Ghee", "घी"), ("besan", "Besan", "बेसन"), ("dry fruits", "Dry fruits", "सूखे मेवे"),
            ("chocolate gift box", "Chocolate gift boxes", "चॉकलेट गिफ्ट बॉक्स"), ("namkeen", "Namkeen", "नमकीन"),
            ("chakli", "Chakli", "चकली"), ("mithai box", "Mithai boxes", "मिठाई का डिब्बा"), ("gulab jamun", "Gulab jamun", "गुलाब जामुन"),
        ],
    },
}

# name, Trends state code, SerpApi location (canonical names from the free Locations API)
CITIES = {
    "pune": ("Pune", "IN-MH", "Pune,Maharashtra,India"),
    "mumbai": ("Mumbai", "IN-MH", "Mumbai,Maharashtra,India"),
    "ahmedabad": ("Ahmedabad", "IN-GJ", "Ahmedabad,Gujarat,India"),
    "delhi": ("Delhi", "IN-DL", "Delhi,Delhi,India"),
    "lucknow": ("Lucknow", "IN-UP", "Lucknow,Uttar Pradesh,India"),
    "patna": ("Patna", "IN-BR", "Patna,Bihar,India"),
    "jaipur": ("Jaipur", "IN-RJ", "Jaipur,Rajasthan,India"),
    "bengaluru": ("Bengaluru", "IN-KA", "Bengaluru,Karnataka,India"),
    "hyderabad": ("Hyderabad", "IN-TG", "Hyderabad,Telangana,India"),
    "chennai": ("Chennai", "IN-TN", "Chennai,Tamil Nadu,India"),
    "kolkata": ("Kolkata", "IN-WB", "Kolkata,West Bengal,India"),
}

# festival -> (this season, last season, Hindi name)
FESTIVALS = {
    "Navratri": (date(2026, 10, 11), date(2025, 9, 22), "नवरात्रि"),
    "Dussehra": (date(2026, 10, 20), date(2025, 10, 2), "दशहरा"),
    "Dhanteras": (date(2026, 11, 6), date(2025, 10, 18), "धनतेरस"),
    "Diwali": (date(2026, 11, 8), date(2025, 10, 20), "दिवाली"),
    "Christmas": (date(2026, 12, 25), date(2025, 12, 25), "क्रिसमस"),
}
ANCHOR = "Diwali"  # the festival whose last-season curve drives the forecast

NEWS_RISK_WORDS = ("shortage", "price hike", "prices rise", "costlier", "expensive", "supply", "import", "duty", "ban",
                   "strike", "flood", "rain", "gst", "demand surge", "sold out", "crackdown", "fake", "adulterat")


# multi-day festivals: (start, end) this season
SPANS = {"Navratri": (date(2026, 10, 11), date(2026, 10, 19))}


def festival_near(day, exclude=None, within=3):
    """The festival this day falls in (multi-day span) or lands within `within` days of."""
    for name, (a, b) in SPANS.items():
        if name != exclude and a <= day <= b:
            return name, FESTIVALS[name][2]
    best = None
    for name, (d, _, hi) in FESTIVALS.items():
        gap = abs((d - day).days)
        if name != exclude and gap <= within and (best is None or gap < best[0]):
            best = (gap, name, hi)
    return (best[1], best[2]) if best else None


def next_festival(today):
    upcoming = [(d, name, hi) for name, (d, _, hi) in FESTIVALS.items() if d >= today]
    return min(upcoming) if upcoming else None
