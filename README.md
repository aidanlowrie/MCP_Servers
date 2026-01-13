# MCP Servers Collection

A collection of Model Context Protocol (MCP) servers for integration with Claude Desktop and Claude Code CLI.

## Available Servers

### BetterTouchTool Bridge (`btt_mcp_bridge`)

MCP server that provides integration with BetterTouchTool, allowing LLMs like Claude to:
- Create, update, and delete BetterTouchTool triggers
- List all triggers or filter by app bundle ID
- Control BetterTouchTool via URL schemes

[See btt_mcp_bridge/README.md for detailed documentation](btt_mcp_bridge/README.md)

## Project Structure

```
MCP_Servers/
├── README.md                    # This file
├── btt_mcp_bridge/             # BetterTouchTool MCP Bridge
│   ├── simplified_direct_runner.py  # Main entry point for MCP
│   ├── simplified_smart_bridge.py   # Simplified bridge implementation
│   ├── smart_btt_bridge.py          # Full bridge implementation
│   ├── requirements.txt             # Python dependencies
│   └── ...                          # Additional files
└── .gitignore                   # Git ignore rules
```

## Installation

Each MCP server has its own dependencies. Navigate to the specific server directory and install:

```bash
cd btt_mcp_bridge
uv pip install -r requirements.txt
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

Example configuration for BTT Bridge:

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
        "/Users/YOUR_USERNAME/Desktop/Home/Source/MCP_Servers/btt_mcp_bridge/simplified_direct_runner.py"
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
