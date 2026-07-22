import urllib.request
import json
from datetime import datetime, timedelta

SUPPORTED = ["USD", "EUR", "GBP", "SAR", "AED"]
BASE = "PKR"

URLS = [
    "https://latest.currency-api.pages.dev/v1/currencies/pkr.json",
    "https://cdn.jsdelivr.net/npm/@fawaz-ahmed/currency-api@latest/v1/currencies/pkr.json",
]

cache = {"rates": None, "date": None, "fetched_at": None}
cache_time = timedelta(hours=1)


def _fetch_from_api():

    last_err = None
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BankFlow/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            all_rates = data["pkr"]                       
            rates = {}
            for c in SUPPORTED:
                rates[c] = all_rates[c.lower()]  
            return rates, data["date"]
        except Exception as e:
            last_err = e
            continue                                       
    raise Exception(f"All exchange rate sources failed: {last_err}")


def get_rates():
    now = datetime.now()

    if cache["rates"] and cache["fetched_at"] and (now - cache["fetched_at"]) < cache_time:
        return cache["rates"], cache["date"], "cache"

    try:
        rates, date = _fetch_from_api()
        cache["rates"] = rates
        cache["date"] = date
        cache["fetched_at"] = now
        return rates, date, "live"
    except Exception as e:
     
        if cache["rates"]:
            return cache["rates"], cache["date"], "stale cache"
        raise Exception(f"Exchange rate service unavailable: {e}")