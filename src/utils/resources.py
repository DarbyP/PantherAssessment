"""
Resource path utilities for bundled and user data
"""
import sys
import os
import shutil
from pathlib import Path


def get_bundled_resource_path(relative_path):
    """Get absolute path to bundled resource in .app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as bundled app
        return Path(sys._MEIPASS) / relative_path
    # Running as script
    return Path(__file__).parent.parent.parent / relative_path


def get_user_data_dir():
    """Get user data directory for PantherAssess"""
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform == 'win32':
        base = Path(os.getenv('APPDATA'))
    else:
        base = Path.home() / '.config'
    
    user_dir = base / 'PantherAssess'
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_templates_dir():
    """Get user templates directory, initialize with bundled templates if empty"""
    user_dir = get_user_data_dir() / 'templates'
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # If user templates folder is empty, copy defaults from bundled
    if not any(user_dir.glob('*.json')):
        bundled_templates = get_bundled_resource_path('templates')
        if bundled_templates.exists():
            for template_file in bundled_templates.glob('*.json'):
                shutil.copy(template_file, user_dir)
    
    return user_dir
