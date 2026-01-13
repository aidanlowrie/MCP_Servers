#!/usr/bin/env python3
"""
Launcher script for the BTT MCP Bridge.
This script is used by Claude Desktop to run the server without requiring uv.
"""

import sys
import os
import importlib.util

def main():
    """Import and run the server module directly."""
    # Get the directory of this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the server.py file
    server_path = os.path.join(current_dir, "server.py")
    
    # Import the server.py module
    spec = importlib.util.spec_from_file_location("server", server_path)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    
    # Run the MCP server
    server.mcp.run()

if __name__ == "__main__":
    main() 