#!/usr/bin/env python3
"""
File Manager Application
Main entry point for the File Manager GUI application
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("Error: tkinter is not available. Please install tkinter.")
    sys.exit(1)

# Import application modules
try:
    from ui.main_window import MainWindow
    from config.settings import Settings
    from utils.file_utils import FileUtils
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please make sure all required modules are properly installed.")
    sys.exit(1)


class FileManagerApp:
    """Main File Manager Application Class"""
    
    def __init__(self):
        """Initialize the File Manager application"""
        self.root = None
        self.main_window = None
        self.settings = None
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "file_manager.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("File Manager application starting...")
    
    def load_settings(self):
        """Load application settings"""
        try:
            self.settings = Settings()
            self.logger.info("Settings loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            # Use default settings if loading fails
            self.settings = Settings()
    
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = ['logs', 'temp', 'config']
        
        for dir_name in directories:
            dir_path = project_root / dir_name
            try:
                dir_path.mkdir(exist_ok=True)
                self.logger.debug(f"Directory ensured: {dir_path}")
            except Exception as e:
                self.logger.warning(f"Could not create directory {dir_path}: {e}")
    
    def initialize_ui(self):
        """Initialize the user interface"""
        try:
            # Create root window
            self.root = tk.Tk()
            
            # Set window properties
            self.root.title("File Manager")
            self.root.geometry("1200x800")
            self.root.minsize(800, 600)
            
            # Set window icon if available
            icon_path = project_root / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            
            # Create main window
            self.main_window = MainWindow(self.root, self.settings)
            
            # Center window on screen
            self.center_window()
            
            self.logger.info("UI initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize UI: {e}")
            messagebox.showerror("Initialization Error", 
                               f"Failed to initialize the application:\n{e}")
            return False
        
        return True
    
    def center_window(self):
        """Center the main window on screen"""
        try:
            self.root.update_idletasks()
            
            # Get window dimensions
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate position
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            # Set window position
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
        except Exception as e:
            self.logger.warning(f"Could not center window: {e}")
    
    def setup_error_handling(self):
        """Setup global error handling"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            self.logger.error(
                "Uncaught exception", 
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
            # Show error dialog if GUI is available
            if self.root:
                try:
                    messagebox.showerror(
                        "Unexpected Error",
                        f"An unexpected error occurred:\n{exc_value}\n\n"
                        "Please check the log file for more details."
                    )
                except:
                    pass
        
        sys.excepthook = handle_exception
    
    def run(self):
        """Run the File Manager application"""
        try:
            # Setup logging
            self.setup_logging()
            
            # Create necessary directories
            self.create_directories()
            
            # Load settings
            self.load_settings()
            
            # Setup error handling
            self.setup_error_handling()
            
            # Initialize UI
            if not self.initialize_ui():
                return 1
            
            # Setup cleanup on window close
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            self.logger.info("Starting main event loop")
            
            # Start the main event loop
            self.root.mainloop()
            
            self.logger.info("Application closed normally")
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            return 0
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            if self.root is None:
                print(f"Fatal error: {e}")
            return 1
    
    def on_closing(self):
        """Handle application closing"""
        try:
            self.logger.info("Application closing...")
            
            # Save settings if main window exists
            if self.main_window:
                try:
                    self.main_window.save_state()
                except Exception as e:
                    self.logger.warning(f"Could not save window state: {e}")
            
            # Clean up temporary files
            temp_dir = project_root / "temp"
            if temp_dir.exists():
                try:
                    FileUtils.cleanup_temp_files(temp_dir)
                except Exception as e:
                    self.logger.warning(f"Could not clean up temp files: {e}")
            
            # Destroy the root window
            if self.root:
                self.root.destroy()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # Force exit if cleanup fails
            sys.exit(1)


def check_requirements():
    """Check if all required dependencies are available"""
    required_modules = [
        'tkinter',
        'pathlib',
        'logging',
        'os',
        'sys'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"Error: Missing required modules: {', '.join(missing_modules)}")
        print("Please install the required dependencies using:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main entry point"""
    print("File Manager - Starting application...")
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Create and run the application
    app = FileManagerApp()
    return app.run()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)