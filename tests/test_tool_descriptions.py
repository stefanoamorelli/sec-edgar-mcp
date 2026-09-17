"""Tests that every registered MCP tool exposes a non-empty description.

Regression for #97: several tool functions declared their docstring as an
f-string. Python does not store an f-string expression in docstring position as
``__doc__``, so those tools registered with an empty MCP description. The server
now uses plain docstrings with a ``{_FINANCIAL_INSTRUCTIONS}`` placeholder that
``register_tools`` expands, so descriptions must be populated for every tool.
"""

from unittest.mock import patch

from mcp.server.fastmcp import FastMCP


def _registered_tools():
    with patch("sec_edgar_mcp.tools.base.EdgarClient"):
        from sec_edgar_mcp import server

        mcp = FastMCP("test")
        server.register_tools(mcp)
        return mcp._tool_manager.list_tools()


def test_every_tool_has_a_nonempty_description():
    tools = _registered_tools()
    assert tools, "no tools were registered"
    empty = [t.name for t in tools if not (t.description or "").strip()]
    assert not empty, f"tools registered with an empty description: {empty}"


def test_shared_financial_instructions_are_injected():
    tools = {t.name: t for t in _registered_tools()}
    # get_financials reuses the shared _FINANCIAL_INSTRUCTIONS block via the
    # placeholder; after expansion its description must contain that block and
    # must not still contain the raw placeholder.
    desc = tools["get_financials"].description or ""
    assert "<instructions>" in desc
    assert "{_FINANCIAL_INSTRUCTIONS}" not in desc
