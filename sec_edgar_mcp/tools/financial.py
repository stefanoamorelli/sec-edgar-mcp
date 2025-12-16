"""Financial data tools for SEC EDGAR data."""

from typing import Any, Dict, List, Optional

from .base import BaseTools, ToolResponse
from .xbrl import (
    BALANCE_CONCEPTS,
    CASH_FLOW_CONCEPTS,
    INCOME_CONCEPTS,
    XBRLExtractor,
)


class FinancialTools(BaseTools):
    """Tools for extracting financial data from SEC EDGAR filings."""

    def __init__(self):
        super().__init__()
        self.xbrl_extractor = XBRLExtractor()

    def get_financials(self, identifier: str, statement_type: str = "all") -> ToolResponse:
        """Get financial statements from the latest SEC filing."""
        try:
            company = self.client.get_company(identifier)
            latest_filing, form_type = self._get_latest_financial_filing(company)

            if not latest_filing:
                return {"success": False, "error": "No 10-K or 10-Q filings found"}

            financials = self._extract_financials(latest_filing, company, form_type)
            if not financials:
                return {
                    "success": False,
                    "error": "Could not extract financial statements from XBRL data",
                    "filing_info": {
                        "form_type": form_type,
                        "filing_date": str(latest_filing.filing_date),
                        "accession_number": latest_filing.accession_number,
                    },
                }

            xbrl = self._get_xbrl(latest_filing)
            statements = self._extract_statements(financials, xbrl, latest_filing, statement_type)

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "form_type": form_type,
                "statements": statements,
                "filing_reference": self._create_filing_reference(latest_filing, company.cik, form_type),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get financials: {e}"}

    def get_segment_data(self, identifier: str, segment_type: str = "business") -> ToolResponse:
        """Get segment revenue breakdown from XBRL data."""
        try:
            company = self.client.get_company(identifier)

            filing = company.get_filings(form="10-K").latest()

            if not filing:
                return {"success": False, "error": "No 10-K filings found"}

            xbrl = filing.xbrl()
            if not xbrl:
                return {"success": False, "error": "No XBRL data found in filing"}

            segments: dict[str, dict[str, dict[str, str | int | float]]] = {
                "revenue": {},
                "cost_of_revenue": {},
                "operating_income": {},
                "operating_expenses": {},
            }
            segment_statements = []

            all_statements = xbrl.get_all_statements()
            for stmt_info in all_statements:
                definition = stmt_info.get("definition", "")
                if "segment" in definition.lower() and "detail" in definition.lower():
                    segment_statements.append(stmt_info)

            for stmt_info in segment_statements:
                role = stmt_info.get("role")
                if not role:
                    continue

                try:
                    stmt_data = xbrl.get_statement(role)
                    if not stmt_data:
                        continue

                    for item in stmt_data:
                        if not item.get("has_values"):
                            continue

                        values = item.get("values", {})
                        if not values:
                            continue

                        label = item.get("label", "Unknown")
                        concept = item.get("concept", "")

                        sorted_periods = sorted(values.keys(), reverse=True)
                        latest_period = sorted_periods[0]
                        value = values[latest_period]

                        if not isinstance(value, (int, float)):
                            continue

                        units = item.get("units", {})
                        unit = units.get(latest_period, "USD")

                        entry = {"value": value, "unit": unit, "period": latest_period}

                        concept_lower = concept.lower()
                        if "costofgoodsandservices" in concept_lower or "costofrevenue" in concept_lower:
                            segments["cost_of_revenue"][label] = entry
                        elif "operatingincome" in concept_lower:
                            segments["operating_income"][label] = entry
                        elif "operatingexpense" in concept_lower:
                            segments["operating_expenses"][label] = entry
                        elif "revenue" in concept_lower:
                            segments["revenue"][label] = entry

                except Exception:
                    continue

            if segment_type == "geographic":
                geographic_keywords = [
                    "united states",
                    "other countries",
                    "foreign",
                    "domestic",
                    "americas",
                    "europe",
                    "asia",
                    "china",
                    "japan",
                    "emea",
                    "apac",
                    "international",
                    "region",
                ]
                for category in segments:
                    segments[category] = {
                        k: v
                        for k, v in segments[category].items()
                        if any(kw in k.lower() for kw in geographic_keywords)
                    }

            segments = {k: v for k, v in segments.items() if v}

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "segment_type": segment_type,
                "segments": segments,
                "filing_date": filing.filing_date.isoformat(),
                "statements_found": len(segment_statements),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get segment data: {e}"}

    def get_key_metrics(self, identifier: str, metrics: Optional[List[str]] = None) -> ToolResponse:
        """Get key financial metrics from company facts."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            if not facts:
                return {"success": False, "error": "No facts data available"}

            if not metrics:
                metrics = [
                    "Revenues",
                    "NetIncomeLoss",
                    "Assets",
                    "Liabilities",
                    "StockholdersEquity",
                    "EarningsPerShareBasic",
                    "CommonStockSharesOutstanding",
                    "CashAndCashEquivalents",
                ]

            result_metrics = self._extract_metrics_from_facts(facts, metrics)
            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "metrics": result_metrics,
                "requested_metrics": metrics,
                "found_metrics": list(result_metrics.keys()),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get key metrics: {e}"}

    def compare_periods(self, identifier: str, metric: str, start_year: int, end_year: int) -> ToolResponse:
        """Compare a financial metric across periods."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            fact_data = facts.get_fact(metric)
            if fact_data is None or fact_data.empty:
                return {"success": False, "error": f"No data found for metric: {metric}"}

            period_data = self._filter_by_year_range(fact_data, start_year, end_year)
            analysis = self._calculate_growth(period_data)

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "metric": metric,
                "period_data": period_data,
                "analysis": analysis,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to compare periods: {e}"}

    def discover_company_metrics(self, identifier: str, search_term: Optional[str] = None) -> ToolResponse:
        """Discover available metrics for a company."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            if not facts:
                return {"success": False, "error": "No facts available"}

            available_facts = self._discover_facts(facts, search_term)
            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "available_metrics": available_facts,
                "count": len(available_facts),
                "search_term": search_term,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to discover metrics: {e}"}

    def get_xbrl_concepts(
        self,
        identifier: str,
        accession_number: Optional[str] = None,
        concepts: Optional[List[str]] = None,
        form_type: str = "10-K",
    ) -> ToolResponse:
        """Extract specific XBRL concepts from a filing."""
        try:
            company = self.client.get_company(identifier)
            filing = self._get_filing(company, accession_number, form_type)

            if not filing:
                error_msg = (
                    f"Filing {accession_number} not found" if accession_number else f"No {form_type} filings found"
                )
                return {"success": False, "error": error_msg}

            xbrl = filing.xbrl()
            if not xbrl:
                return {"success": False, "error": "No XBRL data found in filing"}

            result: Dict[str, Any] = {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "filing_date": self._format_date(filing.filing_date),
                "form_type": filing.form,
                "accession_number": filing.accession_number,
                "concepts": {},
                "filing_reference": self._create_filing_reference(filing, company.cik, filing.form),
            }

            if concepts:
                for concept in concepts:
                    value = self.xbrl_extractor.get_concept_from_xbrl(xbrl, filing, concept)
                    if value is not None:
                        result["concepts"][concept] = value
            else:
                result["concepts"] = self.xbrl_extractor.get_all_financial_concepts(xbrl, filing)
                result["total_concepts"] = len(result["concepts"])

            return result
        except Exception as e:
            return {"success": False, "error": f"Failed to get XBRL concepts: {e}"}

    def discover_xbrl_concepts(
        self,
        identifier: str,
        accession_number: Optional[str] = None,
        form_type: str = "10-K",
        namespace_filter: Optional[str] = None,
    ) -> ToolResponse:
        """Discover all XBRL concepts in a filing."""
        try:
            company = self.client.get_company(identifier)
            filing = self._get_filing(company, accession_number, form_type)

            if not filing:
                error_msg = (
                    f"Filing {accession_number} not found" if accession_number else f"No {form_type} filings found"
                )
                return {"success": False, "error": error_msg}

            xbrl = filing.xbrl()
            if not xbrl:
                return {"success": False, "error": "No XBRL data found in filing"}

            all_statements = []
            if hasattr(xbrl, "get_all_statements"):
                all_statements = xbrl.get_all_statements()

            all_facts, _ = self.xbrl_extractor.query_all_facts(xbrl, namespace_filter)
            financial_statements = self.xbrl_extractor.discover_financial_statements(xbrl)

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "filing_date": self._format_date(filing.filing_date),
                "form_type": filing.form,
                "accession_number": filing.accession_number,
                "available_statements": all_statements,
                "financial_statements": financial_statements,
                "total_facts": len(all_facts),
                "sample_facts": dict(list(all_facts.items())[:20]),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to discover XBRL concepts: {e}"}

    # Private helper methods

    def _get_latest_financial_filing(self, company):
        """Get the most recent 10-K or 10-Q filing."""
        latest_10k = latest_10q = None

        try:
            latest_10k = company.get_filings(form="10-K").latest()
        except Exception:
            pass

        try:
            latest_10q = company.get_filings(form="10-Q").latest()
        except Exception:
            pass

        if latest_10q and latest_10k:
            if hasattr(latest_10q, "filing_date") and hasattr(latest_10k, "filing_date"):
                if latest_10q.filing_date > latest_10k.filing_date:
                    return latest_10q, "10-Q"
            return latest_10k, "10-K"
        elif latest_10q:
            return latest_10q, "10-Q"
        elif latest_10k:
            return latest_10k, "10-K"
        return None, None

    def _extract_financials(self, filing, company, form_type):
        """Extract financials from a filing."""
        try:
            from edgar.financials import Financials

            return Financials.extract(filing)
        except Exception:
            try:
                if form_type == "10-K":
                    return company.get_financials()
                return company.get_quarterly_financials()
            except Exception:
                return None

    def _get_xbrl(self, filing):
        """Get XBRL data from a filing."""
        try:
            return filing.xbrl()
        except Exception:
            return None

    def _extract_statements(self, financials, xbrl, filing, statement_type: str) -> Dict[str, Any]:
        """Extract financial statements based on type."""
        statements: Dict[str, Any] = {}
        statement_configs = {
            "income": ("income_statement", INCOME_CONCEPTS),
            "balance": ("balance_sheet", BALANCE_CONCEPTS),
            "cash": ("cash_flow", CASH_FLOW_CONCEPTS),
        }

        types_to_extract = list(statement_configs.keys()) if statement_type == "all" else [statement_type]

        for stmt_type in types_to_extract:
            if stmt_type not in statement_configs:
                continue

            key, _ = statement_configs[stmt_type]
            try:
                stmt_method = getattr(financials, f"{key}")
                stmt = stmt_method() if callable(stmt_method) else stmt_method

                if stmt is not None and hasattr(stmt, "to_dict"):
                    statements[key] = {
                        "data": stmt.to_dict(orient="index"),
                        "columns": list(stmt.columns),
                        "index": list(stmt.index),
                    }
                elif xbrl:
                    discovered = self.xbrl_extractor.discover_statement_concepts(xbrl, filing, stmt_type)
                    if discovered:
                        statements[key] = {"data": discovered, "source": "xbrl_concepts_dynamic"}
            except Exception as e:
                statements[f"{key}_error"] = str(e)

        return statements

    def _get_filing(self, company, accession_number: Optional[str], form_type: str):
        """Get a specific filing or the latest of a form type."""
        if accession_number:
            return self._find_filing(company.get_filings(), accession_number)
        filings = company.get_filings(form=form_type)
        return filings.latest() if filings else None

    def _extract_metrics_from_facts(self, facts, metrics: List[str]) -> Dict[str, Any]:
        """Extract metrics from company facts."""
        result_metrics: Dict[str, Any] = {}

        if not hasattr(facts, "data"):
            return result_metrics

        facts_data = facts.data
        if "us-gaap" not in facts_data:
            return result_metrics

        gaap_facts = facts_data["us-gaap"]

        for metric in metrics:
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
                    result_metrics[metric] = {
                        "value": float(latest.get("val", 0)),
                        "unit": unit_type,
                        "period": latest.get("end", ""),
                        "form": latest.get("form", ""),
                        "fiscal_year": latest.get("fy", ""),
                        "fiscal_period": latest.get("fp", ""),
                    }
                    break

        return result_metrics

    def _filter_by_year_range(self, fact_data, start_year: int, end_year: int) -> List[Dict[str, Any]]:
        """Filter fact data by year range."""
        period_data: List[Dict[str, Any]] = []
        for _, row in fact_data.iterrows():
            try:
                year = int(row.get("fy", 0))
                if start_year <= year <= end_year:
                    period_data.append(
                        {
                            "year": year,
                            "period": row.get("fp", ""),
                            "value": float(row.get("value", 0)),
                            "unit": row.get("unit", "USD"),
                            "form": row.get("form", ""),
                        }
                    )
            except Exception:
                continue
        period_data.sort(key=lambda x: x["year"])
        return period_data

    def _calculate_growth(self, period_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate growth metrics from period data."""
        if len(period_data) < 2:
            return {
                "total_growth_percent": 0,
                "cagr_percent": 0,
                "start_value": period_data[0]["value"] if period_data else 0,
                "end_value": period_data[-1]["value"] if period_data else 0,
                "periods_found": len(period_data),
            }

        first_value = period_data[0]["value"]
        last_value = period_data[-1]["value"]
        years = period_data[-1]["year"] - period_data[0]["year"]

        if first_value == 0:
            return {
                "total_growth_percent": 0,
                "cagr_percent": 0,
                "start_value": first_value,
                "end_value": last_value,
                "periods_found": len(period_data),
            }

        total_growth = ((last_value - first_value) / first_value) * 100
        cagr = (((last_value / first_value) ** (1 / years)) - 1) * 100 if years > 0 else 0

        return {
            "total_growth_percent": round(total_growth, 2),
            "cagr_percent": round(cagr, 2),
            "start_value": first_value,
            "end_value": last_value,
            "periods_found": len(period_data),
        }

    def _discover_facts(self, facts, search_term: Optional[str]) -> List[Dict[str, Any]]:
        """Discover available facts from company facts."""
        available_facts: List[Dict[str, Any]] = []
        common_facts = [
            "Assets",
            "Liabilities",
            "StockholdersEquity",
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "CostOfRevenue",
            "GrossProfit",
            "OperatingIncomeLoss",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
            "CommonStockSharesOutstanding",
            "CashAndCashEquivalents",
            "AccountsReceivableNet",
            "InventoryNet",
            "PropertyPlantAndEquipmentNet",
            "Goodwill",
            "IntangibleAssetsNet",
            "LongTermDebt",
            "ResearchAndDevelopmentExpense",
            "SellingGeneralAndAdministrativeExpense",
        ]

        for fact_name in common_facts:
            try:
                fact_data = facts.get_fact(fact_name)
                if fact_data is not None and not fact_data.empty:
                    if not search_term or search_term.lower() in fact_name.lower():
                        available_facts.append(
                            {
                                "name": fact_name,
                                "count": len(fact_data),
                                "latest_period": fact_data.iloc[-1].get("end", "") if not fact_data.empty else None,
                            }
                        )
            except Exception:
                continue

        return available_facts
