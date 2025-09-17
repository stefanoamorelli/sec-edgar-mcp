<div align="center">

# SEC EDGAR MCP

mcp-name: io.github.stefanoamorelli/sec-edgar-mcp

</div>

<p align="center">
  <img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" />
  <img alt="Python: 3.11+" src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" />
  <img alt="Platform: Windows | Mac | Linux" src="https://img.shields.io/badge/platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey.svg" />
  <img alt="Build Status" src="https://img.shields.io/badge/build-passing-brightgreen.svg" />
  <a href="https://pypi.org/project/sec-edgar-mcp/"><img alt="PyPI" src="https://img.shields.io/pypi/v/sec-edgar-mcp.svg" /></a>
  <a href="https://anaconda.org/stefanoamorelli/sec-edgar-mcp"><img alt="Conda Version" src="https://img.shields.io/conda/vn/stefanoamorelli/sec-edgar-mcp.svg" /></a>
  <a href="https://mseep.ai/app/0132880c-5e83-410b-a1d5-d3df08ed7b5c"><img alt="Verified on MseeP" src="https://mseep.ai/badge.svg" /></a>
  <a href="https://doi.org/10.5281/zenodo.17123166"><img alt="DOI" src="https://zenodo.org/badge/DOI/10.5281/zenodo.17123166.svg" /></a>
</p>

https://github.com/user-attachments/assets/d310eb42-b3ca-467d-92f7-7d132e6274fe

> [!IMPORTANT]
> EDGAR® and SEC® are trademarks of the U.S. Securities and Exchange Commission. This open-source project is not affiliated with or approved by the U.S. Securities and Exchange Commission.

## Introduction 📣

