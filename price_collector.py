"""Collects news about prices of goods in Sylhet Division from public Google News RSS feeds.
No AI, no API key. Stores only headline, source, date and link (never article text) in price_news.json.
"""
import os, json, re, hashlib, datetime as dt
from urllib.parse import quote
try:
    import feedparser
except ImportError:  # lets the tagging functions be tested without the package
    feedparser = None

DISTRICTS = {"Sylhet": ["sylhet", "সিলেট"], "Moulvibazar": ["moulvibazar", "maulvibazar", "মৌলভীবাজার"],
             "Habiganj": ["habiganj", "হবিগঞ্জ"], "Sunamganj": ["sunamganj", "সুনামগঞ্জ"]}
# Well-known Sylhet bazars, used only as a tag when a headline names one.
MARKETS = {"Bandar Bazar": ["bandar bazar", "বন্দর বাজার", "বন্দরবাজার"], "Ambarkhana": ["ambarkhana", "amborkhana", "আম্বরখানা"],
           "Sobhanighat": ["sobhanighat", "shobhanighat", "শুভানীঘাট", "শোভানীঘাট"], "Kazir Bazar": ["kazir bazar", "কাজির বাজার", "কাজীর বাজার"],
           "Subid Bazar": ["subid bazar", "সুবিদবাজার", "সুবিদ বাজার"], "Madina Market": ["madina market", "মদিনা মার্কেট"],
           "Zindabazar": ["zindabazar", "জিন্দাবাজার"]}
COMMODITIES = {"Rice": ["rice", "চাল"], "Eggs": ["egg", "ডিম"], "Onion": ["onion", "পেঁয়াজ", "পেয়াজ"], "Potato": ["potato", "আলু"],
               "Edible oil": ["oil", "তেল", "সয়াবিন", "পাম"], "Lentils": ["lentil", "ডাল", "মসুর"], "Chicken": ["chicken", "broiler", "মুরগি", "মুরগী", "ব্রয়লার"],
               "Beef/Mutton": ["beef", "mutton", "গরুর মাংস", "খাসি", "খাসী"], "Fish": ["fish", "hilsa", "মাছ", "ইলিশ"], "Vegetables": ["vegetable", "সবজি", "শাক"],
               "Sugar": ["sugar", "চিনি"], "Spices": ["garlic", "ginger", "chilli", "রসুন", "আদা", "মরিচ", "মসলা"], "Flour": ["flour", "আটা", "ময়দা"],
               "Salt": ["salt", "লবণ"], "Fruits": ["fruit", "ফল", "আম", "কলা"]}
GENERAL = ["price", "prices", "market", "essential", "commodit", "bazar", "দাম", "দর", "বাজার", "নিত্যপণ্য", "দ্রব্যমূল্য", "পণ্য", "মূল্য", "কেজি"]
EXCLUDE = ["stock market", "share market", "dse", "cse", "শেয়ার", "পুঁজিবাজার", "ক্রিকেট", "cricket"]

def hits(text, words):
    t = text.lower()
    # English words must start at a word boundary ("rice" must not match "prices"); Bangla uses plain substring match
    return any((re.search(r"\b" + re.escape(w), t) if w.isascii() else w in t) for w in words)

def tag(title):
    """Return a dict of tags for a headline, or None if it is not relevant."""
    if hits(title, EXCLUDE):
        return None
    dist = [d for d, w in DISTRICTS.items() if hits(title, w)]
    mk = [m for m, w in MARKETS.items() if hits(title, w)]
    if mk and "Sylhet" not in dist:
        dist.append("Sylhet")
    com = [c for c, w in COMMODITIES.items() if hits(title, w)]
    if not dist or not (com or hits(title, GENERAL)):
        return None
    return {"dist": dist, "mk": mk, "com": com}

def queries():
    en_d, bn_d = list(DISTRICTS), [w[1] for w in DISTRICTS.values()]
    q = [f"{d} {t}" for d in en_d for t in ("prices", "market prices", "essentials price")]
    topics = ["বাজার দর", "দ্রব্যমূল্য", "নিত্যপণ্য", "চালের দাম", "ডিমের দাম", "পেঁয়াজের দাম", "সবজির দাম", "মাছের দাম", "মুরগির দাম", "তেলের দাম"]
    q += [f"{d} {t}" for d in bn_d for t in topics]
    q += [f"{m} দাম" for m in ("বন্দর বাজার", "আম্বরখানা", "শুভানীঘাট", "কাজির বাজার")]
    return q

def main():
    db_file = "price_news.json"
    db = json.load(open(db_file, encoding="utf-8")) if os.path.exists(db_file) else []
    seen = {r["id"] for r in db}
    seen_titles = {re.sub(r"\W+", "", r["t"].lower()) for r in db}
    added = checked = 0
    for q in queries():
        url = f"https://news.google.com/rss/search?q={quote(q)}+when:7d&hl=bn&gl=BD&ceid=BD:bn"
        for e in feedparser.parse(url).entries:
            rid = hashlib.sha1(e.link.encode()).hexdigest()[:12]
            title = e.title.rsplit(" - ", 1)[0].strip()
            key = re.sub(r"\W+", "", title.lower())
            if rid in seen or key in seen_titles:
                continue
            seen.add(rid); seen_titles.add(key); checked += 1
            tg = tag(title)
            if not tg:
                continue
            d = dt.date(*e.published_parsed[:3]).isoformat() if e.get("published_parsed") else dt.date.today().isoformat()
            db.append({"id": rid, "t": title, "src": e.get("source", {}).get("title", "News portal"), "d": d, "l": e.link, **tg})
            added += 1
    db = sorted(db, key=lambda r: r["d"], reverse=True)[:1500]
    json.dump(db, open(db_file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{checked} new headlines checked, {added} added, {len(db)} stored")

if __name__ == "__main__":
    main()
