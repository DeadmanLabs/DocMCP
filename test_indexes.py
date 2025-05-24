#!/usr/bin/env python3
"""
Test script for the Java API indexes (without MCP dependencies).
"""

import pickle
import json
from pathlib import Path


class SimpleAPITester:
    """Simple tester for the API indexes."""
    
    def __init__(self, indexes_file: str):
        with open(indexes_file, 'rb') as f:
            self.indexes = pickle.load(f)
    
    def lookup_class(self, class_name: str):
        """Look up a class by name."""
        # Try exact match first
        if class_name in self.indexes['classes_by_name']:
            return self.indexes['classes_by_name'][class_name]
        
        if class_name in self.indexes['classes_by_qualified_name']:
            return self.indexes['classes_by_qualified_name'][class_name]
        
        return None
    
    def lookup_method(self, class_name: str, method_name: str):
        """Look up methods in a class."""
        if class_name in self.indexes['methods_by_class']:
            class_methods = self.indexes['methods_by_class'][class_name]
            if method_name in class_methods:
                return class_methods[method_name]
        return None
    
    def get_enum_constants(self, enum_name: str):
        """Get enum constants."""
        if enum_name in self.indexes['enum_constants_by_class']:
            return self.indexes['enum_constants_by_class'][enum_name]
        return None
    
    def search_classes(self, query: str, limit: int = 10):
        """Search for classes."""
        results = []
        query_lower = query.lower()
        
        for class_name, class_info in self.indexes['classes_by_name'].items():
            if query_lower in class_name.lower():
                results.append({
                    'name': class_name,
                    'qualified_name': class_info.get('qualified_name', ''),
                    'type': class_info.get('type', '')
                })
                if len(results) >= limit:
                    break
        
        return results


def main():
    """Test the indexes."""
    print("=== Testing Java API Indexes ===\n")
    
    # Check if indexes file exists
    indexes_file = "java_api_indexes.pkl"
    if not Path(indexes_file).exists():
        print(f"Error: {indexes_file} not found. Please run build_indexes.py first.")
        return
    
    tester = SimpleAPITester(indexes_file)
    
    # Test 1: Lookup ChatFormatting
    print("1. Looking up ChatFormatting class...")
    class_info = tester.lookup_class("ChatFormatting")
    if class_info:
        print(f"✓ Found: {class_info.get('qualified_name')}")
        print(f"  Type: {class_info.get('type')}")
        print(f"  Package: {class_info.get('package')}")
        print(f"  Methods: {len(class_info.get('methods', []))}")
        print(f"  Fields: {len(class_info.get('fields', []))}")
    else:
        print("✗ Not found")
    print()
    
    # Test 2: Look up valueOf method
    print("2. Looking up valueOf method in ChatFormatting...")
    methods = tester.lookup_method("ChatFormatting", "valueOf")
    if methods:
        print(f"✓ Found {len(methods)} overload(s)")
        for i, method in enumerate(methods):
            params = [f"{p['type']} {p['name']}" for p in method.get('parameters', [])]
            print(f"  Overload {i+1}: {method.get('return_type', 'void')} valueOf({', '.join(params)})")
            print(f"    Modifiers: {', '.join(method.get('modifiers', []))}")
    else:
        print("✗ Not found")
    print()
    
    # Test 3: Get enum constants
    print("3. Getting enum constants for ChatFormatting...")
    constants = tester.get_enum_constants("ChatFormatting")
    if constants:
        print(f"✓ Found {len(constants)} constants")
        const_names = list(constants.keys())[:10]  # Show first 10
        print(f"  First 10: {', '.join(const_names)}")
    else:
        print("✗ No constants found")
    print()
    
    # Test 4: Search for Block classes
    print("4. Searching for classes containing 'Block'...")
    results = tester.search_classes("Block", limit=5)
    if results:
        print(f"✓ Found {len(results)} results:")
        for result in results:
            print(f"  {result['qualified_name']} ({result['type']})")
    else:
        print("✗ No results found")
    print()
    
    # Test 5: Check specific method details
    print("5. Checking details of stripFormatting method...")
    methods = tester.lookup_method("ChatFormatting", "stripFormatting")
    if methods:
        method = methods[0]
        modifiers = method.get('modifiers', [])
        print(f"✓ Found method:")
        print(f"  Return type: {method.get('return_type', 'void')}")
        print(f"  Modifiers: {', '.join(modifiers)}")
        print(f"  Public: {'public' in modifiers}")
        print(f"  Static: {'static' in modifiers}")
        print(f"  Parameters: {len(method.get('parameters', []))}")
        
        if method.get('parameters'):
            for param in method['parameters']:
                print(f"    - {param['type']} {param['name']}")
    else:
        print("✗ Method not found")
    print()
    
    # Print some general statistics
    print("=== Index Statistics ===")
    print(f"Total classes: {len(tester.indexes['classes_by_name'])}")
    print(f"Total packages: {len(tester.indexes['packages'])}")
    print(f"Classes with methods: {len(tester.indexes['methods_by_class'])}")
    print(f"Classes with fields: {len(tester.indexes['fields_by_class'])}")
    
    type_counts = {}
    for class_info in tester.indexes['classes_by_name'].values():
        class_type = class_info.get('type', 'unknown')
        type_counts[class_type] = type_counts.get(class_type, 0) + 1
    
    print("Classes by type:")
    for type_name, count in sorted(type_counts.items()):
        print(f"  {type_name}: {count}")
    
    print("\n✓ All tests completed successfully!")


if __name__ == "__main__":
    main()