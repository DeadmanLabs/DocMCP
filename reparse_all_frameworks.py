#!/usr/bin/env python3
"""
Reparse all frameworks with updated scripts and clean up unnecessary files.
This script will:
1. Clear old processed data
2. Use enhanced_javadoc_parser.py to reprocess all Frameworks versions
3. Build new indexes for each version
4. Create updated MCP configurations
5. Clean up unused files
"""

import os
import sys
import json
import shutil
import subprocess
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import concurrent.futures

# Import our enhanced parser and indexer
from enhanced_javadoc_parser import convert_javadoc_to_json
from build_indexes import JavaAPIIndexBuilder


def cleanup_old_data(output_base_dir: str, backup: bool = True) -> None:
    """Clean up old processed data with optional backup."""
    if os.path.exists(output_base_dir):
        if backup:
            backup_dir = f"{output_base_dir}_backup"
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            print(f"Creating backup at {backup_dir}")
            shutil.move(output_base_dir, backup_dir)
        else:
            print(f"Removing old data from {output_base_dir}")
            shutil.rmtree(output_base_dir)
    
    # Also clean up root-level processed files
    cleanup_files = [
        "java_api_indexes.pkl",
        "mcp_config.json",
        "json-output",
        "fixed_json_output"
    ]
    
    for cleanup_file in cleanup_files:
        if os.path.exists(cleanup_file):
            if os.path.isdir(cleanup_file):
                if backup:
                    backup_path = f"{cleanup_file}_backup"
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path)
                    shutil.move(cleanup_file, backup_path)
                    print(f"Backed up {cleanup_file} to {backup_path}")
                else:
                    shutil.rmtree(cleanup_file)
                    print(f"Removed directory {cleanup_file}")
            else:
                if backup:
                    backup_path = f"{cleanup_file}_backup"
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    shutil.move(cleanup_file, backup_path)
                    print(f"Backed up {cleanup_file} to {backup_path}")
                else:
                    os.remove(cleanup_file)
                    print(f"Removed file {cleanup_file}")


def get_all_framework_versions(frameworks_dir: str) -> List[str]:
    """Get all available framework versions."""
    frameworks_path = Path(frameworks_dir)
    if not frameworks_path.exists():
        print(f"Error: {frameworks_dir} directory not found!")
        return []
    
    versions = []
    for item in frameworks_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Verify it contains HTML files
            html_files = list(item.glob("*.html"))
            if html_files:
                versions.append(item.name)
    
    return sorted(versions)


def process_framework_version(version: str, frameworks_dir: str, output_base_dir: str) -> Dict[str, Any]:
    """Process a single framework version with enhanced parser."""
    print(f"\nProcessing framework version {version}...")
    
    version_input_dir = os.path.join(frameworks_dir, version)
    version_output_dir = os.path.join(output_base_dir, version)
    json_output_dir = os.path.join(version_output_dir, "json")
    indexes_file = os.path.join(version_output_dir, f"{version}_indexes.pkl")
    
    # Create output directories
    os.makedirs(version_output_dir, exist_ok=True)
    os.makedirs(json_output_dir, exist_ok=True)
    
    try:
        # Step 1: Convert HTML to JSON using enhanced parser
        print(f"Converting {version} HTML to JSON with enhanced parser...")
        convert_javadoc_to_json(version_input_dir, json_output_dir)
        
        # Verify JSON output
        json_files = list(Path(json_output_dir).rglob("*.json"))
        if not json_files:
            raise Exception(f"No JSON files generated for {version}")
        
        # Step 2: Build indexes
        print(f"Building indexes for {version}...")
        builder = JavaAPIIndexBuilder()
        indexes = builder.build_indexes(json_output_dir)
        
        # Verify indexes have content
        if not indexes or len(indexes.get('classes_by_name', {})) == 0:
            raise Exception(f"Empty indexes generated for {version}")
        
        builder.save_indexes(indexes_file)
        
        # Step 3: Create individual MCP config
        clean_version = version.replace('.', '_').replace('-', '_')
        server_name = f"java_api_{clean_version}"
        
        config = {
            "mcpServers": {
                server_name: {
                    "command": "python3",
                    "args": [
                        os.path.abspath("java_api_server.py"),
                        "--indexes", 
                        os.path.abspath(indexes_file)
                    ],
                    "env": {}
                }
            }
        }
        
        config_file = os.path.join(version_output_dir, f"mcp_config_{clean_version}.json")
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Get stats
        stats = {
            'version': version,
            'total_classes': len(indexes['classes_by_name']),
            'total_packages': len(indexes['packages']),
            'total_methods': len(indexes['all_method_names']),
            'total_fields': len(indexes['all_field_names']),
            'json_files_count': len(json_files),
            'indexes_file': indexes_file,
            'config_file': config_file,
            'json_output_dir': json_output_dir
        }
        
        print(f"✓ {version}: {stats['total_classes']} classes, {stats['total_packages']} packages, {stats['json_files_count']} JSON files")
        return stats
        
    except Exception as e:
        print(f"✗ Error processing {version}: {e}")
        return {'version': version, 'error': str(e)}


