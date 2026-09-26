"""Board-geometry conformance for the horoscope plugin.

Imports the shared suite that FiestaBoard core holds its own plugins to
(``src/plugins/geometry_conformance.py``, available on ``PYTHONPATH`` in
plugin CI). It renders this plugin across every board shape the platform
supports -- Flagship, Note, and note_array from 15x3 up to 120x24 (also
what a FiestaPanel is) -- and checks bounds, declared variable lengths, and
row growth on a taller board.

``strict_growth=True`` is used here because the horoscope text is exactly
the kind of content a fixed, board-independent cap silently truncates: more
board, more of the reading.

Note: the row-count growth check in this shared suite (``check_growth``)
holds width constant at the Note's 15 columns while varying height, so it
cannot by itself distinguish "capped independent of the board" from "capped
correctly" for a single word-wrapped block of prose -- a fixed character
cap of any size that is merely *enough* to fill the shortest rung still lets
a taller board show strictly more lines, satisfying the inequality this
check asserts. The real regression -- a 120x24 board getting the same 264
characters as a Flagship -- is caught by this repo's own
``tests/test_plugin.py::TestFetchData::test_horoscope_grows_with_board_size``
and ``TestFormattedLinesOnResult::test_fetch_data_formatted_lines_grow_with_board_size``,
which compare a Note against a 120x24 note_array directly. Both suites are
kept: this one for the bounds/declared-length/preview checks it uniquely
provides, the other for the growth regression it uniquely catches.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.plugins.geometry_conformance import assert_board_conformance

from plugins.horoscope import HoroscopePlugin

MANIFEST = json.loads((Path(__file__).parent.parent / "manifest.json").read_text())

# Long enough that even the largest board (120x24, capacity 2880) has more
# reading available than it can show -- so every geometry in the suite is
# genuinely exercised, not just handed a few words that fit trivially
# everywhere.
LONG_HOROSCOPE_TEXT = (
    "Things are moving quickly for Aries right now, with new opportunities "
    "and experiences coming up fast. It's a good idea to stay flexible and "
    "adapt to changing circumstances. "
) * 40


def _ok_response():
    response = Mock()
    response.json.return_value = {
        "data": {
            "date": "2026-09-13",
            "period": "daily",
            "sign": "Aries",
            "horoscope": LONG_HOROSCOPE_TEXT,
        },
    }
    response.raise_for_status = Mock()
    return response


@patch("plugins.horoscope.requests.get")
def test_renders_on_every_board_shape(mock_get):
    mock_get.return_value = _ok_response()

    def make_plugin() -> HoroscopePlugin:
        """A fresh, configured plugin. The network is already stubbed above
        for the duration of this test, so no fresh plugin ever touches it."""
        plugin = HoroscopePlugin(MANIFEST)
        plugin._config = {"sign": "Aries", "day": "TODAY", "refresh_seconds": 21600}
        return plugin

    assert_board_conformance(
        make_plugin,
        manifest=MANIFEST,
        strict_growth=True,
        require_note_array_preview=True,
    )
