"""
A simple client for interacting with the BTT MCP Bridge.

Usage:
    python mcp_client.py

This client can be used directly or as a module to interact with BetterTouchTool.
"""

import asyncio
from typing import List, Dict, Optional

from fastmcp import Client


class BTTClient:
    """Client for interacting with the BetterTouchTool MCP Bridge."""

    def __init__(self, server_path: str = "btt_mcp_bridge/server.py"):
        """
        Initialize the BTT MCP client.
        
        Args:
            server_path: Path to the server.py file
        """
        self.server_path = server_path
        self.client = Client(server_path)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def add_trigger(self, trigger_json: str) -> str:
        """
        Add a new BTT trigger.
        
        Args:
            trigger_json: Full JSON definition of a BTT trigger
        
        Returns:
            Response message
        """
        result = await self.client.call_tool("add_btt_trigger", {"trigger_json": trigger_json})
        return result.text
    
    async def update_trigger(self, uuid: str, patch_json: str) -> str:
        """
        Update an existing BTT trigger.
        
        Args:
            uuid: UUID of the trigger to update
            patch_json: JSON patch with fields to update
        
        Returns:
            Response message
        """
        result = await self.client.call_tool(
            "update_btt_trigger", 
            {"uuid": uuid, "patch_json": patch_json}
        )
        return result.text
    
    async def delete_trigger(self, uuid: str) -> str:
        """
        Delete a BTT trigger.
        
        Args:
            uuid: UUID of the trigger to delete
        
        Returns:
            Response message
        """
        result = await self.client.call_tool("delete_btt_trigger", {"uuid": uuid})
        return result.text
    
    async def list_triggers(self, app_bundle_id: Optional[str] = None) -> List[Dict]:
        """
        List all BTT triggers.
        
        Args:
            app_bundle_id: Optional bundle ID to filter triggers
        
        Returns:
            List of trigger dictionaries
        """
        params = {}
        if app_bundle_id:
            params["app_bundle_id"] = app_bundle_id
            
        result = await self.client.call_tool("list_btt_triggers", params)
        return result.json


async def demo():
    """Run a simple demonstration of the BTT client."""
    async with BTTClient() as client:
        # List all triggers
        triggers = await client.list_triggers()
        print(f"Found {len(triggers)} triggers")
        
        # Print the first trigger (if any)
        if triggers:
            print(f"First trigger: {triggers[0]['BTTTriggerName']}")


if __name__ == "__main__":
    asyncio.run(demo()) 