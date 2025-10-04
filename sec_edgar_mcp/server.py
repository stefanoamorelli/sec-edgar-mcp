import argparse
import logging
from mcp.server.fastmcp import FastMCP
from sec_edgar_mcp.tools import CompanyTools, FilingsTools, FinancialTools, InsiderTools

# Suppress INFO logs from edgar library
logging.getLogger("edgar").setLevel(logging.WARNING)

# Add system-wide instructions for deterministic responses
DETERMINISTIC_INSTRUCTIONS = """
CRITICAL: When responding to SEC filing data requests, you MUST follow these rules:

1. ONLY use data from the SEC filing provided by the tools - NO EXTERNAL KNOWLEDGE
2. ALWAYS include complete filing reference information:
   - Filing date, form type, accession number
   - Direct SEC URL for verification
   - Period/context for each data point
3. NEVER add external knowledge, estimates, interpretations, or calculations
4. NEVER analyze trends, provide context, or make comparisons not in the filing
5. Be completely deterministic - identical queries must give identical responses
6. If data is not in the filing, state "Not available in this filing" - DO NOT guess or estimate
7. ALWAYS specify the exact period/date/context for each piece of data from the XBRL
8. PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Use the exact values from the filing
9. Include clickable SEC URL so users can independently verify all data
10. State that all data comes directly from SEC EDGAR filings with no modifications

EXAMPLE RESPONSE FORMAT:
"Based on [Company]'s [Form Type] filing dated [Date] (Accession: [Number]):
- [Data point]: $37,044,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING
- [Data point]: $12,714,000,000 (Period: [Date]) - EXACT VALUE, NO ROUNDING

Source: SEC EDGAR Filing [Accession Number], extracted directly from XBRL data with no rounding or estimates.
Verify at: [SEC URL]"

CRITICAL: NEVER round numbers like "$37.0B" - always show exact values like "$37,044,000,000"

YOU ARE A FILING DATA EXTRACTION SERVICE, NOT A FINANCIAL ANALYST OR ADVISOR.
"""

# Initialize tool classes
company_tools = CompanyTools()
filings_tools = FilingsTools()
financial_tools = FinancialTools()
insider_tools = InsiderTools()


# Company Tools
def get_cik_by_ticker(ticker: str):
    """
    Get the CIK (Central Index Key) for a company based on its ticker symbol.

    Args:
        ticker: The ticker symbol of the company (e.g., "NVDA", "AAPL")

    Returns:
        Dictionary containing the CIK number or error message
    """
    return company_tools.get_cik_by_ticker(ticker)


def get_company_info(identifier: str):
    """
    Get detailed information about a company from SEC records.

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data returned from SEC records. NEVER add external information.
    - ALWAYS include any filing reference information if provided.
    - Be completely deterministic - same query should always give same response.
    - If information is not in SEC records, say "Not available in SEC records".

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Dictionary containing company information from SEC records including name, CIK, SIC, exchange, etc.
    """
    return company_tools.get_company_info(identifier)


def search_companies(query: str, limit: int = 10):
    """
    Search for companies by name.

    Args:
        query: Search query for company name
        limit: Maximum number of results to return (default: 10)

    Returns:
        Dictionary containing list of matching companies
    """
    return company_tools.search_companies(query, limit)


def get_company_facts(identifier: str):
    """
    Get company facts and key financial metrics.

    Args:
        identifier: Company ticker symbol or CIK number

    Returns:
        Dictionary containing available financial metrics
    """
    return company_tools.get_company_facts(identifier)


# Filing Tools
def get_recent_filings(identifier: str = None, form_type: str = None, days: int = 30, limit: int = 50):
    """
    Get recent SEC filings for a company or across all companies.

    Args:
        identifier: Company ticker/CIK (optional, if not provided returns all recent filings)
        form_type: Specific form type to filter (e.g., "10-K", "10-Q", "8-K")
        days: Number of days to look back (default: 30)
        limit: Maximum number of filings to return (default: 50)

    Returns:
        Dictionary containing list of recent filings
    """
    return filings_tools.get_recent_filings(identifier, form_type, days, limit)


def get_filing_content(identifier: str, accession_number: str):
    """
    Get the content of a specific SEC filing.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the filing

    Returns:
        Dictionary containing filing content and metadata
    """
    return filings_tools.get_filing_content(identifier, accession_number)


