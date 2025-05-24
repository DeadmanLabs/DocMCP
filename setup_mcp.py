#!/usr/bin/env python3
"""
Setup script for the Java API MCP server.
Creates or updates the MCP configuration for Claude Code.
"""

import json
import os
import sys
from pathlib import Path


def find_claude_config_dir():
    """Find Claude Code configuration directory."""
    # Common locations for Claude Code config
    possible_locations = [
        Path.home() / ".config" / "claude-code",
        Path.home() / ".claude-code",
        Path.home() / "AppData" / "Roaming" / "claude-code",  # Windows
        Path.home() / "Library" / "Application Support" / "claude-code",  # macOS
    ]
    
    for location in possible_locations:
        if location.exists():
            return location
    
    return None


def setup_mcp_config(server_script_path: str, indexes_path: str):
    """Set up MCP configuration for the Java API server."""
    
    # Get absolute paths
    server_script_path = str(Path(server_script_path).resolve())
    indexes_path = str(Path(indexes_path).resolve())
    
    # Find Claude config directory
    config_dir = find_claude_config_dir()
    
    if config_dir is None:
        print("Could not find Claude Code configuration directory.")
        print("Please manually add the following to your MCP configuration:")
        print()
        print_manual_config(server_script_path, indexes_path)
        return False
    
    config_file = config_dir / "mcp_servers.json"
    
    # Load existing config or create new one
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            config = {"mcpServers": {}}
    else:
        config = {"mcpServers": {}}
    
    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add our server configuration
    config["mcpServers"]["java-api"] = {
        "command": "python3",
        "args": [server_script_path, "--indexes", indexes_path],
        "env": {}
    }
    
    # Save configuration
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ MCP configuration updated: {config_file}")
        print("✓ Java API server added as 'java-api'")
        print()
        print("The server provides these tools:")
        print("  - lookup_class: Get complete class information")
        print("  - lookup_method: Find methods in a class")
        print("  - lookup_field: Find fields in a class")
        print("  - check_method_accessibility: Check method visibility")
        print("  - get_class_constructors: Get constructors")
        print("  - search_classes: Search for classes")
        print("  - get_package_classes: List classes in package")
        print("  - get_inheritance_info: Get inheritance tree")
        print("  - get_enum_constants: Get enum values")
        print("  - validate_method_call: Validate method calls")
        print()
        print("Restart Claude Code to use the new server.")
        return True
        
    except Exception as e:
        print(f"Error saving configuration: {e}")
        print("Please manually add the following to your MCP configuration:")
        print()
        print_manual_config(server_script_path, indexes_path)
        return False


def print_manual_config(server_script_path: str, indexes_path: str):
    """Print manual configuration instructions."""
    config = {
        "mcpServers": {
            "java-api": {
                "command": "python3",
                "args": [server_script_path, "--indexes", indexes_path],
                "env": {}
            }
        }
    }
    
    print("Manual Configuration:")
    print("Add this to your MCP servers configuration:")
    print()
    print(json.dumps(config, indent=2))


def main():
    """Main setup function."""
    print("=== Java API MCP Server Setup ===\n")
    
    # Check if required files exist
    current_dir = Path(__file__).parent
    server_script = current_dir / "java_api_server.py"
    indexes_file = current_dir / "java_api_indexes.pkl"
    
    if not server_script.exists():
        print(f"Error: Server script not found: {server_script}")
        return 1
    
    if not indexes_file.exists():
        print(f"Error: Indexes file not found: {indexes_file}")
        print("Please run: python3 build_indexes.py json-output")
        return 1
    
    # Check for Python dependencies
    try:
        import mcp
        print("✓ MCP package found")
    except ImportError:
        print("⚠ MCP package not found. Install with:")
        print("  pip install mcp")
        print()
        print("Continuing with configuration setup...")
    
    # Set up MCP configuration
    if setup_mcp_config(str(server_script), str(indexes_file)):
        print("✓ Setup completed successfully!")
        return 0
    else:
        print("⚠ Setup completed with manual configuration required.")
        return 1


if __name__ == "__main__":
    sys.exit(main())