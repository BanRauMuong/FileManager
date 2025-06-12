#!/usr/bin/env python3
"""
Script tự động tạo các file __init__.py cho dự án FileManager
"""

import os
from pathlib import Path

# Định nghĩa nội dung cho từng file __init__.py
init_contents = {
    'core/__init__.py': '''"""
Core module for FileManager
Contains main business logic and file operations
"""

from .file_operations import FileOperations
from .directory_manager import DirectoryManager
from .file_executor import FileExecutor

__all__ = [
    'FileOperations',
    'DirectoryManager', 
    'FileExecutor'
]

__version__ = '1.0.0'
''',
    
    'ui/__init__.py': '''"""
UI module for FileManager
Contains all user interface components and windows
"""

from .main_window import MainWindow
from .file_browser import FileBrowser
from .text_editor import TextEditor

__all__ = [
    'MainWindow',
    'FileBrowser',
    'TextEditor'
]

__version__ = '1.0.0'
''',
    
    'utils/__init__.py': '''"""
Utils module for FileManager
Contains utility functions and helper classes
"""

from .file_utils import FileUtils
from .search_engine import SearchEngine
from .compression import CompressionManager

__all__ = [
    'FileUtils',
    'SearchEngine',
    'CompressionManager'
]

__version__ = '1.0.0'
''',
    
    'config/__init__.py': '''"""
Config module for FileManager
Contains configuration settings and constants
"""

from .settings import Settings

__all__ = [
    'Settings'
]

__version__ = '1.0.0'

# Default configuration constants
DEFAULT_WINDOW_WIDTH = 1024
DEFAULT_WINDOW_HEIGHT = 768
DEFAULT_THEME = 'light'
APP_NAME = 'FileManager'
APP_VERSION = '1.0.0'
''',
    
    '__init__.py': '''"""
FileManager Application
A comprehensive file management tool with GUI interface

Author: Your Name
Version: 1.0.0
License: MIT
"""

from config import APP_NAME, APP_VERSION

__title__ = APP_NAME
__version__ = APP_VERSION
__author__ = 'Your Name'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024'

# Main application modules
from core import FileOperations, DirectoryManager, FileExecutor
from ui import MainWindow, FileBrowser, TextEditor
from utils import FileUtils, SearchEngine, CompressionManager
from config import Settings

__all__ = [
    # Core modules
    'FileOperations',
    'DirectoryManager', 
    'FileExecutor',
    
    # UI modules
    'MainWindow',
    'FileBrowser',
    'TextEditor',
    
    # Utility modules
    'FileUtils',
    'SearchEngine',
    'CompressionManager',
    
    # Configuration
    'Settings'
]
'''
}

def create_init_files():
    """Tạo tất cả file __init__.py"""
    base_path = Path('.')
    
    for file_path, content in init_contents.items():
        full_path = base_path / file_path
        
        # Tạo thư mục nếu chưa tồn tại
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ghi nội dung vào file
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            print(f"✓ Đã tạo: {file_path}")
        except Exception as e:
            print(f"✗ Lỗi tạo {file_path}: {e}")

if __name__ == "__main__":
    print("Đang tạo các file __init__.py...")
    create_init_files()
    print("Hoàn thành!")