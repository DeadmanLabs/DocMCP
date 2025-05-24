#!/usr/bin/env python3
"""
Simple script to run the Java API MCP server directly for testing.
"""

import asyncio
import sys
from pathlib import Path
from java_api_server import JavaAPIServer


async def main():
    """Run the MCP server."""
    # Check if indexes exist
    indexes_file = "java_api_indexes.pkl"
    if not Path(indexes_file).exists():
        print("Error: java_api_indexes.pkl not found!")
        print("Please run: python3 build_indexes.py json-output")
        return 1
    
    print("Starting Java API MCP Server...")
    print("Server will communicate via stdin/stdout")
    print("Press Ctrl+C to stop")
    
    try:
        server = JavaAPIServer(indexes_file)
        await server.run()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"Server error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))