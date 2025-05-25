#!/usr/bin/env python3
"""
Comprehensive validation script for DocMCP processing.
Validates that all classes have corresponding JSON files and that directory structures match.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


class ProcessingValidator:
    """Validates DocMCP processing completeness and correctness."""
    
    def __init__(self, version: str):
        self.version = version
        self.html_dir = Path(f"Frameworks/{version}")
        self.json_dir = Path(f"processed_versions/{version}/json")
        self.indexes_file = Path(f"processed_versions/{version}/{version}_indexes.pkl")
        
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_html_files': 0,
            'total_json_files': 0,
            'missing_json_files': 0,
            'extra_json_files': 0,
            'missing_from_indexes': 0,
            'directory_mismatches': 0,
            'namespaces': defaultdict(int)
        }
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        print(f"Validating processing for {self.version}")
        print("=" * 50)
        
        # Check if required directories exist
        if not self.html_dir.exists():
            self.errors.append(f"HTML source directory not found: {self.html_dir}")
            return self._get_validation_report()
        
        if not self.json_dir.exists():
            self.errors.append(f"JSON output directory not found: {self.json_dir}")
            return self._get_validation_report()
        
        if not self.indexes_file.exists():
            self.errors.append(f"Indexes file not found: {self.indexes_file}")
            return self._get_validation_report()
        
        # Run validation checks
        self._validate_html_to_json_mapping()
        self._validate_directory_structure()
        self._validate_indexes()
        self._validate_namespaces()
        self._analyze_missing_files()
        
        return self._get_validation_report()
    
    def _get_class_html_files(self) -> List[Path]:
        """Get list of HTML files that should represent classes."""
        html_files = []
        
        # Skip patterns for non-class files
        skip_patterns = [
            'package-summary.html',
            'package-tree.html', 
            'package-use.html',
            'package-frame.html',
            'overview-',
            'constant-values.html',
            'deprecated-list.html',
            'serialized-form.html',
            'help-doc.html',
            'index-',
            'index.html',  # Root index file
            'search.html',
            'allclasses',
            'allpackages',
            'element-list'
        ]
        
        for html_file in self.html_dir.glob('**/*.html'):
            # Skip files in class-use, legal, script-dir, resources directories
            if any(part in ['class-use', 'legal', 'script-dir', 'resources'] for part in html_file.parts):
                continue
            
            # Skip based on filename patterns
            if any(pattern in html_file.name for pattern in skip_patterns):
                continue
            
            # Skip files that don't end with .html
            if not html_file.suffix == '.html':
                continue
            
            html_files.append(html_file)
        
        return html_files
    
    def _validate_html_to_json_mapping(self):
        """Validate that every class HTML file has a corresponding JSON file."""
        print("1. Validating HTML to JSON mapping...")
        
        html_files = self._get_class_html_files()
        self.stats['total_html_files'] = len(html_files)
        
        missing_json = []
        extra_json = []
        
        # Check for missing JSON files
        for html_file in html_files:
            relative_path = html_file.relative_to(self.html_dir)
            expected_json = self.json_dir / relative_path.with_suffix('.json')
            
            if not expected_json.exists():
                missing_json.append(str(relative_path))
        
        # Check for extra JSON files
        json_files = list(self.json_dir.glob('**/*.json'))
        self.stats['total_json_files'] = len(json_files)
        
        for json_file in json_files:
            relative_path = json_file.relative_to(self.json_dir)
            expected_html = self.html_dir / relative_path.with_suffix('.html')
            
            if not expected_html.exists():
                extra_json.append(str(relative_path))
        
        self.stats['missing_json_files'] = len(missing_json)
        self.stats['extra_json_files'] = len(extra_json)
        
        if missing_json:
            self.errors.append(f"Missing JSON files for {len(missing_json)} HTML files")
            if len(missing_json) <= 10:
                for missing in missing_json:
                    self.errors.append(f"  Missing: {missing}")
            else:
                for missing in missing_json[:5]:
                    self.errors.append(f"  Missing: {missing}")
                self.errors.append(f"  ... and {len(missing_json) - 5} more")
        
        if extra_json:
            self.warnings.append(f"Extra JSON files found: {len(extra_json)}")
        
        print(f"   HTML files: {self.stats['total_html_files']}")
        print(f"   JSON files: {self.stats['total_json_files']}")
        print(f"   Missing JSON: {self.stats['missing_json_files']}")
    
    def _validate_directory_structure(self):
        """Validate that directory structures match between HTML and JSON."""
        print("2. Validating directory structure...")
        
        # Get all directories in HTML and JSON
        html_dirs = set()
        json_dirs = set()
        
        for html_file in self.html_dir.glob('**/*.html'):
            if html_file.is_file():
                relative_dir = html_file.parent.relative_to(self.html_dir)
                if str(relative_dir) != '.':
                    html_dirs.add(str(relative_dir))
        
        for json_file in self.json_dir.glob('**/*.json'):
            if json_file.is_file():
                relative_dir = json_file.parent.relative_to(self.json_dir)
                if str(relative_dir) != '.':
                    json_dirs.add(str(relative_dir))
        
        missing_dirs = html_dirs - json_dirs
        extra_dirs = json_dirs - html_dirs
        
        self.stats['directory_mismatches'] = len(missing_dirs) + len(extra_dirs)
        
        if missing_dirs:
            self.warnings.append(f"Missing directories in JSON: {len(missing_dirs)}")
            for missing_dir in sorted(missing_dirs)[:5]:
                self.warnings.append(f"  Missing dir: {missing_dir}")
        
        if extra_dirs:
            self.warnings.append(f"Extra directories in JSON: {len(extra_dirs)}")
            for extra_dir in sorted(extra_dirs)[:5]:
                self.warnings.append(f"  Extra dir: {extra_dir}")
        
        print(f"   Directory structure matches: {len(missing_dirs) == 0 and len(extra_dirs) == 0}")
    
    def _validate_indexes(self):
        """Validate that indexes contain all expected classes."""
        print("3. Validating indexes...")
        
        try:
            with open(self.indexes_file, 'rb') as f:
                indexes = pickle.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load indexes: {e}")
            return
        
        indexed_classes = set(indexes.get('classes_by_name', {}).keys())
        qualified_classes = set(indexes.get('classes_by_qualified_name', {}).keys())
        
        # Check JSON files against indexes
        missing_from_indexes = []
        
        for json_file in self.json_dir.glob('**/*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    class_info = json.load(f)
                
                qualified_name = class_info.get('qualified_name', '')
                class_name = class_info.get('name', '')
                
                # Check if class is in indexes (prefer qualified name)
                if qualified_name:
                    if qualified_name not in qualified_classes and qualified_name not in indexed_classes:
                        missing_from_indexes.append(qualified_name)
                elif class_name and class_name not in indexed_classes:
                    missing_from_indexes.append(class_name)
                    
            except Exception as e:
                self.errors.append(f"Failed to read JSON file {json_file}: {e}")
        
        self.stats['missing_from_indexes'] = len(missing_from_indexes)
        
        if missing_from_indexes:
            self.errors.append(f"Classes missing from indexes: {len(missing_from_indexes)}")
            for missing in missing_from_indexes[:5]:
                self.errors.append(f"  Missing from index: {missing}")
        
        print(f"   Indexed classes: {len(indexed_classes)}")
        print(f"   Missing from indexes: {len(missing_from_indexes)}")
    
    def _validate_namespaces(self):
        """Validate namespace coverage."""
        print("4. Validating namespaces...")
        
        namespace_stats = defaultdict(int)
        
        for json_file in self.json_dir.glob('**/*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    class_info = json.load(f)
                
                package = class_info.get('package', '')
                if package:
                    root_namespace = package.split('.')[0]
                    namespace_stats[root_namespace] += 1
                else:
                    namespace_stats['<no_package>'] += 1
                    
            except Exception as e:
                self.warnings.append(f"Failed to read JSON for namespace analysis: {json_file}")
        
        self.stats['namespaces'] = dict(namespace_stats)
        
        print("   Namespace distribution:")
        for namespace, count in sorted(namespace_stats.items()):
            print(f"     {namespace}: {count} classes")
        
        # Check for expected namespaces
        expected_namespaces = ['net', 'com', 'mcp']
        missing_namespaces = []
        
        for ns in expected_namespaces:
            if ns not in namespace_stats:
                missing_namespaces.append(ns)
        
        if missing_namespaces:
            self.warnings.append(f"Missing expected namespaces: {missing_namespaces}")
    
    def _analyze_missing_files(self):
        """Analyze patterns in missing files."""
        print("5. Analyzing missing file patterns...")
        
        html_files = self._get_class_html_files()
        missing_by_namespace = defaultdict(int)
        missing_by_depth = defaultdict(int)
        
        for html_file in html_files:
            relative_path = html_file.relative_to(self.html_dir)
            expected_json = self.json_dir / relative_path.with_suffix('.json')
            
            if not expected_json.exists():
                # Analyze by namespace
                parts = relative_path.parts
                if len(parts) > 0:
                    root_namespace = parts[0]
                    missing_by_namespace[root_namespace] += 1
                
                # Analyze by directory depth
                depth = len(parts) - 1  # -1 for the file itself
                missing_by_depth[depth] += 1
        
        if missing_by_namespace:
            print("   Missing files by namespace:")
            for namespace, count in sorted(missing_by_namespace.items()):
                print(f"     {namespace}: {count} missing")
        
        if missing_by_depth:
            print("   Missing files by directory depth:")
            for depth, count in sorted(missing_by_depth.items()):
                print(f"     Depth {depth}: {count} missing")
    
    def _get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report."""
        return {
            'version': self.version,
            'stats': dict(self.stats),
            'errors': self.errors,
            'warnings': self.warnings,
            'success': len(self.errors) == 0
        }


def main():
    """Main validation function."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 validate_processing.py <version>")
        print("Example: python3 validate_processing.py 1.21.x-neoforge")
        return 1
    
    version = sys.argv[1]
    validator = ProcessingValidator(version)
    report = validator.validate_all()
    
    print(f"\n{'='*50}")
    print("VALIDATION SUMMARY")
    print(f"{'='*50}")
    
    if report['success']:
        print("✓ All validations passed!")
    else:
        print(f"✗ Found {len(report['errors'])} errors")
    
    if report['warnings']:
        print(f"⚠ Found {len(report['warnings'])} warnings")
    
    print(f"\nStatistics:")
    for key, value in report['stats'].items():
        if key == 'namespaces':
            print(f"  {key}:")
            for ns, count in value.items():
                print(f"    {ns}: {count}")
        else:
            print(f"  {key}: {value}")
    
    if report['errors']:
        print(f"\nErrors:")
        for error in report['errors']:
            print(f"  ✗ {error}")
    
    if report['warnings']:
        print(f"\nWarnings:")
        for warning in report['warnings']:
            print(f"  ⚠ {warning}")
    
    return 0 if report['success'] else 1


if __name__ == '__main__':
    exit(main())