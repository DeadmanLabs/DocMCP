#!/usr/bin/env python3
"""
Test the MCP server tools directly (simulates what Claude would do).
"""

import asyncio
import json
from java_api_server import JavaAPIServer


async def test_tools():
    """Test all MCP tools."""
    print("=== Testing MCP Server Tools ===\n")
    
    # Initialize server
    server = JavaAPIServer("java_api_indexes.pkl")
    server.load_indexes()
    
    # Test each tool
    tests = [
        {
            "name": "lookup_class",
            "args": {"class_name": "ChatFormatting"},
            "description": "Look up ChatFormatting class"
        },
        {
            "name": "lookup_method", 
            "args": {"class_name": "ChatFormatting", "method_name": "valueOf"},
            "description": "Find valueOf method in ChatFormatting"
        },
        {
            "name": "check_method_accessibility",
            "args": {"class_name": "ChatFormatting", "method_name": "stripFormatting"},
            "description": "Check if stripFormatting is public"
        },
        {
            "name": "get_enum_constants",
            "args": {"enum_name": "ChatFormatting"},
            "description": "Get all ChatFormatting enum values"
        },
        {
            "name": "search_classes",
            "args": {"query": "Block", "limit": 3},
            "description": "Search for classes containing 'Block'"
        },
        {
            "name": "get_package_classes",
            "args": {"package_name": "net.minecraft"},
            "description": "Get classes in net.minecraft package"
        },
        {
            "name": "validate_method_call",
            "args": {
                "class_name": "ChatFormatting", 
                "method_name": "valueOf",
                "parameter_types": ["String"],
                "is_static_call": True
            },
            "description": "Validate ChatFormatting.valueOf(String) call"
        }
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test['description']}...")
        
        try:
            # Simulate tool call
            if test["name"] == "lookup_class":
                result = server._lookup_class(**test["args"])
            elif test["name"] == "lookup_method":
                result = server._lookup_method(**test["args"])
            elif test["name"] == "check_method_accessibility":
                result = server._check_method_accessibility(**test["args"])
            elif test["name"] == "get_enum_constants":
                result = server._get_enum_constants(**test["args"])
            elif test["name"] == "search_classes":
                result = server._search_classes(**test["args"])
            elif test["name"] == "get_package_classes":
                result = server._get_package_classes(**test["args"])
            elif test["name"] == "validate_method_call":
                result = server._validate_method_call(**test["args"])
            
            # Show result summary
            if result.get("found", True):  # Most tools return found: true/false
                print("   ✓ Success")
                
                # Show specific details based on tool
                if test["name"] == "lookup_class":
                    info = result["class_info"]
                    print(f"     Type: {info['type']}, Methods: {info['method_count']}, Fields: {info['field_count']}")
                
                elif test["name"] == "lookup_method":
                    print(f"     Found {result['overloads']} overload(s)")
                    
                elif test["name"] == "check_method_accessibility":
                    access = result["accessibility_info"][0]
                    print(f"     Public: {access['is_public']}, Static: {access['is_static']}")
                    
                elif test["name"] == "get_enum_constants":
                    print(f"     {result['constant_count']} constants")
                    
                elif test["name"] == "search_classes":
                    print(f"     {result['total_results']} matches")
                    
                elif test["name"] == "get_package_classes":
                    print(f"     {result['class_count']} classes")
                    
                elif test["name"] == "validate_method_call":
                    print(f"     Valid: {result.get('valid', False)}")
            else:
                print(f"   ✗ {result.get('message', 'Failed')}")
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print()
    
    print("=== Tool Testing Complete ===")


if __name__ == "__main__":
    asyncio.run(test_tools())