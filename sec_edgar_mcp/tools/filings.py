"""Filing-related tools for SEC EDGAR data."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from edgar import get_current_filings

from ..core.models import FilingInfo
from ..utils.exceptions import FilingNotFoundError
from .base import BaseTools, ToolResponse


class FilingsTools(BaseTools):
    """Tools for retrieving and analyzing SEC filings."""

    def get_recent_filings(
        self,
        identifier: Optional[str] = None,
        form_type: Optional[Union[str, List[str]]] = None,
        days: int = 30,
        limit: int = 40,
    ) -> ToolResponse:
        """Get recent filings for a company or across all companies."""
        try:
            if identifier:
                company = self.client.get_company(identifier)
                filings = company.get_filings(form=form_type)
            else:
                filings = get_current_filings(form=form_type, page_size=limit)

            filings_list = []
            for i, filing in enumerate(filings):
                if i >= limit:
                    break
                filing_info = self._create_filing_info(filing)
                if filing_info:
                    filings_list.append(filing_info.to_dict())

            return {"success": True, "filings": filings_list, "count": len(filings_list)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get recent filings: {e}"}

    def get_filing_content(
        self,
        identifier: str,
        accession_number: str,
        offset: int = 0,
        max_chars: int = 50000,
    ) -> ToolResponse:
        """Get filing content with paging support."""
        try:
            company = self.client.get_company(identifier)
            filing = self._find_filing(company.get_filings(), accession_number)

            if not filing:
                raise FilingNotFoundError(f"Filing {accession_number} not found")

            content = filing.text()
            total_chars = len(content)

            safe_offset = max(0, int(offset))
            safe_max_chars = int(max_chars) if max_chars and int(max_chars) > 0 else 50000

            page_end = min(safe_offset + safe_max_chars, total_chars)
            if safe_offset >= total_chars:
                page_content = ""
                page_end = total_chars
            else:
                page_content = content[safe_offset:page_end]

            next_offset = page_end if page_end < total_chars else None

            return {
                "success": True,
                "accession_number": filing.accession_number,
                "form_type": filing.form,
                "filing_date": filing.filing_date.isoformat(),
                "content": page_content,
                "url": filing.url,
                "offset": safe_offset,
                "returned_chars": len(page_content),
                "total_chars": total_chars,
                "next_offset": next_offset,
            }
        except FilingNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to get filing content: {e}"}

    def analyze_8k(self, identifier: str, accession_number: str) -> ToolResponse:
        """Analyze an 8-K filing for specific events."""
        try:
            company = self.client.get_company(identifier)
            filing = self._find_filing(company.get_filings(form="8-K"), accession_number)

            if not filing:
                raise FilingNotFoundError(f"8-K filing {accession_number} not found")

            eightk = filing.obj()
            analysis = self._analyze_8k_content(eightk)
            return {"success": True, "analysis": analysis}
        except Exception as e:
            return {"success": False, "error": f"Failed to analyze 8-K: {e}"}

    def get_filing_sections(self, identifier: str, accession_number: str, form_type: str) -> ToolResponse:
        """Get specific sections from a filing."""
        try:
            company = self.client.get_company(identifier)
            filing = self._find_filing(company.get_filings(form=form_type), accession_number)

            if not filing:
                raise FilingNotFoundError(f"Filing {accession_number} not found")

            filing_obj = filing.obj()
            sections = self._extract_sections(filing_obj, form_type)
            return {
                "success": True,
                "form_type": form_type,
                "sections": sections,
                "available_sections": list(sections.keys()),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get filing sections: {e}"}

    def _create_filing_info(self, filing) -> Optional[FilingInfo]:
        """Create a FilingInfo object from a filing."""
        try:
            return FilingInfo(
                accession_number=filing.accession_number,
                filing_date=self._parse_date(filing.filing_date),
                form_type=filing.form,
                company_name=filing.company,
                cik=filing.cik,
                file_number=getattr(filing, "file_number", None),
                acceptance_datetime=self._parse_date(getattr(filing, "acceptance_datetime", None)),
                period_of_report=self._parse_date(getattr(filing, "period_of_report", None)),
            )
        except Exception:
            return None

    def _analyze_8k_content(self, eightk) -> Dict[str, Any]:
        """Analyze 8-K content and extract events."""
        analysis: Dict[str, Any] = {
            "date_of_report": None,
            "items": getattr(eightk, "items", []),
            "events": {},
        }

        if hasattr(eightk, "date_of_report"):
            try:
                analysis["date_of_report"] = datetime.strptime(eightk.date_of_report, "%B %d, %Y").isoformat()
            except (ValueError, TypeError):
                pass

        item_descriptions = {
            "1.01": "Entry into Material Agreement",
            "1.02": "Termination of Material Agreement",
            "2.01": "Completion of Acquisition or Disposition",
            "2.02": "Results of Operations and Financial Condition",
            "2.03": "Creation of Direct Financial Obligation",
            "3.01": "Notice of Delisting",
            "4.01": "Changes in Accountant",
            "5.01": "Changes in Control",
            "5.02": "Departure/Election of Directors or Officers",
            "5.03": "Amendments to Articles/Bylaws",
            "7.01": "Regulation FD Disclosure",
            "8.01": "Other Events",
        }

        for item_code, description in item_descriptions.items():
            if hasattr(eightk, "has_item") and eightk.has_item(item_code):
                analysis["events"][item_code] = {"present": True, "description": description}

        if hasattr(eightk, "has_press_release"):
            analysis["has_press_release"] = eightk.has_press_release
            if eightk.has_press_release and hasattr(eightk, "press_releases"):
                analysis["press_releases"] = list(eightk.press_releases)[:3]

        return analysis

    def _extract_sections(self, filing_obj, form_type: str) -> Dict[str, Any]:
        """Extract sections from a filing based on form type."""
        sections: Dict[str, Any] = {}

        if form_type not in ["10-K", "10-Q"]:
            return sections

        for attr in ["business", "risk_factors", "mda"]:
            if hasattr(filing_obj, attr):
                content = str(getattr(filing_obj, attr))
                sections[attr] = content[:10000]

        if hasattr(filing_obj, "financials"):
            sections["has_financials"] = True

        return sections
