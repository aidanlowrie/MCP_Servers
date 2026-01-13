#!/usr/bin/env python3
"""
Direct runner for the BTT MCP Bridge without requiring uv.
This provides better response handling to prevent timeouts.
"""

import os
import sys
import importlib.util
import logging

# Set up logging to stderr to help with debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("btt_mcp_bridge")

# Get the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the server.py file
server_path = os.path.join(current_dir, "server.py")

logger.info(f"Loading server from {server_path}")

# Import the server.py module
spec = importlib.util.spec_from_file_location("server", server_path)
server = importlib.util.module_from_spec(spec)
sys.modules["server"] = server
spec.loader.exec_module(server)

# Export the MCP object directly so Claude can find it
# This is the key part - Claude looks for a FastMCP object named mcp, server, or app
mcp = server.mcp

logger.info(f"Successfully imported server module with MCP: {mcp.name}")

def main():
    """Run the MCP server directly."""
    try:
        logger.info("Starting MCP server...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error running BTT MCP Bridge: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 