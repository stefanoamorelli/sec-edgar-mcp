from typing import Optional
from edgar import Company, set_identity, find_company, search
from ..utils.cache import TickerCache
from ..utils.exceptions import CompanyNotFoundError
from ..config import initialize_config
import edgar


class EdgarClient:
    """Wrapper around edgar-tools for consistent API access."""

    def __init__(self):
        self._user_agent = initialize_config()
        # Set identity for edgar-tools
        set_identity(self._user_agent)
        # Also set the default user agent
        edgar.set_identity(self._user_agent)
        self._ticker_cache = TickerCache(self._user_agent)

    def get_company(self, identifier: str) -> Company:
        """Get a Company object by ticker or CIK."""
        try:
            # First try as CIK (if it's all digits)
            if identifier.isdigit() or (identifier.startswith("000") and len(identifier) == 10):
                return Company(identifier)

            # For tickers, always convert to CIK first
            cik = self.get_cik_by_ticker(identifier)
            if cik:
                return Company(cik)

            # Last resort - try direct lookup
            return Company(identifier)
        except Exception:
            raise CompanyNotFoundError(f"Company '{identifier}' not found")

    def get_cik_by_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK by ticker symbol."""
        # Try the cache first
        cik = self._ticker_cache.get_cik(ticker)
        if cik:
            return str(cik).zfill(10)

        # Try to get via Company object
        try:
            company = Company(ticker)
            return company.cik
        except Exception:
            return None

    def search_companies(self, query: str, limit: int = 10) -> list:
        """Search for companies by name."""
        try:
            # Use edgar-tools search functionality
            results = search(query)

            # Convert to list format and limit results
            companies = []
            for i, result in enumerate(results):
                if i >= limit:
                    break
                companies.append({"cik": result.cik, "name": result.name, "tickers": getattr(result, "tickers", [])})

            return companies
        except Exception:
            # Fallback to find_company if search fails
            try:
                company = find_company(query)
                if company:
                    return [{"cik": company.cik, "name": company.name, "tickers": getattr(company, "tickers", [])}]
            except Exception:
                pass

            return []
