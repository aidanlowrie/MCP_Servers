#!/bin/bash
# install_to_claude.sh
# Script to install the Thoughts MCP server to Claude Desktop

set -e  # Exit immediately if a command exits with a non-zero status

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "👋 Installing Thoughts MCP Server to Claude Desktop..."

# Check if virtual environment exists, create if it doesn't
if [ ! -d "venv" ]; then
    echo "🔧 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install "mcp[cli]"

# Check if Ollama is running
echo "🔍 Checking if Ollama is running..."
if ! curl -s --head http://localhost:11434/api/version > /dev/null; then
    echo "⚠️  Warning: Ollama doesn't appear to be running at http://localhost:11434"
    echo "   You'll need Ollama running to generate embeddings."
    echo "   Start Ollama before using the MCP server."
else
    echo "✅ Ollama is running."
fi

# Check if embeddings exist
echo "🔍 Checking for existing embeddings..."
if [ -f "thought_embeddings.csv" ] && [ -f "title_embeddings.csv" ]; then
    echo "✅ Embeddings files found."
else
    echo "⚠️  Embeddings files not found."
    echo "   Attempting to build embeddings..."
    if curl -s --head http://localhost:11434/api/version > /dev/null; then
        echo "   Running embedding build script..."
        python build_embeddings_cli.py
    else
        echo "⚠️  Cannot build embeddings: Ollama is not running."
        echo "   Please start Ollama and run './build_embeddings_cli.py' manually."
    fi
fi

# Install the MCP server to Claude Desktop
echo "🚀 Installing MCP server to Claude Desktop..."
mcp install mcp_server.py --name "Thoughts Assistant"

echo "✨ Installation complete! The Thoughts Assistant MCP server is now available in Claude Desktop."
echo "   You can now ask Claude to:"
echo "   - List recent thoughts"
echo "   - Search thoughts for specific topics"
echo "   - Compare thoughts for similarity"
echo "   - And more!"
echo ""
echo "   If embeddings were not found, you'll need to run the build_thought_embeddings tool first."
echo "   In Claude, type: 'Use the Thoughts Assistant tool to build thought embeddings.'"

# Deactivate virtual environment
deactivate

echo "🎉 Done!" 