"""The one LLM call the Instagram analysis makes: labelling comment mood."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

from app.core.config import settings

logger = logging.getLogger("optistratix.analysis.llm")


def get_llm() -> Callable[[str], str] | None:
    """Returns call_llm(prompt) -> str, or None when no LLM is configured."""
    if not settings.groq_api_key:
        return None
    try:
        from groq import Groq, RateLimitError
    except ImportError:
        logger.warning("GROQ_API_KEY is set but the 'groq' package is not installed.")
        return None

    client = Groq(api_key=settings.groq_api_key)

    def call_llm(prompt: str) -> str:
        for _ in range(6):
            try:
                r = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return r.choices[0].message.content or ""
            except RateLimitError as exc:
                m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(exc))
                time.sleep((int(m.group(1) or 0) * 60 + float(m.group(2)) + 1) if m else 20)
        raise RuntimeError("The LLM stayed rate-limited; comment analysis was skipped.")

    return call_llm