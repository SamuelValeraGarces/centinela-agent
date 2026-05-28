"""
Pure I/O functions called by the agent tools.
No PydanticAI dependency here — keeps the module testable in isolation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

from .storage import read_json, write_json

_COINGECKO = "https://api.coingecko.com/api/v3"
_HEADERS = {"Accept": "application/json"}
_TIMEOUT = 12


# ── Price data ──────────────────────────────────────────────────────────────

def fetch_price(coin_id: str) -> dict:
    try:
        resp = httpx.get(
            f"{_COINGECKO}/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            },
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if coin_id not in data:
            return {
                "status": "not_found",
                "coin_id": coin_id,
                "tip": f"'{coin_id}' not found. Call search_coin('{coin_id}') to get the correct ID.",
            }
        c = data[coin_id]
        return {
            "status": "ok",
            "coin_id": coin_id,
            "price_usd": c.get("usd", 0),
            "change_24h_pct": round(c.get("usd_24h_change", 0), 2),
            "market_cap_usd": c.get("usd_market_cap", 0),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_history(coin_id: str, days: int) -> dict:
    try:
        days = min(max(days, 1), 30)
        resp = httpx.get(
            f"{_COINGECKO}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        raw_prices = [p[1] for p in resp.json().get("prices", [])]
        if not raw_prices:
            return {"status": "no_data", "coin_id": coin_id}

        # Thin to ≤15 evenly-spaced points for the LLM context
        step = max(1, len(raw_prices) // 15)
        sample = raw_prices[::step][-15:]
        first, last = sample[0], sample[-1]
        change_pct = round((last - first) / first * 100, 2)

        return {
            "status": "ok",
            "coin_id": coin_id,
            "days": days,
            "period_open": round(first, 2),
            "current": round(last, 2),
            "period_high": round(max(raw_prices), 2),
            "period_low": round(min(raw_prices), 2),
            "change_pct": change_pct,
            "trend": "bullish" if change_pct > 3 else ("bearish" if change_pct < -3 else "sideways"),
            "price_sample": [round(p, 2) for p in sample],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_coins(query: str) -> dict:
    try:
        resp = httpx.get(
            f"{_COINGECKO}/search",
            params={"query": query},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        coins = resp.json().get("coins", [])[:5]
        return {
            "results": [
                {"id": c["id"], "name": c["name"], "symbol": c["symbol"].upper()}
                for c in coins
            ],
            "tip": "Use the 'id' field with get_crypto_price()",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Watchlist CRUD ───────────────────────────────────────────────────────────

def get_watchlist() -> dict:
    wl = read_json("watchlist.json")
    return {"watchlist": wl, "count": len(wl)}


def upsert_watchlist(
    coin_id: str,
    alias: str,
    threshold_low: Optional[float] = None,
    threshold_high: Optional[float] = None,
) -> dict:
    wl = read_json("watchlist.json")
    wl = [w for w in wl if w["coin_id"] != coin_id]
    entry = {
        "coin_id": coin_id,
        "alias": alias,
        "threshold_low": threshold_low,
        "threshold_high": threshold_high,
        "added_at": datetime.now().isoformat(),
    }
    wl.append(entry)
    write_json("watchlist.json", wl)
    return {"status": "added", "entry": entry}


def delete_from_watchlist(coin_id: str) -> dict:
    wl = read_json("watchlist.json")
    before = len(wl)
    wl = [w for w in wl if w["coin_id"] != coin_id]
    write_json("watchlist.json", wl)
    removed = len(wl) < before
    return {"status": "removed" if removed else "not_found", "coin_id": coin_id}


# ── Alerts ───────────────────────────────────────────────────────────────────

def append_alert(coin_id: str, message: str, severity: str) -> dict:
    alerts = read_json("alerts.json")
    alert = {
        "coin_id": coin_id,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }
    alerts.append(alert)
    write_json("alerts.json", alerts[-200:])
    return {"status": "saved", "alert": alert}


def recent_alerts(limit: int) -> dict:
    alerts = read_json("alerts.json")
    return {"alerts": alerts[-limit:], "total_saved": len(alerts)}
