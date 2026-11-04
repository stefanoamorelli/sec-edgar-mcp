"""Company-related tools for SEC EDGAR data."""

from typing import Any, Dict

from ..core.models import CompanyInfo
from ..utils.exceptions import CompanyNotFoundError
from .base import BaseTools, ToolResponse


class CompanyTools(BaseTools):
    """Tools for retrieving company information from SEC EDGAR."""

    def get_cik_by_ticker(self, ticker: str) -> ToolResponse:
        """Convert ticker symbol to CIK."""
        try:
            cik = self.client.get_cik_by_ticker(ticker)
            if cik:
                return {"success": True, "cik": cik, "ticker": ticker.upper()}
            return {"success": False, "error": f"CIK not found for ticker: {ticker}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_company_info(self, identifier: str) -> ToolResponse:
        """Get detailed company information from SEC records."""
        try:
            company = self.client.get_company(identifier)
            info = CompanyInfo(
                cik=company.cik,
                name=company.name,
                ticker=(getattr(company, "tickers", None) or [None])[0],
                sic=getattr(company, "sic", None),
                sic_description=getattr(company, "sic_description", None),
                exchange=getattr(company, "exchange", None),
                state=getattr(company, "state", None),
                fiscal_year_end=getattr(company, "fiscal_year_end", None),
            )
            return {"success": True, "company": info.to_dict()}
        except CompanyNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get company info: {e}"}

    def search_companies(self, query: str, limit: int = 10) -> ToolResponse:
        """Search for companies by name."""
        try:
            results = self.client.search_companies(query, limit)
            companies = [{"cik": r.get("cik"), "name": r.get("name"), "tickers": r.get("tickers", [])} for r in results]
            return {"success": True, "companies": companies, "count": len(companies)}
        except Exception as e:
            return {"success": False, "error": f"Failed to search companies: {e}"}

    def get_company_facts(self, identifier: str) -> ToolResponse:
        """Get company facts and financial data from XBRL."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            if not facts:
                return {"success": False, "error": "No facts available for this company"}

            metrics = self._extract_metrics(facts)
            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "metrics": metrics,
                "has_facts": bool(facts),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get company facts: {e}"}

    def _extract_metrics(self, facts) -> Dict[str, Any]:
        """Extract key financial metrics from company facts using get_fact() API.

        The edgar-tools ``EntityFacts`` object does not expose a ``.data`` dict;
        each concept is retrieved via ``get_fact(name)`` which returns a
        ``FinancialFact`` or ``None``.  Most US-GAAP concepts require the
        ``us-gaap:`` namespace prefix to be found reliably.
        """
        import warnings

        metrics: Dict[str, Any] = {}

        metric_names = [
            "Assets",
            "Liabilities",
            "StockholdersEquity",
            "Revenues",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "CashAndCashEquivalentsAtCarryingValue",
            "CommonStockSharesOutstanding",
        ]

        for metric in metric_names:
            fact = None
            for prefix in ("us-gaap:", "", "dei:"):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        fact = facts.get_fact(f"{prefix}{metric}")
                    if fact is not None:
                        break
                except Exception:
                    continue

            if fact is not None:
                metrics[metric] = {
                    "value": float(fact.numeric_value),
                    "unit": getattr(fact, "unit", "USD"),
                    "period": str(getattr(fact, "period_end", "")),
                    "form": getattr(fact, "form_type", ""),
                    "fiscal_year": getattr(fact, "fiscal_year", ""),
                    "fiscal_period": getattr(fact, "fiscal_period", ""),
                }

        return metrics
