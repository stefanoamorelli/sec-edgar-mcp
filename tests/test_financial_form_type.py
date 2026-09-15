from unittest.mock import Mock, patch

from sec_edgar_mcp.tools.financial import FinancialTools


def _make_tools():
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        return FinancialTools()


def test_get_financials_uses_requested_form():
    tools = _make_tools()
    filing = Mock()
    company = Mock(cik="0000000000", name="Example Corp")
    company.get_filings.return_value.latest.return_value = filing
    tools.client = Mock()
    tools.client.get_company.return_value = company
    tools._extract_financials = Mock(return_value=object())
    tools._get_xbrl = Mock(return_value=None)
    tools._extract_statements = Mock(return_value={})
    tools._create_filing_reference = Mock(return_value={})

    result = tools.get_financials("EXAMPLE", form_type="10-K")

    assert result["success"] is True
    assert result["form_type"] == "10-K"
    company.get_filings.assert_called_once_with(form="10-K")


def test_get_financials_reports_missing_requested_form():
    tools = _make_tools()
    company = Mock()
    company.get_filings.return_value.latest.return_value = None
    tools.client = Mock()
    tools.client.get_company.return_value = company

    result = tools.get_financials("EXAMPLE", form_type="10-K")

    assert result == {"success": False, "error": "No 10-K filings found"}


def test_get_financials_rejects_other_forms():
    tools = _make_tools()

    result = tools.get_financials("EXAMPLE", form_type="8-K")

    assert result == {"success": False, "error": 'form_type must be "10-K" or "10-Q"'}
