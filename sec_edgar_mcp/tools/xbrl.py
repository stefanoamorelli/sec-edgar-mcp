"""XBRL data extraction utilities."""

import re
from typing import Any, Dict, List, Optional

import requests

from ..config import initialize_config

# XBRL concept definitions by statement type
INCOME_CONCEPTS = [
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

BALANCE_CONCEPTS = [
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

CASH_FLOW_CONCEPTS = [
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

ALL_MAJOR_CONCEPTS = (
    INCOME_CONCEPTS
    + BALANCE_CONCEPTS
    + CASH_FLOW_CONCEPTS
    + ["CommonStockSharesOutstanding", "CommonStockSharesIssued"]
)


class XBRLExtractor:
    """Utilities for extracting data from XBRL filings."""

    def fetch_filing_content(self, cik: str, accession_number: str) -> Optional[str]:
        """Fetch raw filing content from SEC EDGAR."""
        try:
            user_agent = initialize_config()
            normalized_cik = str(int(cik))
            clean_accession = accession_number.replace("-", "")
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

    def extract_concept_value(self, filing_content: str, concept: str) -> Optional[Dict[str, Any]]:
        """Extract XBRL concept value using regex patterns."""
        try:
            patterns = [
                rf'<ix:nonFraction[^>]*name="[^"]*:{re.escape(concept)}"[^>]*>([^<]+)</ix:nonFraction>',
                rf'<ix:nonFraction[^>]*name="{re.escape(concept)}"[^>]*>([^<]+)</ix:nonFraction>',
                rf'<ix:nonFraction[^>]*name="[^"]*{re.escape(concept)}[^"]*"[^>]*>([^<]+)</ix:nonFraction>',
                rf'<ix:nonNumeric[^>]*name="[^"]*:{re.escape(concept)}"[^>]*>([^<]+)</ix:nonNumeric>',
                rf'<ix:nonNumeric[^>]*name="{re.escape(concept)}"[^>]*>([^<]+)</ix:nonNumeric>',
                rf'<ix:nonNumeric[^>]*name="[^"]*{re.escape(concept)}[^"]*"[^>]*>([^<]+)</ix:nonNumeric>',
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, filing_content, re.IGNORECASE | re.DOTALL):
                    value_text = match.group(1).strip()

                    if not value_text or value_text in ["--", "—", "--06-30"]:
                        continue

                    try:
                        numeric_text = re.sub(r"[,$()]", "", value_text)
                        if "(" in value_text and ")" in value_text:
                            numeric_text = "-" + numeric_text

                        numeric_value = float(numeric_text)

                        scale_match = re.search(r'scale="(-?\d+)"', match.group(0))
                        scale = int(scale_match.group(1)) if scale_match else 0
                        actual_value = numeric_value * (10**scale)

                        context_ref_match = re.search(r'contextRef="([^"]+)"', match.group(0))
                        context_ref = context_ref_match.group(1) if context_ref_match else None

                        period = self._extract_period_from_context(filing_content, context_ref)

                        return {
                            "value": actual_value,
                            "raw_value": value_text,
                            "period": period,
                            "context_ref": context_ref,
                            "scale": scale,
                            "source": "xbrl_direct_extraction",
                        }
                    except (ValueError, TypeError):
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

    def _extract_period_from_context(self, filing_content: str, context_ref: Optional[str]) -> Optional[str]:
        """Extract period from XBRL context."""
        if not context_ref:
            return None

        try:
            context_pattern = rf'<xbrli:context[^>]*id="{re.escape(context_ref)}"[^>]*>(.*?)</xbrli:context>'
            context_match = re.search(context_pattern, filing_content, re.DOTALL)

            if context_match:
                date_match = re.search(r"<xbrli:endDate>([^<]+)</xbrli:endDate>", context_match.group(1))
                if not date_match:
                    date_match = re.search(r"<xbrli:instant>([^<]+)</xbrli:instant>", context_match.group(1))
                return date_match.group(1) if date_match else None
        except Exception:
            pass
        return None

    def get_concept_from_xbrl(self, xbrl, filing, concept_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific concept from XBRL data with fallback methods."""
        filing_content = self.fetch_filing_content(filing.cik, filing.accession_number)

        if filing_content:
            extracted = self.extract_concept_value(filing_content, concept_name)
            if extracted:
                return {
                    "value": extracted.get("value"),
                    "unit": "USD" if isinstance(extracted.get("value"), (int, float)) else None,
                    "context": extracted.get("context_ref"),
                    "period": extracted.get("period"),
                    "concept": concept_name,
                    "raw_value": extracted.get("raw_value"),
                    "scale": extracted.get("scale"),
                    "source": extracted.get("source"),
                }

        return self._get_concept_fallback(xbrl, concept_name)

    def _get_concept_fallback(self, xbrl, concept_name: str) -> Optional[Dict[str, Any]]:
        """Fallback method using edgartools API."""
        if hasattr(xbrl, "query"):
            try:
                query_result = xbrl.query(f"concept={concept_name}").to_dataframe()
                if len(query_result) > 0:
                    fact = query_result.iloc[0]
                    return {
                        "value": fact.get("value"),
                        "unit": fact.get("unit"),
                        "context": fact.get("context"),
                        "period": fact.get("period_end", fact.get("period_instant")),
                        "concept": concept_name,
                    }

                query_result = xbrl.query("").by_concept(concept_name).to_dataframe()
                if len(query_result) > 0:
                    fact = query_result.iloc[0]
                    return {
                        "value": fact.get("value"),
                        "unit": fact.get("unit"),
                        "context": fact.get("context"),
                        "period": fact.get("period_end", fact.get("period_instant")),
                        "concept": fact.get("concept", concept_name),
                    }
            except Exception:
                pass

        if hasattr(xbrl, "facts") and hasattr(xbrl.facts, "facts_history"):
            try:
                history = xbrl.facts.facts_history(concept_name)
                if len(history) > 0:
                    latest = history.iloc[-1]
                    return {
                        "value": latest.get("value"),
                        "unit": latest.get("unit"),
                        "period": latest.get("period_end", latest.get("period_instant")),
                        "concept": concept_name,
                    }
            except Exception:
                pass

        return None

    def get_all_financial_concepts(self, xbrl, filing) -> Dict[str, Any]:
        """Extract all major financial concepts from XBRL."""
        extracted = {}
        for concept in ALL_MAJOR_CONCEPTS:
            value = self.get_concept_from_xbrl(xbrl, filing, concept)
            if value is not None:
                extracted[concept] = value
        return extracted

    def discover_statement_concepts(self, xbrl, filing, statement_type: str) -> Dict[str, Any]:
        """Extract financial concepts for a specific statement type."""
        discovered: Dict[str, Any] = {}

        try:
            filing_content = self.fetch_filing_content(filing.cik, filing.accession_number)
            if not filing_content:
                return discovered

            concept_map = {
                "cash": CASH_FLOW_CONCEPTS[:6],
                "income": INCOME_CONCEPTS[:8],
                "balance": BALANCE_CONCEPTS[:8],
            }

            concepts = concept_map.get(statement_type, [])
            for concept in concepts:
                extracted = self.extract_concept_value(filing_content, concept)
                if extracted:
                    discovered[concept] = extracted
        except Exception as e:
            discovered["extraction_error"] = str(e)

        return discovered

    def query_all_facts(self, xbrl, namespace_filter: Optional[str] = None) -> tuple:
        """Query all facts from XBRL."""
        all_facts: Dict[str, Any] = {}
        sample_concepts: List[str] = []

        if not hasattr(xbrl, "query"):
            return all_facts, sample_concepts

        try:
            facts_query = xbrl.query("")
            all_facts_df = facts_query.to_dataframe()

            if len(all_facts_df) == 0:
                return all_facts, sample_concepts

            concepts = all_facts_df["concept"].unique() if "concept" in all_facts_df.columns else []

            if namespace_filter:
                concepts = [c for c in concepts if namespace_filter in str(c)]

            sample_concepts = list(concepts[:20])

            for concept in sample_concepts[:10]:
                concept_facts = all_facts_df[all_facts_df["concept"] == concept]
                if len(concept_facts) > 0:
                    latest_fact = concept_facts.iloc[-1]
                    all_facts[str(concept)] = {
                        "value": latest_fact.get("value"),
                        "unit": latest_fact.get("unit"),
                        "context": latest_fact.get("context"),
                        "count": len(concept_facts),
                    }
        except Exception as e:
            all_facts["error"] = str(e)

        return all_facts, sample_concepts

    def discover_financial_statements(self, xbrl) -> Dict[str, Any]:
        """Discover available financial statements in XBRL."""
        financial_statements: Dict[str, Any] = {}
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
                        financial_statements[actual_type] = {
                            "role": role,
                            "statement_count": len(statements),
                        }
            except Exception:
                pass

        return financial_statements
