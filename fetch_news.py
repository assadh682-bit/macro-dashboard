import os, json, hashlib, time, requests, feedparser

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KEY = os.environ["GEMINI_API_KEY"]
TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
MAX_PER_RUN = 6          # حد أقصى ديال الأخبار الجديدة فكل مرة (باش نبقاو فالمجاني)
ALERT_MIN_IMPORTANCE = 4 # التنبيه على Telegram غير للأخبار High impact

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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={KEY}"
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(title=title, summary=summary[:800], assets=ASSETS)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def telegram(text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": TG_CHAT, "text": text}, timeout=30)


ARROW = {"up": "▲", "down": "▼", "neutr
