#!/usr/bin/env python3
"""
Simple client for BTT MCP using direct shell commands.
"""
import json
import subprocess
import sys

def run_command(command):
    """Run a shell command and return the output."""
    process = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    return process.stdout.strip()

def main():
    print("🔍 BTT MCP Client")
    print("================")
    
    # Use fastmcp CLI to send commands to the server
    print("\n1️⃣ Testing list_btt_triggers...")
    
    # Create a JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "list_btt_triggers"
    }
    
    # Write request to a temp file
    with open("request.json", "w") as f:
        json.dump(request, f)
    
    # Send the request using fastmcp
    result = run_command("cat request.json | fastmcp run server.py --transport stdio")
    
    try:
        # Parse the response
        response = json.loads(result)
        
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
        print("Error decoding response:")
        print(result)
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main() 