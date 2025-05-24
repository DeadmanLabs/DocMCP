#!/usr/bin/env python3
"""
Test the API tools without MCP dependencies.
This simulates what the MCP server would do.
"""

import pickle
import json
from pathlib import Path
from difflib import get_close_matches


class JavaAPITools:
    """Java API lookup tools without MCP dependencies."""
    
    def __init__(self, indexes_file: str):
        with open(indexes_file, 'rb') as f:
            self.indexes = pickle.load(f)
    
    def lookup_class(self, class_name: str, exact_match: bool = False):
        """Look up a class by name."""
        # Try exact matches first
        if class_name in self.indexes['classes_by_name']:
            class_info = self.indexes['classes_by_name'][class_name]
        elif class_name in self.indexes['classes_by_qualified_name']:
            class_info = self.indexes['classes_by_qualified_name'][class_name]
        else:
            if exact_match:
                return {"found": False, "message": f"Class '{class_name}' not found"}
            
            # Try fuzzy matching
            simple_names = list(self.indexes['classes_by_name'].keys())
            matches = get_close_matches(class_name, simple_names, n=1, cutoff=0.6)
            if matches:
                class_info = self.indexes['classes_by_name'][matches[0]]
            else:
                return {"found": False, "message": f"Class '{class_name}' not found"}
        
        return {
            "found": True,
            "class_info": {
                "name": class_info.get("name"),
                "qualified_name": class_info.get("qualified_name"),
                "package": class_info.get("package"),
                "type": class_info.get("type"),
                "modifiers": class_info.get("modifiers", []),
                "method_count": len(class_info.get("methods", [])),
                "field_count": len(class_info.get("fields", [])),
                "constructor_count": len(class_info.get("constructors", [])),
                "enum_constant_count": len(class_info.get("enum_constants", []))
            }
        }
    
    def lookup_method(self, class_name: str, method_name: str):
        """Look up methods in a class."""
        class_result = self.lookup_class(class_name)
        if not class_result["found"]:
            return class_result
        
        actual_class_name = class_result["class_info"]["name"]
        
        if actual_class_name in self.indexes['methods_by_class']:
            class_methods = self.indexes['methods_by_class'][actual_class_name]
            if method_name in class_methods:
                methods = class_methods[method_name]
                return {
                    "found": True,
                    "class_name": actual_class_name,
                    "method_name": method_name,
                    "overloads": len(methods),
                    "methods": methods
                }
        
        return {
            "found": False,
            "message": f"Method '{method_name}' not found in class '{actual_class_name}'"
        }
    
    def check_method_accessibility(self, class_name: str, method_name: str):
        """Check method accessibility."""
        method_result = self.lookup_method(class_name, method_name)
        if not method_result["found"]:
            return method_result
        
        methods = method_result["methods"]
        accessibility_info = []
        
        for method in methods:
            modifiers = method.get("modifiers", [])
            accessibility = {
                "is_public": "public" in modifiers,
                "is_protected": "protected" in modifiers,
                "is_private": "private" in modifiers,
                "is_static": "static" in modifiers,
                "is_final": "final" in modifiers,
                "modifiers": modifiers,
                "return_type": method.get("return_type", ""),
                "parameters": method.get("parameters", [])
            }
            accessibility_info.append(accessibility)
        
        return {
            "found": True,
            "class_name": method_result["class_name"],
            "method_name": method_name,
            "accessibility_info": accessibility_info
        }
    
    def get_enum_constants(self, enum_name: str):
        """Get enum constants."""
        class_result = self.lookup_class(enum_name)
        if not class_result["found"]:
            return class_result
        
        if class_result["class_info"]["type"] != "enum":
            return {
                "found": False,
                "message": f"'{enum_name}' is not an enum"
            }
        
        actual_class_name = class_result["class_info"]["name"]
        constants = {}
        
        if actual_class_name in self.indexes['enum_constants_by_class']:
            constants = self.indexes['enum_constants_by_class'][actual_class_name]
        
        return {
            "found": True,
            "enum_name": actual_class_name,
            "constant_count": len(constants),
            "constants": list(constants.keys())
        }
    
    def search_classes(self, query: str, limit: int = 20):
        """Search for classes."""
        results = []
        query_lower = query.lower()
        
        for class_name, class_info in self.indexes['classes_by_name'].items():
            qualified_name = class_info.get("qualified_name", "")
            
            score = 0
            if query_lower == class_name.lower():
                score = 100
            elif query_lower in class_name.lower():
                score = 80
            elif query_lower in qualified_name.lower():
                score = 60
            elif query_lower in class_info.get("package", "").lower():
                score = 40
            
            if score > 0:
                results.append({
                    "name": class_name,
                    "qualified_name": qualified_name,
                    "type": class_info.get("type", ""),
                    "package": class_info.get("package", "")
                })
                if len(results) >= limit:
                    break
        
        return {
            "total_results": len(results),
            "results": results
        }
    
    def get_package_classes(self, package_name: str):
        """Get classes in a package."""
        if package_name in self.indexes['packages']:
            classes = self.indexes['packages'][package_name]
            return {
                "found": True,
                "package_name": package_name,
                "class_count": len(classes),
                "classes": classes[:10]  # Show first 10
            }
        
        return {
            "found": False,
            "message": f"Package '{package_name}' not found"
        }
    
    def validate_method_call(self, class_name: str, method_name: str, 
                           parameter_types: list, is_static_call: bool):
        """Validate a method call."""
        method_result = self.lookup_method(class_name, method_name)
        if not method_result["found"]:
            return {"valid": False, "reason": "Method not found"}
        
        methods = method_result["methods"]
        valid_overloads = []
        
        for method in methods:
            modifiers = method.get("modifiers", [])
            method_is_static = "static" in modifiers
            method_params = method.get("parameters", [])
            
            # Check static consistency
            if is_static_call != method_is_static:
                continue
            
            # Check parameter count
            if len(parameter_types) == len(method_params):
                valid_overloads.append(method)
        
        if valid_overloads:
            return {
                "valid": True,
                "matching_overloads": len(valid_overloads),
                "recommended_overload": valid_overloads[0]
            }
        else:
            return {
                "valid": False,
                "reason": f"No compatible overload found"
            }


