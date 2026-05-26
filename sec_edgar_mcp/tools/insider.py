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
                owner = self._get_primary_owner(form4) if form4 else None
                if owner is not None:
                    details["owner"] = {
                        "name": getattr(owner, "name", "") or "",
                        "title": getattr(owner, "officer_title", "") or "",
                        "is_director": bool(getattr(owner, "is_director", False)),
                        "is_officer": bool(getattr(owner, "is_officer", False)),
                        "is_ten_percent_owner": bool(getattr(owner, "is_ten_pct_owner", False)),
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

    @staticmethod
    def _get_primary_owner(ownership):
        """Return the first reporting Owner object, or None if unavailable."""
        try:
            owners = getattr(getattr(ownership, "reporting_owners", None), "owners", None)
            if owners:
                return owners[0]
        except Exception:
            pass
        return None

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
                owner = self._get_primary_owner(ownership) if ownership else None
                if owner is not None:
                    owner_data = {
                        "owner_name": getattr(owner, "name", None),
                        "owner_title": getattr(owner, "officer_title", None),
                        "is_director": getattr(owner, "is_director", None),
                        "is_officer": getattr(owner, "is_officer", None),
                    }
                    for key, value in owner_data.items():
                        if value is not None and value != "":
                            transaction[key] = value
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
            owner = self._get_primary_owner(ownership) if ownership else None
            name = getattr(owner, "name", None) if owner is not None else None
            if name:
                summary["insiders"].add(name)
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

            # Owner information is nested under reporting_owners.owners[0].
            owner = self._get_primary_owner(form4)
            if owner is not None:
                owner_fields = {
                    "owner_name": getattr(owner, "name", None),
                    "owner_title": getattr(owner, "officer_title", None),
                    "is_director": getattr(owner, "is_director", None),
                    "is_officer": getattr(owner, "is_officer", None),
                    "is_ten_percent_owner": getattr(owner, "is_ten_pct_owner", None),
                }
                for key, value in owner_fields.items():
                    if value is not None and value != "":
                        transaction[key] = value

            # Transaction activities (non-derivative + derivative combined).
            try:
                activities = form4.get_transaction_activities()
            except Exception:
                activities = None
            if activities:
                filing_date_iso = filing.filing_date.isoformat() if filing.filing_date else None
                transactions = []
                for tx in activities:
                    tx_data = self._extract_transaction_data(tx, filing_date_iso)
                    if tx_data:
                        transactions.append(tx_data)
                if transactions:
                    transaction["transactions"] = transactions

            # Holdings (populated for Form 3, and for Form 4/5 post-transaction amounts).
            try:
                holdings_list = form4.extract_form3_holdings()
            except Exception:
                holdings_list = None
            if holdings_list:
                holdings = []
                for holding in holdings_list:
                    holding_data = self._extract_holding_data(holding)
                    if holding_data:
                        holdings.append(holding_data)
                if holdings:
                    transaction["holdings"] = holdings

        except Exception as e:
            transaction["parsing_error"] = f"Could not extract detailed data: {e}"

        return transaction

    def _extract_transaction_data(
        self, tx, filing_date_iso: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a TransactionActivity object."""
        tx_data: Dict[str, Any] = {}

        # The TransactionActivity model exposes a flat set of attributes; there
        # is no per-transaction date field, so we fall back to the filing date.
        if filing_date_iso:
            tx_data["transaction_date"] = filing_date_iso

        attrs = [
            ("code", "transaction_code", None),
            ("transaction_type", "transaction_type", None),
            ("security_title", "security_title", None),
            ("shares", "shares", float),
            ("price_per_share", "price_per_share", float),
            ("value", "transaction_amount", float),
        ]

        for src, dest, converter in attrs:
            value = getattr(tx, src, None)
            if value is None or value == "":
                continue
            try:
                tx_data[dest] = converter(value) if converter else value
            except (TypeError, ValueError):
                tx_data[dest] = value

        # Fall back to shares * price_per_share when the reported value is
        # absent but both components are present.
        if "transaction_amount" not in tx_data and "shares" in tx_data and "price_per_share" in tx_data:
            try:
                tx_data["transaction_amount"] = float(tx_data["shares"]) * float(
                    tx_data["price_per_share"]
                )
            except (TypeError, ValueError):
                pass

        # Drop the filing-date placeholder if nothing else extracted — keeps
        # empty activities from masquerading as real data.
        meaningful = [k for k in tx_data if k != "transaction_date"]
        return tx_data if meaningful else None

    def _extract_holding_data(self, holding) -> Optional[Dict[str, Any]]:
        """Extract data from a SecurityHolding object."""
        holding_data: Dict[str, Any] = {}

        shares = getattr(holding, "shares", None)
        if shares not in (None, ""):
            try:
                holding_data["shares_owned"] = float(shares)
            except (TypeError, ValueError):
                holding_data["shares_owned"] = shares

        security_title = getattr(holding, "security_title", None)
        if security_title:
            holding_data["security_title"] = security_title

        ownership_nature = getattr(holding, "ownership_nature", None)
        if ownership_nature:
            holding_data["ownership_nature"] = ownership_nature

        direct_ownership = getattr(holding, "direct_ownership", None)
        if direct_ownership is not None:
            holding_data["direct_ownership"] = bool(direct_ownership)

        return holding_data if holding_data else None
