"""
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