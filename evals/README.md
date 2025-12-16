# SEC EDGAR MCP Server Evaluations

Promptfoo-based evaluation suite for testing the SEC EDGAR MCP Server tools.

## Setup

```bash
cd evals
npm install
export SEC_EDGAR_USER_AGENT="YourApp your@email.com"
```

## Running Evaluations

```bash
npm run eval              # Run all tests
npm run eval:company      # Company tools only
npm run eval:filings      # Filing tools only
npm run eval:financial    # Financial tools only
npm run eval:insider      # Insider trading tools only
npm run view              # View results in browser
```

## Configuration

Tests run sequentially with 2s delay between requests to respect SEC API rate limits.
