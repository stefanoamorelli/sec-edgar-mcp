"""Insider trading tools for SEC EDGAR data (Forms 3, 4, 5)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..utils.exceptions import FilingNotFoundError
from .base import BaseTools, ToolResponse


class InsiderTools(BaseTools):
    """Tools for retrieving insider trading data from SEC EDGAR."""

    def get_insider_transactions(
        self,
        identifier: str,
        form_types: Optional[List[str]] = None,
        days: int = 90,
        limit: int = 50,
    ) -> ToolResponse:
        """Get insider transactions for a company."""
        try:
            company = self.client.get_company(identifier)
            form_types = form_types or ["3", "4", "5"]
            filings = company.get_filings(form=form_types)

            transactions: List[Dict[str, Any]] = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for filing in filings:
                if len(transactions) >= limit:
                    break

                filing_date = self._parse_date(filing.filing_date)
                if not filing_date or filing_date < cutoff_date:
                    continue

                transaction = self._create_transaction_info(filing)
                if transaction:
                    transactions.append(transaction)

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "transactions": transactions,
                "count": len(transactions),
                "form_types": form_types,
                "days_back": days,
                "filing_reference": self._create_insider_filing_reference(days),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get insider transactions: {e}"}

    def get_insider_summary(self, identifier: str, days: int = 180) -> ToolResponse:
        """Get summary of insider trading activity."""
        try:
            company = self.client.get_company(identifier)
            filings = company.get_filings(form=["3", "4", "5"])

            summary: Dict[str, Any] = {
                "total_filings": 0,
                "form_3_count": 0,
                "form_4_count": 0,
                "form_5_count": 0,
                "recent_filings": [],
                "insiders": set(),
            }

            cutoff_date = datetime.now() - timedelta(days=days)

            for filing in filings:
                filing_date = self._parse_date(filing.filing_date)
                if not filing_date or filing_date < cutoff_date:
                    continue

                summary["total_filings"] += 1
                self._count_form_type(summary, filing.form)

                if len(summary["recent_filings"]) < 10:
                    summary["recent_filings"].append(
                        {
                            "date": filing.filing_date.isoformat(),
                            "form": filing.form,
                            "accession": filing.accession_number,
                        }
                    )

                self._add_insider_name(summary, filing)

            summary["unique_insiders"] = len(summary["insiders"])
            summary["insiders"] = list(summary["insiders"])

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "period_days": days,
                "summary": summary,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get insider summary: {e}"}

    def get_form4_details(self, identifier: str, accession_number: str) -> ToolResponse:
        """Get detailed information from a specific Form 4."""
        try:
            company = self.client.get_company(identifier)
            filing = self._find_filing(company.get_filings(form="4"), accession_number)

            if not filing:
                raise FilingNotFoundError(f"Form 4 with accession {accession_number} not found")

            details = {
                "filing_date": filing.filing_date.isoformat(),
                "accession_number": filing.accession_number,
                "company_name": filing.company,
                "cik": filing.cik,
                "url": filing.url,
                "content_preview": filing.text()[:1000] if hasattr(filing, "text") else None,
            }

            try:
                form4 = filing.obj()
                if form4:
                    details["owner"] = {
                        "name": getattr(form4, "owner_name", ""),
                        "title": getattr(form4, "owner_title", ""),
                        "is_director": getattr(form4, "is_director", False),
                        "is_officer": getattr(form4, "is_officer", False),
                        "is_ten_percent_owner": getattr(form4, "is_ten_percent_owner", False),
                    }
            except Exception:
                pass

            return {"success": True, "form4_details": details}
        except Exception as e:
            return {"success": False, "error": f"Failed to get Form 4 details: {e}"}

    def analyze_form4_transactions(self, identifier: str, days: int = 90, limit: int = 50) -> ToolResponse:
        """Analyze Form 4 filings and extract detailed transaction data."""
        try:
            company = self.client.get_company(identifier)
            filings = company.get_filings(form="4")

            detailed_transactions: List[Dict[str, Any]] = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for filing in filings:
                if len(detailed_transactions) >= limit:
                    break

                filing_date = self._parse_date(filing.filing_date)
                if not filing_date or filing_date < cutoff_date:
                    continue

                transaction = self._extract_form4_details(filing)
                detailed_transactions.append(transaction)

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "detailed_transactions": detailed_transactions,
                "count": len(detailed_transactions),
                "days_back": days,
                "filing_reference": {
                    "data_source": "SEC EDGAR Form 4 Filings - Detailed Transaction Analysis",
                    "disclaimer": "All data extracted directly from SEC EDGAR Form 4 filings.",
                    "period_analyzed": f"Last {days} days from {datetime.now().strftime('%Y-%m-%d')}",
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to analyze Form 4 transactions: {e}"}

    def analyze_insider_sentiment(self, identifier: str, months: int = 6) -> ToolResponse:
        """Analyze insider trading sentiment."""
        try:
            company = self.client.get_company(identifier)
            filings = company.get_filings(form=["4"])

            days = months * 30
            cutoff_date = datetime.now() - timedelta(days=days)

            recent_filings = []
            for filing in filings:
                filing_date = self._parse_date(filing.filing_date)
                if filing_date and filing_date >= cutoff_date:
                    recent_filings.append(filing)

            filing_count = len(recent_filings)
            frequency = "high" if filing_count > 10 else "low" if filing_count < 3 else "moderate"

            analysis: Dict[str, Any] = {
                "period_months": months,
                "total_form4_filings": filing_count,
                "filing_frequency": frequency,
                "recent_filings": [
                    {
                        "date": f.filing_date.isoformat(),
                        "accession": f.accession_number,
                        "url": f.url,
                    }
                    for f in recent_filings[:10]
                ],
            }

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "analysis": analysis,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to analyze insider sentiment: {e}"}

    # Private helper methods

    def _create_transaction_info(self, filing) -> Optional[Dict[str, Any]]:
        """Create transaction info dict from a filing."""
        try:
            transaction = {
                "filing_date": filing.filing_date.isoformat(),
                "form_type": filing.form,
                "accession_number": filing.accession_number,
                "company_name": filing.company,
                "cik": filing.cik,
                "url": filing.url,
                "sec_url": self._build_sec_url(filing.cik, filing.accession_number),
                "data_source": f"SEC EDGAR Filing {filing.accession_number}",
            }

            try:
                ownership = filing.obj()
                if ownership:
                    for attr in ["owner_name", "owner_title", "is_director", "is_officer"]:
                        if hasattr(ownership, attr):
                            transaction[attr] = getattr(ownership, attr)
            except Exception:
                pass

            return transaction
        except Exception:
            return None

    def _create_insider_filing_reference(self, days: int) -> Dict[str, str]:
        """Create a filing reference dict for insider filings."""
        return {
            "data_source": "SEC EDGAR Insider Trading Filings (Forms 3, 4, 5)",
            "disclaimer": "All data extracted directly from SEC EDGAR filings.",
            "period_analyzed": f"Last {days} days from {datetime.now().strftime('%Y-%m-%d')}",
        }

    def _count_form_type(self, summary: Dict[str, Any], form_type: str):
        """Increment form type counter."""
        form_counters = {"3": "form_3_count", "4": "form_4_count", "5": "form_5_count"}
        counter_key = form_counters.get(form_type)
        if counter_key:
            summary[counter_key] += 1

    def _add_insider_name(self, summary: Dict[str, Any], filing):
        """Add insider name to summary if available."""
        try:
            ownership = filing.obj()
            if ownership and hasattr(ownership, "owner_name"):
                summary["insiders"].add(ownership.owner_name)
        except Exception:
            pass

    def _extract_form4_details(self, filing) -> Dict[str, Any]:
        """Extract detailed Form 4 information."""
        transaction = {
            "filing_date": filing.filing_date.isoformat(),
            "form_type": filing.form,
            "accession_number": filing.accession_number,
            "sec_url": self._build_sec_url(filing.cik, filing.accession_number),
            "data_source": f"SEC EDGAR Filing {filing.accession_number}",
        }

        try:
            form4 = filing.obj()
            if not form4:
                return transaction

            # Owner information
            for attr in [
                "owner_name",
                "owner_title",
                "is_director",
                "is_officer",
                "is_ten_percent_owner",
            ]:
                if hasattr(form4, attr):
                    transaction[attr] = getattr(form4, attr)

            # Transaction data
            if hasattr(form4, "transactions") and form4.transactions:
                transactions = []
                for tx in form4.transactions:
                    tx_data = self._extract_transaction_data(tx)
                    if tx_data:
                        transactions.append(tx_data)
                if transactions:
                    transaction["transactions"] = transactions

            # Holdings data
            if hasattr(form4, "holdings") and form4.holdings:
                holdings = []
                for holding in form4.holdings:
                    holding_data = self._extract_holding_data(holding)
                    if holding_data:
                        holdings.append(holding_data)
                if holdings:
                    transaction["holdings"] = holdings

        except Exception as e:
            transaction["parsing_error"] = f"Could not extract detailed data: {e}"

        return transaction

    def _extract_transaction_data(self, tx) -> Optional[Dict[str, Any]]:
        """Extract data from a transaction object."""
        tx_data = {}
        attrs = [
            ("transaction_date", str),
            ("transaction_code", None),
            ("shares", float),
            ("price_per_share", float),
            ("transaction_amount", float),
            ("shares_owned_after", float),
            ("acquisition_or_disposition", None),
        ]

        for attr, converter in attrs:
            if hasattr(tx, attr):
                value = getattr(tx, attr)
                if value is not None:
                    tx_data[attr] = converter(value) if converter else value

        return tx_data if tx_data else None

    def _extract_holding_data(self, holding) -> Optional[Dict[str, Any]]:
        """Extract data from a holding object."""
        holding_data = {}

        if hasattr(holding, "shares_owned") and holding.shares_owned:
            holding_data["shares_owned"] = float(holding.shares_owned)
        if hasattr(holding, "ownership_nature"):
            holding_data["ownership_nature"] = holding.ownership_nature

        return holding_data if holding_data else None