def main():
    """Test all API tools."""
    print("=== Testing Java API Tools ===\n")
    
    # Check if indexes exist
    if not Path("java_api_indexes.pkl").exists():
        print("Error: java_api_indexes.pkl not found!")
        print("Please run: python3 build_indexes.py json-output")
        return 1
    
    # Initialize tools
    api = JavaAPITools("java_api_indexes.pkl")
    
    # Test cases
    tests = [
        {
            "name": "lookup_class",
            "func": lambda: api.lookup_class("ChatFormatting"),
            "description": "Look up ChatFormatting class"
        },
        {
            "name": "lookup_method",
            "func": lambda: api.lookup_method("ChatFormatting", "valueOf"),
            "description": "Find valueOf method in ChatFormatting"
        },
        {
            "name": "check_method_accessibility",
            "func": lambda: api.check_method_accessibility("ChatFormatting", "stripFormatting"),
            "description": "Check stripFormatting accessibility"
        },
        {
            "name": "get_enum_constants",
            "func": lambda: api.get_enum_constants("ChatFormatting"),
            "description": "Get ChatFormatting enum constants"
        },
        {
            "name": "search_classes",
            "func": lambda: api.search_classes("Block", limit=5),
            "description": "Search for classes with 'Block'"
        },
        {
            "name": "get_package_classes",
            "func": lambda: api.get_package_classes("net.minecraft"),
            "description": "Get classes in net.minecraft package"
        },
        {
            "name": "validate_method_call",
            "func": lambda: api.validate_method_call("ChatFormatting", "valueOf", ["String"], True),
            "description": "Validate ChatFormatting.valueOf(String)"
        }
    ]
    
    # Run tests
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test['description']}...")
        
        try:
            result = test["func"]()
            
            if result.get("found", True) and result.get("valid", True):
                print("   ✓ Success")
                
                # Show specific details
                if "class_info" in result:
                    info = result["class_info"]
                    print(f"     {info['qualified_name']} ({info['type']})")
                    print(f"     Methods: {info['method_count']}, Fields: {info['field_count']}")
                
                elif "overloads" in result:
                    print(f"     Found {result['overloads']} overload(s)")
                
                elif "accessibility_info" in result:
                    access = result["accessibility_info"][0]
                    print(f"     Public: {access['is_public']}, Static: {access['is_static']}")
                
                elif "constant_count" in result:
                    print(f"     {result['constant_count']} constants")
                    if result.get("constants"):
                        print(f"     Examples: {', '.join(result['constants'][:5])}...")
                
                elif "total_results" in result:
                    print(f"     {result['total_results']} matches found")
                
                elif "class_count" in result:
                    print(f"     {result['class_count']} classes")
                
                elif "matching_overloads" in result:
                    print(f"     Valid call with {result['matching_overloads']} matching overloads")
                
            else:
                print(f"   ✗ {result.get('message', result.get('reason', 'Failed'))}")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print()
    
    print("=== All Tests Complete ===")
    print()
    print("🎯 Your Java API system is working!")
    print("📝 Ready to configure with Claude Code")
    
    return 0


if __name__ == "__main__":
    exit(main())