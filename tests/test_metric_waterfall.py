from unittest.mock import Mock, patch

from sec_edgar_toolkit.compat import CompanyFacts

from sec_edgar_mcp.tools.company import CompanyTools
from sec_edgar_mcp.tools.financial import FinancialTools


def _fact(val, end, filed, fy, fp, form="10-K", start=None):
    fact = {"val": val, "end": end, "filed": filed, "fy": fy, "fp": fp, "form": form, "accn": "x"}
    if start:
        fact["start"] = start
    return fact


def _facts(us_gaap, dei=None):
    data = {"us-gaap": {name: {"units": units} for name, units in us_gaap.items()}}
    if dei:
        data["dei"] = {name: {"units": units} for name, units in dei.items()}
    return CompanyFacts({"cik": 1, "entityName": "Example Corp", "facts": data})


def _make(cls):
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        return cls()


def test_latest_filing_wins_across_concept_waterfall():
    # Revenues was abandoned in 2018; the newer tag must win despite being later in the waterfall.
    facts = _facts(
        {
            "Revenues": {"USD": [_fact(265, "2018-09-29", "2018-11-05", 2018, "FY")]},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "USD": [_fact(416, "2025-09-27", "2025-10-31", 2025, "FY")]
            },
        }
    )

    metrics = _make(CompanyTools)._extract_metrics(facts)

    assert metrics["Revenues"]["value"] == 416.0
    assert metrics["Revenues"]["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert metrics["Revenues"]["filing_date"] == "2025-10-31"
    assert metrics["Revenues"]["fiscal_year"] == 2025


def test_waterfall_order_breaks_ties_within_one_filing():
    facts = _facts(
        {
            "StockholdersEquity": {"USD": [_fact(100, "2025-09-27", "2025-10-31", 2025, "FY")]},
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": {
                "USD": [_fact(110, "2025-09-27", "2025-10-31", 2025, "FY")]
            },
        }
    )

    metrics = _make(FinancialTools)._extract_metrics_from_facts(facts, ["StockholdersEquity"])

    assert metrics["StockholdersEquity"]["value"] == 100.0


def test_latest_filing_beats_later_period_in_older_filing():
    # An amendment filed later restates the same period and must replace the original.
    facts = _facts(
        {
            "Assets": {
                "USD": [
                    _fact(500, "2025-09-27", "2025-10-31", 2025, "FY"),
                    _fact(510, "2025-09-27", "2026-01-15", 2025, "FY", form="10-K/A"),
                ]
            }
        }
    )

    metrics = _make(CompanyTools)._extract_metrics(facts)

    assert metrics["Assets"]["value"] == 510.0
    assert metrics["Assets"]["form"] == "10-K/A"


def test_unmapped_metric_uses_its_own_concept():
    facts = _facts({"Goodwill": {"USD": [_fact(7, "2025-09-27", "2025-10-31", 2025, "FY")]}})

    metrics = _make(FinancialTools)._extract_metrics_from_facts(facts, ["Goodwill", "Missing"])

    assert metrics == {
        "Goodwill": {
            "value": 7.0,
            "unit": "USD",
            "period": "2025-09-27",
            "form": "10-K",
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "concept": "Goodwill",
            "filing_date": "2025-10-31",
        }
    }


def test_compare_periods_keeps_one_full_year_value_per_fiscal_year():
    # A 10-K repeats prior-year comparatives and may include the discrete Q4 quarter.
    fy2020 = "2020-10-30"
    facts = _facts(
        {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "USD": [
                    _fact(260, "2019-09-28", fy2020, 2020, "FY", start="2018-09-30"),
                    _fact(64, "2020-09-26", fy2020, 2020, "FY", start="2020-06-28"),
                    _fact(274, "2020-09-26", fy2020, 2020, "FY", start="2019-09-29"),
                    _fact(365, "2021-09-25", "2021-10-29", 2021, "FY", start="2020-09-27"),
                ]
            }
        }
    )
    tools = _make(FinancialTools)
    company = Mock(cik=1)
    company.name = "Example Corp"
    company.get_facts.return_value = facts
    tools.client = Mock()
    tools.client.get_company.return_value = company

    result = tools.compare_periods("EXAMPLE", "Revenues", 2020, 2021)

    assert result["success"] is True
    assert [(p["year"], p["period"], p["value"]) for p in result["period_data"]] == [
        (2020, "FY", 274.0),
        (2021, "FY", 365.0),
    ]
