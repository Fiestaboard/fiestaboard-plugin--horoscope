"""Horoscope plugin for FiestaBoard.

Displays the daily horoscope for one zodiac sign from the free
Horoscope API (freehoroscopeapi.com), plus locally computed sign facts (symbol, element,
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

API_URL = "https://freehoroscopeapi.com/api/v1/get-horoscope/daily"
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

SHORT_MAX_LENGTH = 66

# Fallback board when a plugin method runs outside a board-scoped render
# (self.board is None) -- a Flagship, per the platform's documented contract.
_DEFAULT_ROWS = 6
_DEFAULT_COLS = 22


def _horoscope_capacity(board) -> int:
    """Character budget for the ``horoscope`` variable, derived from *board*.

    Previously this was a flat 264, sized for a Flagship (6x22) -- fine
    there, but it silently discarded almost all of a large note_array's
    capacity (up to 120x24 = 2880 tiles) since the same 264-character cap
    applied no matter how big the board was. Deriving it from the board's
    own dimensions means a bigger board gets more of the reading; a Note
    gets a small, tight budget instead of 264 characters it could never
    show anyway.
    """
    rows = board.rows if board else _DEFAULT_ROWS
    cols = board.cols if board else _DEFAULT_COLS
    return rows * cols


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


def _build_lines(sign: str, date: str, horoscope_text: str, rows: int, cols: int) -> List[str]:
    """Header line with sign and date, then the wrapped horoscope text.

    Shared by :meth:`HoroscopePlugin.fetch_data` (the live
    ``formatted_lines`` path) and :meth:`HoroscopePlugin.get_formatted_display`
    so the two paths can never drift apart.
    """
    header = f"{sign}  {date}".upper()[:cols]
    lines = [header] + _wrap_lines(horoscope_text, cols, rows - 1)
    while len(lines) < rows:
        lines.append("")
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
            data = response.json().get("data") or {}
            text = (data.get("horoscope") or "").strip()
            if not text:
                return PluginResult(available=False, error="No horoscope returned from API")

            raw_date = str(data.get("date") or "")
            formatted_date = _format_date(raw_date)

            # `short` is a small, fixed-size summary meant for custom
            # templates regardless of board -- take it from the untouched
            # fetched text, before the board-sized cap below narrows `text`
            # down to whatever a Note's tiny budget allows.
            short = _first_sentence(text)

            board = self.board
            rows = board.rows if board else _DEFAULT_ROWS
            cols = board.cols if board else _DEFAULT_COLS
            capacity = _horoscope_capacity(board)
            if len(text) > capacity:
                text = text[: max(capacity - 3, 0)].rstrip() + "..."

            symbol, element, date_range = SIGNS[sign]
            lines = _build_lines(sign, formatted_date, text, rows, cols)
            return PluginResult(
                available=True,
                formatted_lines=lines,
                data={
                    "sign": sign,
                    "date": formatted_date,
                    "horoscope": text,
                    "short": short,
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
        """Header line with sign and date, then the wrapped horoscope text.

        Delegates to :meth:`fetch_data` (via :meth:`get_data`) for both the
        text and the line-wrapping, so this dead-in-core hook never drifts
        from the live ``formatted_lines`` path. Explicitly forwards
        ``self.board`` -- without it, ``get_data()`` binds a fresh ``None``
        board for the duration of the fetch and the reading gets sized for
        a Flagship no matter what board this is actually rendering for.
        """
        result = self.get_data(self.board)
        if not result.available:
            return None
        return result.formatted_lines


# Export the plugin class
Plugin = HoroscopePlugin
