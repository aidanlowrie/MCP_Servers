#!/usr/bin/env python3
"""
Direct runner for the Smart BTT MCP Bridge without requiring uv.
This provides better response handling to prevent timeouts.
"""

import os
import sys
import importlib.util
import logging
import traceback

# Set up logging to stderr to help with debugging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("smart_btt_mcp_bridge")

# Log system information
logger.debug(f"Python version: {sys.version}")
logger.debug(f"Python executable: {sys.executable}")
logger.debug(f"Sys path: {sys.path}")

# Get the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.debug(f"Current directory: {current_dir}")

# Path to the smart_btt_bridge.py file
bridge_path = os.path.join(current_dir, "smart_btt_bridge.py")
logger.debug(f"Bridge path: {bridge_path}")

if not os.path.exists(bridge_path):
    logger.error(f"Bridge file not found at {bridge_path}")
    sys.exit(1)

logger.info(f"Loading smart bridge from {bridge_path}")

try:
    # Import the smart_btt_bridge.py module
    spec = importlib.util.spec_from_file_location("smart_btt_bridge", bridge_path)
    bridge = importlib.util.module_from_spec(spec)
    sys.modules["smart_btt_bridge"] = bridge
    spec.loader.exec_module(bridge)

    # Export the MCP object directly so Claude can find it
    # This is the key part - Claude looks for a FastMCP object named mcp, server, or app
    mcp = bridge.mcp
    logger.info(f"Successfully imported smart bridge module with MCP: {mcp.name}")
    
    # Log available tools to help with debugging
    if hasattr(mcp, 'tools'):
        tools = mcp.tools
        logger.debug(f"Available tools: {[t.name for t in tools]}")
except Exception as e:
    logger.error(f"Error importing bridge module: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def main():
    """Run the MCP server directly."""
    try:
        logger.info("Starting Smart BTT MCP Bridge...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Error running Smart BTT MCP Bridge: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 