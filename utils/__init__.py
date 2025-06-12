"""
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