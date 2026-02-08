"""Base utilities for SEC EDGAR tools."""

from datetime import date, datetime
from typing import Any, Dict, Optional

from ..core.client import EdgarClient

ToolResponse = Dict[str, Any]


class BaseTools:
    """Base class with common utilities for all tool classes."""

    def __init__(self):
        self.client = EdgarClient()

    def _parse_date(self, date_value) -> Optional[datetime]:
        """Parse a date value to datetime."""
        if date_value is None:
            return None
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())
        if isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        return None

    def _format_date(self, date_value) -> str:
        """Format a date value to ISO string."""
        if hasattr(date_value, "isoformat"):
            return date_value.isoformat()
        return str(date_value)

    def _find_filing(self, filings, accession_number: str):
        """Find a filing by accession number."""
        clean_accession = accession_number.replace("-", "")
        for filing in filings:
            if filing.accession_number.replace("-", "") == clean_accession:
                return filing
        return None

    def _build_sec_url(self, cik: str, accession_number: str) -> str:
        """Build SEC URL for a filing."""
        clean_accession = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{clean_accession}/{accession_number}.txt"

    def _create_filing_reference(
        self, filing, cik: str, form_type: str, period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a standard filing reference dict."""
        ref: Dict[str, Any] = {
            "filing_date": self._format_date(filing.filing_date),
            "accession_number": filing.accession_number,
            "form_type": form_type,
            "sec_url": self._build_sec_url(cik, filing.accession_number),
            "data_source": f"SEC EDGAR Filing {filing.accession_number}",
            "disclaimer": "All data extracted directly from SEC EDGAR filing with exact precision.",
        }
        if period_days:
            ref["period_analyzed"] = f"Last {period_days} days from {datetime.now().strftime('%Y-%m-%d')}"
        return ref
