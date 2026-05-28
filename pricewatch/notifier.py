"""
WhatsApp notifications via Twilio.
Sends messages to the personal number configured in WHATSAPP_TO.
"""
from __future__ import annotations

import os
from textwrap import shorten
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .models import MarketReport

_BOLD = "*"  # WhatsApp markdown bold


def _client() -> Client:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        raise RuntimeError(
            "Twilio credentials missing. "
            "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"
        )
    return Client(sid, token)


def _from_number() -> str:
    n = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    return n if n.startswith("whatsapp:") else f"whatsapp:{n}"


def _to_number() -> str:
    n = os.getenv("WHATSAPP_TO", "")
    if not n:
        raise RuntimeError("WHATSAPP_TO not set in .env")
    return n if n.startswith("whatsapp:") else f"whatsapp:{n}"


def whatsapp_configured() -> bool:
    """Return True if all WhatsApp env vars are present."""
    return all([
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
        os.getenv("WHATSAPP_TO"),
    ])


def send_message(text: str) -> dict:
    """Send a raw text message to WHATSAPP_TO. Returns status dict."""
    try:
        msg = _client().messages.create(
            body=text,
            from_=_from_number(),
            to=_to_number(),
        )
        return {"status": "sent", "sid": msg.sid}
    except TwilioRestException as e:
        return {"status": "error", "code": e.code, "message": e.msg}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_report(report: MarketReport) -> dict:
    """Format and send a MarketReport as a WhatsApp message."""
    lines: list[str] = []

    lines.append("*[ Centinela — Market Report ]*")
    lines.append("")

    # Summary (cap at 600 chars to avoid Twilio limits)
    lines.append(shorten(report.summary, width=600, placeholder="..."))

    if report.alerts:
        lines.append("")
        lines.append("*-- Alertas --*")
        for a in report.alerts:
            lines.append(f"  - {a}")

    if report.recommendations:
        lines.append("")
        lines.append("*-- Recomendaciones --*")
        for r in report.recommendations:
            lines.append(f"  - {r}")

    if report.coins_analyzed:
        lines.append("")
        lines.append(f"Analizadas: {', '.join(c.upper() for c in report.coins_analyzed)}")

    return send_message("\n".join(lines))


def send_alert(coin_id: str, message: str, severity: str = "warning") -> dict:
    """Send a single price alert to WhatsApp."""
    prefixes = {"info": "[INFO]", "warning": "[!]", "critical": "[!!]"}
    prefix = prefixes.get(severity, "[!]")
    text = f"*{prefix} Centinela Alert*\n\n*{coin_id.upper()}* - {message}"
    return send_message(text)
