<div align="center">

# SEC EDGAR MCP

</div>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img alt="Python: 3.9+" src="https://img.shields.io/badge/python-3.9+-brightgreen.svg" />
  <img alt="Platform: Windows | Mac | Linux" src="https://img.shields.io/badge/platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey.svg" />
  <img alt="Build Status" src="https://img.shields.io/badge/build-passing-brightgreen.svg" />
  <a href="https://pypi.org/project/sec-edgar-mcp/"><img alt="PyPI" src="https://img.shields.io/pypi/v/sec-edgar-mcp.svg" /></a>
</p>

## Disclaimer 🚨

> EDGAR® and SEC® are trademarks of the U.S. Securities and Exchange Commission. This open-source project is not affiliated with or approved by the U.S. Securities and Exchange Commission.

## Introduction 📣

SEC EDGAR MCP is an open-source MCP server that connects AI models to the rich dataset of [SEC EDGAR filings](https://www.sec.gov/edgar). EDGAR (Electronic Data Gathering, Analysis, and Retrieval) is the U.S. SEC's primary system for companies to submit official filings. It contains millions of filings and "increases the efficiency, transparency, and fairness of the securities markets" by providing free public access to corporate financial information. This project makes that trove of public company data accessible to AI assistants (LLMs) for financial research, investment insights, and corporate transparency use cases.

Using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) – an open standard that "enables seamless integration between LLM applications and external data sources and tools" – the SEC EDGAR MCP server exposes a set of tools backed by the official [SEC EDGAR REST API](https://www.sec.gov/edgar/sec-api-documentation). Under the hood, it leverages the [Python secedgar SDK](https://github.com/sec-edgar/sec-edgar) (an unofficial wrapper for SEC's API) to fetch data like company filings and financial facts. This means an AI agent can ask questions like "What's the latest 10-K filing for Apple?" or "Show me Tesla's total revenue in 2021" and the MCP server will retrieve the answer directly from EDGAR's official data.

## Usage 🚀

Once the SEC EDGAR MCP server is running, you can connect to it with any MCP-compatible client (such as an AI assistant or the MCP CLI tool). The client will discover the available EDGAR tools and can invoke them to get real-time data from SEC filings. For example, an AI assistant could use this server to fetch a company's recent filings or query specific financial metrics without manual web searching.

**Demo**: Here's a demonstration of an AI assistant using SEC EDGAR MCP to retrieve Apple's latest filings and financial facts (click to view the video):

<div align="center">
    <a href="https://www.loom.com/share/17fcd7d891fe496f9a6b8fb85ede66bb">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/17fcd7d891fe496f9a6b8fb85ede66bb-7f8590d1d4bcc2fb-full-play.gif">
    </a>
    <a href="https://www.loom.com/share/17fcd7d891fe496f9a6b8fb85ede66bb">
      <p>SEC EDGAR MCP - Demo - Watch Video</p>
    </a>
</div>

In the demo above, the assistant calls the `get_submissions` tool with Apple's CIK and then uses `get_company_concepts` to fetch a specific financial concept, showcasing how EDGAR data is retrieved and presented in real-time. 📊

## Installation 🛠

Follow these steps to set up and run the `SEC EDGAR MCP` server:

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/sec-edgar-mcp.git
cd sec-edgar-mcp
```

2. **Install dependencies**: Ensure you have [Python 3.9+](https://www.python.org/downloads/) installed. Install the required packages, including the [MCP framework](https://pypi.org/project/mcp/) and [secedgar SDK](https://pypi.org/project/sec-edgar/):

```bash
pip install mcp secedgar
```

3. **Configure SEC EDGAR API access**: The SEC API requires a User-Agent string for all requests. Create a `.env` file in the project directory and add your user agent info:

```
SEC_API_USER_AGENT="Your Name (your.email@domain.com)"
PYTHONPATH=/path/to/your/local/cloned/repo/sec-edgar-mcp
```
This identifies your application to the SEC (replace with your details). The server will load this from the environment to authenticate to EDGAR.

4. **Start the MCP server**: Launch the server to begin listening for MCP clients. For example:

```bash
mcp install sec_edgar_mcp/server.py --env-file .env --name "SEC EDGAR MCP Server" --with secedgar==0.6.0a0
```
Once running, the server will register its tools (see below) and await client connections. You should see logs indicating it's ready. 🎉

Now the server is up and running, ready to serve EDGAR data to any MCP client! You can use the MCP CLI or an AI platform (e.g. Claude Desktop) to connect to localhost (or the appropriate transport) and start issuing tool calls.

## Tools 🔧

SEC EDGAR MCP exposes several tools (functions) from the SEC EDGAR API. These tools allow retrieval of different types of data:

- **Company Submissions** – recent filings and metadata for a company (by CIK).
- **Company Concept** – detailed data for a specific financial concept (XBRL tag) for a company.
- **Company Facts** – all available financial facts for a company.
- **XBRL Frames** – aggregated data for a financial concept across companies or time frames.

Each tool is defined with a name, description, and input parameters. AI assistants can invoke them via MCP's JSON-RPC interface. Below is a list of the tools with details and examples of how to call them (click to expand):

<details>
<summary><strong>📁 get_submissions</strong> – Fetch a company's submissions (filings history)</summary>

Description: Returns the submission history for a given company, identified by its CIK. The response includes company info (name, ticker, etc.) and recent filings (forms, dates, report period, etc.). This is useful for getting a list of the latest filings (10-K, 10-Q, 8-K, etc.) a company has made.

Example call (`MCP` `JSON-RPC`):

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "get_submissions",
    "arguments": { "cik": "0000320193" }
  }
}
```

Example response (truncated):

```json
{
  "cik": "0000320193",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "filings": {
    "recent": {
      "form": ["10-K", "10-Q", ...],
      "filingDate": ["2023-10-26", "2023-07-27", ...],
      "reportDate": ["2023-09-30", "2023-06-30", ...],
      "primaryDocument": ["aapl-2023-10k.htm", "aapl-2023-q3.htm", ...],
      ...
    }
  }
}
```

In this example, calling `get_submissions` for Apple (`CIK` `0000320193`) returned a `JSON` with Apple's basic info and a list of its most recent 10-K and 10-Q filings (with their dates and document names, etc.).
</details>

<details>
<summary><strong>💡 get_company_concepts</strong> – Get a specific reported concept for a company</summary>

Description: Fetches all reported values for a single financial concept (XBRL tag) for a given company. You must specify the company's CIK, the accounting taxonomy (e.g. us-gaap for U.S. GAAP financials), and the specific tag (concept name, e.g. AccountsPayableCurrent). The response includes metadata about that concept and a time-series of reported values (by year/quarter).

Example call (`MCP` `JSON-RPC`):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_company_concepts",
    "arguments": {
      "cik": "0000320193",
      "taxonomy": "us-gaap",
      "tag": "AccountsPayableCurrent"
    }
  }
}
```

Example response (truncated):

```json
{
  "cik": 320193,
  "taxonomy": "us-gaap",
  "tag": "AccountsPayableCurrent",
  "label": "Accounts Payable, Current",
  "description": "The carrying value of accounts payable as of the balance sheet date.",
  "entityName": "Apple Inc.",
  "units": {
    "USD": [
      { "end": "2022-09-24", "val": 64220000000, ... },
      { "end": "2021-09-25", "val": 54763000000, ... },
      ...
    ]
  }
}
```

The above shows Apple's "Accounts Payable, Current" (us-gaap taxonomy) values in USD for recent year-end dates. Each entry under units -> USD includes the period end date and the value reported. This tool lets an AI retrieve specific line-items from a company's financial statements as reported in their filings.
</details>

<details>
<summary><strong>🗃️ get_company_facts</strong> – Retrieve all facts for a company (full XBRL fact set)</summary>

Description: Returns all available XBRL facts for a given company (by CIK). This is a comprehensive dataset of that company's financial facts, including multiple taxonomies (e.g. general company info in dei, financial statements in us-gaap, etc.). The response is a nested JSON grouping facts by taxonomy and then by individual tags, with arrays of values.

Example call (`MCP` `JSON-RPC`):

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_company_facts",
    "arguments": { "cik": "0000320193" }
  }
}
```

