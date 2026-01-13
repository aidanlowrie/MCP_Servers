#!/usr/bin/env python3
"""
Example of using the BTT_MCP bridge to control BetterTouchTool.
"""
import asyncio
import json
import os
from mcp.client import ClientSession

async def main():
    print("🚀 Connecting to BTT_MCP server...")
    # Connect to the MCP server
    client = ClientSession(url="http://127.0.0.1:6274")
    await client.initialize()
    
    try:
        # Get a list of available tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # 1. List all BTT triggers
        print("\n1️⃣ Listing all BTT triggers...")
        triggers = await client.call("list_btt_triggers")
        print(f"Found {len(triggers)} triggers")
        
        # Display first trigger as an example
        if triggers:
            first = triggers[0]
            print(f"\n📋 Example trigger:")
            print(f"  Name: {first.get('BTTTriggerName', 'Unnamed')}")
            print(f"  Type: {first.get('BTTTriggerType')}")
            print(f"  UUID: {first.get('BTTUUID')}")
            
        # 2. Create a simple keyboard shortcut
        print("\n2️⃣ Creating a new keyboard shortcut trigger...")
        
        # Example trigger: Cmd+Shift+H to hide all applications
        trigger_json = json.dumps({
            "BTTTriggerType": 0,  # Keyboard shortcut
            "BTTTriggerClass": "BTTTriggerTypeKeyboardShortcut",
            "BTTPredefinedActionType": 96,  # Hide all applications
            "BTTPredefinedActionName": "Hide All Applications",
            "BTTTriggerName": "Hide All Apps (Added by MCP)",
            "BTTShortcutToSend": "h",
            "BTTAdditionalConfiguration": "1048848",  # Cmd+Shift
            "BTTTriggerOnKeyDown": 1,
            "BTTEnabled2": 1,
            "BTTKeyboardShortcutKeyboardType": 0
        })
        
        # Ask user before adding trigger
        confirm = input("\nDo you want to add this trigger to BTT? (y/n): ")
        if confirm.lower() == 'y':
            result = await client.call("add_btt_trigger", trigger_json=trigger_json)
            print(f"Result: {result}")
            print("\n✅ Trigger added! Press Cmd+Shift+H to hide all applications.")
        else:
            print("\n❌ Trigger creation canceled.")
            
        # 3. Show how to delete a trigger (commented out for safety)
        print("\n3️⃣ To delete a trigger, you would use:")
        print('await client.call("delete_btt_trigger", uuid="TRIGGER_UUID_HERE")')
    
    finally:
        # Always close the client session
        await client.close()
        
if __name__ == "__main__":
    asyncio.run(main()) 