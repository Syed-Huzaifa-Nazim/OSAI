"""robots.txt enforcement for the Alibaba scraper, per RFC 9309.

Every listing URL is checked here before it is fetched -- by requests and by
the browser fallback alike. A disallowed URL is never fetched, and there is no
override.

The standard library's `urllib.robotparser` matches rule paths by prefix only,
so it ignores `*` and `$` wildcards. The listing host publishes
`Disallow: /*?`; under prefix matching that rule matches nothing and query-string
URLs would wrongly look fetchable. The matcher below implements the
specification: wildcards, end anchors, longest-match precedence, Allow winning
ties, and user-agent group selection.

Ported from the reference Alibaba scraper, where it is covered by tests against
Alibaba's real policies.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

#: How long a fetched robots.txt is trusted before being fetched again.
CACHE_SECONDS = 3600


@dataclass(frozen=True)
class _Rule:
    pattern: "re.Pattern[str]"
    allow: bool
    specificity: int


@dataclass
class _Group:
    rules: List[_Rule] = field(default_factory=list)
    crawl_delay: Optional[float] = None


def _compile(path: str) -> Optional["re.Pattern[str]"]:
    if not path:
        return None
    anchored_end = path.endswith("$")
    body = path[:-1] if anchored_end else path
    regex = ".*".join(re.escape(segment) for segment in body.split("*"))
    return re.compile("^" + regex + ("$" if anchored_end else ""))


def _specificity(path: str) -> int:
    return len(path[:-1] if path.endswith("$") else path)


class RobotsRules:
    """A parsed robots.txt, queryable per user agent."""

    def __init__(self, groups: Dict[str, _Group]) -> None:
        self._groups = groups

    @classmethod
    def parse(cls, text: str) -> "RobotsRules":
        groups: Dict[str, _Group] = {}
        current: List[str] = []
        # A directive closes the preceding run of user-agent lines.
        expecting_agents = True

        for raw_line in (text or "").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            name, _, value = line.partition(":")
            key = name.strip().lower()
            value = value.strip()

            if key == "user-agent":
                if not expecting_agents:
                    current = []
                    expecting_agents = True
                agent = value.lower()
                if agent:
                    current.append(agent)
                    groups.setdefault(agent, _Group())
                continue

            if not current:
                continue
            expecting_agents = False

            if key in {"allow", "disallow"}:
                if key == "disallow" and not value:
                    continue  # "Disallow:" with no path restricts nothing
                pattern = _compile(value)
                if pattern is None:
                    continue
                rule = _Rule(pattern=pattern, allow=key == "allow", specificity=_specificity(value))
                for agent in current:
                    groups[agent].rules.append(rule)
            elif key == "crawl-delay":
                try:
                    delay = float(value)
                except ValueError:
                    continue
                for agent in current:
                    groups[agent].crawl_delay = delay

        return cls(groups)

    def _group_for(self, user_agent: str) -> Optional[_Group]:
        needle = user_agent.lower()
        best: Optional[_Group] = None
        best_length = -1
        for agent, group in self._groups.items():
            if agent == "*":
                continue
            if agent in needle and len(agent) > best_length:
                best, best_length = group, len(agent)
        return best if best is not None else self._groups.get("*")

    def can_fetch(self, user_agent: str, url: str) -> bool:
        group = self._group_for(user_agent)
        if group is None or not group.rules:
            return True

        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        winner: Optional[_Rule] = None
        for rule in group.rules:
            if not rule.pattern.match(path):
                continue
            if winner is None or rule.specificity > winner.specificity:
                winner = rule
            elif rule.specificity == winner.specificity and rule.allow:
                winner = rule
        return True if winner is None else winner.allow

    def crawl_delay(self, user_agent: str) -> Optional[float]:
        group = self._group_for(user_agent)
        return group.crawl_delay if group is not None else None


class RobotsDisallowed(Exception):
    """The URL is off-limits under the host's robots.txt."""


class RobotsPolicy:
    """Fetches, caches and applies robots.txt per origin. Thread-safe."""

    def __init__(self, user_agent: str, timeout_seconds: float = 15.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout_seconds
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def _rules_for(self, url: str) -> RobotsRules:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._lock:
            cached = self._cache.get(origin)
            if cached and time.monotonic() - cached[1] < CACHE_SECONDS:
                return cached[0]

            robots_url = f"{origin}/robots.txt"
            try:
                response = requests.get(
                    robots_url, headers={"User-Agent": self._user_agent}, timeout=self._timeout
                )
                if response.status_code >= 400:
                    # A missing robots.txt imposes no restrictions (REP default).
                    log.info("%s returned HTTP %s; no restrictions", robots_url, response.status_code)
                    rules = RobotsRules.parse("")
                else:
                    rules = RobotsRules.parse(response.text)
            except requests.RequestException as exc:
                # Unreachable robots.txt is treated as allow, per the REP, but
                # not cached for long so a transient failure is retried.
                log.warning("Could not fetch %s (%s); proceeding as allowed", robots_url, exc)
                self._cache[origin] = (RobotsRules.parse(""), time.monotonic() - CACHE_SECONDS + 60)
                return self._cache[origin][0]

            self._cache[origin] = (rules, time.monotonic())
            return rules

    def require_allowed(self, url: str) -> None:
        if not self._rules_for(url).can_fetch(self._user_agent, url):
            raise RobotsDisallowed(f"robots.txt disallows fetching {url}")

    def crawl_delay(self, url: str) -> Optional[float]:
        return self._rules_for(url).crawl_delay(self._user_agent)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
