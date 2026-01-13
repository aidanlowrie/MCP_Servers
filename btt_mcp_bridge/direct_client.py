#!/usr/bin/env python3
"""
Direct client for interacting with the BTT MCP server.
"""
import os
import sys
import json
import asyncio
import subprocess

async def main():
    print("🔍 BTT MCP Client")
    print("================")
    
    # We'll use direct subprocess calls to communicate with the MCP server
    # This bypasses any client library issues
    
    print("\n1️⃣ Testing list_btt_triggers...")
    try:
        # Run the server in a subprocess and capture its output
        process = await asyncio.create_subprocess_exec(
            "python", "server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Create JSON-RPC request for list_btt_triggers
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "list_btt_triggers"
        }
        
        # Send the request
        print(f"Sending request: {json.dumps(request)}")
        process.stdin.write(f"{json.dumps(request)}\n".encode())
        await process.stdin.drain()
        
        # Read the response
        response_line = await process.stdout.readline()
        response_text = response_line.decode().strip()
        print(f"Raw response: {response_text}")
        
        # Parse the response
        try:
            response = json.loads(response_text)
            if "result" in response:
                triggers = response["result"]
                print(f"\nFound {len(triggers)} triggers")
                
                # Display first trigger as an example
                if triggers:
                    first = triggers[0]
                    print(f"\n📋 Example trigger:")
                    print(f"  Name: {first.get('BTTTriggerName', 'Unnamed')}")
                    print(f"  Type: {first.get('BTTTriggerType')}")
                    print(f"  UUID: {first.get('BTTUUID', 'Unknown')}")
            else:
                print(f"Error: {response.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            print("Error decoding response JSON")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Make sure to terminate the subprocess
        if 'process' in locals():
            process.terminate()
            await process.wait()
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(main()) 