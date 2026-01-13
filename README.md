# MCP Servers Collection

A collection of Model Context Protocol (MCP) servers for integration with Claude Desktop and Claude Code CLI.

## Available Servers

### BetterTouchTool Bridge (`btt_mcp_bridge`)

MCP server that provides integration with BetterTouchTool, allowing LLMs like Claude to:
- Create, update, and delete BetterTouchTool triggers
- List all triggers or filter by app bundle ID
- Control BetterTouchTool via URL schemes

[See btt_mcp_bridge/README.md for detailed documentation](btt_mcp_bridge/README.md)

### Obsidian Thoughts Assistant (`obsidian_thoughts_mcp`)

MCP server for semantic search and interaction with your Obsidian thoughts collection:
- Semantic search through thoughts using AI embeddings
- Create new AI-generated notes in your Obsidian vault
- Compare thoughts and analyze connections
- Manage spaced repetition cards and decks
- List recent thoughts and get collection statistics

**Requires**: Ollama running locally for embeddings generation

[See obsidian_thoughts_mcp/README.md for detailed documentation](obsidian_thoughts_mcp/README.md)

## Project Structure

```
MCP_Servers/
├── README.md                           # This file
├── btt_mcp_bridge/                    # BetterTouchTool MCP Bridge
│   ├── simplified_direct_runner.py   # Main entry point for MCP
│   ├── simplified_smart_bridge.py    # Simplified bridge implementation
│   ├── smart_btt_bridge.py           # Full bridge implementation
│   ├── requirements.txt              # Python dependencies
│   └── ...                           # Additional files
├── obsidian_thoughts_mcp/            # Obsidian Thoughts Assistant
│   ├── mcp_server.py                 # Main MCP server
│   ├── build_embeddings.py           # Embeddings generation
│   ├── search_thoughts.py            # Search functionality
│   ├── thought_embeddings.csv        # Content embeddings (~6MB)
│   ├── title_embeddings.csv          # Title embeddings (~6MB)
│   ├── requirements.txt              # Python dependencies
│   └── ...                           # Additional files
└── .gitignore                         # Git ignore rules
```

## Installation

Each MCP server has its own dependencies. Navigate to the specific server directory and install:

```bash
# For BetterTouchTool Bridge
cd btt_mcp_bridge
uv pip install -r requirements.txt

# For Obsidian Thoughts Assistant
cd obsidian_thoughts_mcp
pip install -r requirements.txt
pip install mcp[cli]
# Then build embeddings (requires Ollama running)
./build_embeddings_cli.py
```

Or with pip:

```bash
pip install -r requirements.txt
```

## Usage with Claude Desktop

Add servers to your Claude Desktop configuration at:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Example configuration:

```json
{
  "mcpServers": {
    "btt-bridge": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "fastmcp",
        "run",
        "/Users/YOUR_USERNAME/Source/MCP_Servers/btt_mcp_bridge/simplified_direct_runner.py"
      ]
    },
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

## Usage with Claude Code CLI

To add an MCP server to Claude Code:

```bash
claude mcp add
```

Follow the prompts to configure the server.

## Development

Each server is self-contained in its own directory with its own dependencies and documentation.

## License

MIT
