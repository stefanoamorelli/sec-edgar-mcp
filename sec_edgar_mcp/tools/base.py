"""Base utilities for SEC EDGAR tools."""

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ..core.client import EdgarClient
from ..utils.constants import METRIC_CONCEPTS

ToolResponse = Dict[str, Any]


def json_safe(value: Any) -> Any:
    """Replace NaN and infinities with None so the payload is valid JSON.

    Statement tables come from DataFrames where a missing cell is NaN, and
    json.dumps writes those as bare NaN, which no JSON parser accepts.
    """
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


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
            try:
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                return None
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

    def _metric_concepts(self, metric: str) -> List[str]:
        """Resolve a metric name to its waterfall of XBRL concepts."""
        return METRIC_CONCEPTS.get(metric, [metric])

    def _metric_history(self, facts, metric: str) -> Optional[pd.DataFrame]:
        """Every reported fact for a metric across its concept waterfall.

        Adds ``concept`` (the tag reported) and ``priority`` (its waterfall position) columns.
        """
        frames = []
        for priority, concept in enumerate(self._metric_concepts(metric)):
            history = facts.get_fact(concept)
            if history is not None and not history.empty:
                frames.append(history.assign(concept=concept, priority=priority))
        if not frames:
            return None
        return pd.concat(frames, ignore_index=True)

    def _latest_metric_fact(self, facts, metric: str) -> Optional[Dict[str, Any]]:
        """Most recently filed fact for a metric across its concept waterfall.

        Ranks by filing date, then period end; the waterfall order only breaks ties.
        """
        history = self._metric_history(facts, metric)
        if history is None:
            return None
        history = history[history["value"].notna()]
        if history.empty:
            return None
        ranked = history.assign(filed=history["filed"].fillna(""), end=history["end"].fillna("")).sort_values(
            ["filed", "end", "priority"], ascending=[False, False, True]
        )
        return ranked.iloc[0].to_dict()

    def _fact_to_metric(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize a fact row into the standard metric dict."""

        def clean(value: Any) -> Any:
            return "" if value is None or pd.isna(value) else value

        fiscal_year = clean(fact.get("fy"))
        return {
            "value": float(fact["value"]),
            "unit": fact.get("unit"),
            "period": clean(fact.get("end")),
            "form": clean(fact.get("form")),
            "fiscal_year": int(fiscal_year) if fiscal_year != "" else "",
            "fiscal_period": clean(fact.get("fp")),
            "concept": fact.get("concept"),
            "filing_date": clean(fact.get("filed")),
        }
