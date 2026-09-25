"""Tests for the insider-trading tools against a parsed Form 4.

The upstream ``sec_edgar_toolkit`` turns a Form 4 into an ``OwnershipForm``;
these tests feed one built from a bundled fixture through mocked filings so
the tools' output shape can be checked without network access. Regression for
stefanoamorelli/sec-edgar-mcp#111 (insider tools returning empty or partial
data).
"""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from sec_edgar_toolkit.core.ownership import OwnershipForm
from sec_edgar_toolkit.parsers import Form4Parser

from sec_edgar_mcp.tools.insider import InsiderTools

FIXTURE = Path(__file__).parent / "fixtures" / "form4_rsu_sample.xml"
ACCESSION = "0001140361-26-037020"


def _form4() -> OwnershipForm:
    return OwnershipForm(Form4Parser(FIXTURE.read_text(encoding="utf-8")).parse_all())


def _filing(obj=None, raises=None):
    filing = Mock()
    filing.filing_date = date.today()
    filing.form = "4"
    filing.accession_number = ACCESSION
    filing.company = "Apple Inc."
    filing.cik = "0000320193"
    filing.url = "https://www.sec.gov/example"
    filing.text.return_value = "SEC FORM 4 ..."
    if raises is not None:
        filing.obj.side_effect = raises
    else:
        filing.obj.return_value = obj if obj is not None else _form4()
    return filing


def _tools(*filings):
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        tools = InsiderTools()
    company = Mock(cik="0000320193", name="Apple Inc.")
    company.get_filings.return_value = list(filings)
    tools.client = Mock()
    tools.client.get_company.return_value = company
    return tools


class TestAnalyzeForm4Transactions:
    def test_rows_identify_the_security_and_derivative_flag(self):
        result = _tools(_filing()).analyze_form4_transactions("AAPL", days=30)

        assert result["success"] is True
        rows = result["detailed_transactions"][0]["transactions"]
        assert [row["security_title"] for row in rows] == [
            "Common Stock",
            "Restricted Stock Unit",
        ]
        assert [row["is_derivative"] for row in rows] == [False, True]
        assert rows[0]["ownership_type"] == "D"

    def test_non_derivative_row_keeps_amounts(self):
        result = _tools(_filing()).analyze_form4_transactions("AAPL", days=30)

        row = result["detailed_transactions"][0]["transactions"][0]
        assert row["transaction_code"] == "S"
        assert row["shares"] == 1438.0
        assert row["price_per_share"] == 330.19
        assert row["shares_owned_after"] == 32914.0
        assert row["acquisition_or_disposition"] == "D"

    def test_holdings_include_derivative_positions(self):
        result = _tools(_filing()).analyze_form4_transactions("AAPL", days=30)

        holdings = result["detailed_transactions"][0]["holdings"]
        assert {h["security_title"] for h in holdings} == {"Common Stock", "Restricted Stock Unit"}
        derivative = next(h for h in holdings if h["is_derivative"])
        assert derivative["shares_owned"] == 66600.0
        assert derivative["ownership_type"] == "D"
        assert derivative["underlying_security"] == {"title": "Common Stock", "shares": 66600.0}

    def test_owner_fields_are_reported(self):
        result = _tools(_filing()).analyze_form4_transactions("AAPL", days=30)

        row = result["detailed_transactions"][0]
        assert row["owner_name"] == "Newstead Jennifer"
        assert row["owner_title"] == "SVP, GC and Government Affairs"
        assert row["is_officer"] is True


class TestParsingErrorsAreVisible:
    def test_get_form4_details_reports_parse_failure(self):
        tools = _tools(_filing(raises=ValueError("bad xml")))

        result = tools.get_form4_details("AAPL", ACCESSION)

        assert result["success"] is True
        details = result["form4_details"]
        assert "owner" not in details
        assert "bad xml" in details["parsing_error"]

    def test_get_insider_transactions_reports_parse_failure(self):
        tools = _tools(_filing(raises=ValueError("bad xml")))

        result = tools.get_insider_transactions("AAPL", days=30)

        assert result["count"] == 1
        assert "bad xml" in result["transactions"][0]["parsing_error"]

    def test_get_insider_summary_counts_parse_failures(self):
        tools = _tools(_filing(), _filing(raises=ValueError("bad xml")))

        summary = tools.get_insider_summary("AAPL", days=30)["summary"]

        assert summary["insiders"] == ["Newstead Jennifer"]
        assert summary["unique_insiders"] == 1
        assert summary["parsing_errors"] == 1


class TestGetForm4Details:
    def test_owner_block_from_parsed_form(self):
        result = _tools(_filing()).get_form4_details("AAPL", ACCESSION)

        owner = result["form4_details"]["owner"]
        assert owner["name"] == "Newstead Jennifer"
        assert owner["is_officer"] is True
        assert owner["is_director"] is False
