"""Compatibility tests for edgartools EntityFacts APIs."""

from dataclasses import dataclass
from datetime import date
from unittest.mock import patch

from sec_edgar_mcp.tools.financial import FinancialTools


@dataclass
class FakeFact:
    numeric_value: float
    unit: str
    period_end: date
    form_type: str
    fiscal_year: int
    fiscal_period: str


class FakeFacts:
    def __init__(self, series_by_metric):
        self._series_by_metric = series_by_metric

    def get_fact(self, metric):
        series = self._series_by_metric.get(metric) or []
        return series[-1] if series else None

    def time_series(self, metric, periods=100):
        return self._series_by_metric.get(metric) or []


class FakeCompany:
    cik = "0000320193"
    name = "Apple Inc."

    def __init__(self, facts):
        self._facts = facts

    def get_facts(self):
        return self._facts


def _make_tools(facts):
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        tools = FinancialTools()
    tools.client.get_company.return_value = FakeCompany(facts)
    return tools


def test_compare_periods_accepts_financial_fact_series_without_empty_attr():
    facts = FakeFacts(
        {
            "Revenues": [
                FakeFact(100.0, "USD", date(2022, 9, 24), "10-K", 2022, "FY"),
                FakeFact(125.0, "USD", date(2023, 9, 30), "10-K", 2023, "FY"),
            ]
        }
    )
    tools = _make_tools(facts)

    result = tools.compare_periods("AAPL", "Revenues", 2022, 2023)

    assert result["success"] is True
    assert [row["year"] for row in result["period_data"]] == [2022, 2023]
    assert result["analysis"]["total_growth_percent"] == 25.0


def test_get_key_metrics_uses_get_fact_when_raw_data_is_unavailable():
    facts = FakeFacts(
        {
            "Revenues": [
                FakeFact(383_285_000_000.0, "USD", date(2023, 9, 30), "10-K", 2023, "FY"),
            ]
        }
    )
    tools = _make_tools(facts)

    result = tools.get_key_metrics("AAPL", ["Revenues"])

    assert result["success"] is True
    assert result["metrics"]["Revenues"]["value"] == 383_285_000_000.0
    assert result["metrics"]["Revenues"]["period"] == "2023-09-30"


def test_discover_company_metrics_uses_time_series_without_dataframe_empty():
    facts = FakeFacts(
        {
            "Assets": [
                FakeFact(350.0, "USD", date(2022, 9, 24), "10-K", 2022, "FY"),
                FakeFact(352.0, "USD", date(2023, 9, 30), "10-K", 2023, "FY"),
            ]
        }
    )
    tools = _make_tools(facts)

    result = tools.discover_company_metrics("AAPL", "Assets")

    assert result["success"] is True
    assert result["available_metrics"] == [{"name": "Assets", "count": 2, "latest_period": "2023-09-30"}]
