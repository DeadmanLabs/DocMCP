#!/usr/bin/env python3
"""
Test script for the Java API MCP server.
"""

import json
import pickle
import sys
from java_api_server import JavaAPIServer


async def test_server():
    """Test the server functionality."""
    server = JavaAPIServer("java_api_indexes.pkl")
    server.load_indexes()
    
    print("=== Testing Java API Server ===\n")
    
    # Test 1: Lookup a class
    print("1. Looking up ChatFormatting class...")
    result = server._lookup_class("ChatFormatting")
    if result["found"]:
        print(f"✓ Found: {result['class_info']['qualified_name']}")
        print(f"  Type: {result['class_info']['type']}")
        print(f"  Methods: {result['class_info']['method_count']}")
        print(f"  Fields: {result['class_info']['field_count']}")
    else:
        print("✗ Not found")
    print()
    
    # Test 2: Lookup a method
    print("2. Looking up valueOf method in ChatFormatting...")
    result = server._lookup_method("ChatFormatting", "valueOf")
    if result["found"]:
        print(f"✓ Found {result['overloads']} overload(s)")
        for i, method in enumerate(result["methods"]):
            params = [p["type"] + " " + p["name"] for p in method["parameters"]]
            print(f"  Overload {i+1}: {method['return_type']} valueOf({', '.join(params)})")
    else:
        print("✗ Not found")
    print()
    
    # Test 3: Check method accessibility
    print("3. Checking accessibility of valueOf method...")
    result = server._check_method_accessibility("ChatFormatting", "valueOf")
    if result["found"]:
        access = result["accessibility_info"][0]
        print(f"✓ Public: {access['is_public']}, Static: {access['is_static']}")
    else:
        print("✗ Not found")
    print()
    
    # Test 4: Get enum constants
    print("4. Getting enum constants for ChatFormatting...")
    result = server._get_enum_constants("ChatFormatting")
    if result["found"]:
        print(f"✓ Found {result['constant_count']} constants")
        constants = list(result["constants"].keys())[:5]  # Show first 5
        print(f"  Examples: {', '.join(constants)}...")
    else:
        print("✗ Not found")
    print()
    
    # Test 5: Search classes
    print("5. Searching for classes containing 'Block'...")
    result = server._search_classes("Block", limit=5)
    print(f"✓ Found {result['total_results']} results")
    for r in result["results"][:3]:
        print(f"  {r['qualified_name']} ({r['type']})")
    print()
    
    # Test 6: Get package classes
    print("6. Getting classes in net.minecraft package...")
    result = server._get_package_classes("net.minecraft")
    if result["found"]:
        print(f"✓ Found {result['class_count']} classes")
        print(f"  Examples: {', '.join([c['name'] for c in result['classes'][:5]])}...")
    else:
        print("✗ Package not found")
    print()
    
    print("=== All tests completed ===")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_server())