SEC EDGAR MCP is an open-source MCP server that connects AI models to the rich dataset of [SEC EDGAR filings](https://www.sec.gov/edgar). EDGAR (Electronic Data Gathering, Analysis, and Retrieval) is the U.S. SEC's primary system for companies to submit official filings. It contains millions of filings and "increases the efficiency, transparency, and fairness of the securities markets" by providing free public access to corporate financial information. This project makes that trove of public company data accessible to AI assistants (LLMs) for financial research, investment insights, and corporate transparency use cases.

Using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) – an open standard that "enables seamless integration between LLM applications and external data sources and tools" – the SEC EDGAR MCP server exposes a comprehensive set of tools for accessing SEC filing data. Under the hood, it leverages the [EdgarTools Python library](https://github.com/dgunning/edgartools) to fetch data from official SEC sources and performs direct XBRL parsing for exact financial precision. This means an AI agent can ask questions like "What's the latest 10-K filing for Apple?" or "Show me Tesla's exact revenue from their latest 10-K" and the MCP server will retrieve the answer directly from EDGAR's official data with complete accuracy and filing references.

> [!TIP]
> If you use this software, please cite it using the DOI below or following [CITATION.cff](CITATION.cff):
>
> [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17123166.svg)](https://doi.org/10.5281/zenodo.17123166)
>
> **APA Citation:**
>
> Amorelli, S. (2025). *SEC EDGAR MCP (Model Context Protocol) Server* (Version 1.0.6) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.17123166
>
> **BibTeX:**
> ```bibtex
> @software{amorelli_sec_edgar_mcp_2025,
>   title = {{SEC EDGAR MCP (Model Context Protocol) Server}},
>   author = {Amorelli, Stefano},
>   version = {1.0.6},
>   year = {2025},
>   month = {9},
>   url = {https://doi.org/10.5281/zenodo.17123166},
>   doi = {10.5281/zenodo.17123166}
> }
> ```

## Usage 🚀

Once the SEC EDGAR MCP server is running, you can connect to it with any MCP-compatible client (such as an AI assistant or the MCP CLI tool). The client will discover the available EDGAR tools and can invoke them to get real-time data from SEC filings. For example, an AI assistant could use this server to fetch a company's recent filings or query specific financial metrics without manual web searching.

For comprehensive guides, examples, and tool documentation, visit the [SEC EDGAR MCP Documentation](https://sec-edgar-mcp.amorelli.tech/).

### Docker Configuration

To use SEC EDGAR MCP with Docker, add the following configuration to your MCP client:

```json
{
  "mcpServers": {
    "sec-edgar-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "SEC_EDGAR_USER_AGENT=Your Name (name@domain.com)",
        "stefanoamorelli/sec-edgar-mcp:latest"
      ],
      "env": {}
    }
  }
}
```

**Demo**: Here's a demonstration of an AI assistant using SEC EDGAR MCP to retrieve Apple's latest filings and financial facts (click to view the video):

<div align="center">
    <a href="https://www.loom.com/share/17fcd7d891fe496f9a6b8fb85ede66bb">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/17fcd7d891fe496f9a6b8fb85ede66bb-7f8590d1d4bcc2fb-full-play.gif">
    </a>
    <a href="https://www.loom.com/share/17fcd7d891fe496f9a6b8fb85ede66bb">
      <p>SEC EDGAR MCP - Demo - Watch Video</p>
    </a>
</div>

In the demo above, the assistant uses SEC EDGAR MCP tools to retrieve Apple's filings and financial data, showcasing how EDGAR information is fetched and presented in real-time with exact precision and filing references. 📊

## Documentation 📚

For installation and setup instructions, visit the [SEC EDGAR MCP Quickstart Guide](https://sec-edgar-mcp.amorelli.tech/setup/quickstart). For complete tool documentation, usage examples, and configuration guides, visit the [SEC EDGAR MCP Documentation](https://sec-edgar-mcp.amorelli.tech/).

### Running Documentation Locally

To run the documentation locally for development or offline access:

```bash
# Install Mintlify CLI globally
npm i -g mintlify

# Navigate to the docs directory
cd docs

# Start the development server
mintlify dev
```

The documentation will be available at `http://localhost:3000`. Any changes you make to the documentation files will be reflected in real-time.

## Architecture 🏗️

The SEC EDGAR MCP server acts as a middleman between an AI (MCP client) and the SEC's EDGAR backend:

- 🔸 **MCP Client**: Could be an AI assistant (like [Claude](https://claude.ai/) or other MCP-compatible tools) or any app that speaks the MCP protocol. The client sends JSON-RPC requests to invoke tools and receives JSON results.

- 🔸 **MCP Server (SEC EDGAR MCP)**: This server defines comprehensive EDGAR tools and handles incoming requests. It features:
  - **Company Tools**: CIK lookup, company information, and company facts
  - **Filing Tools**: Recent filings, filing content, 8-K analysis, and section extraction
  - **Financial Tools**: Financial statements with direct XBRL parsing for exact precision
  - **Insider Trading Tools**: Form 3/4/5 analysis with detailed transaction data

- 🔸 **EDGAR Data Sources**: The server uses the [edgartools Python library](https://github.com/dgunning/edgartools) to access:
  - **SEC EDGAR REST API**: Official SEC endpoint for company data and filing metadata
  - **Direct XBRL Parsing**: Extracts financial data directly from SEC filings using regex patterns for exact numeric precision
  - **Filing Content**: Downloads and parses complete SEC filing documents (.txt format)

**Key Features**:
- **Deterministic Responses**: All tools include strict instructions to prevent AI hallucination and ensure responses are based only on SEC filing data
- **Exact Precision**: Financial data maintains exact numeric precision (no rounding) as filed with the SEC
- **Filing References**: Every response includes clickable SEC URLs for independent verification
- **Flexible XBRL Extraction**: Uses pattern matching to find financial concepts without hardcoded mappings

**How it works**: The MCP client discovers available tools (company lookup, financial statements, insider transactions, etc.). When invoked, each tool fetches data from SEC sources, applies deterministic processing rules, and returns structured JSON with filing references. This ensures AI responses are accurate, verifiable, and based solely on official SEC data.

## Integrations

By default, the MCP server is configured to use the [stdio](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#stdio) transport. Integrations with platforms such as [Dify](https://dify.ai) require switching to [streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http), or possibly [SSE](https://modelcontextprotocol.io/specification/2024-11-05/basic/transports#http-with-sse) depending on the required [backwards compatibility](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)). Streamable HTTP can be enabled by passing a `--transport streamable-http` argument to `server.py`.  The host and port to listen on default to host `0.0.0.0` and port `9870`.  These values can be over-ridden using the `--host` and `--port` addresses.

NOTE: there is no authentication on the server, and the HTTP exposure has not been tested or assured for any particular threat model.  You would be wise to limit such usage to private, firewalled networks, or private cloud networks.  Having the server directly addressable from the whole internet would be unwise without additional security protections.

## References 📚

- **[SEC EDGAR](https://www.sec.gov/edgar)** – About EDGAR, SEC.gov (2024). EDGAR is the SEC's database for electronic company filings.

- **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)** – Official documentation and SDKs. ModelContextProtocol.io – An open standard for connecting LLMs to tools.

- **[EdgarTools](https://github.com/dgunning/edgartools)** – A modern Python library for accessing SEC EDGAR data with powerful filing analysis capabilities. [GitHub repo](https://github.com/dgunning/edgartools), [Documentation](https://dgunning.github.io/edgartools/).


## Contributors 🤝

A big thank you to all the contributors who have helped make this project better!

<a href="https://github.com/stefanoamorelli/sec-edgar-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=stefanoamorelli/sec-edgar-mcp" />
</a>

## License ⚖️

This open-source project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE). This means:
- You can use, modify, and distribute this software
- If you modify and distribute it, you must release your changes under AGPL-3.0
- If you run a modified version on a server, you must provide the source code to users
- See the LICENSE file for full details

For commercial licensing options or other licensing inquiries, please contact stefano@amorelli.tech.

---

© 2025 [Stefano Amorelli](https://amorelli.tech) – Released under the [GNU Affero General Public License v3.0](LICENSE).  Enjoy! 🎉

