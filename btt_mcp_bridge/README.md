# BTT MCP Bridge

Model Context Protocol (MCP) bridge for BetterTouchTool, allowing LLMs like Claude to interact with BetterTouchTool functionality.

## Features

- Create, update, and delete BetterTouchTool triggers
- List all triggers or filter by app bundle ID
- Simple Python client for programmatic access
- Full FastMCP integration for Claude Desktop

## Installation

1. Install dependencies:

```bash
uv pip install -r requirements.txt
```

Or with pip:

```bash
pip install -r requirements.txt
```

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

Replace `YOUR_USERNAME` with your actual username.

### Running the Server Directly

You can run the server directly:

```bash
python simplified_direct_runner.py
```

Or using the FastMCP CLI:

```bash
fastmcp run simplified_direct_runner.py
```

### Configuration

Set the `BTT_SHARED_SECRET` environment variable if your BetterTouchTool installation requires a shared secret:

```bash
export BTT_SHARED_SECRET="your-secret-here"
python simplified_direct_runner.py
```

### Using the Client Programmatically

```python
import asyncio
from mcp_client import BTTClient

async def main():
    async with BTTClient() as client:
        # List all triggers
        triggers = await client.list_triggers()
        print(f"Found {len(triggers)} triggers")

        # Add a new trigger
        trigger_json = '{"BTTTriggerType":100, "BTTTriggerClass":"BTTTriggerTypeKeyboardShortcut", ...}'
        result = await client.add_trigger(trigger_json)
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Files

- `simplified_direct_runner.py` - Main entry point for MCP (recommended)
- `simplified_smart_bridge.py` - Simplified bridge implementation
- `smart_btt_bridge.py` - Full featured bridge implementation
- `btt_direct.py` - Direct BetterTouchTool interface
- `mcp_client.py` - Python client for programmatic access
- `requirements.txt` - Python dependencies

## Examples

### Adding a Keyboard Shortcut

```python
import asyncio
import json
from mcp_client import BTTClient

async def add_keyboard_shortcut():
    trigger = {
        "BTTTriggerType": 0,
        "BTTTriggerClass": "BTTTriggerTypeKeyboardShortcut",
        "BTTShortcutToSend": "CURRENT_SPACE",
        "BTTTriggerName": "Go to Current Space",
        "BTTAdditionalConfiguration": "{\"BTTTriggerConfig\":{\"BTTKeyboardShortcutKeyboardType\":0,\"BTTKeyboardShortcutBTTP\":13,\"BTTKeyboardShortcutBTTM\":768}}",
        "BTTEnabled2": 1
    }

    async with BTTClient() as client:
        result = await client.add_trigger(json.dumps(trigger))
        print(result)

asyncio.run(add_keyboard_shortcut())
```

### Listing App-Specific Triggers

```python
import asyncio
from mcp_client import BTTClient

async def list_app_triggers():
    async with BTTClient() as client:
        # List triggers for Safari
        safari_triggers = await client.list_triggers(app_bundle_id="com.apple.Safari")
        print(f"Safari has {len(safari_triggers)} triggers")

        for trigger in safari_triggers:
            print(f"- {trigger.get('BTTTriggerName', 'Unnamed')}")

asyncio.run(list_app_triggers())
```

## Troubleshooting

If you encounter connection issues:

1. Ensure BetterTouchTool is running
2. Check that the BTT URL scheme is enabled in BetterTouchTool preferences
3. If using a shared secret, ensure `BTT_SHARED_SECRET` is set correctly
4. Check the logs for detailed error messages

## License

MIT
