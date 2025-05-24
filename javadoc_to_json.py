#!/usr/bin/env python3
"""
Javadoc HTML to JSON Converter

This script converts Javadoc HTML files to JSON format while preserving directory structure.
It extracts all important details including class information, fields, methods, constructors,
enum constants, annotations, and more.
"""

import os
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import unquote
import re

try:
    from bs4 import BeautifulSoup, Tag
    import requests
except ImportError:
    print("This script requires BeautifulSoup4. Install it with: pip install beautifulsoup4")
    sys.exit(1)


class JavadocParser:
    """Parser for Javadoc HTML files."""
    
    def __init__(self):
        self.skip_patterns = [
            r'.*package-summary\.html$',
            r'.*package-tree\.html$', 
            r'.*package-use\.html$',
            r'.*overview-.*\.html$',
            r'.*/class-use/.*\.html$',
            r'.*constant-values\.html$',
            r'.*deprecated-list\.html$',
            r'.*serialized-form\.html$',
            r'.*help-doc\.html$',
            r'.*index-.*\.html$',
            r'.*search\.html$',
            r'.*allclasses-index\.html$',
            r'.*allpackages-index\.html$',
            r'.*element-list$',
            r'.*\.js$',
            r'.*\.css$',
            r'.*\.svg$',
            r'.*\.png$',
            r'.*\.md$',
            r'.*/legal/.*',
            r'.*/script-dir/.*',
            r'.*/resources/.*'
        ]
    
    def should_skip_file(self, filepath: str) -> bool:
        """Check if a file should be skipped based on patterns."""
        for pattern in self.skip_patterns:
            if re.match(pattern, filepath):
                return True
        return False
    
    def extract_text_content(self, element: Union[Tag, str, None]) -> str:
        """Extract clean text content from an element."""
        if element is None:
            return ""
        if isinstance(element, str):
            return element.strip()
        if hasattr(element, 'get_text'):
            text = element.get_text(separator=' ', strip=True)
            # Clean up excessive whitespace
            return re.sub(r'\s+', ' ', text).strip()
        return str(element).strip()
    
    def extract_modifiers(self, element: Tag) -> List[str]:
        """Extract modifiers from a member signature."""
        modifiers = []
        if element:
            modifiers_elem = element.find('span', class_='modifiers')
            if modifiers_elem:
                mod_text = self.extract_text_content(modifiers_elem)
                # Split and clean modifiers
                modifiers = [m.strip() for m in mod_text.split() if m.strip()]
        return modifiers
    
    def extract_annotations(self, element: Tag) -> List[str]:
        """Extract annotations from a member signature."""
        annotations = []
        if element:
            annotation_elems = element.find_all('span', class_='annotations')
            for elem in annotation_elems:
                ann_text = self.extract_text_content(elem)
                if ann_text and ann_text.startswith('@'):
                    annotations.append(ann_text)
        return annotations
    
    def extract_type_info(self, element: Tag) -> Dict[str, Any]:
        """Extract type information from an element."""
        type_info = {
            'name': '',
            'qualified_name': '',
            'generic_params': []
        }
        
        if element:
            return_type_elem = element.find('span', class_='return-type')
            element_name_elem = element.find('span', class_='element-name')
            
            if return_type_elem:
                type_info['name'] = self.extract_text_content(return_type_elem)
                type_info['qualified_name'] = type_info['name']
            elif element_name_elem:
                type_info['name'] = self.extract_text_content(element_name_elem)
                type_info['qualified_name'] = type_info['name']
        
        return type_info
    
    def extract_parameters(self, element: Tag) -> List[Dict[str, Any]]:
        """Extract parameter information from a method or constructor."""
        parameters = []
        if element:
            params_elem = element.find('span', class_='parameters')
            if params_elem:
                param_text = self.extract_text_content(params_elem)
                # Remove parentheses
                param_text = param_text.strip('()')
                
                if param_text and param_text.strip():
                    # Split parameters by comma, but be careful with generics
                    param_parts = self._split_parameters(param_text)
                    
                    for param in param_parts:
                        param = param.strip()
                        if param:
                            # Extract annotations, type, and name
                            param_info = self._parse_parameter(param)
                            if param_info:
                                parameters.append(param_info)
        
        return parameters
    
    def _split_parameters(self, param_text: str) -> List[str]:
        """Split parameter text by comma, respecting generic brackets."""
        params = []
        current_param = ""
        bracket_depth = 0
        
        for char in param_text:
            if char == '<':
                bracket_depth += 1
            elif char == '>':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                if current_param.strip():
                    params.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _parse_parameter(self, param: str) -> Optional[Dict[str, Any]]:
        """Parse a single parameter string."""
        # Remove extra whitespace
        param = re.sub(r'\s+', ' ', param).strip()
        
        # Extract annotations
        annotations = []
        while param.startswith('@'):
            end_idx = param.find(' ')
            if end_idx == -1:
                break
            annotations.append(param[:end_idx])
            param = param[end_idx:].strip()
        
        # Split into type and name
        parts = param.split()
        if len(parts) >= 2:
            param_type = ' '.join(parts[:-1])
            param_name = parts[-1]
            
            return {
                'name': param_name,
                'type': param_type,
                'annotations': annotations
            }
        
        return None
    
    def extract_methods(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract method information from the HTML."""
        methods = []
        
        # Find method details section
        method_details = soup.find('section', class_='method-details')
        if method_details:
            method_sections = method_details.find_all('section', class_='detail')
            
            for section in method_sections:
                method_info = self._extract_method_info(section)
                if method_info:
                    methods.append(method_info)
        
        return methods
    
    def _extract_method_info(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract information from a single method section."""
        method_info = {
            'name': '',
            'modifiers': [],
            'annotations': [],
            'return_type': '',
            'parameters': [],
            'exceptions': [],
            'description': '',
            'overrides': None,
            'since': None,
            'deprecated': False
        }
        
        # Get method name from heading
        heading = section.find(['h3', 'h4'])
        if heading:
            method_info['name'] = self.extract_text_content(heading)
        
        # Get method signature
        signature = section.find('div', class_='member-signature')
        if signature:
            method_info['modifiers'] = self.extract_modifiers(signature)
            method_info['annotations'] = self.extract_annotations(signature)
            
            # Extract return type
            return_type_elem = signature.find('span', class_='return-type')
            if return_type_elem:
                method_info['return_type'] = self.extract_text_content(return_type_elem)
            
            # Extract parameters
            method_info['parameters'] = self.extract_parameters(signature)
        
        # Extract description and other details
        self._extract_method_details(section, method_info)
        
        return method_info
    
    def _extract_method_details(self, section: Tag, method_info: Dict[str, Any]):
        """Extract additional method details like description, exceptions, etc."""
        # Extract description
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            method_info['description'] = self.extract_text_content(desc_elem)
        
        # Extract additional details from dl tags
        dl_tags = section.find_all('dl', class_='notes')
        for dl in dl_tags:
            dt_tags = dl.find_all('dt')
            dd_tags = dl.find_all('dd')
            
            for dt, dd in zip(dt_tags, dd_tags):
                dt_text = self.extract_text_content(dt).lower()
                dd_text = self.extract_text_content(dd)
                
                if 'throws' in dt_text or 'exception' in dt_text:
                    method_info['exceptions'].append(dd_text)
                elif 'overrides' in dt_text:
                    method_info['overrides'] = dd_text
                elif 'since' in dt_text:
                    method_info['since'] = dd_text
                elif 'deprecated' in dt_text:
                    method_info['deprecated'] = True
    
    def extract_constructors(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract constructor information from the HTML."""
        constructors = []
        
        # Find constructor details section
        constructor_details = soup.find('section', class_='constructor-details')
        if constructor_details:
            constructor_sections = constructor_details.find_all('section', class_='detail')
            
            for section in constructor_sections:
                constructor_info = self._extract_constructor_info(section)
                if constructor_info:
                    constructors.append(constructor_info)
        
        return constructors
    
    def _extract_constructor_info(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract information from a single constructor section."""
        constructor_info = {
            'name': '',
            'modifiers': [],
            'annotations': [],
            'parameters': [],
            'exceptions': [],
            'description': '',
            'deprecated': False
        }
        
        # Get constructor name from heading
        heading = section.find(['h3', 'h4'])
        if heading:
            constructor_info['name'] = self.extract_text_content(heading)
        
        # Get constructor signature
        signature = section.find('div', class_='member-signature')
        if signature:
            constructor_info['modifiers'] = self.extract_modifiers(signature)
            constructor_info['annotations'] = self.extract_annotations(signature)
            constructor_info['parameters'] = self.extract_parameters(signature)
        
        # Extract description and other details
        self._extract_constructor_details(section, constructor_info)
        
        return constructor_info
    
    def _extract_constructor_details(self, section: Tag, constructor_info: Dict[str, Any]):
        """Extract additional constructor details."""
        # Extract description
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            constructor_info['description'] = self.extract_text_content(desc_elem)
        
        # Extract exceptions and other details
        dl_tags = section.find_all('dl', class_='notes')
        for dl in dl_tags:
            dt_tags = dl.find_all('dt')
            dd_tags = dl.find_all('dd')
            
            for dt, dd in zip(dt_tags, dd_tags):
                dt_text = self.extract_text_content(dt).lower()
                dd_text = self.extract_text_content(dd)
                
                if 'throws' in dt_text or 'exception' in dt_text:
                    constructor_info['exceptions'].append(dd_text)
                elif 'deprecated' in dt_text:
                    constructor_info['deprecated'] = True
    
    def extract_fields(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract field information from the HTML."""
        fields = []
        
        # Find field details section
        field_details = soup.find('section', class_='field-details')
        if field_details:
            field_sections = field_details.find_all('section', class_='detail')
            
            for section in field_sections:
                field_info = self._extract_field_info(section)
                if field_info:
                    fields.append(field_info)
        
        return fields
    
    def _extract_field_info(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract information from a single field section."""
        field_info = {
            'name': '',
            'modifiers': [],
            'annotations': [],
            'type': '',
            'value': None,
            'description': '',
            'deprecated': False
        }
        
        # Get field name from heading
        heading = section.find(['h3', 'h4'])
        if heading:
            field_info['name'] = self.extract_text_content(heading)
        
        # Get field signature
        signature = section.find('div', class_='member-signature')
        if signature:
            field_info['modifiers'] = self.extract_modifiers(signature)
            field_info['annotations'] = self.extract_annotations(signature)
            
            # Extract field type
            return_type_elem = signature.find('span', class_='return-type')
            if return_type_elem:
                field_info['type'] = self.extract_text_content(return_type_elem)
        
        # Extract description and other details
        self._extract_field_details(section, field_info)
        
        return field_info
    
    def _extract_field_details(self, section: Tag, field_info: Dict[str, Any]):
        """Extract additional field details."""
        # Extract description
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            field_info['description'] = self.extract_text_content(desc_elem)
        
        # Extract constant value or other details
        dl_tags = section.find_all('dl', class_='notes')
        for dl in dl_tags:
            dt_tags = dl.find_all('dt')
            dd_tags = dl.find_all('dd')
            
            for dt, dd in zip(dt_tags, dd_tags):
                dt_text = self.extract_text_content(dt).lower()
                dd_text = self.extract_text_content(dd)
                
                if 'see also' in dt_text:
                    # Handle constant values reference
                    pass
                elif 'deprecated' in dt_text:
                    field_info['deprecated'] = True
    
    def extract_enum_constants(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract enum constant information from the HTML."""
        enum_constants = []
        
        # Find enum constant details section
        enum_details = soup.find('section', class_='constant-details')
        if enum_details:
            enum_sections = enum_details.find_all('section', class_='detail')
            
            for section in enum_sections:
                enum_info = self._extract_enum_constant_info(section)
                if enum_info:
                    enum_constants.append(enum_info)
        
        return enum_constants
    
    def _extract_enum_constant_info(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract information from a single enum constant section."""
        enum_info = {
            'name': '',
            'modifiers': [],
            'annotations': [],
            'description': '',
            'deprecated': False
        }
        
        # Get enum constant name from heading
        heading = section.find(['h3', 'h4'])
        if heading:
            enum_info['name'] = self.extract_text_content(heading)
        
        # Get enum constant signature
        signature = section.find('div', class_='member-signature')
        if signature:
            enum_info['modifiers'] = self.extract_modifiers(signature)
            enum_info['annotations'] = self.extract_annotations(signature)
        
        # Extract description
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            enum_info['description'] = self.extract_text_content(desc_elem)
        
        return enum_info
    
    def extract_nested_classes(self, soup: BeautifulSoup) -> List[str]:
        """Extract nested class names from the HTML."""
        nested_classes = []
        
        # Find nested class summary section
        nested_summary = soup.find('section', class_='nested-class-summary')
        if nested_summary:
            # Look for class links in the summary table
            links = nested_summary.find_all('a', class_='type-name-link')
            for link in links:
                class_name = self.extract_text_content(link)
                if class_name:
                    nested_classes.append(class_name)
        
        return nested_classes
    
    def extract_inheritance_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract inheritance information from the HTML."""
        inheritance_info = {
            'extends': None,
            'implements': [],
            'inheritance_tree': []
        }
        
        # Find inheritance tree
        inheritance_div = soup.find('div', class_='inheritance')
        if inheritance_div:
            # Extract inheritance chain
            links = inheritance_div.find_all('a')
            for link in links:
                class_name = self.extract_text_content(link)
                if class_name and class_name != 'Object':
                    inheritance_info['inheritance_tree'].append(class_name)
        
        # Find implemented interfaces
        class_desc = soup.find('section', class_='class-description')
        if class_desc:
            dl_tags = class_desc.find_all('dl', class_='notes')
            for dl in dl_tags:
                dt_tags = dl.find_all('dt')
                dd_tags = dl.find_all('dd')
                
                for dt, dd in zip(dt_tags, dd_tags):
                    dt_text = self.extract_text_content(dt).lower()
                    
                    if 'all implemented interfaces' in dt_text:
                        # Extract interface names
                        interface_links = dd.find_all('a')
                        for link in interface_links:
                            interface_name = self.extract_text_content(link)
                            if interface_name:
                                inheritance_info['implements'].append(interface_name)
        
        return inheritance_info
    
    def extract_class_info(self, soup: BeautifulSoup, file_path: str) -> Dict[str, Any]:
        """Extract complete class information from the HTML."""
        class_info = {
            'type': 'unknown',
            'name': '',
            'qualified_name': '',
            'package': '',
            'modifiers': [],
            'annotations': [],
            'description': '',
            'inheritance': {},
            'nested_classes': [],
            'fields': [],
            'constructors': [],
            'methods': [],
            'enum_constants': [],
            'since': None,
            'deprecated': False,
            'source_file': file_path
        }
        
        # Extract package information
        package_elem = soup.find('span', class_='package-label-in-type')
        if package_elem and package_elem.find_next_sibling('a'):
            class_info['package'] = self.extract_text_content(package_elem.find_next_sibling('a'))
        
        # Extract class name and type
        title_elem = soup.find('h1', class_='title')
        if title_elem:
            title_text = self.extract_text_content(title_elem)
            # Determine type from title
            if 'Interface' in title_text:
                class_info['type'] = 'interface'
            elif 'Enum Class' in title_text or 'Enum' in title_text:
                class_info['type'] = 'enum'
            elif 'Annotation Interface' in title_text:
                class_info['type'] = 'annotation'
            elif 'Record Class' in title_text:
                class_info['type'] = 'record'
            elif 'Class' in title_text:
                class_info['type'] = 'class'
            
            # Extract class name
            class_name = title_text.split()[-1]  # Get the last word which should be the class name
            class_info['name'] = class_name
            
            # Build qualified name
            if class_info['package']:
                class_info['qualified_name'] = f"{class_info['package']}.{class_name}"
            else:
                class_info['qualified_name'] = class_name
        
        # Extract class signature (modifiers, annotations)
        type_signature = soup.find('div', class_='type-signature')
        if type_signature:
            class_info['modifiers'] = self.extract_modifiers(type_signature)
            class_info['annotations'] = self.extract_annotations(type_signature)
        
        # Extract class description
        class_desc = soup.find('section', class_='class-description')
        if class_desc:
            # Look for description block
            desc_block = class_desc.find('div', class_='block')
            if desc_block:
                class_info['description'] = self.extract_text_content(desc_block)
        
        # Extract inheritance information
        class_info['inheritance'] = self.extract_inheritance_info(soup)
        
        # Extract nested classes
        class_info['nested_classes'] = self.extract_nested_classes(soup)
        
        # Extract fields
        class_info['fields'] = self.extract_fields(soup)
        
        # Extract constructors
        class_info['constructors'] = self.extract_constructors(soup)
        
        # Extract methods
        class_info['methods'] = self.extract_methods(soup)
        
        # Extract enum constants (if applicable)
        if class_info['type'] == 'enum':
            class_info['enum_constants'] = self.extract_enum_constants(soup)
        
        return class_info
    
    def parse_html_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a single HTML file and extract class information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check if this is a class/interface/enum documentation page
            if not self._is_class_doc_page(soup):
                return None
            
            return self.extract_class_info(soup, file_path)
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return None
    
    def _is_class_doc_page(self, soup: BeautifulSoup) -> bool:
        """Check if the HTML page is a class/interface/enum documentation page."""
        # Check for class description section
        class_desc = soup.find('section', class_='class-description')
        if not class_desc:
            return False
        
        # Check for title indicating this is a class/interface/enum
        title = soup.find('h1', class_='title')
        if title:
            title_text = self.extract_text_content(title)
            keywords = ['Class', 'Interface', 'Enum', 'Annotation', 'Record']
            return any(keyword in title_text for keyword in keywords)
        
        return False


def convert_javadoc_to_json(input_dir: str, output_dir: str):
    """Convert Javadoc HTML files to JSON format."""
    parser = JavadocParser()
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all HTML files
    html_files = list(input_path.glob('**/*.html'))
    total_files = len(html_files)
    processed_files = 0
    converted_files = 0
    
    print(f"Found {total_files} HTML files to process...")
    
    for html_file in html_files:
        relative_path = html_file.relative_to(input_path)
        
        # Skip files that should not be processed
        if parser.should_skip_file(str(relative_path)):
            continue
        
        processed_files += 1
        
        # Parse the HTML file
        class_info = parser.parse_html_file(str(html_file))
        if class_info:
            # Create JSON output path
            json_path = output_path / relative_path.with_suffix('.json')
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON file
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(class_info, f, indent=2, ensure_ascii=False)
                
                converted_files += 1
                
                if converted_files % 50 == 0:
                    print(f"Converted {converted_files} files...")
                    
            except Exception as e:
                print(f"Error writing JSON file {json_path}: {e}")
    
    print(f"\nConversion complete!")
    print(f"Processed {processed_files} HTML files")
    print(f"Successfully converted {converted_files} files to JSON")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Convert Javadoc HTML files to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python javadoc_to_json.py ./javadoc ./json-output
  python javadoc_to_json.py /path/to/javadoc /path/to/output --verbose
        """
    )
    
    parser.add_argument(
        'input_dir',
        help='Input directory containing Javadoc HTML files'
    )
    
    parser.add_argument(
        'output_dir',
        help='Output directory for JSON files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Input directory: {args.input_dir}")
        print(f"Output directory: {args.output_dir}")
        print()
    
    try:
        convert_javadoc_to_json(args.input_dir, args.output_dir)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user.")
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()