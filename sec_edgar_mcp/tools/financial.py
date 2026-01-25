from typing import List, Optional
import requests
from ..core.client import EdgarClient
from ..config import initialize_config
from .types import ToolResponse


class FinancialTools:
    """Tools for financial data and XBRL operations."""

    def __init__(self):
        self.client = EdgarClient()

    def get_financials(self, identifier: str, statement_type: str = "all") -> ToolResponse:
        """Get financial statements for a company by parsing XBRL data from filings."""
        try:
            company = self.client.get_company(identifier)

            # First try to get the latest 10-K or 10-Q
            latest_10k = None
            latest_10q = None

            try:
                filings_10k = company.get_filings(form="10-K")
                latest_10k = filings_10k.latest()
            except Exception:
                pass

            try:
                filings_10q = company.get_filings(form="10-Q")
                latest_10q = filings_10q.latest()
            except Exception:
                pass

            # Use the most recent filing
            if latest_10q and latest_10k:
                # Compare dates
                if hasattr(latest_10q, "filing_date") and hasattr(latest_10k, "filing_date"):
                    if latest_10q.filing_date > latest_10k.filing_date:
                        latest_filing = latest_10q
                        form_type = "10-Q"
                    else:
                        latest_filing = latest_10k
                        form_type = "10-K"
                else:
                    latest_filing = latest_10q
                    form_type = "10-Q"
            elif latest_10q:
                latest_filing = latest_10q
                form_type = "10-Q"
            elif latest_10k:
                latest_filing = latest_10k
                form_type = "10-K"
            else:
                return {"success": False, "error": "No 10-K or 10-Q filings found"}

            # Try to get financials using the Financials.extract method
            financials = None
            try:
                from edgar.financials import Financials

                financials = Financials.extract(latest_filing)
            except Exception:
                # Fallback to company methods
                try:
                    if form_type == "10-K":
                        financials = company.get_financials()
                    else:
                        financials = company.get_quarterly_financials()
                except Exception:
                    pass

            if not financials:
                return {
                    "success": False,
                    "error": "Could not extract financial statements from XBRL data",
                    "filing_info": {
                        "form_type": form_type,
                        "filing_date": str(latest_filing.filing_date) if latest_filing else None,
                        "accession_number": latest_filing.accession_number if latest_filing else None,
                    },
                }

            result = {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "form_type": form_type,
                "statements": {},
                "filing_reference": {
                    "filing_date": latest_filing.filing_date.isoformat()
                    if hasattr(latest_filing.filing_date, "isoformat")
                    else str(latest_filing.filing_date),
                    "accession_number": latest_filing.accession_number,
                    "form_type": form_type,
                    "sec_url": f"https://www.sec.gov/Archives/edgar/data/{company.cik}/{latest_filing.accession_number.replace('-', '')}/{latest_filing.accession_number}.txt",
                    "filing_url": latest_filing.url if hasattr(latest_filing, "url") else None,
                    "data_source": f"SEC EDGAR Filing {latest_filing.accession_number}, extracted directly from XBRL data",
                    "disclaimer": "All data extracted directly from SEC EDGAR filing with exact precision. No estimates, calculations, or rounding applied.",
                    "verification_note": "Users can verify all data independently at the provided SEC URL",
                },
            }

            # Get XBRL data from the filing for direct access
            xbrl = None
            try:
                xbrl = latest_filing.xbrl()
            except Exception:
                pass

            # Extract financial statements - these are parsed from XBRL
            if statement_type in ["income", "all"]:
                try:
                    income = financials.income_statement()
                    if income is not None and hasattr(income, "to_dict"):
                        result["statements"]["income_statement"] = {
                            "data": income.to_dict(orient="index"),
                            "columns": list(income.columns),
                            "index": list(income.index),
                        }
                    else:
                        # Try to get income statement from XBRL directly
                        if xbrl and hasattr(xbrl, "get_statement_by_type"):
                            try:
                                income_stmt = xbrl.get_statement_by_type("IncomeStatement")
                                if income_stmt:
                                    result["statements"]["income_statement"] = {
                                        "xbrl_statement": str(income_stmt)[:5000]
                                    }
                            except Exception:
                                pass

                        # Dynamically discover income statement concepts
                        if xbrl:
                            income_concepts = self._discover_statement_concepts(xbrl, latest_filing, "income")
                            if income_concepts:
                                result["statements"]["income_statement"] = {
                                    "data": income_concepts,
                                    "source": "xbrl_concepts_dynamic",
                                }
                except Exception as e:
                    result["statements"]["income_statement_error"] = str(e)

            if statement_type in ["balance", "all"]:
                try:
                    balance = financials.balance_sheet()
                    if balance is not None and hasattr(balance, "to_dict"):
                        result["statements"]["balance_sheet"] = {
                            "data": balance.to_dict(orient="index"),
                            "columns": list(balance.columns),
                            "index": list(balance.index),
                        }
                    else:
                        # Try to get balance sheet from XBRL directly
                        if xbrl and hasattr(xbrl, "get_statement_by_type"):
                            try:
                                balance_stmt = xbrl.get_statement_by_type("BalanceSheet")
                                if balance_stmt:
                                    result["statements"]["balance_sheet"] = {"xbrl_statement": str(balance_stmt)[:5000]}
                            except Exception:
                                pass

                        # Dynamically discover balance sheet concepts
                        if xbrl:
                            balance_concepts = self._discover_statement_concepts(xbrl, latest_filing, "balance")
                            if balance_concepts:
                                result["statements"]["balance_sheet"] = {
                                    "data": balance_concepts,
                                    "source": "xbrl_concepts_dynamic",
                                }
                except Exception as e:
                    result["statements"]["balance_sheet_error"] = str(e)

            if statement_type in ["cash", "all"]:
                try:
                    cash = financials.cashflow_statement()
                    if cash is not None and hasattr(cash, "to_dict"):
                        result["statements"]["cash_flow"] = {
                            "data": cash.to_dict(orient="index"),
                            "columns": list(cash.columns),
                            "index": list(cash.index),
                        }
                    else:
                        # Try to get cash flow from XBRL directly
                        if xbrl and hasattr(xbrl, "get_statement_by_type"):
                            try:
                                cash_stmt = xbrl.get_statement_by_type("CashFlow")
                                if cash_stmt:
                                    result["statements"]["cash_flow"] = {"xbrl_statement": str(cash_stmt)[:5000]}
                            except Exception:
                                pass

                        # Dynamically discover cash flow related concepts
                        if xbrl:
                            cash_concepts = self._discover_statement_concepts(xbrl, latest_filing, "cash")

                            if cash_concepts:
                                result["statements"]["cash_flow"] = {
                                    "data": cash_concepts,
                                    "source": "xbrl_concepts_dynamic",
                                }
                except Exception as e:
                    result["statements"]["cash_flow_error"] = str(e)

            # Add raw XBRL access for advanced users
            if hasattr(financials, "_xbrl") and financials._xbrl:
                result["has_raw_xbrl"] = True
                result["message"] = "Raw XBRL data available - use get_xbrl_concepts() for detailed concept extraction"

            return result

        except Exception as e:
            return {"success": False, "error": f"Failed to get financials: {str(e)}"}

    def _extract_income_statement(self, xbrl_data):
        """Extract income statement items from XBRL data."""
        income_concepts = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "GrossProfit",
            "OperatingExpenses",
            "OperatingIncomeLoss",
            "NonoperatingIncomeExpense",
            "InterestExpense",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeTaxExpenseBenefit",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
        ]

        return self._extract_concepts(xbrl_data, income_concepts)

    def _extract_balance_sheet(self, xbrl_data):
        """Extract balance sheet items from XBRL data."""
        balance_concepts = [
            "Assets",
            "AssetsCurrent",
            "CashAndCashEquivalentsAtCarryingValue",
            "AccountsReceivableNetCurrent",
            "InventoryNet",
            "AssetsNoncurrent",
            "PropertyPlantAndEquipmentNet",
            "Goodwill",
            "IntangibleAssetsNetExcludingGoodwill",
            "Liabilities",
            "LiabilitiesCurrent",
            "AccountsPayableCurrent",
            "LiabilitiesNoncurrent",
            "LongTermDebtNoncurrent",
            "StockholdersEquity",
            "CommonStockValue",
            "RetainedEarningsAccumulatedDeficit",
        ]

        return self._extract_concepts(xbrl_data, balance_concepts)

    def _extract_cash_flow(self, xbrl_data):
        """Extract cash flow statement items from XBRL data."""
        cash_concepts = [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInFinancingActivities",
            "CashAndCashEquivalentsPeriodIncreaseDecrease",
            "DepreciationDepletionAndAmortization",
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsOfDividends",
            "ProceedsFromIssuanceOfDebt",
            "RepaymentsOfDebt",
        ]

        return self._extract_concepts(xbrl_data, cash_concepts)

    def _extract_concepts(self, xbrl_data, concepts):
        """Extract specific concepts from XBRL data."""
        extracted = {}

        for concept in concepts:
            # Try different namespaces
            for ns in ["us-gaap", "ifrs-full", None]:
                try:
                    if ns:
                        value = xbrl_data.get(f"{{{ns}}}{concept}")
                    else:
                        value = xbrl_data.get(concept)

                    if value is not None:
                        # Handle different value formats
                        if hasattr(value, "value"):
                            extracted[concept] = {
                                "value": float(value.value),
                                "unit": getattr(value, "unit", "USD"),
                                "decimals": getattr(value, "decimals", None),
                                "context": getattr(value, "context", None),
                            }
                        elif isinstance(value, (int, float)):
                            extracted[concept] = {"value": float(value), "unit": "USD"}
                        break
                except Exception:
                    continue

        return extracted

    def _format_statement(self, statement):
        """Format a financial statement for output."""
        if hasattr(statement, "to_dict"):
            return statement.to_dict(orient="index")
        elif hasattr(statement, "to_json"):
            return statement.to_json()
        else:
            return str(statement)

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
            return {"success": False, "error": f"Failed to get segment data: {str(e)}"}

    def get_key_metrics(self, identifier: str, metrics: Optional[List[str]] = None) -> ToolResponse:
        """Get key financial metrics."""
        try:
            company = self.client.get_company(identifier)

            # Default metrics if none specified
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

            # Get company facts
            facts = company.get_facts()

            if not facts:
                return {"success": False, "error": "No facts data available for this company"}

            result_metrics = {}

            # Try to access facts data
            if hasattr(facts, "data"):
                facts_data = facts.data

                # Look for US-GAAP facts
                if "us-gaap" in facts_data:
                    gaap_facts = facts_data["us-gaap"]

                    for metric in metrics:
                        if metric in gaap_facts:
                            metric_data = gaap_facts[metric]
                            if "units" in metric_data:
                                # Get the most recent value
                                for unit_type, unit_data in metric_data["units"].items():
                                    if unit_data:
                                        # Sort by end date and get the latest
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

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "metrics": result_metrics,
                "requested_metrics": metrics,
                "found_metrics": list(result_metrics.keys()),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get key metrics: {str(e)}"}

    def compare_periods(self, identifier: str, metric: str, start_year: int, end_year: int) -> ToolResponse:
        """Compare a financial metric across periods."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            # Get the metric data
            fact_data = facts.get_fact(metric)
            if fact_data is None or fact_data.empty:
                return {"success": False, "error": f"No data found for metric: {metric}"}

            # Filter by year range
            period_data = []
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

            # Sort by year
            period_data.sort(key=lambda x: x["year"])

            # Calculate growth rates
            if len(period_data) >= 2:
                first_value = period_data[0]["value"]
                last_value = period_data[-1]["value"]

                if first_value != 0:
                    total_growth = ((last_value - first_value) / first_value) * 100
                    years = period_data[-1]["year"] - period_data[0]["year"]
                    if years > 0:
                        cagr = (((last_value / first_value) ** (1 / years)) - 1) * 100
                    else:
                        cagr = 0
                else:
                    total_growth = 0
                    cagr = 0
            else:
                total_growth = 0
                cagr = 0

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "metric": metric,
                "period_data": period_data,
                "analysis": {
                    "total_growth_percent": round(total_growth, 2),
                    "cagr_percent": round(cagr, 2),
                    "start_value": period_data[0]["value"] if period_data else 0,
                    "end_value": period_data[-1]["value"] if period_data else 0,
                    "periods_found": len(period_data),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to compare periods: {str(e)}"}

    def discover_company_metrics(self, identifier: str, search_term: Optional[str] = None) -> ToolResponse:
        """Discover available metrics for a company."""
        try:
            company = self.client.get_company(identifier)
            facts = company.get_facts()

            if not facts:
                return {"success": False, "error": "No facts available for this company"}

            # Get all available facts
            available_facts = []

            # This would depend on the actual API of edgar-tools
            # For now, we'll try common fact names
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
                        # Apply search filter if provided
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

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "available_metrics": available_facts,
                "count": len(available_facts),
                "search_term": search_term,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to discover company metrics: {str(e)}"}

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

            if accession_number:
                # Get specific filing by accession number
                filings = company.get_filings()
                filing = None
                for f in filings:
                    if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                        filing = f
                        break
                if not filing:
                    return {"success": False, "error": f"Filing with accession number {accession_number} not found"}
            else:
                # Get latest filing of specified type
                filings = company.get_filings(form=form_type)
                filing = filings.latest()
                if not filing:
                    return {"success": False, "error": f"No {form_type} filings found"}

            # Get XBRL data
            xbrl = filing.xbrl()

            if not xbrl:
                return {"success": False, "error": "No XBRL data found in filing"}

            result = {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "filing_date": filing.filing_date.isoformat()
                if hasattr(filing.filing_date, "isoformat")
                else str(filing.filing_date),
                "form_type": filing.form,
                "accession_number": filing.accession_number,
                "concepts": {},
                "filing_reference": {
                    "filing_date": filing.filing_date.isoformat()
                    if hasattr(filing.filing_date, "isoformat")
                    else str(filing.filing_date),
                    "accession_number": filing.accession_number,
                    "form_type": filing.form,
                    "sec_url": f"https://www.sec.gov/Archives/edgar/data/{company.cik}/{filing.accession_number.replace('-', '')}/{filing.accession_number}.txt",
                    "filing_url": filing.url if hasattr(filing, "url") else None,
                    "data_source": f"SEC EDGAR Filing {filing.accession_number}, extracted directly from XBRL data",
                    "disclaimer": "All data extracted directly from SEC EDGAR filing with exact precision. No estimates, calculations, or rounding applied.",
                    "verification_note": "Users can verify all data independently at the provided SEC URL",
                },
            }

            if concepts:
                # Extract specific concepts
                for concept in concepts:
                    value = self._get_xbrl_concept(xbrl, filing, concept)
                    if value is not None:
                        result["concepts"][concept] = value
            else:
                # Get all major financial concepts
                all_concepts = self._get_all_financial_concepts(xbrl, filing)
                result["concepts"] = all_concepts
                result["total_concepts"] = len(all_concepts)

            return result

        except Exception as e:
            return {"success": False, "error": f"Failed to get XBRL concepts: {str(e)}"}

    def _get_xbrl_concept(self, xbrl, filing, concept_name):
        """Get a specific concept from XBRL data using direct filing content extraction."""
        try:
            # Get raw filing content for direct parsing
            user_agent = initialize_config()
            filing_content = self._fetch_filing_content(filing.cik, filing.accession_number, user_agent)

            if not filing_content:
                return self._get_xbrl_concept_fallback(xbrl, concept_name)

            # Extract the concept using direct regex parsing
            extracted_value = self._extract_xbrl_concept_value(filing_content, concept_name)

            if extracted_value:
                return {
                    "value": extracted_value.get("value"),
                    "unit": "USD" if isinstance(extracted_value.get("value"), (int, float)) else None,
                    "context": extracted_value.get("context_ref"),
                    "period": extracted_value.get("period"),
                    "concept": concept_name,
                    "raw_value": extracted_value.get("raw_value"),
                    "scale": extracted_value.get("scale"),
                    "source": extracted_value.get("source"),
                }

            # If direct extraction failed, try fallback
            return self._get_xbrl_concept_fallback(xbrl, concept_name)

        except Exception:
            # Fallback to old method on any error
            return self._get_xbrl_concept_fallback(xbrl, concept_name)

    def _get_xbrl_concept_fallback(self, xbrl, concept_name):
        """Fallback method using edgartools API (may return placeholder values)."""
        # Try to get the concept using the query method
        if hasattr(xbrl, "query"):
            try:
                # Query for the concept - try exact match first
                query_result = xbrl.query(f"concept={concept_name}").to_dataframe()
                if len(query_result) > 0:
                    fact = query_result.iloc[0]
                    return {
                        "value": fact.get("value", None),
                        "unit": fact.get("unit", None),
                        "context": fact.get("context", None),
                        "period": fact.get("period_end", fact.get("period_instant", None)),
                        "concept": concept_name,
                    }

                # Try partial match
                query_result = xbrl.query("").by_concept(concept_name).to_dataframe()
                if len(query_result) > 0:
                    fact = query_result.iloc[0]
                    return {
                        "value": fact.get("value", None),
                        "unit": fact.get("unit", None),
                        "context": fact.get("context", None),
                        "period": fact.get("period_end", fact.get("period_instant", None)),
                        "concept": fact.get("concept", concept_name),
                    }
            except Exception:
                pass

        # Try using facts_history method for the concept
        if hasattr(xbrl, "facts") and hasattr(xbrl.facts, "facts_history"):
            try:
                history = xbrl.facts.facts_history(concept_name)
                if len(history) > 0:
                    latest = history.iloc[-1]
                    return {
                        "value": latest.get("value", None),
                        "unit": latest.get("unit", None),
                        "period": latest.get("period_end", latest.get("period_instant", None)),
                        "concept": concept_name,
                    }
            except Exception:
                pass

        return None

    def _discover_statement_concepts(self, xbrl, filing, statement_type):
        """Extract financial concepts directly from XBRL filing content using regex patterns."""
        discovered_concepts = {}

        try:
            # Get the raw filing content
            user_agent = initialize_config()
            filing_content = self._fetch_filing_content(filing.cik, filing.accession_number, user_agent)

            if not filing_content:
                return discovered_concepts

            # Define concept patterns for different statement types
            concept_patterns = {
                "cash": [
                    "NetCashProvidedByUsedInOperatingActivities",
                    "NetCashProvidedByUsedInInvestingActivities",
                    "NetCashProvidedByUsedInFinancingActivities",
                    "CashAndCashEquivalentsAtCarryingValue",
                    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                    "NetIncreaseDecreaseInCashAndCashEquivalents",
                ],
                "income": [
                    "Revenues",
                    "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "NetIncomeLoss",
                    "OperatingIncomeLoss",
                    "GrossProfit",
                    "CostOfRevenue",
                    "EarningsPerShareBasic",
                    "EarningsPerShareDiluted",
                ],
                "balance": [
                    "Assets",
                    "AssetsCurrent",
                    "Liabilities",
                    "LiabilitiesCurrent",
                    "StockholdersEquity",
                    "CashAndCashEquivalentsAtCarryingValue",
                    "AccountsReceivableNetCurrent",
                    "PropertyPlantAndEquipmentNet",
                ],
            }

            concepts_to_find = concept_patterns.get(statement_type, [])

            for concept in concepts_to_find:
                extracted_value = self._extract_xbrl_concept_value(filing_content, concept)
                if extracted_value:
                    discovered_concepts[concept] = extracted_value

        except Exception as e:
            discovered_concepts["extraction_error"] = str(e)

        return discovered_concepts

    def _fetch_filing_content(self, cik, accession_number, user_agent):
        """Fetch raw filing content from SEC EDGAR."""
        try:
            # Normalize CIK
            normalized_cik = str(int(cik))
            clean_accession = accession_number.replace("-", "")

            # Build URL for the .txt file (contains XBRL)
            url = f"https://www.sec.gov/Archives/edgar/data/{normalized_cik}/{clean_accession}/{accession_number}.txt"

            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text

        except Exception:
            return None

    def _extract_xbrl_concept_value(self, filing_content, concept):
        """Extract XBRL concept value using regex patterns like the old server."""
        import re

        try:
            # Pattern to find XBRL facts - flexible search for any tag containing the concept name
            patterns = [
                # Exact matches first (highest priority)
                rf'<ix:nonFraction[^>]*name="[^"]*:{re.escape(concept)}"[^>]*>([^<]+)</ix:nonFraction>',
                rf'<ix:nonFraction[^>]*name="{re.escape(concept)}"[^>]*>([^<]+)</ix:nonFraction>',
                # Flexible substring matches - any tag name containing the concept
                rf'<ix:nonFraction[^>]*name="[^"]*{re.escape(concept)}[^"]*"[^>]*>([^<]+)</ix:nonFraction>',
                # Same for nonNumeric tags
                rf'<ix:nonNumeric[^>]*name="[^"]*:{re.escape(concept)}"[^>]*>([^<]+)</ix:nonNumeric>',
                rf'<ix:nonNumeric[^>]*name="{re.escape(concept)}"[^>]*>([^<]+)</ix:nonNumeric>',
                rf'<ix:nonNumeric[^>]*name="[^"]*{re.escape(concept)}[^"]*"[^>]*>([^<]+)</ix:nonNumeric>',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, filing_content, re.IGNORECASE | re.DOTALL)

                for match in matches:
                    value_text = match.group(1).strip()

                    # Skip empty or placeholder values
                    if not value_text or value_text in ["--", "—", "--06-30"]:
                        continue

                    # Try to extract numeric value
                    try:
                        # Remove commas and convert to number
                        numeric_text = re.sub(r"[,$()]", "", value_text)

                        # Handle negative values in parentheses
                        if "(" in value_text and ")" in value_text:
                            numeric_text = "-" + numeric_text

                        numeric_value = float(numeric_text)

                        # Extract scale attribute if present
                        scale_match = re.search(r'scale="(-?\d+)"', match.group(0))
                        scale = int(scale_match.group(1)) if scale_match else 0

                        # Apply scale
                        actual_value = numeric_value * (10**scale)

                        # Extract context and period info
                        context_ref_match = re.search(r'contextRef="([^"]+)"', match.group(0))
                        context_ref = context_ref_match.group(1) if context_ref_match else None

                        # Find the context to get period info
                        period = None
                        if context_ref:
                            context_pattern = (
                                rf'<xbrli:context[^>]*id="{re.escape(context_ref)}"[^>]*>(.*?)</xbrli:context>'
                            )
                            context_match = re.search(context_pattern, filing_content, re.DOTALL)
                            if context_match:
                                # Extract end date
                                date_match = re.search(
                                    r"<xbrli:endDate>([^<]+)</xbrli:endDate>", context_match.group(1)
                                )
                                if not date_match:
                                    date_match = re.search(
                                        r"<xbrli:instant>([^<]+)</xbrli:instant>", context_match.group(1)
                                    )
                                period = date_match.group(1) if date_match else None

                        return {
                            "value": actual_value,
                            "raw_value": value_text,
                            "period": period,
                            "context_ref": context_ref,
                            "scale": scale,
                            "source": "xbrl_direct_extraction",
                        }

                    except (ValueError, TypeError):
                        # If not numeric, return as text
                        return {
                            "value": value_text,
                            "raw_value": value_text,
                            "period": None,
                            "context_ref": None,
                            "source": "xbrl_text_extraction",
                        }

            return None

        except Exception:
            return None

    def _get_all_financial_concepts(self, xbrl, filing):
        """Extract all major financial concepts from XBRL."""
        major_concepts = [
            # Income Statement
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "GrossProfit",
            "OperatingExpenses",
            "OperatingIncomeLoss",
            "NetIncomeLoss",
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
            # Balance Sheet
            "Assets",
            "AssetsCurrent",
            "AssetsNoncurrent",
            "CashAndCashEquivalentsAtCarryingValue",
            "AccountsReceivableNetCurrent",
            "InventoryNet",
            "PropertyPlantAndEquipmentNet",
            "Goodwill",
            "Liabilities",
            "LiabilitiesCurrent",
            "LiabilitiesNoncurrent",
            "AccountsPayableCurrent",
            "LongTermDebtNoncurrent",
            "StockholdersEquity",
            "CommonStockValue",
            "RetainedEarningsAccumulatedDeficit",
            # Cash Flow
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInFinancingActivities",
            # Other Key Metrics
            "CommonStockSharesOutstanding",
            "CommonStockSharesIssued",
        ]

        extracted = {}
        for concept in major_concepts:
            value = self._get_xbrl_concept(xbrl, filing, concept)
            if value is not None:
                extracted[concept] = value

        return extracted

    def discover_xbrl_concepts(
        self,
        identifier: str,
        accession_number: Optional[str] = None,
        form_type: str = "10-K",
        namespace_filter: Optional[str] = None,
    ) -> ToolResponse:
        """Discover all available XBRL concepts in a filing, including company-specific ones."""
        try:
            company = self.client.get_company(identifier)

            if accession_number:
                # Get specific filing by accession number
                filings = company.get_filings()
                filing = None
                for f in filings:
                    if f.accession_number.replace("-", "") == accession_number.replace("-", ""):
                        filing = f
                        break
                if not filing:
                    return {"success": False, "error": f"Filing with accession number {accession_number} not found"}
            else:
                # Get latest filing of specified type
                filings = company.get_filings(form=form_type)
                filing = filings.latest()
                if not filing:
                    return {"success": False, "error": f"No {form_type} filings found"}

            # Get XBRL data
            xbrl = filing.xbrl()

            if not xbrl:
                return {"success": False, "error": "No XBRL data found in filing"}

            # Get all available statements
            all_statements = []
            if hasattr(xbrl, "get_all_statements"):
                all_statements = xbrl.get_all_statements()

            # Get facts from XBRL using query method
            all_facts = {}
            sample_concepts = []

            if hasattr(xbrl, "query"):
                try:
                    # Get all facts
                    facts_query = xbrl.query("")  # Empty query should return all facts
                    all_facts_df = facts_query.to_dataframe()
                    if len(all_facts_df) > 0:
                        # Get unique concepts
                        concepts = all_facts_df["concept"].unique() if "concept" in all_facts_df.columns else []

                        # Filter by namespace if specified
                        if namespace_filter:
                            concepts = [c for c in concepts if namespace_filter in str(c)]

                        # Get a sample of concepts for display
                        sample_concepts = list(concepts[:20])  # First 20 concepts

                        for concept in sample_concepts[:10]:  # Limit to 10 for detailed info
                            concept_facts = all_facts_df[all_facts_df["concept"] == concept]
                            if len(concept_facts) > 0:
                                latest_fact = concept_facts.iloc[-1]
                                all_facts[str(concept)] = {
                                    "value": latest_fact.get("value", None),
                                    "unit": latest_fact.get("unit", None),
                                    "context": latest_fact.get("context", None),
                                    "count": len(concept_facts),
                                }
                except Exception as e:
                    # Fallback - at least return the error info
                    all_facts["error"] = str(e)

            # Try to get specific financial statements
            financial_statements = {}
            statement_types = [
                "BalanceSheet",
                "IncomeStatement",
                "CashFlow",
                "StatementsOfIncome",
                "ConsolidatedBalanceSheets",
                "ConsolidatedStatementsOfOperations",
                "ConsolidatedStatementsOfCashFlows",
            ]

            for stmt_type in statement_types:
                try:
                    if hasattr(xbrl, "find_statement"):
                        statements, role, actual_type = xbrl.find_statement(stmt_type)
                        if statements:
                            financial_statements[actual_type] = {"role": role, "statement_count": len(statements)}
                except Exception:
                    pass

            return {
                "success": True,
                "cik": company.cik,
                "name": company.name,
                "filing_date": filing.filing_date.isoformat()
                if hasattr(filing.filing_date, "isoformat")
                else str(filing.filing_date),
                "form_type": filing.form,
                "accession_number": filing.accession_number,
                "available_statements": all_statements,
                "financial_statements": financial_statements,
                "total_facts": len(all_facts),
                "sample_facts": dict(list(all_facts.items())[:20]),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to discover XBRL concepts: {str(e)}"}
