#!/usr/bin/env python3
"""
MCP Server for Java API lookups.
Provides tools for looking up Java classes, methods, fields, and other API information.
"""

import asyncio
import json
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import argparse
import re
from difflib import get_close_matches

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio


class JavaAPIServer:
    """MCP Server for Java API lookups."""
    
    def __init__(self, indexes_file: str):
        """Initialize the server with prebuilt indexes."""
        self.indexes_file = indexes_file
        self.indexes = None
        self.server = Server("java-api")
        self._setup_handlers()
    
    def load_indexes(self):
        """Load the prebuilt indexes."""
        if self.indexes is not None:
            return
        
        try:
            with open(self.indexes_file, 'rb') as f:
                self.indexes = pickle.load(f)
            print(f"Loaded indexes from {self.indexes_file}", file=sys.stderr)
        except Exception as e:
            print(f"Error loading indexes: {e}", file=sys.stderr)
            raise
    
    def _setup_handlers(self):
        """Set up MCP handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="lookup_class",
                    description="Look up a Java class by name. Returns complete class information including methods, fields, inheritance, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class to look up (e.g., 'ChatFormatting' or 'net.minecraft.ChatFormatting')"
                            },
                            "exact_match": {
                                "type": "boolean",
                                "description": "Whether to require exact match or allow fuzzy matching",
                                "default": False
                            }
                        },
                        "required": ["class_name"]
                    }
                ),
                types.Tool(
                    name="lookup_method",
                    description="Look up methods in a specific class. Can check if method exists, get parameters, return type, modifiers, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class containing the method"
                            },
                            "method_name": {
                                "type": "string",
                                "description": "Name of the method to look up"
                            },
                            "include_inherited": {
                                "type": "boolean",
                                "description": "Whether to include inherited methods",
                                "default": False
                            }
                        },
                        "required": ["class_name", "method_name"]
                    }
                ),
                types.Tool(
                    name="lookup_field",
                    description="Look up fields in a specific class. Returns field type, modifiers, visibility, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class containing the field"
                            },
                            "field_name": {
                                "type": "string",
                                "description": "Name of the field to look up"
                            },
                            "include_inherited": {
                                "type": "boolean",
                                "description": "Whether to include inherited fields",
                                "default": False
                            }
                        },
                        "required": ["class_name", "field_name"]
                    }
                ),
                types.Tool(
                    name="check_method_accessibility",
                    description="Check if a method is accessible (public, protected, private) and other details like static, final, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class containing the method"
                            },
                            "method_name": {
                                "type": "string",
                                "description": "Name of the method to check"
                            }
                        },
                        "required": ["class_name", "method_name"]
                    }
                ),
                types.Tool(
                    name="get_class_constructors",
                    description="Get all constructors for a class with their parameters and accessibility.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class"
                            }
                        },
                        "required": ["class_name"]
                    }
                ),
                types.Tool(
                    name="search_classes",
                    description="Search for classes by name pattern or package. Useful for finding classes when you're not sure of the exact name.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (class name pattern, package name, etc.)"
                            },
                            "class_type": {
                                "type": "string",
                                "description": "Filter by class type: 'class', 'interface', 'enum', 'annotation', 'record'",
                                "enum": ["class", "interface", "enum", "annotation", "record"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 20
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_package_classes",
                    description="Get all classes in a specific package.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the package (e.g., 'net.minecraft', 'java.util')"
                            }
                        },
                        "required": ["package_name"]
                    }
                ),
                types.Tool(
                    name="get_inheritance_info",
                    description="Get inheritance information for a class (extends, implements, inheritance tree).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class"
                            }
                        },
                        "required": ["class_name"]
                    }
                ),
                types.Tool(
                    name="get_enum_constants",
                    description="Get all constants/values for an enum class.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "enum_name": {
                                "type": "string",
                                "description": "Name of the enum class"
                            }
                        },
                        "required": ["enum_name"]
                    }
                ),
                types.Tool(
                    name="validate_method_call",
                    description="Validate if a method call would be valid (exists, accessible, correct parameters).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "class_name": {
                                "type": "string",
                                "description": "Name of the class"
                            },
                            "method_name": {
                                "type": "string",
                                "description": "Name of the method"
                            },
                            "parameter_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of parameter types for the method call",
                                "default": []
                            },
                            "is_static_call": {
                                "type": "boolean",
                                "description": "Whether this is a static method call",
                                "default": False
                            }
                        },
                        "required": ["class_name", "method_name"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Handle tool calls."""
            self.load_indexes()  # Ensure indexes are loaded
            
            try:
                if name == "lookup_class":
                    result = self._lookup_class(
                        arguments["class_name"],
                        arguments.get("exact_match", False)
                    )
                elif name == "lookup_method":
                    result = self._lookup_method(
                        arguments["class_name"],
                        arguments["method_name"],
                        arguments.get("include_inherited", False)
                    )
                elif name == "lookup_field":
                    result = self._lookup_field(
                        arguments["class_name"],
                        arguments["field_name"],
                        arguments.get("include_inherited", False)
                    )
                elif name == "check_method_accessibility":
                    result = self._check_method_accessibility(
                        arguments["class_name"],
                        arguments["method_name"]
                    )
                elif name == "get_class_constructors":
                    result = self._get_class_constructors(arguments["class_name"])
                elif name == "search_classes":
                    result = self._search_classes(
                        arguments["query"],
                        arguments.get("class_type"),
                        arguments.get("limit", 20)
                    )
                elif name == "get_package_classes":
                    result = self._get_package_classes(arguments["package_name"])
                elif name == "get_inheritance_info":
                    result = self._get_inheritance_info(arguments["class_name"])
                elif name == "get_enum_constants":
                    result = self._get_enum_constants(arguments["enum_name"])
                elif name == "validate_method_call":
                    result = self._validate_method_call(
                        arguments["class_name"],
                        arguments["method_name"],
                        arguments.get("parameter_types", []),
                        arguments.get("is_static_call", False)
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                error_result = {"error": str(e), "tool": name, "arguments": arguments}
                return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    def _find_class(self, class_name: str, exact_match: bool = False) -> Optional[Dict[str, Any]]:
        """Find a class by name, supporting both simple and qualified names."""
        # Try exact match first
        if class_name in self.indexes['classes_by_name']:
            return self.indexes['classes_by_name'][class_name]
        
        if class_name in self.indexes['classes_by_qualified_name']:
            return self.indexes['classes_by_qualified_name'][class_name]
        
        if exact_match:
            return None
        
        # Try fuzzy matching on simple names
        simple_names = list(self.indexes['classes_by_name'].keys())
        matches = get_close_matches(class_name, simple_names, n=1, cutoff=0.6)
        if matches:
            return self.indexes['classes_by_name'][matches[0]]
        
        # Try partial matching on qualified names
        for qualified_name, class_info in self.indexes['classes_by_qualified_name'].items():
            if class_name.lower() in qualified_name.lower():
                return class_info
        
        return None
    
    def _lookup_class(self, class_name: str, exact_match: bool = False) -> Dict[str, Any]:
        """Look up a class by name."""
        class_info = self._find_class(class_name, exact_match)
        
        if not class_info:
            # Suggest similar classes
            simple_names = list(self.indexes['classes_by_name'].keys())
            suggestions = get_close_matches(class_name, simple_names, n=5, cutoff=0.4)
            
            return {
                "found": False,
                "message": f"Class '{class_name}' not found",
                "suggestions": suggestions
            }
        
        # Return comprehensive class information
        return {
            "found": True,
            "class_info": {
                "name": class_info.get("name"),
                "qualified_name": class_info.get("qualified_name"),
                "package": class_info.get("package"),
                "type": class_info.get("type"),
                "modifiers": class_info.get("modifiers", []),
                "annotations": class_info.get("annotations", []),
                "description": class_info.get("description", ""),
                "inheritance": class_info.get("inheritance", {}),
                "nested_classes": class_info.get("nested_classes", []),
                "method_count": len(class_info.get("methods", [])),
                "field_count": len(class_info.get("fields", [])),
                "constructor_count": len(class_info.get("constructors", [])),
                "enum_constant_count": len(class_info.get("enum_constants", [])),
                "deprecated": class_info.get("deprecated", False)
            }
        }
    
    def _lookup_method(self, class_name: str, method_name: str, include_inherited: bool = False) -> Dict[str, Any]:
        """Look up methods in a class."""
        class_info = self._find_class(class_name)
        
        if not class_info:
            return {
                "found": False,
                "message": f"Class '{class_name}' not found"
            }
        
        actual_class_name = class_info["name"]
        methods = []
        
        # Get methods from the class
        if actual_class_name in self.indexes['methods_by_class']:
            class_methods = self.indexes['methods_by_class'][actual_class_name]
            if method_name in class_methods:
                methods.extend(class_methods[method_name])
        
        if not methods:
            return {
                "found": False,
                "class_name": actual_class_name,
                "method_name": method_name,
                "message": f"Method '{method_name}' not found in class '{actual_class_name}'"
            }
        
        return {
            "found": True,
            "class_name": actual_class_name,
            "method_name": method_name,
            "overloads": len(methods),
            "methods": methods
        }
    
    def _lookup_field(self, class_name: str, field_name: str, include_inherited: bool = False) -> Dict[str, Any]:
        """Look up a field in a class."""
        class_info = self._find_class(class_name)
        
        if not class_info:
            return {
                "found": False,
                "message": f"Class '{class_name}' not found"
            }
        
        actual_class_name = class_info["name"]
        
        # Get field from the class
        if actual_class_name in self.indexes['fields_by_class']:
            class_fields = self.indexes['fields_by_class'][actual_class_name]
            if field_name in class_fields:
                return {
                    "found": True,
                    "class_name": actual_class_name,
                    "field_name": field_name,
                    "field_info": class_fields[field_name]
                }
        
        return {
            "found": False,
            "class_name": actual_class_name,
            "field_name": field_name,
            "message": f"Field '{field_name}' not found in class '{actual_class_name}'"
        }
    
    def _check_method_accessibility(self, class_name: str, method_name: str) -> Dict[str, Any]:
        """Check method accessibility and other modifiers."""
        method_result = self._lookup_method(class_name, method_name)
        
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
                "is_abstract": "abstract" in modifiers,
                "is_synchronized": "synchronized" in modifiers,
                "modifiers": modifiers,
                "parameters": method.get("parameters", []),
                "return_type": method.get("return_type", ""),
                "deprecated": method.get("deprecated", False),
                "annotations": method.get("annotations", [])
            }
            accessibility_info.append(accessibility)
        
        return {
            "found": True,
            "class_name": method_result["class_name"],
            "method_name": method_name,
            "overloads": len(accessibility_info),
            "accessibility_info": accessibility_info
        }
    
    def _get_class_constructors(self, class_name: str) -> Dict[str, Any]:
        """Get constructors for a class."""
        class_info = self._find_class(class_name)
        
        if not class_info:
            return {
                "found": False,
                "message": f"Class '{class_name}' not found"
            }
        
        actual_class_name = class_info["name"]
        constructors = []
        
        if actual_class_name in self.indexes['constructors_by_class']:
            constructors = self.indexes['constructors_by_class'][actual_class_name]
        
        return {
            "found": True,
            "class_name": actual_class_name,
            "constructor_count": len(constructors),
            "constructors": constructors
        }
    
    def _search_classes(self, query: str, class_type: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Search for classes by query."""
        results = []
        query_lower = query.lower()
        
        # Search in class names and qualified names
        for class_name, class_info in self.indexes['classes_by_name'].items():
            if class_type and class_info.get("type") != class_type:
                continue
            
            qualified_name = class_info.get("qualified_name", "")
            
            # Score matches
            score = 0
            if query_lower == class_name.lower():
                score = 100  # Exact match
            elif query_lower in class_name.lower():
                score = 80   # Partial match in class name
            elif query_lower in qualified_name.lower():
                score = 60   # Partial match in qualified name
            elif query_lower in class_info.get("package", "").lower():
                score = 40   # Match in package name
            
            if score > 0:
                results.append({
                    "score": score,
                    "name": class_name,
                    "qualified_name": qualified_name,
                    "package": class_info.get("package", ""),
                    "type": class_info.get("type", ""),
                    "description": class_info.get("description", "")[:200]  # Truncate description
                })
        
        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]
        
        return {
            "query": query,
            "class_type_filter": class_type,
            "total_results": len(results),
            "results": results
        }
    
    def _get_package_classes(self, package_name: str) -> Dict[str, Any]:
        """Get all classes in a package."""
        if package_name not in self.indexes['packages']:
            # Try partial matching
            matching_packages = [pkg for pkg in self.indexes['packages'].keys() 
                               if package_name.lower() in pkg.lower()]
            
            if not matching_packages:
                return {
                    "found": False,
                    "message": f"Package '{package_name}' not found"
                }
            
            if len(matching_packages) == 1:
                package_name = matching_packages[0]
            else:
                return {
                    "found": False,
                    "message": f"Multiple packages match '{package_name}'",
                    "suggestions": matching_packages[:10]
                }
        
        classes = self.indexes['packages'][package_name]
        
        # Get additional info for each class
        class_info = []
        for class_name in classes:
            if class_name in self.indexes['classes_by_name']:
                info = self.indexes['classes_by_name'][class_name]
                class_info.append({
                    "name": class_name,
                    "type": info.get("type", ""),
                    "qualified_name": info.get("qualified_name", ""),
                    "deprecated": info.get("deprecated", False)
                })
        
        return {
            "found": True,
            "package_name": package_name,
            "class_count": len(classes),
            "classes": class_info
        }
    
    def _get_inheritance_info(self, class_name: str) -> Dict[str, Any]:
        """Get inheritance information for a class."""
        class_info = self._find_class(class_name)
        
        if not class_info:
            return {
                "found": False,
                "message": f"Class '{class_name}' not found"
            }
        
        actual_class_name = class_info["name"]
        inheritance = class_info.get("inheritance", {})
        
        return {
            "found": True,
            "class_name": actual_class_name,
            "inheritance": inheritance
        }
    
    def _get_enum_constants(self, enum_name: str) -> Dict[str, Any]:
        """Get enum constants for an enum class."""
        class_info = self._find_class(enum_name)
        
        if not class_info:
            return {
                "found": False,
                "message": f"Enum '{enum_name}' not found"
            }
        
        if class_info.get("type") != "enum":
            return {
                "found": False,
                "message": f"'{enum_name}' is not an enum (it's a {class_info.get('type', 'unknown')})"
            }
        
        actual_class_name = class_info["name"]
        constants = {}
        
        if actual_class_name in self.indexes['enum_constants_by_class']:
            constants = self.indexes['enum_constants_by_class'][actual_class_name]
        
        return {
            "found": True,
            "enum_name": actual_class_name,
            "constant_count": len(constants),
            "constants": constants
        }
    
    def _validate_method_call(self, class_name: str, method_name: str, 
                            parameter_types: List[str], is_static_call: bool) -> Dict[str, Any]:
        """Validate if a method call would be valid."""
        method_result = self._lookup_method(class_name, method_name)
        
        if not method_result["found"]:
            return {
                "valid": False,
                "reason": f"Method '{method_name}' not found in class '{class_name}'"
            }
        
        methods = method_result["methods"]
        valid_overloads = []
        
        for method in methods:
            modifiers = method.get("modifiers", [])
            method_is_static = "static" in modifiers
            method_is_public = "public" in modifiers
            method_params = method.get("parameters", [])
            
            # Check static consistency
            if is_static_call and not method_is_static:
                continue
            if not is_static_call and method_is_static:
                continue
            
            # Check parameter count
            if len(parameter_types) != len(method_params):
                continue
            
            # This is a basic validation - in real use you'd want more sophisticated type matching
            valid_overloads.append({
                "method": method,
                "is_accessible": method_is_public,  # Simplified accessibility check
                "parameter_match": "exact_count"    # Simplified parameter matching
            })
        
        if not valid_overloads:
            return {
                "valid": False,
                "reason": f"No compatible overload found for {method_name}({', '.join(parameter_types)})",
                "available_overloads": [
                    {
                        "parameters": [p.get("type", "") for p in m.get("parameters", [])],
                        "is_static": "static" in m.get("modifiers", [])
                    }
                    for m in methods
                ]
            }
        
        return {
            "valid": True,
            "matching_overloads": len(valid_overloads),
            "recommended_overload": valid_overloads[0]["method"]
        }
    
    async def run(self):
        """Run the MCP server."""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="java-api",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Java API MCP Server")
    parser.add_argument(
        "--indexes",
        default="java_api_indexes.pkl",
        help="Path to the prebuilt indexes file"
    )
    
    args = parser.parse_args()
    
    if not Path(args.indexes).exists():
        print(f"Error: Indexes file not found: {args.indexes}", file=sys.stderr)
        print("Please run build_indexes.py first to create the indexes.", file=sys.stderr)
        return 1
    
    server = JavaAPIServer(args.indexes)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())