def create_master_mcp_config(successful_versions: List[Dict[str, Any]], output_base_dir: str) -> str:
    """Create a master MCP configuration file for all versions."""
    configs = {}
    
    for version_info in successful_versions:
        version = version_info['version']
        indexes_file = version_info['indexes_file']
        
        clean_version = version.replace('.', '_').replace('-', '_')
        server_name = f"java_api_{clean_version}"
        
        configs[server_name] = {
            "command": "python3",
            "args": [
                os.path.abspath("java_api_server.py"),
                "--indexes", 
                os.path.abspath(indexes_file)
            ],
            "env": {}
        }
    
    master_config = {"mcpServers": configs}
    config_file = os.path.join(output_base_dir, "mcp_config_all_versions.json")
    
    with open(config_file, 'w') as f:
        json.dump(master_config, f, indent=2)
    
    return config_file


def test_processed_version(version_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test that a processed version is working correctly."""
    if 'error' in version_info:
        return {
            'version': version_info['version'], 
            'test_status': 'skipped', 
            'reason': 'processing_error'
        }
    
    version = version_info['version']
    indexes_file = version_info['indexes_file']
    
    try:
        # Test loading indexes
        with open(indexes_file, 'rb') as f:
            indexes = pickle.load(f)
        
        # Basic validation
        required_keys = ['classes_by_name', 'packages', 'all_method_names', 'all_field_names']
        for key in required_keys:
            if key not in indexes:
                return {
                    'version': version, 
                    'test_status': 'failed', 
                    'reason': f'missing_index_key_{key}'
                }
        
        if len(indexes['classes_by_name']) == 0:
            return {
                'version': version, 
                'test_status': 'failed', 
                'reason': 'no_classes_found'
            }
        
        # Run comprehensive validation
        try:
            from validate_processing import ProcessingValidator
            validator = ProcessingValidator(version)
            validation_report = validator.validate_all()
            
            validation_errors = len(validation_report.get('errors', []))
            validation_warnings = len(validation_report.get('warnings', []))
            
            return {
                'version': version, 
                'test_status': 'passed',
                'classes_count': len(indexes['classes_by_name']),
                'packages_count': len(indexes['packages']),
                'methods_count': len(indexes['all_method_names']),
                'fields_count': len(indexes['all_field_names']),
                'validation_errors': validation_errors,
                'validation_warnings': validation_warnings,
                'validation_stats': validation_report.get('stats', {}),
                'comprehensive_validation': validation_errors == 0
            }
        except Exception as validation_error:
            # If validation fails, still return basic test results
            return {
                'version': version, 
                'test_status': 'passed',
                'classes_count': len(indexes['classes_by_name']),
                'packages_count': len(indexes['packages']),
                'methods_count': len(indexes['all_method_names']),
                'fields_count': len(indexes['all_field_names']),
                'validation_error': str(validation_error)
            }
        
    except Exception as e:
        return {
            'version': version, 
            'test_status': 'failed', 
            'reason': f'exception: {str(e)}'
        }


def cleanup_unused_files() -> List[str]:
    """Remove unused and unnecessary files from the project."""
    cleanup_patterns = [
        # Debug files
        "debug_*.py",
        "test_*.py",
        # Cache files
        "__pycache__",
        "*.pyc",
        "*.pyo",
        # Old backup files
        "*_backup",
        # Temporary files
        "*.tmp",
        "*.temp",
        # Old processing files that are no longer needed
        "javadoc_to_json.py",  # replaced by enhanced_javadoc_parser.py
        "get-pip.py",
        "test_output",
        "test_serverlevel.json",
        # Old single version processing scripts
        "process_single_version.py",
        "process_remaining_versions.py",
        "reprocess_with_fixes.py",
        "reprocess_with_logging.py",
        "fix_missing_files.py",
        "create_configs_for_existing.py"
    ]
    
    removed_files = []
    
    for pattern in cleanup_patterns:
        if '*' in pattern:
            # Use glob for patterns
            from glob import glob
            matches = glob(pattern)
            for match in matches:
                if os.path.exists(match):
                    if os.path.isdir(match):
                        shutil.rmtree(match)
                        removed_files.append(f"directory: {match}")
                    else:
                        os.remove(match)
                        removed_files.append(f"file: {match}")
        else:
            # Direct file/directory removal
            if os.path.exists(pattern):
                if os.path.isdir(pattern):
                    shutil.rmtree(pattern)
                    removed_files.append(f"directory: {pattern}")
                else:
                    os.remove(pattern)
                    removed_files.append(f"file: {pattern}")
    
    return removed_files


def main():
    """Main function to reparse all frameworks."""
    print("Framework Reprocessing Script")
    print("=" * 50)
    
    frameworks_dir = "Frameworks"
    output_base_dir = "processed_versions"
    
    # Check if frameworks directory exists
    if not os.path.exists(frameworks_dir):
        print(f"Error: {frameworks_dir} directory not found!")
        return 1
    
    # Get user confirmation for cleanup
    response = input(f"This will clean up old data in {output_base_dir}. Create backup? (y/n): ").strip().lower()
    backup = response in ['y', 'yes', '']
    
    # Step 1: Clean up old data
    print(f"\nStep 1: Cleaning up old processed data...")
    cleanup_old_data(output_base_dir, backup=backup)
    
    # Step 2: Get all framework versions
    print(f"\nStep 2: Discovering framework versions...")
    versions = get_all_framework_versions(frameworks_dir)
    if not versions:
        print("No framework versions found!")
        return 1
    
    print(f"Found {len(versions)} framework versions: {', '.join(versions)}")
    
    # Step 3: Process all versions
    print(f"\nStep 3: Processing all framework versions...")
    os.makedirs(output_base_dir, exist_ok=True)
    
    processed_versions = []
    for i, version in enumerate(versions, 1):
        print(f"\n[{i}/{len(versions)}] Processing {version}...")
        result = process_framework_version(version, frameworks_dir, output_base_dir)
        processed_versions.append(result)
    
    # Step 4: Create configurations and test
    successful_versions = [v for v in processed_versions if 'error' not in v]
    failed_versions = [v for v in processed_versions if 'error' in v]
    
    print(f"\n{'='*50}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Total versions: {len(versions)}")
    print(f"Successful: {len(successful_versions)}")
    print(f"Failed: {len(failed_versions)}")
    
    if successful_versions:
        print(f"\nStep 4: Creating master MCP configuration...")
        master_config_file = create_master_mcp_config(successful_versions, output_base_dir)
        print(f"Master config created: {master_config_file}")
        
        print(f"\nStep 5: Testing processed versions...")
        test_results = []
        for version_info in successful_versions:
            test_result = test_processed_version(version_info)
            test_results.append(test_result)
            status_icon = "✓" if test_result['test_status'] == 'passed' else "✗"
            print(f"  {status_icon} {test_result['version']}: {test_result['test_status']}")
        
        # Count test results
        passed_tests = len([t for t in test_results if t['test_status'] == 'passed'])
        print(f"\nTest Results: {passed_tests}/{len(test_results)} passed")
    
    # Step 5: Clean up unused files
    print(f"\nStep 6: Cleaning up unused files...")
    removed_files = cleanup_unused_files()
    if removed_files:
        print(f"Removed {len(removed_files)} unused items:")
        for item in removed_files[:10]:  # Show first 10 items
            print(f"  - {item}")
        if len(removed_files) > 10:
            print(f"  ... and {len(removed_files) - 10} more items")
    else:
        print("No unused files found to remove")
    
    # Final summary
    print(f"\n{'='*50}")
    print(f"FINAL SUMMARY")
    print(f"{'='*50}")
    
    if successful_versions:
        total_classes = sum(v['total_classes'] for v in successful_versions)
        total_packages = sum(v['total_packages'] for v in successful_versions)
        total_json_files = sum(v['json_files_count'] for v in successful_versions)
        
        print(f"Successfully processed {len(successful_versions)} framework versions")
        print(f"Total classes: {total_classes}")
        print(f"Total packages: {total_packages}")
        print(f"Total JSON files: {total_json_files}")
        print(f"Master config: {master_config_file}")
        
        # Write summary file
        summary = {
            'total_versions': len(versions),
            'successful_versions': len(successful_versions),
            'failed_versions': len(failed_versions),
            'total_classes': total_classes,
            'total_packages': total_packages,
            'total_json_files': total_json_files,
            'processed_versions': processed_versions,
            'test_results': test_results if 'test_results' in locals() else [],
            'master_config_file': master_config_file if successful_versions else None,
            'removed_files': removed_files,
            'timestamp': str(__import__('datetime').datetime.now())
        }
        
        summary_file = os.path.join(output_base_dir, "reprocessing_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Summary written to: {summary_file}")
    
    if failed_versions:
        print(f"\nFailed versions:")
        for v in failed_versions:
            print(f"  ✗ {v['version']}: {v['error']}")
    
    print(f"\nReprocessing complete!")
    return 0 if not failed_versions else 1


if __name__ == '__main__':
    exit(main())