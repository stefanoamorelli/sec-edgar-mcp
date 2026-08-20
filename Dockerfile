FROM python:3.13-slim

# Install server dependencies
RUN pip install --no-cache-dir "mcp[cli]>=1.7.1,<2" "sec-edgar-toolkit[pandas]>=0.2.0" "packaging" "requests" "python-dotenv"

# Copy source
WORKDIR /app
COPY . .

# Ensure local package is discoverable
ENV PYTHONPATH=/app

# The server requires NASDAQ_DATA_LINK_API_KEY to be set at runtime
# Example mcpServers config for your client:
# 
# "mcpServers": {
#   "sec-edgar-mcp": {
#     "command": "docker",
#     "args": [
#       "run",
#       "--rm",
#       "-i",
#       "-e", "SEC_EDGAR_USER_AGENT=<First Name, Last name (your@email.com)>",
#       "stefanoamorelli/sec-edgar-mcp:latest"
#     ]
#   }
# }

CMD ["python", "sec_edgar_mcp/server.py"]
