"""SEC EDGAR MCP Server - Access SEC filings and financial data via MCP protocol."""

import argparse
import logging
from mcp.server.fastmcp import FastMCP

from sec_edgar_mcp.tools import CompanyTools, FilingsTools, FinancialTools, InsiderTools

logging.getLogger("edgar").setLevel(logging.WARNING)

# Tool instances
company_tools = CompanyTools()
filings_tools = FilingsTools()
financial_tools = FinancialTools()
insider_tools = InsiderTools()

# Base instructions for financial data tools
_FINANCIAL_INSTRUCTIONS = """
<instructions>
  <data-integrity>
    Use only data returned by this tool. Do not add external information or estimates.
  </data-integrity>
  <precision>
    Preserve exact numeric precision from the data. Do not round numbers.
  </precision>
  <verification>
    Always include the SEC filing URL so users can verify the source.
  </verification>
  <context>
    State the filing date and form type when presenting data.
  </context>
</instructions>
"""


# =============================================================================
# Company Tools
# =============================================================================


def get_cik_by_ticker(ticker: str):
    """
    Convert a stock ticker symbol to its SEC CIK (Central Index Key).

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "NVDA", "MSFT")

    Returns:
        CIK number for use with other SEC EDGAR tools.
    """
    return company_tools.get_cik_by_ticker(ticker)


def get_company_info(identifier: str):
    """
    Retrieve company information from SEC records.

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Company details including name, CIK, SIC code, exchange, and fiscal year end.
    """
    return company_tools.get_company_info(identifier)


def search_companies(query: str, limit: int = 10):
    """
    Search for companies by name in SEC records.

    Args:
        query: Company name search query
        limit: Maximum results to return (default: 10)

    Returns:
        List of matching companies with CIK and ticker information.
    """
    return company_tools.search_companies(query, limit)


def get_company_facts(identifier: str):
    f"""
    Retrieve all available XBRL facts for a company from SEC filings.

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Available financial metrics with most recent values.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return company_tools.get_company_facts(identifier)


# =============================================================================
# Filing Tools
# =============================================================================


def get_recent_filings(identifier: str = None, form_type: str = None, days: int = 30, limit: int = 40):
    """
    Get recent SEC filings for a company or across all filers.

    Args:
        identifier: Company ticker/CIK (optional, omit for all recent filings)
        form_type: Filter by form type (e.g., "10-K", "10-Q", "8-K", "4")
        days: Number of days to look back (default: 30)
        limit: Maximum filings to return (default: 50)

    Returns:
        List of filings with dates, form types, accession numbers, and SEC URLs.
    """
    return filings_tools.get_recent_filings(identifier, form_type, days, limit)


def get_filing_content(identifier: str, accession_number: str, offset: int = 0, max_chars: int = 50000):
    """
    Get the content of a specific SEC filing with paging support.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the filing
        offset: Character offset into the filing content (default: 0)
        max_chars: Maximum number of characters to return (default: 50000)

    Returns:
        Dictionary containing filing content page and pagination metadata
    """
    return filings_tools.get_filing_content(identifier, accession_number, offset, max_chars)


def analyze_8k(identifier: str, accession_number: str):
    """
    Analyze an 8-K current report for material events.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The 8-K filing accession number

    Returns:
        Analysis of reported items:
        <items>
          <item code="1.01">Material agreements</item>
          <item code="2.02">Results of operations (earnings)</item>
          <item code="5.02">Officer/director changes</item>
          <item code="7.01">Regulation FD disclosures</item>
          <item code="8.01">Other material events</item>
        </items>
    """
    return filings_tools.analyze_8k(identifier, accession_number)


def get_filing_sections(identifier: str, accession_number: str, form_type: str):
    """
    Extract specific sections from 10-K or 10-Q filings.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Filing accession number
        form_type: Form type ("10-K" or "10-Q")

    Returns:
        Extracted sections including business description, risk factors, and MD&A.
    """
    return filings_tools.get_filing_sections(identifier, accession_number, form_type)


# =============================================================================
# Financial Tools
# =============================================================================


def get_financials(identifier: str, statement_type: str = "all"):
    f"""
    Extract financial statements from the latest SEC filing.

    <when-to-use>
      Use this tool when users ask about income statements, revenue, net income,
      earnings, profit margins, balance sheets, assets, liabilities, equity, debt,
      cash flow statements, operating cash flow, free cash flow, or capex.
    </when-to-use>

    Args:
        identifier: Company ticker symbol or CIK number
        statement_type: "income", "balance", "cash", or "all" (default: "all")

    Returns:
        Financial statement data with exact values from XBRL.
    {_FINANCIAL_INSTRUCTIONS}
    <presentation>
      <formatting>Format large numbers with appropriate scale (millions/billions).</formatting>
      <comparison>Include year-over-year comparisons when multiple periods are available.</comparison>
      <period>Note the fiscal period end date.</period>
    </presentation>
    """
    return financial_tools.get_financials(identifier, statement_type)


def get_segment_data(identifier: str, segment_type: str = "geographic"):
    f"""
    Get revenue breakdown by business or geographic segments.

    Args:
        identifier: Company ticker symbol or CIK number
        segment_type: Segment type (default: "geographic")

    Returns:
        Segment revenue data from the latest 10-K filing.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return financial_tools.get_segment_data(identifier, segment_type)


