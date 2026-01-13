#!/bin/bash
# Demo script for interacting with the MCP server using curl

echo "🔍 BTT MCP Demo"
echo "==============="

# Define the MCP server URL (default for fastmcp)
MCP_URL="http://127.0.0.1:6274"

# Function to make MCP requests
function mcp_request() {
  local method=$1
  local params=$2
  local id=$(date +%s)
  
  echo -e "\n📤 Sending request: $method"
  
  # Create JSON-RPC request
  request="{\"jsonrpc\":\"2.0\",\"id\":\"$id\",\"method\":\"$method\""
  if [ ! -z "$params" ]; then
    request="$request,\"params\":$params"
  fi
  request="$request}"
  
  # Send request to MCP server
  response=$(curl -s -X POST $MCP_URL \
    -H "Content-Type: application/json" \
    -d "$request")
  
  # Display response
  echo -e "📥 Response:"
  echo "$response" | python -m json.tool
  
  # Return the result part for further processing
  echo "$response" | python -c "import sys, json; print(json.loads(sys.stdin.read()).get('result', {}))" 
}

# 1. List available tools
echo -e "\n🧰 Step 1: List available tools"
mcp_request "rpc.discover" | python -c "import sys, json; tools = json.loads(sys.stdin.read()).get('tools', []); print('\nAvailable tools:'); [print(f'- {t}') for t in tools]"

# 2. List BTT triggers
echo -e "\n🔄 Step 2: List BTT triggers"
triggers=$(mcp_request "list_btt_triggers")

# Count triggers and show first one as example
trigger_count=$(echo "$triggers" | python -c "import sys, json; print(len(json.loads(sys.stdin.read())))")
echo -e "\nFound $trigger_count BTT triggers"

if [ "$trigger_count" -gt 0 ]; then
  echo -e "\n📋 First trigger example:"
  echo "$triggers" | python -c "import sys, json; trigger = json.loads(sys.stdin.read())[0]; print(f'Name: {trigger.get(\"BTTTriggerName\", \"Unnamed\")}'); print(f'Type: {trigger.get(\"BTTTriggerType\")}'); print(f'UUID: {trigger.get(\"BTTUUID\", \"Unknown\")}')"
fi

echo -e "\n✅ Demo complete!"
echo "To add a new trigger, you could use:"
echo 'curl -X POST http://127.0.0.1:6274 -H "Content-Type: application/json" -d '"'"'{"jsonrpc":"2.0","id":"123","method":"add_btt_trigger","params":{"trigger_json":"..."}}'"'"
echo -e "\nOpen the MCP Inspector in your browser to interact with the API visually." 