"""The demo supermarket: Dukaan Radar Mart, Dadar West, Mumbai. 50 starting items.

Each item: name, Hindi name, category, unit, quantity in stock, reorder level (the normal weekly
stock), cost and selling price in rupees, the Google search term people use for it, and the
Wikipedia article its picture comes from (Wikimedia Commons, freely licensed).
"""

STORE = dict(
    name="Dukaan Radar Mart",
    area="Dadar West, Mumbai",
    address="Near Dadar station, Dadar West, Mumbai, Maharashtra 400028",
    lat=19.0186, lng=72.8424,
    state="IN-MH", location="Mumbai,Maharashtra,India",
)

# name, hindi, category, unit, qty, reorder, cost, price, search term, wikipedia title
ITEMS = [
    ("Basmati rice", "बासमती चावल", "Staples", "5 kg bag", 25, 25, 520, 640, "basmati rice", "Basmati"),
    ("Wheat atta", "गेहूँ का आटा", "Staples", "10 kg bag", 30, 30, 390, 465, "atta", "Atta flour"),
    ("Toor dal", "तूर दाल", "Staples", "1 kg", 40, 40, 145, 175, "toor dal", "Pigeon pea"),
    ("Moong dal", "मूंग दाल", "Staples", "1 kg", 25, 25, 120, 148, "moong dal", "Mung bean"),
    ("Besan", "बेसन", "Staples", "1 kg", 20, 20, 85, 110, "besan", "Gram flour"),
    ("Sugar", "चीनी", "Staples", "1 kg", 50, 50, 42, 50, "sugar price", "Sugar"),
    ("Salt", "नमक", "Staples", "1 kg", 52, 30, 20, 28, "tata salt", "Salt"),
    ("Poha", "पोहा", "Staples", "1 kg", 20, 20, 55, 70, "poha", "Flattened rice"),
    ("Rava (sooji)", "रवा (सूजी)", "Staples", "1 kg", 20, 20, 45, 60, "rava", "Semolina"),
    ("Jaggery", "गुड़", "Staples", "1 kg", 15, 15, 55, 72, "jaggery", "Jaggery"),
    ("Sunflower oil", "सूरजमुखी तेल", "Oils & ghee", "1 L", 35, 35, 135, 160, "sunflower oil", "Cooking oil"),
    ("Mustard oil", "सरसों का तेल", "Oils & ghee", "1 L", 15, 15, 150, 180, "mustard oil", "Mustard oil"),
    ("Groundnut oil", "मूंगफली का तेल", "Oils & ghee", "1 L", 20, 20, 170, 205, "groundnut oil", "Peanut oil"),
    ("Ghee", "घी", "Oils & ghee", "1 L", 5, 15, 560, 650, "ghee", "Clarified butter"),
    ("Milk", "दूध", "Dairy & bakery", "500 ml", 80, 80, 28, 33, "milk", "Milk"),
    ("Paneer", "पनीर", "Dairy & bakery", "200 g", 6, 20, 75, 95, "paneer", "Paneer"),
    ("Curd", "दही", "Dairy & bakery", "400 g", 25, 25, 40, 50, "curd", "Dahi (curd)"),
    ("Butter", "मक्खन", "Dairy & bakery", "100 g", 25, 25, 52, 60, "butter", "Butter"),
    ("Bread", "ब्रेड", "Dairy & bakery", "loaf", 30, 30, 35, 45, "bread", "Bread"),
    ("Eggs", "अंडे", "Dairy & bakery", "tray of 12", 6, 20, 72, 90, "eggs", "Egg as food"),
    ("Onion", "प्याज़", "Fruits & veg", "1 kg", 50, 50, 32, 45, "onion price", "Onion"),
    ("Potato", "आलू", "Fruits & veg", "1 kg", 50, 50, 24, 35, "potato", "Potato"),
    ("Tomato", "टमाटर", "Fruits & veg", "1 kg", 35, 35, 30, 45, "tomato price", "Tomato"),
    ("Banana", "केला", "Fruits & veg", "dozen", 25, 25, 45, 60, "banana", "Banana"),
    ("Apple", "सेब", "Fruits & veg", "1 kg", 15, 15, 140, 180, "apple fruit", "Apple"),
    ("Lemon", "नींबू", "Fruits & veg", "250 g", 20, 20, 25, 40, "lemon", "Lemon"),
    ("Green chilli", "हरी मिर्च", "Fruits & veg", "250 g", 15, 15, 15, 25, "green chilli", "Chili pepper"),
    ("Coriander", "धनिया", "Fruits & veg", "bunch", 25, 25, 8, 15, "coriander", "Coriander"),
    ("Namkeen", "नमकीन", "Snacks & sweets", "400 g", 30, 30, 75, 95, "namkeen", "Namkeen"),
    ("Chakli", "चकली", "Snacks & sweets", "250 g", 15, 15, 60, 80, "chakli", "Chakli"),
    ("Soan papdi", "सोन पापड़ी", "Snacks & sweets", "500 g box", 15, 15, 110, 140, "soan papdi", "Soan papdi"),
    ("Kaju katli", "काजू कतली", "Snacks & sweets", "500 g box", 3, 10, 420, 520, "kaju katli", "Kaju katli"),
    ("Biscuits", "बिस्कुट", "Snacks & sweets", "family pack", 40, 40, 35, 45, "biscuits", "Biscuit"),
    ("Chocolate gift box", "चॉकलेट गिफ्ट बॉक्स", "Snacks & sweets", "box", 10, 10, 260, 330, "chocolate gift box", "Chocolate"),
    ("Almonds", "बादाम", "Snacks & sweets", "500 g", 15, 15, 380, 460, "dry fruits", "Almond"),
    ("Tea", "चाय पत्ती", "Beverages", "250 g", 30, 30, 120, 150, "tea", "Tea"),
    ("Coffee", "कॉफ़ी", "Beverages", "100 g", 26, 15, 180, 220, "coffee", "Coffee"),
    ("Cold drink", "कोल्ड ड्रिंक", "Beverages", "2 L", 45, 25, 80, 95, "cold drink", "Soft drink"),
    ("Packaged water", "पैकेज्ड पानी", "Beverages", "1 L", 95, 60, 15, 20, "water bottle", "Bottled water"),
    ("Detergent powder", "डिटर्जेंट पाउडर", "Household", "1 kg", 20, 20, 95, 120, "detergent", "Laundry detergent"),
    ("Dishwash bar", "बर्तन साबुन", "Household", "bar", 30, 30, 18, 25, "dishwash bar", "Dishwashing"),
    ("Agarbatti", "अगरबत्ती", "Household", "pack", 25, 25, 35, 50, "agarbatti", "Incense"),
    ("Floor cleaner", "फ़र्श क्लीनर", "Household", "1 L", 15, 15, 95, 120, "floor cleaner", "Cleaning agent"),
    ("LED bulb", "LED बल्ब", "Household", "9 W", 20, 20, 60, 90, "led bulb", "LED lamp"),
    ("Diyas", "दीये", "Festive & pooja", "pack of 12", 14, 20, 60, 99, "diya", "Diya (lamp)"),
    ("Rangoli colours", "रंगोली के रंग", "Festive & pooja", "set of 10", 9, 15, 80, 120, "rangoli", "Rangoli"),
    ("Akash kandil", "आकाश कंदील", "Festive & pooja", "lantern", 5, 10, 250, 399, "akash kandil", "Lantern"),
    ("Pooja thali", "पूजा थाली", "Festive & pooja", "set", 5, 8, 220, 320, "pooja thali", "Aarti"),
    ("Diwali lights", "दिवाली लाइट", "Festive & pooja", "10 m string", 10, 15, 110, 180, "diwali lights", "Holiday lighting technology"),
    ("Gift hamper", "गिफ्ट हैम्पर", "Festive & pooja", "hamper", 4, 8, 650, 899, "gift hamper", "Gift basket"),
]
assert len(ITEMS) == 50
