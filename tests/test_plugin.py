"""Tests for the horoscope plugin."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from plugins.horoscope import (
    SIGNS,
    HoroscopePlugin,
    _first_sentence,
    _format_date,
    _lucky_number,
    _wrap_lines,
)
from src.devices import BoardContext

MANIFEST = json.loads((Path(__file__).parent.parent / "manifest.json").read_text())

HOROSCOPE_TEXT = (
    "Things are moving quickly for Aries right now, with new opportunities "
    "and experiences coming up fast. It's a good idea to stay flexible and "
    "adapt to changing circumstances. This is a time to be open-minded."
)


def _ok_response(text=HOROSCOPE_TEXT, date="2026-09-13", **extra):
    response = Mock()
    response.json.return_value = {
        "data": {"date": date, "period": "daily", "sign": "Aries", "horoscope": text},
        **extra,
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def plugin():
    p = HoroscopePlugin(MANIFEST)
    p._config = {"sign": "Aries", "day": "TODAY", "refresh_seconds": 21600}
    return p


class TestFetchData:
    def test_plugin_id(self, plugin):
        assert plugin.plugin_id == "horoscope"

    @patch("plugins.horoscope.requests.get")
    def test_success_returns_every_declared_variable(self, mock_get, plugin):
        mock_get.return_value = _ok_response()

        result = plugin.fetch_data()

        assert result.available is True
        assert result.error is None
        for var in MANIFEST["variables"]["simple"]:
            assert var in result.data, f"Variable '{var}' declared but not returned"
        assert set(result.data) == set(MANIFEST["variables"]["simple"])

    @patch("plugins.horoscope.requests.get")
    def test_success_values(self, mock_get, plugin):
        mock_get.return_value = _ok_response()

        data = plugin.fetch_data().data

        assert data["sign"] == "Aries"
        assert data["date"] == "Sep 13"
        assert data["horoscope"] == HOROSCOPE_TEXT
        assert data["short"].startswith("Things are moving quickly")
        assert len(data["short"]) == 66 and data["short"].endswith("...")
        assert data["element"] == "Fire"
        assert data["symbol"] == "The Ram"
        assert data["date_range"] == "Mar 21 - Apr 19"
        assert 1 <= data["lucky_number"] <= 99

    @patch("plugins.horoscope.requests.get")
    def test_request_params_and_headers(self, mock_get, plugin):
        mock_get.return_value = _ok_response()
        plugin._config["sign"] = "Leo"
        plugin._config["day"] = "TOMORROW"

        plugin.fetch_data()

        kwargs = mock_get.call_args.kwargs
        assert kwargs["params"] == {"sign": "Leo", "day": "TOMORROW"}
        assert kwargs["timeout"] == 10
        assert "FiestaBoard" in kwargs["headers"]["User-Agent"]

    @patch("plugins.horoscope.requests.get")
    def test_http_error(self, mock_get, plugin):
        response = Mock()
        response.raise_for_status.side_effect = Exception("HTTP 500")
        mock_get.return_value = response

        result = plugin.fetch_data()

        assert result.available is False
        assert "HTTP 500" in result.error

    @patch("plugins.horoscope.requests.get")
    def test_network_error(self, mock_get, plugin):
        mock_get.side_effect = Exception("Connection timed out")

        result = plugin.fetch_data()

        assert result.available is False
        assert "Connection timed out" in result.error

    @patch("plugins.horoscope.requests.get")
    def test_empty_text(self, mock_get, plugin):
        mock_get.return_value = _ok_response(text="   ")

        result = plugin.fetch_data()

        assert result.available is False
        assert "No horoscope" in result.error

    @patch("plugins.horoscope.requests.get")
    def test_malformed_response(self, mock_get, plugin):
        response = Mock()
        response.json.return_value = {}
        response.raise_for_status = Mock()
        mock_get.return_value = response

        result = plugin.fetch_data()

        assert result.available is False

    @patch("plugins.horoscope.requests.get")
    def test_invalid_sign_in_config_does_not_call_api(self, mock_get, plugin):
        plugin._config["sign"] = "Ophiuchus"

        result = plugin.fetch_data()

        assert result.available is False
        assert "Invalid sign" in result.error
        mock_get.assert_not_called()

    @patch("plugins.horoscope.requests.get")
    def test_defaults_when_config_empty(self, mock_get, plugin):
        mock_get.return_value = _ok_response()
        plugin._config = {}

        result = plugin.fetch_data()

        assert result.available is True
        assert mock_get.call_args.kwargs["params"] == {"sign": "Aries", "day": "TODAY"}

    @patch("plugins.horoscope.requests.get")
    def test_long_text_is_truncated_to_max_length(self, mock_get, plugin):
        mock_get.return_value = _ok_response(text="word " * 100)

        data = plugin.fetch_data().data

        assert len(data["horoscope"]) <= 264
        assert data["horoscope"].endswith("...")


class TestValidateConfig:
    def test_valid(self, plugin):
        assert plugin.validate_config({"sign": "Pisces", "day": "YESTERDAY", "refresh_seconds": 3600}) == []

    def test_defaults_valid(self, plugin):
        assert plugin.validate_config({}) == []

    def test_invalid_sign(self, plugin):
        errors = plugin.validate_config({"sign": "aries"})
        assert len(errors) == 1
        assert "Invalid sign" in errors[0]

    def test_invalid_day(self, plugin):
        errors = plugin.validate_config({"day": "NEXT_WEEK"})
        assert len(errors) == 1
        assert "Invalid day" in errors[0]

    def test_refresh_below_minimum(self, plugin):
        errors = plugin.validate_config({"refresh_seconds": 60})
        assert len(errors) == 1
        assert "3600" in errors[0]


class TestHelpers:
    def test_first_sentence_period(self):
        assert _first_sentence("First one. Second one.") == "First one."

    def test_first_sentence_question_and_exclamation(self):
        assert _first_sentence("Ready? Go!") == "Ready?"
        assert _first_sentence("Go! Now.") == "Go!"

    def test_first_sentence_no_terminator(self):
        assert _first_sentence("no punctuation here") == "no punctuation here"

    def test_first_sentence_does_not_split_on_decimal(self):
        assert _first_sentence("Pay 3.5 percent today. Then rest.") == "Pay 3.5 percent today."

    def test_first_sentence_truncates(self):
        long = "a" * 100 + "."
        short = _first_sentence(long)
        assert len(short) == 66
        assert short.endswith("...")

    def test_format_date(self):
        assert _format_date("2026-09-13") == "Sep 13"
        assert _format_date("2026-01-05") == "Jan 5"
        assert _format_date("Sep 13, 2026") == "Sep 13, 2026"
        assert _format_date("") == ""

    def test_wrap_fits(self):
        lines = _wrap_lines("short text", 22, 5)
        assert lines == ["short text"]

    def test_wrap_respects_width(self):
        lines = _wrap_lines(HOROSCOPE_TEXT, 22, 5)
        assert 1 < len(lines) <= 5
        assert all(len(line) <= 22 for line in lines)

    def test_wrap_truncates_with_ellipsis(self):
        lines = _wrap_lines("word " * 60, 22, 5)
        assert len(lines) == 5
        assert lines[-1].endswith("...")
        assert all(len(line) <= 22 for line in lines)

    def test_wrap_no_ellipsis_when_it_fits(self):
        lines = _wrap_lines("one two three", 22, 5)
        assert not lines[-1].endswith("...")


class TestLuckyNumber:
    def test_in_range(self):
        for sign in SIGNS:
            assert 1 <= _lucky_number(sign, "2026-09-13") <= 99

    def test_stable_within_a_day(self):
        assert _lucky_number("Aries", "2026-09-13") == _lucky_number("Aries", "2026-09-13")

    def test_changes_across_days(self):
        numbers = {_lucky_number("Aries", f"2026-09-{d:02d}") for d in range(1, 31)}
        assert len(numbers) > 1

    def test_different_across_signs(self):
        numbers = {_lucky_number(sign, "2026-09-13") for sign in SIGNS}
        assert len(numbers) > 1
        assert _lucky_number("Aries", "2026-09-13") != _lucky_number("Taurus", "2026-09-13")


class TestFormattedDisplay:
    @patch("plugins.horoscope.requests.get")
    def test_flagship_shape(self, mock_get, plugin):
        mock_get.return_value = _ok_response()

        lines = plugin.get_formatted_display()

        assert lines is not None
        assert len(lines) == 6
        assert all(len(line) <= 22 for line in lines)
        assert lines[0] == "ARIES  SEP 13"
        assert lines[1].startswith("Things are moving")

    @patch("plugins.horoscope.requests.get")
    def test_short_text_is_padded_to_six_lines(self, mock_get, plugin):
        mock_get.return_value = _ok_response(text="Be bold.")

        lines = plugin.get_formatted_display()

        assert lines == ["ARIES  SEP 13", "Be bold.", "", "", "", ""]

    @patch("plugins.horoscope.requests.get")
    def test_flagship_truncates_long_text(self, mock_get, plugin):
        mock_get.return_value = _ok_response(text="word " * 52)

        lines = plugin.get_formatted_display()

        assert len(lines) == 6
        assert lines[5].endswith("...")

    @patch("plugins.horoscope.requests.get")
    def test_note_board(self, mock_get, plugin):
        mock_get.return_value = _ok_response()
        plugin._config["sign"] = "Sagittarius"

        with plugin._bound_board(BoardContext("note", rows=3, cols=15)):
            lines = plugin.get_formatted_display()

        assert len(lines) == 3
        assert all(len(line) <= 15 for line in lines)
        assert lines[0] == "SAGITTARIUS  SE"

    @patch("plugins.horoscope.requests.get")
    def test_returns_none_on_error(self, mock_get, plugin):
        mock_get.side_effect = Exception("boom")

        assert plugin.get_formatted_display() is None


class TestManifest:
    def test_settings_enums_match_code(self):
        props = MANIFEST["settings_schema"]["properties"]
        assert props["sign"]["enum"] == list(SIGNS)
        assert props["day"]["enum"] == ["TODAY", "TOMORROW", "YESTERDAY"]

    def test_all_variables_have_descriptions_and_groups(self):
        groups = set(MANIFEST["variables"]["groups"])
        for name, meta in MANIFEST["variables"]["simple"].items():
            assert meta.get("description"), f"{name} missing description"
            assert meta["group"] in groups, f"{name} has undefined group"

    def test_color_rule_covers_every_element(self):
        rules = MANIFEST["color_rules_schema"]["element"]["default_rules"]
        assert {r["value"] for r in rules} == {e for _, e, _ in SIGNS.values()}
