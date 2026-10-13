import os, json, hashlib, time, requests, feedparser
from datetime import datetime
from zoneinfo import ZoneInfo

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
KEY = os.environ["GEMINI_API_KEY"].strip()
TG_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()
MAX_PER_RUN = 8
ALERT_MIN_IMPORTANCE = 4
ALERT_MIN_CONFIDENCE = 50

FEEDS = [
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.fxstreet.com/rss/news",
    "http://feeds.marketwatch.com/marketwatch/topstories/",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
]
ASSETS = ["GC", "SIL", "NQ", "ES", "DXY", "US10Y", "VIX"]

KEYWORDS = [
    "fed", "federal reserve", "fomc", "powell", "inflation", "cpi", "pce", "ppi",
    "jobs", "payroll", "nfp", "unemployment", "gdp", "rate", "yield", "treasury",
    "dollar", "gold", "silver", "oil", "crude", "wti", "brent", "opec", "tariff",
    "sanction", "war", "iran", "israel", "russia", "ukraine", "china", "nasdaq",
    "s&p", "stocks", "wall street", "ecb", "boj", "bank of", "recession", "vix",
    "trump", "houthi", "middle east",
]

PROMPT = """نتا محلل ماكرو. هادو أخبار مرقمة:

__ITEMS__

لكل خبر رجع عنصر فـ JSON بهاد الشكل بالضبط:
{"items":[{"i":0,"relevant":true,"importance":3,"summary":"ملخص بالدارجة المغربية فـ 2-3 جمل مع سبب التأثير","confidence":70,"impacts":[{"asset":"GC","direction":"up","strength":2,"duration":"daily"}]}]}
importance من 1 لـ 5، confidence من 0 لـ 100، direction واحد من up/down/neutral، strength من 1 لـ 5، duration واحد من instant/daily/weekly.
asset خاصو يكون واحد من: __ASSETS__
relevant=false إلا الخبر ما عندو علاقة بهاد الأصول. ما تخمنش، وإلا ماكانش واضح نقص الثقة."""


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def now_ma():
    return datetime.now(ZoneInfo("Africa/Casablanca")).strftime("%H:%M")


def is_relevant(text):
    t = text.lower()
    return any(k in t for k in KEYWORDS)


def analyze_batch(batch):
    lines = []
    for idx, (uid, e, src) in enumerate(batch):
        lines.append("[" + str(idx) + "] العنوان: " + e.get("title", "") + "\nالملخص: " + e.get("summary", "")[:300])
    prompt = PROMPT.replace("__ITEMS__", "\n\n".join(lines)).replace("__ASSETS__", ", ".join(ASSETS))
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    r = requests.post(url, json=body, headers={"x-goog-api-key": KEY}, timeout=90)
    if not r.ok:
        print("GEMINI:", r.status_code, r.text[:200])
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    return data.get("items", []) if isinstance(data, dict) else data


def telegram(text):
    r = requests.post("https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text}, timeout=30)
    print("TELEGRAM:", r.status_code)


ARROW = {"up": "\u25b2", "down": "\u25bc", "neutral": "\u25cf"}


def should_alert(n):
    if n.get("importance", 0) < ALERT_MIN_IMPORTANCE:
        return False
    if n.get("confidence", 0) < ALERT_MIN_CONFIDENCE:
        return False
    return any(i.get("direction") != "neutral" for i in n.get("impacts", []))


def format_alert(n):
    lines = ["\U0001F514 " + n["title"], "", n["summary"], ""]
    for i in n["impacts"]:
        lines.append(ARROW.get(i.get("direction"), "\u25cf") + " " + str(i.get("asset")) + " | قوة " + str(i.get("strength")) + "/5 | " + str(i.get("duration")))
    lines += ["", "ثقة AI: " + str(n["confidence"]) + "% | المصدر: " + n["source"]]
    return "\n".join(lines)


def main():
    seen = set(load("seen.json", []))
    news = load("docs/news.json", [])
    fresh = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:10]:
            uid = hashlib.md5((e.get("link") or e.get("title", "")).encode()).hexdigest()
            if uid in seen:
                continue
            if is_relevant(e.get("title", "") + " " + e.get("summary", "")):
                fresh.append((uid, e, feed.feed.get("title", url)))
            else:
                seen.add(uid)
    batch = fresh[:MAX_PER_RUN]
    results = None
    ai_status = "idle"
    if batch:
        try:
            results = analyze_batch(batch)
            ai_status = "ok"
        except requests.HTTPError as err:
            code = err.response.status_code if err.response is not None else 0
            print("AI error:", code)
            ai_status = "quota" if code == 429 else "error"
            if code not in (429, 500, 503):
                for uid, e, src in batch:
                    seen.add(uid)
        except Exception as err:
            print("AI error:", type(err).__name__)
            ai_status = "error"
            for uid, e, src in batch:
                seen.add(uid)
    added = 0
    if results is not None:
        for uid, e, src in batch:
            seen.add(uid)
        for a in results:
            try:
                idx = int(a.get("i", -1))
            except Exception:
                continue
            if idx < 0 or idx >= len(batch) or not a.get("relevant"):
                continue
            uid, e, src = batch[idx]
            item = {"id": uid, "time": now_ma(), "title": e.get("title", ""),
                    "link": e.get("link", ""), "source": src, "relevant": True,
                    "importance": a.get("importance", 1), "summary": a.get("summary", ""),
                    "confidence": a.get("confidence", 0), "impacts": a.get("impacts", [])}
            news.insert(0, item)
            added += 1
            if should_alert(item):
                telegram(format_alert(item))
    save("docs/news.json", news[:40])
    save("seen.json", list(seen)[-2000:])
    save("docs/status.json", {
        "last_run": datetime.now(ZoneInfo("Africa/Casablanca")).isoformat(),
        "ai": ai_status,
        "fresh": len(fresh),
        "added": added,
    })


if __name__ == "__main__":
    main()
