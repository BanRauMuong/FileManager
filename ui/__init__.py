"""
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