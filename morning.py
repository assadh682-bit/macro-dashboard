import os, json, requests
from datetime import datetime
from zoneinfo import ZoneInfo

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
KEY = os.environ["GEMINI_API_KEY"].strip()
TG_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()
FORCE = os.environ.get("FORCE") == "true"
ASSETS = ["GC", "SIL", "NQ", "ES", "DXY", "US10Y", "VIX"]
AR = {"up": "صاعد", "down": "هابط", "neutral": "محايد"}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text[:4000]}, timeout=30)
    print("TELEGRAM:", r.status_code)


def fallback(items):
    score = {a: 0 for a in ASSETS}
    for n in items:
        for i in n.get("impacts", []):
            if i.get("asset") in score:
                d = 1 if i.get("direction") == "up" else -1 if i.get("direction") == "down" else 0
                score[i["asset"]] += d * i.get("strength", 0)
    lines = ["ملخص الصباح (بدون AI):", ""]
    for a in ASSETS:
        v = score[a]
        lines.append(a + ": " + (AR["up"] if v > 0 else AR["down"] if v < 0 else AR["neutral"]) + " (" + str(v) + ")")
    return "\n".join(lines)


def ask_gemini(items):
    brief = []
    for n in items:
        imp = ", ".join(i.get("asset", "") + " " + i.get("direction", "") for i in n.get("impacts", []))
        brief.append("- " + n.get("title", "") + " | " + n.get("summary", "") + " | " + imp)
    prompt = ("نتا محلل ماكرو. هادو آخر الأخبار المحللة:\n" + "\n".join(brief) +
              "\n\nكتب ملخص صباحي بالدارجة المغربية قبل افتتاح جلسة نيويورك، بهاد الترتيب:\n"
              "1) الجو العام فجملتين\n2) أهم 3 حوايج خاصك تعرفها\n"
              "3) نظرة سريعة على كل أصل من " + str(ASSETS) + " (اتجاه محتمل وسبب فسطر)\n"
              "ما تخترعش أخبار ما كاينينش فاللائحة، وما تعطيش أسعار. أقصى 1500 حرف. نص عادي بلا markdown.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]},
                      headers={"x-goog-api-key": KEY}, timeout=90)
    if not r.ok:
        print("GEMINI:", r.status_code, r.text[:200])
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def main():
    ny = datetime.now(ZoneInfo("America/New_York"))
    today = ny.strftime("%Y-%m-%d")
    if not FORCE:
        mins = ny.hour * 60 + ny.minute
        if ny.weekday() > 4 or not (7 * 60 + 10 <= mins <= 8 * 60):
            print("Not the right time, skipping")
            return
        if load("docs/morning.json", {}).get("date") == today:
            print("Already sent today")
            return
    items = load("docs/news.json", [])[:12]
    if not items:
        telegram("صباح الخير. ما كاين حتى خبر محلل دابا.")
        return
    try:
        text = ask_gemini(items)
    except Exception as err:
        print("AI error:", type(err).__name__)
        text = fallback(items)
    telegram("\u2615 ملخص الصباح قبل نيويورك\n\n" + text)
    os.makedirs("docs", exist_ok=True)
    with open("docs/morning.json", "w", encoding="utf-8") as f:
        json.dump({"date": today}, f)


if __name__ == "__main__":
    main()
