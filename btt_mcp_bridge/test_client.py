#!/usr/bin/env python3
"""
Test client for the BTT MCP server.
"""

import asyncio
from mcp.client import Client

async def main():
    # Connect to the MCP server
    print("Connecting to MCP server...")
    async with Client() as client:
        # List available tools
        tools = await client.list_tools()
        print(f"\nAvailable tools: {[t.name for t in tools]}")
        
        # Test the list_btt_triggers function
        print("\nTesting list_btt_triggers...")
        try:
            triggers = await client.call("list_btt_triggers")
            print(f"Success! Found {len(triggers)} triggers.")
            if triggers:
                # Just show the first trigger as an example
                print(f"\nExample trigger: {triggers[0]['BTTTriggerName']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 