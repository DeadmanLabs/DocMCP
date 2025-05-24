# Java API MCP Server - Setup Guide

This guide will help you set up the Java API MCP server for use with Claude Code.

## What This Does

This MCP server allows Claude to:
- Look up Java classes, methods, fields, and constructors
- Check method accessibility (public/private/static/etc.)
- Validate method calls before suggesting code
- Search for classes and packages
- Get inheritance information
- Retrieve enum constants
- **Prevent common coding errors** like "method is private" or "method not found"

## Files Created

- `javadoc_to_json.py` - Converts HTML Javadoc to JSON
- `build_indexes.py` - Builds search indexes from JSON
- `java_api_server.py` - MCP server with 10 lookup tools
- `java_api_indexes.pkl` - Prebuilt indexes (8,211 classes, 54,923 methods)
- `test_indexes.py` - Test script to verify everything works

## Quick Test

Run this to verify the system works:

```bash
cd /mnt/d/Code/NeoForgeDocSpeedrun
python3 test_indexes.py
```

You should see output like:
```
✓ Found: net.minecraft.ChatFormatting
✓ Found 1 overload(s)
✓ Found 22 constants
✓ All tests completed successfully!
```

## MCP Configuration

Add this to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "java-api": {
      "command": "python3",
      "args": [
        "/mnt/d/Code/NeoForgeDocSpeedrun/java_api_server.py",
        "--indexes",
        "/mnt/d/Code/NeoForgeDocSpeedrun/java_api_indexes.pkl"
      ],
      "env": {}
    }
  }
}
```

## Available Tools

Once configured, Claude will have access to these tools:

1. **lookup_class** - Get complete class information
2. **lookup_method** - Find methods with parameters, return types, modifiers
3. **lookup_field** - Find fields with types and accessibility
4. **check_method_accessibility** - Check if method is public/private/static
5. **get_class_constructors** - Get all constructors for a class
6. **search_classes** - Search for classes by name or package
7. **get_package_classes** - List all classes in a package
8. **get_inheritance_info** - Get extends/implements information
9. **get_enum_constants** - Get all enum values
10. **validate_method_call** - Validate if a method call would work

## Example Usage

After configuration, you can ask Claude:

- "Does ChatFormatting have a valueOf method?"
- "What are the parameters for BlockUtil.getLargestRectangleAround?"
- "Is the getColor method in ChatFormatting public?"
- "What enum constants are available in ChatFormatting?"
- "Find all classes in the net.minecraft package"
- "Can I call ChatFormatting.valueOf() statically?"

## Index Statistics

Your Java API server includes:
- **8,211** total classes
- **488** packages  
- **54,923** methods
- **38,104** fields
- **20,865** unique method names

Classes by type:
- **6,003** classes
- **930** records
- **848** interfaces
- **430** enums

## Dependencies

If you need to install MCP for other projects:
```bash
pip install mcp beautifulsoup4
```

## Troubleshooting

1. **"Indexes file not found"** - Run `python3 build_indexes.py json-output`
2. **"JSON files not found"** - Run `python3 javadoc_to_json.py 1.21.x-neoforge json-output`
3. **Server not working** - Test with `python3 test_indexes.py`

## Regenerating for Other Javadoc

To use with different Javadoc:

1. Convert HTML to JSON:
   ```bash
   python3 javadoc_to_json.py /path/to/javadoc /path/to/json-output
   ```

2. Build indexes:
   ```bash
   python3 build_indexes.py /path/to/json-output
   ```

3. Update MCP config to point to the new `java_api_indexes.pkl`

The system works with any standard Javadoc HTML structure!