Example response (truncated):

```json
{
  "cik": 320193,
  "entityName": "Apple Inc.",
  "facts": {
    "dei": {
      "EntityCommonStockSharesOutstanding": {
        "label": "Entity Common Stock, Shares Outstanding",
        "units": { "shares": [ ... ] }
      },
      "EntityPublicFloat": {
        "label": "Entity Public Float",
        "units": { "USD": [ ... ] }
      },
      ...
    },
    "us-gaap": {
      "AccountsPayableCurrent": {
        "label": "Accounts Payable, Current",
        "units": { "USD": [ { "end": "2022-09-24", "val": 64220000000 }, ... ] }
      },
      "AccountsReceivableNet": {
        "label": "Accounts Receivable, Net",
        "units": { "USD": [ ... ] }
      },
      ...
    }
  }
}
```

This truncated example shows the structure of get_company_facts output for Apple. It includes dei facts (like shares outstanding) and us-gaap financial facts (like Accounts Payable, Accounts Receivable, etc.), each with their values. An AI could use this to pull a range of data points from a company's filings in one call (though often it's more data than needed, so targeting a specific concept with get_company_concepts is preferable for focused questions).
</details>

<details>
<summary><strong>🌐 get_xbrl_frames</strong> – Query XBRL "frames" (data across entities or time)</summary>

