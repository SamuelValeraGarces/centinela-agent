"""
Centinela — autonomous crypto market monitoring agent.

Uses PydanticAI (2026 state-of-the-art) to:
  - Orchestrate multi-step tool calls in a ReAct loop
  - Return type-safe structured output via Pydantic validation
  - Interact with Claude claude-sonnet-4-6 via Anthropic tool use
"""
from __future__ import annotations

from typing import Optional

from pydantic_ai import Agent

from .models import MarketReport
from . import tools as t
from . import notifier

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = """\
You are Centinela, an autonomous crypto market monitoring agent.

WORKFLOW (follow this order):
1. check_watchlist() → see what's being monitored
2. get_crypto_price(coin_id) → current price for each coin
3. get_price_history(coin_id, days=7) → trend analysis
4. If price < threshold_low OR price > threshold_high → call save_alert()
5. add_to_watchlist() when user requests tracking a new coin
6. If a coin ID is uncertain → call search_coin() first to get the CoinGecko ID

SEVERITY RULES for save_alert() and send_whatsapp_alert():
- "info"     → informational update, no threshold breach
- "warning"  → price within 5% of threshold
- "critical" → threshold already breached

When a threshold is breached, call BOTH save_alert() AND send_whatsapp_alert() so the user gets notified immediately on WhatsApp.

TREND classification (from get_price_history):
- bullish  : change_pct > +3%
- bearish  : change_pct < -3%
- sideways : between -3% and +3%

OUTPUT (MarketReport):
- summary        : executive overview with specific USD values and trends
- alerts         : threshold breaches found this run (empty list if none)
- recommendations: 2–4 actionable suggestions (e.g. "Set stop-loss at $X")
- coins_analyzed : every coin_id you checked

Always be precise with numbers. Use $USD notation. Be concise.
"""

# ── Agent instantiation ───────────────────────────────────────────────────────

agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=MarketReport,
    instructions=_SYSTEM,
)

# ── Tool registrations ────────────────────────────────────────────────────────

@agent.tool_plain
def get_crypto_price(coin_id: str) -> dict:
    """Fetch current USD price and 24h stats for a coin.
    coin_id must be a valid CoinGecko ID (e.g. 'bitcoin', 'ethereum', 'solana').
    """
    return t.fetch_price(coin_id)


@agent.tool_plain
def get_price_history(coin_id: str, days: int = 7) -> dict:
    """Analyze price history and classify trend for a coin over N days (1–30).
    Returns: period_open, current, high, low, change_pct, trend ('bullish'/'bearish'/'sideways').
    """
    return t.fetch_history(coin_id, days)


@agent.tool_plain
def search_coin(query: str) -> dict:
    """Search CoinGecko for a cryptocurrency by name or ticker symbol.
    Returns a list of matches with their CoinGecko ID to use in other tools.
    """
    return t.search_coins(query)


@agent.tool_plain
def check_watchlist() -> dict:
    """Return the full watchlist: all coins being monitored with their thresholds."""
    return t.get_watchlist()


@agent.tool_plain
def add_to_watchlist(
    coin_id: str,
    alias: str,
    threshold_low: Optional[float] = None,
    threshold_high: Optional[float] = None,
) -> dict:
    """Add or update a coin in the watchlist.
    threshold_low / threshold_high (USD): trigger save_alert() when breached.
    alias: human-readable name (e.g. 'Bitcoin').
    """
    return t.upsert_watchlist(coin_id, alias, threshold_low, threshold_high)


@agent.tool_plain
def remove_from_watchlist(coin_id: str) -> dict:
    """Remove a coin from the watchlist permanently."""
    return t.delete_from_watchlist(coin_id)


@agent.tool_plain
def save_alert(coin_id: str, message: str, severity: str = "warning") -> dict:
    """Persist a price alert. Call this whenever a threshold is breached.
    severity: 'info' | 'warning' | 'critical'
    """
    return t.append_alert(coin_id, message, severity)


@agent.tool_plain
def get_recent_alerts(limit: int = 10) -> dict:
    """Return the N most recent saved alerts from the alert log."""
    return t.recent_alerts(limit)


@agent.tool_plain
def send_whatsapp_alert(coin_id: str, message: str, severity: str = "warning") -> dict:
    """Send an immediate WhatsApp notification to the user's personal number.
    Call this when a price threshold is breached (in addition to save_alert).
    severity: 'info' | 'warning' | 'critical'
    """
    if not notifier.whatsapp_configured():
        return {"status": "skipped", "reason": "WhatsApp not configured (TWILIO credentials missing)"}
    return notifier.send_alert(coin_id, message, severity)
