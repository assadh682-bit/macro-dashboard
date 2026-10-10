import os, json, hashlib, time, requests, feedparser

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
KEY = os.environ["GEMINI_API_KEY"].strip()
TG_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()
MAX_PER_RUN = 6
ALERT_MIN_IMPORTANCE = 4

FEEDS = [
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.fxstreet.com/rss/news",
    "http://feeds.marketwatch.com/marketwatch/topstories/",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
]
ASSETS = ["GC", "SIL", "NQ", "ES", "DXY", "US10Y", "VIX"]

PROMPT = """نتا محلل ماكرو. هادا خبر:
العنوان: {title}
الملخص: {summary}

رجع JSON فقط بهاد الشكل:
{{"relevant": true/false,
 "importance": 1-5,
 "summary": "ملخص بالدارجة المغربية فـ 2-3 جمل مع سبب التأثير",
 "confidence": 0-100,
 "impacts": [{{"asset": "واحد من {assets}", "direction": "up|down|neutral", "strength": 1-5, "duration": "instant|daily|weekly"}}]}}
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


def analyze(title, summary):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(title=title, summary=summary[:800], assets=ASSETS)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    r = requests.post(url, json=body, headers={"x-goog-api-key": KEY}, timeout=60)
    if not r.ok:
        print("GEMINI:", r.text[:400])
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text}, timeout=30)
    print("TELEGRAM:", r.status_code, r.text[:200])


ARROW = {"up": "\u25b2", "down": "\u25bc", "neutral": "\u25cf"}


def format_alert(n):
    lines = ["\U0001F514 " + n["title"], "", n["summary"], ""]
    for i in n["impacts"]:
        lines.append(ARROW.get(i["direction"], "\u25cf") + " " + i["asset"] + " | قوة " + str(i["strength"]) + "/5 | " + i["duration"])
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
            if uid not in seen:
                fresh.append((uid, e, feed.feed.get("title", url)))
    for uid, e, src in fresh[:MAX_PER_RUN]:
        seen.add(uid)
        try:
            a = analyze(e.get("title", ""), e.get("summary", ""))
        except Exception as err:
            print("AI error:", err)
            continue
        time.sleep(5)
        if not a.get("relevant"):
            continue
        item = {"id": uid, "time": time.strftime("%H:%M", time.gmtime()), "title": e.get("title", ""),
                "link": e.get("link", ""), "source": src, **a}
        news.insert(0, item)
        if a.get("importance", 0) >= ALERT_MIN_IMPORTANCE:
            telegram(format_alert(item))
    save("docs/news.json", news[:40])
    save("seen.json", list(seen)[-2000:])


if __name__ == "__main__":
    telegram("TEST bot OK")
    main()
