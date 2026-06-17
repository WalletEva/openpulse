## Agent Integration Guide / Agent 接入指南

This guide explains how to integrate OpenPulse with AI agents via the MCP (Model Context Protocol) server.

### Prerequisites

1. Install OpenPulse:
```bash
pip install openpulse
# or install from source
git clone https://github.com/WalletEva/openpulse.git
cd openpulse
pip install -e .
```

2. Initialize the database:
```bash
openpulse init
```

3. (Optional) Add information sources:
```bash
openpulse source add --name reuters --type rsshub --adapter rsshub --route /reuters/world --category news
openpulse source add --name bbc --type rsshub --adapter rsshub --route /bbc/zhongwen/simp --category news
openpulse source add --name weibo-hot --type rsshub --adapter rsshub --route /weibo/search/hot --category social
```

### MCP Server Overview

OpenPulse exposes a FastMCP server that provides the following tools to AI agents:

| Tool | Description |
|------|-------------|
| `search_articles` | Search collected articles by keyword, source, and language |
| `collect_now` | Trigger immediate collection from a source, RSSHub route, or feed URL |
| `get_trending_topics` | Get trending keywords from recent articles |
| `get_article_detail` | Get full content of a specific article |
| `get_sources` | List configured information sources |
| `manage_watchlist` | Add/remove/list keyword watchlists |

### Integration with Hermes Agent

Add the following to your Hermes `config.yaml`:

```yaml
mcp:
  servers:
    - name: openpulse
      command: python
      args: ["-m", "openpulse.mcp_server"]
      env:
        OPENPULSE_DB_PATH: "~/.openpulse/openpulse.db"
        # Optional: connect to a remote RSSHub instance
        # OPENPULSE_RSSHUB_BASE_URL: "http://localhost:1200"
```

Hermes will automatically discover all OpenPulse MCP tools on startup. Example usage in conversation:

```
User: What's trending in tech news today?
Hermes: [calls get_trending_topics(language="en", hours=24)]
       [calls search_articles(query="AI", language="en", limit=5)]
       Here are today's top tech stories...
```

### Integration with OpenClaw

Add the following to your OpenClaw `openclaw.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "openpulse",
        "command": "python",
        "args": ["-m", "openpulse.mcp_server"],
        "env": {
          "OPENPULSE_DB_PATH": "~/.openpulse/openpulse.db"
        }
      }
    ]
  }
}
```

OpenClaw will discover tools via `mcp.list` and invoke them with `mcp.call`.

### Configuration via Environment Variables

All OpenPulse settings can be controlled via environment variables (prefixed with `OPENPULSE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENPULSE_DATABASE_URL` | `sqlite:///~/.openpulse/openpulse.db` | Database connection URL |
| `OPENPULSE_RSSHUB_BASE_URL` | `http://localhost:1200` | RSSHub instance URL |
| `OPENPULSE_NEWSAPI_KEY` | (none) | NewsAPI.org API key |
| `OPENPULSE_YOUTUBE_API_KEY` | (none) | YouTube Data API key |
| `OPENPULSE_SCHEDULER_ENABLED` | `true` | Enable/disable background scheduler |
| `OPENPULSE_LOG_LEVEL` | `INFO` | Logging level |

### Usage Examples

#### Collect and Search

```python
# The agent can call these tools via MCP:

# 1. Collect from Reuters immediately
collect_now(rsshub_route="/reuters/world", limit=20)

# 2. Search for AI-related articles
search_articles(query="artificial intelligence", language="en", limit=10)

# 3. Get article details
get_article_detail(article_id="abc123def456")
```

#### Monitor Keywords

```python
# Add keywords to watchlist
manage_watchlist(action="add", keywords=["OpenAI", "GPT-5", "quantum computing"])

# Check trending topics
get_trending_topics(language="en", hours=24, limit=10)
```

#### List Sources

```python
# Get all configured sources
get_sources()

# Get only enabled news sources
get_sources(category="news", enabled_only=True)
```

### Running MCP Server Standalone

For testing, you can run the MCP server directly:

```bash
python -m openpulse.mcp_server
```

This starts the MCP server on stdio, ready to accept tool calls from any MCP-compatible client.

### REST API (Alternative Integration)

If MCP is not available, OpenPulse also provides a REST API:

```bash
# Start the API server
openpulse serve --host 0.0.0.0 --port 8000

# Search articles via curl
curl "http://localhost:8000/api/v1/articles?q=AI&lang=en&limit=20"
```

### Troubleshooting

- **"Source not found"**: Run `openpulse source list` to check configured sources, then add missing ones with `openpulse source add`.
- **RSSHub connection errors**: Ensure RSSHub is running at the configured URL. You can self-host RSSHub with `docker run -p 1200:1200 diygod/rsshub`.
- **Database locked**: Only one process should write to SQLite at a time. If running both the API server and MCP server, consider switching to PostgreSQL.