def get_key_metrics(identifier: str, metrics: list = None):
    f"""
    Retrieve specific financial metrics from SEC filings.

    Args:
        identifier: Company ticker symbol or CIK number
        metrics: List of XBRL concepts (default: common metrics like Revenue, NetIncome)

    Returns:
        Requested metrics with values, periods, and filing references.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return financial_tools.get_key_metrics(identifier, metrics)


def compare_periods(identifier: str, metric: str, start_year: int, end_year: int):
    f"""
    Compare a financial metric across multiple fiscal years.

    Args:
        identifier: Company ticker symbol or CIK number
        metric: XBRL concept name (e.g., "Revenues", "NetIncomeLoss")
        start_year: Starting fiscal year
        end_year: Ending fiscal year

    Returns:
        Year-over-year comparison with growth rates and CAGR.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return financial_tools.compare_periods(identifier, metric, start_year, end_year)


def discover_company_metrics(identifier: str, search_term: str = None):
    """
    Discover what financial metrics are available for a company.

    <tip>Use this tool to find available XBRL concepts before using get_key_metrics.</tip>

    Args:
        identifier: Company ticker symbol or CIK number
        search_term: Filter metrics by name (optional)

    Returns:
        List of available XBRL concepts with data counts.
    """
    return financial_tools.discover_company_metrics(identifier, search_term)


def get_xbrl_concepts(
    identifier: str,
    accession_number: str = None,
    concepts: list = None,
    form_type: str = "10-K",
):
    f"""
    Extract specific XBRL concepts from a filing.

    <note>For general financial data, prefer get_financials() instead.
    This tool is for advanced users needing specific XBRL concepts.</note>

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Specific filing accession number (optional)
        concepts: List of XBRL concepts to extract (e.g., ["Revenues", "Assets"])
        form_type: Form type if no accession number provided (default: "10-K")

    Returns:
        Extracted XBRL concept values with exact precision.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return financial_tools.get_xbrl_concepts(identifier, accession_number, concepts, form_type)


def discover_xbrl_concepts(
    identifier: str,
    accession_number: str = None,
    form_type: str = "10-K",
    namespace_filter: str = None,
):
    """
    Discover all XBRL concepts available in a filing.

    <tip>Use this to explore available data before extracting specific concepts.</tip>

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Specific filing accession number (optional)
        form_type: Form type if no accession number provided (default: "10-K")
        namespace_filter: Filter by namespace (e.g., "us-gaap")

    Returns:
        All discovered concepts, namespaces, and sample values.
    """
    return financial_tools.discover_xbrl_concepts(identifier, accession_number, form_type, namespace_filter)


# =============================================================================
# Insider Trading Tools
# =============================================================================


def get_insider_transactions(identifier: str, form_types: list = None, days: int = 90, limit: int = 50):
    f"""
    Get insider trading transactions from Forms 3, 4, and 5.

    <when-to-use>
      Use this tool when users ask about insider buying/selling, executive stock
      transactions, director share purchases, or 10% owner activity.
    </when-to-use>

    Args:
        identifier: Company ticker symbol or CIK number
        form_types: List of form types (default: ["3", "4", "5"])
        days: Number of days to look back (default: 90)
        limit: Maximum transactions to return (default: 50)

    Returns:
        Insider transactions with owner names, titles, and SEC filing URLs.
    {_FINANCIAL_INSTRUCTIONS}
    <presentation>
      <insider>Clearly identify the insider (name, title, relationship).</insider>
      <direction>Distinguish between purchases (acquisitions) and sales (dispositions).</direction>
      <dates>Note transaction dates vs filing dates.</dates>
    </presentation>
    """
    return insider_tools.get_insider_transactions(identifier, form_types, days, limit)


def get_insider_summary(identifier: str, days: int = 180):
    """
    Get a summary of insider trading activity.

    Args:
        identifier: Company ticker symbol or CIK number
        days: Number of days to analyze (default: 180)

    Returns:
        Summary with filing counts by form type, unique insiders, and recent activity.
    """
    return insider_tools.get_insider_summary(identifier, days)


def get_form4_details(identifier: str, accession_number: str):
    f"""
    Get detailed information from a specific Form 4 filing.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Form 4 accession number

    Returns:
        Detailed Form 4 data including owner info, transactions, and holdings.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return insider_tools.get_form4_details(identifier, accession_number)


