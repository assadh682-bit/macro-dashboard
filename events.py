import json, os, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

TG_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()
FORCE = os.environ.get("FORCE") == "true"
WINDOW_MIN = 45


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def telegram(text):
    r = requests.post("https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text}, timeout=30)
    print("TELEGRAM:", r.status_code)


def ma_time(ts):
    return datetime.fromtimestamp(ts / 1000, ZoneInfo("Africa/Casablanca")).strftime("%H:%M")


def build(ts, items, mins, test):
    head = "\u23F0 " + ("(تجربة) " if test else "") + "حدث مهم بعد " + str(mins) + " دقيقة تقريبا"
    lines = [head, "التوقيت بالمغرب: " + ma_time(ts), ""]
    for e in items:
        line = "\u2022 " + e.get("title", "")
        extra = []
        if e.get("forecast"):
            extra.append("Forecast: " + str(e["forecast"]))
        if e.get("previous"):
            extra.append("Previous: " + str(e["previous"]))
        if extra:
            line += " (" + " | ".join(extra) + ")"
        lines.append(line)
    lines += ["", "غادي توصلك الأخبار والتحليل بعد الإعلان."]
    return "\n".join(lines)


def main():
    data = load("docs/data.json", {})
    events = data.get("calendar") or []
    if not events:
        print("No events in data.json")
        return
    now = int(time.time() * 1000)
    groups = {}
    for e in events:
        try:
            ts = int(e["ts"])
        except Exception:
            continue
        groups.setdefault(ts, []).append(e)

    if FORCE:
        future = sorted(t for t in groups if t > now)
        if not future:
            print("No upcoming events")
            return
        ts = future[0]
        mins = max(1, int((ts - now) / 60000))
        telegram(build(ts, groups[ts], mins, True))
        return

    week_ago = now - 7 * 24 * 3600 * 1000
    alerted = [t for t in load("docs/alerted.json", []) if isinstance(t, int) and t > week_ago]
    for ts in sorted(groups):
        delta = (ts - now) / 60000
        if 0 < delta <= WINDOW_MIN and ts not in alerted:
            telegram(build(ts, groups[ts], int(delta), False))
            alerted.append(ts)
    os.makedirs("docs", exist_ok=True)
    with open("docs/alerted.json", "w", encoding="utf-8") as f:
        json.dump(alerted, f)


if __name__ == "__main__":
    main()
