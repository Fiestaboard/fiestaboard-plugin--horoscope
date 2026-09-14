"""Horoscope plugin for FiestaBoard.

Displays the daily horoscope for one zodiac sign from the free
Horoscope App API, plus locally computed sign facts (symbol, element,
date range) and a deterministic daily lucky number.
"""

import hashlib
import logging
import re
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from src.plugins.base import PluginBase, PluginResult

logger = logging.getLogger(__name__)

API_URL = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
USER_AGENT = "FiestaBoard (https://github.com/FiestaBoard/FiestaBoard)"

DAYS = ("TODAY", "TOMORROW", "YESTERDAY")

# sign -> (symbol, element, date range)
SIGNS = {
    "Aries": ("The Ram", "Fire", "Mar 21 - Apr 19"),
    "Taurus": ("The Bull", "Earth", "Apr 20 - May 20"),
    "Gemini": ("The Twins", "Air", "May 21 - Jun 20"),
    "Cancer": ("The Crab", "Water", "Jun 21 - Jul 22"),
    "Leo": ("The Lion", "Fire", "Jul 23 - Aug 22"),
    "Virgo": ("The Maiden", "Earth", "Aug 23 - Sep 22"),
    "Libra": ("The Scales", "Air", "Sep 23 - Oct 22"),
    "Scorpio": ("The Scorpion", "Water", "Oct 23 - Nov 21"),
    "Sagittarius": ("The Archer", "Fire", "Nov 22 - Dec 21"),
    "Capricorn": ("The Goat", "Earth", "Dec 22 - Jan 19"),
    "Aquarius": ("The Water Bearer", "Air", "Jan 20 - Feb 18"),
    "Pisces": ("The Fish", "Water", "Feb 19 - Mar 20"),
}

HOROSCOPE_MAX_LENGTH = 264
SHORT_MAX_LENGTH = 66


def _first_sentence(text: str, max_length: int = SHORT_MAX_LENGTH) -> str:
    """Return the first sentence of *text*, truncated to *max_length*."""
    sentence = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
    if len(sentence) > max_length:
        sentence = sentence[: max_length - 3].rstrip() + "..."
    return sentence


def _format_date(raw: str) -> str:
    """Turn the API's ``YYYY-MM-DD`` into ``Sep 13``; pass through anything else."""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%b %d").replace(" 0", " ")
    except ValueError:
        return raw


def _lucky_number(sign: str, date: str) -> int:
    """Deterministic 1-99 number for a sign on a given date."""
    digest = hashlib.sha256(f"{sign}:{date}".encode()).hexdigest()
    return int(digest, 16) % 99 + 1


def _wrap_lines(text: str, width: int, max_lines: int) -> List[str]:
    """Word-wrap *text* to at most *max_lines* lines, ending with ``...`` if cut."""
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 3].rstrip() + "..."
    return lines


class HoroscopePlugin(PluginBase):
    """Daily horoscope for a single zodiac sign."""

    @property
    def plugin_id(self) -> str:
        return "horoscope"

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        errors = self._validate_refresh_seconds(config)
        sign = config.get("sign", "Aries")
        if sign not in SIGNS:
            errors.append(f"Invalid sign '{sign}'. Must be one of: {', '.join(SIGNS)}")
        day = config.get("day", "TODAY")
        if day not in DAYS:
            errors.append(f"Invalid day '{day}'. Must be one of: {', '.join(DAYS)}")
        return errors

    def fetch_data(self) -> PluginResult:
        """Fetch the daily horoscope and build the variable set."""
        try:
            sign = self.config.get("sign") or "Aries"
            day = self.config.get("day") or "TODAY"
            if sign not in SIGNS:
                return PluginResult(available=False, error=f"Invalid sign: {sign}")

            response = requests.get(
                API_URL,
                params={"sign": sign, "day": day},
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()

            if payload.get("success") is False:
                return PluginResult(
                    available=False,
                    error=payload.get("error") or "API reported failure",
                )

            data = payload.get("data") or {}
            # The service has served the text under both keys over time.
            text = (data.get("horoscope") or data.get("horoscope_data") or "").strip()
            if not text:
                return PluginResult(available=False, error="No horoscope returned from API")

            raw_date = str(data.get("date") or "")
            if len(text) > HOROSCOPE_MAX_LENGTH:
                text = text[: HOROSCOPE_MAX_LENGTH - 3].rstrip() + "..."

            symbol, element, date_range = SIGNS[sign]
            return PluginResult(
                available=True,
                data={
                    "sign": sign,
                    "date": _format_date(raw_date),
                    "horoscope": text,
                    "short": _first_sentence(text),
                    "element": element,
                    "symbol": symbol,
                    "date_range": date_range,
                    "lucky_number": _lucky_number(sign, raw_date),
                },
            )

        except Exception as e:
            logger.exception("Error fetching horoscope")
            return PluginResult(available=False, error=str(e))

    def get_formatted_display(self) -> Optional[List[str]]:
        """Header line with sign and date, then the wrapped horoscope text."""
        result = self.get_data()
        if not result.available or not result.data:
            return None

        rows = self.board.rows if self.board else 6
        cols = self.board.cols if self.board else 22

        header = f"{result.data['sign']}  {result.data['date']}".upper()[:cols]
        lines = [header] + _wrap_lines(result.data["horoscope"], cols, rows - 1)
        while len(lines) < rows:
            lines.append("")
        return lines


# Export the plugin class
Plugin = HoroscopePlugin
