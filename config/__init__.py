"""
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