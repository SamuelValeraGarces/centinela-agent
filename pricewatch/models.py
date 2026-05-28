from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WatchEntry(BaseModel):
    coin_id: str
    alias: str
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PriceAlert(BaseModel):
    coin_id: str
    message: str
    severity: str = "warning"  # info | warning | critical
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class MarketReport(BaseModel):
    """Structured report returned by the agent after completing a task."""

    summary: str = Field(
        description="Executive summary: key prices, trends found, and actions taken. Include specific USD values."
    )
    alerts: list[str] = Field(
        default_factory=list,
        description="List of threshold breaches or notable price events found.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="2-4 concrete, actionable recommendations based on the analysis.",
    )
    coins_analyzed: list[str] = Field(
        default_factory=list,
        description="CoinGecko IDs of every coin that was checked.",
    )
