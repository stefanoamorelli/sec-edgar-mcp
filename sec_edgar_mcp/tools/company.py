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
                ticker=getattr(company, "tickers", [None])[0] if hasattr(company, "tickers") else None,
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
            companies = [{"cik": r.cik, "name": r.name, "tickers": getattr(r, "tickers", [])} for r in results]
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
        """Extract key financial metrics from company facts."""
        metrics: Dict[str, Any] = {}

        if not hasattr(facts, "data"):
            return metrics

        facts_data = facts.data
        if "us-gaap" not in facts_data:
            return metrics

        gaap_facts = facts_data["us-gaap"]
        metric_names = [
            "Assets",
            "Liabilities",
            "StockholdersEquity",
            "Revenues",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "CashAndCashEquivalents",
            "CommonStockSharesOutstanding",
        ]

        for metric in metric_names:
            if metric not in gaap_facts:
                continue

            metric_data = gaap_facts[metric]
            if "units" not in metric_data:
                continue

            for unit_type, unit_data in metric_data["units"].items():
                if not unit_data:
                    continue

                sorted_data = sorted(unit_data, key=lambda x: x.get("end", ""), reverse=True)
                if sorted_data:
                    latest = sorted_data[0]
                    metrics[metric] = {
                        "value": float(latest.get("val", 0)),
                        "unit": unit_type,
                        "period": latest.get("end", ""),
                        "form": latest.get("form", ""),
                        "fiscal_year": latest.get("fy", ""),
                        "fiscal_period": latest.get("fp", ""),
                    }
                    break

        return metrics
