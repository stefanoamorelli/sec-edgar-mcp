"""Period selection and concept fallback in the company-facts tools.

The company-facts API tags every value with the fiscal year of the *filing*
that reported it (``fy``), not of the period it covers, and a 10-K carries
prior-year comparatives and quarterly rows under that same ``fy``. These tests
feed a facts object shaped like Apple's real data through ``compare_periods``
and ``get_key_metrics`` and check that annual values are picked by period and
that revenue falls through to the post-ASC 606 concept. Regression for
stefanoamorelli/sec-edgar-mcp#111 (item 1).
"""

from unittest.mock import Mock, patch

import pandas as pd

from sec_edgar_mcp.tools.financial import FinancialTools

COLUMNS = ["fy", "fp", "value", "unit", "form", "end", "start", "filed", "accn"]


def _row(fy, fp, value, form, end, start, filed):
    return {
        "fy": fy,
        "fp": fp,
        "value": value,
        "unit": "USD",
        "form": form,
        "end": end,
        "start": start,
        "filed": filed,
        "accn": f"{filed}-x",
    }


# Apple stopped tagging ``Revenues`` after ASC 606; only old rows remain.
OLD_REVENUES = [
    _row(2018, "FY", 215_639_000_000, "10-K", "2016-09-24", "2015-09-27", "2018-11-05"),
    _row(2018, "FY", 265_595_000_000, "10-K", "2018-09-29", "2017-10-01", "2018-11-05"),
]

# The post-ASC 606 concept: each 10-K reports the year plus two comparatives,
# the 10-Qs report quarters and year-to-date, all tagged with the filing's fy.
ASC606 = [
    # FY2021 10-K (filed 2021-10-29): FY2019, FY2020 comparatives and FY2021
    _row(2021, "FY", 260_174_000_000, "10-K", "2019-09-28", "2018-09-30", "2021-10-29"),
    _row(2021, "FY", 274_515_000_000, "10-K", "2020-09-26", "2019-09-29", "2021-10-29"),
    _row(2021, "FY", 365_817_000_000, "10-K", "2021-09-25", "2020-09-27", "2021-10-29"),
    # FY2021 10-Q rows: a quarter and a year-to-date value share fy/fp
    _row(2021, "Q2", 89_584_000_000, "10-Q", "2021-03-27", "2020-12-27", "2021-04-29"),
    _row(2021, "Q2", 201_023_000_000, "10-Q", "2021-03-27", "2020-09-27", "2021-04-29"),
    # FY2022 10-K
    _row(2022, "FY", 365_817_000_000, "10-K", "2021-09-25", "2020-09-27", "2022-10-28"),
    _row(2022, "FY", 394_328_000_000, "10-K", "2022-09-24", "2021-09-26", "2022-10-28"),
    # FY2023 10-K restates FY2022 by a dollar to prove the latest filing wins
    _row(2023, "FY", 394_328_000_001, "10-K", "2022-09-24", "2021-09-26", "2023-11-03"),
    _row(2023, "FY", 383_285_000_000, "10-K", "2023-09-30", "2022-09-25", "2023-11-03"),
    # FY2024 10-Q (fy outside the range, period inside it is not: excluded)
    _row(2024, "Q1", 119_575_000_000, "10-Q", "2023-12-30", "2023-10-01", "2024-02-02"),
]

NET_INCOME = [
    _row(2023, "FY", 94_680_000_000, "10-K", "2021-09-25", "2020-09-27", "2023-11-03"),
    _row(2023, "FY", 99_803_000_000, "10-K", "2022-09-24", "2021-09-26", "2023-11-03"),
    _row(2023, "FY", 96_995_000_000, "10-K", "2023-09-30", "2022-09-25", "2023-11-03"),
    # The latest 10-Q reports the nine-month total and the discrete quarter
    # under the same end date and filing date.
    _row(2026, "Q3", 101_464_000_000, "10-Q", "2026-06-27", "2025-09-28", "2026-07-31"),
    _row(2026, "Q3", 29_789_000_000, "10-Q", "2026-06-27", "2026-03-29", "2026-07-31"),
]

# Instant concept: no start date, one balance per year end.
ASSETS = [
    _row(2022, "FY", 351_002_000_000, "10-K", "2021-09-25", None, "2022-10-28"),
    _row(2022, "FY", 352_755_000_000, "10-K", "2022-09-24", None, "2022-10-28"),
    _row(2023, "FY", 352_583_000_000, "10-K", "2023-09-30", None, "2023-11-03"),
]

CASH_AT_CARRYING_VALUE = [
    _row(2023, "FY", 29_965_000_000, "10-K", "2023-09-30", None, "2023-11-03"),
]


class FakeFacts:
    """Mimics ``sec_edgar_toolkit.core.facts.CompanyFacts.get_fact``."""

    def __init__(self, concepts):
        self._concepts = concepts

    def __bool__(self):
        return True

    def get_fact(self, concept):
        rows = self._concepts.get(concept)
        if not rows:
            return None
        frame = pd.DataFrame(rows, columns=COLUMNS)
        return frame.sort_values(by=["end", "filed"]).reset_index(drop=True)