def analyze_8k(identifier: str, accession_number: str):
    """
    Analyze an 8-K filing for specific events and items.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the 8-K filing

    Returns:
        Dictionary containing analysis of 8-K items and events
    """
    return filings_tools.analyze_8k(identifier, accession_number)


def get_filing_sections(identifier: str, accession_number: str, form_type: str):
    """
    Get specific sections from a filing (e.g., business description, risk factors, MD&A).

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the filing
        form_type: The type of form (e.g., "10-K", "10-Q")

    Returns:
        Dictionary containing available sections from the filing
    """
    return filings_tools.get_filing_sections(identifier, accession_number, form_type)


# Financial Tools
def get_financials(identifier: str, statement_type: str = "all"):
    """
    Get financial statements for a company. USE THIS TOOL when users ask for:
    - Cash flow, cash flow statement, operating cash flow, investing cash flow, financing cash flow
    - Income statement, revenue, net income, earnings, profit/loss, operating income
    - Balance sheet, assets, liabilities, equity, cash and cash equivalents
    - Any financial statement data or financial metrics

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data from the returned SEC filing. NEVER add external information.
    - ALWAYS include the filing reference information with clickable SEC URL in your response.
    - NEVER estimate, calculate, or interpret data beyond what is explicitly in the filing.
    - PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Show exact values like $37,044,000,000 not $37.0B.
    - ALWAYS state the exact filing date and form type when presenting data.
    - Be completely deterministic - same query should always give same response.
    - If data is not in the filing, say "Not available in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        statement_type: Type of statement ("income", "balance", "cash", or "all")

    Returns:
        Dictionary containing financial statement data extracted directly from SEC EDGAR filings,
        including filing_reference with source URLs and disclaimer.
    """
    return financial_tools.get_financials(identifier, statement_type)


def get_segment_data(identifier: str, segment_type: str = "geographic"):
    """
    Get revenue breakdown by segments (geographic, product, etc.).

    Args:
        identifier: Company ticker symbol or CIK number
        segment_type: Type of segment analysis (default: "geographic")

    Returns:
        Dictionary containing segment revenue data
    """
    return financial_tools.get_segment_data(identifier, segment_type)


def get_key_metrics(identifier: str, metrics: list = None):
    """
    Get key financial metrics for a company.

    Args:
        identifier: Company ticker symbol or CIK number
        metrics: List of specific metrics to retrieve (optional)

    Returns:
        Dictionary containing requested financial metrics
    """
    return financial_tools.get_key_metrics(identifier, metrics)


def compare_periods(identifier: str, metric: str, start_year: int, end_year: int):
    """
    Compare a financial metric across different time periods.

    Args:
        identifier: Company ticker symbol or CIK number
        metric: The financial metric to compare (e.g., "Revenues", "NetIncomeLoss")
        start_year: Starting year for comparison
        end_year: Ending year for comparison

    Returns:
        Dictionary containing period comparison data and growth analysis
    """
    return financial_tools.compare_periods(identifier, metric, start_year, end_year)


def discover_company_metrics(identifier: str, search_term: str = None):
    """
    Discover available financial metrics for a company.

    Args:
        identifier: Company ticker symbol or CIK number
        search_term: Optional search term to filter metrics

    Returns:
        Dictionary containing list of available metrics
    """
    return financial_tools.discover_company_metrics(identifier, search_term)


def get_xbrl_concepts(identifier: str, accession_number: str = None, concepts: list = None, form_type: str = "10-K"):
    """
    ADVANCED TOOL: Extract specific XBRL concepts from a filing.

    DO NOT USE for general financial data requests. Use get_financials() instead for:
    - Cash flow statements, income statements, balance sheets
    - Revenue, net income, assets, liabilities, cash data

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY report values found in the specific SEC filing. NEVER add context from other sources.
    - ALWAYS include the filing reference information with clickable SEC URL (date, accession number, SEC URL).
    - NEVER estimate or calculate values not explicitly present in the filing.
    - PRESERVE EXACT NUMERIC PRECISION - NO ROUNDING! Show exact values like $37,044,000,000 not $37.0B.
    - ALWAYS specify the exact period/context for each value from the filing.
    - Be completely deterministic - identical queries must give identical responses.
    - If a concept is not found in the filing, state "Not found in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Optional specific filing accession number
        concepts: Optional list of specific concepts to extract (e.g., ["Revenues", "Assets"])
        form_type: Form type if no accession number provided (default: "10-K")

    Returns:
        Dictionary containing extracted XBRL concepts with filing_reference and source URLs.
    """
    return financial_tools.get_xbrl_concepts(identifier, accession_number, concepts, form_type)


