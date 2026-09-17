"""Live E2E of every registered MCP tool against SEC EDGAR.

Runs each tool through the real FastMCP dispatch path (schema validation +
serialization), not by calling the underlying functions directly.

Requires SEC_EDGAR_USER_AGENT. Usage: python scripts/mcp_live_e2e.py
"""

import asyncio
import json
import os
import sys

EXPECTED_TOOL_COUNT = 21

FAIL = []
COVERED = set()


def check(name, condition, detail=""):
    if not condition:
        FAIL.append(name)
    print(f"[{'PASS' if condition else 'FAIL'}] {name} {detail}")


def unwrap(raw):
    """Normalize FastMCP call_tool return into a python object."""
    if isinstance(raw, tuple):
        raw = raw[1] if len(raw) > 1 and raw[1] is not None else raw[0]
    if isinstance(raw, list) and raw and hasattr(raw[0], "text"):
        try:
            return json.loads(raw[0].text)
        except json.JSONDecodeError:
            return raw[0].text
    if isinstance(raw, dict) and set(raw) == {"result"}:
        return raw["result"]
    return raw


async def main():
    if not os.environ.get("SEC_EDGAR_USER_AGENT"):
        sys.exit("SEC_EDGAR_USER_AGENT is not set")

    from mcp.server.fastmcp import FastMCP

    from sec_edgar_mcp.server import register_tools

    mcp = FastMCP("SEC EDGAR MCP")
    register_tools(mcp)

    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    check(f"tool count == {EXPECTED_TOOL_COUNT}", len(names) == EXPECTED_TOOL_COUNT, f"got {len(names)}")
    if len(names) != EXPECTED_TOOL_COUNT:
        print("registered:", names)

    async def call(name, args, ok, detail=lambda r: ""):
        COVERED.add(name)
        try:
            res = unwrap(await mcp.call_tool(name, args))
        except Exception as exc:  # noqa: BLE001 - surface any dispatch failure as a FAIL
            check(name, False, f"raised {type(exc).__name__}: {exc}")
            return None
        if isinstance(res, dict) and res.get("error"):
            check(name, False, f"error: {res['error']}")
            return res
        try:
            json.dumps(res, allow_nan=False)
        except ValueError as exc:
            check(f"{name} (strict JSON)", False, str(exc))
            return res
        try:
            check(name, ok(res), detail(res))
        except Exception as exc:  # noqa: BLE001
            check(name, False, f"assertion raised {type(exc).__name__}: {exc}")
        return res

    # --- Company ---
    await call(
        "get_cik_by_ticker", {"ticker": "AAPL"}, lambda r: "320193" in json.dumps(r), lambda r: json.dumps(r)[:80]
    )
    await call(
        "get_company_info",
        {"identifier": "AAPL"},
        lambda r: "Apple" in json.dumps(r),
        lambda r: str(r.get("name", ""))[:40],
    )
    await call(
        "search_companies",
        {"query": "Apple", "limit": 5},
        lambda r: bool(json.dumps(r).strip()) and "Apple" in json.dumps(r),
    )
    await call(
        "get_company_facts",
        {"identifier": "AAPL"},
        lambda r: r.get("has_facts") and {"Assets", "NetIncomeLoss"} <= set(r.get("metrics", {})),
        lambda r: f"metrics={len(r.get('metrics', {}))}",
    )

    # --- Filings ---
    recent = await call(
        "get_recent_filings",
        {"identifier": "AAPL", "form_type": "10-K", "days": 900, "limit": 5},
        lambda r: bool(r.get("filings")),
        lambda r: f"n={len(r.get('filings', []))}",
    )
    tenk_acc = recent["filings"][0]["accession_number"] if recent and recent.get("filings") else None
    check("10-K accession discovered", bool(tenk_acc), str(tenk_acc))

    await call(
        "get_recent_filings",
        {"days": 1, "limit": 5},
        lambda r: bool(r.get("filings")),
        lambda r: f"global n={len(r.get('filings', []))}",
    )

    if tenk_acc:
        await call(
            "get_filing_content",
            {"identifier": "AAPL", "accession_number": tenk_acc, "max_chars": 5000},
            lambda r: len(json.dumps(r)) > 1000,
            lambda r: f"chars={len(str(r.get('content', '')))}",
        )
        await call(
            "get_filing_sections",
            {"identifier": "AAPL", "accession_number": tenk_acc, "form_type": "10-K"},
            lambda r: len(json.dumps(r)) > 500,
            lambda r: f"keys={list(r)[:5]}",
        )

    eightk = await call(
        "get_recent_filings",
        {"identifier": "AAPL", "form_type": "8-K", "days": 400, "limit": 3},
        lambda r: bool(r.get("filings")),
        lambda r: f"8-K n={len(r.get('filings', []))}",
    )
    eightk_acc = eightk["filings"][0]["accession_number"] if eightk and eightk.get("filings") else None
    if eightk_acc:
        await call(
            "analyze_8k",
            {"identifier": "AAPL", "accession_number": eightk_acc},
            lambda r: bool(r["analysis"]["items"]) and r["analysis"]["date_of_report"],
            lambda r: f"items={r['analysis']['items']} press_release={r['analysis'].get('has_press_release')}",
        )

    # --- Financial ---
    await call("get_financials", {"identifier": "AAPL", "statement_type": "income"}, lambda r: len(json.dumps(r)) > 500)
    await call(
        "get_segment_data", {"identifier": "AAPL", "segment_type": "geographic"}, lambda r: len(json.dumps(r)) > 100
    )
    await call("get_key_metrics", {"identifier": "AAPL"}, lambda r: len(json.dumps(r)) > 200)
    await call(
        "compare_periods",
        {"identifier": "AAPL", "metric": "Revenues", "start_year": 2023, "end_year": 2024},
        lambda r: len(json.dumps(r)) > 100,
    )
    await call(
        "discover_company_metrics", {"identifier": "AAPL", "search_term": "revenue"}, lambda r: len(json.dumps(r)) > 100
    )
    await call(
        "get_xbrl_concepts", {"identifier": "AAPL", "concepts": ["Revenues"]}, lambda r: len(json.dumps(r)) > 100
    )
    await call("discover_xbrl_concepts", {"identifier": "AAPL"}, lambda r: len(json.dumps(r)) > 100)

    # --- Insider ---
    await call(
        "get_insider_transactions", {"identifier": "AAPL", "days": 180, "limit": 5}, lambda r: len(json.dumps(r)) > 100
    )
    await call("get_insider_summary", {"identifier": "AAPL", "days": 180}, lambda r: len(json.dumps(r)) > 100)

    form4 = await call(
        "get_recent_filings",
        {"identifier": "AAPL", "form_type": "4", "days": 180, "limit": 3},
        lambda r: bool(r.get("filings")),
        lambda r: f"Form4 n={len(r.get('filings', []))}",
    )
    form4_acc = form4["filings"][0]["accession_number"] if form4 and form4.get("filings") else None
    if form4_acc:
        await call(
            "get_form4_details",
            {"identifier": "AAPL", "accession_number": form4_acc},
            lambda r: len(json.dumps(r)) > 200,
            lambda r: str(r.get("owner", r.get("reporting_owner", "")))[:40],
        )
    await call(
        "analyze_form4_transactions",
        {"identifier": "AAPL", "days": 120, "limit": 10},
        lambda r: len(json.dumps(r)) > 100,
    )
    await call("analyze_insider_sentiment", {"identifier": "AAPL", "months": 6}, lambda r: len(json.dumps(r)) > 100)

    # --- Utility ---
    await call("get_recommended_tools", {"form_type": "10-K"}, lambda r: len(json.dumps(r)) > 50)

    missing = sorted(set(names) - COVERED)
    check("every registered tool exercised", not missing, f"missing={missing}")

    print()
    if FAIL:
        print(f"FAILED ({len(FAIL)}): {FAIL}")
        sys.exit(1)
    print(f"ALL MCP E2E CHECKS PASSED ({len(COVERED)}/{len(names)} tools exercised)")


asyncio.run(main())
