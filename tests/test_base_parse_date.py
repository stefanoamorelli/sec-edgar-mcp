"""Tests for BaseTools._parse_date."""

from datetime import date, datetime
from unittest.mock import patch

from sec_edgar_mcp.tools.base import BaseTools


def _make_base():
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        return BaseTools()


def test_parse_date_returns_none_for_non_iso_string():
    # Regression: upstream edgartools can return a concatenation of filer
    # names (e.g. from multi-filer Schedule 13D/G homepages) instead of a
    # period string. _parse_date must degrade gracefully rather than raise.
    base = _make_base()
    garbage = "FILER ONE LLCFILER TWO INC.FILER THREE LP"
    assert base._parse_date(garbage) is None


def test_parse_date_returns_none_for_empty_string():
    base = _make_base()
    assert base._parse_date("") is None


def test_parse_date_parses_iso_string():
    base = _make_base()
    result = base._parse_date("2024-05-01")
    assert result == datetime(2024, 5, 1)


def test_parse_date_parses_iso_string_with_z():
    base = _make_base()
    result = base._parse_date("2024-05-01T12:00:00Z")
    assert result is not None
    assert result.year == 2024 and result.month == 5 and result.day == 1


def test_parse_date_passes_through_datetime():
    base = _make_base()
    dt = datetime(2024, 1, 1, 12, 0, 0)
    assert base._parse_date(dt) is dt


def test_parse_date_converts_date_to_datetime():
    base = _make_base()
    result = base._parse_date(date(2024, 1, 1))
    assert result == datetime(2024, 1, 1)


def test_parse_date_none_returns_none():
    base = _make_base()
    assert base._parse_date(None) is None
