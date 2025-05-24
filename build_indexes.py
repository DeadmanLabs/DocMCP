#!/usr/bin/env python3
"""
Build indexes from JSON files for fast Java API lookups.
"""

import json
import os
import pickle
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict
import re


class JavaAPIIndexBuilder:
    """Builds search indexes from Javadoc JSON files."""
    
    def __init__(self):
        self.indexes = {
            'classes_by_name': {},           # class_name -> class_info
            'classes_by_qualified_name': {}, # qualified_name -> class_info
            'methods_by_class': defaultdict(dict),  # class_name -> {method_name -> [method_info]}
            'fields_by_class': defaultdict(dict),   # class_name -> {field_name -> field_info}
            'constructors_by_class': defaultdict(list), # class_name -> [constructor_info]
            'packages': defaultdict(list),   # package_name -> [class_names]
            'inheritance_tree': {},          # class_name -> inheritance_info
            'enum_constants_by_class': defaultdict(dict), # class_name -> {constant_name -> constant_info}
            'nested_classes': defaultdict(list), # parent_class -> [nested_class_names]
            'all_method_names': set(),       # All unique method names
            'all_field_names': set(),        # All unique field names
            'classes_by_type': defaultdict(list), # 'class'/'interface'/'enum' -> [class_names]
        }
    
    def build_indexes(self, json_dir: str) -> Dict[str, Any]:
        """Build all indexes from JSON files in the directory."""
        json_path = Path(json_dir)
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON directory not found: {json_dir}")
        
        json_files = list(json_path.glob('**/*.json'))
        print(f"Processing {len(json_files)} JSON files...")
        
        processed = 0
        for json_file in json_files:
            try:
                self._process_json_file(json_file)
                processed += 1
                if processed % 100 == 0:
                    print(f"Processed {processed} files...")
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        
        print(f"Successfully processed {processed} files")
        self._finalize_indexes()
        return self.indexes
    
    def _process_json_file(self, json_file: Path):
        """Process a single JSON file and update indexes."""
        with open(json_file, 'r', encoding='utf-8') as f:
            class_info = json.load(f)
        
        class_name = class_info.get('name', '')
        qualified_name = class_info.get('qualified_name', '')
        package_name = class_info.get('package', '')
        class_type = class_info.get('type', 'unknown')
        
        if not class_name:
            return
        
        # Index class by name and qualified name
        self.indexes['classes_by_name'][class_name] = class_info
        if qualified_name:
            self.indexes['classes_by_qualified_name'][qualified_name] = class_info
        
        # Index by package
        if package_name:
            self.indexes['packages'][package_name].append(class_name)
        
        # Index by type
        self.indexes['classes_by_type'][class_type].append(class_name)
        
        # Index inheritance
        inheritance = class_info.get('inheritance', {})
        if inheritance:
            self.indexes['inheritance_tree'][class_name] = inheritance
        
        # Index nested classes
        nested_classes = class_info.get('nested_classes', [])
        if nested_classes:
            self.indexes['nested_classes'][class_name] = nested_classes
        
        # Index methods
        methods = class_info.get('methods', [])
        for method in methods:
            method_name = method.get('name', '')
            if method_name:
                if method_name not in self.indexes['methods_by_class'][class_name]:
                    self.indexes['methods_by_class'][class_name][method_name] = []
                self.indexes['methods_by_class'][class_name][method_name].append(method)
                self.indexes['all_method_names'].add(method_name)
        
        # Index fields
        fields = class_info.get('fields', [])
        for field in fields:
            field_name = field.get('name', '')
            if field_name:
                self.indexes['fields_by_class'][class_name][field_name] = field
                self.indexes['all_field_names'].add(field_name)
        
        # Index constructors
        constructors = class_info.get('constructors', [])
        self.indexes['constructors_by_class'][class_name] = constructors
        
        # Index enum constants
        enum_constants = class_info.get('enum_constants', [])
        for constant in enum_constants:
            constant_name = constant.get('name', '')
            if constant_name:
                self.indexes['enum_constants_by_class'][class_name][constant_name] = constant
    
    def _finalize_indexes(self):
        """Finalize indexes by converting sets to lists and defaultdicts to regular dicts."""
        # Convert sets to sorted lists
        self.indexes['all_method_names'] = sorted(list(self.indexes['all_method_names']))
        self.indexes['all_field_names'] = sorted(list(self.indexes['all_field_names']))
        
        # Convert defaultdicts to regular dicts
        self.indexes['methods_by_class'] = dict(self.indexes['methods_by_class'])
        self.indexes['fields_by_class'] = dict(self.indexes['fields_by_class'])
        self.indexes['constructors_by_class'] = dict(self.indexes['constructors_by_class'])
        self.indexes['packages'] = dict(self.indexes['packages'])
        self.indexes['enum_constants_by_class'] = dict(self.indexes['enum_constants_by_class'])
        self.indexes['nested_classes'] = dict(self.indexes['nested_classes'])
        self.indexes['classes_by_type'] = dict(self.indexes['classes_by_type'])
        
        # Sort package contents
        for package, classes in self.indexes['packages'].items():
            self.indexes['packages'][package] = sorted(list(set(classes)))
    
    def save_indexes(self, output_file: str):
        """Save indexes to a pickle file."""
        with open(output_file, 'wb') as f:
            pickle.dump(self.indexes, f)
        print(f"Indexes saved to {output_file}")
    
    def print_stats(self):
        """Print statistics about the indexes."""
        print("\n=== Index Statistics ===")
        print(f"Total classes: {len(self.indexes['classes_by_name'])}")
        print(f"Total packages: {len(self.indexes['packages'])}")
        print(f"Total unique method names: {len(self.indexes['all_method_names'])}")
        print(f"Total unique field names: {len(self.indexes['all_field_names'])}")
        
        type_counts = {t: len(classes) for t, classes in self.indexes['classes_by_type'].items()}
        print(f"Classes by type: {type_counts}")
        
        total_methods = sum(
            sum(len(methods) for methods in class_methods.values())
            for class_methods in self.indexes['methods_by_class'].values()
        )
        print(f"Total methods: {total_methods}")
        
        total_fields = sum(len(fields) for fields in self.indexes['fields_by_class'].values())
        print(f"Total fields: {total_fields}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Java API search indexes from JSON files")
    parser.add_argument('json_dir', help='Directory containing JSON files')
    parser.add_argument('-o', '--output', default='java_api_indexes.pkl', 
                       help='Output file for indexes (default: java_api_indexes.pkl)')
    
    args = parser.parse_args()
    
    builder = JavaAPIIndexBuilder()
    try:
        indexes = builder.build_indexes(args.json_dir)
        builder.print_stats()
        builder.save_indexes(args.output)
        print(f"\nIndexes successfully built and saved to {args.output}")
    except Exception as e:
        print(f"Error building indexes: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())