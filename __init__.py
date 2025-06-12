"""
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