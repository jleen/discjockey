import os
import sys

from pathlib import Path

from . import config

def catalog():
    create_catalog(config.music_path, config.catalog_path, sys.argv[1])

def create_catalog(music, catalog, album):
    # Build full source directory path
    src_dir = Path(music) / album
    
    # Check if source directory exists
    if not src_dir.exists():
        print(f'Error: Source directory {src_dir} does not exist')
        return False
    
    if not src_dir.is_dir():
        print(f'Error: {src_dir} is not a directory')
        return False
    
    # Find all .flac files (non-recursive)
    flac_files = []
    for file in src_dir.iterdir():
        if file.is_file() and file.suffix.lower() == '.flac':
            flac_files.append(file.stem)
    
    flac_files.sort()
    
    if not Path(catalog).exists():
        print(f'Error: Destination base directory {catalog} does not exist')
        return False
    
    dest_file = Path(catalog) / album
    
    if dest_file.exists():
        print(f'Error: Destination file {dest_file} already exists')
        return False
    
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(dest_file, 'w', encoding='utf-8') as f:
            for flac_file in flac_files:
                f.write(f'{flac_file}\n')
    except Exception as e:
        print(f'Error writing to {dest_file}: {e}')