def _tools(concepts):
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        tools = FinancialTools()
    company = Mock(cik="0000320193", name="Apple Inc.")
    company.get_facts.return_value = FakeFacts(concepts)
    tools.client = Mock()
    tools.client.get_company.return_value = company
    return tools


APPLE = {
    "Revenues": OLD_REVENUES,
    "RevenueFromContractWithCustomerExcludingAssessedTax": ASC606,
    "NetIncomeLoss": NET_INCOME,
    "Assets": ASSETS,
    "CashAndCashEquivalentsAtCarryingValue": CASH_AT_CARRYING_VALUE,
}


class TestComparePeriods:
    def test_revenues_falls_through_to_the_asc606_concept(self):
        result = _tools(APPLE).compare_periods("AAPL", "Revenues", 2021, 2023)

        assert result["success"] is True
        assert result["metric"] == "Revenues"
        assert result["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax"

    def test_one_annual_value_per_fiscal_year_selected_by_period(self):
        result = _tools(APPLE).compare_periods("AAPL", "Revenues", 2021, 2023)

        rows = result["period_data"]
        assert [r["year"] for r in rows] == [2021, 2022, 2023]
        assert [r["value"] for r in rows] == [
            365_817_000_000.0,
            394_328_000_001.0,  # the FY2023 10-K restatement wins over the FY2022 10-K
            383_285_000_000.0,
        ]
        assert all(r["period"] == "FY" and r["form"] == "10-K" for r in rows)
        assert rows[0]["end"] == "2021-09-25"

    def test_growth_spans_the_requested_years_only(self):
        result = _tools(APPLE).compare_periods("AAPL", "Revenues", 2021, 2023)

        analysis = result["analysis"]
        assert analysis["periods_found"] == 3
        assert analysis["start_value"] == 365_817_000_000.0
        assert analysis["end_value"] == 383_285_000_000.0
        assert analysis["total_growth_percent"] == round((383_285 / 365_817 - 1) * 100, 2)

    def test_instant_concept_uses_year_end_balances(self):
        result = _tools(APPLE).compare_periods("AAPL", "Assets", 2021, 2023)

        assert [(r["year"], r["value"]) for r in result["period_data"]] == [
            (2021, 351_002_000_000.0),
            (2022, 352_755_000_000.0),
            (2023, 352_583_000_000.0),
        ]

    def test_direct_concept_is_not_rewritten(self):
        result = _tools(APPLE).compare_periods("AAPL", "NetIncomeLoss", 2022, 2023)

        assert result["concept"] == "NetIncomeLoss"
        assert [r["year"] for r in result["period_data"]] == [2022, 2023]

    def test_no_annual_data_in_range_is_an_error_not_zero_growth(self):
        result = _tools(APPLE).compare_periods("AAPL", "Revenues", 2010, 2012)

        assert result["success"] is False
        assert "Revenues" in result["error"]
        assert "RevenueFromContractWithCustomerExcludingAssessedTax" in result["error"]

    def test_unknown_concept_is_an_error(self):
        result = _tools(APPLE).compare_periods("AAPL", "NoSuchConcept", 2021, 2023)

        assert result["success"] is False
        assert "NoSuchConcept" in result["error"]


class TestGetKeyMetrics:
    def test_revenue_picks_the_concept_with_the_newest_period(self):
        result = _tools(APPLE).get_key_metrics("AAPL", ["Revenues"])

        revenue = result["metrics"]["Revenues"]
        assert revenue["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
        assert revenue["period"] == "2023-12-30"
        assert revenue["value"] == 119_575_000_000.0
        assert revenue["fiscal_period"] == "Q1"

    def test_cash_falls_through_to_the_carrying_value_concept(self):
        result = _tools(APPLE).get_key_metrics("AAPL", ["CashAndCashEquivalents"])

        cash = result["metrics"]["CashAndCashEquivalents"]
        assert cash["concept"] == "CashAndCashEquivalentsAtCarryingValue"
        assert cash["value"] == 29_965_000_000.0
        assert result["found_metrics"] == ["CashAndCashEquivalents"]

    def test_latest_value_is_the_discrete_quarter_not_year_to_date(self):
        result = _tools(APPLE).get_key_metrics("AAPL", ["NetIncomeLoss"])

        latest = result["metrics"]["NetIncomeLoss"]
        assert latest["period"] == "2026-06-27"
        assert latest["start"] == "2026-03-29"
        assert latest["value"] == 29_789_000_000.0

    def test_missing_metric_is_left_out(self):
        result = _tools(APPLE).get_key_metrics("AAPL", ["NoSuchConcept", "Assets"])

        assert result["found_metrics"] == ["Assets"]
        assert result["metrics"]["Assets"]["concept"] == "Assets"
