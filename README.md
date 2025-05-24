# Java API Documentation to JSON Converter & MCP Server

This project converts Javadoc HTML documentation to JSON format and provides an MCP (Model Context Protocol) server for fast Java API lookups.

## Features

### Javadoc to JSON Converter (`javadoc_to_json.py`)
- Converts HTML Javadoc files to structured JSON
- Preserves directory structure
- Extracts comprehensive information:
  - Class/interface/enum/record details
  - Methods with parameters, return types, modifiers
  - Fields with types and modifiers
  - Constructors
  - Enum constants
  - Inheritance information
  - Annotations
  - Nested classes

### MCP Server (`java_api_server.py`)
- Fast Java API lookups for LLMs
- Prevents common coding errors like "method is private" or "method not found"
- 10 powerful tools for API exploration

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Convert Javadoc HTML to JSON:
```bash
python3 javadoc_to_json.py /path/to/javadoc /path/to/json-output
```

3. Build search indexes:
```bash
python3 build_indexes.py /path/to/json-output
```

4. Run the MCP server:
```bash
python3 java_api_server.py --indexes java_api_indexes.pkl
```

## MCP Tools Available

1. **lookup_class** - Get complete class information
2. **lookup_method** - Find methods in a class with all details
3. **lookup_field** - Find fields in a class
4. **check_method_accessibility** - Check if method is public/private/static/etc
5. **get_class_constructors** - Get all constructors for a class
6. **search_classes** - Search for classes by name/package
7. **get_package_classes** - List all classes in a package
8. **get_inheritance_info** - Get extends/implements information
9. **get_enum_constants** - Get all enum values
10. **validate_method_call** - Validate if a method call would work

## Example Usage with Claude

Once configured as an MCP server, you can ask Claude questions like:

- "Does ChatFormatting have a valueOf method?"
- "What are the parameters for BlockUtil.getLargestRectangleAround?"
- "Is the getColor method in ChatFormatting public or private?"
- "What enum constants are available in ChatFormatting?"
- "Find all classes in the net.minecraft package"

## Configuration

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "java-api": {
      "command": "python3",
      "args": ["/path/to/java_api_server.py"],
      "env": {}
    }
  }
}
```

## Statistics (NeoForge 1.21.x example)

- **8,211** total classes processed
- **488** packages
- **54,923** methods indexed
- **38,104** fields indexed
- **20,865** unique method names
- Supports: classes, interfaces, enums, records, annotations

## File Structure

```
├── javadoc_to_json.py      # Convert HTML to JSON
├── build_indexes.py        # Build search indexes
├── java_api_server.py      # MCP server
├── requirements.txt        # Dependencies
├── mcp_config.json        # Example MCP configuration
└── README.md              # This file
```