#!/bin/bash
# Install and run the Java API MCP server

echo "=== Java API MCP Server Setup ==="
echo

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

# Install MCP if not already installed
echo "Checking for MCP package..."
if ! python3 -c "import mcp" 2>/dev/null; then
    echo "Installing MCP package..."
    pip3 install mcp beautifulsoup4
else
    echo "✓ MCP package found"
fi

# Check if indexes exist
if [ ! -f "java_api_indexes.pkl" ]; then
    echo "Error: java_api_indexes.pkl not found!"
    echo "Please run: python3 build_indexes.py json-output"
    exit 1
fi

echo "✓ Indexes found"

# Test the server
echo
echo "Testing server functionality..."
python3 test_mcp_tools.py

if [ $? -eq 0 ]; then
    echo
    echo "✓ Server test successful!"
    echo
    echo "=== MCP Configuration ==="
    echo "Add this to your Claude Code MCP configuration:"
    echo
    echo "{"
    echo "  \"mcpServers\": {"
    echo "    \"java-api\": {"
    echo "      \"command\": \"python3\","
    echo "      \"args\": ["
    echo "        \"$(pwd)/java_api_server.py\","
    echo "        \"--indexes\","
    echo "        \"$(pwd)/java_api_indexes.pkl\""
    echo "      ],"
    echo "      \"env\": {}"
    echo "    }"
    echo "  }"
    echo "}"
    echo
    echo "Then restart Claude Code to use the server."
else
    echo "✗ Server test failed"
    exit 1
fi