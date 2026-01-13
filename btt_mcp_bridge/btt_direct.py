#!/usr/bin/env python3
"""
Direct BTT access script (no MCP, just using AppleScript directly).
"""
import json
import subprocess
import sys

def run_osascript(script):
    """Run AppleScript via osascript command."""
    process = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    return process.stdout.strip()

def list_btt_triggers():
    """Get all BTT triggers using AppleScript."""
    script = 'tell application "BetterTouchTool" to get_triggers'
    result = run_osascript(script)
    return json.loads(result)

def main():
    print("🔍 BTT Direct Client")
    print("===================")
    
    # 1. List all triggers
    print("\n1️⃣ Listing all BTT triggers...")
    try:
        triggers = list_btt_triggers()
        print(f"Found {len(triggers)} triggers")
        
        # Display first trigger as an example
        if triggers:
            first = triggers[0]
            print(f"\n📋 Example trigger:")
            print(f"  Name: {first.get('BTTTriggerName', 'Unnamed')}")
            print(f"  Type: {first.get('BTTTriggerType')}")
            print(f"  UUID: {first.get('BTTUUID', 'Unknown')}")
            
            # List the first 5 triggers
            print("\n📋 First 5 triggers:")
            for i, trigger in enumerate(triggers[:5]):
                print(f"  {i+1}. {trigger.get('BTTTriggerName', 'Unnamed')}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Offer to add a sample trigger
    print("\n2️⃣ Would you like to add a sample trigger?")
    choice = input("Add a 'Hide All Apps' keyboard shortcut (Cmd+Shift+H)? (y/n): ")
    
    if choice.lower() == 'y':
        # Define the trigger
        trigger_json = json.dumps({
            "BTTTriggerType": 0,  # Keyboard shortcut
            "BTTTriggerClass": "BTTTriggerTypeKeyboardShortcut",
            "BTTPredefinedActionType": 96,  # Hide all applications
            "BTTPredefinedActionName": "Hide All Applications",
            "BTTTriggerName": "Hide All Apps (Added by Script)",
            "BTTShortcutToSend": "h",
            "BTTAdditionalConfiguration": "1048848",  # Cmd+Shift
            "BTTTriggerOnKeyDown": 1,
            "BTTEnabled2": 1,
            "BTTKeyboardShortcutKeyboardType": 0
        })
        
        # Create URL for adding the trigger
        url = f"btt://add_new_trigger/?json={trigger_json}"
        
        # Use open command to invoke the URL
        subprocess.run(['open', url], check=True)
        print("✅ Trigger added! Press Cmd+Shift+H to hide all applications.")
    else:
        print("❌ Trigger creation canceled.")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main() 