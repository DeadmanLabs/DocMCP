#!/usr/bin/env python3
"""
Process all javadoc versions and create indexes for each one.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Any

# Import our enhanced parser and indexer
from enhanced_javadoc_parser import convert_javadoc_to_json
from build_indexes import JavaAPIIndexBuilder


def get_all_versions(frameworks_dir: str) -> List[str]:
    """Get all available javadoc versions."""
    frameworks_path = Path(frameworks_dir)
    versions = []
    
    for item in frameworks_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            versions.append(item.name)
    
    return sorted(versions)


def process_single_version(version: str, frameworks_dir: str, output_base_dir: str) -> Dict[str, Any]:
    """Process a single javadoc version."""
    print(f"Processing version {version}...")
    
    version_input_dir = os.path.join(frameworks_dir, version)
    version_output_dir = os.path.join(output_base_dir, version)
    json_output_dir = os.path.join(version_output_dir, "json")
    indexes_file = os.path.join(version_output_dir, f"{version}_indexes.pkl")
    
    # Create output directories
    os.makedirs(version_output_dir, exist_ok=True)
    
    try:
        # Step 1: Convert HTML to JSON
        print(f"Converting {version} HTML to JSON...")
        convert_javadoc_to_json(version_input_dir, json_output_dir)
        
        # Step 2: Build indexes
        print(f"Building indexes for {version}...")
        builder = JavaAPIIndexBuilder()
        indexes = builder.build_indexes(json_output_dir)
        builder.save_indexes(indexes_file)
        
        # Get stats
        stats = {
            'version': version,
            'total_classes': len(indexes['classes_by_name']),
            'total_packages': len(indexes['packages']),
            'total_methods': len(indexes['all_method_names']),
            'total_fields': len(indexes['all_field_names']),
            'indexes_file': indexes_file
        }
        
        print(f"✓ {version}: {stats['total_classes']} classes, {stats['total_packages']} packages")
        return stats
        
    except Exception as e:
        print(f"✗ Error processing {version}: {e}")
        return {'version': version, 'error': str(e)}


def create_mcp_server_configs(processed_versions: List[Dict[str, Any]], output_base_dir: str):
    """Create MCP server configurations for each version."""
    configs = {}
    
    for version_info in processed_versions:
        if 'error' not in version_info:
            version = version_info['version']
            indexes_file = version_info['indexes_file']
            
            # Clean version name for server name
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
    
    # Write the master config file
    master_config = {"mcpServers": configs}
    config_file = os.path.join(output_base_dir, "mcp_config_all_versions.json")
    
    with open(config_file, 'w') as f:
        json.dump(master_config, f, indent=2)
    
    print(f"\nMCP server configuration written to: {config_file}")
    return config_file


def create_version_specific_configs(processed_versions: List[Dict[str, Any]], output_base_dir: str):
    """Create individual MCP config files for each version."""
    config_files = []
    
    for version_info in processed_versions:
        if 'error' not in version_info:
            version = version_info['version']
            indexes_file = version_info['indexes_file']
            
            # Clean version name for server name
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
            
            config_file = os.path.join(output_base_dir, version, f"mcp_config_{clean_version}.json")
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            config_files.append(config_file)
    
    return config_files


def test_version(version_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single version's MCP server."""
    if 'error' in version_info:
        return {'version': version_info['version'], 'test_status': 'skipped', 'reason': 'processing_error'}
    
    version = version_info['version']
    indexes_file = version_info['indexes_file']
    
    try:
        # Test if we can load the indexes
        builder = JavaAPIIndexBuilder()
        with open(indexes_file, 'rb') as f:
            import pickle
            indexes = pickle.load(f)
        
        # Basic validation
        if not indexes or len(indexes.get('classes_by_name', {})) == 0:
            return {'version': version, 'test_status': 'failed', 'reason': 'empty_indexes'}
        
        return {
            'version': version, 
            'test_status': 'passed',
            'classes_count': len(indexes['classes_by_name'])
        }
        
    except Exception as e:
        return {'version': version, 'test_status': 'failed', 'reason': str(e)}


def main():
    """Main function."""
    frameworks_dir = "Frameworks"
    output_base_dir = "processed_versions"
    
    if not os.path.exists(frameworks_dir):
        print(f"Error: {frameworks_dir} directory not found!")
        return 1
    
    # Get all versions
    versions = get_all_versions(frameworks_dir)
    print(f"Found {len(versions)} versions: {', '.join(versions)}")
    
    # Create output directory
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Process versions sequentially (to avoid overwhelming the system)
    processed_versions = []
    
    for version in versions:
        result = process_single_version(version, frameworks_dir, output_base_dir)
        processed_versions.append(result)
    
    # Create summary
    successful_versions = [v for v in processed_versions if 'error' not in v]
    failed_versions = [v for v in processed_versions if 'error' in v]
    
    print(f"\n{'='*50}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Total versions: {len(versions)}")
    print(f"Successful: {len(successful_versions)}")
    print(f"Failed: {len(failed_versions)}")
    
    if successful_versions:
        print(f"\nSuccessful versions:")
        for v in successful_versions:
            print(f"  ✓ {v['version']}: {v['total_classes']} classes, {v['total_packages']} packages")
    
    if failed_versions:
        print(f"\nFailed versions:")
        for v in failed_versions:
            print(f"  ✗ {v['version']}: {v['error']}")
    
    # Create MCP server configurations
    if successful_versions:
        print(f"\nCreating MCP server configurations...")
        master_config_file = create_mcp_server_configs(successful_versions, output_base_dir)
        individual_configs = create_version_specific_configs(successful_versions, output_base_dir)
        
        print(f"Created {len(individual_configs)} individual config files")
        
        # Test each version
        print(f"\nTesting processed versions...")
        test_results = []
        for version_info in successful_versions:
            test_result = test_version(version_info)
            test_results.append(test_result)
            status_icon = "✓" if test_result['test_status'] == 'passed' else "✗"
            print(f"  {status_icon} {test_result['version']}: {test_result['test_status']}")
        
        # Write summary file
        summary = {
            'total_versions': len(versions),
            'successful_versions': len(successful_versions),
            'failed_versions': len(failed_versions),
            'processed_versions': processed_versions,
            'test_results': test_results,
            'master_config_file': master_config_file,
            'individual_config_files': individual_configs
        }
        
        summary_file = os.path.join(output_base_dir, "processing_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nSummary written to: {summary_file}")
        print(f"Master MCP config: {master_config_file}")
        print(f"\nAll processing complete!")
    
    return 0


if __name__ == '__main__':
    exit(main())