def analyze_form4_transactions(identifier: str, days: int = 90, limit: int = 50):
    f"""
    Extract detailed transaction data from Form 4 filings.

    <tip>Use this for comprehensive insider transaction analysis including
    share counts, prices, and post-transaction ownership.</tip>

    Args:
        identifier: Company ticker symbol or CIK number
        days: Number of days to look back (default: 90)
        limit: Maximum filings to analyze (default: 50)

    Returns:
        Detailed transaction data with exact values from SEC filings.
    {_FINANCIAL_INSTRUCTIONS}
    """
    return insider_tools.analyze_form4_transactions(identifier, days, limit)


def analyze_insider_sentiment(identifier: str, months: int = 6):
    """
    Analyze insider trading patterns and frequency.

    Args:
        identifier: Company ticker symbol or CIK number
        months: Number of months to analyze (default: 6)

    Returns:
        Filing frequency analysis (high/moderate/low) and recent activity summary.

    <note>This provides frequency analysis only. For buy/sell sentiment,
    use analyze_form4_transactions to examine actual transaction details.</note>
    """
    return insider_tools.analyze_insider_sentiment(identifier, months)


# =============================================================================
# Utility Tools
# =============================================================================


FORM_RECOMMENDATIONS = {
    "10-K": {
        "tools": ["get_financials", "get_filing_sections", "get_segment_data", "get_key_metrics"],
        "description": "Annual report with comprehensive business and financial information",
        "tips": [
            "Use get_financials for financial statements",
            "Use get_filing_sections for business description and risk factors",
            "Use get_segment_data for revenue breakdown",
        ],
    },
    "10-Q": {
        "tools": ["get_financials", "get_filing_sections", "compare_periods"],
        "description": "Quarterly report with unaudited financial statements",
        "tips": [
            "Use get_financials for quarterly data",
            "Use compare_periods for quarter-over-quarter trends",
        ],
    },
    "8-K": {
        "tools": ["analyze_8k", "get_filing_content"],
        "description": "Current report for material events",
        "tips": [
            "Use analyze_8k to identify reported events",
            "Check for press releases and material agreements",
        ],
    },
    "4": {
        "tools": [
            "get_insider_transactions",
            "analyze_form4_transactions",
            "get_form4_details",
            "analyze_insider_sentiment",
        ],
        "description": "Statement of changes in beneficial ownership",
        "tips": [
            "Use get_insider_transactions for activity overview",
            "Use analyze_form4_transactions for detailed analysis",
            "Use analyze_insider_sentiment for trading patterns",
        ],
    },
    "DEF 14A": {
        "tools": ["get_filing_content", "get_filing_sections"],
        "description": "Proxy statement with executive compensation and governance",
        "tips": [
            "Look for executive compensation tables",
            "Review shareholder proposals and board information",
        ],
    },
}


def get_recommended_tools(form_type: str):
    """
    Get recommended tools for analyzing a specific SEC form type.

    Args:
        form_type: SEC form type (e.g., "10-K", "8-K", "4", "DEF 14A")

    Returns:
        Recommended tools and usage tips for the form type.
    """
    form_upper = form_type.upper()
    if form_upper in FORM_RECOMMENDATIONS:
        return {
            "success": True,
            "form_type": form_upper,
            "recommendations": FORM_RECOMMENDATIONS[form_upper],
        }
    return {
        "success": True,
        "form_type": form_upper,
        "message": "No specific recommendations for this form type",
        "general_tools": ["get_filing_content", "get_recent_filings"],
    }


# =============================================================================
# Server Setup
# =============================================================================


def register_tools(mcp: FastMCP):
    """Register all tools with the MCP server."""
    tools = [
        # Company
        get_cik_by_ticker,
        get_company_info,
        search_companies,
        get_company_facts,
        # Filings
        get_recent_filings,
        get_filing_content,
        analyze_8k,
        get_filing_sections,
        # Financial
        get_financials,
        get_segment_data,
        get_key_metrics,
        compare_periods,
        discover_company_metrics,
        get_xbrl_concepts,
        discover_xbrl_concepts,
        # Insider Trading
        get_insider_transactions,
        get_insider_summary,
        get_form4_details,
        analyze_form4_transactions,
        analyze_insider_sentiment,
        # Utility
        get_recommended_tools,
    ]
    for tool in tools:
        mcp.add_tool(tool)


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="SEC EDGAR MCP Server - Access SEC filings and financial data")
    parser.add_argument("--transport", default="stdio", help="Transport method")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9870, help="Port to bind to (default: 9870)")
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp = FastMCP("SEC EDGAR MCP", host=args.host, port=args.port, dependencies=["edgartools"])
    else:
        mcp = FastMCP("SEC EDGAR MCP", dependencies=["edgartools"])

    register_tools(mcp)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
