#!/usr/bin/env python3
"""
Enhanced Javadoc HTML to JSON Converter
Supports multiple javadoc formats from older to newer versions.
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


class EnhancedJavadocParser:
    """Enhanced parser for Javadoc HTML files supporting multiple versions."""
    
    def __init__(self):
        self.skip_patterns = [
            r'.*package-summary\.html$',
            r'.*package-tree\.html$', 
            r'.*package-use\.html$',
            r'.*package-frame\.html$',
            r'.*overview-.*\.html$',
            r'.*/class-use/.*\.html$',
            r'.*constant-values\.html$',
            r'.*deprecated-list\.html$',
            r'.*serialized-form\.html$',
            r'.*help-doc\.html$',
            r'.*index-.*\.html$',
            r'.*search\.html$',
            r'.*allclasses.*\.html$',
            r'.*allpackages.*\.html$',
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
    
    def detect_javadoc_version(self, soup: BeautifulSoup) -> str:
        """Detect the javadoc version from HTML structure."""
        # Check for modern javadoc (newer structure)
        if soup.find('section', class_='class-description'):
            return 'modern'
        
        # Check for 1.17.1 specific format (uses 'description' instead of 'class-description')
        if soup.find('section', class_='description') and soup.find('h1', class_='title'):
            return 'modern'
        
        # Check for legacy javadoc (older structure)
        if soup.find('div', class_='header') and soup.find('h2', class_='title'):
            return 'legacy'
        
        return 'unknown'
    
    def extract_text_content(self, element: Union[Tag, str, None]) -> str:
        """Extract clean text content from an element."""
        if element is None:
            return ""
        if isinstance(element, str):
            return element.strip()
        if hasattr(element, 'get_text'):
            text = element.get_text(separator=' ', strip=True)
            return re.sub(r'\s+', ' ', text).strip()
        return str(element).strip()
    
    def extract_class_info_modern(self, soup: BeautifulSoup, file_path: str) -> Dict[str, Any]:
        """Extract class info from modern javadoc format."""
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
        
        # Extract package
        package_elem = soup.find('span', class_='package-label-in-type')
        if package_elem and package_elem.find_next_sibling('a'):
            class_info['package'] = self.extract_text_content(package_elem.find_next_sibling('a'))
        
        # Extract class name and type
        title_elem = soup.find('h1', class_='title')
        if title_elem:
            title_text = self.extract_text_content(title_elem)
            if 'Interface' in title_text:
                class_info['type'] = 'interface'
            elif 'Enum' in title_text:
                class_info['type'] = 'enum'
            elif 'Annotation' in title_text:
                class_info['type'] = 'annotation'
            elif 'Record' in title_text:
                class_info['type'] = 'record'
            elif 'Class' in title_text:
                class_info['type'] = 'class'
            
            class_name = title_text.split()[-1]
            class_info['name'] = class_name
            
            if class_info['package']:
                class_info['qualified_name'] = f"{class_info['package']}.{class_name}"
            else:
                class_info['qualified_name'] = class_name
        
        # Extract modifiers from type signature
        type_signature = soup.find('div', class_='type-signature')
        if type_signature:
            modifiers_elem = type_signature.find('span', class_='modifiers')
            if modifiers_elem:
                mod_text = self.extract_text_content(modifiers_elem)
                class_info['modifiers'] = [m.strip() for m in mod_text.split() if m.strip()]
        
        # Extract description
        class_desc = soup.find('section', class_='class-description')
        if not class_desc:
            # Try 1.17.1 format
            class_desc = soup.find('section', class_='description')
        
        if class_desc:
            desc_block = class_desc.find('div', class_='block')
            if desc_block:
                class_info['description'] = self.extract_text_content(desc_block)
        
        # Extract inheritance
        class_info['inheritance'] = self.extract_inheritance_modern(soup)
        
        # Extract methods
        class_info['methods'] = self.extract_methods_modern(soup)
        
        # Extract fields
        class_info['fields'] = self.extract_fields_modern(soup)
        
        # Extract constructors
        class_info['constructors'] = self.extract_constructors_modern(soup)
        
        return class_info
    
    def extract_class_info_legacy(self, soup: BeautifulSoup, file_path: str) -> Dict[str, Any]:
        """Extract class info from legacy javadoc format."""
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
        
        # Extract class name from title
        title_elem = soup.find('h2', class_='title')
        if title_elem:
            title_text = self.extract_text_content(title_elem)
            # Extract class name (format: "Class ClassName" or "Interface InterfaceName", etc.)
            parts = title_text.split()
            if len(parts) >= 2:
                class_type_word = parts[0].lower()
                class_name = parts[1]
                
                class_info['name'] = class_name
                
                if class_type_word == 'interface':
                    class_info['type'] = 'interface'
                elif class_type_word == 'enum':
                    class_info['type'] = 'enum'
                elif class_type_word == 'class':
                    class_info['type'] = 'class'
                elif 'annotation' in class_type_word:
                    class_info['type'] = 'annotation'
        
        # Extract package from inheritance or contentContainer
        inheritance_list = soup.find('ul', class_='inheritance')
        if inheritance_list:
            # First item is usually java.lang.Object, second might have package info
            li_elements = inheritance_list.find_all('li')
            for li in li_elements:
                text = self.extract_text_content(li)
                if '.' in text and text != 'java.lang.Object':
                    # This might contain package info
                    if '.' in class_info['name']:
                        # Class name itself contains package
                        parts = class_info['name'].rsplit('.', 1)
                        if len(parts) == 2:
                            class_info['package'] = parts[0]
                            class_info['name'] = parts[1]
                    else:
                        # Try to infer package from file path
                        path_parts = file_path.split('/')
                        if len(path_parts) > 3:
                            # Look for net/minecraft pattern
                            for i, part in enumerate(path_parts):
                                if part == 'net' and i + 1 < len(path_parts) and path_parts[i + 1] == 'minecraft':
                                    package_parts = path_parts[i:-1]  # exclude filename
                                    class_info['package'] = '.'.join(package_parts)
                                    break
        
        # Set qualified name
        if class_info['package']:
            class_info['qualified_name'] = f"{class_info['package']}.{class_info['name']}"
        else:
            class_info['qualified_name'] = class_info['name']
        
        # Extract description from first contentContainer
        content_container = soup.find('div', class_='contentContainer')
        if content_container:
            # Look for description block
            desc_block = content_container.find('div', class_='block')
            if desc_block:
                class_info['description'] = self.extract_text_content(desc_block)
        
        # Extract inheritance
        class_info['inheritance'] = self.extract_inheritance_legacy(soup)
        
        # Extract methods
        class_info['methods'] = self.extract_methods_legacy(soup)
        
        # Extract fields
        class_info['fields'] = self.extract_fields_legacy(soup)
        
        # Extract constructors
        class_info['constructors'] = self.extract_constructors_legacy(soup)
        
        return class_info
    
    def extract_inheritance_modern(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract inheritance info from modern format."""
        inheritance_info = {'extends': None, 'implements': [], 'inheritance_tree': []}
        
        inheritance_div = soup.find('div', class_='inheritance')
        if inheritance_div:
            links = inheritance_div.find_all('a')
            for link in links:
                class_name = self.extract_text_content(link)
                if class_name and class_name != 'Object':
                    inheritance_info['inheritance_tree'].append(class_name)
        
        return inheritance_info
    
    def extract_inheritance_legacy(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract inheritance info from legacy format."""
        inheritance_info = {'extends': None, 'implements': [], 'inheritance_tree': []}
        
        inheritance_list = soup.find('ul', class_='inheritance')
        if inheritance_list:
            links = inheritance_list.find_all('a')
            for link in links:
                class_name = self.extract_text_content(link)
                if class_name and class_name != 'java.lang.Object':
                    inheritance_info['inheritance_tree'].append(class_name)
        
        return inheritance_info
    
    def extract_methods_modern(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract methods from modern format."""
        methods = []
        method_details = soup.find('section', class_='method-details')
        if method_details:
            method_sections = method_details.find_all('section', class_='detail')
            for section in method_sections:
                method_info = self.extract_method_info_modern(section)
                if method_info:
                    methods.append(method_info)
        return methods
    
    def extract_methods_legacy(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract methods from legacy format."""
        methods = []
        
        # Look for method detail section
        method_detail_anchor = soup.find('a', {'name': 'method.detail'})
        if method_detail_anchor:
            # Find the parent container
            detail_container = method_detail_anchor.find_parent()
            if detail_container:
                # Look for method entries
                method_headers = detail_container.find_all('h4')
                for header in method_headers:
                    method_info = self.extract_method_info_legacy(header)
                    if method_info:
                        methods.append(method_info)
        
        return methods
    
    def extract_method_info_modern(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract method info from modern section."""
        method_info = {
            'name': '',
            'modifiers': [],
            'return_type': '',
            'parameters': [],
            'description': '',
            'deprecated': False
        }
        
        heading = section.find(['h3', 'h4'])
        if heading:
            method_info['name'] = self.extract_text_content(heading)
        
        signature = section.find('div', class_='member-signature')
        if signature:
            modifiers_elem = signature.find('span', class_='modifiers')
            if modifiers_elem:
                mod_text = self.extract_text_content(modifiers_elem)
                method_info['modifiers'] = [m.strip() for m in mod_text.split() if m.strip()]
            
            return_type_elem = signature.find('span', class_='return-type')
            if return_type_elem:
                method_info['return_type'] = self.extract_text_content(return_type_elem)
            
            # Extract parameters
            parameters_elem = signature.find('span', class_='parameters')
            if parameters_elem:
                method_info['parameters'] = self.extract_parameters(parameters_elem)
        
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            method_info['description'] = self.extract_text_content(desc_elem)
        
        return method_info
    
    def extract_method_info_legacy(self, header: Tag) -> Optional[Dict[str, Any]]:
        """Extract method info from legacy header."""
        method_info = {
            'name': '',
            'modifiers': [],
            'return_type': '',
            'parameters': [],
            'description': '',
            'deprecated': False
        }
        
        if header:
            method_info['name'] = self.extract_text_content(header)
            
            # Try to find the method signature
            next_elem = header.find_next_sibling()
            if next_elem and next_elem.name == 'pre':
                # This contains the full signature
                sig_text = self.extract_text_content(next_elem)
                # Parse basic modifiers and return type
                words = sig_text.split()
                if len(words) > 0:
                    # Simple parsing - first words are usually modifiers
                    modifiers = []
                    for word in words:
                        if word in ['public', 'private', 'protected', 'static', 'final', 'abstract', 'synchronized']:
                            modifiers.append(word)
                        else:
                            break
                    method_info['modifiers'] = modifiers
        
        return method_info
    
    def extract_fields_modern(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract fields from modern format."""
        fields = []
        field_details = soup.find('section', class_='field-details')
        if field_details:
            field_sections = field_details.find_all('section', class_='detail')
            for section in field_sections:
                field_info = self.extract_field_info_modern(section)
                if field_info:
                    fields.append(field_info)
        return fields
    
    def extract_fields_legacy(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract fields from legacy format."""
        fields = []
        
        # Look for field detail section
        field_detail_anchor = soup.find('a', {'name': 'field.detail'})
        if field_detail_anchor:
            detail_container = field_detail_anchor.find_parent()
            if detail_container:
                field_headers = detail_container.find_all('h4')
                for header in field_headers:
                    field_info = self.extract_field_info_legacy(header)
                    if field_info:
                        fields.append(field_info)
        
        return fields
    
    def extract_field_info_modern(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract field info from modern section."""
        field_info = {
            'name': '',
            'modifiers': [],
            'type': '',
            'description': '',
            'deprecated': False
        }
        
        heading = section.find(['h3', 'h4'])
        if heading:
            field_info['name'] = self.extract_text_content(heading)
        
        signature = section.find('div', class_='member-signature')
        if signature:
            modifiers_elem = signature.find('span', class_='modifiers')
            if modifiers_elem:
                mod_text = self.extract_text_content(modifiers_elem)
                field_info['modifiers'] = [m.strip() for m in mod_text.split() if m.strip()]
            
            return_type_elem = signature.find('span', class_='return-type')
            if return_type_elem:
                field_info['type'] = self.extract_text_content(return_type_elem)
        
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            field_info['description'] = self.extract_text_content(desc_elem)
        
        return field_info
    
    def extract_field_info_legacy(self, header: Tag) -> Optional[Dict[str, Any]]:
        """Extract field info from legacy header."""
        field_info = {
            'name': '',
            'modifiers': [],
            'type': '',
            'description': '',
            'deprecated': False
        }
        
        if header:
            field_info['name'] = self.extract_text_content(header)
        
        return field_info
    
    def extract_constructors_modern(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract constructors from modern format."""
        constructors = []
        constructor_details = soup.find('section', class_='constructor-details')
        if constructor_details:
            constructor_sections = constructor_details.find_all('section', class_='detail')
            for section in constructor_sections:
                constructor_info = self.extract_constructor_info_modern(section)
                if constructor_info:
                    constructors.append(constructor_info)
        return constructors
    
    def extract_constructors_legacy(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract constructors from legacy format."""
        constructors = []
        
        # Look for constructor detail section
        constructor_detail_anchor = soup.find('a', {'name': 'constructor.detail'})
        if constructor_detail_anchor:
            detail_container = constructor_detail_anchor.find_parent()
            if detail_container:
                constructor_headers = detail_container.find_all('h4')
                for header in constructor_headers:
                    constructor_info = self.extract_constructor_info_legacy(header)
                    if constructor_info:
                        constructors.append(constructor_info)
        
        return constructors
    
    def extract_constructor_info_modern(self, section: Tag) -> Optional[Dict[str, Any]]:
        """Extract constructor info from modern section."""
        constructor_info = {
            'name': '',
            'modifiers': [],
            'parameters': [],
            'description': '',
            'deprecated': False
        }
        
        heading = section.find(['h3', 'h4'])
        if heading:
            constructor_info['name'] = self.extract_text_content(heading)
        
        signature = section.find('div', class_='member-signature')
        if signature:
            modifiers_elem = signature.find('span', class_='modifiers')
            if modifiers_elem:
                mod_text = self.extract_text_content(modifiers_elem)
                constructor_info['modifiers'] = [m.strip() for m in mod_text.split() if m.strip()]
            
            # Extract parameters
            parameters_elem = signature.find('span', class_='parameters')
            if parameters_elem:
                constructor_info['parameters'] = self.extract_parameters(parameters_elem)
        
        desc_elem = section.find('div', class_='block')
        if desc_elem:
            constructor_info['description'] = self.extract_text_content(desc_elem)
        
        return constructor_info
    
    def extract_constructor_info_legacy(self, header: Tag) -> Optional[Dict[str, Any]]:
        """Extract constructor info from legacy header."""
        constructor_info = {
            'name': '',
            'modifiers': [],
            'parameters': [],
            'description': '',
            'deprecated': False
        }
        
        if header:
            constructor_info['name'] = self.extract_text_content(header)
        
        return constructor_info
    
    def extract_parameters(self, parameters_elem: Tag) -> List[Dict[str, Any]]:
        """Extract parameters from a parameters span element."""
        parameters = []
        if not parameters_elem:
            return parameters
        
        # Get the text content and parse it
        param_text = self.extract_text_content(parameters_elem)
        if not param_text or param_text.strip() == '()':
            return parameters
        
        # Remove outer parentheses
        param_text = param_text.strip()
        if param_text.startswith('(') and param_text.endswith(')'):
            param_text = param_text[1:-1].strip()
        
        if not param_text:
            return parameters
        
        # Split by comma, but be careful with generics
        param_parts = self._split_parameters(param_text)
        
        for part in param_parts:
            param_info = self._parse_parameter(part.strip())
            if param_info:
                parameters.append(param_info)
        
        return parameters
    
    def _split_parameters(self, param_text: str) -> List[str]:
        """Split parameter text by commas, respecting generic types."""
        parts = []
        current_part = ''
        depth = 0
        
        for char in param_text:
            if char in '<(':
                depth += 1
            elif char in '>)':
                depth -= 1
            elif char == ',' and depth == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ''
                continue
            
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def _parse_parameter(self, param_text: str) -> Optional[Dict[str, Any]]:
        """Parse a single parameter string into parameter info."""
        if not param_text:
            return None
        
        # Handle annotations like @Nullable
        annotations = []
        # Check for annotations both at start of line and embedded in text
        words = param_text.split()
        filtered_words = []
        
        for word in words:
            if word.startswith('@'):
                annotations.append(word[1:])  # Remove @
            else:
                filtered_words.append(word)
        
        if len(filtered_words) < 2:
            return None
        
        # Last word is the parameter name
        param_name = filtered_words[-1]
        # Everything else is the type
        param_type = ' '.join(filtered_words[:-1])
        
        return {
            'name': param_name,
            'type': param_type,
            'annotations': annotations
        }
    
    def parse_html_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a single HTML file and extract class information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check if this is a class documentation page
            if not self._is_class_doc_page(soup):
                return None
            
            # Detect javadoc version and parse accordingly
            version = self.detect_javadoc_version(soup)
            
            if version == 'modern':
                return self.extract_class_info_modern(soup, file_path)
            elif version == 'legacy':
                return self.extract_class_info_legacy(soup, file_path)
            else:
                print(f"Unknown javadoc format in {file_path}")
                return None
                
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return None
    
    def _is_class_doc_page(self, soup: BeautifulSoup) -> bool:
        """Check if the HTML page is a class documentation page."""
        # Modern format
        if soup.find('section', class_='class-description'):
            return True
        
        # 1.17.1 format (uses 'description' instead of 'class-description')
        if soup.find('section', class_='description'):
            title = soup.find('h1', class_='title')
            if title:
                title_text = self.extract_text_content(title)
                keywords = ['Class', 'Interface', 'Enum', 'Annotation', 'Record']
                return any(keyword in title_text for keyword in keywords)
        
        # Legacy format
        if soup.find('h2', class_='title'):
            title = soup.find('h2', class_='title')
            if title:
                title_text = self.extract_text_content(title)
                keywords = ['Class', 'Interface', 'Enum', 'Annotation']
                return any(keyword in title_text for keyword in keywords)
        
        return False


def convert_javadoc_to_json(input_dir: str, output_dir: str):
    """Convert Javadoc HTML files to JSON format."""
    parser = EnhancedJavadocParser()
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    html_files = list(input_path.glob('**/*.html'))
    total_files = len(html_files)
    processed_files = 0
    converted_files = 0
    
    print(f"Found {total_files} HTML files to process...")
    
    for html_file in html_files:
        relative_path = html_file.relative_to(input_path)
        
        if parser.should_skip_file(str(relative_path)):
            continue
        
        processed_files += 1
        
        class_info = parser.parse_html_file(str(html_file))
        if class_info:
            json_path = output_path / relative_path.with_suffix('.json')
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
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
    parser = argparse.ArgumentParser(description="Enhanced Javadoc HTML to JSON converter")
    
    parser.add_argument('input_dir', help='Input directory containing Javadoc HTML files')
    parser.add_argument('output_dir', help='Output directory for JSON files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
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