def discover_xbrl_concepts(
    identifier: str, accession_number: str = None, form_type: str = "10-K", namespace_filter: str = None
):
    """
    Discover all available XBRL concepts in a filing, including company-specific ones.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: Optional specific filing accession number
        form_type: Form type if no accession number provided (default: "10-K")
        namespace_filter: Optional filter to show only concepts from specific namespace

    Returns:
        Dictionary containing all discovered XBRL concepts, namespaces, and company-specific tags
    """
    return financial_tools.discover_xbrl_concepts(identifier, accession_number, form_type, namespace_filter)


# Insider Trading Tools
def get_insider_transactions(identifier: str, form_types: list = None, days: int = 90, limit: int = 50):
    """
    Get insider trading transactions for a company from SEC filings.

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data from the returned SEC insider filings. NEVER add external information.
    - ALWAYS include the filing reference information with clickable SEC URLs in your response.
    - NEVER estimate or calculate values not explicitly present in the filings.
    - PRESERVE EXACT DATES AND VALUES - NO ROUNDING! Show exact values from filings.
    - ALWAYS specify the exact filing date and accession number for each transaction.
    - Be completely deterministic - same query should always give same response.
    - If data is not in the filing, say "Not available in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        form_types: List of form types to include (default: ["3", "4", "5"])
        days: Number of days to look back (default: 90)
        limit: Maximum number of transactions to return (default: 50)

    Returns:
        Dictionary containing insider transactions with direct SEC URLs for verification
    """
    return insider_tools.get_insider_transactions(identifier, form_types, days, limit)


def get_insider_summary(identifier: str, days: int = 180):
    """
    Get a summary of insider trading activity for a company from SEC filings.

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data from the returned SEC insider filings. NEVER add external information.
    - ALWAYS include the filing reference information with SEC URLs in your response.
    - PRESERVE EXACT COUNTS AND DATES - NO ROUNDING OR ESTIMATES!
    - Be completely deterministic - same query should always give same response.
    - If data is not in the filing, say "Not available in filings" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        days: Number of days to analyze (default: 180)

    Returns:
        Dictionary containing insider trading summary from SEC filings
    """
    return insider_tools.get_insider_summary(identifier, days)


def get_form4_details(identifier: str, accession_number: str):
    """
    Get detailed information from a specific Form 4 filing.

    Args:
        identifier: Company ticker symbol or CIK number
        accession_number: The accession number of the Form 4

    Returns:
        Dictionary containing detailed Form 4 information
    """
    return insider_tools.get_form4_details(identifier, accession_number)


def analyze_form4_transactions(identifier: str, days: int = 90, limit: int = 50):
    """
    Analyze Form 4 filings and extract detailed transaction data including insider names,
    transaction amounts, share counts, prices, and ownership details.

    USE THIS TOOL when users ask for detailed insider transaction analysis, transaction tables,
    or specific transaction amounts from Form 4 filings.

    CRITICAL INSTRUCTIONS FOR LLM RESPONSES:
    - ONLY use data from the returned SEC Form 4 filings. NEVER add external information.
    - ALWAYS include the filing reference information with clickable SEC URLs.
    - PRESERVE EXACT NUMERIC VALUES - NO ROUNDING! Show exact share counts and prices.
    - ALWAYS specify the exact filing date and accession number for each transaction.
    - Present data in table format when requested by users.
    - Be completely deterministic - same query should always give same response.
    - If data is not in the filing, say "Not available in this filing" - DO NOT guess.

    Args:
        identifier: Company ticker symbol or CIK number
        days: Number of days to look back (default: 90)
        limit: Maximum number of filings to analyze (default: 50)

    Returns:
        Dictionary containing detailed Form 4 transaction analysis with exact values from SEC filings
    """
    return insider_tools.analyze_form4_transactions(identifier, days, limit)