Description: Retrieves data for a given financial concept across all companies or a set time frame. In EDGAR's API, a "frame" is essentially an aggregation for a specific tag, unit, and period (for example, all companies' values for Revenue in Q1 2023). You need to specify the taxonomy, tag, unit (e.g. USD), year, and period (annual or quarter). This tool returns a list of data points from all entities that reported that concept in that period.

Example call (MCP JSON-RPC):

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_xbrl_frames",
    "arguments": {
      "taxonomy": "us-gaap",
      "tag": "AccountsPayableCurrent",
      "unit": "USD",
      "year": 2019,
      "quarter": 1
    }
  }
}
```

Example response (truncated):

```json
{
  "taxonomy": "us-gaap",
  "tag": "AccountsPayableCurrent",
  "uom": "USD",
  "ccp": "CY2019Q1I",  <!-- Calendar Year 2019, Q1, Instantaneous -->
  "data": [
    {
      "cik": 1555538,
      "entityName": "SUNCOKE ENERGY PARTNERS, L.P.",
      "end": "2019-03-31",
      "val": 78300000
    },
    {
      "cik": 11199,
      "entityName": "BEMIS CO INC",
      "end": "2019-03-31",
      "val": 465700000
    },
    ... (thousands more data points) ...
  ]
}
```

This example asks for the value of "Accounts Payable, Current" (in USD) for Q1 2019. The result includes an array of all companies that reported that metric at the end of Q1 2019, each with their CIK, name, and value. There were many companies (in this case, the frame returned 3388 data points). This is useful for broad analyses (e.g., finding industry totals or comparing peers), though an LLM would typically filter or request a specific company's data instead of retrieving thousands of entries at once.
</details>

> Note: The JSON structures above are directly returned from the SEC EDGAR API via the secedgar SDK. The MCP server does not alter the data, so you get the same fields as the official API. All tools require a valid CIK (Central Index Key) for company-specific queries – you can use the [SEC's CIK lookup tool](https://www.sec.gov/edgar/searchedgar/cik) if you only know a ticker or name.

## Architecture 🏗️

The SEC EDGAR MCP server acts as a middleman between an AI (MCP client) and the SEC's EDGAR backend:

- 🔸 **MCP Client**: Could be an AI assistant (like [Claude](https://claude.ai/) or [GPT-4](https://openai.com/gpt-4) with an MCP plugin) or any app that speaks the MCP protocol. The client sends JSON-RPC requests to invoke tools (e.g. get_submissions) and receives JSON results.

- 🔸 **MCP Server (SEC EDGAR MCP)**: This server (the project you are reading about) defines the EDGAR tools and handles incoming tool requests. When a request comes in, the server uses the [secedgar Python SDK](https://github.com/sec-edgar/sec-edgar) to call the SEC EDGAR REST API and then returns the response back over MCP.

- 🔸 **SEC EDGAR REST API**: The official SEC endpoint ([data.sec.gov](https://data.sec.gov/)) that provides EDGAR data in JSON format. The secedgar library communicates with this REST API, abiding by its [usage policies](https://www.sec.gov/developer) (including rate limits and user agent identification).

**How it works**: The MCP client first queries the server's tool list (discovering functions like get_submissions, etc.). The AI can then decide to call a tool by name with appropriate parameters. The server receives the tools/call request, executes the corresponding EDGAR API call via secedgar, and returns the data. This response is sent back to the AI client in a structured JSON format that the AI can read and incorporate into its answer or reasoning.

In essence, SEC EDGAR MCP bridges the gap between natural language questions and the raw SEC filings data. By adhering to MCP, it standardizes the way AI models can fetch real-world financial data, using officially sourced information for accurate and up-to-date answers.

## References 📚

- **[SEC EDGAR](https://www.sec.gov/edgar)** – About EDGAR, SEC.gov (2024). EDGAR is the SEC's database for electronic company filings.

- **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)** – Official documentation and SDKs. ModelContextProtocol.io – An open standard for connecting LLMs to tools.

- **[SEC EDGAR API Python SDK (secedgar)](https://github.com/sec-edgar/sec-edgar)** – An unofficial Python wrapper for SEC's EDGAR REST API. [GitHub repo](https://github.com/sec-edgar/sec-edgar), [Documentation](https://sec-edgar.github.io/sec-edgar/).


## License ⚖️

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, and distribute it. See the LICENSE file for details.

---

© 2025 Stefano Amorelli – Released under the MIT license.  Enjoy! 🎉

