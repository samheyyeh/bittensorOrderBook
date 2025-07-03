#!/usr/bin/env python3

import requests
from decimal import Decimal, InvalidOperation
import time
import math
import threading
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HEADERS = {
    "accept": "application/json",
    "Authorization": os.environ.get("TAOSTATS_API_KEY", "")
}

SUBNETS = {
    3: "Templar",
    4: "Targon",
    5: "OpenKaito",
    8: "Taoshi",
    10: "Sturdy",
    19: "Vision",
    56: "Gradient",
    64: "Chutes"
}

RAO_DIVISOR = 10**9

# Rate limiting: 5 requests per minute
TAOSTATS_RATE_LIMIT = 5
TAOSTATS_TIME_WINDOW = 40  # seconds
_taostats_request_times = []
_taostats_lock = threading.Lock()

def taostats_rate_limited_request(*args, **kwargs):
    """Wrap requests.get to rate limit Taostats API calls to 5 per minute."""
    import time
    global _taostats_request_times
    with _taostats_lock:
        now = time.time()
        # Remove timestamps older than 60 seconds
        _taostats_request_times = [t for t in _taostats_request_times if now - t < TAOSTATS_TIME_WINDOW]
        if len(_taostats_request_times) >= TAOSTATS_RATE_LIMIT:
            sleep_time = TAOSTATS_TIME_WINDOW - (now - _taostats_request_times[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
            now = time.time()
            _taostats_request_times = [t for t in _taostats_request_times if now - t < TAOSTATS_TIME_WINDOW]
        _taostats_request_times.append(time.time())
    return requests.get(*args, **kwargs)

def format_number(value, decimals=2, add_commas=True):
    try:
        num = float(value)
        num = round(num, decimals)
        if add_commas:
            return f"{num:,.{decimals}f}"
        else:
            return f"{num:.{decimals}f}"
    except (ValueError, TypeError):
        return value

def fetch_tao_price_usd():
    # Try Taostats API first
    try:
        resp = taostats_rate_limited_request("https://api.taostats.io/api/price/latest", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Try to find the price in the response
        if isinstance(data, dict):
            price = data.get("price_usd") or data.get("price")
            if price:
                return float(price)
    except Exception:
        pass
    # Fallback to CoinGecko (not rate-limited)
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bittensor&vs_currencies=usd", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = data.get("bittensor", {}).get("usd")
        if price:
            return float(price)
    except Exception:
        pass
    return None

def fetch_financial_data(netuid, tao_price_usd=None):
    url = f"https://api.taostats.io/api/dtao/pool/latest/v1?netuid={netuid}&page=1"
    try:
        response = taostats_rate_limited_request(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()["data"][0]
        # Parse TAO values
        market_cap_tao = float(data.get('market_cap', 0)) / RAO_DIVISOR
        alpha_staked_tao = float(data.get('alpha_staked', 0)) / RAO_DIVISOR
        alpha_in_pool_tao = float(data.get('alpha_in_pool', 0)) / RAO_DIVISOR
        tao_volume_24_hr_tao = float(data.get('tao_volume_24_hr', 0)) / RAO_DIVISOR
        # USD conversions
        price = float(data.get('price', 0))
        market_cap_usd = market_cap_tao * tao_price_usd if tao_price_usd is not None else None
        alpha_staked_usd = alpha_staked_tao * price if price else None
        alpha_in_pool_usd = alpha_in_pool_tao * price if price else None
        tao_volume_24_hr_usd = tao_volume_24_hr_tao * tao_price_usd if tao_price_usd is not None else None
        return {
            "netuid": data.get("netuid"),
            "name": data.get("name"),
            "market_cap": f"{format_number(market_cap_tao)} TAO",
            "market_cap_usd": f"${format_number(market_cap_usd)}" if market_cap_usd is not None else "N/A",
            "market_cap_change_1_day": f"{format_number(data.get('market_cap_change_1_day'), 2, False)} %",
            "alpha_staked": f"{format_number(alpha_staked_tao)} ALPHA",
            "alpha_staked_usd": f"${format_number(alpha_staked_usd)}" if alpha_staked_usd is not None else "N/A",
            "alpha_in_pool": f"{format_number(alpha_in_pool_tao)} ALPHA",
            "alpha_in_pool_usd": f"${format_number(alpha_in_pool_usd)}" if alpha_in_pool_usd is not None else "N/A",
            "price": f"${format_number(data.get('price'), 5, False)}",
            "price_change_1_day": f"{format_number(data.get('price_change_1_day'), 2, False)} %",
            "tao_volume_24_hr": f"{format_number(tao_volume_24_hr_tao)} TAO",
            "tao_volume_24_hr_usd": f"${format_number(tao_volume_24_hr_usd)}" if tao_volume_24_hr_usd is not None else "N/A",
            "buyers_24_hr": f"{format_number(data.get('buyers_24_hr'), 0, True)}",
            "sellers_24_hr": f"{format_number(data.get('sellers_24_hr'), 0, True)}",
            "fear_and_greed_index": f"{format_number(data.get('fear_and_greed_index'), 2, False)}",
            "fear_and_greed_sentiment": data.get("fear_and_greed_sentiment")
        }
    except Exception as e:
        print(f"Error fetching subnet {netuid}: {e}")
        return {
            "netuid": netuid,
            "name": SUBNETS.get(netuid, f"Subnet {netuid}"),
            "error": str(e)
        }

def get_all_subnet_financial_data():
    results = []
    subnet_ids = list(SUBNETS.keys())
    tao_price_usd = fetch_tao_price_usd()
    for i in range(0, len(subnet_ids), 4):
        batch = subnet_ids[i:i+4]
        for netuid in batch:
            results.append(fetch_financial_data(netuid, tao_price_usd=tao_price_usd))
        if i + 4 < len(subnet_ids):
            time.sleep(60)  # Wait 60 seconds before next batch
    return results
