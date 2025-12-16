# SEC EDGAR MCP

<p align="center">
  <a href="https://pypi.org/project/sec-edgar-mcp/"><img alt="PyPI" src="https://img.shields.io/pypi/v/sec-edgar-mcp.svg" /></a>
  <a href="https://anaconda.org/stefanoamorelli/sec-edgar-mcp"><img alt="Conda Version" src="https://img.shields.io/conda/vn/stefanoamorelli/sec-edgar-mcp.svg" /></a>
  <img alt="Python: 3.11+" src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" />
  <img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" />
  <a href="https://mseep.ai/app/0132880c-5e83-410b-a1d5-d3df08ed7b5c"><img alt="Verified on MseeP" src="https://mseep.ai/badge.svg" /></a>
  <a href="https://doi.org/10.5281/zenodo.17123166"><img alt="DOI" src="https://zenodo.org/badge/DOI/10.5281/zenodo.17123166.svg" /></a>
</p>

MCP server for accessing SEC EDGAR filings. Connects AI assistants to company filings, financial statements, and insider trading data with exact numeric precision.

Built on [edgartools](https://github.com/dgunning/edgartools).

https://github.com/user-attachments/assets/d310eb42-b3ca-467d-92f7-7d132e6274fe

<details>
<summary>See demo video</summary>

<a href="https://www.loom.com/share/17fcd7d891fe496f9a6b8fb85ede66bb">
  <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/17fcd7d891fe496f9a6b8fb85ede66bb-7f8590d1d4bcc2fb-full-play.gif">
</a>

</details>

> [!NOTE]
> This project is not affiliated with or endorsed by the U.S. Securities and Exchange Commission. EDGAR and SEC are trademarks of the SEC.

## Quick Start

```json
{
  "mcpServers": {
    "sec-edgar-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "SEC_EDGAR_USER_AGENT=Your Name (your@email.com)",
        "stefanoamorelli/sec-edgar-mcp:latest"
      ]
    }
  }
}
```

The `-i` flag is required for MCP's JSON-RPC communication.

For other installation methods (pip, conda, uv), see the [documentation](https://sec-edgar-mcp.amorelli.tech/setup/quickstart).

## Tools

| Category | Tools |
|----------|-------|
| **Company** | CIK lookup, company info, company facts |
| **Filings** | 10-K, 10-Q, 8-K retrieval, section extraction |
| **Financials** | Balance sheet, income statement, cash flow (XBRL-parsed) |
| **Insider Trading** | Form 3/4/5 transactions |

All responses include SEC filing URLs for verification.

## HTTP Transport

For platforms like [Dify](https://dify.ai), use streamable HTTP instead of stdio:

```bash
python -m sec_edgar_mcp.server --transport streamable-http --port 9870
```

No authentication is included. Use only on private networks.

## Documentation

Full docs: [sec-edgar-mcp.amorelli.tech](https://sec-edgar-mcp.amorelli.tech/)

## Contributors

<a href="https://github.com/stefanoamorelli/sec-edgar-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=stefanoamorelli/sec-edgar-mcp" />
</a>

## Citation

If you use this software in research, please cite it:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17123166.svg)](https://doi.org/10.5281/zenodo.17123166)

```bibtex
@software{amorelli_sec_edgar_mcp_2025,
  title = {{SEC EDGAR MCP (Model Context Protocol) Server}},
  author = {Amorelli, Stefano},
  version = {1.0.6},
  year = {2025},
  month = {9},
  url = {https://doi.org/10.5281/zenodo.17123166},
  doi = {10.5281/zenodo.17123166}
}
```

See [CITATION.cff](CITATION.cff) for additional formats.

## License

[AGPL-3.0](LICENSE). For commercial licensing: stefano@amorelli.tech

