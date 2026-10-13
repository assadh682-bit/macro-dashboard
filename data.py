import json, os, requests
from datetime import datetime
from zoneinfo import ZoneInfo


def get(url, params=None):
    r = requests.get(url, params=params, timeout=40, headers={"User-Agent": "macro-dashboard"})
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


def main():
    out = {"updated": datetime.now(ZoneInfo("Africa/Casablanca")).strftime("%Y-%m-%d %H:%M"),
           "auctions": None, "cot": None}
    for key, fn in (("auctions", auctions), ("cot", cot)):
        try:
            out[key] = fn()
        except Exception as err:
            print(key, "error:", type(err).__name__, str(err)[:200])
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
