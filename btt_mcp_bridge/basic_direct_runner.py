#!/usr/bin/env python3
"""
Direct runner for the basic smart BTT bridge.
This file is used by the install_claude.py script.
"""

import os
import sys
import logging

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add the parent directory to the Python path to ensure imports work
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("basic_direct_runner")

# Import the bridge
try:
    from btt_mcp_bridge.basic_smart_bridge import mcp
    logger.info("Successfully imported the Basic Smart BTT Bridge")
except ImportError as e:
    logger.error(f"Error importing bridge: {e}")
    sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting Basic Smart BTT Bridge...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1) 