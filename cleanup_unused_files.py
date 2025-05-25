#!/usr/bin/env python3
"""
Clean up unused and unnecessary files from the DocMCP project.
This script identifies and removes debug files, test files, cache files, 
and other temporary/unused items to keep the project clean.
"""

import os
import shutil
import glob
from pathlib import Path
from typing import List, Dict


def get_unused_files() -> Dict[str, List[str]]:
    """Identify unused files by category."""
    unused_files = {
        'debug_files': [],
        'test_files': [],
        'cache_files': [],
        'backup_files': [],
        'temp_files': [],
        'old_scripts': [],
        'misc_files': []
    }
    
    # Debug files
    debug_patterns = [
        "debug_*.py",
        "*debug*.py"
    ]
    
    for pattern in debug_patterns:
        matches = glob.glob(pattern)
        unused_files['debug_files'].extend(matches)
    
    # Test files (keep essential ones, remove development test files)
    test_patterns = [
        "test_*.py"
    ]
    
    for pattern in test_patterns:
        matches = glob.glob(pattern)
        unused_files['test_files'].extend(matches)
    
    # Cache and compiled files
    cache_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache"
    ]
    
    for pattern in cache_patterns:
        matches = glob.glob(pattern, recursive=True)
        unused_files['cache_files'].extend(matches)
    
    # Backup files
    backup_patterns = [
        "*_backup",
        "*_backup.*",
        "*.bak",
        "*.orig"
    ]
    
    for pattern in backup_patterns:
        matches = glob.glob(pattern)
        unused_files['backup_files'].extend(matches)
    
    # Temporary files
    temp_patterns = [
        "*.tmp",
        "*.temp",
        ".DS_Store",
        "Thumbs.db"
    ]
    
    for pattern in temp_patterns:
        matches = glob.glob(pattern)
        unused_files['temp_files'].extend(matches)
    
    # Old scripts that have been replaced
    old_scripts = [
        "javadoc_to_json.py",  # replaced by enhanced_javadoc_parser.py
        "get-pip.py",          # no longer needed
        "process_single_version.py",  # replaced by reparse_all_frameworks.py
        "process_remaining_versions.py",  # replaced by reparse_all_frameworks.py
        "reprocess_with_fixes.py",  # replaced by reparse_all_frameworks.py
        "reprocess_with_logging.py",  # replaced by reparse_all_frameworks.py
        "fix_missing_files.py",  # no longer needed
        "create_configs_for_existing.py"  # functionality moved to reparse_all_frameworks.py
    ]
    
    for script in old_scripts:
        if os.path.exists(script):
            unused_files['old_scripts'].append(script)
    
    # Miscellaneous files/directories
    misc_items = [
        "test_output",
        "test_serverlevel.json"
    ]
    
    for item in misc_items:
        if os.path.exists(item):
            unused_files['misc_files'].append(item)
    
    return unused_files


def analyze_disk_usage() -> Dict[str, int]:
    """Analyze disk usage of different file types."""
    usage = {
        'total_size': 0,
        'frameworks_size': 0,
        'processed_size': 0,
        'cache_size': 0
    }
    
    # Total project size
    def get_dir_size(path):
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except (OSError, FileNotFoundError):
            pass
        return total
    
    usage['total_size'] = get_dir_size('.')
    
    # Frameworks directory
    if os.path.exists('Frameworks'):
        usage['frameworks_size'] = get_dir_size('Frameworks')
    
    # Processed versions
    if os.path.exists('processed_versions'):
        usage['processed_size'] = get_dir_size('processed_versions')
    
    # Cache files
    if os.path.exists('__pycache__'):
        usage['cache_size'] = get_dir_size('__pycache__')
    
    return usage


def format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def remove_files(file_list: List[str], dry_run: bool = True) -> List[str]:
    """Remove files and directories. Returns list of removed items."""
    removed = []
    
    for item in file_list:
        if not os.path.exists(item):
            continue
            
        try:
            if dry_run:
                if os.path.isdir(item):
                    removed.append(f"[DRY RUN] Would remove directory: {item}")
                else:
                    size = os.path.getsize(item)
                    removed.append(f"[DRY RUN] Would remove file: {item} ({format_size(size)})")
            else:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    removed.append(f"Removed directory: {item}")
                else:
                    size = os.path.getsize(item)
                    os.remove(item)
                    removed.append(f"Removed file: {item} ({format_size(size)})")
        except Exception as e:
            removed.append(f"Error removing {item}: {e}")
    
    return removed


def main():
    """Main cleanup function."""
    print("DocMCP Project Cleanup Tool")
    print("=" * 50)
    
    # Analyze current disk usage
    print("\n1. Analyzing current disk usage...")
    usage = analyze_disk_usage()
    print(f"Total project size: {format_size(usage['total_size'])}")
    print(f"Frameworks directory: {format_size(usage['frameworks_size'])}")
    print(f"Processed versions: {format_size(usage['processed_size'])}")
    print(f"Cache files: {format_size(usage['cache_size'])}")
    
    # Identify unused files
    print("\n2. Identifying unused files...")
    unused_files = get_unused_files()
    
    total_unused = sum(len(files) for files in unused_files.values())
    print(f"Found {total_unused} unused items:")
    
    for category, files in unused_files.items():
        if files:
            print(f"\n{category.replace('_', ' ').title()}:")
            for file in files:
                if os.path.exists(file):
                    if os.path.isdir(file):
                        print(f"  📁 {file}/")
                    else:
                        size = os.path.getsize(file)
                        print(f"  📄 {file} ({format_size(size)})")
    
    if total_unused == 0:
        print("No unused files found!")
        return 0
    
    # Ask user what to do
    print(f"\n3. Cleanup options:")
    print("1. Dry run (show what would be removed)")
    print("2. Remove cache files only")
    print("3. Remove all unused files")
    print("4. Cancel")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        # Dry run
        print("\nDry run - showing what would be removed:")
        all_files = []
        for files in unused_files.values():
            all_files.extend(files)
        
        removed = remove_files(all_files, dry_run=True)
        for item in removed:
            print(f"  {item}")
        
    elif choice == "2":
        # Remove cache files only
        print("\nRemoving cache files...")
        removed = remove_files(unused_files['cache_files'], dry_run=False)
        for item in removed:
            print(f"  {item}")
        print(f"\nRemoved {len(removed)} cache items")
        
    elif choice == "3":
        # Remove all unused files
        confirm = input("Are you sure you want to remove ALL unused files? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            print("\nRemoving all unused files...")
            all_removed = []
            
            for category, files in unused_files.items():
                if files:
                    print(f"\nRemoving {category}...")
                    removed = remove_files(files, dry_run=False)
                    all_removed.extend(removed)
                    for item in removed:
                        print(f"  {item}")
            
            print(f"\nTotal items removed: {len(all_removed)}")
            
            # Show new disk usage
            new_usage = analyze_disk_usage()
            saved_space = usage['total_size'] - new_usage['total_size']
            print(f"Disk space saved: {format_size(saved_space)}")
        else:
            print("Cleanup cancelled")
            
    elif choice == "4":
        print("Cleanup cancelled")
        
    else:
        print("Invalid choice")
        return 1
    
    print("\nCleanup complete!")
    return 0


if __name__ == '__main__':
    exit(main())