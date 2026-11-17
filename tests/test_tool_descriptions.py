"""Every registered MCP tool must reach the client with a description."""

import asyncio
import os
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP


def _tools():
    os.environ.setdefault("SEC_EDGAR_USER_AGENT", "pytest (test@example.com)")
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        import sec_edgar_mcp.server as server

    mcp = FastMCP("test")
    server.register_tools(mcp)
    return asyncio.run(mcp.list_tools())


def test_no_tool_is_registered_without_a_description():
    # Regression: nine tools carried their text in an f-string literal, which
    # Python does not store as __doc__, so FastMCP advertised them with an
    # empty description.
    missing = [tool.name for tool in _tools() if not (tool.description or "").strip()]

    assert missing == []


def test_financial_tools_carry_the_data_integrity_instructions():
    # The same bug dropped the instructions telling the model not to add
    # outside numbers and to cite the filing URL.
    described = [tool for tool in _tools() if "data-integrity" in (tool.description or "")]

    assert {tool.name for tool in described} >= {
        "get_financials",
        "get_key_metrics",
        "compare_periods",
        "get_xbrl_concepts",
    }
