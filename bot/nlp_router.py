"""LLM-fronted free-text router for the bot.

Claude Haiku 4.5 classifies the pilot's plain-language message into one of
a small set of intents. The router never fabricates aviation data — it
only routes to a command. The command's backend call is the source of
truth for everything we tell the pilot.

LLM failures degrade silently to a keyword-matching fallback — roster
generation and FTL legality never depend on the LLM.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.services import llm_client

log = logging.getLogger("ratiba.bot.nlp")

Intent = Literal[
    "roster",
    "duty_today",
    "currency",
    "notices",
    "swap_help",
    "leave_help",
    "help",
    "unknown",
]


@dataclass(frozen=True)
class Routed:
    intent: Intent
    confidence: float
    raw_text: str


SYSTEM_PROMPT = """\
You are the intent router for a Telegram bot used by airline pilots.
Classify the user's message into ONE of these intents:

- "roster"       — they want their upcoming roster / schedule
- "duty_today"   — they want today's specific duty
- "currency"     — they're asking about recency / OPC / LPC / line check
- "notices"      — they want fleet notices / operational comms / announcements
- "swap_help"    — they want to swap a duty with another pilot
- "leave_help"   — they want to request leave / time off
- "help"         — they're confused, asking for help, saying hi
- "unknown"      — anything else (small-talk, complaints, irrelevant)

Respond with STRICT JSON only — no markdown, no commentary — in the shape:

  {"intent": "<one of the strings above>", "confidence": <0.0-1.0>}

Be conservative: when in doubt between two intents, prefer "help" with
moderate confidence. Never invent flight details — you are only routing.
"""


# Order matters: more specific intents come first so a generic phrase
# ("next week") can't preempt a specific one ("annual leave next week").
_KEYWORD_FALLBACK: tuple[tuple[re.Pattern[str], Intent], ...] = (
    (re.compile(r"\b(leave|holiday|time off|annual|sick)\b", re.I), "leave_help"),
    (re.compile(r"\b(swap|switch|trade)\b", re.I), "swap_help"),
    (re.compile(r"\b(opc|lpc|currency|recency|line check|landings?)\b", re.I), "currency"),
    (re.compile(r"\b(notice|notices|announcement|memo|bulletin|comms)\b", re.I), "notices"),
    (re.compile(r"\b(today|do i fly|tonight)\b", re.I), "duty_today"),
    (re.compile(r"\b(roster|schedule|next\s+week|14\s*days?)\b", re.I), "roster"),
    (re.compile(r"\b(help|hi|hello|hey|how\b|what can)", re.I), "help"),
)


def _keyword_route(text: str) -> Routed:
    for pattern, intent in _KEYWORD_FALLBACK:
        if pattern.search(text):
            return Routed(intent=intent, confidence=0.55, raw_text=text)
    return Routed(intent="unknown", confidence=0.0, raw_text=text)


_VALID_INTENTS = {
    "roster",
    "duty_today",
    "currency",
    "notices",
    "swap_help",
    "leave_help",
    "help",
    "unknown",
}


def route(text: str) -> Routed:
    """Classify ``text``. Falls back to keyword matching on any LLM failure."""
    text = (text or "").strip()
    if not text:
        return Routed(intent="help", confidence=1.0, raw_text="")

    try:
        result = llm_client.conversational_route(
            system=SYSTEM_PROMPT, user_message=text, max_tokens=64
        )
    except llm_client.LlmClientNotConfigured:
        log.info("LLM not configured — keyword fallback")
        return _keyword_route(text)
    except Exception as exc:
        log.warning("LLM router error %r — keyword fallback", exc)
        return _keyword_route(text)

    body = result.text.strip()
    # Best-effort strip of any code fences the model might add.
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    try:
        payload = json.loads(body)
        intent_raw = str(payload.get("intent", "unknown"))
        if intent_raw not in _VALID_INTENTS:
            return _keyword_route(text)
        confidence = float(payload.get("confidence", 0.5))
        return Routed(
            intent=intent_raw,  # type: ignore[arg-type]
            confidence=max(0.0, min(1.0, confidence)),
            raw_text=text,
        )
    except (ValueError, KeyError, TypeError) as exc:
        log.warning("malformed LLM response %r — keyword fallback", exc)
        return _keyword_route(text)
