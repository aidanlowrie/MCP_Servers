# Obsidian Thoughts MCP Server

Model Context Protocol (MCP) server for semantic search and interaction with your Obsidian thoughts collection.

## Features

- **Semantic Search**: Search thoughts by content or title similarity using AI embeddings
- **Note Writing**: Create new AI-generated notes directly in your Obsidian vault
- **Spaced Repetition**: Create and manage spaced repetition cards with deck integration
- **Thought Analysis**: Compare thoughts, analyze similarities, and explore connections
- **Recent Thoughts**: List recently modified thoughts for quick access
- **Statistics**: Get insights about your thoughts collection
- **Keyword Search**: Exact text matching when needed

## Prerequisites

- Python 3.7+ with pip
- Ollama running locally (for embeddings generation)
- Obsidian vault with thoughts in `1 - Thoughts` directory
- Claude Desktop with MCP support

## Installation

1. Install dependencies:

```bash
cd obsidian_thoughts_mcp
pip install -r requirements.txt
pip install mcp[cli]
```

Or with uv:

```bash
uv pip install -r requirements.txt
uv pip install mcp[cli]
```

2. **Build embeddings** (first time only):

```bash
./build_embeddings_cli.py
```

This requires Ollama to be running locally. The embeddings are stored in CSV files and persist between sessions.

## Configuration

### With Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "thoughts-assistant": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/Users/YOUR_USERNAME/Source/MCP_Servers/obsidian_thoughts_mcp/mcp_server.py"
      ]
    }
  }
}
```

Replace `YOUR_USERNAME` with your actual username.

### Vault Location

The server is configured for the vault at:
```
/Users/aidanlowrie/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Brain/1 - Thoughts
```

If your vault is elsewhere, edit `mcp_server.py` line 92:
```python
THOUGHTS_DIR = "/path/to/your/vault/1 - Thoughts"
```

## Usage with Claude

Once installed and Claude Desktop is restarted, you can use commands like:

- "List my 5 most recent thoughts"
- "Search my thoughts for information about productivity"
- "Find thoughts with titles related to meditation"
- "Write a detailed note about [topic] and save it to my Obsidian vault"

See [MCP_README.md](MCP_README.md) for complete documentation.

## Available Tools

- **build_thought_embeddings**: Build embeddings for all thoughts
- **search_by_content**: Search thoughts by content similarity
- **search_by_title**: Search thoughts by title similarity
- **get_thought_content**: Get full content of a specific thought
- **compare_thoughts**: Compare two thoughts and calculate similarity
- **list_recent_thoughts**: List recently modified thought files
- **write_note**: Write new AI-generated notes to your vault
- **create_sr_cards**: Create spaced-repetition cards
- **list_sr_decks** / **create_sr_deck**: Manage spaced repetition decks

## Files

- `mcp_server.py` - Main MCP server (1,706 lines)
- `build_embeddings.py` - Embeddings generation using Ollama
- `build_embeddings_cli.py` - CLI for building embeddings
- `search_thoughts.py` - Search functionality
- `thought_embeddings.csv` - Content embeddings (~6MB)
- `title_embeddings.csv` - Title embeddings (~6MB)
- `requirements.txt` - Python dependencies
- `MCP_README.md` - Detailed usage documentation

## Troubleshooting

**Server won't connect:**
1. Ensure embeddings are built (`./build_embeddings_cli.py`)
2. Verify Ollama is running
3. Check Claude Desktop logs
4. Verify vault path in `mcp_server.py`

**Permission errors:**
- `xattr -cr obsidian_thoughts_mcp/`
- `chmod +x *.py *.sh`

## Maintenance

Run `./build_embeddings_cli.py` periodically to update embeddings as your thoughts collection grows.

## Environment Variables

- `OLLAMA_BASE_URL`: Ollama API URL (default: "http://localhost:11434")
- `EMBEDDING_MODEL`: Model for embeddings (default: "mxbai-embed-large:latest")

## License

MIT 