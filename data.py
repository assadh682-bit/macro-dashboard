import json, os, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get(url, params=None, headers=None):
    h = {"User-Agent": "macro-dashboard"}
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, timeout=40, headers=h)
    r.raise_for_status()
    return r.json()


def auctions():
    data = get("https://www.treasurydirect.gov/TA_WS/securities/upcoming", {"format": "json"})
    out = []
    for a in data:
        out.append({
            "type": a.get("securityType", ""),
            "term": a.get("securityTerm", ""),
            "date": (a.get("auctionDate") or "")[:10],
            "amount": a.get("offeringAmount", ""),
        })
    out.sort(key=lambda x: x["date"])
    return out[:12]


def to_int(v):
    try:
        return int(float(v))
    except Exception:
        return 0


def cot():
    url = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
    res = {}
    for name, market in [("GC", "GOLD - COMMODITY EXCHANGE INC."), ("SIL", "SILVER - COMMODITY EXCHANGE INC.")]:
        rows = get(url, {"market_and_exchange_names": market,
                         "$order": "report_date_as_yyyy_mm_dd DESC", "$limit": "2"})
        if not rows:
            continue
        cur = rows[0]
        long_ = to_int(cur.get("m_money_positions_long_all"))
        short = to_int(cur.get("m_money_positions_short_all"))
        net = long_ - short
        change = None
        if len(rows) > 1:
            prev = to_int(rows[1].get("m_money_positions_long_all")) - to_int(rows[1].get("m_money_positions_short_all"))
            change = net - prev
        res[name] = {"date": (cur.get("report_date_as_yyyy_mm_dd") or "")[:10],
                     "long": long_, "short": short, "net": net, "change": change}
    return res


def calendar():
    events = []
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/json,text/plain,*/*",
               "Referer": "https://www.forexfactory.com/"}
    for url in ("https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                "https://nfs.faireconomy.media/ff_calendar_nextweek.json"):
        rows = None
        for attempt in range(2):
            try:
                rows = get(url, headers=headers)
                break
            except requests.HTTPError as err:
                code = err.response.status_code if err.response is not None else 0
                print("calendar HTTP", code, url)
                if code == 429 and attempt == 0:
                    time.sleep(8)
                    continue
                break
            except Exception as err:
                print("calendar part error:", type(err).__name__, str(err)[:150])
                break
        if not rows:
            continue
        for e in rows:
            if e.get("country") != "USD" or e.get("impact") != "High":
                continue
            try:
                ts = int(datetime.fromisoformat(e["date"]).timestamp() * 1000)
            except Exception:
                continue
            events.append({"ts": ts, "title": e.get("title", ""),
                           "forecast": e.get("forecast", ""), "previous": e.get("previous", "")})
    if not events:
        raise RuntimeError("no events")
    events.sort(key=lambda x: x["ts"])
    return events


def main():
    out = {"updated": datetime.now(ZoneInfo("Africa/Casablanca")).strftime("%Y-%m-%d %H:%M"),
           "auctions": None, "cot": None, "calendar": None}
    for key, fn in (("auctions", auctions), ("cot", cot), ("calendar", calendar)):
        try:
            out[key] = fn()
        except Exception as err:
            print(key, "error:", type(err).__name__, str(err)[:200])
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
