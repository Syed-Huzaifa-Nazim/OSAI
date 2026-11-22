"""The one LLM call the Instagram analysis makes: labelling comment mood.

Uses Groq when GROQ_API_KEY is set in backend/.env. Without a key the comment
analysis is skipped and the run says so; nothing else depends on it.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

from app.core.config import settings

logger = logging.getLogger("optistratix.analysis.llm")
MAX_WAIT_S = 15          # longest a person on the screen is kept waiting for a rate limit


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
    models = [settings.groq_model] + [m.strip() for m in settings.groq_fallback_models.split(",") if m.strip()]

    def call_llm(prompt: str) -> str:
        # A rate-limited model is skipped at once for the next one in GROQ_FALLBACK_MODELS, so a person waiting on
        # the screen is not kept waiting. Only when every model is limited is there one short wait, then a retry.
        waits: list[float] = []
        for attempt in range(2):
            for model in models:
                try:
                    r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
                    return r.choices[0].message.content or ""
                except RateLimitError as exc:
                    m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(exc))
                    waits.append((int(m.group(1) or 0) * 60 + float(m.group(2)) + 1) if m else 20)
                    logger.info("Groq model %s is rate-limited; trying the next one.", model)
            if attempt == 0 and waits and min(waits) <= MAX_WAIT_S:
                time.sleep(min(waits))
            else:
                break
        raise RuntimeError("The language model is busy right now (rate limit). Please try again in a minute.")

    return call_llm