def analyze_insider_sentiment(identifier: str, months: int = 6):
    """
    Analyze insider trading sentiment and trends over time.

    Args:
        identifier: Company ticker symbol or CIK number
        months: Number of months to analyze (default: 6)

    Returns:
        Dictionary containing sentiment analysis and trends
    """
    return insider_tools.analyze_insider_sentiment(identifier, months)


# Utility Tools
def get_recommended_tools(form_type: str):
    """
    Get recommended tools for analyzing specific form types.

    Args:
        form_type: The SEC form type (e.g., "10-K", "8-K", "4")

    Returns:
        Dictionary containing recommended tools and usage tips
    """
    recommendations = {
        "10-K": {
            "tools": ["get_financials", "get_filing_sections", "get_segment_data", "get_key_metrics"],
            "description": "Annual report with comprehensive business and financial information",
            "tips": [
                "Use get_financials to extract financial statements",
                "Use get_filing_sections to read business description and risk factors",
                "Use get_segment_data for geographic/product revenue breakdown",
            ],
        },
        "10-Q": {
            "tools": ["get_financials", "get_filing_sections", "compare_periods"],
            "description": "Quarterly report with unaudited financial statements",
            "tips": [
                "Use get_financials for quarterly financial data",
                "Use compare_periods to analyze quarter-over-quarter trends",
            ],
        },
        "8-K": {
            "tools": ["analyze_8k", "get_filing_content"],
            "description": "Current report for material events",
            "tips": [
                "Use analyze_8k to identify specific events reported",
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
                "Use get_insider_transactions for recent trading activity overview",
                "Use analyze_form4_transactions for detailed transaction analysis and tables",
                "Use analyze_insider_sentiment to understand trading patterns",
            ],
        },
        "DEF 14A": {
            "tools": ["get_filing_content", "get_filing_sections"],
            "description": "Proxy statement with executive compensation and governance",
            "tips": ["Look for executive compensation tables", "Review shareholder proposals and board information"],
        },
    }

    form_type_upper = form_type.upper()
    if form_type_upper in recommendations:
        return {"success": True, "form_type": form_type_upper, "recommendations": recommendations[form_type_upper]}
    else:
        return {
            "success": True,
            "form_type": form_type_upper,
            "message": "No specific recommendations available for this form type",
            "general_tools": ["get_filing_content", "get_recent_filings"],
        }


def register_tools(mcp):
    """Register all tools with the MCP server."""
    # Company Tools
    mcp.add_tool(get_cik_by_ticker)
    mcp.add_tool(get_company_info)
    mcp.add_tool(search_companies)
    mcp.add_tool(get_company_facts)

    # Filing Tools
    mcp.add_tool(get_recent_filings)
    mcp.add_tool(get_filing_content)
    mcp.add_tool(analyze_8k)
    mcp.add_tool(get_filing_sections)

    # Financial Tools
    mcp.add_tool(get_financials)
    mcp.add_tool(get_segment_data)
    mcp.add_tool(get_key_metrics)
    mcp.add_tool(compare_periods)
    mcp.add_tool(discover_company_metrics)
    mcp.add_tool(get_xbrl_concepts)
    mcp.add_tool(discover_xbrl_concepts)

    # Insider Trading Tools
    mcp.add_tool(get_insider_transactions)
    mcp.add_tool(get_insider_summary)
    mcp.add_tool(get_form4_details)
    mcp.add_tool(analyze_form4_transactions)
    mcp.add_tool(analyze_insider_sentiment)

    # Utility Tools
    mcp.add_tool(get_recommended_tools)


def main():
    """Main entry point for the MCP server."""

    parser = argparse.ArgumentParser(description="SEC EDGAR MCP Server - Access SEC filings and financial data")
    parser.add_argument("--transport", default="stdio", help="Transport method")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9870, help="Port to bind to (default: 9870)")
    args = parser.parse_args()

    # Initialize MCP server with appropriate configuration
    if args.transport == "streamable-http":
        mcp = FastMCP("SEC EDGAR MCP", host=args.host, port=args.port, dependencies=["edgartools"])
    else:
        mcp = FastMCP("SEC EDGAR MCP", dependencies=["edgartools"])

    # Register all tools after initialization
    register_tools(mcp)

    # Run the MCP server
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
